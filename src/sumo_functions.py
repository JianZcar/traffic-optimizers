import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List, Optional
from custom_typings import SignalPhase
from custom_typings import Intersection
from custom_typings import SignalPlan


def prettify_xml(elem: ET.Element) -> str:
    rough_string = ET.tostring(elem, 'utf-8')
    return minidom.parseString(rough_string).toprettyxml(indent="  ")


# ---------------- Nodes ----------------
def generate_nodes_xml(intersection: Intersection, output_path: Path):
    """
    Generate nodes.xml with a central traffic light node (J0)
    and peripheral approach nodes.
    """
    root = ET.Element("nodes")

    # Central node (junction)
    ET.SubElement(root, "node", {
        "id": "J0",
        "x": str(intersection.position[0]),
        "y": str(intersection.position[1]),
        "type": "traffic_light"
    })

    # One node per approach
    for app in intersection.approaches:
        ET.SubElement(root, "node", {
            "id": f"{app.name}_node",
            "x": str(app.x),
            "y": str(app.y),
            "type": "priority"
        })

    output_path.write_text(prettify_xml(root), encoding="utf-8")


# ---------------- Edges ----------------
def generate_edges_xml(intersection: Intersection, output_path: Path):
    """
    Generate edges.xml defining incoming and outgoing edges.
    Each approach gets a pair of edges linked to J0.
    """
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

    output_path.write_text(prettify_xml(root), encoding="utf-8")


# ---------------- Connections ----------------
def generate_connections_xml(intersection: Intersection, output_path: Path):
    """
    Generate connections.xml under the new lane-based Movement model.
    Each Movement corresponds to exactly ONE inbound lane (lane_index).

    Therefore:
    - fromLane = mv.lane_index
    - toLane loops over mv.toLanes
    """
    root = ET.Element("connections")

    for mv in intersection.movements:

        if mv.toLanes is None or len(mv.toLanes) == 0:
            raise ValueError(
                f"Movement {mv.from_approach.edge_id}->{mv.to_approach.edge_id} "
                f"has empty toLanes list."
            )

        # FROM lane is always the movement's single lane_index
        f = mv.lane_index

        # Loop through ALL outgoing lanes
        for t in mv.toLanes:
            ET.SubElement(root, "connection", {
                "from": mv.from_approach.edge_id,
                "to": mv.to_approach.edge_id,
                "fromLane": str(f),
                "toLane": str(t),
                "dir": mv.dir,
            })

    output_path.write_text(prettify_xml(root), encoding="utf-8")


# ---------------- Routes ----------------
def generate_routes_xml(intersection: Intersection, output_path: Path):
    """
    Generate routes.xml including vehicle type and traffic flows.
    Each Movement corresponds to one inbound lane, so flow IDs must be unique.
    We encode the lane index in the flow id.
    """
    root = ET.Element("routes")

    # Default vehicle type
    ET.SubElement(root, "vType", {
        "id": "car",
        "accel": "2.5",
        "decel": "4.5",
        "length": "5",
        "maxSpeed": "13.89",
        # "sigma": "0.5"   # randomness for driver imperfection
    })

    # Flows for each lane-based movement
    for mv in intersection.movements:
        flow_id = (
            f"flow_{mv.from_approach.edge_id}_to_"
            f"{mv.to_approach.edge_id}_lane{mv.lane_index}"
        )

        ET.SubElement(root, "flow", {
            "id": flow_id,
            "from": mv.from_approach.edge_id,
            "to": mv.to_approach.edge_id,
            "begin": "0",
            "end": "3600",
            "number": str(int(mv.average_flow))
        })

    output_path.write_text(prettify_xml(root), encoding="utf-8")


# ---------------- SUMO Config ----------------
def create_sumo_config(
    routes_path: Path,
    net_path: Path,
    tls_path: Optional[Path] = None,
    output_path: Path = Path("simulation.sumocfg"),
    gui_settings_path: Optional[Path] = None,
    begin: int = 0,
    end: int = 3600,
    use_random: bool = True,
    seed: Optional[int] = None,
):
    """
    Creates a SUMO configuration (.sumocfg) file.
    Supports optional traffic light file (tls_path) and GUI settings file.
    Adds random number settings for stochastic simulation.
    """
    root = ET.Element("configuration")

    # ---- Input files ----
    input_elem = ET.SubElement(root, "input")
    ET.SubElement(input_elem, "net-file", {"value": str(net_path)})
    ET.SubElement(input_elem, "route-files", {"value": str(routes_path)})

    # ---- Additional files (TLS, detectors, etc.) ----
    if tls_path:
        additional_elem = ET.SubElement(root, "additional")
        ET.SubElement(additional_elem, "additional-files",
                      {"value": str(tls_path)})

    # ---- GUI defaults (zoom, speed, etc.) ----
    gui_elem = ET.SubElement(root, "gui_only")
    ET.SubElement(gui_elem, "start", {"value": "true"})
    ET.SubElement(gui_elem, "delay", {"value": "60"})

    # ---- GUI settings ----
    if gui_settings_path:
        ET.SubElement(root, "gui-settings-file",
                      {"value": str(gui_settings_path)})

    # ---- Time settings ----
    time_elem = ET.SubElement(root, "time")
    ET.SubElement(time_elem, "begin", {"value": str(begin)})
    ET.SubElement(time_elem, "end", {"value": str(end)})

    # ---- Random number settings ----
    # rnd_elem = ET.SubElement(root, "random_number")
    # if seed is not None:
    #     ET.SubElement(rnd_elem, "seed", {"value": str(seed)})
    # else:
    #     ET.SubElement(rnd_elem, "random", {
    #                   "value": "true" if use_random else "false"})

    # ---- Report settings ----
    report_elem = ET.SubElement(root, "report")
    ET.SubElement(report_elem, "verbose", {"value": "true"})
    ET.SubElement(report_elem, "no-step-log", {"value": "true"})

    # ---- Save XML ----
    xml_string = prettify_xml(root)
    output_path.write_text(xml_string, encoding="utf-8")


