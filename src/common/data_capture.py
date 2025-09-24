import subprocess
import xml.etree.ElementTree as ET
import traci
from collections import defaultdict
from pathlib import Path
from typing import Dict, Union, cast
from os import PathLike

from .xml_generators import saturation_flow_scenario


def get_average_flow(
    routes_path: Union[str, PathLike[str]] = "data/routes.xml"
) -> Dict[str, float]:
    """
    Calculate average traffic flow (veh/hour) for incoming edges to junction center,
    with fallback for non-traffic-light scenarios.

    Args:
        routes_path: Path to SUMO routes.xml file

    Returns:
        Dict[str, float]: Average flow per incoming edge (veh/hour)

    Raises:
        RuntimeError: If SUMO simulation cannot start or run properly
    """
    routes_path = str(routes_path)  # normalize Path -> str

    try:
        sumo_cmd = ["sumo", "-n", "data/net.xml", "-r", routes_path]
        traci.start(sumo_cmd)
    except Exception as e:
        raise RuntimeError(
            f"Failed to start SUMO with routes {routes_path}") from e

    print("All edges:", traci.edge.getIDList())

    incoming_edges: list[str] = ["W_in", "N_in", "E_in"]
    vehicle_counts: Dict[str, int] = {edge: 0 for edge in incoming_edges}
    has_traffic_light: bool = False

    # Traffic light setup
    try:
        tl_ids = traci.trafficlight.getIDList()
    except traci.TraCIException as e:
        traci.close()
        raise RuntimeError("Failed to query traffic light IDs") from e

    active_tls: str | None = None
    phase_incoming: Dict[int, str] = {}

    if tl_ids:
        has_traffic_light = True
        active_tls = tl_ids[0]  # use first TLS
        try:
            tl_program = traci.trafficlight.getCompleteRedYellowGreenDefinition(
                active_tls
            )
        except traci.TraCIException as e:
            traci.close()
            raise RuntimeError(
                f"Failed to fetch TLS definition for {active_tls}") from e
        print(f"Traffic light {active_tls} phases:", tl_program)

        phase_incoming = {
            0: "E_in",
            1: "N_in",
            2: "W_in",
        }

    counted_vehicles: set[str] = set()
    previous_vehicles: Dict[str, set[str]] = {
        edge: set() for edge in incoming_edges}

    try:
        while cast(int, traci.simulation.getMinExpectedNumber()) > 0:
            traci.simulationStep()

            if has_traffic_light and active_tls:
                try:
                    current_phase: int = cast(
                        int, traci.trafficlight.getPhase(active_tls)
                    )
                    active_incoming: str | None = phase_incoming.get(
                        current_phase % 3, None
                    )
                except traci.TraCIException:
                    has_traffic_light = False
                    active_incoming = None
            else:
                active_incoming = None

            if has_traffic_light and active_incoming:
                current_vehicles = set(
                    traci.edge.getLastStepVehicleIDs(active_incoming)
                )
                new_vehicles = current_vehicles - \
                    previous_vehicles[active_incoming]

                for veh_id in new_vehicles:
                    if veh_id not in counted_vehicles:
                        vehicle_counts[active_incoming] += 1
                        counted_vehicles.add(veh_id)

                previous_vehicles[active_incoming] = current_vehicles.copy()
            else:
                for edge in incoming_edges:
                    current_vehicles = set(
                        traci.edge.getLastStepVehicleIDs(edge))
                    new_vehicles = current_vehicles - previous_vehicles[edge]

                    for veh_id in new_vehicles:
                        if veh_id not in counted_vehicles:
                            vehicle_counts[edge] += 1
                            counted_vehicles.add(veh_id)

                    previous_vehicles[edge] = current_vehicles.copy()

        total_time: float = cast(float, traci.simulation.getTime())
    finally:
        traci.close()

    if total_time <= 0:
        raise RuntimeError("Simulation time is zero, cannot compute flows")

    average_flows: Dict[str, float] = {
        edge: (vehicle_counts[edge] / total_time) * 3600 for edge in incoming_edges
    }

    print(
        f"Average flows ({'with' if has_traffic_light else 'without'} traffic lights):"
    )
    print(average_flows)
    return average_flows


def get_saturation_flow() -> float:
    """
    Runs a temporary saturation flow scenario and computes the saturated flow
    for the eastbound approach (E_in).

    Returns:
        float: Saturated flow for E_in (veh/hour)

    Raises:
        RuntimeError: If netconvert or SUMO simulation fails
    """
    routes_path, tmp_dir = saturation_flow_scenario()

    original_nodes_path = Path("data") / "nodes.xml"
    try:
        tree = ET.parse(original_nodes_path)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse {original_nodes_path}") from e

    root = tree.getroot()

    modified_root = ET.Element("nodes")
    for node in root.findall("node"):
        node_copy = ET.Element("node", node.attrib)
        if node_copy.get("id") == "J0":
            node_copy.set("type", "priority")
        modified_root.append(node_copy)

    nodes_path = Path(tmp_dir) / "nodes.xml"
    ET.ElementTree(modified_root).write(
        str(nodes_path), encoding="utf-8", xml_declaration=True
    )

    try:
        subprocess.run(
            [
                "netconvert",
                "-n", str(nodes_path),
                "-e", "data/edges.xml",
                "-x", "data/connections.xml",
                "-o", "data/net.xml",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError("netconvert failed") from e

    flows = get_average_flow(str(routes_path))

    if "E_in" not in flows:
        raise RuntimeError("No flow data for E_in in simulation output")

    print(f"Saturated flow: {flows['E_in']}")
    return flows["E_in"]


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
