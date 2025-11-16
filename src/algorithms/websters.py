from typing import List, Tuple
from collections import defaultdict
from custom_typings import SignalPhase, SignalPlan, Movement
from math import ceil
import numpy as np


# -------------------------------------------------
# WEBSTER'S METHOD
# -------------------------------------------------
def websters_method(L: int, Y: float) -> int:
    """Compute optimal cycle length. Handles Y ≥ 1 safely."""
    if Y >= 1.0:
        Y = 0.999  # prevent division by zero
    return int(ceil((1.5 * L + 5) / (1 - Y)))


def compute_amber_time(tr: float, v: float, a: float) -> int:
    """Compute the amber (yellow) interval."""
    return ceil(tr + (v / (2 * a)))


def compute_all_red_time(W: float, L: float, v: float) -> int:
    """Compute the all-red clearance interval."""
    return ceil((W + L) / v)


def compute_green_time(y: float, Y: float, C: float, L: int) -> int:
    """Equation for allocating green time in Webster's method."""
    return ceil((y * (C - L)) / Y)


def compute_phase_safety_times(phase: SignalPhase) -> Tuple[int, int]:
    """
    Compute amber + all-red clearance for each phase using
    the WORST-CASE movement inside that phase.

    Hard failure:
        - missing required attributes
        - invalid numeric values
        - missing clearance distance
    """

    amber_candidates = []
    all_red_candidates = []

    for mv in phase.movements:

        required = [
            "reaction_time",
            "vehicle_speed",
            "deceleration_rate",
            "vehicle_length",
            "road_width"
        ]

        for attr in required:
            if not hasattr(mv, attr):
                raise ValueError(
                    f"Movement {mv} missing required attribute '{attr}'. "
                    f"Cannot compute safety times."
                )

        tr = mv.reaction_time
        v = mv.vehicle_speed
        a = mv.deceleration_rate
        veh_len = mv.vehicle_length
        W = mv.road_width

        # Validation
        if tr < 0 or v <= 0 or a <= 0 or veh_len <= 0 or W <= 0:
            raise ValueError(
                f"Invalid movement values detected in {mv}. "
                f"All must be > 0 (except tr)."
            )

        amber_t = compute_amber_time(tr=tr, v=v, a=a)
        all_red_t = compute_all_red_time(W=W, L=veh_len, v=v)

        amber_candidates.append(amber_t)
        all_red_candidates.append(all_red_t)

    if not amber_candidates:
        raise RuntimeError(
            "No movements found in phase; cannot compute safety times.")

    return max(amber_candidates), max(all_red_candidates)


def compute_green_times(flow_ratios, Y, amber_times, all_red_times):
    """
    Allocate green times using Webster's method.
    Halts if inputs are invalid.
    """

    if len(flow_ratios) != len(amber_times) or len(flow_ratios) != len(all_red_times):
        raise ValueError(
            "Mismatch in list lengths for flow ratios vs. safety times.")

    if Y <= 0:
        raise ValueError(
            "Invalid total critical ratio Y <= 0. Cannot compute greens.")

    # lost time per phase
    L = sum(a + r for a, r in zip(amber_times, all_red_times))

    # cycle length
    C = websters_method(L=L, Y=Y)

    if C <= L:
        raise ValueError(
            f"Invalid cycle length C={C}. Must be > total lost time L={L}."
        )

    greens = []
    for y in flow_ratios:
        if y <= 0:
            raise ValueError(f"Invalid flow ratio y={y}. Must be > 0.")
        g = compute_green_time(y=y, Y=Y, C=C, L=L)
        greens.append(g)

    return greens, C, L


# -------------------------------------------------
# POISSON'S ARRIVAL PROCESS
# -------------------------------------------------
def simulate_poisson_arrival_rate(lambda_rate: float) -> int:
    """Simulate arrivals using Poisson distribution; always ≥ 1."""
    arrivals = np.random.poisson(lam=lambda_rate)
    return max(1, arrivals)


def compute_critical_ratios_with_poissons(phases: List[SignalPhase]):
    """
    Compute critical flow ratios for each phase using Poisson flows.
    Halts if a phase stays oversaturated (Y >= 1) after 20 attempts.
    """
    per_phase_Y = []
    Y_total = 0.0

    for ph in phases:

        attempt = 0
        while True:
            attempt += 1

            lane_flows = defaultdict(float)
            lane_saturations = {}

            # Step 1: compute per-lane Poisson flows and saturation
            for mv in ph.movements:
                lane_key = f"{mv.from_approach.edge_id}_lane_{mv.lane_index}"

                # Poisson arrivals per minute → convert to veh/h
                poisson_flow = simulate_poisson_arrival_rate(
                    mv.lambda_rate) * 60

                lane_flows[lane_key] += poisson_flow

                sat_per_lane = getattr(
                    mv.from_approach,
                    "saturation_flow_per_lane",
                    mv.from_approach.saturation_flow_total / mv.from_approach.num_lanes
                )
                lane_saturations[lane_key] = sat_per_lane

            # Step 2: compute critical ratio
            sum_flows = sum(lane_flows.values())
            sum_sats = sum(lane_saturations.values())

            phase_Y = sum_flows / sum_sats if sum_sats > 0 else 0.0

            # Stop if Y < 1 (valid)
            if phase_Y < 1:
                break

            # Too many attempts → intersection is oversaturated
            if attempt >= 20:
                print("\nERROR: Intersection is oversaturated.")
                print(f"Phase could not reach Y < 1 after {attempt} attempts.")
                print(f"Last computed Y = {phase_Y:.4f}")
                raise RuntimeError(
                    "Oversaturated intersection — aborting simulation.")

        per_phase_Y.append(phase_Y)
        Y_total += phase_Y

    return per_phase_Y, Y_total


# -------------------------------------------------
# OVERALL SIGNAL CONFIG PROCESS
# -------------------------------------------------
def compute_signal_config_with_poisson_and_websters(
    signal_plan: SignalPlan
) -> SignalPlan:

    # 1. Poisson flows
    poisson_flow_ratios, Y = compute_critical_ratios_with_poissons(
        signal_plan)

    # 2. Amber + All-Red
    amber_times = []
    all_red_times = []
    for phase in signal_plan:
        amber_t, ar_t = compute_phase_safety_times(phase)
        amber_times.append(amber_t)
        all_red_times.append(ar_t)

    # 3. Greens from Webster
    green_times, C, L = compute_green_times(
        poisson_flow_ratios, Y, amber_times, all_red_times)

    # 4. Assign timings to plan
    start = 0
    for i, phase in enumerate(signal_plan):
        phase.green = green_times[i]
        phase.amber = amber_times[i]
        phase.all_red = all_red_times[i]
        phase.start = start
        phase.duration = phase.green + phase.amber + phase.all_red

        start += phase.duration

    return signal_plan
