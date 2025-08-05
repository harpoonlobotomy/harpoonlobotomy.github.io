##--- Current vers in blender.
## Need to fix shell nodegroups' socket allocations, and fix autohide by nodegroup data.
# potentially needlessly resorts the connections data. Seems to actually be okay as it was now, have fixed enough other things.
# 5/8/25 - setting up for the nodegroup-block node replacement + wiring setup. Doing it separately from the regular nodegroups.

## Want to edit how it interprets names in the exported nodegroups; want to add a [type] suffix (optional) to be able to specify socket type if desired.
## Currently neither nodegroups or native nodes record socket type. Probably should...
## Also, currently the nodegroup detection relies on nodegroup flag, not presence in the nodegroup file. Could change it to make nodegen key set and compare against that, instead of requiring reprocessing of input files

# Written for Blender vers 4.3
#harpoonlobotomy

import bpy
import json
import os
import sys
from collections import Counter
from collections import defaultdict
import importlib
import re

counts = Counter()

template_name = "test_temp_gen_redux"
delete_nodes = False
# === CONFIG: Path to the new JSON node structure ===
MAIN_JSON_PATH = r"F:\test\wrapper_script_test_output6\stage_5_tmp_CHAR_BASE_VT.json"
#MAIN_JSON_PATH = r"F:\test\wrapper_script_test_output6\stage_5_tmp_BASE_Tile_VT.json"


node_instance_map = {}  # key: node_id (int), value: actual Blender node instance
global_socket_map = {} # global_socket_map[node_id][socket_id] = socket

NODEGROUP_JSON_PATH = r"F:\Python_Scripts\Blender Scripts\frame_exported_nodegroups_4.json"

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
    "nodegroup_connectors": False
}

used_connectors = set()
temp_nodes = set()
created_groups = {}

