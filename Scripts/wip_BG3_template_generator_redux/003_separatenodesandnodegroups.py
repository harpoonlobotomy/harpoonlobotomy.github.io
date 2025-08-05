## based on template_nodegroups_gen_v2
## successfully places native nodes.

# Written for Blender vers 4.3
#harpoonlobotomy

import bpy
import json
import os

###----------   counter: -------------###
## not using but would be useful at some point
from collections import Counter

counts = Counter()

#for node in nodes:
#    if is_native(node):
#        node_type_counts["native"] += 1
#    elif is_special(node):
#        node_type_counts["special"] += 1
#    else:
#        node_type_counts["nodegroup"] += 1
#
### ========================= ###

# === CONFIG: Path to the new JSON node structure ===
JSON_PATH = r"F:\test\wrapper_script_test_output\stage_5_tmp_CHAR_Fur.json"

# === LOAD JSON NODES ===
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

    nodes = data.get("Nodes", {})
    connections = data.get("Connections", {})

# === Create sockets for each node group ===
def add_all_sockets(ng, node_data):
    socket_id_name_map = {}

    for direction in ["m_Inputs", "m_Outputs"]:
        group = node_data.get(direction)
        if not group:
            continue

        io = "INPUT" if direction == "m_Inputs" else "OUTPUT"
        connectors = group.get("Connectors", [])

        for conn in connectors:
            conn_id = conn.get("Socket_Id")
            name = f"Socket_{conn_id}"

            # Create the socket
            if not any(s.name == name for s in ng.interface.items_tree):
                ng.interface.new_socket(name=name, in_out=io, socket_type='NodeSocketFloat')

            socket_id_name_map[conn_id] = name

    return socket_id_name_map

# === delete all nodegroups - remove when testing is done ===
def clear_all_ng_from_file():
    for group in list(bpy.data.node_groups):  # Make a copy of the list to avoid modifying the list while iterating
        bpy.data.node_groups.remove(group)

# === get nodes and nodegroups as sets ===  ##-- works, splits into blendernative_entries and nodegroup_entries
def get_node_sets(nodes_json):
    allnode_data = []
    blendernative_entries = []
    nodegroup_entries = []
    optional_keys = [
        "Node_Type", "Blender_type", "Data_Type", "Blend_Type",
        "Blender_Operation", "d2p1_Attributes", "Location",   # Replace with your actual optional field names
    ]

    for node_id, node_data in nodes_json.items():
        node_entry = {
            "node_id": node_id
        }

        for key in optional_keys:
            if key in node_data:
                node_entry[key] = node_data[key]
        if "Blender_type" in node_data:
            blendernative_entries.append(node_entry)
#            print(f"Blender native node found: {node_id}")

        if "Is_NodeGroup" in node_data:
            nodegroup_entries.append(node_entry)
#            print(f"Nodegroup found: {node_id}")

#        print(f"Found {node_entry}")
        allnode_data.append(node_entry)
        counts["Node entries found"] += 1

    print(counts)
    return allnode_data, blendernative_entries, nodegroup_entries

##--- Not really needed, currently just proves the nodes are correctly identified at present.
##-- Convert into a version that just adds the native nodes directly, they don't need more processing.
def get_correct_native_nodes(blendernative_entries, nt):

    for entry in blendernative_entries:
        node = None
                                                    # ------- print(f"{}")
        blender_type = entry.get("Blender_type")
        print(f"{blender_type}")
        op = entry.get("Blender_Operation")
        print(f"{op}")
        datatype = entry.get("Data_Type")
        print(f"{datatype}")
        blendtype = entry.get("Blend_Type")
        print(f"{blendtype}")
        loc_raw = entry.get("Location", {})
        x = loc_raw.get("x", 0.0)
        y = loc_raw.get("y", 0.0)
        loc = (x, y)
        print(f"{loc}")

        try:# DO NOT RUN YET, RECURSES AND CRASHES BLENDER
            print("Attempting to create node of type:", blender_type)
            node = nt.nodes.new(blender_type)
            print("Node created")
            node.location = loc
            print("Location set to", loc)

        except Exception as e:
            print(f"[Warning] Could not create node '{blender_type}': {e}")

