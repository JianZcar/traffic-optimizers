import subprocess
from pathlib import Path
from pprint import pprint

from algorithms.ga import generate_population, run_evolution
from algorithms.websters import websters_method
from common.data_capture import average_queue_length_per_edge, derive_saturation_flows
from common.typings import Approach, Movement, SignalPhase
from common.xml_generators import (
    build_intersection_sumo,
    generate_tl_logic,
)
from common.run_baseline_sim import runBaseline
from common.export_data import generate_traffic_report
from common.utils import attach_link_indices
from common.constants import BASE_NETWORK_PATH
from common.intersection_builder import build_intersection

# --- Define approach input data for a T-intersection ---
approach_inputs = [
    # North
    {"name": "1_in", "x": 0.0, "y": 100, "edge_id": "1_in", "num_lanes": 2},
    {"name": "1_out", "x": 0.0, "y": 100, "edge_id": "1_out", "num_lanes": 2},

    # South
    {"name": "3_in", "x": 0.0, "y": -100, "edge_id": "3_in", "num_lanes": 2},
    {"name": "3_out", "x": 0.0, "y": -100, "edge_id": "3_out", "num_lanes": 2},

    # West
    {"name": "4_in", "x": -150, "y": 0.0, "edge_id": "4_in", "num_lanes": 2},
    {"name": "4_out", "x": -150, "y": 0.0, "edge_id": "4_out", "num_lanes": 2},
]

# --- Define allowed movements for a T-intersection with fixed average flows ---
allowed_movements = [
    {"from_edge": "1_in", "to_edge": "3_out", "num_lanes": 1,
        "movement_type": "straight", "average_flow": 500},
    {"from_edge": "1_in", "to_edge": "4_out", "num_lanes": 1,
        "movement_type": "right", "average_flow": 400},
    {"from_edge": "3_in", "to_edge": "1_out", "num_lanes": 1,
        "movement_type": "straight", "average_flow": 600},
    {"from_edge": "3_in", "to_edge": "4_out", "num_lanes": 1,
        "movement_type": "left", "average_flow": 350},
    {"from_edge": "4_in", "to_edge": "3_out", "num_lanes": 1,
        "movement_type": "right", "average_flow": 450},
    {"from_edge": "4_in", "to_edge": "1_out", "num_lanes": 1,
        "movement_type": "left", "average_flow": 300},
]

# --- Build intersection object ---
intersection = build_intersection(
    name="T-Intersection",
    approach_data=approach_inputs,
    allowed_movements=allowed_movements,
    position=(0.0, 0.0),
    radius=1.0
)

# --- Generate XMLs fresh each run ---
build_intersection_sumo(intersection, BASE_NETWORK_PATH)

# --- Attach link indices to movements ---
attach_link_indices(BASE_NETWORK_PATH / "connections.xml",
                    intersection.movements)

print("HEY")

# # --- Run baseline & flows ---
derive_saturation_flows(intersection)
pprint(intersection)
# runBaseline()
# average_flows = get_average_flow()

# --- Baseline SUMO run ---
# subprocess.run(
#     [
#         "sumo",
#         "-n", "data/net.xml",
#         "-r", "data/routes.xml",
#         "--tripinfo-output", "tripinfo.xml",
#         "--queue-output", "q_.xml",
#         "--verbose"
#     ],
#     check=True,
#     capture_output=True,
#     text=True
# )

print(average_queue_length_per_edge("q_.xml"))
generate_traffic_report("tripinfo.xml", "Initial_traffic_bySUMO.png")

# --- Generate population ---
population = generate_population(size=1, phase_params_list=phase_params)
pprint(population)

# --- Run Webster’s & GA ---
generate_tl_logic('data/connections.xml', "tl_logic.xml", population[0])

subprocess.run(
    [
        "sumo",
        "-n", "data/net.xml",
        "-r", "data/routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--additional-files", "tl_logic.xml",
        "--verbose"
    ],
    check=True,
    capture_output=True,
    text=True
)

generate_traffic_report("tripinfo.xml", "Initial_traffic_byWebsters.png")

pop = run_evolution(population)

tl_xml = generate_tl_logic('data/connections.xml', "tl_logic.xml", pop[0][0])

subprocess.run(
    [
        "sumo",
        "-n", "data/net.xml",
        "-r", "data/routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--additional-files", "tl_logic.xml",
        "--verbose"
    ],
    check=True,
    capture_output=True,
    text=True
)

generate_traffic_report("tripinfo.xml", "finalGA.png")

print("Initial Websters")
print(population[0])

print("Final GA")
print(pop[0][0])
