from typing import List, Dict, Optional, Tuple
from common.typings import Approach, Movement, Intersection, SignalPlan
from common.intersection_presets import T_INTERSECTION, X_INTERSECTION


def create_approaches(input_data: List[Dict]) -> List[Approach]:
    """
    Generate Approach objects from input data.
    input_data: list of dicts with keys:
        name, x, y, edge_id, num_lanes, lane_length (optional), speed (optional)
    """
    approaches = []
    for entry in input_data:
        approaches.append(
            Approach(
                name=entry["name"],
                x=entry["x"],
                y=entry["y"],
                edge_id=entry["edge_id"],
                num_lanes=entry.get("num_lanes", 1),
                lane_length=entry.get("lane_length", 100),
                speed=entry.get("speed", 13.9)
            )
        )
    return approaches


def create_movements(approaches: List[Approach], allowed_movements: List[dict]) -> List[Movement]:
    """
    Generate Movement objects dynamically from approaches.

    Args:
        approaches: List of Approach objects.
        allowed_movements: List of dicts, each with keys:
            'from_edge', 'to_edge', 'num_lanes', plus optional Movement params.

    Returns:
        List[Movement]: Generated movement objects.
    """
    movements = []
    edge_map = {a.edge_id: a for a in approaches}

    for mv_data in allowed_movements:
        from_edge = mv_data.pop("from_edge")
        to_edge = mv_data.pop("to_edge")
        num_lanes = mv_data.pop("num_lanes", 1)

        movements.append(
            Movement(
                from_approach=edge_map[from_edge],
                to_approach=edge_map[to_edge],
                num_lanes=num_lanes,
                **mv_data
            )
        )
    return movements


def build_intersection(
    name: str,
    approach_data: List[Dict],
    allowed_movements: List[dict],
    position: Tuple[float, float] = (0.0, 0.0),
    radius: float = 30.0,
    signal_plan: Optional[SignalPlan] = None
) -> Intersection:
    """
    Build a complete Intersection object from input data.
    """
    approaches = create_approaches(approach_data)
    movements = create_movements(approaches, allowed_movements)
    return Intersection(
        name=name,
        approaches=approaches,
        movements=movements,
        signal_plan=signal_plan,
        position=position,
        radius=radius
    )


def build_fixed_intersection(kind: str) -> Intersection:
    presets = {
        "T": T_INTERSECTION,
        "X": X_INTERSECTION
    }
    config = presets[kind.upper()]
    return build_intersection(
        name=config["name"],
        approach_data=config["approaches"],
        allowed_movements=config["movements"],
        position=(0, 0),
        radius=1.0
    )
