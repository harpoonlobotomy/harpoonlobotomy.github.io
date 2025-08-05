## Only gets native nodes, not nodegroups

#requires nodes to already be present and connected - does not make connections on its own.
#Correctly merges sockets only if they match index and node attributes; prioritises any True over any False.

import bpy
import json
import os


# === Helper functions ===

#--- get existing custom-named nodes in input file to prevent overwrite
def is_generated_key(key, value):
    parts = [value.get("type")]
    if "operation" in value:
        parts.append(value["operation"])
    if "data_type" in value and "blend_type" in value:
        parts.extend([value["data_type"], value["blend_type"]])
    generated = "_".join(parts)
    return key == generated

def content_matches(entry1, entry2):
    # Your matching logic here, e.g.:
    return entry1 == entry2


# ---- only get True linked sockets
def get_socket_info(sockets):
    info = []
    for i, socket in enumerate(sockets):
        if socket.is_linked:
            info.append({
                "index": i,
                "name": socket.name,
                "identifier": socket.identifier,
                "type": socket.type,
                "is_linked": True
            })
    return info


def get_nodegroup_interface_info(node_tree):
    inputs = []
    outputs = []

    for item in node_tree.interface.items_tree:
        # Safely convert default_value if it exists and is not None
        raw_value = getattr(item, "default_value", None)
        if isinstance(raw_value, (int, float, str, bool)):
            default = raw_value
        elif hasattr(raw_value, "__iter__"):
            default = list(raw_value)
        else:
            default = None

        entry = {
            "name": item.name,
            "in_out": item.in_out,
            "socket_type": item.socket_type,
            "description": item.description,
            "default_value": default
        }

        if item.in_out == "INPUT":
            inputs.append(entry)
        elif item.in_out == "OUTPUT":
            outputs.append(entry)

    return inputs, outputs


def get_node_operator_attributes(node):
    attrs = {}

    if node.bl_idname in {"ShaderNodeMath", "ShaderNodeVectorMath"}:
        attrs["operation"] = getattr(node, "operation", "UNLABELED")
    elif node.bl_idname == "ShaderNodeMix":
        attrs["blend_type"] = getattr(node, "blend_type", "UNLABELED")
        attrs["data_type"] = getattr(node, "data_type", "UNLABELED")
    elif node.bl_idname == "ShaderNodeValue":
        attrs["label"] = "Value"
    elif node.bl_idname == "ShaderNodeRGB":
        attrs["label"] = "Color"
    else:
        label = node.label.strip()
        attrs["label"] = label

    return attrs


def compare_and_merge(existing_sockets, new_sockets, socket_type, node_type, label):
    for new_sock in new_sockets:
        idx = new_sock["index"]

        match_found = False
        for exist_sock in existing_sockets:
            if exist_sock["index"] == idx and all(
                exist_sock.get(k) == new_sock.get(k) for k in ("name", "identifier", "type")
            ):
                match_found = True
                if new_sock["is_linked"] and not exist_sock["is_linked"]:
                    print(f"Upgrading socket is_linked to True for {node_type} '{label}' {socket_type}[{idx}] '{new_sock['name']}'")
                    exist_sock["is_linked"] = True
                break

        if not match_found:
            existing_sockets.append(new_sock)

        else:
            # Optionally warn on mismatches in metadata
            for prop in ("name", "identifier", "type"):
                if exist_sock.get(prop) != new_sock.get(prop):
                    print(f"Conflict in {node_type} '{label}' {socket_type}[{idx}] on key '{prop}':")
                    print(f"  Existing: {exist_sock[prop]}")
                    print(f"  New     : {new_sock[prop]}")


def inspect_material_nodes(mat):
    result = {}
    seen_keys = {}
    label = {}
    if not mat.use_nodes:
        print(f"Material '{mat.name}' does not use nodes.")
        return result

    for node in mat.node_tree.nodes:
        node_type = node.bl_idname


        # Now allow 'NodeReroute'
    #    if node_type == "ShaderNodeGroup" or node_type == "NodeReroute" or node_type == "NodeFrame":
        if node_type == "ShaderNodeGroup" or node_type == "NodeFrame":
            continue

        entry = {
            "type": node_type,
        }

        attr_data = get_node_operator_attributes(node)  # always a dict now

        if "operation" in attr_data:
            label = f"{node_type}_{attr_data['operation']}"
        elif "data_type" in attr_data:
            label = f'{entry["type"]}_{attr_data["data_type"]}_{attr_data["blend_type"]}'
        else:
            label = node_type
        if label != node_type:
            entry["label"] = label

        key = (node_type, label)
        entry["label"] = label

    #-- Add operations and data/blender_type
        if "operation" in attr_data:
            entry["operation"] = attr_data["operation"]
        if "data_type" in attr_data:
            entry["data_type"] = attr_data["data_type"]
        if "blend_type" in attr_data:
            entry["blend_type"] = attr_data["blend_type"]

        entry["inputs"] = get_socket_info(node.inputs)
        entry["outputs"] = get_socket_info(node.outputs)

        print(f"node_type: {node_type}, label: {label} ({type(label)})")

        if key in seen_keys:
            existing_key = seen_keys[key]
            existing = result[existing_key]
            compare_and_merge(existing["inputs"], entry["inputs"], "inputs", node_type, label)
            compare_and_merge(existing["outputs"], entry["outputs"], "outputs", node_type, label)
            existing["inputs"].sort(key=lambda e: e["index"])
            existing["outputs"].sort(key=lambda e: e["index"])

        else:
            result[label] = entry
            seen_keys[key] = label

    for entry in result.values():
       entry.pop("label", None)  # silently remove label if present

    return result


def main():

    obj = bpy.context.active_object
    if not obj or not obj.active_material:
        print("No active object or material.")
        return

    mat = obj.active_material
    print(f"Inspecting material: {mat.name}")

    data1 = inspect_material_nodes(mat)

    ref_file = r"F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\blender_native_node_ref_2.json"
  #  ref_file = r"F:\Python_Scripts\Blender Scripts\merged_native_node_sockets_onlytrue.json"
    # Load existing reference data (data2) or start empty if missing
    if os.path.exists(ref_file):
        try:
            with open(ref_file, "r") as f:
                data2 = json.load(f)
        except json.JSONDecodeError:
            print("Warning: Reference file was empty or invalid JSON. Starting fresh.")
            data2 = {}
    else:
        data2 = {}

    # Your existing merge logic here
    merged_data = dict(data2)

    for key1, value1 in data1.items():
        found_match = False
        for key2, value2 in data2.items():
            if content_matches(value1, value2):
                found_match = True
                break
        if found_match and is_generated_key(key1, value1):
            continue
        if not found_match:
            merged_data[key1] = value1

    # Save merged reference file

   # with open(r"F:\Python_Scripts\LSMG_scripts\Final\blender_native_node_ref.json", "w") as f:
    with open(ref_file, "w") as f:
        json.dump(merged_data, f, indent=2, sort_keys=True)

    print(f"Reference JSON updated: {ref_file}")

main()
