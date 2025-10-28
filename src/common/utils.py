import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Set
from collections import defaultdict
from common.typings import Approach, Movement


def sync_lane_map_from_xml(connections_path: Path, movements: list[Movement]) -> None:
    """
    Load lane mapping from connections.xml and store into Movement.lane_map.
    Ensures consistency between model + exported XML.
    """
    tree = ET.parse(connections_path)
    root = tree.getroot()

    # Build dictionary grouped by movement (from,to)
    lane_mapping: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)

    for conn in root.findall("connection"):
        from_edge = conn.attrib["from"]
        to_edge = conn.attrib["to"]
        from_lane = int(conn.attrib["fromLane"])
        to_lane = int(conn.attrib["toLane"])
        lane_mapping[(from_edge, to_edge)][from_lane] = to_lane

    # Assign to movement objects
    for mv in movements:
        key = (mv.from_approach.edge_id, mv.to_approach.edge_id)

        if key not in lane_mapping:
            raise ValueError(
                f"No lane connections found for movement {key} in {connections_path}"
            )

        mv.lane_map = lane_mapping[key].copy()

    print(f"✅ Lane mapping synchronized from {connections_path}")


def allocate_lanes_per_approach(
    approach_edge: str,
    movements: List["Movement"],
    approach_num_lanes: int,
    used_lanes: Dict[str, Set[int]],
    reverse: bool = False
) -> List[Tuple["Movement", List[int]]]:
    """
    Dynamic lane allocation per approach for SUMO with orientation awareness.
    Lane 0 = rightmost, lane n-1 = leftmost (from vehicle perspective).
    reverse=True flips the indexing (for approaches from south or west).

    Tracks which lanes are already used in used_lanes dict.
    """
    allocations: List[Tuple["Movement", List[int]]] = []
    total = approach_num_lanes

    def lane_index(i: int) -> int:
        """Convert physical lane index to SUMO lane index, considering reverse."""
        return total - 1 - i if reverse else i

    for mv in movements:
        need = min(mv.num_lanes, total)
        lanes: List[int] = []

        # Left turns → leftmost available
        if mv.movement_type == "left":
            for i in reversed(range(total)):
                idx = lane_index(i)
                if idx not in used_lanes[approach_edge]:
                    lanes.append(idx)
                if len(lanes) == need:
                    break

        # Right turns → rightmost available
        elif mv.movement_type == "right":
            for i in range(total):
                idx = lane_index(i)
                if idx not in used_lanes[approach_edge]:
                    lanes.append(idx)
                if len(lanes) == need:
                    break

        # Straight → middle outward
        else:
            mid = total // 2
            candidates = []
            for offset in range(total):
                for cand in (mid - offset, mid + offset):
                    if 0 <= cand < total and cand not in candidates:
                        candidates.append(cand)
            for i in candidates:
                idx = lane_index(i)
                if idx not in used_lanes[approach_edge]:
                    lanes.append(idx)
                if len(lanes) == need:
                    break

        used_lanes[approach_edge].update(lanes)
        allocations.append((mv, sorted(lanes)))

    return allocations
