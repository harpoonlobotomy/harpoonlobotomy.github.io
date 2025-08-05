import json
from collections import OrderedDict
import os

SOCKET_MAP = {
    "RGBA": {
        "Alpha": {"identifier": "Factor_Float", "index": 0},
        "X": {"identifier": "A_Color", "index": 6},
        "Y": {"identifier": "B_Color", "index": 7},
        "Result": {"identifier": "Result_Color", "index": 2}
    },
    "VECTOR": {
        "Alpha": {"identifier": "Factor_Float", "index": 0},
        "X": {"identifier": "A_Vector", "index": 4},
        "Y": {"identifier": "B_Vector", "index": 5},
        "Result": {"identifier": "Result_Vector", "index": 1}
    },
    "VALUE": {
        "Alpha": {"identifier": "Factor_Float", "index": 0},
        "X": {"identifier": "A_Float", "index": 2},
        "Y": {"identifier": "B_Float", "index": 3},
        "Result": {"identifier": "Result_Float", "index": 0}
    }
}

def load_json_files(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path):
    with open(first_data_path, "r", encoding="utf-8") as f1, \
         open(second_data_path, "r", encoding="utf-8") as f2, \
         open(blender_native_nodes_path, "r", encoding="utf-8") as f3, \
         open(nodegroups_defs_path, "r", encoding="utf-8-sig") as f4:
        first_data = json.load(f1)
        second_data = json.load(f2)
        blender_native_nodes = json.load(f3)
        nodegroups_defs = json.load(f4)

    return first_data, second_data, blender_native_nodes, nodegroups_defs

def extract_type(full_type):
    return full_type.split(" /")[0].strip()

def traverse_and_update(node, first_data, seen_node_types):
    if not isinstance(node, dict):
        return
    conn = node.get("Connection")
    if conn:
        for dir in ["From", "To"]:
            node_id = conn.get(f"{dir}_Node")
            node_type = conn.get(f"{dir}_Node_Type_Name")
            if node_id and node_type:
                clean_type = extract_type(node_type)
                if node_id in first_data["Nodes"]:
                    first_data["Nodes"][node_id]["Node_Type"] = clean_type
                    seen_node_types[node_id] = clean_type
    for child in node.get("Outputs", []):
        traverse_and_update(child, first_data, seen_node_types)

def update_node_types_from_second_data(second_data, first_data):
    seen_node_types = {}
    for entry in second_data.values():
        if isinstance(entry, list):
            for item in entry:
                traverse_and_update(item, first_data, seen_node_types)
        else:
            traverse_and_update(entry, first_data, seen_node_types)
    return seen_node_types

def enhance_nodes_with_blender_info(first_data, blender_native_nodes, nodegroups_defs):
    for node_id, node in first_data["Nodes"].items():
        node_type = node.get("Node_Type")
        if not node_type:
            continue

        blender_node = blender_native_nodes.get(node_type)
        if not blender_node:
            if node_type in nodegroups_defs:
                node["Is_NodeGroup"] = True
            continue

        node["Blender_type"] = blender_node.get("type")

        if "blend_type" in blender_node:
            node["Blend_Type"] = blender_node.get("blend_type")
            node["Data_Type"] = blender_node.get("data_type")
        if "operation" in blender_node:
            node["Blender_Operation"] = blender_node["operation"]
        if "autohide" in blender_node:
            node["Autohide"] = blender_node["autohide"]

        conn_name = None
        data_type = node["Data_Type"] = blender_node.get("data_type")

        blender_inputs_list = blender_node.get("inputs", [])
        connectors = node.get("m_Inputs", {}).get("Connectors", [])
        for i, conn in enumerate(connectors):
            if i < len(blender_inputs_list):
                socket = blender_inputs_list[i]
                conn["Socket_Identifier"] = socket.get("identifier")
                conn["blender_index"] = socket.get("index")

                conn_name = conn.get("Conn_Name")  # <-- Fix is here
                socket_info = SOCKET_MAP.get(data_type, {}).get(conn_name)
                if socket_info:
        #            print(f"{data_type}, {conn_name}")
                    conn["Socket_Identifier"] = socket_info["identifier"]
                    conn["blender_index"] = socket_info["index"]

        blender_outputs_list = blender_node.get("outputs", [])
        connectors = node.get("m_Outputs", {}).get("Connectors", [])
        for i, conn in enumerate(connectors):
            if i < len(blender_outputs_list):
                socket = blender_outputs_list[i]
                conn["Socket_Identifier"] = socket.get("identifier")
                conn["blender_index"] = socket.get("index")

                conn_name = conn.get("Conn_Name")  # <-- Fix is here
                socket_info = SOCKET_MAP.get(data_type, {}).get(conn_name)
                if socket_info:
            #        print(f"{data_type}, {conn_name}")
                    conn["Socket_Identifier"] = socket_info["identifier"]
                    conn["blender_index"] = socket_info["index"]
                # Handle special case: add default Factor input if missing

        if len(blender_inputs_list) == len(connectors) + 1:
            for socket in blender_inputs_list:
                identifier = socket.get("identifier", "").lower()
                if identifier.startswith("factor"):
                    if not any(conn.get("Socket_Identifier") == socket["identifier"] for conn in connectors):
                        connectors.append({
                            "Socket_Identifier": socket["identifier"],
                            "Default_Value": 1.0,
                            "blender_index": socket.get("index")
                        })
                                #print(f"[Set Factor] Node '{node.get('ID', '?')}' (type: {node.get('Type', '?')}) – defaulted 'Factor' to 1.0")
                        break

