import math
from typing import List, Dict, Literal
from common.typings import Approach, Movement, SignalPhase, SignalPlan
from common.compute import (
    compute_amber_time,
    compute_all_red_time,
    compute_green_time,
    simulate_poisson_arrival_rate
)


def vector(m: Movement):
    dx = m.to_approach.x - m.from_approach.x
    dy = m.to_approach.y - m.from_approach.y
    return dx, dy


def angle_between(v1, v2):
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    mag1 = math.hypot(*v1)
    mag2 = math.hypot(*v2)
    if mag1 == 0 or mag2 == 0:
        return 0
    cos_theta = dot / (mag1 * mag2)
    cos_theta = max(min(cos_theta, 1), -1)  # numerical safety
    return math.acos(cos_theta)


def check_phase_conflict(m1: Movement, m2: Movement, angle_threshold=10):
    """
    Checks if two phases conflict based on their geometric directions.
    """
    # 1. Same from_approach always conflicts
    if m1.from_approach.edge_id == m2.from_approach.edge_id:
        return True

    # 2. Compute vectors
    v1 = vector(m1)
    v2 = vector(m2)

    # 3. Angle between movements in degrees
    theta = math.degrees(angle_between(v1, v2))

    # 4. Conflict if angle is not near 0 or 180 (approx. intersecting)
    if angle_threshold < theta < (180 - angle_threshold):
        return True

    return False


def websters_method(
    L: int,
    Y: float
) -> int:
    """Compute for the Optimal Cycle Length

    Args:
        L (int): Total Lost Time (s)
        Y (float): Total Critical Ratio

    Returns:
        int: Optimal Cycle Length (s)
    """
    return int(math.ceil((1.5 * L + 5) / (1 - Y)))


def compute_signal_config_with_poisson(
    phases: List[Movement],
    mode: Literal['concurrent', 'simultaneous', 'sequential'] = 'sequential'
) -> SignalPlan:
    """
    Compute traffic signal configuration for a given mode using Poisson flow simulation.

    Args:
        phases: List of Movement objects (with link_index attached from connections.xml)
        mode: Mode to compute. Options: 'concurrent', 'simultaneous', 'sequential'

    Returns:
        List of PhaseConfig objects with SUMO state strings.
    """
    n = len(phases)

    # ------------------ 1) Simulate flows and compute flow ratios ------------------
    while True:
        normal_flow_per_hour = [
            simulate_poisson_arrival_rate(p.lambda_rate) for p in phases
        ]
        flow_ratios = [
            q / p.saturation_flow if p.saturation_flow > 0 else 0
            for q, p in zip(normal_flow_per_hour, phases)
        ]
        Y = sum(flow_ratios)
        if Y < 1:
            break

    # ------------------ 2) Compute amber and all-red times ------------------
    amber_times = [compute_amber_time(p.reaction_time, p.vehicle_speed, p.deceleration_rate)
                   for p in phases]
    all_red_times = [compute_all_red_time(p.road_width, p.vehicle_length, p.vehicle_speed)
                     for p in phases]
    L = sum(amber_times + all_red_times)

    # ------------------ 3) Webster cycle length ------------------
    C = websters_method(L=L, Y=Y)

    # ------------------ 4) Compute green times ------------------
    green_times = [compute_green_time(y, Y, C, L) for y in flow_ratios]

    # ------------------ 5) Build conflict matrix ------------------
    conflict_matrix = [[False]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            conflict_matrix[i][j] = (
                i == j) or check_phase_conflict(phases[i], phases[j])

    # ------------------ 6) Compute start times depending on mode ------------------
    start_times = [0]*n

    if mode == 'concurrent':
        start_times = [-1]*n
        for i in sorted(range(n), key=lambda x: -flow_ratios[x]):
            earliest = 0
            for j in range(n):
                if start_times[j] >= 0 and conflict_matrix[i][j]:
                    earliest = max(
                        earliest,
                        start_times[j] + green_times[j] +
                        amber_times[j] + all_red_times[j]
                    )
            start_times[i] = earliest

    elif mode == 'simultaneous':
        unassigned = set(range(n))
        groups = []
        while unassigned:
            idx = unassigned.pop()
            group = [idx]
            remove_set = set()
            for other in unassigned:
                if all(not conflict_matrix[other][g] for g in group):
                    group.append(other)
                    remove_set.add(other)
            unassigned -= remove_set
            groups.append(group)
        current_time = 0
        for group in groups:
            for idx in group:
                start_times[idx] = current_time
            max_group_duration = max(
                green_times[idx] + amber_times[idx] + all_red_times[idx] for idx in group
            )
            current_time += max_group_duration

    elif mode == 'sequential':
        for i in range(1, n):
            start_times[i] = (
                start_times[i-1] +
                green_times[i-1] +
                amber_times[i-1] +
                all_red_times[i-1]
            )

    else:
        raise ValueError(f"Invalid mode: {mode}")

   # ------------------ 7) Build PhaseConfig list ------------------
    tl_config = []
    for i in range(n):
        cfg = SignalPhase(
            green=green_times[i],
            amber=amber_times[i],
            all_red=all_red_times[i],
            start=start_times[i],
            from_approach=phases[i].from_approach.name,
            to_approach=phases[i].to_approach.name,
            state="",  # will be filled below
            duration=green_times[i] + amber_times[i] + all_red_times[i],
            link_index=i,
            movements=[phases[i]]  # traceability
        )
        tl_config.append(cfg)

        # Debug print
        print(f"[DEBUG] PhaseConfig {i}: from={cfg.from_approach}, "
              f"to={cfg.to_approach}, start={cfg.start:.2f}, "
              f"green={cfg.green:.2f}, amber={cfg.amber:.2f}, "
              f"all_red={cfg.all_red:.2f}, duration={cfg.duration:.2f}")

    # ------------------ 8) Build SUMO-compatible states ------------------
    sumo_states = build_sumo_tl_states(tl_config, phases)

    print("\n[DEBUG] SUMO States:")
    for idx, s in enumerate(sumo_states):
        print(f"  State {idx}: {s}")

    # Assign the resulting SUMO state string(s) into each config
    for cfg in tl_config:
        for s in sumo_states:
            if cfg.from_approach == s["from"] and cfg.to_approach == s["to"]:
                cfg.state = s["state"]

    return tl_config


def build_sumo_tl_states(configs: SignalPlan, phases: List[Movement]) -> List[dict]:
    """
    Merge SignalPlan into SUMO-compatible tlLogic states.
    Uses link_index from Movement to build the state string.
    """
    # total number of links = max link_index + 1
    total_links = max(
        p.link_index for p in phases if p.link_index is not None) + 1
    events = []

    # Map configs back to phases (to access link_index)
    cfg_to_phase = {(c.from_approach, c.to_approach): p for c, p in zip(configs, phases)}

    # Collect all start/transition times
    for cfg in configs:
        phase = cfg_to_phase[(cfg.from_approach, cfg.to_approach)]
        li = phase.link_index
        events.extend([
            (cfg.start, li, "G"),
            (cfg.start + cfg.green, li, "y"),
            (cfg.start + cfg.green + cfg.amber, li, "r"),
        ])

    events.sort(key=lambda x: x[0])

    states = []
    state = ["r"] * total_links
    last_t = 0.0

    for t, li, new_char in events:
        if t > last_t:
            states.append({
                "start": last_t,
                "end": t,
                "duration": t - last_t,
                "state": "".join(state),
                "from": phases[li].from_approach.name,
                "to": phases[li].to_approach.name,
            })
        state[li] = new_char
        last_t = t

    return states
