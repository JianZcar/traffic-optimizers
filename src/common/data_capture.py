import subprocess
import math
import xml.etree.ElementTree as ET
import traci
import sumolib
from collections import defaultdict
from .xml_generators import saturation_flow_scenario
from pathlib import Path


def get_average_flow(routes_path="data/routes.xml"):
    """
    Calculate average traffic flow (veh/hour) for incoming edges to junction center,
    with fallback for non-traffic-light scenarios.
    """
    # Start SUMO simulation
    sumo_cmd = ["sumo",
                "-n", "data/net.xml",
                "-r", routes_path]
    traci.start(sumo_cmd)
    print("All edges:", traci.edge.getIDList())

    # Initialize data structures
    incoming_edges = ['W_in', 'N_in', 'E_in']
    vehicle_counts = {edge: 0 for edge in incoming_edges}
    has_traffic_light = False

    try:
        # Check if traffic light exists
        tl_ids = traci.trafficlight.getIDList()
        if 'J0' in traci.trafficlight.getIDList():
            tl_program = traci.trafficlight.getCompleteRedYellowGreenDefinition(
                'J0')
            print("Traffic light phases:", tl_program)

            # Example mapping (adjust based on actual phases):
            phase_incoming = {
                0: 'E_in',  # Phase 0: East green
                1: 'N_in',  # Phase 1: North green
                2: 'W_in',  # Phase 2: West green
            }
    except traci.TraCIException:
        has_traffic_light = False

    # Track vehicles that have been counted
    counted_vehicles = set()
    previous_vehicles = {edge: set() for edge in incoming_edges}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        if has_traffic_light:
            try:
                current_phase = traci.trafficlight.getPhase()
                active_incoming = phase_incoming.get(current_phase % 3, None)
            except traci.TraCIException:
                # Fallback if traffic light disappears during simulation
                has_traffic_light = False
                active_incoming = None
        else:
            # No traffic light mode: count all incoming edges
            active_incoming = None

        if has_traffic_light and active_incoming:
            # Traffic light-aware counting
            current_vehicles = set(
                traci.edge.getLastStepVehicleIDs(active_incoming))
            new_vehicles = current_vehicles - \
                previous_vehicles[active_incoming]

            for veh_id in new_vehicles:
                if veh_id not in counted_vehicles:
                    vehicle_counts[active_incoming] += 1
                    counted_vehicles.add(veh_id)

            previous_vehicles[active_incoming] = current_vehicles.copy()
        else:
            # Count all incoming edges continuously
            for edge in incoming_edges:
                current_vehicles = set(traci.edge.getLastStepVehicleIDs(edge))
                new_vehicles = current_vehicles - previous_vehicles[edge]

                for veh_id in new_vehicles:
                    if veh_id not in counted_vehicles:
                        vehicle_counts[edge] += 1
                        counted_vehicles.add(veh_id)

                previous_vehicles[edge] = current_vehicles.copy()

    total_time = traci.simulation.getTime()
    traci.close()

    # Calculate flows
    average_flows = {}
    for edge in incoming_edges:
        if total_time == 0:
            average_flows[edge] = 0
        else:
            average_flows[edge] = (vehicle_counts[edge] / total_time) * 3600

    print(
        f"Average flows ({'with' if has_traffic_light else 'without'} traffic lights):")
    print(average_flows)
    return average_flows


def get_saturation_flow():
    routes_path, tmp_dir = saturation_flow_scenario()

    original_nodes_path = Path("data") / "nodes.xml"
    tree = ET.parse(original_nodes_path)
    root = tree.getroot()

    # Copy all nodes, change only J0 type
    modified_root = ET.Element("nodes")
    for node in root.findall("node"):
        node_copy = ET.Element("node", node.attrib)
        if node_copy.get("id") == "J0":
            node_copy.set("type", "priority")
        modified_root.append(node_copy)

    nodes_path = Path(tmp_dir) / "nodes.xml"
    ET.ElementTree(modified_root).write(str(nodes_path),
                                        encoding="utf-8", xml_declaration=True)

    try:
        subprocess.run([
            "netconvert",
            "-n", str(nodes_path),
            "-e", "data/edges.xml",
            "-x", "data/connections.xml",
            "-o", "data/net.xml"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print("netconvert failed:", e)
        return None

    flows = get_average_flow(routes_path)
    print(f'Saturated flow: {flows["E_in"]}')
    return flows["E_in"]


def average_queue_length_per_edge(queue_output_path):
    tree = ET.parse(queue_output_path)
    root = tree.getroot()

    edge_totals = defaultdict(float)
    edge_counts = defaultdict(int)
    lane_to_edge = {}

    for timestep in root.findall('data'):
        lanes = timestep.find('lanes')
        if lanes is None:
            continue
        for lane in lanes.findall('lane'):
            lane_id = lane.attrib['id']
            # Convert N_in_0 → N_in
            edge_id = "_".join(lane_id.split("_")[:-1])
            queue_length = float(lane.attrib.get('queueing_length', 0.0))

            # Track edge stats
            edge_totals[edge_id] += queue_length
            edge_counts[edge_id] += 1

    # Compute averages
    edge_averages = {edge: round(edge_totals[edge] / edge_counts[edge], 2)
                     for edge in edge_totals}

    return edge_averages
