from collections import defaultdict
import xml.etree.ElementTree as ET
from typing import List, Tuple, Set
from .typings import Intersection, SignalPlan
import tempfile
from pathlib import Path
import subprocess

from pprint import pprint

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
from common.typings import Approach, Movement
from common.utils import allocate_lanes_per_approach

# ---------------- Nodes ----------------


def build_nodes_xml(intersection: Intersection, output_path: Path) -> None:
    print(f'Intersection radius: {intersection.radius}')
    print(f'Output path: {output_path}')
    root = ET.Element("nodes")
    # Junction node
    ET.SubElement(root, "node", {
        "id": "J0",
        "x": str(intersection.position[0]),
        "y": str(intersection.position[1]),
        "type": "traffic_light",
        "radius": str(intersection.radius)
    })
    for app in intersection.approaches:
        ET.SubElement(root, "node", {
            "id": f"{app.name}_node",
            "x": str(app.x),
            "y": str(app.y),
            "type": "priority"
        })
    ET.ElementTree(root).write(
        output_path, encoding="utf-8", xml_declaration=True)


# ---------------- Edges ----------------
def build_edges_xml(intersection: Intersection, output_path: Path) -> None:
    root = ET.Element("edges")
    for app in intersection.approaches:
        edge_attrs = {
            "id": app.edge_id,
            "numLanes": str(app.num_lanes),
            "speed": str(app.speed)
        }
        if app.edge_id.endswith("_in"):
            edge_attrs.update({"from": f"{app.name}_node", "to": "J0"})
        else:
            edge_attrs.update({"from": "J0", "to": f"{app.name}_node"})
        ET.SubElement(root, "edge", edge_attrs)
    ET.ElementTree(root).write(
        output_path, encoding="utf-8", xml_declaration=True)


def get_to_lane(mv: "Movement", num_to: int, used_lanes: Dict[str, Set[int]]) -> int:
    """
    Dynamic assignment for outgoing lane considering approach orientation.

    - Left → leftmost (or reversed if south/west)
    - Right → rightmost (or reversed if south/west)
    - Straight → middle lane
    """
    if num_to <= 0:
        return 0

    to_edge = mv.to_approach.edge_id
    used = used_lanes.setdefault(to_edge, set())

    # Determine approach orientation
    dx = mv.from_approach.x - mv.to_approach.x
    dy = mv.from_approach.y - mv.to_approach.y
    reverse = dy < 0 or dx > 0  # south or east approaches reverse indexing

    # Compute candidate lanes
    if mv.movement_type == "left":
        candidates = list(range(num_to))
    elif mv.movement_type == "right":
        candidates = list(reversed(range(num_to)))
    else:  # straight
        mid = num_to // 2
        candidates = []
        for offset in range(num_to):
            for cand in (mid - offset, mid + offset):
                if 0 <= cand < num_to and cand not in candidates:
                    candidates.append(cand)

    if reverse:
        candidates = list(reversed(candidates))

    # pick first unused lane
    for i in candidates:
        if i not in used:
            used.add(i)
            return i

    # fallback
    for i in range(num_to):
        if i not in used:
            used.add(i)
            return i
    return 0


# ---------------- Connections ----------------


