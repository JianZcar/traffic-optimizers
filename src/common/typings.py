from dataclasses import dataclass
from typing import Callable, List, Tuple


@dataclass
class IntersectionParams:
    saturation_flows: List[float]  # veh/hour per phase
    lambda_rates: List[float]      # mean arrivals (veh/min)
    reaction_time: float           # driver reaction (s)
    road_widths: List[float]       # approach width per phase (m)
    vehicle_speed: float           # vehicle speed (m/s)
    deceleration_rate: float       # comfortable deceleration (m/s^2)
    vehicle_length: float          # average vehicle length (m)


@dataclass
class PhaseConfig:
    green: float
    amber: float
    all_red: float


TrafficConfiguration = List[PhaseConfig]
Population = List[TrafficConfiguration]
FitnessFunc = Callable[[TrafficConfiguration], int]

PopulateFunc = Callable[[], Population]
SelectionFunc = Callable[[Population, FitnessFunc],
                         Tuple[TrafficConfiguration, TrafficConfiguration]]
CrossoverFunc = Callable[[TrafficConfiguration, TrafficConfiguration],
                         Tuple[TrafficConfiguration, TrafficConfiguration, TrafficConfiguration]]
MutationFunc = Callable[[TrafficConfiguration], TrafficConfiguration]