def reorder_node_fields(node):
    desired_order = [
        "Node_Id",
        "Node_Name",
        "Node_Type",
        "Blender_type",
        "Data_Type",
        "Blend_Type",
        "Blender_Operation",
        "Is_NodeGroup",
        "Autohide",
        "d2p1_Attributes",
        "Location",
        "m_Inputs",
        "m_Outputs",
        "Internal_Connectors"
    ]
    ordered = OrderedDict()
    for key in desired_order:
        if key in node:
            ordered[key] = node[key]
    for key in node:
        if key not in ordered:
            ordered[key] = node[key]
    return ordered

def reorder_all_nodes(first_data):
    for node_id in first_data.get("Nodes", {}):
        node = first_data["Nodes"][node_id]
        first_data["Nodes"][node_id] = reorder_node_fields(node)

def collect_missing_node_types(first_data, blender_native_nodes, nodegroups_defs):
    missing_node_types = sorted({
        node.get("Node_Type")
        for node in first_data["Nodes"].values()
        if node.get("Node_Type") and node.get("Node_Type") not in blender_native_nodes
    })

    truly_missing = [nt for nt in missing_node_types if nt not in nodegroups_defs]
    return missing_node_types, truly_missing

def write_missing_node_types(missing_node_types, truly_missing, missing_nodes_output_path):
    with open(missing_nodes_output_path, "w", encoding="utf-8") as f_missing:
        json.dump({
            #"missing_node_types": missing_node_types,
            "truly_missing_node_types": truly_missing
        }, f_missing, indent=2)
    print(f"[Info] Wrote missing and truly missing node types to '{missing_nodes_output_path}'")

def write_reordered_output(first_data, reordered_output_path):
    with open(reordered_output_path, 'w', encoding='utf-8') as f_out:
        json.dump(first_data, f_out, indent=2)
    print(f"[Info] Wrote reordered data to '{reordered_output_path}'")

# Final run() function for the wrapper:
def run(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, output_path):
    missing_nodes_output_path = os.path.splitext(output_path)[0] + "_missing_nodes.json"

    first_data, second_data, blender_native_nodes, nodegroups_defs = load_json_files(
        first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path)
    update_node_types_from_second_data(second_data, first_data)
    enhance_nodes_with_blender_info(first_data, blender_native_nodes, nodegroups_defs)
    reorder_all_nodes(first_data)
    missing_node_types, truly_missing = collect_missing_node_types(first_data, blender_native_nodes, nodegroups_defs)

    if truly_missing:
        write_missing_node_types(missing_node_types, truly_missing, missing_nodes_output_path)
    else:
        print("[Info] No missing node types found.")

    write_reordered_output(first_data, output_path)

# Optional CLI (won't interfere with wrapper)
if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 6:
        print("Usage: python LSMG_stage5_merge_2and5_final_output.py <stage2.json> <stage4.json> <blender_native.json> <nodegroups.json> <output.json>")
        sys.exit(1)

    first_data_path = sys.argv[1]
    second_data_path = sys.argv[2]
    blender_native_nodes_path = sys.argv[3]
    nodegroups_defs_path = sys.argv[4]
    output_path = sys.argv[5]

    run(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, output_path)