#                if op and hasattr(node, "operation"):
#                    print(f"{operation}")
#                    valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
#                    if op in valid_ops:
#                        node.operation = op
#                    else:
#                        print(f"[Warning] Invalid operation '{op}' for node '{blender_type}'")
#
#                if op and hasattr(node, "operation"):
#                    valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
#                    if op in valid_ops:
#                        node.operation = op
#                    else:
#                        print(f"[Warning] Invalid operation '{op}' for node '{blender_type}'")
#
#                if op and hasattr(node, "operation"):
#                    valid_ops = [item.identifier for item in node.bl_rna.properties["operation"].enum_items]
#                    if op in valid_ops:
#                        node.operation = op
#                    else:
#                        print(f"[Warning] Invalid operation '{op}' for node '{blender_type}'")
#
        #    except Exception as e:
        #        print(f"[Warning] Could not create node '{blender_type}': {e}")

# === Create nodegroups from JSON ===
def create_nodegroup_from_JSON(nodegroup_entries):
    return
    nodegroups = {}

    #if node in native_group_list:
    #    if node in native_group_list is ###### what?

    for node_id, node_data in nodes.items():
        group_name = f"NodeGroup_{node_id}"
        ng = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
        ng.use_fake_user = False
        # Label the nodegroup with the human-readable name
     #   ng.label = node_data.get("Node_Name", "")

        # Clear interface and add sockets
        for item in list(ng.interface.items_tree):
            ng.interface.remove(item)

        socket_map = add_all_sockets(ng, node_data)

        nodegroups[node_id] = {
            "nodegroup": ng,
            "socket_map": socket_map,
        }

        # Input/output/value nodes inside group
        group_input = ng.nodes.new('NodeGroupInput')
        group_input.location = (-300, 0)

        group_output = ng.nodes.new('NodeGroupOutput')
        group_output.location = (300, 0)

        value_node = ng.nodes.new('ShaderNodeValue')
        value_node.location = (0, 0)

        # Link first input → output if they exist
        inputs = [s for s in ng.interface.items_tree if s.in_out == "INPUT"]
        outputs = [s for s in ng.interface.items_tree if s.in_out == "OUTPUT"]

        if inputs and outputs:
            input_name = inputs[0].name
            output_name = outputs[0].name
            if input_name in group_input.outputs and output_name in group_output.inputs:
                ng.links.new(group_input.outputs[input_name], group_output.inputs[output_name])
            if output_name in group_output.inputs:
                ng.links.new(value_node.outputs[0], group_output.inputs[output_name])


# === Helper to build cleaned connections list ===
def build_connections_list(connections_json):
    """
    Converts raw connection dict into a list of connections with socket IDs and types.
    """
    connections_list = []
    for conn_id, conn_data in connections_json.items():
        connections_list.append({
            "connection_id": conn_id,
            "from_socket": conn_data.get("From_Socket"),
            "from_type": conn_data.get("From_Conn_Type"),
            "to_socket": conn_data.get("To_Socket"),
            "to_type": conn_data.get("To_Conn_Type"),
        })
    return connections_list

# === Helper to find socket name and owning nodegroup for a socket ID ===
def find_socket_name(socket_id, nodegroups):
    """
    Given a socket ID, return (node_id, socket_name).
    Returns (None, None) if not found.
    """
    for node_id, ng_data in nodegroups.items():
        socket_map = ng_data["socket_map"]
        if socket_id in socket_map:
            return node_id, socket_map[socket_id]
    return None, None

