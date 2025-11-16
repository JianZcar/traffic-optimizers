import math
from dataclasses import dataclass, field
from typing import Callable, List, Set, Tuple, Optional, Dict


@dataclass
class Approach:
    """
    Represents a single approach (entry/exit point) of the intersection.
    Saturation flow is stored here (per lane), not in the Movement class.
    """
    name: str
    x: float
    y: float
    edge_id: str
    num_lanes: int = 1
    speed: float = 13.9

    # Webster typical value per lane (veh/h)
    saturation_flow_per_lane: float = 1850.0

    # Computed properties
    angle: float = field(init=False)
    saturation_flow_total: float = field(init=False)

    def __post_init__(self):
        # Direction INTO the junction
        self.angle = math.atan2(-self.y, -self.x)

        # Total saturation flow = per lane × number of lanes
        self.saturation_flow_total = self.saturation_flow_per_lane * self.num_lanes


@dataclass
class Movement:
    """
    Represents a single allowed movement from one approach to another
    for a specific inbound lane. Saturation flow is now handled at the
    Approach level, so each Movement only contains demand and lane mapping.
    """
    from_approach: "Approach"
    to_approach: "Approach"
    lane_index: int  # <-- THIS MOVEMENT USES ONE SPECIFIC LANE

    movement_type: Optional[str] = None
    average_flow: float = 100  # veh/h

    # computed fields
    lambda_rate: float = field(init=False)  # veh/s
    dir: Optional[str] = None  # L / R / S / U (auto from movement_type)

    # lane mapping for outgoing connection
    toLanes: List[int] = field(default_factory=list)

    # geometric + behavioral (unchanged)
    road_width: float = 3.2
    reaction_time: float = 1.0
    vehicle_speed: float = 13.9
    deceleration_rate: float = 4.5
    vehicle_length: float = 5

    def __post_init__(self):
        # λ = veh/min
        self.lambda_rate = round(self.average_flow / 60.0, 2)

        # Auto-classify turn type
        if self.movement_type is None:
            self.movement_type = self._classify_turn()

        # Direction shorthand (L/R/S/U)
        self.dir = self.movement_type[0].upper()

    def _classify_turn(self) -> str:
        """Determine movement type based on approach angles."""
        from_angle = self.from_approach.angle
        to_angle = self.to_approach.angle

        # Normalize difference to [-180, 180]
        diff = math.degrees((to_angle - from_angle + math.pi) %
                            (2 * math.pi) - math.pi)

        if abs(diff) < 30 or abs(diff) > 150:
            return "straight"
        elif 30 <= diff < 150:
            return "right"
        elif -150 < diff <= -30:
            return "left"
        return "u-turn"


@dataclass
class SignalPhase:
    """
    Computed configuration for a traffic signal phase.
    Each phase represents a movement from one approach to another,
    with timing.
    """
    green: Optional[float] = None
    amber: Optional[float] = None
    all_red: Optional[float] = None
    start: Optional[float] = None
    duration: Optional[float] = None
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
    position: Tuple[float, float] = (0.0, 0.0)
    radius: float = 30.0

    def __post_init__(self):
        # Assign lanes immediately upon creation
        # self._assign_lanes_to_movements() - for dynamic assignment (manual now)
        pass

    # -----------------------------
    # Internal lane mapping logic
    # -----------------------------
    def _assign_lanes_to_movements(self):
        """
        Assign (fromLane, toLane, dir) for each movement based on
        approach lane counts and movement type.

        - Left turns → inner lanes
        - Right turns → outer lanes
        - Straight → middle lanes
        - South/East approaches → reverse lane order
        - Multiple movements can share the same lane
        """
        for mv in self.movements:
            from_app = mv.from_approach
            to_app = mv.to_approach

            num_from = from_app.num_lanes
            num_to = to_app.num_lanes

            # -----------------------
            # Assign fromLane(s)
            # -----------------------
            if mv.movement_type == "left":
                from_candidates = list(range(num_from))
            elif mv.movement_type == "right":
                from_candidates = list(reversed(range(num_from)))
            else:
                mid = num_from // 2
                from_candidates = []
                for offset in range(num_from):
                    for cand in (mid - offset, mid + offset):
                        if 0 <= cand < num_from and cand not in from_candidates:
                            from_candidates.append(cand)

            reverse = from_app.y < to_app.y or from_app.x > to_app.x
            if reverse:
                from_candidates = list(reversed(from_candidates))

            mv.fromLanes = from_candidates[:mv.num_lanes]

            # -----------------------
            # Assign toLane(s)
            # -----------------------
            if mv.movement_type == "left":
                to_candidates = list(range(num_to))
            elif mv.movement_type == "right":
                to_candidates = list(reversed(range(num_to)))
            else:
                mid = num_to // 2
                to_candidates = []
                for offset in range(num_to):
                    for cand in (mid - offset, mid + offset):
                        if 0 <= cand < num_to and cand not in to_candidates:
                            to_candidates.append(cand)

            if reverse:
                to_candidates = list(reversed(to_candidates))

            mv.toLanes = to_candidates[:mv.num_lanes]

            # -----------------------
            # Assign direction shorthand
            # -----------------------
            mv.dir = mv.movement_type[0].upper()  # L / R / S / U

        print(
            f"[{self.name}] Lane mapping completed for {len(self.movements)} movements.")


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
