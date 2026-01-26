from custom_typings import Approach, Movement, Intersection, SignalPhase, SignalPlan
from constants import INTERSECTION_SHEETS_PATH
from pathlib import Path
from openpyxl import load_workbook
from pprint import pprint
from math import ceil
from typing import Dict, List


def flow_stats(sheet, col="AC", start=68, end=82):
    """Returns avg, min, max flow rate (veh/h) for a given movement."""
    values = [
        sheet[f"{col}{r}"].value
        for r in range(start, end)
        if sheet[f"{col}{r}"].value is not None
    ]

    if not values:
        return {"avg": 0, "min": 0, "max": 0}

    avg_flow = ceil(sum(values) / len(values))
    return {
        "avg": avg_flow,
        "min": min(values),
        "max": max(values)
    }


# --- DATA FROM SHEETS ---
workbook = load_workbook(
    INTERSECTION_SHEETS_PATH / 'TC9.xlsx', data_only=True)


# Peak flow rates (veh/h)
# flow_1_in_3_out: int = ceil(workbook['1-3']['AC86'].value)
# flow_1_in_4_out: int = ceil(workbook['1-4']['AC86'].value)
# flow_3_in_1_out: int = ceil(workbook['3-1']['AC86'].value)
# flow_3_in_4_out: int = ceil(workbook['3-4']['AC86'].value)
# flow_4_in_1_out: int = ceil(workbook['4-1']['AC86'].value)
# flow_4_in_3_out: int = ceil(workbook['4-3']['AC86'].value)

# Average flow rates (veh/h)
flow_2_in_1_out = flow_stats(workbook["21"])
flow_2_in_4_out = flow_stats(workbook["24"])
flow_3_in_1_out = flow_stats(workbook["31"])
flow_3_in_2_out = flow_stats(workbook["32"])
flow_3_in_4_out = flow_stats(workbook["34"])
flow_4_in_1_out = flow_stats(workbook["41"])
flow_4_in_2_out = flow_stats(workbook["42"])


# --- APPROACHES ---

# Approach 1 (North)
approach_1_out: Approach = Approach(name='1_out',
                                    x=0,
                                    y=100,
                                    edge_id='1_out',
                                    num_lanes=2)


# Approach 2 (East)
approach_2_in: Approach = Approach(name='2_in',
                                   x=150,
                                   y=0,
                                   edge_id='2_in',
                                   num_lanes=2)

approach_2_out: Approach = Approach(name='2_out',
                                    x=150,
                                    y=0,
                                    edge_id='2_out',
                                    num_lanes=2)


# Approach 3 (South)
approach_3_in: Approach = Approach(name='3_in',
                                   x=0,
                                   y=-100,
                                   edge_id='3_in',
                                   num_lanes=2)


# Approach 4 (West)
approach_4_in: Approach = Approach(name='4_in',
                                   x=-150,
                                   y=0,
                                   edge_id='4_in',
                                   num_lanes=2)
approach_4_out: Approach = Approach(name='4_out',
                                    x=-150,
                                    y=0,
                                    edge_id='4_out',
                                    num_lanes=2)

approaches: List[Approach] = [approach_1_out,
                              approach_2_in, approach_2_out,
                              approach_3_in,
                              approach_4_in, approach_4_out]


# --- MIN MOVEMENTS ---

min_movement_2_in_1_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_2_in_1_out["min"],
    average_flow=flow_2_in_1_out["avg"],
)

