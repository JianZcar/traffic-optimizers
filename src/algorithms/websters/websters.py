from math import ceil
from typing import List
from common.typings import PhaseConfig
from common.compute import (
    compute_amber_time,
    compute_all_red_time,
    compute_green_time,
    simulate_poisson_arrival_rate
)


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
    return ceil(1.5 * L + 5) / (1 - Y)


def compute_signal_config_with_poisson(
    saturation_flows: List[float],  # veh/hour per phase
    lambda_rates: List[float],      # mean arrivals (veh/min)
    reaction_time: float,           # driver reaction (s)
    road_widths: List[float],       # approach width per phase (m)
    vehicle_speed: float,           # vehicle speed (m/s)
    deceleration_rate: float,       # comfortable deceleration (m/s^2)
    vehicle_length: float           # average vehicle length (m)
) -> List[PhaseConfig]:
    """
    Returns a list of PhaseConfig tuples (green, amber, red) for each phase.
    If Y >= 1, recomputes with a new Poisson realization until Y < 1.
    """
    while True:
        # 1) Simulate total arrivals per minute using Poisson
        normal_flows_per_minute = [
            simulate_poisson_arrival_rate(q=lam) for lam in lambda_rates]

        # 2) Compute flow ratios
        flow_ratios = [(q * 60) / s if s > 0 else 0 for q,
                       s in zip(normal_flows_per_minute, saturation_flows)]
        Y = sum(flow_ratios)

        if Y < 1:
            break  # Acceptable configuration found

    # 3) Lost time per phase (reaction + max clearance)
    amber_times = []
    all_red_times = []
    for W in road_widths:
        amber_time = compute_amber_time(
            tr=reaction_time, v=vehicle_speed, a=deceleration_rate)
        amber_times.append(amber_time)

        all_red_time = compute_all_red_time(
            W=W, L=vehicle_length, v=vehicle_speed)
        all_red_times.append(all_red_time)

    L = sum(amber_times + all_red_times)

    # 4) Webster cycle length
    C = websters_method(L=L, Y=Y)

    # 5) Allocate green times
    green_times = [compute_green_time(y=y, Y=Y, C=C, L=L) for y in flow_ratios]

    # 6) Build phase configurations
    tl_config = []
    for i in range(len(green_times)):
        tl_config.append(PhaseConfig(
            green=green_times[i],
            amber=amber_times[i],
            all_red=all_red_times[i]
        ))

    return tl_config
