## written for Blender 4.3
# - harpoonlobotomy

#C:\Users\Gabriel>python "F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\LSMG_5Stage_Wrapper_NG_Blocks_vers.py" "D:\Steam\steamapps\common\Baldurs Gate 3\Data\Editor\Mods\Shared\Assets\Materials\Characters\CHAR_Skin_Body.lsmg" --named-temp --temp-dir "F:\test\wrapper_script_test_output" --start-at 1
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
        "Result": {"identifier": "Result_Vector", "index": 1},
        "MinOld": {"identifier": "From Min", "index": 1},
        "MaxOld": {"identifier": "From Max", "index": 2},
        "MinNew": {"identifier": "To Min", "index": 3},
        "MaxNew": {"identifier": "To Max", "index": 4}
    },
    "VALUE": {
        "Alpha": {"identifier": "Factor_Float", "index": 0},
        "X": {"identifier": "A_Float", "index": 2},
        "Y": {"identifier": "B_Float", "index": 3},
        "Result": {"identifier": "Result_Float", "index": 0},
        "MinOld": {"identifier": "From_Min_FLOAT3", "index": 7},
        "MaxOld": {"identifier": "From_Max_FLOAT3", "index": 8},
        "MinNew": {"identifier": "To_Min_FLOAT3", "index": 9},
        "MaxNew": {"identifier": "To_Max_FLOAT3", "index": 10}
    },
    "FLOAT": {
        "Alpha": {"identifier": "Factor_Float", "index": 0},
        "X": {"identifier": "A_Float", "index": 2},
        "Y": {"identifier": "B_Float", "index": 3},
        "Result": {"identifier": "Result_Float", "index": 0},
        "MinOld": {"identifier": "From_Min_FLOAT3", "index": 7},
        "MaxOld": {"identifier": "From_Max_FLOAT3", "index": 8},
        "MinNew": {"identifier": "To_Min_FLOAT3", "index": 9},
        "MaxNew": {"identifier": "To_Max_FLOAT3", "index": 10}
    }
}

DEBUG_GROUPS = {
    "ng_blocks": False
}

def debug_print(groups, *args, **kwargs): #             ---------- debug_print("nodegroup_creation", "Setting up node:")
    if isinstance(groups, str):
        groups = [groups]
    if any(DEBUG_GROUPS.get(g, False) for g in groups):
        print(*args, **kwargs)


def load_json_files(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, ng_blocks_path):
    with open(first_data_path, "r", encoding="utf-8") as f1, \
         open(second_data_path, "r", encoding="utf-8") as f2, \
         open(blender_native_nodes_path, "r", encoding="utf-8") as f3, \
         open(nodegroups_defs_path, "r", encoding="utf-8-sig") as f4, \
         open(ng_blocks_path, "r", encoding="utf-8-sig") as f5:
        first_data = json.load(f1)
        second_data = json.load(f2)
        blender_native_nodes = json.load(f3)
        nodegroups_defs = json.load(f4)
        ng_blocks = json.load(f5)

    return first_data, second_data, blender_native_nodes, nodegroups_defs, ng_blocks

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
                conn['default_value'] = socket.get('default_value')

                conn_name = conn.get("Conn_Name")  # <-- Fix is here
                socket_info = SOCKET_MAP.get(data_type, {}).get(conn_name)
                if socket_info:
                    #print(f"{data_type}, {conn_name}")
                    conn["Socket_Identifier"] = socket_info["identifier"]
                    conn["blender_index"] = socket_info["index"]
                    if "default_value" in socket_info:
                        conn["default_value"] = socket_info["default_value"]

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
                    #print(f"{data_type}, {conn_name}")
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

####---- add ng blocks support -------