def build_connections_xml(intersection, output_path: Path, tl_id: str = "J0") -> None:
    """
    Build SUMO <connections> XML for T/X intersections.
    Lane mapping (fromLane → toLane) is written into Movement.lane_map here.
    """
    root = ET.Element("connections")
    preview_lines = []
    link_index = 0  # 🔹 We'll increment this manually

    by_from = {}
    for mv in intersection.movements:
        by_from.setdefault(mv.from_approach.edge_id, []).append(mv)

    used_lanes: Dict[str, Set[int]] = defaultdict(set)

    for from_edge_id, mvs in by_from.items():
        approach_num_lanes = mvs[0].from_approach.num_lanes
        reverse = mvs[0].from_approach.y < 0 or mvs[0].from_approach.x > 0

        allocations = allocate_lanes_per_approach(
            approach_edge=mvs[0].from_approach.edge_id,
            movements=mvs,
            approach_num_lanes=approach_num_lanes,
            used_lanes=used_lanes,
            reverse=reverse
        )

        for mv, from_lanes in allocations:
            num_to_lanes = mv.to_approach.num_lanes
            for from_lane in from_lanes:
                to_lane = get_to_lane(mv, num_to_lanes, used_lanes)
                mv.lane_map[from_lane] = to_lane
                used_lanes[mv.to_approach.edge_id].add(to_lane)

                # ✅ Assign a linkIndex and attach to Movement
                mv.link_index = link_index

                # ✅ Write XML using assigned linkIndex
                ET.SubElement(
                    root, "connection",
                    {
                        "from": mv.from_approach.edge_id,
                        "to": mv.to_approach.edge_id,
                        "fromLane": str(from_lane),
                        "toLane": str(to_lane),
                        "tl": tl_id,
                        "linkIndex": str(link_index),  # 🔹 Added here
                    }
                )
                link_index += 1

                preview_lines.append(
                    f"{mv.from_approach.edge_id}_{from_lane} → "
                    f"{mv.to_approach.edge_id}_{to_lane} "
                    f"({mv.movement_type}, linkIndex={mv.link_index})"
                )

    print("\n=== Final Lane Map Preview ===")
    for line in preview_lines:
        print(line)
    print("====================================\n")

    ET.ElementTree(root).write(
        output_path, encoding="utf-8", xml_declaration=True)


# ---------------- Routes ----------------
def build_routes_xml(intersection: Intersection, output_path: Path) -> None:
    """
    Generate routes.xml with flows for each movement.
    Uses the average_flow attribute of each Movement.
    """
    root = ET.Element("routes")
    ET.SubElement(root, "vType", {
        "id": "car",
        "accel": "2.5",
        "decel": "4.5",
        "maxSpeed": "13.89",
        "length": "5"
    })

    for mv in intersection.movements:
        if mv.average_flow is None:
            raise ValueError(
                f"Movement {mv.from_approach.edge_id} -> {mv.to_approach.edge_id} has no average_flow defined")

        ET.SubElement(root, "flow", {
            "id": f"flow_{mv.from_approach.edge_id}_to_{mv.to_approach.edge_id}",
            "from": mv.from_approach.edge_id,
            "to": mv.to_approach.edge_id,
            "begin": "0",
            "end": "3600",
            "number": str(int(mv.average_flow))
        })

    ET.ElementTree(root).write(
        output_path, encoding="utf-8", xml_declaration=True)

# ---------------- Netconvert ----------------


