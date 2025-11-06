import subprocess
from pathlib import Path
from pprint import pprint
from unittest import result

# --- Import algorithm modules ---
from algorithms.ga import generate_population, run_evolution
from algorithms.websters import websters_method

# --- Import data utilities ---
from common.data_capture import average_queue_length_per_edge, derive_saturation_flows
from common.typings import Approach, Movement, SignalPhase

# --- Import XML & SUMO utilities ---
from common.xml_generators import (
    build_intersection_sumo,
    generate_tl_logic,
)
from common.run_baseline_sim import runBaseline
from common.export_data import generate_traffic_report
from common.utils import sync_lane_map_from_xml
from common.constants import BASE_NETWORK_PATH
from common.intersection_builder import build_fixed_intersection


# =====================================================
# SECTION 1: INTERSECTION SETUP AND XML GENERATION
# =====================================================

# Build a fixed-type intersection (e.g., T-intersection)
intersection = build_fixed_intersection("T")

# Generate SUMO-compatible XML files for the intersection
build_intersection_sumo(intersection, BASE_NETWORK_PATH)

# Synchronize the lane map from SUMO’s connections XML to local intersection data
sync_lane_map_from_xml(BASE_NETWORK_PATH / "connections.xml",
                       intersection.movements)

# pprint(f"Built Intersection: {intersection}")


# =====================================================
# SECTION 2: BASELINE FLOW ANALYSIS (SATURATION & QUEUES)
# =====================================================

# Derive saturation flow rates for each movement in the intersection
derive_saturation_flows(intersection)

# Optional diagnostics (commented out):
# print(average_queue_length_per_edge("q_.xml"))
# generate_traffic_report("tripinfo.xml", "Initial_traffic_bySUMO.png")


# =====================================================
# SECTION 3: INITIAL POPULATION GENERATION (FOR GA)
# =====================================================

# Create initial candidate signal timing configurations (population)
population = generate_population(size=1, movements=intersection.movements)
pprint(f"Initial Population: {population}")


# =====================================================
# SECTION 4: RUN WEBSTER’S METHOD AS BASELINE
# =====================================================

# Generate Webster’s signal timing plan into SUMO TL logic XML
generate_tl_logic(BASE_NETWORK_PATH / "connections.xml",
                  "tl_logic.xml", population[0])

# Run SUMO simulation using Webster’s plan
subprocess.run(
    [
        "sumo",
        "-n", BASE_NETWORK_PATH / "network.net.xml",
        "-r", BASE_NETWORK_PATH / "routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--additional-files", "tl_logic.xml",
        "--verbose"
    ],
    check=True,
    capture_output=True,
    text=True
)

# Export simulation results into a readable traffic report
generate_traffic_report("tripinfo.xml", "Initial_traffic_byWebsters.png")


# =====================================================
# SECTION 5: RUN GENETIC ALGORITHM (GA) OPTIMIZATION
# =====================================================

# Run the GA process to evolve better traffic light timings
pop = run_evolution(population)

# Generate the final evolved TL logic XML from the best GA result
tl_xml = generate_tl_logic(
    BASE_NETWORK_PATH / "connections.xml", "tl_logic.xml", pop[0][0])


# =====================================================
# SECTION 6: RUN FINAL SUMO SIMULATION USING GA RESULTS
# =====================================================

# Execute SUMO with the evolved GA timing plan
subprocess.run(
    [
        "sumo",
        "-n", BASE_NETWORK_PATH / "network.net.xml",
        "-r", BASE_NETWORK_PATH / "routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--additional-files", "tl_logic.xml",
        "--verbose"
    ],
    check=True,
    capture_output=True,
    text=True
)

# Generate and save a final performance comparison report
generate_traffic_report("tripinfo.xml", "finalGA.png")


# =====================================================
# SECTION 7: OUTPUT FINAL COMPARISON
# =====================================================

print("Initial Websters")
print(population[0])

print("Final GA")
print(pop[0][0])
