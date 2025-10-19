import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
from common.typings import Approach, Movement


def attach_link_indices(connections_path: Path, movements: list[Movement]) -> None:
    """
    Attach linkIndex values from connections.xml to Movement objects.
    """
    tree = ET.parse(connections_path)
    root = tree.getroot()

    # Build dictionary: (from, to) -> linkIndex
    link_mapping: dict[tuple[str, str], int] = {}
    for conn in root.findall("connection"):
        if "from" in conn.attrib and "to" in conn.attrib and "linkIndex" in conn.attrib:
            from_edge = conn.attrib["from"]
            to_edge = conn.attrib["to"]
            link_index = int(conn.attrib["linkIndex"])
            link_mapping[(from_edge, to_edge)] = link_index

    # Update Movement objects in-place
    for movement in movements:
        key = (movement.from_approach.edge_id, movement.to_approach.edge_id)
        if key in link_mapping:
            movement.link_index = link_mapping[key]
        else:
            raise ValueError(
                f"No linkIndex found for movement {key} in {connections_path}"
            )


def allocate_lanes_per_approach(
    approach: Approach, movements: List[Movement]
) -> List[Tuple[Movement, List[int]]]:
    """
    Assign from-lanes per movement, using direction rules:
      - left turns → leftmost lanes
      - right turns → rightmost lanes
      - straight → middle lanes
    Ensures fair sharing if oversubscribed.
    """
    total = int(approach.num_lanes)
    used: set[int] = set()
    allocations: List[Tuple[Movement, List[int]]] = []

    if not movements:
        return allocations

    for mv in movements:
        need = min(mv.num_lanes, total)
        lanes: list[int] = []

        if mv.movement_type == "left":
            candidates = range(total)  # 0,1,...
        elif mv.movement_type == "right":
            candidates = reversed(range(total))  # N-1,...
        else:  # straight
            mid = total // 2
            candidates = []
            for offset in range(total):
                for cand in [mid - offset, mid + offset]:
                    if 0 <= cand < total:
                        candidates.append(cand)

        # assign preferred lanes if free
        for i in candidates:
            if i not in used:
                lanes.append(i)
                used.add(i)
            if len(lanes) == need:
                break

        # if not enough, allow sharing (reuse lanes)
        if len(lanes) < need:
            for i in candidates:
                if i not in lanes:
                    lanes.append(i)
                if len(lanes) == need:
                    break

        allocations.append((mv, sorted(lanes)))

    return allocations