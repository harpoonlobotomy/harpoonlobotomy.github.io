## correctly identifies the componentmasknode data_type by checking the name suffix (x/xy/etc)

## written for Blender 4.3
# - harpoonlobotomy

import json
from collections import defaultdict, deque
import re

# Fixed node type rules
node_type_behaviour = {
    "DotNode": "scalar",
    "DesaturationNode": "color",
    "CombineNode": "vector",
    "ConstantFloatNode": "scalar",
    "UV": "vector",
    "LengthNode": "scalar",
    "normal": "vector",
    "Texture2DNode": "color",
    "ConstantVector2Node": "vector",
    "ConstantVector3Node": "color",
    "ConstantVector4Node": "vector",
    "position": "vector"
}

enum_behaviour = {
    "float": "scalar",
    "float2": "vector",
    "float3": "vector",
    "float4": "vector",
}

def socket_name_behaviour(socket_names):
    color_sockets = {"rgb", "rgba", "color", "albedo"}
    normalized = {s.lower() for s in socket_names if s}
    if normalized & color_sockets:
        return "color"

def build_output_map(chains):
    output_map = defaultdict(list)
    for conn in chains.values():
        output_map[conn["From_Node"]].append(conn)
    return output_map

def find_start_nodes(chains):
    from_nodes = {conn["From_Node"] for conn in chains.values()}
    to_nodes = {conn["To_Node"] for conn in chains.values()}
    return from_nodes - to_nodes

def assign_locked_types(chains, node_data_type_map):
    locked_nodes = set()
    for conn in chains.values():
        for node_key, type_key in [("From_Node", "From_Node_Type_Name"), ("To_Node", "To_Node_Type_Name")]:
            nid = conn.get(node_key)
            node_type_name = conn.get(type_key, "")
            for match_key in node_type_behaviour:
                if match_key.lower() in node_type_name.lower():
                    forced_type = node_type_behaviour[match_key]
                    if nid not in node_data_type_map:
                        node_data_type_map[nid] = forced_type
                        locked_nodes.add(nid)
                    break

            if "componentmasknode" in node_type_name.lower():
                # Try to extract suffix like "XY" from "ComponentMaskNode_XY"
                match = re.search(r'componentmasknode_([a-zA-Z]+)', node_type_name.lower())

                if match:
                    mask = match.group(1)
                    if len(mask) == 3:
                        forced_type = "color"
                    if len(mask) == 2:
                        forced_type = "vector"
                    if len(mask) == 1:
                        forced_type = "scalar"

                    if nid not in node_data_type_map:
                        node_data_type_map[nid] = forced_type
                        locked_nodes.add(nid)

            #if "componentmasknode" in node_type_name.lower():
            #    print(f"{node_type_name} is {forced_type}")

    return locked_nodes

def override_type_by_socket(node_type_name, socket_names):
    texture2d_scalar_sockets = {"g", "y", "a", "b", "alpha", "r"}#, "m_outputa"}

    if "texture2dnode" in node_type_name.lower():
        normalized = {s.lower() for s in socket_names if s}
        if normalized & texture2d_scalar_sockets:
            #print(f"{node_type_name} changed to scalar because of socket")
            return "scalar"

    return None

def assign_enum_socket_type(chains):
    socket_type_map = {}
    locked_nodes = set()
    for conn in chains.values():
        for socket_key, enum_key in [("From_Socket", "From_Socket_Enum"), ("To_Socket", "To_Socket_Enum")]:
            sid = conn.get(socket_key)
            enum = conn.get(enum_key, "")
        #    print(f"{sid}, {enum}")
            if sid and enum:
                socket_type_map[sid] = enum
                return

    #for sid, enum in socket_type_map.items():
        #print(f"{sid}: {enum}")

def merge_input_types(inputs):
    if "color" in inputs:
        return "color"
    if "vector" in inputs:
        return "vector"
        return "scalar"

