## Generates template from JSON file - will produce the JSON file from LSMG automatically if not found. Supports Patterns and nodegroup generation.
# Recursive nodegroups not yet implemented, but most other things are, including the addition of template-level images into image texture nodegroups.

# Written for Blender vers 4.3
# - harpoonlobotomy

import bpy
import json
import os
import sys
from collections import Counter
from collections import defaultdict
import importlib
import re
from datetime import datetime
from pprint import pprint
import sqlite3

counts = Counter()
## F:\test\wrapper_script_test_output_changing_parser1\stage_5_tmp_CHAR_Skin_Body.json

delete_nodes = False
node_id_labels = False ######### Change this back to have parameters again
recreate_nodegroups = True
## need a better version of this - currently, it either always rebuilds, or never does. which isn't idea. A PowerNode_vector can be reused;
#  -- but a texture node shouldn't be.(Unless it's shared.)

track_nodes = []#"1588", "1965"]
track_sockets = []
# === CONFIG===
#MAIN_JSON_PATH = r"F:\test\wrapper_script_test_fixing_node_id\stage_5_tmp_CHAR_BASE_VT.json"
#MAIN_JSON_PATH = r"F:\test\wrapper_script_test_fixing_node_id\stage_5_tmp_CHAR_Skin_Body.json"

node_instance_map = {}  # key: node_id (int), value: actual Blender node instance
global_socket_map = {} # global_socket_map[node_id][socket_id] = socket
texture_nodegroups = set()
texture_data = {}

NODEGROUP_JSON_PATH = r"F:\Python_Scripts\Template_Generator\nodegroup_blueprints.json"
#NODEGROUP_JSON_PATH = r"F:\Python_Scripts\Stash_working_tempgen\frame_exported_nodegroups_6.json"
SQLITE_PATH = r"F:\BG3 Extract PAKs\Asset Management Core\Master_Asset_Database.db"

COLOR_NAME_TO_TAG = {
    "none": "NONE",
    "yellow": "COLOR",
    "blue": "CONVERTER",
    "red": "INPUT",
    "black": "OUTPUT",
    "teal": "SCRIPT",
    "green": "SHADER",
    "orange": "TEXTURE",
    "purple": "VECTOR",
}

# Define which groups are active --------------  debug_print(["node_setup", "summary"], "Node info...") <- square brackets to put the print in multiple groups.
DEBUG_GROUPS = {
    "native_nodes": False,
    "nodegroup_creation": False,
    "nodegroup_setup": False,
    "errors": True,
    "sockets": False,
    "other": False,
    "links": False,
    "nodegroup_connectors": False,
    "4ch_requirements": False,
    "pattern": False,
    "sets_creation": False,
    "setup": True,
    "track_nodes": False,
    "UV_maps": False,
    "shell_nodegroups": False,
    "W_redirect": True
}

used_connectors = set()
temp_nodes = set()
created_groups = {}

special_template_keys = ["Hair", "Fur", "Feathers"]
template_data = {
    "template_path": "Public/Shared/Assets/Materials/Effects/Model/VFX_Model_AlphaTest_BASE_CINE_WINGS_TwoSided_WAlpha_FX_01.lsf",
    "template_name": "VFX_Model_AlphaTest_Base_Cine_Wings",
    "force_new_template": False,
    "force_new_template_file": False,
    "disable_patterns": False,
    "recreate_nodegroups": False
}

def debug_print(groups, *args, **kwargs): #             ---------- debug_print("nodegroup_creation", "Setting up node:")
    if isinstance(groups, str):
        groups = [groups]
    if any(DEBUG_GROUPS.get(g, False) for g in groups):
        print(*args, **kwargs)