def build_sumo_net(nodes_file: Path, edges_file: Path, connections_file: Path, output_net: Path) -> None:
    print(
        f"PATHS: {nodes_file}, {edges_file}, {connections_file}, {output_net}")
    try:
        subprocess.run([
            "netconvert",
            "-n", str(nodes_file),
            "-e", str(edges_file),
            "-x", str(connections_file),
            "-o", str(output_net)
        ], check=True)
        print(f"SUMO network generated: {output_net}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"netconvert failed: {e}") from e


# ---------------- Convenience Wrapper ----------------
def build_intersection_sumo(intersection: Intersection, output_dir: Path):
    """
    Build all XMLs for SUMO network and generate net.xml.
    Flows are derived from Movement.average_flow.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_file = output_dir / "nodes.xml"
    edges_file = output_dir / "edges.xml"
    connections_file = output_dir / "connections.xml"
    routes_file = output_dir / "routes.xml"
    net_file = output_dir / "network.net.xml"

    build_nodes_xml(intersection, nodes_file)
    build_edges_xml(intersection, edges_file)
    build_connections_xml(intersection, connections_file)
    build_routes_xml(intersection, routes_file)
    build_sumo_net(nodes_file, edges_file, connections_file, net_file)


# -------------------- Generate tlLogic --------------------
def generate_tl_logic(
    connections_path: Path,
    output_path: Path,
    signal_plan: SignalPlan,
    tl_id: str = "J0",
) -> None:
    """
    Generate a tlLogic XML for SUMO based on a SignalPlan.
    Supports multi-lane movements by using lane_map to look up
    corresponding linkIndex values from connections.xml.
    """

    print(f"[DEBUG] Parsing connections file: {connections_path}")
    tree = ET.parse(connections_path)
    root = tree.getroot()

    # Collect all connections with tl + linkIndex attributes
    connections = [
        conn for conn in root.findall("connection")
        if "tl" in conn.attrib and "linkIndex" in conn.attrib
    ]
    total_links = len(connections)
    print(f"[DEBUG] Total tl-controlled connections found: {total_links}")
    print("[DEBUG] Sample connections (first 5):")
    for conn in connections[:5]:
        print("  ", conn.attrib)

    # Helper: find linkIndex from lane_map and approaches
    def find_link_index(from_edge: str, to_edge: str, from_lane: int, to_lane: int):
        for conn in connections:
            if (conn.attrib.get("from") == from_edge and
                conn.attrib.get("to") == to_edge and
                int(conn.attrib.get("fromLane", -1)) == from_lane and
                    int(conn.attrib.get("toLane", -1)) == to_lane):
                return int(conn.attrib["linkIndex"])
        return None

    # --- Build tlLogic phases ---
    phases_xml = []

    for phase_idx, phase in enumerate(signal_plan):
        print(
            f"\n[DEBUG] Processing phase {phase_idx}: {phase.from_approach}->{phase.to_approach}")
        state = ["r"] * total_links

        # GREEN PHASE
        for mov_idx, movement in enumerate(phase.movements):
            print(f"  [DEBUG] Movement {mov_idx}: {movement.from_approach.name}->{movement.to_approach.name}, "
                  f"lane_map={movement.lane_map}")

            for from_lane, to_lane in movement.lane_map.items():
                link_index = find_link_index(
                    movement.from_approach.edge_id,
                    movement.to_approach.edge_id,
                    from_lane,
                    to_lane
                )

                if link_index is None:
                    print(f"  [WARN] No linkIndex found for {movement.from_approach.edge_id}->{movement.to_approach.edge_id} "
                          f"(lane {from_lane}->{to_lane}) — skipping")
                    continue

                if link_index >= total_links:
                    print(
                        f"  [ERROR] linkIndex {link_index} out of range (total_links={total_links})")
                    continue

                print(f"    [DEBUG] Setting GREEN at linkIndex={link_index}")
                state[link_index] = "G"

        phases_xml.append(
            f'''      <phase duration="{phase.green}" state="{"".join(state)}"/>'''
        )

        # AMBER PHASE
        state = ["r"] * total_links
        for movement in phase.movements:
            for from_lane, to_lane in movement.lane_map.items():
                link_index = find_link_index(
                    movement.from_approach.edge_id,
                    movement.to_approach.edge_id,
                    from_lane,
                    to_lane
                )
                if link_index is not None and link_index < total_links:
                    state[link_index] = "y"

        phases_xml.append(
            f'''      <phase duration="{phase.amber}" state="{"".join(state)}"/>'''
        )

        # ALL-RED PHASE
        phases_xml.append(
            f'''      <phase duration="{phase.all_red}" state="{"r" * total_links}"/>'''
        )

    # --- Final wrap ---
    output_xml = f'''<additional>
  <tlLogics version="1.16">
    <tlLogic id="{tl_id}" type="static" programID="1" offset="0">
{"\n".join(phases_xml)}
    </tlLogic>
  </tlLogics>
</additional>'''

    with open(output_path, "w") as f:
        f.write(output_xml)

    print(f"\n[DEBUG] tlLogic XML successfully written to {output_path}")

# -------------------- Saturation Flow Scenario --------------------


def saturation_flow_scenario() -> Tuple[Path, str]:
    """
    Create a simple routes.xml to test saturation flow rates.
    """
    routes = ET.Element("routes")

    ET.SubElement(routes, "vType", {
        "id": "car",
        "accel": "2.5",
        "decel": "4.5",
        "maxSpeed": "13.89",  # ~50 km/h
        "length": "5"
    })

    ET.SubElement(routes, "flow", {
        "id": "flow_E_to_W",
        "type": "car",
        "begin": "0",
        "end": "3600",
        "number": "3000",
        "from": "E_in",
        "to": "W_out"
    })

    tmp_dir = tempfile.mkdtemp()
    file_path = Path(tmp_dir) / "routes.xml"

    tree = ET.ElementTree(routes)
    tree.write(str(file_path), encoding="utf-8", xml_declaration=True)

    return file_path, tmp_dir
