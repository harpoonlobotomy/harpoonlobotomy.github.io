# F:\BG3 Extract PAKs\PAKs\Textures\Generated\Public\Shared\Assets\Textures\Procedural_Masks\Resources\

## Exports "nodegroups" in the form of frame-bounded node setups with links.
##-- Label reroute nodes as 'input_0/Name' - it will recognise the input_0 for linking, indexing, but use the /Name for the output file.
## Run script `F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\BLENDER_really_nodegroup_from_frame_json_file.py` to deploy nodegroups

import bpy
import os
import json

def serialize_value(val, indent=0):
    ind = '  ' * indent
    if isinstance(val, dict):
        lines = []
        lines.append("{")
        n = len(val)
        for i, (k, v) in enumerate(val.items()):
            comma = "," if i < n - 1 else ""
            lines.append(f'{ind}    "{k}": {serialize_value(v, indent + 1)}{comma}')
        lines.append(ind + "}")
        return "\n".join(lines)
    elif isinstance(val, (list, tuple)):
        if len(val) <= 4 and all(isinstance(x, (int, float)) for x in val):
            return "[" + ", ".join(str(round(x)) if isinstance(x, float) else str(x) for x in val) + "]"
        lines = ["["]
        n = len(val)
        for i, item in enumerate(val):
            comma = "," if i < n - 1 else ""
            if isinstance(item, (list, tuple)) and len(item) <= 4 and all(isinstance(x, (int, float, str)) for x in item):
                item_str = "[" + ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in item) + "]"
                lines.append(f'{ind}    {item_str}{comma}')
            else:
                lines.append(f'{ind}    {serialize_value(item, indent + 1)}{comma}')
        lines.append(ind + "]")
        return "\n".join(lines)

    elif isinstance(val, str):
        return f'"{val}"'
    elif isinstance(val, bool):
        print(f"{val} 123456")
        return "true" if val else "false"
    elif val is None:
        return "null"
    else:
        return str(val)

from collections import defaultdict

def normalize_node_names_in_group(group_data):
    """Ensure node names in this group start from 'Type', 'Type.001', etc. locally."""
    type_counters = defaultdict(int)
    name_map = {}

    for node in group_data["nodes"]:
        old_name = node["name"]
        node_type = node["type"]

        # Derive readable base name from the node type
        short_name = node_type.removeprefix("ShaderNode").removeprefix("CompositorNode").removeprefix("GeometryNode")

        count = type_counters[short_name]
        if count == 0:
            new_name = short_name
        else:
            new_name = f"{short_name}.{count:03d}"
        type_counters[short_name] += 1

        node["name"] = new_name
        name_map[old_name] = new_name

    # Now update links to use the new names
    for link in group_data["links"]:
        link[0] = name_map.get(link[0], link[0])  # from_node
        link[2] = name_map.get(link[2], link[2])  # to_node

    return name_map

def remap_reroute_names(group_data, reroute_map):
    """
    Replace reroute node names AND reroute socket names in nodes and links
    with 'GroupInput' or 'GroupOutput' and consistent socket labels like 'input_0' or 'output_0'.
    This happens *only in the output data*, NOT in Blender node names.
    """
    print(f"Remapping reroute nodes for group (before remap): {[node['name'] for node in group_data['nodes']]}")

    # Remap node names
    for node in group_data["nodes"]:
        if node["name"] in reroute_map:
            print(f"Remapping node '{node['name']}' to '{reroute_map[node['name']][0]}'")
            node["name"] = reroute_map[node["name"]][0]

    # Remap link endpoints *and* socket names if from/to node is a reroute
    for i, (from_node, from_socket, to_node, to_socket) in enumerate(group_data["links"]):

        if from_node in reroute_map:
            group_node_type, full_label = reroute_map[from_node]
            print(f"Remapping link from_node '{from_node}' to '{group_node_type}' with socket '{from_socket}' to label '{full_label}'")
            from_node = group_node_type
            # Split the label for display name
            if "/" in full_label:
                _, display_name = full_label.split("/", 1)
                from_socket = display_name
                print(f"{from_socket}")
            else:
                from_socket = full_label

        if to_node in reroute_map:
            group_node_type, full_label = reroute_map[to_node]
            print(f"Remapping link to_node '{to_node}' to '{group_node_type}' with socket '{to_socket}' to label '{full_label}'")
            to_node = group_node_type
            if "/" in full_label:
                _, display_name = full_label.split("/", 1)
                to_socket = display_name
            else:
                to_socket = full_label

        group_data["links"][i] = [from_node, from_socket, to_node, to_socket]


    print(f"Remapping reroute nodes for group (after remap): {[node['name'] for node in group_data['nodes']]}")