# === Create master material and attach ===
def create_material_and_instance(blendernative_entries, nodegroup_entries):

    obj = bpy.context.active_object

    print(f"{obj}")
    if not obj or obj.type != 'MESH':
        raise RuntimeError("Select a mesh object")

    obj = bpy.context.active_object
    mat = bpy.data.materials.get("test_temp_gen_redux")
    if not mat:
        mat = bpy.data.materials.new("test_temp_gen_redux")
        mat.use_nodes = True
        obj.data.materials.append(mat)

    mat.use_nodes = True
    nt = mat.node_tree

    # FULL CLEAR — no stale state
    nt.nodes.clear()
    nt.links.clear()

    nodes = mat.node_tree.nodes
    obj.active_material = mat

    node_instance = get_correct_native_nodes(blendernative_entries, nt)
    print("Node exists now")#if node_id in blendernative_entries:


#        loc = node_data.get("Location", {})
#
##
#        node_inst = master_tree.nodes.new("ShaderNodeGroup")
#        node_inst.node_tree = nodegroups[node_id]["nodegroup"]  #Correct group per ID
#
#        print(f"Node {node_id} location data: {loc}")

#        try:
#            x = float(loc.get("x", default_x))
#            y = float(loc.get("y", default_y))
#        except (TypeError, ValueError):
#            x = default_x
#            y = default_y
#
#        node_inst.location = (-x, -y)
#
#        print(f"Placing node {node_id} at ({x}, {y})")

#        node_inst.label = node_data.get("Node_Name", "")
    #    print(f"Creating node instance for node {node_id} with nodegroup {ng.name}")

#        instances[node_id] = node_inst
    #    print(f"Creating node instance for node {node_id} with nodegroup {ng.name}")

#        default_y -= vertical_spacing

# === Function to create Blender links between nodegroup instances ===
def create_blender_links(master_tree, instances, connections_list, nodegroups):
    """
    Link nodegroup sockets in the master node tree based on connections.
    """
    for conn in connections_list:
        from_socket_id = conn["from_socket"]
        to_socket_id = conn["to_socket"]

        from_node_id, from_socket_name = find_socket_name(from_socket_id, nodegroups)
        to_node_id, to_socket_name = find_socket_name(to_socket_id, nodegroups)

        if None in (from_node_id, from_socket_name, to_node_id, to_socket_name):
            print(f"[Warning] Missing socket mapping for connection {conn['connection_id']}: from {from_socket_id} to {to_socket_id}")
            continue

        from_node_inst = instances.get(from_node_id)
        to_node_inst = instances.get(to_node_id)

        if not from_node_inst or not to_node_inst:
            print(f"[Warning] Missing node instance for connection {conn['connection_id']}: from {from_node_id} to {to_node_id}")
            continue

        from_output = from_node_inst.outputs.get(from_socket_name)
        to_input = to_node_inst.inputs.get(to_socket_name)

        if from_output is None or to_input is None:
            print(f"[Warning] Missing sockets on Blender nodes for connection {conn['connection_id']}: from {from_socket_name} to {to_socket_name}")
            continue

        try:
            master_tree.links.new(from_output, to_input)
            print(f"[Link] Connected {from_node_id}.{from_socket_name} → {to_node_id}.{to_socket_name}")
        except Exception as e:
            print(f"[Error] Failed to link connection {conn['connection_id']}: {e}")


# === Usage example, after nodegroups and instances are created ===

#connections_list = build_connections_list(data.get("Connections", {}))
#print("All connections made.")

all_data, blendernative_entries, nodegroup_entries = get_node_sets(data.get("Nodes", {}))

#clear_all_ng_from_file()
#print("Cleared existing nodegroups from file.")

create_material_and_instance(blendernative_entries, nodegroup_entries)

#get_correct_native_nodes(blendernative_entries)
#get_native_node_mapping(native_node_list, data.get("Nodes", {}), allnode_data)

#if "blender_type" in allnode_data:

#allnode_data = get_nodegroup_mapping(native_node_list, data.get("Nodes", {}), allnode_data)

#print(f"{allnode_data}")

#create_nodegroup_from_JSON(nodes) # currently only creates basic default nodegroups

#nodegroups = get_nodegroup_mapping(nodegroups)



#create_blender_links(master_tree, instances, connections_list, nodegroups)




print("Run successful.")
#print("All node groups created and stacked into new material.")