min_movement_2_in_4_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_2_in_4_out["min"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

min_movement_2_in_4_out_lane_1 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_2_in_4_out["min"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

min_movement_3_in_1_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_3_in_1_out["min"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

min_movement_3_in_1_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_3_in_1_out["min"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

min_movement_3_in_2_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_3_in_2_out["min"],
    average_flow=flow_3_in_2_out["avg"],
)

min_movement_3_in_4_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_3_in_4_out["min"],
    average_flow=flow_3_in_4_out["avg"],
)

min_movement_4_in_1_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_4_in_1_out["min"],
    average_flow=flow_4_in_1_out["avg"],
)

min_movement_4_in_2_out_lane_0 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_4_in_2_out["min"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)

min_movement_4_in_2_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_4_in_2_out["min"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)


min_movements: List[Movement] = [min_movement_2_in_1_out_lane_0, min_movement_2_in_4_out_lane_0,
                                 min_movement_3_in_1_out_lane_0, min_movement_3_in_1_out_lane_1, min_movement_3_in_2_out_lane_0, min_movement_3_in_4_out_lane_1,
                                 min_movement_4_in_1_out_lane_1, min_movement_4_in_2_out_lane_0, min_movement_4_in_2_out_lane_1]

# --- INTERSECTION ---
min_flow_intersection: Intersection = Intersection(name="TC9",
                                                   approaches=approaches,
                                                   movements=min_movements)


# --- PHASES (DEFAULT DESIGN) ---
min_phase_1: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[min_movement_3_in_1_out_lane_0, min_movement_3_in_1_out_lane_1,
               min_movement_3_in_2_out_lane_0, min_movement_3_in_4_out_lane_1]
)

min_phase_2: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[min_movement_4_in_1_out_lane_1,
               min_movement_4_in_2_out_lane_0, min_movement_4_in_2_out_lane_1]
)

min_phase_3: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[min_movement_2_in_1_out_lane_0, min_movement_2_in_4_out_lane_0, min_movement_2_in_4_out_lane_1,
               min_movement_4_in_2_out_lane_0, min_movement_4_in_2_out_lane_1]
)


min_signal_plan: SignalPlan = [min_phase_1, min_phase_2, min_phase_3]

# --- AVG MOVEMENTS ---

avg_movement_2_in_1_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_2_in_1_out["avg"],
    average_flow=flow_2_in_1_out["avg"],
)

avg_movement_2_in_4_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_2_in_4_out["avg"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

avg_movement_2_in_4_out_lane_1 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_2_in_4_out["avg"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

avg_movement_3_in_1_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_3_in_1_out["avg"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

avg_movement_3_in_1_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_3_in_1_out["avg"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

avg_movement_3_in_2_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_3_in_2_out["avg"],
    average_flow=flow_3_in_2_out["avg"],
)

avg_movement_3_in_4_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_3_in_4_out["avg"],
    average_flow=flow_3_in_4_out["avg"],
)

avg_movement_4_in_1_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_4_in_1_out["avg"],
    average_flow=flow_4_in_1_out["avg"],
)

avg_movement_4_in_2_out_lane_0 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_4_in_2_out["avg"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)

avg_movement_4_in_2_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_4_in_2_out["avg"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)


avg_movements: List[Movement] = [avg_movement_2_in_1_out_lane_0, avg_movement_2_in_4_out_lane_0,
                                 avg_movement_3_in_1_out_lane_0, avg_movement_3_in_1_out_lane_1, avg_movement_3_in_2_out_lane_0, avg_movement_3_in_4_out_lane_1,
                                 avg_movement_4_in_1_out_lane_1, avg_movement_4_in_2_out_lane_0, avg_movement_4_in_2_out_lane_1]

# --- INTERSECTION ---
avg_flow_intersection: Intersection = Intersection(name="TC9",
                                                   approaches=approaches,
                                                   movements=avg_movements)


# --- PHASES (DEFAULT DESIGN) ---
avg_phase_1: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[avg_movement_3_in_1_out_lane_0, avg_movement_3_in_1_out_lane_1,
               avg_movement_3_in_2_out_lane_0, avg_movement_3_in_4_out_lane_1]
)

avg_phase_2: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[avg_movement_4_in_1_out_lane_1,
               avg_movement_4_in_2_out_lane_0, avg_movement_4_in_2_out_lane_1]
)

avg_phase_3: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[avg_movement_2_in_1_out_lane_0, avg_movement_2_in_4_out_lane_0, avg_movement_2_in_4_out_lane_1,
               avg_movement_4_in_2_out_lane_0, avg_movement_4_in_2_out_lane_1]
)


avg_signal_plan: SignalPlan = [avg_phase_1, avg_phase_2, avg_phase_3]


