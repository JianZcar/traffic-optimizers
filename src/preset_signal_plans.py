import copy
from pprint import pformat
from custom_typings import SignalPlan

# --- Import without collisions ---
from intersections.TC2 import (
    min_signal_plan as TC2_min_base,
    avg_signal_plan as TC2_avg_base,
    max_signal_plan as TC2_max_base,
)

from intersections.TC9 import (
    min_signal_plan as TC9_min_base,
    avg_signal_plan as TC9_avg_base,
    max_signal_plan as TC9_max_base,
)


# --- PSU TINIGUIBAN CURRENT CONFIGURATIONS ---

def configure_TC2_signal_plan(base_plan: SignalPlan, phase_timings: list[dict]) -> SignalPlan:
    plan_copy = copy.deepcopy(base_plan)
    start_time = 0.0

    for idx, phase in enumerate(plan_copy):
        phase.green = phase_timings[idx]["green"]
        phase.amber = phase_timings[idx]["amber"]
        phase.all_red = phase_timings[idx]["all_red"]

        phase.start = start_time
        phase.duration = phase.green + phase.amber + phase.all_red
        start_time += phase.duration

    return plan_copy


phase_timings_TC2 = [
    {'green': 68.0, 'amber': 3.0, 'all_red': 3.0},
    {'green': 32.0, 'amber': 3.0, 'all_red': 3.0},
    {'green': 28.0, 'amber': 3.0, 'all_red': 3.0},
]

TC2_min_signal_plan = configure_TC2_signal_plan(TC2_min_base, phase_timings_TC2)
TC2_avg_signal_plan = configure_TC2_signal_plan(TC2_avg_base, phase_timings_TC2)
TC2_max_signal_plan = configure_TC2_signal_plan(TC2_max_base, phase_timings_TC2)


# --- RIZAL AVE – VALENCIA ST. CURRENT CONFIGURATIONS ---

def configure_TC9_signal_plan(base_plan: SignalPlan, phase_timings: list[dict]) -> SignalPlan:
    plan_copy = copy.deepcopy(base_plan)
    start_time = 0.0

    for idx, phase in enumerate(plan_copy):
        phase.green = phase_timings[idx]["green"]
        phase.amber = phase_timings[idx]["amber"]
        phase.all_red = phase_timings[idx]["all_red"]

        phase.start = start_time
        phase.duration = phase.green + phase.amber + phase.all_red
        start_time += phase.duration

    return plan_copy


phase_timings_TC9 = [
    {'green': 26.0, 'amber': 3.0, 'all_red': 3.0},
    {'green': 18.0, 'amber': 3.0, 'all_red': 1.0},
    {'green': 58.0, 'amber': 3.0, 'all_red': 3.0},
]

TC9_min_signal_plan = configure_TC9_signal_plan(TC9_min_base, phase_timings_TC9)
TC9_avg_signal_plan = configure_TC9_signal_plan(TC9_avg_base, phase_timings_TC9)
TC9_max_signal_plan = configure_TC9_signal_plan(TC9_max_base, phase_timings_TC9)


# --- Output Example ---
if __name__ == "__main__":
    with open("TC2_avg_signal_plan.txt", "w") as f:
        f.write(pformat(TC2_avg_signal_plan))