def add_ng_block_data(first_data, ng_blocks):

    for node_id, node in first_data["Nodes"].items():
        if not node_id:
            continue

        for pattern in ng_blocks:
            patt_name = pattern
            debug_print("ng_blocks", patt_name)

            for group_id, group_data in ng_blocks[patt_name]["ng_nodes"].items():
                debug_print("ng_blocks", group_id)
                for state in ["start", "end", "contained"]:
                    nodes_dict = group_data.get(state, {})
                    if node_id in nodes_dict:
                        debug_print("ng_blocks", f"NodeGroup Block ID: {group_id} // State: {state}")
                        node["ng_block"] = group_id
                        node["ng_block_role"] = nodes_dict[node_id]
                        node["ng_block_state"] = state
                else:
                    continue  # only runs if inner loop did NOT break
                break  # stop searching other groups if matched

def reorder_node_fields(node):
    desired_order = [
        "Node_Id",
        "Node_Name",
        "Node_Type",
        "Is_Pattern",
        "ng_block",
        "ng_block_role",
        "ng_block_state",
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

def add_ng_blocks(first_data, ng_blocks):

    for pattern in ng_blocks:
        patt_name = pattern
        #print(f"Pattern name found in NG BLocks: {patt_name}")

        for node_id in ng_blocks[patt_name]["ng_pattern_blocks"]:
            debug_print("ng_blocks", node_id)
            node = ng_blocks[patt_name]["ng_pattern_blocks"][node_id]
            node["Is_NodeGroup"] = True
            node["Is_Pattern"] = True

            first_data["Nodes"][node_id] = (node)

def write_reordered_output(first_data, reordered_output_path):
    with open(reordered_output_path, 'w', encoding='utf-8') as f_out:
        json.dump(first_data, f_out, indent=2)
    print(f"[Info] Wrote reordered data to '{reordered_output_path}'")

# Final run() function for the wrapper:
def run(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, ng_blocks_path, output_path):
    missing_nodes_output_path = os.path.splitext(output_path)[0] + "_missing_nodes.json"

    first_data, second_data, blender_native_nodes, nodegroups_defs, ng_blocks = load_json_files(
        first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, ng_blocks_path)
    update_node_types_from_second_data(second_data, first_data)
    enhance_nodes_with_blender_info(first_data, blender_native_nodes, nodegroups_defs)
    add_ng_block_data(first_data, ng_blocks)

    missing_node_types, truly_missing = collect_missing_node_types(first_data, blender_native_nodes, nodegroups_defs)
    if truly_missing:
        write_missing_node_types(missing_node_types, truly_missing, missing_nodes_output_path)
    else:
        print("[Info] No missing node types found.")

    add_ng_blocks(first_data, ng_blocks)
    reorder_all_nodes(first_data)
    write_reordered_output(first_data, output_path)

# Optional CLI (won't interfere with wrapper)
if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 7:
        print("Usage: python LSMG_stage5_merge_2and5_final_output_ngblocks_01.py <stage2.json> <stage4.json> <blender_native.json> <nodegroups.json> <ng_blocks.json> <output.json>")
        sys.exit(1)

    first_data_path = sys.argv[1]
    second_data_path = sys.argv[2]
    blender_native_nodes_path = sys.argv[3]
    nodegroups_defs_path = sys.argv[4]
    ng_blocks_path = sys.argv[5]
    output_path = sys.argv[6]

    run(first_data_path, second_data_path, blender_native_nodes_path, nodegroups_defs_path, ng_blocks_path, output_path)

##   python "F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\LSMG_stage5_merge_2and5_final_output_ngblocks_vers.py" "F:\test\wrapper_script_test_output6\stage_2_tmp_CHAR_BASE_VT.json" "F:\test\wrapper_script_test_output6\stage_4_tmp_CHAR_BASE_VT.json" "F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\blender_native_node_ref_2.json" "F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\frame_exported_nodegroups_5.json" "F:\test\wrapper_script_test_output6\node_sequence_CHAR_BASE_VT_pseudonode_03.json" "F:\test\wrapper_script_test_output6\stage_5_output_w_node_sequence_CHAR_BASE_VT_02.json"
