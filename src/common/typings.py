import math
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional, Dict


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
    Fully identified by lane mapping.
    """
    from_approach: "Approach"
    to_approach: "Approach"
    movement_type: Optional[str] = None
    num_lanes: int = 1
    average_flow: float = 100  # veh/h
    saturation_flow: Optional[float] = None
    road_width: float = 3.2
    reaction_time: float = 1.0
    vehicle_speed: float = 13.9
    deceleration_rate: float = 4.5
    vehicle_length: float = 5

    # ✅ New! Lane mapping stored directly
    lane_map: Dict[int, int] = field(default_factory=dict)
    # Example: {0: 0} meaning fromLane 0 connects to toLane 0

    def __post_init__(self):
        # Compute λ = veh/s
        self.lambda_rate = self.average_flow / 3600.0

        # Auto classify turn if missing
        if self.movement_type is None:
            self.movement_type = self._classify_turn()

    def _classify_turn(self) -> str:
        """Determine movement type based on approach angles."""
        from_angle = self.from_approach.angle
        to_angle = self.to_approach.angle

        diff = math.degrees((to_angle - from_angle + math.pi) %
                            (2 * math.pi) - math.pi)

        if abs(diff) < 30:
            return "straight"
        elif 30 <= diff < 150:
            return "left"
        elif -150 < diff <= -30:
            return "right"
        return "u-turn"


@dataclass
class SignalPhase:
    """
    Computed configuration for a traffic signal phase.
    Each phase represents a movement from one approach to another,
    with timing and SUMO-compatible state information.
    """
    green: float
    amber: float
    all_red: float
    start: float
    from_approach: str
    to_approach: str
    state: str
    duration: float
    link_index: Optional[int] = None
    movements: List["Movement"] = field(default_factory=list)


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
    intersection_type: str = "T"
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