def get_template_name(template_data):

    global recreate_nodegroups

    template_base_path = "D:\Steam\steamapps\common\Baldurs Gate 3\Data\Editor\Mods"  # where it is on your harddrive
    output_folder = r"F:\test\new_pattern"

    template_name = template_data.get("template_name", "DefaultName")
    force_new_template = template_data.get("force_new_template", False)
    force_new_template_file = template_data.get("force_new_template_file", False)
    recreate_nodegroups = template_data.get("recreate_nodegroups", False)
    disable_patterns = template_data.get("disable_patterns", False)

    sourcefile = template_data.get("template_path", "DefaultName")

    db_path = str(sourcefile)  #path from SourceFile

    #debug_print("setup", f"Template name: {template_name}")
    #debug_print("setup", f"Force new template: {force_new_template}")
    #debug_print("setup", f"Force new template file: {force_new_template_file}")
    #debug_print("setup", f"Recreate nodegroups: {recreate_nodegroups}")

    if "/" in db_path:
        if db_path:
            db_path = db_path.translate(str.maketrans("", "", "()',"))
            db_path = db_path.replace("lsf", "lsmg")

            #debug_print("setup", f"Sourcefile: {sourcefile}")
            #debug_print("setup", f"db_path after cleanup: {db_path}")

            _, split_path = db_path.split("/", 1)
            #print(split_path)
            template_path = os.path.join(template_base_path, split_path)
            template_path = template_path.replace("/", "\\")
            template_name = os.path.basename(template_path)
            template_name = template_name.replace(".lsmg", "")

            #debug_print("setup", f"db_path: {db_path} // template name: {template_name} // template_path = {template_path}")
            debug_print("setup",f"template_name: {template_name} // force_new_template: {force_new_template} // force_new_template_file: {force_new_template_file} // disable_patterns: {disable_patterns} // recreate_nodegroups: {recreate_nodegroups}")
            output_filename = "stage_5_tmp_" + template_name + ".json"
            #print(f"Output filename = `{output_filename}`")
            final_file_path = os.path.join(output_folder, output_filename)
            #debug_print("setup", f"Template path: {final_file_path}")
            print(f"Final file path to be used: `{final_file_path}`")
    if template_name:
        #if os.path.exists(final_file_path):
            #debug_print("setup", f"File already exists; not sure if force_new_template_file is true yet.")

        #if force_new_template_file is not True:
            #debug_print("setup", f"Force new template file is not True. If file exists was also true, the next message should be `File already exists`.")

        if os.path.exists(final_file_path) and force_new_template_file is not True:
            debug_print("setup", f"Not creating new template file; file already exists:")
            debug_print("setup", final_file_path)
            return template_name, final_file_path

        else:
            debug_print("setup", f"Creating new template file.")
            import subprocess

            if disable_patterns:
                print("disable patterns is True, proceeding with template generation accordingly.")
                cmd = [
                    "python",
                    r"F:\Python_Scripts\Template_Generator\CURRENT\LSMG_5Stage_Wrapper_NG_Blocks_vers.py",
                    template_path,
                    "--named-temp",
                    "--temp-dir", output_folder,
                    "--start-at", "1", # :::::: CHANGE THIS BACK TO ONE. ONLY AT 4 FOR PATTERN TESTING.
                    "--disable_patterns", "True"
                ]

            else:
                print("disable patterns is not True, proceeding with template generation accordingly.")
                cmd = [
                    "python",
                    r"F:\Python_Scripts\Template_Generator\CURRENT\LSMG_5Stage_Wrapper_NG_Blocks_vers.py",
                    template_path,
                    "--named-temp",
                    "--temp-dir", output_folder,
                    "--start-at", "1" # :::::: CHANGE THIS BACK TO ONE. ONLY AT 4 FOR PATTERN TESTING.
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # This is everything the script printed to stdout
            debug_print("setup", f"{result.stdout}")

            output_filename = "stage_5_tmp_" + template_name + ".json"
            #print(output_filename)
            final_file_path = os.path.join(output_folder, output_filename)
            #print(final_file_path)
            if os.path.exists(final_file_path):
                debug_print("setup", "Template file generated.")
            else:
                print(f"Failed to generate file for {template_name}.")
    else:
        print("Could not find template files.")

    return template_name, final_file_path

def clear_all_ng_from_file(): # === delete all nodegroups - remove when testing is done ===
    if delete_nodes == True:
        for node_group in list(bpy.data.node_groups):  # Make a copy of the list to avoid modifying the list while iterating
            bpy.data.node_groups.remove(node_group)
        print("cleared all nodegroups from file")
        debug_print("other", "Cleared existing nodegroups from file.")

def normalize_name(name):
    if not name:
        return ""
    return name.lower().replace(" ", "").removeprefix("mat")

def set_reroute_type(node_instance, node_tree, node_type):
    reroute = node_instance

    if node_type == "PassthroughNode_color":
#        #print(f"Reroute is color type {node_type}")
        return
    elif node_type == "PassthroughNode_vector":
#        #print(f"Reroute is vector type {node_type}")
        vector_node = node_tree.nodes.new("ShaderNodeCombineXYZ")
        temp_nodes.add(vector_node)
        node_tree.links.new(vector_node.outputs[0], reroute.inputs[0])

    else:  # PassthroughNode (assumed float)
        value_node = node_tree.nodes.new("ShaderNodeValue")
#        #print(f"Reroute is scalar type {node_type}")
        temp_nodes.add(value_node)
        node_tree.links.new(value_node.outputs[0], reroute.inputs[0])

def map_native_connectors(node_type, node_id, node_instance, connectors_json, node_tree, connections_list):
    mapping = {}

    if "PassthroughNode" in node_type:
        set_reroute_type(node_instance,  node_tree, node_type)

    # Create a lookup for actual socket objects
    input_sockets = list(node_instance.inputs)
    output_sockets = list(node_instance.outputs)

    from_id = [conn.get("from_socket") for conn in connections_list]
    to_id = [conn.get("to_socket") for conn in connections_list]

    for conn in connectors_json:
        socket_id = conn.get("Socket_Id")

        if socket_id in from_id:
    #        #print(f"From_Socket == Socket_Id: {socket_id}")
            used_connectors.add(socket_id)
        elif socket_id in to_id:
    #        #print(f"To_Socket == Socket_Id: {socket_id}")
            used_connectors.add(socket_id)

    try:
        for conn in connectors_json:
            real_sockets = []
            socket_id = conn.get("Socket_Id")
            if socket_id not in used_connectors:
        #        #print(f"Socket ID {socket_id} not used")
                continue

            is_input = socket_id in to_id
            is_output = socket_id in from_id

            if is_input:
                relevant_sockets = input_sockets
            elif is_output:
                relevant_sockets = output_sockets
            else:
                continue

            index = conn.get("blender_index")
            conn_2 = conn.get("Conn_name_2")
            socket = None

            if index is not None:
                try:
                    index = int(index)
                    socket = (
                        node_instance.inputs[index]
                        if conn.get("Socket_Id") in to_id else
                        node_instance.outputs[index]
                    )
                    mapping[conn["Socket_Id"]] = socket
                except (IndexError, ValueError):
                    print(f"[Warning] Invalid socket index {index}, at socket {socket_id} on node {node_id} // {node_instance.name}")
            else:
                if "Combine" in node_type and conn_2 == "Value4":
                    debug_print("4ch_requirements", f"Socket {conn_2}/{socket_id} is {node_type} - ignore.")
### # NOTE: Add the autocheck for alpha input options
                else:
                    print(f"[Warning] Missing index for connector: {conn}")
            socket_id = conn.get("Socket_Id")
            if socket_id is None:
                print(f"[Warning] Connector missing Socket_Id: {conn}")
                #continue
            mapping[socket_id] = socket

    except Exception as e:
        print(f"[ERROR] map_connections failed for node {node_id}: {e}")
        import traceback
        traceback.print_exc()
    return mapping

def map_connections(connectors_json, sockets_internal, node_id, node_instance, blender_sockets, node_type, connections_list, used_connectors, nodes_json):
    mapping = {}
    node_id = node_id

    is_pattern = False
    if node_type in node_id:
        is_pattern = True

    valid_input_sockets = {s.name for s in node_instance.inputs}
    valid_output_sockets = {s.name for s in node_instance.outputs}

    input_sockets = list(node_instance.inputs)
    output_sockets = list(node_instance.outputs)

## -----------   Get 'used_connectors' set first -------------
    from_id = [conn.get("from_socket") for conn in connections_list]
    to_id = [conn.get("to_socket") for conn in connections_list]

    from_pattern_sockets = []
    to_pattern_sockets = []

    pattern_socket_ids = set()

    for node_id, node_data in nodes_json.items():
        if node_data.get("Is_Pattern"):
            outputs = node_data.get("m_Outputs", {})
            connectors = outputs.get("Connectors", [])
            for conn in connectors:
                socket_id = conn.get("Socket_Id")
                if socket_id is not None:
                    pattern_socket_ids.add(str(socket_id))
            inputs = node_data.get("m_Inputs", {})
            connectors = inputs.get("Connectors", [])
            for conn in connectors:
                socket_id = conn.get("Socket_Id")
                #print(f"{socket_id}")
                if socket_id is not None:
                    pattern_socket_ids.add(str(socket_id))
                    #print(f"Assigned from_pattern_sockets:, {pattern_socket_ids}")

    for conn in connectors_json:
        key = None
        socket_id = conn.get("Socket_Id")
        if socket_id in track_sockets:
             print(conn)
        if socket_id in from_id or socket_id in to_id:
            used_connectors.add(socket_id)
            if socket_id in track_sockets:
                 print(conn)
        if socket_id in pattern_socket_ids:
            used_connectors.add(socket_id)
            if socket_id in track_sockets:
                 print(conn)
## ----------- Now actually start matching sockets -------------
    try:
        for conn in connectors_json:
            socket_id = conn.get("Socket_Id")
            if socket_id not in used_connectors:
                continue

            is_input = socket_id in to_id
            is_output = socket_id in from_id

            if is_input:
                relevant_sockets = input_sockets
                valid_sockets = valid_input_sockets
            elif is_output:
                relevant_sockets = output_sockets
                valid_sockets = valid_output_sockets
            else:
                continue

            key = None
            socket_id = conn.get("Socket_Id")
            if socket_id in track_sockets:
                 print(f"For conn in connectors json // track sockets: {conn}")
            if socket_id in pattern_socket_ids:
                conn_name = f"{conn.get('Conn_name_2') or ''}/{conn.get('Conn_Name') or ''}"
                conn_2 = conn.get("Conn_Name")
            else:
                conn_name = conn.get("Conn_Name") #----------------------------------Add the above back in
                conn_2 = conn.get("Conn_name_2")

            int_out = None
            int_in = None
            only_sock = None
            socket = None

            for ic in sockets_internal:
                if ic.get("ID") == socket_id:
                    raw_socket = ic.get("Socket", "")
                    match = re.match(r"m_Output(.+)", raw_socket)
                    if match:
                        int_out = match.group(1)
                    else:
                        match = re.match(r"m_Input(.+)", raw_socket)
                        if match:
                            int_in = match.group(1)

            if any(x in valid_sockets for x in (conn_name, conn_2, int_out, int_in)):
                for sock in relevant_sockets:
                    if sock.name in (conn_name, conn_2, int_out, int_in):
                        socket = sock
                        if socket_id in track_sockets:
                            print(f"socket found in relevant_sockets for {conn_name}//{conn_2}/{int_out}/{int_in}: {relevant_sockets}")

                        break

            elif conn_name:
                for sock in blender_sockets:
                    if normalize_name(sock.name) == normalize_name(conn_name):
                        socket = sock
                        break
                    #elif socket_id in track_sockets:
                #        #print(f"socket found in relevant_sockets for {conn_name}//{conn_2}/{int_out}/{int_in}: {relevant_sockets}")
                    elif len(blender_sockets) == 1:
                        socket = sock
                        if socket_id in track_sockets:
                            print(f"only one socket available for {conn_name}: {valid_sockets}")

                    elif sock.name in conn_name and conn_name != "":
                        socket = sock
                        if socket_id in track_sockets:
                            print(f"Elif conn name in sock name:: Conn name: {conn_name} // sockets: {sock}")

            else:
                print(f"Unused or missing socket for: {socket_id} - not present on this node, {node_id}. Trying... :")
                if len(valid_sockets) == 1:
                    for sock in relevant_sockets:
                        socket = sock
                    if socket_id in track_sockets:
                        print(f"only one socket available for {conn_name}: {valid_sockets}")

            if socket_id is None:
                debug_print(["sockets", "errors"], f"[Warning] Connector missing Socket_Id: {conn}")

            if socket != None:
                mapping[socket_id] = socket

    except Exception as e:
        print(f"[ERROR] map_connections failed for node {node_id}: {e}")
        import traceback
        traceback.print_exc()
    return mapping

def map_socket_ids_to_blender_sockets(node_data, node_instance, nodegroup_json_data, connections_list, node_tree, nodes_json):
    #print("top of map socket ids")
    node_id = node_data["Node_Id"]
    node_type = node_data["Node_Type"]
    from_sock = [conn.get("from_socket") for conn in connections_list]
    to_sock = [conn.get("from_socket") for conn in connections_list]
    inputs_internal = [ic for ic in node_data.get("Internal_Connectors", []) if ic.get("Socket", "").startswith("m_Input")]
    outputs_internal = [ic for ic in node_data.get("Internal_Connectors", []) if ic.get("Socket", "").startswith("m_Output")]

    if node_id in track_nodes:
        print(f"Inside map_socket_ids_to_blender_sockets // node data:       {node_data}")

    is_nodeblock = "ng_block" in node_data
    is_native = "Blender_type" in node_data
    #print("About to go to map connectors")
    if is_native and not is_nodeblock:
        inputs = map_native_connectors(node_type, node_id, node_instance, node_data.get("m_Inputs", {}).get("Connectors", []), node_tree, connections_list)
        outputs = map_native_connectors(node_type, node_id, node_instance, node_data.get("m_Outputs", {}).get("Connectors", []), node_tree, connections_list)
    else:
        inputs = map_connections(node_data.get("m_Inputs", {}).get("Connectors", []), inputs_internal, node_id, node_instance, node_instance.inputs, node_type, connections_list, used_connectors, nodes_json)
        outputs = map_connections(node_data.get("m_Outputs", {}).get("Connectors", []), outputs_internal, node_id, node_instance, node_instance.outputs, node_type, connections_list, used_connectors, nodes_json)

    if node_id in track_nodes:
        print(f"{node_id} has just left 'map connections'. Inputs and Outputs follow:")
        pprint(f"Input count: {len(inputs)}")
        pprint(f"Output count: {len(outputs)}")


    if node_id not in global_socket_map:
        global_socket_map[node_id] = {}

    for socket_id, socket in inputs.items():
        global_socket_map[node_id][socket_id] = socket
    for socket_id, socket in outputs.items():
        global_socket_map[node_id][socket_id] = socket
    existing_entry = global_socket_map.get(node_id)

    return global_socket_map

def create_shell_nodegroup(group_name, nodes_json): #----   Is just a hollow placeholder if node not found in native or nodegroup documents
#                                              ---- Should have the required number of sockets; seems to now.

    typename = None
    nodename = None
    for entry in nodes_json:
        debug_print("shell_nodegroups", entry)
        if entry == "Node_Type":
            node_type = "Test"
            if node_type != "":
                if node_id_labels is True:
                    typename = group_name + "_" + node_type
                else:
                    typename = node_type

    for entry in nodes_json:
        if entry == "Node_Name":
            node_name = nodes_json.get("Node_Name")
            if node_name != "":
                if node_id_labels is True:
                    nodename = "[" + group_name + "]" + node_name
                else:
                    nodename = node_name

    if nodename:
        group_name = nodename
    else:
        if typename:
            group_name = typename

    outputs = nodes_json.get("m_Outputs", {})
    inputs = nodes_json.get("m_Inputs", {})

    # Create new nodetreeree
    nodegroup = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    nodegroup.use_fake_user = False
    nodegroup["label"] = group_name

    group_input = nodegroup.nodes.new('NodeGroupInput')
    group_input.location = (-350, 0)
    group_input.label = "Group Input"

    group_output = nodegroup.nodes.new('NodeGroupOutput')
    group_output.location = (350, 0)
    group_output.label = "Group Output"

    debug_print("shell_nodegroups", f"Have generated the basid nodetree for {group_name}")
    # Helper: clear existing sockets
    def clear_interface_sockets(in_out: str):
        for item in list(nodegroup.interface.items_tree):
            if item.in_out == in_out:
                nodegroup.interface.remove(item)

    clear_interface_sockets('INPUT')
    clear_interface_sockets('OUTPUT')

    # Add interface INPUT sockets
    for conn in nodes_json.get("m_Inputs", {}).get("Connectors", []):
        sock_name = conn.get("Conn_Name") or conn.get("Conn_name_2") or "Input"
        if sock_name and sock_name not in nodegroup.interface.items_tree:
            nodegroup.interface.new_socket(
                name=sock_name,
                in_out='INPUT',
                socket_type='NodeSocketFloat'
            )


    # Add interface OUTPUT sockets
    for conn in nodes_json.get("m_Outputs", {}).get("Connectors", []):
        sock_name = conn.get("Conn_Name") or conn.get("Conn_name_2") or "Output"
        if sock_name and sock_name not in nodegroup.interface.items_tree:
            nodegroup.interface.new_socket(
                name=sock_name,
                in_out='OUTPUT',
                socket_type='NodeSocketFloat'
            )

    group_in = next((n for n in nodegroup.nodes if n.type == "GROUP_INPUT"), None)
    group_out = next((n for n in nodegroup.nodes if n.type == "GROUP_OUTPUT"), None)


    #print(f"Reroute is scalar type {node_type}")
    nodegroup.links.new(group_in.outputs[0], group_out.inputs[0])
    #print(f"Did I link inside a shell nodegroup? Nodegroup: {nodegroup}")

    return nodegroup

def get_node_sets(nodes_json, nodegroup_json_data):
    blendernative_entries = []
    nodegroup_entries = []
    ng_block_node_entries = []
    pattern_entries = []
    ng_block = []
    optional_keys = [
        "Node_Type", "Blender_type", "Data_Type", "Blend_Type", "Node_Name",
        "Blender_Operation", "d2p1_Attributes", "Location", "Autohide", "Is_NodeGroup",
        "ng_block", "ng_block_role", "ng_block_state", "Parameter", "Is_Pattern"]

    for node_id, node_data in nodes_json.items():
        node_entry = {"node_id": node_id}
        for key in optional_keys:
            if key in node_data:
                node_entry[key] = node_data[key]

        if "ng_block" in node_data:
            ng_block_node_entries.append(node_entry)
            debug_print(["ng_block_setup", "sets_creation"], f"NG block component found: {node_id}")
            #print(f"NG block component found: {node_id}")
        elif "Is_Pattern" in node_data:
            debug_print(["pattern", "sets_creation"], f":::::::::::{node_id} found by the pattern")
            pattern_entries.append(node_entry)
            #nodegroup_entries.append(node_entry)
        elif "Is_NodeGroup" in node_data:
            nodegroup_entries.append(node_entry)
            debug_print(["nodegroup_setup", "sets_creation"], f"Nodegroup found: {node_id}: is_nodegroup in data.")
        elif "Blender_type" in node_data:
            blendernative_entries.append(node_entry)
            debug_print(["native_nodes", "sets_creation"], f"Native node found: {node_id}")
        else:
            nodegroup_entries.append(node_entry) ##=== make a new one inside here.
            debug_print(["nodegroup_setup", "sets_creation"], f"Not nodegroup or native: {node_id}. Shell nodegroup will be created.")

    return blendernative_entries, nodegroup_entries, ng_block_node_entries, pattern_entries

def get_correct_native_nodes(blendernative_entries, node_tree, nodes_json, nodegroup_json_data, connections_list):

    for entry in blendernative_entries:
        node = None
        debug_print("native_nodes", f"Starting new node:")
        node_id = entry.get("node_id")
        node_name = entry.get("Node_Name")
        node_type = entry.get("Node_Type")
        blender_type = entry.get("Blender_type")             # ------- print(f"{}")
        autohide = entry.get("Autohide")
        op = entry.get("Blender_Operation")
        datatype = entry.get("Data_Type")
        blendtype = entry.get("Blend_Type")
        loc_raw = entry.get("Location", {})
        param_name = entry.get("d2p1_Attributes", {}).get("ParameterName")


        x = loc_raw.get("x", 0.0)
        y = loc_raw.get("y", 0.0)
        x = x*-1
        y = y*-1
        loc = (x, y)

        try:
            debug_print("native_nodes", f"Attempting to create node {node_id}, a {blender_type} node.")

            node = node_tree.nodes.new(blender_type)
            node_instance_map[node_id] = node
            node.location = loc

            if op and hasattr(node, "operation"):
                valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
                if op in valid_ops:
                    node.operation = op

            if datatype and hasattr(node, "data_type"):
                datas = [item.identifier for item in node.bl_rna.properties["data_type"].enum_items]
                if datatype in datas:
                    node.data_type = datatype

            if blendtype and hasattr(node, "blend_type"):
                blends = [item.identifier for item in node.bl_rna.properties["blend_type"].enum_items]
                if blendtype in blends:
                    node.blend_type = blendtype

            node_data = nodes_json[node_id]
            map_socket_ids_to_blender_sockets(node_data, node, nodegroup_json_data, connections_list, node_tree, nodes_json)

        except Exception as e:
            #print(f"native node failure for {node_id}")
            debug_print(["native_nodes", "errors"], f"[Warning] Could not create node '{blender_type}': {e}")

        if param_name is not None:
            param_label = str(param_name)
            node.label = param_label

        if param_name is None:
            param_label = str(node_name)
            node.label = param_label

        if node_id_labels == True:
            node.label = "[" + node_id + "]" + param_label

        if autohide:
            node.hide = True

        val = float(1)
        valvec = (1, 1, 1)
        if blendtype and hasattr(node, "blend_type"):
            for sock in node.inputs:  # sock is each input socket
                if sock.identifier == "Factor_Float":  # or sock.identifier if you prefer
                    sock.default_value = val
                elif sock.identifier == "Factor_Vector":
                    sock.default_value = valvec

        if blender_type == "ShaderNodeValue":
            x_str = entry.get("d2p1_Attributes", {}).get("X")
            if x_str is not None:
                try:
                    val = float(x_str)
                    node.outputs[0].default_value = val
                    #print(f"[Set] ShaderNodeValue {node_id} value set to {val}")
                except ValueError:
                    debug_print(["native_nodes", "errors"], f"Warning: X value '{x_str}' is not a valid number.")

                except Exception as e:
                    debug_print(["native_nodes", "errors"], f"[Error] Failed to set ShaderNodeValue {node_id} value: {e}")

        if blender_type == "ShaderNodeRGB":
            try:
                x_str = entry.get("d2p1_Attributes", {}).get("X")
                y_str = entry.get("d2p1_Attributes", {}).get("Y")
                z_str = entry.get("d2p1_Attributes", {}).get("Z")

                x = float(x_str)
                y = float(y_str)
                z = float(z_str)

                node.outputs[0].default_value = (x, y, z, 1.0)

            except Exception:
                debug_print(["native_nodes", "errors"], f"[Error] Failed to set ShaderNodeRGB {node_id} value: {e}")

        if blender_type == "ShaderNodeCombineXYZ":
            try:
                x_str = entry.get("d2p1_Attributes", {}).get("X")
                y_str = entry.get("d2p1_Attributes", {}).get("Y")
                z_str = entry.get("d2p1_Attributes", {}).get("Z")

                if x_str:
                    x = float(x_str)
                    node.inputs[0].default_value = x
                if y_str:
                    y = float(y_str)
                    node.inputs[1].default_value = y
                if z_str:
                    z = float(z_str)
                    node.inputs[3].default_value = z


            except Exception:
                debug_print(["native_nodes", "errors"], f"[Error] Failed to set ShaderNodeCombineXYZ {node_id} value: {e}")

        debug_print("native_nodes", f"[NodeCreated] node_id: {node_id} → Blender node name: {node.name}, label: {node.label}, location: {node.location}")

def check_sockets_against_expected(test_group, ng_data, node_type):

    debug_print(["nodegroup_creation", "sockets"], "Pretending to check sockets. Not actually doing anything, though...")
    #Proxy function.
    #When the migraine passes, check test_group's sockets against those expected in ng_data.
    #If same, True. Else, False.
    return test_group, True

def set_up_nodegroups(nodegroup_entries, node_tree, nodes_json, nodegroup_json_data, connections_list, template_name):

    for entry in nodegroup_entries:
        node = None
        node_id = entry.get("node_id")
        node_name = entry.get("Node_Name")
        node_type = entry.get("Node_Type")
        autohide = entry.get("autohide")
        is_pattern = entry.get("is_pattern")
        loc_raw = entry.get("Location", {})
        is_native = entry.get("Is_Native")

        param_name = entry.get("d2p1_Attributes", {}).get("ParameterName")
        param_true_false = entry.get("d2p1_Attributes", {}).get("Parameter")
        texture_guid = entry.get("d2p1_Attributes", {}).get("TextureGUID")
        #print(texture_guid)

        if "ShadowPassSwitchNode" in node_type and any(key in template_name for key in special_template_keys):
            print("Found a ShadowPassSwitchNode.")
            new_type = "ShadowPassSwitchNode_fine"
            print(f"Changed its type: {new_type}") ## now I need to update its nodegroup entries entry,
            node_type = new_type

        if is_pattern:
            debug_print("pattern", f"::::::::::: {node_id}/{node_name} is pattern")
        if is_native:
            debug_print("native_nodes", f"This node, {node_id}, node_type has the native node flag.")
        #debug_print("nodegroup_setup", f"Starting new nodegroup entry: {node_id} {node_type}")
        if node_name in node_id:
            if node_name == "":
                is_nodegroup = entry.get("Is_NodeGroup")
            else:
                #is_nodegroup = True
                debug_print("pattern", f"node_name is in node_id: {node_name} / {node_id}")
                is_pattern = True
                is_nodegroup = True
                debug_print("pattern", is_pattern)
        else:
            is_nodegroup = entry.get("Is_NodeGroup")

        if node_id in track_nodes:
            debug_print("track_nodes", entry)

        if node_name == "":
            node_name = node_type
        #print(node_id, node_name, is_pattern)
        if node_name in node_id and not "":
            loc = loc_raw

        elif is_pattern:
            loc = loc_raw
        elif node_name == "VT_Layers_4ch": ## placeholder - doesn't work if I use is_pattern for some reason.
            loc = loc_raw
        else:
            loc_raw = entry.get("Location", {})

            x = loc_raw.get("x", 0.0)
            y = loc_raw.get("y", 0.0)
            x = x*-1
            y = y*-1
            loc = (x, y)

        #print(loc)
        if node_type == "":
            #print(f"No node type found for {node_id}.")
            if node_name != "":
                #print(f"But it has a name: {node_name}.")
                node_type = node_name

                #print(f"So now it's node_type is {node_name}.")
            else:
                node_type = "Node_Type_Missing"
                node_name = "Node_Name_Missing"
                print("Missing node, no number, no name.")

        try:
            #print(node_type)
            if "Texture2DNode" in node_type:
                node_name = node_name
                #print(node_name)

            else:
                node_name = node_type

            if is_nodegroup is None or is_nodegroup is False:
#                for nodegroup_type in nodegroup_json_data.get(node_type, {}):
                if node_name == nodegroup_json_data.get(node_type):
                #if nodegroup_type == node_name:
                    debug_print("nodegroup_setup", f"Nodegroup entry found for {node_name}")
                    is_nodegroup = True
                    node_type = node_name

            if is_nodegroup is None or is_nodegroup is False:
                node_group = create_shell_nodegroup(node_id, nodes_json[node_id])
                debug_print("nodegroup_setup", f"Created shell nodegroup: {node_group}")
                created_groups[node_name] = node_group
            else:
                ng_data = nodegroup_json_data.get(node_type)

                if ng_data:
                    if node_id in track_nodes:
                        debug_print("track_nodes", f"Sending {node_name} / {node_id} to create nodegroup.")

                    if node_name in created_groups:
                        node_group = created_groups[node_name]
                    else:
                        if recreate_nodegroups or "Texture2D" in node_type or "VirtualTextureNode" in node_name:  #<-- automatically recreate texture and VT nodegroups
                            if node_name == "":
                                print(f"Why the hell is this node name still blank? Node data:", ng_data)

                            if recreate_nodegroups:
                                debug_print("nodegroup_setup", f"Recreate nodegroups is on. Creating all nodegroups fresh.")
                            node_group = create_nodegroup_from_ng_data(node_name, node_type, ng_data, entry.get("node_id"), connections_list)
                            created_groups[node_name] = node_group

                            if "Texture2D" in node_type:
                                debug_print("nodegroup_setup", f"Found texture nodegroup; adding to texture_data.")
                                texture_data[node_group] = entry # <---- Add them for image adding later.
                                texture_nodegroups.add(node_group)
                        else:
                            test_group = next((ng for ng in bpy.data.node_groups if ng.name == node_name), None)
                            if test_group:
                                check = check_sockets_against_expected(test_group, ng_data, node_type)
                                if check:
                                    node_group = test_group
                                    created_groups[node_name] = node_group
                                    debug_print("nodegroup_setup", f"Found node group: {node_group.name}. Using.")
                            else:
                                node_group = create_nodegroup_from_ng_data(node_name, node_type, ng_data, entry.get("node_id"), connections_list)
                                created_groups[node_name] = node_group
                else:
                    node_group = create_shell_nodegroup(node_id, nodes_json[node_id])
                    created_groups[node_name] = node_group
            debug_print("nodegroup_setup", f"About to make {entry} an instanced nodegroup")
            node = node_tree.nodes.new("ShaderNodeGroup")
            node.node_tree = node_group
            #if ng_data:
             #   autohide = ng_data.get("autohide", False)#  <-- haven't tested this is yet.
            if autohide:
                node.hide = True
            #node.color_tag = color_tag
            #print(f" Location for {node_id} is {loc}")
            node.location = loc
            node.name = f"[{node_id}][{node_type}]"
            node.label = f"[{node_id}][{node_type}]"
            node_instance_map[node_id] = node  # Track for later linking etc.
            #debug_print(["nodegroup_setup", "error"], f"Sending nodegroup {node_type} to get socket data...")
            node_data = nodes_json[node_id]
            if node_id in track_nodes:
                print#(f"{node_id}'s data, just before map socket ids to blender sockets: {node_data}")

            #print(f"About to send node {node_id} for socket mapping...")
            global_socket_map = map_socket_ids_to_blender_sockets(node_data, node, nodegroup_json_data, connections_list, node_tree, nodes_json)
            #debug_print("nodegroup_setup", f"Recorded nodegroup {node_id} to socket map")

        except Exception as e:
            print(f"nodegroup failure for {node_id}: {e}")
            #debug_print(["nodegroup_setup", "errors"], f"[Exception] Failed to instance nodegroup for {node_id}/{node_type}: {e}")
            return

def set_up_ng_blocks(ng_block_node_entries, nodes_json, nodegroup_json_data, connections_list, node_tree, pattern):

    if not ng_block_node_entries:
        return

    from collections import defaultdict
    ng_groups = set()
    ng_group_data = {}
    position_sums = defaultdict(lambda: [0.0, 0.0])
    counts = defaultdict(int)

    for entry in ng_block_node_entries:
        node = None
        node_id = entry.get("node_id")
        #print(f"Node in ng_block_node_entries: {node_id}")
        loc_raw = entry.get("Location", {})
        x = loc_raw.get("x", 0.0) * -1
        y = loc_raw.get("y", 0.0) * -1
        ng_block = entry.get("ng_block")
        ng_block_role = entry.get("ng_block_role")
        ng_block_state = entry.get("ng_block_state")
        is_pattern = entry.get("Is_Pattern")

        #print(f"Node ID: {node_id} / node block: {ng_block} / location: {loc_raw}")
        if ng_block not in ng_groups:
            if ng_block == None:
                print("ng_block is none")
            else:
                ng_groups.add(ng_block)
                #print(f"Added {ng_block} to ng_groups.")

        #print(f"node_id: {node_id}.")
#--- Location averaging
        position_sums[ng_block][0] += x
        position_sums[ng_block][1] += y
        counts[ng_block] += 1

    avg_position = {}

    for ng_block, (sum_x, sum_y) in position_sums.items():
        print(f"Getting location from the block for {ng_block}")
        count = counts[ng_block]
        if count > 0:
            avg_position[ng_block] = (sum_x / count, sum_y / count)
            ng_group_data["Location"] = avg_position
        else:
            print("Could not get average, using 0,0")
            avg_position[ng_block] = (0.0, 0.0)

    return ng_group_data

def add_default_values_to_ng(node_tree, node_map, nodegroup_entries, nodegroup_json_data, global_socket_map):

    for entry in nodegroup_entries:
        value_dict = {}
        param_keys = []
        node_id = entry["node_id"]
        node_type = entry["Node_Type"]
        instance = node_map.get(node_id)
        params = entry.get("d2p1_Attributes", {})

        for param in params:
            param_keys.append(param)
            for key in param_keys:
                if param == key:
                    value_dict[key] = entry.get("d2p1_Attributes", {}).get(key)

        if instance:
            if instance.inputs:
                input_sockets = {s for s in instance.inputs}
                for i, sock in enumerate(instance.inputs):
                    #if node_id == "3255":
                        #print(i, sock)
                    for idx, value in nodegroup_json_data.get(node_type, {}).get("sockets", {}).get("input_values", {}).items():
                        idx_int = int(idx)
                        if idx_int == i:
                            debug_print("default_values", f"Found socket index {i} in inputs values with {idx_int} // default value: {value}")#: {inputval}.")
                            sock.default_value = value

                    value = value_dict.get(sock.name)
                    if value:
                        if sock.default_value:
                            debug_print("default_values", f"Existing sock default value: {sock.default_value}")
                        sock.default_value = float(value)
                        debug_print("default_values", f"Found value ( {sock.default_value} ) for {sock.name} in the value_dict for node {node_id}/{node_type}")
                        #print(sock, value)
                    #params = entry.get("d2p1_Attributes", {})
uv_maps_added = set()

def exceptional_nodes(connections_list, template_name, node_tree, nodegroup_entries, uv_maps_added):

    to_socket_map = {conn["to_socket"]: conn for conn in connections_list}

    for node_id, node in node_instance_map.items():
        for sock in node.inputs:
            if node in uv_maps_added:
                break
            if sock.name == "UV":

                for socket_id, socket in global_socket_map[node_id].items():
                    if node_id in uv_maps_added:
                        break
                    if sock == socket:
                        #print(f"This socket {socket} has a connection in the global socket map.")
                        #print(f"Socket {socket_id} is a UV input socket.")
                        conn = to_socket_map.get(socket_id)
                        if conn:
                            #print(f"Socket id {socket_id} is a to socket already: {conn}.")
                            break

                    loc = node.location
                    from mathutils import Vector
                    offset = Vector((-200.0, 0.0))
                    uv_map_loc = loc + offset

                    uv_node = node_tree.nodes.new(type="ShaderNodeUVMap")
                    #uv_node.hide = True
                    uv_node.location = uv_map_loc
                    uv_out = uv_node.outputs[0]
                    node_tree.links.new(uv_out, sock)
                    uv_maps_added.add(node_id)

    for entry in nodegroup_entries:   ### maybe do this in reverse, from the linked socket? Find the linked socket id via the global map? Might be quicker on big nodetrees. ::
        entry_node_id = entry.get("node_id")
        nodetype = entry.get("Node_Type")
        nodename = entry.get("Node_Name")

        u_tile = entry.get("d2p1_Attributes", {}).get("UTiling")
        if u_tile:
            UTiling = float(u_tile)
            v_tile = entry.get("d2p1_Attributes", {}).get("VTiling")
            VTiling = float(v_tile)
            uv_index = entry.get("d2p1_Attributes", {}).get("UVIndex")

            if nodetype == "UVNode_vector" and u_tile:
                for node_id, node in node_instance_map.items():
                    if node_id == entry_node_id:
                        for i, sock in enumerate(node.inputs):
                            if sock.name == "UTiling":
                                sock.default_value = UTiling
                            if sock.name == "VTiling":
                                sock.default_value = VTiling
                            if uv_index != "0":
                                idx = int(uv_index)
                                if sock.is_linked: ## find the UV map attached to the UVNode
                                    other_node = sock.links[0].from_node
                                    if other_node.type == "UVMAP":
                                        #print(f"{node_id}")
                                        print(f"Other node: {other_node}")
                                        other_index = other_node.uv_map.index  ###---- is this even used? ::
                                        print(f"Other node uv map index: {other_index}")
                                        obj = bpy.context.active_object
                                        print("uv layers: {obj.data.uv_layers}")
                                        uv_map_names = [uv.name for uv in obj.data.uv_layers]
                                        print(f"UV map names: {uv_map_names}")
                                        if uv_map_names:
                                            other_node.uv_map = uv_map_names[idx] ## set it to the UV index given in the file

                    ##### do frame things here.
                            if uv_index:
                                idx = int(uv_index)
                                if sock.is_linked and sock.links[0].from_node.type == "UVMAP": ## find the UV map attached to the UVNode
                                    other_node = sock.links[0].from_node
                                    debug_print("UV_maps", f"Adding frame to UV map with index {idx}")
                                    location = other_node.location
                                    frame = node_tree.nodes.new("NodeFrame")  # <---- "bl_idname" for new nodes.
                                    frame.height = 130
                                    frame.width = 100
                                    offset = Vector((25.0, +40.0))
                                    frame.location = location + offset
                                    frame.label = "Index_" + str(idx)
                                    color = (1.0, 0.0, 0.0)
                                    frame.use_custom_color = True
                                    frame.color = (0.424043, 0.212141, 0.253039)
                                    frame.label_size = 18

        if nodetype == "ComponentMaskNode_W":
            mask_w_instance = node_instance_map.get(entry_node_id)

            if mask_w_instance is not None:
                #print("Found node:", mask_w_instance.name)
                for sock in mask_w_instance.inputs:
                    if sock.is_linked:
                        link = sock.links[0]   # usually one link for inputs
                        #print(link.from_node, link.from_socket)
                        sockname = link.from_socket.name

            #            if link.from_node.type == "REROUTE":
            #                print("This ComponentMaskW has input from a Reroute node.")
            #                test_node = link.from_node
            #                reroute_counter = 0
            #                def recursive_reroute_check(test_node, reroute_counter):
            #                    reroute_found = False
            #                    reroute_counter += 1
            #                    print(f"Number of times the recursive check has run: {reroute_counter}")
            #                    for sock in test_node.inputs:
            #                        print("Socket in test node being checked.")
            #                        if sock.is_linked:
            #                            print("Socket in test node is linked.")
            #                            link = sock.links[0]   # usually one link for inputs
            #                            if link:
            #                                print("Sock has link.")
            #                            print(link.from_node, link.from_socket)
            #                            if link.from_node.type == "REROUTE":
            #                                print("Sock's from_node is also a reroute.")
            #                                try:
            #                                    return link.from_node.outputs, True
            #                                except:
            #                                    print("Recursion failed.")
            #                            else:
            #                                print("Sock's from_node is not a reroute. Returning.")
            #                                return link.from_node.outputs, False
            #                        else:
            #                            print(f"The reroute inputting doesn't have a valid input connections of its own. Reroute node: {test_node}. Reroute jump failed for {mask_w_instance}")
#
            #                from_node, reroute_found = recursive_reroute_check(test_node, reroute_counter)
            #                if reroute_found:
            #                    from_node, reroute_found = recursive_reroute_check(test_node, reroute_counter)
                        def resolve_non_reroute(link):
                            """Follow reroutes backwards until a non-reroute node is found.
                            Returns (node, socket)."""
                            from_node = link.from_node
                            from_socket = link.from_socket

                            while from_node.type == "REROUTE":
                                # A reroute has exactly 1 input and 1 output socket
                                if not from_node.inputs[0].is_linked:
                                    # no further links, bail
                                    return None, None
                                # step backwards to the next link
                                link = from_node.inputs[0].links[0]
                                from_node = link.from_node
                                from_socket = link.from_socket

                            return from_node, from_socket

                        from_node, from_socket = resolve_non_reroute(link)
                        if from_node is None:
                            print("Dead reroute chain, nothing found")
                        else:
                            debug_print("W_redirect", f"Resolved upstream node: {from_node.name}, socket: {from_socket.name}")
                            sockname = from_socket.name
                            for output_socket in from_node.outputs:
                                #print(f"output socket found: {output_socket}.")
                                if output_socket.name == sockname + "_Alpha":
                                    debug_print("W_redirect", f"Found an output sock w alpha suffix: {output_socket.name}")
                                    #print(output_socket.name)
                                    try:
                                        node_tree.links.new(output_socket, sock)
                                    except Exception as e:
                                        debug_print("W_redirect", f"Failed to connect with alpha variant socket because {e}")

                                elif output_socket.name == "W":
                                    debug_print("W_redirect", f"Found an output sock with a W socket: {output_socket.name}")
                                    #print(output_socket.name)
                                    try:
                                        node_tree.links.new(output_socket, sock)
                                    except Exception as e:
                                        debug_print("W_redirect", f"Failed to connect with W socket because {e}")

                                elif output_socket.name == sockname + "_W":
                                        debug_print("W_redirect", f"Found an output sock with a W socket: {output_socket.name}")
                                        #print(output_socket.name)
                                        try:
                                            node_tree.links.new(output_socket, sock)
                                        except Exception as e:
                                            debug_print("W_redirect", f"Failed to connect with W socket because {e}")
            else:
                debug_print("W_redirect", "not w_mask_node.")
            #for node_id, node in node_instance_map.items():
#node_instance_map = {}  # key: node_id (int), value: actual Blender node instance
#global_socket_map = {} # global_socket_map[node_id][socket_id] = socket

def generate_pattern_nodegroup(pattern_entries, ng_group_data, nodegroup_json_data):
    from pprint import pprint
    #pprint(ng_group_data)
    pattern_node_entries = []
    for entry in pattern_entries:
        id = entry["node_id"]
        type = entry["Node_Name"]
        location = ng_group_data["Location"][id]

        node_entry = {
            "node_id": id,
            "Node_Name": type,
            "Node_Type": type,
            #"Is_Nodegroup": True,
            "Location": location,
            "autohide": False,
            "is_pattern": True
        }
        pattern_node_entries.append(node_entry)
    return pattern_node_entries

def log_missing_node(node_data):

    log_path = "F:\Python_Scripts\Blender Scripts\missing_nodes_from_template_gen.json"
    # Load existing data if file exists
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Check if Node_Type already exists in the list
    existing_types = {entry.get("Node_Type") for entry in existing_data}
    existing_ids = {entry.get("node_id") for entry in existing_data}
    should_log = False
    node_type = node_data.get("Node_Type")
    node_id = node_data.get("node_id")
    #print(f"Node ID: {node_id}, node type: {node_type} being tested as empty.")

    if node_type == "":
        if node_id not in existing_ids:
            print("No Node_Type found but new ID {node_id}. Recording anyway:")
            should_log = True
        else:
            print(f"Nodetype blank, but ID {node_id} is in existing IDs; skipping.")
    elif node_type not in existing_types:
        print("Logged missing node:", node_type)
        should_log = True

    if should_log:
        existing_data.append(node_data)
        with open(log_path, "w") as f:
            json.dump(existing_data, f, indent=2)
        print("Logged missing node:", node_data["Node_Type"])
    #else:
        #print("Node_Type already logged:", node_data["Node_Type"])

def find_socket_by_identifier_or_name(node, identifier_or_name, is_input=True):
    sockets = node.inputs if is_input else node.outputs
    for s in sockets:
        if s.identifier == identifier_or_name or s.name == identifier_or_name:
            return s
        #else:
        #    debug_print("sockets", f"[WARN] Socket '{identifier_or_name}' not found on node '{node.name}' ({'input' if is_input else 'output'})")
    return None

def create_nodegroup_from_ng_data(name, node_type, ng_data, node_id, connections_list):

    #print("Start of nodegroup from ng data")
    if node_id_labels == True:
        ng_name = "[" + node_id + "]" + name
    elif name == "":
        ng_name = node_type
    else:
        ng_name = name

    debug_print("nodegroup_creation", f"Creating {ng_name}")
    node_group = bpy.data.node_groups.new(ng_name, 'ShaderNodeTree')

    # === Color tag ===
    colour_str = ng_data.get("colour", "") or ng_data.get("color", "")
    if colour_str:
        colour_key = colour_str.strip().lower()
        try:
            node_group.color_tag = colour_key
        except:
            node_group.color_tag = COLOR_NAME_TO_TAG.get(colour_key, "NONE")

    # === Group input/output nodes ===
    group_input = node_group.nodes.new('NodeGroupInput')
    group_output = node_group.nodes.new('NodeGroupOutput')
    #print("about to do internal nodes")
    # === Internal node creation ===
    node_defs = ng_data.get("nodes", [])
    name_to_node = {}
    for node_def in node_defs:
        node_type = node_def.get("type")
        node_name = node_def.get("name")
        location = node_def.get("location", [0, 0])
        operation = node_def.get("operation", None)
        blend_type = node_def.get("blend_type", None)
        data_type = node_def.get("data_type", None)
        default_value = node_def.get("default_value", 0.0)
        label = node_def.get("label")
        param_t_f = node_def.get("param_true_false")
        guid = node_def.get("texture_guid")

############        :: set up for internal nodegroups
        int_nodegroup = node_def.get("is_nodegroup")

            ### create the new nodetree first, then instance it here.



        if node_name == "":
            node_name = node_type
        if label:
            debug_print("nodegroup_creation", f"Label found for {node_name} in {ng_name}")
############        :: set up for internal nodegroups

        try:
            if int_nodegroup:
                node_group = bpy.data.node_groups.new(ng_name, 'ShaderNodeTree')
                #but not really this line. Actually just figure out how to make it recursive, nodegroups in nodegroups. Would be very helpful.

##----------------
            node = node_group.nodes.new(type=node_type)
            node.location = location
            if operation and hasattr(node, "operation"):
                valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
                if operation in valid_ops:
                    node.operation = operation

            # Blend type enum
            if blend_type and hasattr(node, "blend_type"):
                blends = [item.identifier for item in node.bl_rna.properties["blend_type"].enum_items]
                if blend_type in blends:
                    node.blend_type = blend_type

            # Data type enum
            if data_type and hasattr(node, "data_type"):
                datas = [item.identifier for item in node.bl_rna.properties["data_type"].enum_items]
                if data_type in datas:
                    node.data_type = data_type

            if node_name == "":
                name_to_node[node_type] = node
            else:
                name_to_node[node_name] = node
            debug_print("nodegroup_creation", f"About to attempt default values for {ng_name}")
            if node_type == "ShaderNodeValue":
                #print("found value node")
                if default_value:
                    #print("Default value found for this node:")
                    #print(node_name)
                    #print(default_value)
                    try:
                        val = float(default_value)
                        node.outputs[0].default_value = val
                        debug_print(["nodegroup_creation", "default_values"], f"[Set] ShaderNodeValue {node_id} value set to {val}")
                    except ValueError:
                        debug_print(["native_nodes", "errors"], f"Warning: X value '{x_str}' is not a valid number.")

            try:
                for sock_name, val in node_def.get("default_values", {}).items():
                    debug_print("default_values", f"Node `{node_name}`: socket `{sock_name}`: default value `{val}`") #::::?
                    socket = find_socket_by_identifier_or_name(node, sock_name, is_input=True)
                    if not socket:
                        #print(f"socket not found by name or identifier for {node_name}, {sock_name}")
                        if node_type == "ShaderNodeValue":
                            socket = find_socket_by_identifier_or_name(node, sock_name, is_input=False)
                    if socket:
                        #print(f"Socket `{sock_name}` found on node `{node_name}`")
                        if not socket.is_linked and hasattr(socket, "default_value"):
                            try:
                                socket.default_value = val
                                #print(f"Set default value `{val}` on socket `{sock_name}` of node `{node_name}`")
                            except Exception as e:
                                debug_print(["nodegroup_creation", "sockets", "errors"], f"[WARN] Failed to set default on {node.name}.{socket.identifier}: {e}")
            except:
                print(f"Skipped default values for {node_id}, {node_type}.")
## labels from split name for image textures.
            if "ShaderNodeTexImage" in node_type:
                if " - " in name:
                    group, imagename = name.split(" - ", 1)
                    node.label = imagename

                    if param_t_f is False:
                        node.label = imagename + guid

                if label:
                    node.label = label

        except Exception as e:
            debug_print(["nodegroup_creation", "errors"], f"[Warning] Failed to create node {node_name}: {e}")
    #print("internal nodes done")
    # Center nodes around (0, 0) in the node group
    if name_to_node:
        xs = [node.location.x for node in name_to_node.values()]
        ys = [node.location.y for node in name_to_node.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Offset all internal nodes to center them at (0, 0)
        for node in name_to_node.values():
            node.location.x -= center_x
            node.location.y -= center_y

        # Place GroupInput to the left, centered vertically
        group_input.location = (-200 - (max_x - center_x), 0)
        # Place GroupOutput to the right, centered vertically
        group_output.location = (200 + (max_x - center_x), 0)
    else:
        # Fallback default position if no internal nodes
        group_input.location = (-500, 0)
        group_output.location = (500, 0)
    # Add GroupInput and GroupOutput to node lookup map
    name_to_node["GroupInput"] = group_input
    name_to_node["GroupOutput"] = group_output

    # === Parse links early to detect socket types for auto-inference ===
    inferred_socket_types = {}  # name: bl_idname
    for link in ng_data.get("links", []):
        if len(link) != 4:
            continue
        from_node, from_sock, to_node, to_sock = link
        # Infer input socket type (GroupInput)
        if from_node == "GroupInput" and to_node in name_to_node:
            target_node = name_to_node[to_node]
            target_socket = find_socket_by_identifier_or_name(target_node, to_sock, is_input=True)
            if target_socket:
                inferred_socket_types[from_sock] = target_socket.bl_idname
        # Infer output socket type (GroupOutput)
        if to_node == "GroupOutput" and from_node in name_to_node:
            source_node = name_to_node[from_node]
            source_socket = find_socket_by_identifier_or_name(source_node, from_sock, is_input=False)
            if source_socket:
                inferred_socket_types[to_sock] = source_socket.bl_idname
    debug_print(["nodegroup_creation", "sockets"], f"starting interface socket creation")
    #print("Parsed links early to detect socket types.")
    # === Interface socket creation ===
    socket_map = {}
    for direction, in_out, group_node in [
        ("inputs", "INPUT", group_input),
        ("outputs", "OUTPUT", group_output),
    ]:
        socket_defs = ng_data.get("sockets", {}).get(direction, {})
        #print("Added input and output sockets to interface.")
        for idx_str, sock_def in socket_defs.items():
            #print(socket_defs)
            if isinstance(sock_def, list):
                #print(socket_defs)
                sock_name, sock_type = sock_def
                if sock_type == "NodeSocketFloatFactor":
                    sock_type = "NodeSocketFloat"
                    debug_print("sockets", f"Corrected sock_type to: {sock_type}")
            else:
                sock_name = sock_def
                #print(f"sock def: {sock_def}")
                if sock_name == "NodeSocketFloatFactor":
                    sock_type = "NodeSocketFloat"
                    debug_print("sockets", f"Corrected sock_type to: {sock_type}")
                elif direction == "inputs":
                    input_types = ng_data.get("input_types", {})
                    if input_types:
                        #print(f"Input types found: {input_types}")
                        for type_idx_str, inputtype in input_types.items():
                            #print(f"{idx_str} // {type_idx_str}")
                            if type_idx_str in idx_str:
                                sock_type = inputtype
                                continue
                            else:
                                #print(f"No input types found.")
                                continue
                    else:
                        sock_type = inferred_socket_types.get(sock_name, 'NodeSocketFloat')

                elif direction == "outputs":
                    output_types = ng_data.get("output_types", {})
                    if output_types:
                        #print(f"output types found: {output_types}")
                        for type_idx_str, outputtype in output_types.items():
                            #print(f"{idx_str} // {type_idx_str}")
                            if type_idx_str in idx_str:
                                sock_type = outputtype
                                continue
                            else:
                                #print(f"No output types found.")
                                continue
                    else:
                        sock_type = inferred_socket_types.get(sock_name, 'NodeSocketFloat')
                else:
                    sock_type = inferred_socket_types.get(sock_name, 'NodeSocketFloat')

            if sock_type == "NodeSocketFloatFactor":
                sock_type = "NodeSocketFloat"

            node_group.interface.new_socket(name=sock_name, in_out=in_out, socket_type=sock_type)

    debug_print("nodegroup_creation", "About to create links for internal nodes")
    # === Create links ===
    for link in ng_data.get("links", []):
        if len(link) != 4:
            debug_print(["links", "errors"], f"[Warning] Invalid link format: {link}")
            continue
        #print(f"link:: {link}")

        from_node_name, from_sock_id, to_node_name, to_sock_id = link
        from_node = name_to_node.get(from_node_name)
        to_node = name_to_node.get(to_node_name)
        #print(f"from_node_name, from_sock_id, to_node_name, to_sock_id: {from_node_name}, {from_sock_id}, {to_node_name}, {to_sock_id}")

        if not from_node or not to_node:
            debug_print(["links", "errors"], f"[Warning] Missing node in link: {link} on {name_to_node}")
            continue

        from_socket = find_socket_by_identifier_or_name(from_node, from_sock_id, is_input=False)
        to_socket = find_socket_by_identifier_or_name(to_node, to_sock_id, is_input=True)
        if not from_socket or not to_socket:
            debug_print(["links", "errors"], f"[Warning] Could not find sockets in link: {link}")
            continue

        try:
            node_group.links.new(from_socket, to_socket)
        except Exception as e:
            debug_print(["links", "errors"], f"[Warning] Failed to create link {link}: {e}")

    debug_print("nodegroup_setup", "returning nodegroup")
    return node_group

def add_images_to_texture_nodegroups(texture_nodegroups, texture_data, mat):

    """
    {'node_id': '84', 'Node_Type': 'Texture2DNode_color',
    'Node_Name': 'Texture2D - SKIN_Shared_Dirt_Body_MSK',
     'd2p1_Attributes': {'Parameter': 'false', 'IgnoreTexelDensity': 'false',
     'IsLuminance': 'false', 'MipLevel': '-1', 'TextureAddressMode': 'Wrap', 'TextureCompression': 'Default',
     'TextureFilterOverride': 'Default', 'TextureGUID': '7c850182-9bbc-bdee-22f1-706d81d4d2cb'},
    'Location': {'x': 9070.98, 'y': -3002.44}, 'Is_NodeGroup': True}
    """
    #print(texture_data)
    #print(len(texture_nodegroups))
    #print(len(texture_data))
    for nodegroup in texture_nodegroups:

        #print(f"[START]       Nodegroup in the 'add images function (nodegroup.name): {nodegroup.name}")
        #for datapoint in texture_data[nodegroup]["d2p1_Attributes"]:
            #print(datapoint)
        uuid = texture_data[nodegroup]["d2p1_Attributes"].get("TextureGUID", "")
        #print(f"UUID: {uuid}")
        node_name = texture_data[nodegroup]["Node_Name"]
        #print(f"FROM DATA: node_name from texture data: {node_name}")
#DetailNormalMap - DT_Skin_A_NM <nodetree name?
#[1233][Texture2DNode_vector] < instance name

        #print(texture_data[nodegroup])
        if uuid:
            ### currently accesses the db repeatedly. should be able to make this better by batching the uuids to be looked up.
            conn = sqlite3.connect(SQLITE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT LocalPath, SRGB, Template FROM Textures WHERE UUID = ?", (uuid,))
            found_texture = cursor.fetchone()

            if found_texture:
                #print(f"[DB]     Found texture by UUID: {uuid}")
                #print(f"nodegroup name: {nodegroup.name}")#", nodegroup label: {nodegroup.label}")
                #continue
                local_path, srgb_raw, label = found_texture
                srgb_flag = str(srgb_raw).strip().lower() == "true"
                color_space = "sRGB" if srgb_flag else "Non-Color"
                #old_tree = nodegroup
                #nodegroup = nodegroup.nodetree
                #new_tree = nodegroup.copy()   # duplicate datablock
                #nodegroup = new_tree          # reassign this node to point at the copy
                #print(old_tree, nodegroup)
                #print(f"New nodegroup: {nodegroup}")
                node = next((n for n in nodegroup.nodes if n.type == "TEX_IMAGE"), None)
                if node:
                    old_node = node
                    #print(f"node found: {node.name}")
                if node.image:
                    #print("Image already present.")
                    #if node.image.path == local_path, do not make new. ::todo
                    node.image = node.image.copy()

                img = bpy.data.images.load(local_path, check_existing=True)
                #if img:
                    #print(f"Found image, {img}")
                #else:
                    #print("No image found.")
                node.image = img
                node.image.colorspace_settings.name = color_space
                debug_print("image_textures", f"  [OK] Set Image '{label}' = {os.path.basename(local_path)} ({color_space})")
                #print(f"  [OK] Set Image '{label}' = {os.path.basename(local_path)} ({color_space})")
                #print(dir(node.image))
                #print(f"[ENDING]        Tex image added, nodegroup: {nodegroup}, nodegroup name: {nodegroup.name}, node: {node}, node.image: {node.image}")
                #if old_node == node:
                #    print("old_node == node")
                #else:
                #    print("old_node is different to node...")

        else:
            print("INFO: NO UUID FOUND.")

        instances = []

        for node in mat.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree == nodegroup:
                instances.append(node)

        #for inst in instances:
            #print(inst.name, inst.bl_label, inst.location)
            #loc = inst.location
            #inst.location = loc + loc


# === Helper to build cleaned connections list ===
def build_connections_list(connections_json):

    connections_list = []
    for conn_id, conn_data in connections_json.items():
        connections_list.append({
            "connection_id": conn_id,
            "from_socket": conn_data.get("From_Socket"),
            "to_socket": conn_data.get("To_Socket"),
        })

    debug_print("links", "Returning connections list:")
    return connections_list

# === Create master material and attach ===
def create_material_and_instance(template_name, blendernative_entries, nodegroup_entries, ng_block_node_entries, pattern_entries, nodes_json, nodegroup_json_data, connections_list, connections_json):

    ng_group_data = {}
    obj = bpy.context.active_object
    print()
    debug_print("errors", f"Printing Error log...")

    if not obj or obj.type != 'MESH':
        raise RuntimeError("Select a mesh object")

    obj = bpy.context.active_object

    mat = bpy.data.materials.get(template_name)
    if not mat:
        mat = bpy.data.materials.new(template_name)
        mat.use_nodes = True
        obj.data.materials.append(mat)

    node_tree = mat.node_tree
        # FULL CLEAR
    node_tree.nodes.clear()
    node_tree.links.clear()
    nodes = mat.node_tree.nodes
    obj.active_material = mat

    get_correct_native_nodes(blendernative_entries, node_tree, nodes_json, nodegroup_json_data, connections_list)
    set_up_nodegroups(nodegroup_entries, node_tree, nodes_json, nodegroup_json_data, connections_list, template_name)

    if texture_nodegroups:
        add_images_to_texture_nodegroups(texture_nodegroups, texture_data, mat)

    ng_group_data = set_up_ng_blocks(ng_block_node_entries, nodes_json, nodegroup_json_data, connections_list, node_tree, pattern_entries)
    pattern_node_entries = generate_pattern_nodegroup(pattern_entries, ng_group_data, nodegroup_json_data)
    set_up_nodegroups(pattern_node_entries, node_tree, nodes_json, nodegroup_json_data, connections_list, template_name) # run again with contained node locations already found
    missed_sockets = create_blender_links(node_tree, connections_list, node_instance_map, global_socket_map, used_connectors)
    add_default_values_to_ng(node_tree, node_instance_map, nodegroup_entries, nodegroup_json_data, global_socket_map)

    return node_tree, missed_sockets, mat

def remove_temp_nodes(node, node_tree, temp_nodes):
    for node in temp_nodes: #------------------- Note: If reroutes start failing, move this to after links are created.
        node_tree.nodes.remove(node)
    temp_nodes.clear()

def create_blender_links(master_tree, connections_list, node_instance_map, global_socket_map, used_connectors):

    missed_sockets = []
    socket_to_node = {
        socket_id: node_id
        for node_id, sockets in global_socket_map.items()
        for socket_id in sockets
    }

    for conn in connections_list:
        from_sid = conn["from_socket"]
        to_sid = conn["to_socket"]

        from_nid = socket_to_node.get(from_sid)
        to_nid = socket_to_node.get(to_sid)
        if not from_nid or not to_nid:
           #print("Socket is not from_nid or to_nid")
            continue

        from_socket = global_socket_map[from_nid].get(from_sid)
        to_socket = global_socket_map[to_nid].get(to_sid)
        if not from_socket or not to_socket:
            #print("from socket or to socket missing")
            continue
        try:
            master_tree.links.new(from_socket, to_socket)
        except Exception as e:
            print(f"[Exception] Failed to make connection for {from_sid} and/or {to_sid}: {e}")

        actual_link_exists = any(
            l.from_socket == from_socket and l.to_socket == to_socket
            for l in master_tree.links
        )
        if not actual_link_exists:
            #print(f"[Warning] Link did NOT register in Blender: {from_nid}:{from_sid} ({from_socket.name}) ({from_socket.type}) > {to_nid}:{to_sid} ({to_socket.name}, ({to_socket.type}))")
            missed_sockets.append(tuple((from_nid, from_sid, to_nid, to_sid)))
            from pprint import pprint

    return missed_sockets

def try_failed_links_again(node_tree, missed_sockets, global_socket_map):
    #This mostly exists because reroutes change when their type changes, and all this mess was to fix that. It worked, but god was it a painful afternoon.
    socket_holding = []
    socket_identifiers = {}
    node_entity = None
    node_name_dict = {}

    for node_id, sockets in global_socket_map.items():
        socket_identifiers[node_id] = {}
        for socket_id, socket in sockets.items():
            if socket:
                #print(f"socket identifiers: {socket.identifier}")
                if socket.identifier == "":
                    #print(f"socket name instead: {socket.name}")
                    socket_identifiers[node_id][socket_id] = socket.name
                else:
                    socket_identifiers[node_id][socket_id] = socket.identifier
                node_entity = socket.node
                node_name = node_entity.name
                node = node_tree.nodes.get(node_name)
                node_name_dict[socket_id] = node.name
            else:
                debug_print("sockets", f"Sockets for {node_id} do not exist.")

    for from_nid, from_sid, to_nid, to_sid in missed_sockets:
        from_socket_id = None
        to_sock_id = None

#node names
        to_nodename = node_name_dict[to_sid]
        #print(f"To node from node_name_dict: {to_nid}")
        from_nodename = node_name_dict[from_sid]
# node objects
        from_node = node_tree.nodes.get(from_nodename)
        to_node = node_tree.nodes.get(to_nodename)

        #print(f"To node {to_nid} // to sock ID: {to_sid}: {to_node}")
        to_sock_id = socket_identifiers[to_nid][to_sid]
        #print(f"From node {from_nid} // to sock ID: {from_sid}: {from_node}")
        from_sock_id = socket_identifiers[from_nid][from_sid]

        if to_nid in socket_identifiers and to_sid in socket_identifiers[to_nid]:
            #print(f"to_sid {to_sid} in socket identifiers for node {to_nid}")
            to_sock_id = socket_identifiers[to_nid][to_sid]
        if from_nid in socket_identifiers and from_sid in socket_identifiers[from_nid]:
            #print(f"from_sid {from_sid} in socket identifiers for node {from_nid}")
            from_sock_id = socket_identifiers[from_nid][from_sid]
        else:
            #print(f"No from_sid {from_sid} in socket identifiers for node {from_nid}")
            debug_print("sockets", f"No to_sid {to_sid} in socket identifiers for node {to_nid}")

        if to_sock_id:
            for s in to_node.inputs:
                #print(f"Checking socket: {s}, identifier: {s.identifier}, target: {to_sock_id}")
                if s.identifier == to_sock_id:
                    to_socket = s
                    #print(f"from_socket matches: {to_socket}, {s.identifier}")
                    break

        if from_sock_id:
            for s in from_node.outputs:
                #print(f"Checking socket: {s}, identifier: {s.identifier}, target: {from_sock_id}")
                if s.identifier == from_sock_id:
                    from_socket = s
                    #print(f"from_socket matches: {from_socket}, {s.identifier}")
                    break

        try:
            node_tree.links.new(from_socket, to_socket)
            #print(f"Connected: {from_nid}:{from_sock_id} → {to_nid}:{to_sock_id}")
        except Exception as e:
            #print(f"Failed to connect: {from_nid}:{from_sock_id} → {to_nid}:{to_sock_id} because {e}")
            debug_print("errors", f"Failed to connect: {from_nid}:{from_sid} → {to_nid}:{to_sid} because {e}")
        #bpy.context.view_layer.update()

    mat_output = None
    for node in node_tree.nodes:

        if node.name == "Material Output":
            mat_output = node
            #print(f"Node {node} claims to be material output.")
        if not mat_output or mat_output is None:
            #print("No mat_output yet. Generating:")
            mat_output = node_tree.nodes.new("ShaderNodeOutputMaterial")
            #print(f"Node {mat_output} claims to be material output.")
        if mat_output:
            matnode = next((n for n in node_tree.nodes if n.type == 'GROUP' and n.node_tree and "MaterialNode" in n.name), None)
            if not matnode:
                debug_print("errors", "No materialnode found...")
            else:
                from mathutils import Vector
                matnode_location = matnode.location
                mat_output.location = matnode_location + Vector((250.0, 0.0))
                node_tree.links.new(matnode.outputs[0], mat_output.inputs[0])
        else:
            print("Material Output not existing or creating. Look into this...")

def run(template_data):

    print("\n" * 2)
    print("\n" + "="*40)
    print("=== Template generation started at", datetime.now(), "===")
    print("="*40 + "\n")
    print("\n" * 2)

    template_name, MAIN_JSON_PATH = get_template_name(template_data)

    # === LOAD JSON NODES ===
    try:
        with open(MAIN_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            nodes_json = data.get("Nodes", {})
            connections = data.get("Connections", {})
    except Exception as e:
        print("Error trying to load main JSON file:", e)

    try:
        with open(NODEGROUP_JSON_PATH, 'r', encoding='utf-8') as f:
            nodegroup_json_data = json.load(f)
    except Exception as e:
        print("Error trying to load nodegroup JSON file:", e)

    connections_list = build_connections_list(data.get("Connections", {}))
    clear_all_ng_from_file()
    blendernative_entries, nodegroup_entries, ng_block_node_entries, pattern_entries = get_node_sets(nodes_json, nodegroup_json_data)
    node_tree, missed_sockets, material = create_material_and_instance(template_name, blendernative_entries, nodegroup_entries, ng_block_node_entries, pattern_entries, nodes_json, nodegroup_json_data, connections_list, connections)
    remove_temp_nodes(node_instance_map, node_tree, temp_nodes)
    try_failed_links_again(node_tree, missed_sockets, global_socket_map)
    exceptional_nodes(connections_list, template_name, node_tree, nodegroup_entries, uv_maps_added)
    debug_print("UV_maps", f"Added {len(uv_maps_added)} UV Map nodes to the material.")
    #print(f"Added {len(node_tree.nodes) -


    print("Template generated.")
    print()
    return material

# CLI entry point
if __name__ == "__main__":

    # When running directly, use the global default
    run(sourcefile, force_new_template)
