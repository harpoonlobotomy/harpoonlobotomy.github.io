# CLI version
import re
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python parse_blocks.py input.txt [output.json]")
    sys.exit(1)

input_path = sys.argv[1]
output_path = sys.argv[2] if len(sys.argv) > 2 else None

def parse_attr(tag_line):
    return dict(re.findall(r'(\w+:\w+|\w+)="([^"]+)"', tag_line))

def extract_blocks_from_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        lines = f.read().replace('\r\n', '\n').split('\n')

    blocks = []
    current_type = None
    current_block = []
    node_location = {"X": None, "Y": None}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            if current_type and current_block:
                blocks.append((current_type, current_block))
            current_type = stripped.strip("<!-> ").strip()
            current_block = []
        elif current_type:
            if stripped:  # skip blank lines
                current_block.append(stripped)
            elif "<d3p1:x>" in line:
                node_location["X"] = float(re.sub(r"<.*?>", "", line).strip())
            elif "<d3p1:y>" in line:
                node_location["Y"] = float(re.sub(r"<.*?>", "", line).strip())



    if current_type and current_block:
        blocks.append((current_type, current_block))

    return blocks

def parse_blocks(blocks):
    nodes = {}
    connectors = {}
    connections = {}
    nodeconnection = {}

    for block_type, lines in blocks:
        if block_type == "Node":
            if len(lines) == 1 and '<Node z:Ref=' in lines[0]:
                continue  # Skip one-line z:Ref nodes

            node_id = None
            node_name = None
            full_type = None
            node_type = None
            m_inputs_id = None
            m_inputs_size = None
            m_outputs_id = None
            m_outputs_size = None

            for line in lines:
                if "<Node" in line and "z:Id=" in line:
                    attrs = parse_attr(line)
                    node_id = attrs.get("z:Id")
                    full_type = attrs.get("i:type", "")
                    node_type = full_type.split(":")[-1] if ":" in full_type else full_type

                elif "<Name" in line and "z:Id" in line and node_name is None:
                    node_name = re.sub(r"<.*?>", "", line).strip()

                elif "<m_Inputs" in line:
                    attrs = parse_attr(line)
                    m_inputs_id = attrs.get("z:Id")
                    m_inputs_size = attrs.get("z:Size")

                elif "<m_Outputs" in line:
                    attrs = parse_attr(line)
                    m_outputs_id = attrs.get("z:Id")
                    m_outputs_size = attrs.get("z:Size")

            if node_id:
                if node_id not in nodes:
                    nodes[node_id] = {
                        "Node_Id": node_id,
                        "Node_Name": node_name or "",
                        "Node_Type": node_type or "",
                    #    "isColor": "",
                        "m_Inputs": {
                            "Id": int(m_inputs_id) if m_inputs_id else None,
                            "Size": int(m_inputs_size) if m_inputs_size else None
                        },
                        "m_Outputs": {
                            "Id": int(m_outputs_id) if m_outputs_id else None,
                            "Size": int(m_outputs_size) if m_outputs_size else None
                        }
                    }
                else:
                    if node_name and not nodes[node_id].get("Node_Name"):
                        nodes[node_id]["Node_Name"] = node_name

        elif block_type in {"m_Inputs", "m_Outputs"}:
            mode = block_type
            current_parent = None
            connectors_in_group = []

            i = 0
            while i < len(lines):
                line = lines[i]

                if f"<{mode}" in line and "z:Id" in line:
                    attrs = parse_attr(line)
                    current_parent = {
                        "z:Id": attrs.get("z:Id"),
                        "z:Size": int(attrs.get("z:Size", "0"))
                    }
                    connectors_in_group = []

                if "<NodeConnector" in line:
                    attrs = parse_attr(line)
                    socket_id = attrs.get("z:Id") or attrs.get("z:Ref")
                    conn_type = "z:Id" if "z:Id" in attrs else "z:Ref"
                    conn_name = None
                    node_ref = None
                    enum = None

                    # Only read inside this NodeConnector block
                    j = i + 1
                    while j < len(lines) and "<NodeConnector" not in lines[j]:
                        lookahead = lines[j]
                        if "<Name" in lookahead:
                            conn_name = re.sub(r"<.*?>", "", lookahead).strip()
                        elif "<Node" in lookahead and ("z:Ref" in lookahead or "z:Id" in lookahead):
                            ref_attrs = parse_attr(lookahead)
                            node_ref = ref_attrs.get("z:Ref") or ref_attrs.get("z:Id")
                        j += 1

                    connectors_in_group.append({
                        "Socket_Id": socket_id,
                        "Conn_Type": conn_type,
                        "Conn_Name": conn_name or "",
                        "Node": node_ref#,
                        #"Enum": enum
                    })

                    i = j - 1  # Advance past this block

                i += 1

            if current_parent:
                group_id = current_parent["z:Id"]
                for node_id, node in nodes.items():
                    group = node.get(mode)
                    if group and str(group.get("Id")) == group_id:
                        group["Connectors"] = connectors_in_group
                        break

        elif block_type == "m_Connections":
            current_conn = {}

            for i, line in enumerate(lines):
                if "<NodeConnection" in line:
                    attrs = parse_attr(line)
                    current_conn = {"z:Id": attrs.get("z:Id")}



                elif "<From" in line:
                    from_attrs = parse_attr(line)
                    if "z:Id" in from_attrs:
                        current_conn["From_Socket"] = from_attrs.get("z:Id")
                        current_conn["From_Conn_Type"] = "z:Id"
                    elif "z:Ref" in from_attrs:
                        current_conn["From_Socket"] = from_attrs.get("z:Ref")
                        current_conn["From_Conn_Type"] = "z:Ref"

                    # Optional: extract From_Socket_Name if present
                    for j in range(i + 1, min(i + 6, len(lines))):
                        if "<Name" in lines[j]:
                            current_conn["From_Socket_Name"] = re.sub(r"<.*?>", "", lines[j]).strip()
                            break

                elif "<To" in line:
                    to_attrs = parse_attr(line)
                    if "z:Id" in to_attrs:
                        current_conn["To_Socket"] = to_attrs.get("z:Id")
                        current_conn["To_Conn_Type"] = "z:Id"
                    elif "z:Ref" in to_attrs:
                        current_conn["To_Socket"] = to_attrs.get("z:Ref")
                        current_conn["To_Conn_Type"] = "z:Ref"

                    # Optional: extract To_Socket_Name if present
                    for j in range(i + 1, min(i + 6, len(lines))):
                        if "<Name" in lines[j]:
                            current_conn["To_Socket_Name"] = re.sub(r"<.*?>", "", lines[j]).strip()
                            break

                if "</NodeConnection>" in line and current_conn.get("z:Id"):
                    connections[current_conn["z:Id"]] = current_conn
                    current_conn = {}

        elif block_type == "NodeConnection":
            enum_value = None
            target_socket_id = None
            is_color = False
            component_mask_node_id = None  # store the z:Id of the ComponentMaskNode if we find one
            component_lines = {}

            for i, line in enumerate(lines):
                if "<Enabled>" in line and i > 0:
                    prev_line = lines[i - 1].strip()
                    if "<From" in prev_line or "<To" in prev_line:
                        attrs = parse_attr(prev_line)
                        target_socket_id = attrs.get("z:Id") or attrs.get("z:Ref")

                elif "<d2p1:m_EnumMember>" in line:
                    match = re.search(r">([^<]+)<", line)
                    if match:
                        enum_value = match.group(1)

                elif "<d2p1:IsColor>" in line:
                    match = re.search(r"<d2p1:IsColor>(true|false)</d2p1:IsColor>", line, re.IGNORECASE)
                    if match and match.group(1).lower() == "true":
                        is_color = True

                elif "<Node" in line and "ComponentMaskNode" in line:
                    attrs = parse_attr(line)
                    component_mask_node_id = attrs.get("z:Id")  # store the node ID for later

                elif "<d2p1:Component1>" in line:
                    component_lines["X"] = line.strip().split(">")[1].split("<")[0]
                elif "<d2p1:Component2>" in line:
                    component_lines["Y"] = line.strip().split(">")[1].split("<")[0]
                elif "<d2p1:Component3>" in line:
                    component_lines["Z"] = line.strip().split(">")[1].split("<")[0]
                elif "<d2p1:Component4>" in line:
                    component_lines["W"] = line.strip().split(">")[1].split("<")[0]

            # Patch connector info
            if target_socket_id:
                for node in nodes.values():
                    for group_key in ["m_Inputs", "m_Outputs"]:
                        conns = node.get(group_key, {}).get("Connectors", [])
                        for conn in conns:
                            if conn.get("Socket_Id") == target_socket_id:
                                if enum_value:
                                    conn["Enum"] = enum_value
                                node["IsColor"] = is_color
                                break

            # Patch ComponentMaskNode type if we found one
            if component_mask_node_id and component_mask_node_id in nodes:
                for key, val in component_lines.items():
                    if val and val.lower() != "none":
                        nodes[component_mask_node_id]["Node_Type"] = f"ComponentMaskNode_{key}"
                        break  # only first non-None



    return {
        "Nodes": nodes,
        "NodeConnectors": connectors,
        "NodeConnection": nodeconnection,
        "Connections": connections
    }

