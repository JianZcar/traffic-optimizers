import subprocess
import os
from algorithms.ga import generate_population, run_evolution
from algorithms.websters import websters_method
from common.data_capture import get_average_flow, get_saturation_flow, average_queue_length_per_edge
from common.typings import IntersectionParams
from common.xml_generators import generate_tl_logic
from common.run_baseline_sim import runBaseline
from common.export_data import generate_traffic_report
from pprint import pprint

# Main CLI
saturation_flow = get_saturation_flow()
runBaseline()
average_flows = get_average_flow()

subprocess.run(
    [
        "netconvert",
        "-n", "data/nodes.xml",
        "-e", "data/edges.xml",
        "-x", "data/connections.xml",
        "-o", "data/net.xml",
        "--verbose"
    ],
    check=True,       # raises if SUMO exits non-zero
    capture_output=True,
    text=True
)

subprocess.run(
    [
        "sumo",
        "-n", "data/net.xml",
        "-r", "data/routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--queue-output", "q_.xml",
        "--verbose"
    ],
    check=True,       # raises if SUMO exits non-zero
    capture_output=True,
    text=True
)

print(average_queue_length_per_edge("q_.xml"))
generate_traffic_report("tripinfo.xml", "Initial_traffic_bySUMO.png")

intersection_params = IntersectionParams(
    saturation_flows=[saturation_flow, saturation_flow,
                      saturation_flow, saturation_flow],
    lambda_rates=[round(average_flows['W_in']/60, 2),
                  round(average_flows['E_in']/60, 2), round(average_flows['N_in']/60, 2)],
    reaction_time=1.0,                    # s
    road_widths=[3.2, 3.2, 3.2, 3.2],          # m
    vehicle_speed=13.89,                  # m/s
    deceleration_rate=4.5,                # m/s^2
    vehicle_length=5                      # m
)

population = generate_population(
    size=20, intersection_params=intersection_params)

pprint(population)

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
    check=True,       # raises if SUMO exits non-zero
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
    check=True,       # raises if SUMO exits non-zero
    capture_output=True,
    text=True
)

generate_traffic_report("tripinfo.xml", "finalGA.png")
print("Initial Websters")
# population.sort(key=lambda config: fitness(config))
print(population[0])


print("Final GA")
print(pop[0][0])
