## Exports full nodegroups, as nodegroups - no need for ungrouping first. If output file already exists, will append if key is unique.

## Written for Blender 4.3
# - harpoonlobotomy

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
        short_name = node_type.removeprefix("ShaderNode")

        count = type_counters[short_name]
        if count == 0:
            new_name = short_name
        else:
            new_name = f"{short_name}.{count:03d}"
        type_counters[short_name] += 1


        if old_name == "Group Input":
            new_name = "GroupInput"
        if old_name == "Group Output":
            new_name = "GroupOutput"

        node["name"] = new_name
        name_map[old_name] = new_name

    # Now update links to use the new names
    for link in group_data["links"]:
        print(link)
        link[0] = name_map.get(link[0], link[0])  # from_node
        link[2] = name_map.get(link[2], link[2])  # to_node

    return name_map

def nodegroup_to_json(nodegroup_node):

    nodegroup = nodegroup_node.node_tree

    data = {}

    data["color"] = getattr(nodegroup, "color_tag", None)

    # Sockets
    # Find the Group Input/Output nodes
    group_in_node = next((n for n in nodegroup.nodes if n.type == 'GROUP_INPUT'), None)
    group_out_node = next((n for n in nodegroup.nodes if n.type == 'GROUP_OUTPUT'), None)

    sockets = {"inputs": {}, "outputs": {}}
    input_sock_type = {}
    input_sock_val = {}
    output_sock_type = {}
    output_sock_val = {}

    # Input sockets come from the Group Input node's outputs
    if group_in_node:
        for i, sock in enumerate(group_in_node.outputs):
            if sock.name == "":
                continue
            else:
                sockets["inputs"][str(i)] = sock.name
                input_sock_type[str(i)] = sock.bl_idname


    # Output sockets come from the Group Output node's inputs
    if group_out_node:
        for i, sock in enumerate(group_out_node.inputs):
            if sock.name == "":
                continue
            else:
                sockets["outputs"][str(i)] = sock.name
                output_sock_type[str(i)] = sock.bl_idname


    data["sockets"] = sockets
    data["input_types"] = input_sock_type
    data["input_value"] = input_sock_val
    data["output_types"] = output_sock_type

    # Nodes
    nodes_data = []
    for node in nodegroup.nodes:
        print(node.name)
        if node.name == "Group Input":
            #input_sockets = {s for s in node.inputs}
            for i, sock in enumerate(node.outputs):
                if sock.name != "":
                    i_str = str(i)
                    print(f"index: {i} // socket: {sock} // val: {sock.default_value}")
                    val = sock.default_value
                    if isinstance(val, (int, float)):
                        input_sock_val[i_str] = float(val)

                   # val = sock.default_value
                    # = val
            #continue
#        elif node.name == "Group Output":
#            continue
        node_entry = {
            "name": node.name,
            "type": node.bl_idname,
            "location": [round(node.location.x / 10) * 10, round(node.location.y / 10) * 10],
        }

        if hasattr(node, "operation"):
            node_entry["operation"] = node.operation
        if hasattr(node, "blend_type"):
            node_entry["blend_type"] = node.blend_type
        if hasattr(node, "data_type"):
            node_entry["data_type"] = node.data_type

        # Default values
        default_vals = {}
        for inp in node.inputs:
            if not inp.is_linked and hasattr(inp, "default_value"):
                # Only grab if it's not connected and supports a default
                if "Rotation" not in inp.identifier:

                    val = inp.default_value
                    # Convert to list for sequences like vectors/colors/rotations
                    if hasattr(val, "__iter__") and not isinstance(val, str):
                        default_vals[inp.identifier] = list(val)
                    if isinstance(val, (int, float)):
                        default_vals[inp.identifier] = float(val)

        if default_vals:
            node_entry["default_values"] = default_vals

        nodes_data.append(node_entry)
    data["nodes"] = nodes_data

    # Links
    links_data = []
    for link in nodegroup.links:
        from_node_name = link.from_node.name if link.from_node else "GroupInput"
        to_node_name = link.to_node.name if link.to_node else "GroupOutput"
        print(from_node_name)
        if from_node_name == "Group Input":
            from_socket_id = link.from_socket.name
        else:
            from_socket_id = link.from_socket.identifier

        if to_node_name == "Group Output":
            to_socket_id = link.to_socket.name
        else:
            to_socket_id = link.to_socket.identifier

        links_data.append([
            from_node_name,
            from_socket_id,
            to_node_name,
            to_socket_id
        ])

    data["links"] = links_data

    return data

def export_frame_groups_custom():
    obj = bpy.context.object
    mat = obj.active_material
    if not mat:
        print("No active object or material found.")
        return

    nodes = mat.node_tree.nodes
    #for node in nodes:
        #print(node.type)
    links = obj.active_material.node_tree.links

    nodegroups = [n for n in nodes if n.type == 'GROUP']
    new_output = {}
    output_path = r"F:\Python_Scripts\Template_Generator\nodegroup_blueprints_new.json"


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
    for nodegroup in nodegroups:
        group_data = nodegroup_to_json(nodegroup)
        nodetemp = nodegroup.node_tree
        temp_name = nodetemp.name
        if "." in temp_name:
            group_name, _ = temp_name.split(".", 1)
        else:
            group_name = temp_name
        normalize_node_names_in_group(group_data)

        group_data["nodes"] = [
            node for node in group_data["nodes"]
            if node["name"] not in ("GroupInput", "GroupOutput")
        ]

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
