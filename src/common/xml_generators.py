import xml.etree.ElementTree as ET
from .typings import PhaseConfig
import tempfile
from pathlib import Path


def generate_tl_logic(input_path: str, output_path: str, phase_configs: list[PhaseConfig]):
    # Parse the input XML file
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Find all connection elements with tl and linkIndex attributes
    connections = []
    for conn in root.findall('connection'):
        if 'tl' in conn.attrib and 'linkIndex' in conn.attrib:
            connections.append(conn)

    # Group connections by 'from' attribute, preserving order of first occurrence
    groups_order = []
    groups = {}
    for conn in connections:
        from_attr = conn.get('from')
        link_index = int(conn.get('linkIndex'))
        if from_attr not in groups:
            groups_order.append(from_attr)
            groups[from_attr] = []
        groups[from_attr].append(link_index)

    # Validate config-group count match
    if len(groups_order) != len(phase_configs):
        raise ValueError(
            "Number of PhaseConfigs must match number of connection groups")

    # Determine total number of links
    total_links = max([max(indices)
                      for indices in groups.values()]) + 1 if groups else 0

    # Generate phases for each group with its own config
    phases = []
    for from_attr, config in zip(groups_order, phase_configs):
        link_indices = groups[from_attr]

        # Green phase
        state = ['r'] * total_links
        for idx in link_indices:
            state[idx] = 'G'
        phases.append(f'''      <phase duration="{
                      config.green}" state="{"".join(state)}"/>''')

        # Amber phase
        state = ['r'] * total_links
        for idx in link_indices:
            state[idx] = 'y'
        phases.append(f'''      <phase duration="{
                      config.amber}" state="{"".join(state)}"/>''')

        # All-red phase
        phases.append(f'''      <phase duration="{config.all_red}" state="{
                      "".join(["r"] * total_links)}"/>''')

    # Construct and write output XML
    output_xml = f'''<additional>
  <tlLogics version="1.16">
    <tlLogic id="J0" type="static" programID="1" offset="0">
{"\n".join(phases)}
    </tlLogic>
  </tlLogics>
</additional>'''

    with open(output_path, 'w') as f:
        f.write(output_xml)


def saturation_flow_scenario():
    routes = ET.Element("routes")

    ET.SubElement(routes, "vType", {
        "id": "car",
        "accel": "2.5",
        "decel": "4.5",
        "maxSpeed": "13.89",
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
