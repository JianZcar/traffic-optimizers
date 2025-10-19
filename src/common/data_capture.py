import json
import subprocess
import xml.etree.ElementTree as ET
import traci
from collections import defaultdict
from pathlib import Path
from typing import Dict, Union, List, cast
from os import PathLike
import shutil
from common.typings import Movement, Intersection
from common.constants import BASE_NETWORK_PATH, SATURATION_ROOT_PATH, SATURATION_CACHE_FILE


def load_saturation_cache() -> Dict[str, float]:
    if SATURATION_CACHE_FILE.exists():
        with open(SATURATION_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_saturation_cache(cache: Dict[str, float]) -> None:
    SATURATION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SATURATION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def movement_key(movement: Movement) -> str:
    """Unique key for a movement (used for caching)."""
    return f"{movement.from_approach.edge_id}->{movement.to_approach.edge_id}:{movement.num_lanes}"


def setup_saturation_folder(movement: Movement, folder: Path) -> Path:
    """
    Create a dedicated folder for the movement and generate a high-demand route.
    Returns path to the routes.xml.
    """
    folder.mkdir(parents=True, exist_ok=True)

    # Copy base network files
    for file_name in ["nodes.xml", "edges.xml", "connections.xml"]:
        shutil.copy(BASE_NETWORK_PATH / file_name, folder / file_name)

    # Generate routes.xml with high demand for the movement
    routes_file = folder / "routes.xml"
    with open(routes_file, "w") as f:
        f.write(f"""<routes>
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"/>
    <flow id="flow_{movement.from_approach.edge_id}_to_{movement.to_approach.edge_id}"
          type="car"
          begin="0"
          end="3600"
          number="10000"
          from="{movement.from_approach.edge_id}"
          to="{movement.to_approach.edge_id}"/>
</routes>""")
    return routes_file


def run_saturation_simulation(movement: Movement, routes_path: Path) -> float:
    """
    Run SUMO for a single movement and compute per-lane saturation flow.
    Uses caching so repeated calls return stored results.
    """
    # --- check cache ---
    cache = load_saturation_cache()
    key = movement_key(movement)
    if key in cache:
        return cache[key]

    # --- build network ---
    net_file = routes_path.parent / "network.net.xml"
    subprocess.run(
        [
            "netconvert",
            "-n", str(routes_path.parent / "nodes.xml"),
            "-e", str(routes_path.parent / "edges.xml"),
            "-x", str(routes_path.parent / "connections.xml"),
            "-o", str(net_file),
        ],
        check=True,
    )

    traci.start(["sumo", "-n", str(net_file), "-r", str(routes_path)])

    try:
        lane_ids = [f"{movement.from_approach.edge_id}_{i}" for i in range(
            movement.from_approach.num_lanes)]
        prev_seen: Dict[str, set] = {lane: set() for lane in lane_ids}
        total_passed = 0

        while cast(int, traci.simulation.getMinExpectedNumber()) > 0:
            traci.simulationStep()
            for lane in lane_ids:
                current = set(traci.lane.getLastStepVehicleIDs(lane))
                # new vehicles = those in current but not seen before
                new = current - prev_seen[lane]
                total_passed += len(new)
                prev_seen[lane] |= new  # mark them as seen

        sim_time: float = cast(float, traci.simulation.getTime())
        if sim_time <= 0:
            raise RuntimeError("Simulation time is zero")

        # veh/h/lane
        result = (total_passed / sim_time) * 3600

        # --- save to cache ---
        cache[key] = result
        save_saturation_cache(cache)

        return result

    finally:
        traci.close()


def derive_saturation_flows(intersection: Intersection):
    """
    Loop through all movements, run dedicated simulations (if needed),
    and compute saturation flows. Uses cache when available.
    """
    saturation_root = Path("data/saturation")
    cache = load_saturation_cache()

    for m in intersection.movements:
        key = movement_key(m)

        if key in cache:
            m.saturation_flow = cache[key]
            print(
                f"[CACHE] {m.from_approach.name} -> {m.to_approach.name}: {m.saturation_flow:.1f} veh/h/lane")
        else:
            folder = saturation_root / \
                f"{m.from_approach.edge_id}_to_{m.to_approach.edge_id}"
            routes_path = setup_saturation_folder(m, folder)
            m.saturation_flow = run_saturation_simulation(m, routes_path)
            print(
                f"[SIMULATED] {m.from_approach.name} -> {m.to_approach.name}: {m.saturation_flow:.1f} veh/h/lane")


def get_all_incoming_edges(routes_path: Union[str, PathLike[str]]) -> list[str]:
    """Parse routes.xml to get all unique 'from' edges."""
    tree = ET.parse(routes_path)
    root = tree.getroot()
    # only include non-None 'from' attributes
    edges = {flow.get("from") for flow in root.findall(
        "flow") if flow.get("from") is not None}
    return [edge for edge in edges if edge is not None]


def average_queue_length_per_edge(queue_output_path: str) -> Dict[str, float]:
    """
    Computes the average queue length per edge from SUMO's queue output file.

    Args:
        queue_output_path (str): Path to SUMO queue XML output

    Returns:
        Dict[str, float]: Average queue length per edge

    Raises:
        RuntimeError: If XML parsing fails
    """
    try:
        tree = ET.parse(queue_output_path)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse {queue_output_path}") from e

    root = tree.getroot()

    edge_totals: Dict[str, float] = defaultdict(float)
    edge_counts: Dict[str, int] = defaultdict(int)

    for timestep in root.findall("data"):
        lanes = timestep.find("lanes")
        if lanes is None:
            continue
        for lane in lanes.findall("lane"):
            lane_id = lane.attrib["id"]
            edge_id = "_".join(lane_id.split("_")[:-1])
            queue_length: float = float(
                lane.attrib.get("queueing_length", 0.0))

            edge_totals[edge_id] += queue_length
            edge_counts[edge_id] += 1

    if not edge_totals:
        raise RuntimeError("No queueing data found in file")

    edge_averages: Dict[str, float] = {
        edge: round(edge_totals[edge] / edge_counts[edge], 2)
        for edge in edge_totals
    }

    return edge_averages