def iterative_type_propagation(chains, locked_nodes, node_data_type_map):
    output_map = build_output_map(chains)
    node_input_types = defaultdict(list)
    node_arrival_count = defaultdict(int)
    socket_type_map = assign_enum_socket_type(chains)
    work_queue = deque()

    # Initialize queue with nodes that have locked types
    for node in locked_nodes:
        work_queue.append(node)

    # Also start nodes default to scalar if no type assigned
    start_nodes = find_start_nodes(chains)
    for sn in start_nodes:
        if sn not in node_data_type_map:
            node_data_type_map[sn] = "scalar"
            work_queue.append(sn)

    precedence = {"scalar": 0, "vector": 1, "color": 2}

    while work_queue:
        current = work_queue.popleft()
        current_type = node_data_type_map.get(current, "scalar")

        for conn in output_map.get(current, []):
            to_node = conn["To_Node"]
            from_socket = conn.get("From_Socket_ID", "?")
            to_socket = conn.get("To_Socket_ID", "?")

            if to_node in locked_nodes:
                continue

            connection_type = current_type
            from_node_type = conn.get("From_Node_Type_Name", "")
            enum = conn.get("From_Socket_Enum", "")
            from_socket_names = {
                conn.get("From_Socket_Name", ""),
                conn.get("From_Internal_Socket", "")
            }


            # Enum override, with Color heuristic
            enum_override_type = enum_behaviour.get(enum.lower())
            if enum_override_type:
                if "_color" in from_node_type.lower():
                    connection_type = "color"
                if "Vector4" in from_node_type.lower():
                    connection_type = "vector"
                else:
                    connection_type = enum_override_type

            # Special socket override (e.g., Texture2DNode heuristics)
            override_type = override_type_by_socket(from_node_type, from_socket_names)
            if override_type:
                connection_type = override_type

            # Socket name override
            socket_override_type = socket_name_behaviour(from_socket_names)
            if socket_override_type:
                connection_type = socket_override_type

            # Enum override, with Color heuristic
            enum_override_type = enum_behaviour.get(enum.lower())
            if enum_override_type:
                if "_color" in from_node_type.lower():
                    connection_type = "color"
                if "Vector4" in from_node_type.lower():
                    connection_type = "vector"
                else:
                    connection_type = enum_override_type

            # Track input types
            node_input_types[to_node].append(connection_type)
            node_arrival_count[to_node] += 1

            # Merge all known inputs to determine best type
            merged_type = "scalar"
            for t in node_input_types[to_node]:
                if precedence[t] > precedence[merged_type]:
                    merged_type = t

            old_type = node_data_type_map.get(to_node, "scalar")
            if precedence[merged_type] > precedence[old_type]:
                node_data_type_map[to_node] = merged_type
                work_queue.append(to_node)

    return node_data_type_map, node_input_types, node_arrival_count

def forward_trace(
    node_id,
    output_map,
    memo,
    node_arrival_count,
    node_data_type_map,
    node_input_types,
    visited,
):
    if node_id in visited:
        # Already expanded this subtree: stop recursion to avoid duplication
        return []

    visited.add(node_id)

    branches = []

    for conn in output_map.get(node_id, []):
        to_node = conn["To_Node"]

        # Regardless of visited, accumulate input types and arrivals
        node_input_types[to_node].append(node_data_type_map.get(node_id, "scalar"))
        node_arrival_count[to_node] += 1

        # Expand subtree only if not visited
        if to_node not in visited:
            outputs = forward_trace(
                to_node,
                output_map,
                memo,
                node_arrival_count,
                node_data_type_map,
                node_input_types,
                visited,
            )
        else:
            outputs = []

        branch = {
            "Connection": conn,
            "Outputs": outputs
        }
        branches.append(branch)

    memo[node_id] = branches
    return branches

def trace_structure_only(chains, node_data_type_map, locked_nodes):
    output_map = build_output_map(chains)
    memo = {}
    visited = set()
    traced = {}
    start_nodes = find_start_nodes(chains)
    for node in start_nodes:
        traced[node] = forward_trace(
            node,
            output_map,
            memo,
            node_arrival_count=defaultdict(int),
            node_data_type_map=node_data_type_map,
            node_input_types=defaultdict(list),
            visited=visited,
        )
    return traced

def append_type_to_node_name(original_name, data_type):
    if not original_name or not data_type or data_type == "scalar":
        return original_name
    if original_name == "MaterialNode / Material":
        parts = original_name.split("/")
        return parts[0]
    parts = original_name.split("/")
    parts[0] = parts[0].strip() + f"_{data_type}"
    return " / ".join(parts)

def print_node_chain_summary(named_chains, data_types, chains):
    id_to_name = {}
    for conn in chains.values():
        fid = conn["From_Node"]
        tid = conn["To_Node"]
        if fid not in id_to_name:
            id_to_name[fid] = conn.get("From_Node_Type_Name", "")
        if tid not in id_to_name:
            id_to_name[tid] = conn.get("To_Node_Type_Name", "")

    for label, node_ids in named_chains:
        print(f"\n--- Node Chain Summary: {label} ---")
        for nid in node_ids:
            name = id_to_name.get(nid, "UNKNOWN")
            dtype = data_types.get(nid, "scalar")
            tagged = append_type_to_node_name(name, dtype)
            print(f"{nid} > {name}")

def run(input_file: str, output_file: str):
    with open(input_file, "r") as f:
        chains = json.load(f)

    node_data_type_map = {}
    locked_nodes = assign_locked_types(chains, node_data_type_map)
    assigned_sockets = assign_enum_socket_type(chains)
    node_data_type_map, node_input_types, node_arrival_count = iterative_type_propagation(
        chains, locked_nodes, node_data_type_map
    )

    traced = trace_structure_only(chains, node_data_type_map, locked_nodes)

    # Update node type names in chains
    for conn in chains.values():
        from_id = conn["From_Node"]
        to_id = conn["To_Node"]

        from_type = node_data_type_map.get(from_id, "scalar")
        to_type = node_data_type_map.get(to_id, "scalar")

        conn["From_Node_Type_Name"] = append_type_to_node_name(conn.get("From_Node_Type_Name", ""), from_type)
        conn["To_Node_Type_Name"] = append_type_to_node_name(conn.get("To_Node_Type_Name", ""), to_type)

    with open(output_file, "w") as f:
        json.dump(traced, f, indent=2)

    #print("Done.")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python LSMG_stage5_forward_tracer.py input.json [output.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "forward_traced_output.json"

    run(input_path, output_path)
