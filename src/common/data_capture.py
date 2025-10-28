import json
import subprocess
import xml.etree.ElementTree as ET
from common.utils import allocate_lanes_per_approach
from common.xml_generators import get_to_lane
import traci
from collections import defaultdict
from pathlib import Path
from typing import Dict, Union, List, cast, Optional
from os import PathLike
import shutil
from common.typings import Movement, Intersection, SignalPhase
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


def movement_key(movement: Movement, phase_id: Optional[str] = None) -> str:
    """
    Unique key for a movement in a given phase (used for caching).
    If phase_id is None, defaults to just the movement.
    """
    if phase_id:
        return f"{movement.from_approach.edge_id}_{phase_id}->{movement.to_approach.edge_id}_{phase_id}"
    return f"{movement.from_approach.edge_id}->{movement.to_approach.edge_id}"


def setup_saturation_folder(
    movement: Movement,
    folder: Path,
    allocated_from_lanes: List[int]
) -> Dict[int, Path]:
    """
    Create dedicated folders per allocated lane for the movement and generate
    high-pressure demand routes for saturation flow measurement.
    Returns a dictionary: {lane_idx: Path_to_routes.xml}.
    """
    lane_routes: Dict[int, Path] = {}

    for lane_idx in allocated_from_lanes:
        lane_folder = folder / f"lane_{lane_idx}"
        lane_folder.mkdir(parents=True, exist_ok=True)

        # Copy base network files
        for file_name in ["nodes.xml", "edges.xml", "connections.xml"]:
            shutil.copy(BASE_NETWORK_PATH / file_name, lane_folder / file_name)

        # Create high-demand routes.xml for this lane
        routes_file = lane_folder / "routes.xml"
        with open(routes_file, "w") as f:
            f.write(f"""<routes>
    <vType id="car"
           accel="2.6"
           decel="4.5"
           sigma="0.5"
           length="5"
           minGap="2.5"
           maxSpeed="13.9"/>

    <flow id="flow_{movement.from_approach.edge_id}_{lane_idx}_to_{movement.to_approach.edge_id}"
          type="car"
          begin="0"
          end="360"               
          vehsPerHour="10000"      
          from="{movement.from_approach.edge_id}"
          to="{movement.to_approach.edge_id}"
          departLane="{lane_idx}"
          departSpeed="0"/>      
</routes>""")

        lane_routes[lane_idx] = routes_file

    return lane_routes


def run_saturation_simulation(
    movement: Movement,
    lane_idx: int,
    routes_path: Path
) -> float:
    """
    Run SUMO for a single lane of a movement and compute its saturation flow.
    Uses priority junctions (constant green) to simulate ideal conditions.
    Returns saturation flow in veh/h for that lane.
    """
    # --- load cache ---
    cache = load_saturation_cache()
    key = movement_key(movement) + f"_{lane_idx}"
    if key in cache:
        return cache[key]

    # --- patch network for priority junctions ---
    net_file = routes_path.parent / "network.net.xml"
    nodes_file = routes_path.parent / "nodes.xml"

    tree = ET.parse(nodes_file)
    root = tree.getroot()
    for junc in root.findall("junction"):
        junc.attrib["type"] = "priority"
    tree.write(nodes_file, encoding="utf-8", xml_declaration=True)

    # --- convert network ---
    subprocess.run(
        [
            "netconvert",
            "-n", str(nodes_file),
            "-e", str(routes_path.parent / "edges.xml"),
            "-x", str(routes_path.parent / "connections.xml"),
            "-o", str(net_file),
        ],
        check=True,
    )
    # --- enforce all-green signal logic ---
    tree = ET.parse(net_file)
    root = tree.getroot()

    for tl in root.findall("tlLogic"):
        # Count total signals this tl controls
        controlled_links = sum(
            1
            for _ in root.findall(
                f"./connection[@tl='{tl.attrib['id']}']"
            )
        )

        if controlled_links > 0:
            all_green = "G" * controlled_links

            # Overwrite any existing program/phases
            for child in list(tl):
                tl.remove(child)

            ET.SubElement(
                tl,
                "phase",
                attrib={"duration": "99999", "state": all_green}
            )

    tree.write(net_file, encoding="utf-8", xml_declaration=True)

    # --- run SUMO ---
    traci.start(["sumo", "-n", str(net_file), "-r", str(routes_path)])
    try:
        lane_id = f"{movement.from_approach.edge_id}_{lane_idx}"
        prev_seen: set = set()
        total_passed = 0

        while cast(int, traci.simulation.getMinExpectedNumber()) > 0:
            traci.simulationStep()
            current = set(traci.lane.getLastStepVehicleIDs(lane_id))
            new = current - prev_seen
            total_passed += len(new)
            prev_seen |= new

        sim_time: float = cast(float, traci.simulation.getTime())
        if sim_time <= 0:
            raise RuntimeError("Simulation time is zero")

        # veh/h for this lane
        saturation_flow = (total_passed/sim_time) * 3600.0

        # --- cache ---
        cache[key] = saturation_flow
        save_saturation_cache(cache)

        return saturation_flow

    finally:
        traci.close()


def derive_saturation_flows(intersection: Intersection):
    """
    Loop through all movements, run dedicated simulations per lane using allocated lanes,
    and compute per-lane saturation flows. Uses cache when available.
    """
    saturation_root = Path("data/saturation")
    cache = load_saturation_cache()
    used_lanes: Dict[str, set] = defaultdict(set)

    # Group movements by from_approach
    by_from = defaultdict(list)
    for mv in intersection.movements:
        by_from[mv.from_approach.edge_id].append(mv)

    for from_edge_id, movements in by_from.items():
        approach = movements[0].from_approach
        allocations = allocate_lanes_per_approach(
            from_edge_id, movements, approach.num_lanes, used_lanes
        )

        for mv, allocated_from_lanes in allocations:
            folder = saturation_root / \
                f"{mv.from_approach.edge_id}_to_{mv.to_approach.edge_id}"
            lane_routes = setup_saturation_folder(
                mv, folder, allocated_from_lanes)

            # Run simulation per lane
            per_lane_saturation = {}
            for lane_idx, routes_path in lane_routes.items():
                key = movement_key(mv, phase_id=str(lane_idx))
                if key in cache:
                    sat = cache[key]
                else:
                    sat = run_saturation_simulation(
                        mv, lane_idx, routes_path)
                    cache[key] = sat
                    save_saturation_cache(cache)
                per_lane_saturation[lane_idx] = sat
                print(
                    f"[LANE {lane_idx}] {mv.from_approach.name} -> {mv.to_approach.name}: {sat:.1f} veh/h/lane")

            # Optional: store average for the movement
            mv.saturation_flow = sum(
                per_lane_saturation.values()) / len(per_lane_saturation)


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
