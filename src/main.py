import subprocess
from pathlib import Path
from pprint import pprint
from unittest import result

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
from common.intersection_builder import build_fixed_intersection

intersection = build_fixed_intersection("T")
build_intersection_sumo(intersection, BASE_NETWORK_PATH)
attach_link_indices(BASE_NETWORK_PATH / "connections.xml", intersection.movements)

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
population = generate_population(size=1, movements=intersection.movements)
pprint(f"Initial Population: {population}")

# --- Run Webster’s & GA ---
generate_tl_logic(BASE_NETWORK_PATH / "connections.xml", "tl_logic.xml", population[0])

result = subprocess.run(
    [
        "sumo",
        "-n", BASE_NETWORK_PATH / "net.xml",
        "-r", BASE_NETWORK_PATH / "routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--additional-files", "tl_logic.xml",
        "--verbose"
    ],
    check=True,
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("❌ SUMO failed with error:")
    print(result.stderr)   # ← this is the key part
else:
    print("✅ SUMO ran successfully!")

generate_traffic_report("tripinfo.xml", "Initial_traffic_byWebsters.png")

pop = run_evolution(population)

tl_xml = generate_tl_logic(BASE_NETWORK_PATH / "connections.xml", "tl_logic.xml", pop[0][0])

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