def patch_node_locations(blocks, nodes):
    for block_type, lines in blocks:
        if block_type != "Node":
            continue

        node_id = None
        location_x = None
        location_y = None

        for line in lines:
            if "<Node" in line and "z:Id=" in line:
                attrs = parse_attr(line)
                node_id = attrs.get("z:Id")

            elif ":x>" in line:
                try:
                    location_x = float(re.sub(r"<.*?>", "", line).strip())
                except ValueError:
                    pass
            elif ":y>" in line:
                try:
                    location_y = float(re.sub(r"<.*?>", "", line).strip())
                except ValueError:
                    pass

        if node_id and node_id in nodes and location_x is not None and location_y is not None:
            nodes[node_id]["Location"] = {
                "x": location_x,
                "y": location_y
            }


def patch_missing_connector_names(parsed):
    """
    Fills in missing Conn_Name fields in node connectors by looking up connection info.
    """
    nodes = parsed["Nodes"]
    connections = parsed["Connections"]
    nodeconnectors = parsed["NodeConnectors"]

    # Build map of Socket_Id → name from connections
    socket_name_map = {}
    for conn in connections.values():
        from_id = conn.get("From_Socket")
        to_id = conn.get("To_Socket")
        from_name = conn.get("From_Socket_Name", "").strip()
        to_name = conn.get("To_Socket_Name", "").strip()

        if from_id and from_name:
            socket_name_map[from_id] = from_name
        if to_id and to_name:
            socket_name_map[to_id] = to_name

    # Patch missing Conn_Name entries in m_Inputs and m_Outputs
    for node in nodes.values():
        for io_key in ["m_Inputs", "m_Outputs"]:
            group = node.get(io_key, {})
            conns = group.get("Connectors", [])
            for conn in conns:
                if not conn.get("Conn_Name") and conn.get("Socket_Id") in socket_name_map:
                    conn["Conn_Name"] = socket_name_map[conn["Socket_Id"]]

    return parsed



# === Main execution ===
if __name__ == "__main__":
    # Step 1: Load and parse the raw block-structured text input
    raw_blocks = extract_blocks_from_file(input_path)

    # Step 2: Parse nodes, connectors, and connections
    structured = parse_blocks(raw_blocks)

    # Step 3: Patch in Location data from duplicate or noisy Node blocks
    patch_node_locations(raw_blocks, structured["Nodes"])

    # Step 4: Patch in missing Conn_Names from the m_Connections block
    structured = patch_missing_connector_names(structured)

    # Step 5: Export final structured JSON
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=2)
        print(f"Wrote structured JSON to: {output_path}")
    else:
        print(json.dumps(structured, indent=2))
