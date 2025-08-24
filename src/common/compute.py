from math import ceil
import numpy as np


def compute_amber_time(
    tr: int | float,
    v: int | float,
    a: int | float
) -> int:
    """Compute the amber (yellow) interval

    Args:
        tr (float): driver reaction time (s)
        v (float): vehicle approach speed (m/s)
        a (float): comfortable deceleration rate (m/s²)

    Returns:
        int: amber (yellow) interval
    """
    return ceil(tr + (v / (2 * a)))


def compute_all_red_time(
    W: int | float,
    L: int | float,
    v: int | float
) -> int:
    """Compute the all-red clearance interval

    Args:
        W (int | float): width of the lane approach (m)
        L (int | float): average vehicle length (m)
        v (int | float): approach speed (m/s)

    Returns:
        int: all‑red clearance interval
    """
    return ceil((W + L) / v)


def compute_green_time(
    y: int | float,
    Y: int | float,
    C: int,
    L: int
) -> int:
    return ceil((y * (C - L)) / Y)


def simulate_poisson_arrival_rate(q: float) -> int:
    """
    Return a single Poisson‐distributed random draw representing
    the number of arrivals in one time interval, given mean q.

    Args:
        q: Expected number of arrivals in that interval.
    Returns:
        An integer count of arrivals.
    """
    return max(1, ceil(np.random.poisson(lam=q)))
