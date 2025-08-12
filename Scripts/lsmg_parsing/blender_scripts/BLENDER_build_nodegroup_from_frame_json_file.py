## Creates nodegroups from file in new blender material.

import bpy
import json

# === CONFIG ===
NODEGROUP_JSON_PATH = r"F:\Python_Scripts\Blender Scripts\frame_exported_nodegroups_3.json"

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

def load_nodegroup_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[ERROR] Failed to load nodegroup JSON: {e}")
        return None

def find_socket_by_identifier_or_name(node, identifier_or_name, is_input=True):
    sockets = node.inputs if is_input else node.outputs
    for s in sockets:
        if s.identifier == identifier_or_name or s.name == identifier_or_name:
            return s
    print(f"[WARN] Socket '{identifier_or_name}' not found on node '{node.name}' ({'input' if is_input else 'output'})")
    return None

def create_nodegroup_from_ng_data(name, ng_data):

    ng_name = name.replace('.', '_').replace(' ', '_')

    # Remove existing node group if it exists
    if ng_name in bpy.data.node_groups:
        old_ng = bpy.data.node_groups[ng_name]
        # Disconnect old groups from materials before removing (safe cleanup)
        for mat in bpy.data.materials:
            for node in getattr(mat.node_tree, "nodes", []):
                if node.type == 'GROUP' and node.node_tree == old_ng:
                    node.node_tree = None
        bpy.data.node_groups.remove(old_ng)

    # Create new node group
    ng = bpy.data.node_groups.new(ng_name, 'ShaderNodeTree')

    # === Color tag ===
    colour_str = ng_data.get("colour", "") or ng_data.get("color", "")
    if colour_str:
        colour_key = colour_str.strip().lower()
        ng.color_tag = COLOR_NAME_TO_TAG.get(colour_key, "NONE")

    # === Custom props ===
    autohide = ng_data.get("autohide", False)
    ng["autohide"] = autohide
    print("autohide:", ng.get("autohide", "not set"))

    # === Group input/output nodes ===
    group_input = ng.nodes.new('NodeGroupInput')
    group_output = ng.nodes.new('NodeGroupOutput')

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
            node = ng.nodes.new(type=node_type)
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
                socket = find_socket_by_identifier_or_name(node, sock_name, is_input=True)
                if socket:
                    print(f"[DEBUG] Socket match: {node.name}.{socket.identifier}, linked={socket.is_linked}, has default={hasattr(socket, 'default_value')}")
                else:
                    print(f"[WARN] Socket not found: {node.name}.{sock_name}")

                if socket and not socket.is_linked and hasattr(socket, "default_value"):
                    try:
                        socket.default_value = val
                        print(f"[DEBUG] Set default on {node.name}.{socket.identifier}: {val}")
                    except Exception as e:
                        print(f"[WARN] Failed to set default on {node.name}.{socket.identifier}: {e}")

        except Exception as e:
            print(f"[Warning] Failed to create node {node_name}: {e}")

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
                    print(f"Corrected sock_type to: {sock_type}")
            else:
                sock_name = sock_def
                if sock_name == "NodeSocketFloatFactor":
                    sock_type = "NodeSocketFloat"
                    print(f"Corrected sock_type to: {sock_type}")
                else:
                    sock_type = inferred_socket_types.get(sock_name, 'NodeSocketFloat')

            if sock_type == "NodeSocketFloatFactor":
                print(f"{sock_type}")
                sock_type = "NodeSocketFloat"
                print(f"{sock_type}")

            ng.interface.new_socket(name=sock_name, in_out=in_out, socket_type=sock_type)
            socket_map[sock_name] = (in_out, group_node)

    # === Create links ===
    for link in ng_data.get("links", []):
        if len(link) != 4:
            print(f"[Warning] Invalid link format: {link}")
            continue

        from_node_name, from_sock_id, to_node_name, to_sock_id = link

        from_node = name_to_node.get(from_node_name)
        to_node = name_to_node.get(to_node_name)

        if not from_node or not to_node:
            print(f"[Warning] Missing node in link: {link}")
            continue

        from_socket = find_socket_by_identifier_or_name(from_node, from_sock_id, is_input=False)
        to_socket = find_socket_by_identifier_or_name(to_node, to_sock_id, is_input=True)
        if not from_socket or not to_socket:
            print(f"[Warning] Could not find sockets in link: {link}")
            continue

        try:
            ng.links.new(from_socket, to_socket)
        except Exception as e:
            print(f"[Warning] Failed to create link {link}: {e}")

    return ng

def create_material_with_nodegroups(nodegroups):
    mat = bpy.data.materials.new("Generated_Nodegroups_Material")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in nt.nodes:
        nt.nodes.remove(n)

    output_node = nt.nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (800, 0)

    spacing_x = 240
    spacing_y = -200
    col = 0
    row = 0

    for i, ng in enumerate(nodegroups):
        node = nt.nodes.new("ShaderNodeGroup")
        node.node_tree = ng
        # ng.use_fake_user = True

        node.location = (col * spacing_x, row * spacing_y)

        base_name = ng.name
        name_try = base_name
        count = 1
        while name_try in nt.nodes and nt.nodes[name_try] != node:
            name_try = f"{base_name}.{count:03d}"
            count += 1
        node.name = name_try

        if ng.get("autohide", False):
            node.hide = True

        row += 1
        if row >= 10:
            row = 0
            col += 1

    obj = bpy.context.active_object
    if obj and obj.type == 'MESH':
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    print(f"[INFO] Material '{mat.name}' created with {len(nodegroups)} node groups.")

def main():
    nodegroup_json_data = load_nodegroup_json(NODEGROUP_JSON_PATH)
    if not nodegroup_json_data:
        print("No nodegroup json data loaded. Exiting.")
        return

    created_groups = []

    for node_name, ng_data in nodegroup_json_data.items():
        ng = create_nodegroup_from_ng_data(node_name, ng_data)
        print(f"Created nodegroup: {ng.name}")
        created_groups.append(ng)

    create_material_with_nodegroups(created_groups)


if __name__ == "__main__":
    main()
