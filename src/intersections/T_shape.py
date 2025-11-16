from custom_typings import Approach, Movement, Intersection, SignalPhase, SignalPlan
from pathlib import Path
from openpyxl import load_workbook
from pprint import pprint
from math import ceil
from typing import Dict, List


# --- DATA FROM SHEETS ---
workbook = load_workbook(
    Path.cwd() / 'uzzi/intersections/sheets/T_intersection.xlsx', data_only=True)


# Peak flow rates (veh/h)
# flow_1_in_3_out: int = ceil(workbook['1-3']['AC86'].value)
# flow_1_in_4_out: int = ceil(workbook['1-4']['AC86'].value)
# flow_3_in_1_out: int = ceil(workbook['3-1']['AC86'].value)
# flow_3_in_4_out: int = ceil(workbook['3-4']['AC86'].value)
# flow_4_in_1_out: int = ceil(workbook['4-1']['AC86'].value)
# flow_4_in_3_out: int = ceil(workbook['4-3']['AC86'].value)

# Average flow rates (veh/h)
flow_1_in_3_out = ceil(sum(v for v in [
                       workbook['1-3'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)
flow_1_in_4_out = ceil(sum(v for v in [
                       workbook['1-4'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)
flow_3_in_1_out = ceil(sum(v for v in [
                       workbook['3-1'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)
flow_3_in_4_out = ceil(sum(v for v in [
                       workbook['3-4'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)
flow_4_in_1_out = ceil(sum(v for v in [
                       workbook['4-1'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)
flow_4_in_3_out = ceil(sum(v for v in [
                       workbook['4-3'][f'AC{r}'].value for r in range(68, 82)] if v is not None) / 14)


# --- APPROACHES ---

# Approach 1 (North)
approach_1_in: Approach = Approach(name='1_in',
                                   x=-250,
                                   y=0,
                                   edge_id='1_in',
                                   num_lanes=2)
approach_1_out: Approach = Approach(name='1_out',
                                    x=-250,
                                    y=0,
                                    edge_id='1_out',
                                    num_lanes=2)

# Approach 3 (South)
approach_3_in: Approach = Approach(name='3_in',
                                   x=250,
                                   y=0,
                                   edge_id='3_in',
                                   num_lanes=2)
approach_3_out: Approach = Approach(name='3_out',
                                    x=250,
                                    y=-0,
                                    edge_id='3_out',
                                    num_lanes=2)

# Approach 4 (West)
approach_4_in: Approach = Approach(name='4_in',
                                   x=0,
                                   y=-150,
                                   edge_id='4_in',
                                   num_lanes=2)
approach_4_out: Approach = Approach(name='4_out',
                                    x=0,
                                    y=-150,
                                    edge_id='4_out',
                                    num_lanes=2)

approaches: List[Approach] = [approach_1_in, approach_1_out,
                              approach_3_in, approach_3_out,
                              approach_4_in, approach_4_out]


# --- MOVEMENTS ---

# Movement: 1_in -> 3_out (North to South, Straight)
movement_1_in_3_out_lane_0 = Movement(
    from_approach=approach_1_in,
    to_approach=approach_3_out,
    lane_index=0,
    toLanes=[0],
    average_flow=flow_1_in_3_out / 2,
)

movement_1_in_3_out_lane_1 = Movement(
    from_approach=approach_1_in,
    to_approach=approach_3_out,
    lane_index=1,
    toLanes=[1],
    average_flow=flow_1_in_3_out / 2,
)

# Movement: 1_in -> 4_out (North to West, Right Turn)
movement_1_in_4_out_lane_0 = Movement(
    from_approach=approach_1_in,
    to_approach=approach_4_out,
    lane_index=0,
    toLanes=[0, 1],
    average_flow=flow_1_in_4_out,
)

# Movement: 3_in -> 1_out (South to North, Straight)
movement_3_in_1_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0],
    average_flow=flow_3_in_1_out / 2,
)

movement_3_in_1_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[1],
    average_flow=flow_3_in_1_out / 2,
)

# Movement: 3_in -> 4_out (South to West, Left Turn)
movement_3_in_4_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[0, 1],
    average_flow=flow_3_in_4_out,
)

# Movement: 4_in -> 1_out (West to North, Left Turn)
movement_4_in_1_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[0, 1],
    average_flow=flow_4_in_1_out,
)

# Movement: 4_in -> 3_out (West to South, Right Turn)
movement_4_in_3_out_lane_0 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_3_out,
    lane_index=0,
    toLanes=[0, 1],
    average_flow=flow_4_in_3_out,
)

movements: List[Movement] = [movement_1_in_3_out_lane_0, movement_1_in_3_out_lane_1,
                             movement_1_in_4_out_lane_0, movement_3_in_1_out_lane_0,
                             movement_3_in_1_out_lane_1, movement_3_in_4_out_lane_1,
                             movement_4_in_1_out_lane_1, movement_4_in_3_out_lane_0]

movements_dict: Dict[str, Movement] = {
    f"{mv.from_approach.edge_id}_{mv.to_approach.edge_id}_{mv.lane_index}": mv
    for mv in movements
}

# --- INTERSECTION ---
intersection: Intersection = Intersection(name="T Intersection (PSU Tiniguiban)",
                                          approaches=approaches,
                                          movements=movements)


# --- PHASES (DEFAULT DESIGN) ---
phase_1: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[movement_1_in_3_out_lane_0, movement_1_in_3_out_lane_1,
               movement_1_in_4_out_lane_0,
               movement_3_in_1_out_lane_0, movement_3_in_1_out_lane_1]
)

phase_2: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[movement_4_in_1_out_lane_1, movement_4_in_3_out_lane_0]
)

phase_3: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[movement_3_in_1_out_lane_0, movement_3_in_1_out_lane_1,
               movement_3_in_4_out_lane_1, movement_4_in_3_out_lane_0]
)


signal_plan: SignalPlan = [phase_1, phase_2, phase_3]


if __name__ == "__main__":
    pprint(intersection)  # Need for constructing intersection in SUMO
    pprint(signal_plan)  # Need for configuring traffic lights