# --- MAX MOVEMENTS ---

max_movement_2_in_1_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_2_in_1_out["max"],
    average_flow=flow_2_in_1_out["avg"],
)

max_movement_2_in_4_out_lane_0 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_2_in_4_out["max"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

max_movement_2_in_4_out_lane_1 = Movement(
    from_approach=approach_2_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_2_in_4_out["max"] / 2,
    average_flow=flow_2_in_4_out["avg"] / 2,
)

max_movement_3_in_1_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_3_in_1_out["max"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

max_movement_3_in_1_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_3_in_1_out["max"] / 2,
    average_flow=flow_3_in_1_out["avg"] / 2,
)

max_movement_3_in_2_out_lane_0 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0, 1],
    expected_flow=flow_3_in_2_out["max"],
    average_flow=flow_3_in_2_out["avg"],
)

max_movement_3_in_4_out_lane_1 = Movement(
    from_approach=approach_3_in,
    to_approach=approach_4_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_3_in_4_out["max"],
    average_flow=flow_3_in_4_out["avg"],
)

max_movement_4_in_1_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_1_out,
    lane_index=1,
    toLanes=[0, 1],
    expected_flow=flow_4_in_1_out["max"],
    average_flow=flow_4_in_1_out["avg"],
)

max_movement_4_in_2_out_lane_0 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=0,
    toLanes=[0],
    expected_flow=flow_4_in_2_out["max"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)

max_movement_4_in_2_out_lane_1 = Movement(
    from_approach=approach_4_in,
    to_approach=approach_2_out,
    lane_index=1,
    toLanes=[1],
    expected_flow=flow_4_in_2_out["max"] / 2,
    average_flow=flow_4_in_2_out["avg"] / 2,
)


max_movements: List[Movement] = [max_movement_2_in_1_out_lane_0, max_movement_2_in_4_out_lane_0,
                                 max_movement_3_in_1_out_lane_0, max_movement_3_in_1_out_lane_1, max_movement_3_in_2_out_lane_0, max_movement_3_in_4_out_lane_1,
                                 max_movement_4_in_1_out_lane_1, max_movement_4_in_2_out_lane_0, max_movement_4_in_2_out_lane_1]

# --- INTERSECTION ---
max_flow_intersection: Intersection = Intersection(name="TC9",
                                                   approaches=approaches,
                                                   movements=max_movements)


# --- PHASES (DEFAULT DESIGN) ---
max_phase_1: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[max_movement_3_in_1_out_lane_0, max_movement_3_in_1_out_lane_1,
               max_movement_3_in_2_out_lane_0, max_movement_3_in_4_out_lane_1]
)

max_phase_2: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[max_movement_4_in_1_out_lane_1,
               max_movement_4_in_2_out_lane_0, max_movement_4_in_2_out_lane_1]
)

max_phase_3: SignalPhase = SignalPhase(
    green=None,
    amber=None,
    all_red=None,
    start=None,
    duration=None,
    movements=[max_movement_2_in_1_out_lane_0, max_movement_2_in_4_out_lane_0, max_movement_2_in_4_out_lane_1,
               max_movement_4_in_2_out_lane_0, max_movement_4_in_2_out_lane_1]
)


max_signal_plan: SignalPlan = [max_phase_1, max_phase_2, max_phase_3]


# HOURLY VERSION
# Hourly flow lists (veh/h)
# Hourly flow lists (veh/h)
hours_2_in_1_out = [
    workbook['21'][f'AC{r}'].value for r in range(68, 82)
    if workbook['21'][f'AC{r}'].value is not None
]

hours_2_in_4_out = [
    workbook['24'][f'AC{r}'].value for r in range(68, 82)
    if workbook['24'][f'AC{r}'].value is not None
]

hours_3_in_1_out = [
    workbook['31'][f'AC{r}'].value for r in range(68, 82)
    if workbook['31'][f'AC{r}'].value is not None
]

hours_3_in_2_out = [
    workbook['32'][f'AC{r}'].value for r in range(68, 82)
    if workbook['32'][f'AC{r}'].value is not None
]