# ---------------- Traffic Lights ----------------
def generate_traffic_lights_xml(
    signal_plan: SignalPlan,
    net_path: Path,
    output_path: Path,
    tl_id: str = "J0"
):
    """
    Generate a SUMO traffic light configuration (tls file) from an intersection
    and a lane-based signal plan, using linkIndex ordering from network.net.xml.

    Each incoming-lane -> outgoing-lanes movement gets its own light.
    """
    import xml.etree.ElementTree as ET

    root = ET.Element("tlLogic", attrib={
        "id": tl_id,
        "type": "static",
        "programID": "1",
        "offset": "0"
    })

    # --- Parse network.net.xml for linkIndex ordering ---
    tree = ET.parse(net_path)
    net_root = tree.getroot()
    link_connections = []

    for conn in net_root.findall("connection"):
        if conn.attrib.get("tl") != tl_id:
            continue
        link_connections.append({
            "from_edge": conn.attrib["from"],
            "from_lane": int(conn.attrib["fromLane"]),
            "to_edge": conn.attrib["to"],
            "to_lane": int(conn.attrib["toLane"]),
            "link_index": int(conn.attrib["linkIndex"]),
        })

    # Sort connections by linkIndex
    link_connections.sort(key=lambda x: x["link_index"])

    # --- Build a set of active movements per phase for quick lookup ---
    phase_active_sets: List[set] = []
    for phase in signal_plan:
        active_set = set()
        for mv in phase.movements:
            for to_lane in mv.toLanes:
                active_set.add((mv.from_approach.edge_id, mv.lane_index,
                                mv.to_approach.edge_id, to_lane))
        phase_active_sets.append(active_set)

    # --- Helper: build state string in linkIndex order ---
    def build_green_state(phase_idx: int) -> str:
        active_set = phase_active_sets[phase_idx]
        state = []
        for conn in link_connections:
            key = (conn["from_edge"], conn["from_lane"],
                   conn["to_edge"], conn["to_lane"])
            if key in active_set:
                state.append("G")
            else:
                state.append("r")
        return "".join(state)

    def build_amber_state(phase_idx: int) -> str:
        active_set = phase_active_sets[phase_idx]
        state = []

        for conn in link_connections:
            key = (conn["from_edge"], conn["from_lane"],
                   conn["to_edge"], conn["to_lane"])

            if key in active_set:
                if key in phase_active_sets[(phase_idx + 1) % len(phase_active_sets)]:
                    state.append("G")
                else:
                    state.append("y")
            else:
                state.append("r")
        return "".join(state)

    def build_red_state(phase_idx: int) -> str:
        active_set = phase_active_sets[phase_idx]
        state = []
        for conn in link_connections:
            key = (conn["from_edge"], conn["from_lane"],
                   conn["to_edge"], conn["to_lane"])
            if key in active_set and key in phase_active_sets[(phase_idx + 1) % len(phase_active_sets)]:
                state.append("G")
            else:
                state.append("r")

        return "".join(state)

    # --- Build TLS phases ---
    for i, phase in enumerate(signal_plan):
        # GREEN
        ET.SubElement(root, "phase", attrib={
            "duration": str(phase.green or 0),
            "state": build_green_state(i)
        })

        # AMBER
        if phase.amber and phase.amber > 0:
            ET.SubElement(root, "phase", attrib={
                "duration": str(phase.amber),
                "state": build_amber_state(i)
            })

        # ALL-RED
        if phase.all_red and phase.all_red > 0:
            ET.SubElement(root, "phase", attrib={
                "duration": str(phase.all_red),
                "state": build_red_state(i)
            })

    # Write XML
    output_path.write_text(prettify_xml(root), encoding="utf-8")


def generate_viewsettings_xml(output_path: Path, scheme="real world"):
    root = ET.Element("viewsettings")
    ET.SubElement(root, "scheme", {"name": scheme})
    xml_str = ET.tostring(root, encoding="unicode")
    output_path.write_text(xml_str)