def export_frame_groups_custom():
    obj = bpy.context.object
    if not obj or not obj.active_material:
        print("No active object or material found.")
        return

    nodes = obj.active_material.node_tree.nodes
    links = obj.active_material.node_tree.links

    frames = [n for n in nodes if n.type == 'FRAME']
    new_output = {}
    output_path = r"F:\Python_Scripts\Blender Scripts\frame_exported_nodegroups_4.json"


    # Step 1: Get existing top-level frame keys
    existing_keys = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
                existing_keys = set(existing_data.keys())
            except json.JSONDecodeError:
                print("[WARN] Existing file is not valid JSON. Starting fresh.")
                existing_data = {}


    print(f"[Info] Existing frame keys in file: {existing_keys}")


 # Step 2: Build new entries
    for frame in frames:
        group_name = frame.label or frame.name

        if group_name in existing_keys:
            saved_data = {}
            existing_entry = existing_data.get(group_name, {})
            if "color" in existing_entry:
                saved_data["color"] = existing_entry["color"]

            if "autohide" in existing_entry:
                saved_data["autohide"] = existing_entry["autohide"]
                print(f"Saved data for {group_name} is: {saved_data}")

        if group_name:
            group_data = {
                "color": "",
                "autohide": False,
                "sockets": {
                    "inputs": {},
                    "outputs": {}
                },
                "nodes": [],
                "links": []
            }

            group_nodes = [n for n in nodes if n.parent == frame]
            node_names = {n.name for n in group_nodes}
            print(f"Group nodes: {sorted(node_names)}")

            # First pass: detect reroutes and classify inputs/outputs
            input_index = 0
            output_index = 0
            reroute_map = {}  # reroute node name → ("GroupInput"/"GroupOutput", socket_label)

            for node in group_nodes:
                if node.type == 'REROUTE':
                    has_input_links = any(link.to_node == node for link in links)
                    has_output_links = any(link.from_node == node for link in links)

                    raw_label = node.label.strip() if node.label else node.name
                    socket_label = raw_label.split("/")[0]  # just for indexing & logic

                    if not has_input_links and has_output_links:
                        idx_str = str(input_index)
                        group_data["sockets"]["inputs"][idx_str] = socket_label
                        reroute_map[node.name] = ("GroupInput", raw_label)  # <-- store full label here!
                        print(f"Detected GroupInput reroute node: {node.name} with label '{raw_label}'")
                        input_index += 1
                    elif has_input_links and not has_output_links:
                        idx_str = str(output_index)
                        group_data["sockets"]["outputs"][idx_str] = socket_label
                        reroute_map[node.name] = ("GroupOutput", raw_label)  # <-- store full label here!
                        print(f"Detected GroupOutput reroute node: {node.name} with label '{raw_label}'")
                        output_index += 1


            # Second pass: add non-reroute nodes (keep all node names intact)
            for node in group_nodes:
                if node.type == 'REROUTE':
                    # Do NOT rename node.name here, keep Blender's unique names
                    continue

                node_info = {
                    "name": node.name,
                    "type": node.bl_idname,
                    "location": [round(node.location.x / 10) * 10, round(node.location.y / 10) * 10],
                }

                if node.bl_idname in {"ShaderNodeMath", "ShaderNodeVectorMath"}:
                    node_info["operation"] = node.operation
                elif node.bl_idname in {"ShaderNodeMix", "ShaderNodeMixRGB"}:
                    node_info["blend_type"] = node.blend_type
                    if hasattr(node, "data_type"):
                        node_info["data_type"] = node.data_type

                default_values = {}
                for sock in node.inputs:
                    if hasattr(sock, "default_value") and not sock.is_linked:
                        try:
                            val = sock.default_value
                            if isinstance(val, (int, float, bool)):
                                safe_val = val
                            elif hasattr(val, "__len__"):  # e.g., Vector, Euler, Color
                                safe_val = tuple(val)
                            else:
                                continue  # Skip things like images or unknown types

                            default_values[sock.identifier] = safe_val
                        except Exception as e:
                            print(f"[WARN] Failed to read default for {node.name}.{sock.identifier}: {e}")

                if default_values:
                    node_info["default_values"] = default_values

                group_data["nodes"].append(node_info)

            # Third pass: export links with reroute names replaced at output time only
            for link in links:
                from_node_name = link.from_node.name
                to_node_name = link.to_node.name
                from_socket = link.from_socket.identifier
                to_socket = link.to_socket.identifier

                # Note: we do NOT replace reroute names here directly,
                # replacement is done after building group_data, in remap function.
                # Just keep original Blender node names here.

    #----------V Removes nodes  with name containing "delete" - name placeholder reroutes this if you need to have sockets present but not linked.


                if (from_node_name in node_names or from_node_name in reroute_map or from_node_name in ("GroupInput", "GroupOutput")) and \
                   (to_node_name in node_names or to_node_name in reroute_map or to_node_name in ("GroupInput", "GroupOutput")):
                    if "delete" in from_node_name.lower() or "delete" in to_node_name.lower():
                        continue
                    else:
                        group_data["links"].append([
                            from_node_name,
                            from_socket,
                            to_node_name,
                            to_socket
                        ])


            if group_name in existing_keys:
                if "color" in saved_data:
                    group_data["color"] = saved_data["color"]
                if "autohide" in saved_data:
              #      group_data["autohide"] = saved_data["autohide"]
                    print(f"[Debug] Restoring autohide for {group_name}: {saved_data['autohide']} ({type(saved_data['autohide'])})")
                    group_data["autohide"] = saved_data["autohide"]

            # Now remap reroute names to GroupInput/GroupOutput for output ONLY
            remap_reroute_names(group_data, reroute_map)

            # Patch socket display names too
            for reroute_name, (node_type, label) in reroute_map.items():
                if "/" in label:
                    idx_label, display_name = label.split("/", 1)
                    if node_type == "GroupInput":
                        idx = idx_label.replace("input_", "")
                        group_data["sockets"]["inputs"][idx] = display_name
                    elif node_type == "GroupOutput":
                        idx = idx_label.replace("output_", "")
                        group_data["sockets"]["outputs"][idx] = display_name

            normalize_node_names_in_group(group_data)

    ##--------- # Remove any input/output sockets with names containing "delete"

            group_data["sockets"]["inputs"] = {
                k: v for k, v in group_data["sockets"]["inputs"].items()
                if "delete" not in v.lower()
            }
            group_data["sockets"]["outputs"] = {
                k: v for k, v in group_data["sockets"]["outputs"].items()
                if "delete" not in v.lower()
            }
            new_output[group_name] = group_data

        print(f"Completed group '{group_name}':")
        print(f"  Inputs sockets: {group_data['sockets']['inputs']}")
        print(f"  Output sockets: {group_data['sockets']['outputs']}")
        print(f"  Nodes count: {len(group_data['nodes'])}")
        print(f"  Links count: {len(group_data['links'])}")

    # Output all groups to file, with commas between, no extra file opening
        # Step 3: Append new entries to the file

    # Load existing content (if any)
    existing_data = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Existing file is not valid JSON. Starting fresh.")


    # Update with new entries (overwriting by group name if duplicated)
    existing_data.update(new_output)

    # Serialize using your custom function
    full_serialized = "{\n"
    items = list(existing_data.items())
    for i, (key, val) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        full_serialized += f'  "{key}": {serialize_value(val, 1)}{comma}\n'
    full_serialized += "}\n"

    # Save to file (overwrite)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_serialized)

    print(f"[Info] Wrote {len(new_output)} new group(s) to JSON at '{output_path}'")

export_frame_groups_custom()
