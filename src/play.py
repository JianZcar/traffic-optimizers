from intersections.utils import print_phase_flow_ratios
from intersections.TC2 import avg_signal_plan, avg_flow_intersection
from pprint import pprint
from algorithms.websters import simulate_poisson_arrival_rate

if __name__ == "__main__":
    print_phase_flow_ratios(signal_plan=avg_signal_plan)
    print(simulate_poisson_arrival_rate(0.12 * 60))
    