hours_3_in_4_out = [
    workbook['34'][f'AC{r}'].value for r in range(68, 82)
    if workbook['34'][f'AC{r}'].value is not None
]

hours_4_in_1_out = [
    workbook['41'][f'AC{r}'].value for r in range(68, 82)
    if workbook['41'][f'AC{r}'].value is not None
]

hours_4_in_2_out = [
    workbook['42'][f'AC{r}'].value for r in range(68, 82)
    if workbook['42'][f'AC{r}'].value is not None
]


intersection_hourly = []

for hour in range(14):

    # HOURLY MOVEMENTS (updated to match former layout)

    m_2_1_0 = Movement(
        from_approach=approach_2_in,
        to_approach=approach_1_out,
        lane_index=0,
        toLanes=[0, 1],
        expected_flow=hours_2_in_1_out[hour],
        average_flow=flow_2_in_1_out["avg"]
    )

    m_2_4_0 = Movement(
        from_approach=approach_2_in,
        to_approach=approach_4_out,
        lane_index=0,
        toLanes=[0],
        expected_flow=hours_2_in_4_out[hour] / 2,
        average_flow=flow_2_in_4_out["avg"] / 2
    )

    m_2_4_1 = Movement(
        from_approach=approach_2_in,
        to_approach=approach_4_out,
        lane_index=1,
        toLanes=[1],
        expected_flow=hours_2_in_4_out[hour] / 2,
        average_flow=flow_2_in_4_out["avg"] / 2,
    )

    m_3_1_0 = Movement(
        from_approach=approach_3_in,
        to_approach=approach_1_out,
        lane_index=0,
        toLanes=[0],
        expected_flow=hours_3_in_1_out[hour] / 2,
        average_flow=flow_3_in_1_out["avg"] / 2
    )

    m_3_1_1 = Movement(
        from_approach=approach_3_in,
        to_approach=approach_1_out,
        lane_index=1,
        toLanes=[1],
        expected_flow=hours_3_in_1_out[hour] / 2,
        average_flow=flow_3_in_1_out["avg"] / 2
    )

    m_3_2_0 = Movement(
        from_approach=approach_3_in,
        to_approach=approach_2_out,
        lane_index=0,
        toLanes=[0, 1],
        expected_flow=hours_3_in_2_out[hour],
        average_flow=flow_3_in_2_out["avg"]
    )

    m_3_4_1 = Movement(
        from_approach=approach_3_in,
        to_approach=approach_4_out,
        lane_index=1,
        toLanes=[0, 1],
        expected_flow=hours_3_in_4_out[hour],
        average_flow=flow_3_in_4_out["avg"]
    )

    m_4_1_1 = Movement(
        from_approach=approach_4_in,
        to_approach=approach_1_out,
        lane_index=1,
        toLanes=[0, 1],
        expected_flow=hours_4_in_1_out[hour],
        average_flow=flow_4_in_1_out["avg"]
    )

    m_4_2_0 = Movement(
        from_approach=approach_4_in,
        to_approach=approach_2_out,
        lane_index=0,
        toLanes=[0],
        expected_flow=hours_4_in_2_out[hour] / 2,
        average_flow=flow_4_in_2_out["avg"] / 2
    )

    m_4_2_1 = Movement(
        from_approach=approach_4_in,
        to_approach=approach_2_out,
        lane_index=1,
        toLanes=[1],
        expected_flow=hours_4_in_2_out[hour] / 2,
        average_flow=flow_4_in_2_out["avg"] / 2
    )

    movements_hour = [
        m_2_1_0,
        m_2_4_0, m_2_4_1,
        m_3_1_0, m_3_1_1,
        m_3_2_0,
        m_3_4_1,
        m_4_1_1,
        m_4_2_0, m_4_2_1
    ]

    intersection_hour = Intersection(
        name=f"TC9_hour_{hour+1}",
        approaches=approaches,
        movements=movements_hour
    )

    intersection_hourly.append(intersection_hour)

if __name__ == "__main__":
    pass