# === LOAD JSON NODES ===
with open(MAIN_JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    nodes_json = data.get("Nodes", {})
    connections = data.get("Connections", {})
with open(NODEGROUP_JSON_PATH, 'r', encoding='utf-8') as f:
    nodegroup_json_data = json.load(f)

def debug_print(groups, *args, **kwargs): #             ---------- debug_print("nodegroup_creation", "Setting up node:")
    if isinstance(groups, str):
        groups = [groups]
    if any(DEBUG_GROUPS.get(g, False) for g in groups):
        print(*args, **kwargs)

def clear_all_ng_from_file(): # === delete all nodegroups - remove when testing is done ===
    if delete_nodes == True:
        for node_group in list(bpy.data.node_groups):  # Make a copy of the list to avoid modifying the list while iterating
            bpy.data.node_groups.remove(node_group)
        debug_print("other", "Cleared existing nodegroups from file.")

def normalize_name(name):
    if not name:
        return ""
    return name.lower().replace(" ", "").removeprefix("mat")

def set_reroute_type(node_instance, node_tree, node_type):
    reroute = node_instance

    if node_type == "PassthroughNode_color":
#        print(f"Reroute is color type {node_type}")
        return
    elif node_type == "PassthroughNode_vector":
#        print(f"Reroute is vector type {node_type}")
        vector_node = node_tree.nodes.new("ShaderNodeCombineXYZ")
        temp_nodes.add(vector_node)
        node_tree.links.new(vector_node.outputs[0], reroute.inputs[0])

    else:  # PassthroughNode (assumed float)
        value_node = node_tree.nodes.new("ShaderNodeValue")
#        print(f"Reroute is scalar type {node_type}")
        temp_nodes.add(value_node)
        node_tree.links.new(value_node.outputs[0], reroute.inputs[0])

def map_native_connectors(node_type, node_id, node_instance, connectors_json, connectionsock, node_tree):
    mapping = {}

    if "PassthroughNode" in node_type:
        set_reroute_type(node_instance,  node_tree, node_type)

    # Create a lookup for actual socket objects
    input_sockets = list(node_instance.inputs)
    output_sockets = list(node_instance.outputs)

    from_id = [conn.get("from_socket") for conn in connections_list]
    to_id = [conn.get("to_socket") for conn in connections_list]


    if node_id == "98":
        print(f"to Id 98, input sockets: {input_sockets}, {to_id}")

    for conn in connectors_json:
        socket_id = conn.get("Socket_Id")

        if socket_id in from_id:
    #        print(f"From_Socket == Socket_Id: {socket_id}")
            used_connectors.add(socket_id)
        elif socket_id in to_id:
    #        print(f"To_Socket == Socket_Id: {socket_id}")
            used_connectors.add(socket_id)

    try:
        for conn in connectors_json:
            real_sockets = []
            socket_id = conn.get("Socket_Id")
            if socket_id not in used_connectors:
        #        print(f"Socket ID {socket_id} not used")
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
                print(f"[Warning] Missing index for connector: {conn}")
                if index is None:
                    elif len(relevant_sockets) == 1:
                            for sock in relevant_sockets:
                                mapping[conn["Socket_Id"]] = sock
                            print(f"Only one socket for {node_id}")

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

def map_connections(connectionsock, connectors_json, sockets_internal, node_id, node_instance, blender_sockets, nodegroup_in_out, node_type, connections_list, used_connectors):
    mapping = {}
    node_id = node_id

    valid_input_sockets = {s.name for s in node_instance.inputs}
    valid_output_sockets = {s.name for s in node_instance.outputs}

    if node_id == "22":
        print(set(valid_output_sockets))

    input_sockets = list(node_instance.inputs)
    output_sockets = list(node_instance.outputs)
    if node_id == "22":
        print(f"Output Sockets: {output_sockets}, ()")

## -----------   Get 'used_connectors' set first -------------
    from_id = [conn.get("from_socket") for conn in connections_list]
    to_id = [conn.get("to_socket") for conn in connections_list]

    print(f"{output_sockets} : {from_id}")

    for conn in connectors_json:
        key = None
        socket_id = conn.get("Socket_Id")

        if socket_id in from_id:
            used_connectors.add(socket_id)
        elif socket_id in to_id:
            used_connectors.add(socket_id)

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
            conn_name = conn.get("Conn_Name")
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
                        break

            elif conn_name:
                for sock in blender_sockets:
                    if normalize_name(sock.name) == normalize_name(conn_name):
                        socket = sock
                        break

            elif len(valid_sockets) == 1:
                    for sock in relevant_sockets:
                        socket = sock
                    print(f"Only one socket for {node_id}")


            else:
                print(f"Skipping unused or missing socket: {conn.get('Socket_Id')} - not present on this node, {node_id}")

            if socket_id is None:
                debug_print(["sockets", "errors"], f"[Warning] Connector missing Socket_Id: {conn}")

            if socket != None:
                mapping[socket_id] = socket

    except Exception as e:
        print(f"[ERROR] map_connections failed for node {node_id}: {e}")
        import traceback
        traceback.print_exc()
    return mapping

def map_socket_ids_to_blender_sockets(nodes_json, node_instance, nodegroup_json_data, connections_list, node_tree):

    node_id = nodes_json["Node_Id"]
    node_type = nodes_json["Node_Type"]
    from_sock = [conn.get("from_socket") for conn in connections_list]
    to_sock = [conn.get("from_socket") for conn in connections_list]
    inputs_internal = [ic for ic in nodes_json.get("Internal_Connectors", []) if ic.get("Socket", "").startswith("m_Input")]
    outputs_internal = [ic for ic in nodes_json.get("Internal_Connectors", []) if ic.get("Socket", "").startswith("m_Output")]
    is_native = "Blender_type" in nodes_json

    if is_native:
        inputs = map_native_connectors(node_type, node_id, node_instance, nodes_json.get("m_Inputs", {}).get("Connectors", []), to_sock, node_tree)
        outputs = map_native_connectors(node_type, node_id, node_instance, nodes_json.get("m_Outputs", {}).get("Connectors", []), from_sock, node_tree)
    else:
        inputs = map_connections(to_sock, nodes_json.get("m_Inputs", {}).get("Connectors", []), inputs_internal, node_id, node_instance, node_instance.inputs, nodegroup_json_data.get("inputs"), node_type, connections_list, used_connectors)
        outputs = map_connections(from_sock, nodes_json.get("m_Outputs", {}).get("Connectors", []), outputs_internal, node_id, node_instance, node_instance.outputs, nodegroup_json_data.get("outputs"), node_type, connections_list, used_connectors)

    if node_id not in global_socket_map:
        global_socket_map[node_id] = {}

    for socket_id, socket in inputs.items():
        global_socket_map[node_id][socket_id] = socket
    for socket_id, socket in outputs.items():
        global_socket_map[node_id][socket_id] = socket
    existing_entry = global_socket_map.get(node_id)

def create_shell_nodegroup(group_name, nodes_json): #----   Is just a hollow placeholder if node not found in native or nodegroup documents
#                                                    ---- Should have the required number of sockets; seems to now.
    outputs = nodes_json.get("m_Outputs", {})
    inputs = nodes_json.get("m_Inputs", {})

    print("Checking outputs for", group_name, ":", outputs)
    for conn in outputs.get("Connectors", []):
        print(f"{conn}")

    # Create new ShaderNodeTree
    nodegroup = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    nodegroup.use_fake_user = True
    nodegroup["label"] = group_name

    # Add Group Input/Output nodes
    group_input = nodegroup.nodes.new('NodeGroupInput')
    group_input.location = (-350, 0)
    group_input.label = "Group Input"

    group_output = nodegroup.nodes.new('NodeGroupOutput')
    group_output.location = (350, 0)
    group_output.label = "Group Output"

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
        print("literally anything")
        sock_name = conn.get("Conn_Name") or conn.get("Conn_name_2") or "Output"
        if sock_name and sock_name not in nodegroup.interface.items_tree:
            nodegroup.interface.new_socket(
                name=sock_name,
                in_out='OUTPUT',
                socket_type='NodeSocketFloat'
            )

    return nodegroup

def get_node_sets(nodes_json):
    blendernative_entries = []
    nodegroup_entries = []
    ng_block = []
    optional_keys = [
        "Node_Type", "Blender_type", "Data_Type", "Blend_Type", "Node_Name",
        "Blender_Operation", "d2p1_Attributes", "Location", "Autohide", "Is_NodeGroup"]

    for node_id, node_data in nodes_json.items():
        node_entry = {"node_id": node_id}
        for key in optional_keys:
            if key in node_data:
                node_entry[key] = node_data[key]
        if "Blender_type" in node_data:
            blendernative_entries.append(node_entry)
          #  print(f"native node {node_id}")
            debug_print("native_nodes", f"Native node found: {node_id}")
        elif "Is_NodeGroup" in node_data:
            nodegroup_entries.append(node_entry)
            debug_print("nodegroup_setup", f"Nodegroup found: {node_id}")
          #  print(f"nodegroup {node_id}")
        elif "ng_block" in node_data:
            ng_block_entries.append(node_entry)
            debug_print("ng_block_setup", f"NG block component found: {node_id}")


            nodegroup_entries.append(node_entry) ##=== make a new one inside here.
            print(f"Not nodegroup or native: {node_id}")

    return blendernative_entries, nodegroup_entries

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
        #    print(f"Attempting to create node {node_id}, a {blender_type} node.")
            debug_print("native_nodes", f"Attempting to create node {node_id}, a {blender_type} node.")

            node = node_tree.nodes.new(blender_type)
            node_instance_map[node_id] = node
            #counts["Added to node_instance_map"] += 1
            node.location = loc

            # Operation enum
            if op and hasattr(node, "operation"):
                valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
                if op in valid_ops:
                    node.operation = op

            # Data type enum
            if datatype and hasattr(node, "data_type"):
                datas = [item.identifier for item in node.bl_rna.properties["data_type"].enum_items]
                if datatype in datas:
                    node.data_type = datatype

            # Blend type enum
            if blendtype and hasattr(node, "blend_type"):
                blends = [item.identifier for item in node.bl_rna.properties["blend_type"].enum_items]
                if blendtype in blends:
                    node.blend_type = blendtype

            node_data = nodes_json[node_id]
            map_socket_ids_to_blender_sockets(node_data, node, nodegroup_json_data, connections_list, node_tree)

        except Exception as e:
            print(f"native node failure for {node_id}")
            debug_print(["native_nodes", "errors"], f"[Warning] Could not create node '{blender_type}': {e}")

        #    print(f"Location set to: {loc}, has operation {op}, is datatype: {datatype}, blendtype is {blendtype}")#" - and might have autohide? ..{autohide}..")

        if param_name is not None:
            param_label = str(param_name)
            node.label = param_label

        if param_name is None:
            param_label = str(node_name)
            node.label = param_label

        node.label = f"[{node_id}][{node_type}]" #----------------- debug node.label delete later

        if autohide:
            node.hide = True

        val = float(1)
        valvec = (1, 1, 1)
        if blendtype and hasattr(node, "blend_type"):
        #    print("Blendtype")
            for sock in node.inputs:  # sock is each input socket
                #print(f"{sock.identifier}//{sock.name}")
                #print Check by name or identifier
                if sock.identifier == "Factor_Float":  # or sock.identifier if you prefer
                    # Only set default_value if not linked
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
        debug_print("native_nodes", f"[NodeCreated] node_id: {node_id} → Blender node name: {node.name}, label: {node.label}, location: {node.location}")

def set_up_nodegroups(nodegroup_entries, node_tree, nodes_json, nodegroup_json_data, connections_list):

    for entry in nodegroup_entries:
        node = None
        node_id = entry.get("node_id")
        node_name = entry.get("Node_Name")
        node_type = entry.get("Node_Type")
        autohide = entry.get("autohide")
        debug_print("nodegroup_setup", f"Starting new nodegroup entry: {node_id} {node_type}")
        is_nodegroup = entry.get("Is_NodeGroup")
        loc_raw = entry.get("Location", {})
        param_name = entry.get("d2p1_Attributes", {}).get("ParameterName")

        x = loc_raw.get("x", 0.0)
        y = loc_raw.get("y", 0.0)
        x = x*-1
        y = y*-1
        loc = (x, y)

        try:
            if node_type == "Texture2DNode_color":
                node_name = node_name
            else:
                node_name = node_type

            if is_nodegroup is None:
                node_data = entry
                print(f"Not a real nodegroup: {node_id}//{node_name}, {node_data}")
                node_group = create_shell_nodegroup(node_id, nodes_json[node_id])
                created_groups[node_name] = node_group
            else:
                ng_data = nodegroup_json_data.get(node_type)

                if ng_data:
                    if node_name in created_groups:
                        node_group = created_groups[node_name]
                    else:
                        node_group = create_nodegroup_from_ng_data(node_name, node_type, ng_data, entry.get("node_id"), connections_list)
                        created_groups[node_name] = node_group

            node = node_tree.nodes.new("ShaderNodeGroup")
            node.node_tree = node_group
            autohide = ng_data.get("autohide", False)
            if autohide:
                node.hide = True
            #node.color_tag = color_tag
            node.location = loc
            node.name = f"[{node_id}][{node_type}]"
            node_instance_map[node_id] = node  # Track for later linking etc.
            debug_print(["nodegroup_setup", "error"], f"Sending nodegroup {node_type} to get socket data...")
            node_data = nodes_json[node_id]
            map_socket_ids_to_blender_sockets(node_data, node, nodegroup_json_data, connections_list, node_tree)

            debug_print("nodegroup_setup", f"Recorded nodegroup {node_id} to socket map")

        except Exception as e:
            print(f"nodegroup failure for {node_id}: {e}")
            #debug_print(["nodegroup_setup", "errors"], f"[Exception] Failed to instance nodegroup for {node_id}/{node_type}: {e}")

def set_up_ng_blocks(nodes_json, nodegroup_json_data):

def find_socket_by_identifier_or_name(node, identifier_or_name, is_input=True):
    sockets = node.inputs if is_input else node.outputs
    for s in sockets:
        if s.identifier == identifier_or_name or s.name == identifier_or_name:
            return s
        else:
            debug_print("sockets", f"[WARN] Socket '{identifier_or_name}' not found on node '{node.name}' ({'input' if is_input else 'output'})")
    return None

def create_nodegroup_from_ng_data(name, node_type, ng_data, node_id, connections_list):

    ng_name = name
    debug_print("nodegroup_creation", f"Creating {ng_name}")
    # Create new node group
    node_group = bpy.data.node_groups.new(ng_name, 'ShaderNodeTree')

    # === Color tag ===
    colour_str = ng_data.get("colour", "") or ng_data.get("color", "")
    if colour_str:
        colour_key = colour_str.strip().lower()
        node_group.color_tag = COLOR_NAME_TO_TAG.get(colour_key, "NONE")

    # === Group input/output nodes ===
    group_input = node_group.nodes.new('NodeGroupInput')
    group_output = node_group.nodes.new('NodeGroupOutput')

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

        try:
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

            name_to_node[node_name] = node

            for sock_name, val in node_def.get("default_values", {}).items():
                if not group_input or group_output:
                    debug_print(["nodegroup_creation", "sockets"], f"default value on group in/output for {node_type}")
                    debug_print(["nodegroup_creation", "sockets"], f"Looking for sock name: {sock_name}")
                    socket = find_socket_by_identifier_or_name(node, sock_name, is_input=True)
                    if socket:
                        debug_print(["nodegroup_creation", "sockets"], f"[DEBUG] Socket match: {node.name}.{socket.identifier}, linked={socket.is_linked}, has default={hasattr(socket, 'default_value')}")
                    else:
                        debug_print(["nodegroup_creation", "sockets", "errors"], f"[WARN] Socket not found: {node.name}.{sock_name}")
                    if socket and not socket.is_linked and hasattr(socket, "default_value"):
                        try:
                            socket.default_value = val
                            debug_print(["nodegroup_creation", "sockets"], f"[[DEBUG] Set default on {node.name}.{socket.identifier}: {val}")
                        except Exception as e:
                            debug_print(["nodegroup_creation", "sockets", "errors"], f"[[WARN] Failed to set default on {node.name}.{socket.identifier}: {e}")
            for sock_name, val in node_def.get("default_values", {}).items():
                debug_print("sockets", f"Looking for sock name: {sock_name}")
                socket = find_socket_by_identifier_or_name(node, sock_name, is_input=True)
                if socket:
                    debug_print(["nodegroup_creation", "sockets"], f"[DEBUG] Socket match: {node.name}.{socket.identifier}, linked={socket.is_linked}, has default={hasattr(socket, 'default_value')}")
                else:
                    debug_print(["nodegroup_creation", "sockets", "errors"], f"[WARN] Socket not found: {node.name}.{sock_name}")

                if socket and not socket.is_linked and hasattr(socket, "default_value"):
                    try:
                        socket.default_value = val
                        debug_print(["nodegroup_creation", "sockets"], f"[DEBUG] Set default on {node.name}.{socket.identifier}: {val}")
                    except Exception as e:
                        debug_print(["nodegroup_creation", "sockets", "errors"], f"[WARN] Failed to set default on {node.name}.{socket.identifier}: {e}")

        except Exception as e:
            debug_print(["nodegroup_creation", "errors"], f"[Warning] Failed to create node {node_name}: {e}")

#    print("internal nodes done")
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

    # === Interface socket creation ===
    socket_map = {}
    for direction, in_out, group_node in [
        ("inputs", "INPUT", group_input),
        ("outputs", "OUTPUT", group_output),
    ]:
        socket_defs = ng_data.get("sockets", {}).get(direction, {})
        for idx_str, sock_def in socket_defs.items():

            if isinstance(sock_def, list):
                sock_name, sock_type = sock_def
                if sock_type == "NodeSocketFloatFactor":
                    sock_type = "NodeSocketFloat"
                    debug_print("sockets", f"Corrected sock_type to: {sock_type}")
            else:
                sock_name = sock_def
                if sock_name == "NodeSocketFloatFactor":
                    sock_type = "NodeSocketFloat"
                    debug_print("sockets", f"Corrected sock_type to: {sock_type}")
                else:
                    sock_type = inferred_socket_types.get(sock_name, 'NodeSocketFloat')

            if sock_type == "NodeSocketFloatFactor":
                sock_type = "NodeSocketFloat"

            node_group.interface.new_socket(name=sock_name, in_out=in_out, socket_type=sock_type)
            socket_map[sock_name] = (in_out, group_node)

    # === Create links ===
    for link in ng_data.get("links", []):
        if len(link) != 4:
            debug_print(["links", "errors"], f"[Warning] Invalid link format: {link}")
            continue

        from_node_name, from_sock_id, to_node_name, to_sock_id = link
        from_node = name_to_node.get(from_node_name)
        to_node = name_to_node.get(to_node_name)

        if not from_node or not to_node:
            debug_print(["links", "errors"], f"[Warning] Missing node in link: {link}")
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

# === Helper to build cleaned connections list ===
def build_connections_list(connections_json):

    connections_list = []
    for conn_id, conn_data in connections_json.items():
        connections_list.append({
            "connection_id": conn_id,
            "from_socket": conn_data.get("From_Socket"),
            "to_socket": conn_data.get("To_Socket"),
        })

    return connections_list

# === Create master material and attach ===
def create_material_and_instance(blendernative_entries, nodegroup_entries, nodes_json, nodegroup_json_data, connections_list, connections_json):

    obj = bpy.context.active_object
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
        # FULL CLEAR — no stale state
    node_tree.nodes.clear()
    node_tree.links.clear()
    nodes = mat.node_tree.nodes
    obj.active_material = mat


    matout = node_tree.nodes.new('ShaderNodeOutputMaterial')
    #matout.loc = 0, 200
#  node_instance_map[node_id] = matout

    get_correct_native_nodes(blendernative_entries, node_tree, nodes_json, nodegroup_json_data, connections_list)
    set_up_nodegroups(nodegroup_entries, node_tree, nodes_json, nodegroup_json_data, connections_list)
    create_blender_links(node_tree, connections_list, node_instance_map, global_socket_map, used_connectors)



    return node_tree

def remove_temp_nodes(node, node_tree, temp_nodes):
    for node in temp_nodes: #------------------- Note: If reroutes start failing, move this to after links are created.
        node_tree.nodes.remove(node)
    temp_nodes.clear()

    # Create reverse lookup for which socket belongs to which node
def create_blender_links(master_tree, connections_list, node_instance_map, global_socket_map, used_connectors):

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
 #          print("Socket is not from_nid or to_nid")
            continue

        from_socket = global_socket_map[from_nid].get(from_sid)
        to_socket = global_socket_map[to_nid].get(to_sid)
        if not from_socket or not to_socket:
 #           print("from socket or to socket missing")
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
            print(f"[Warning] Link did NOT register in Blender: {from_nid}:{from_sid} ({from_socket.name}) ({from_socket.type}) > {to_nid}:{to_sid} ({to_socket.name}, ({to_socket.type}))")


connections_list = build_connections_list(data.get("Connections", {}))
clear_all_ng_from_file()
blendernative_entries, nodegroup_entries = get_node_sets(nodes_json)
node_tree = create_material_and_instance(blendernative_entries, nodegroup_entries, nodes_json, nodegroup_json_data, connections_list, connections)
remove_temp_nodes(node_instance_map, node_tree, temp_nodes)
print("Run successful.")
