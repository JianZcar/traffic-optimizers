import math
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional


@dataclass
class Approach:
    """
    Represents a single approach (entry/exit point) of the intersection.
    """
    name: str
    x: float
    y: float
    edge_id: str
    num_lanes: int = 1
    lane_length: float = 100
    speed: float = 13.9
    node_type: str = "priority"  # e.g., 'priority', 'dead_end', 'traffic_light'

    angle: float = field(init=False)  # computed after init

    def __post_init__(self):
        # Precompute the "approach angle" (direction pointing INTO junction)
        # 0 = east, counterclockwise positive
        self.angle = math.atan2(-self.y, -self.x)  # into the junction


@dataclass
class Movement:
    """
    Represents a single allowed movement (from one approach to another).
    Used for defining connections and flow parameters.
    """
    from_approach: "Approach"
    to_approach: "Approach"
    # 'straight', 'left', 'right', 'u-turn'
    movement_type: Optional[str] = None
    num_lanes: int = 1
    average_flow: float = 100             # expected flow (veh/h)
    saturation_flow: Optional[float] = None
    road_width: float = 3.2               # meters per lane
    reaction_time: float = 1.0            # seconds
    vehicle_speed: float = 13.9           # m/s (~50 km/h)
    deceleration_rate: float = 4.5        # m/s^2
    vehicle_length: float = 5             # meters
    link_index: Optional[int] = None      # assigned later from connections.xml
    lambda_rate: Optional[float] = None   # vehicles per second, derived

    def __post_init__(self):
        # Derive lambda_rate from average_flow (veh/h → veh/s)
        if self.lambda_rate is None:
            self.lambda_rate = self.average_flow / 3600.0

        # Auto-compute movement_type if not provided
        if self.movement_type is None:
            self.movement_type = self._classify_turn()

    def _classify_turn(self) -> str:
        """Classify as left, right, straight, or u-turn based on approach angles."""
        from_angle = self.from_approach.angle
        to_angle = self.to_approach.angle

        # Normalize difference to [-180, 180]
        diff = math.degrees((to_angle - from_angle + math.pi) %
                            (2 * math.pi) - math.pi)

        if abs(diff) < 30:
            return "straight"
        elif 30 <= diff < 150:
            return "left"
        elif -150 < diff <= -30:
            return "right"
        else:
            return "u-turn"


@dataclass
class SignalPhase:
    """
    Computed configuration for a traffic signal phase.
    """
    green: float
    amber: float
    all_red: float
    start: float
    movements: List[Movement]            # movements served in this phase
    # SUMO phase state string (e.g., "GrGr")
    state: str
    duration: float                      # Total duration of this phase


# A complete traffic signal plan (set of all phases for the intersection)
SignalPlan = List[SignalPhase]


@dataclass
class Intersection:
    """
    Represents a full intersection, including approaches, movements, and signal plans.
    """
    name: str
    approaches: List[Approach]
    movements: List[Movement]
    # currently assigned signal phases
    signal_plan: Optional[SignalPlan] = None
    position: Tuple[float, float] = (0.0, 0.0)  # optional center coordinates
    radius: float = 30.0  # SUMO junction radius


# A collection of candidate signal plans (the GA population)
SignalPopulation = List[SignalPlan]

# GA type hints
FitnessFunc = Callable[[SignalPlan], float]
PopulateFunc = Callable[[], SignalPopulation]
SelectionFunc = Callable[[SignalPopulation, FitnessFunc],
                         Tuple[SignalPlan, SignalPlan]]
CrossoverFunc = Callable[[SignalPlan, SignalPlan],
                         Tuple[SignalPlan, SignalPlan, SignalPlan]]
MutationFunc = Callable[[SignalPlan], SignalPlan]
