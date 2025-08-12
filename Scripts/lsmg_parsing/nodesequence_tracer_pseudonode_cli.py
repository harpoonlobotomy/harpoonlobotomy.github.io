## Takes in Stage 3 parser .json file. currently, exclusively finds the VT_Layers pattern, but might potentially be expandable.
# 6/8/25, now outputs a proper pseudonode I can hopefully inject in stage5. Works nicely. Was hell to make work.
# 6/8/25 I switched the socket id to actually be the socket instead of the node. Not sure how I feel about it yet but hopefully it helps.


import json
import collections
from collections import defaultdict
from pprint import pprint
from itertools import chain
import copy
import re

# === CONFIGURATION ===
pattern_links = [
    ["LengthNode[1]", "Result", "CombineNode[1]", "Value2"],
    ["LengthNode[2]", "Result", "CombineNode[1]", "Value3"],
    ["ConstantFloatNode[1]", "Output", "SquareRootNode[1]", "Value"],
    ["SquareRootNode[1]", "Result", "DivideNode[1]", "Y"],
    ["SubtractNode[5]", "Result", "ConstantClampNode[1]", "Value"],
    ["ConstantClampNode[1]", "Result", "DivideNode[2]", "X"],
    ["ComponentMaskNode_XYZ[3]", "Result", "MultiplyNode[3]", "Y"],
    ["DivideNode[2]", "Result", "ComponentMaskNode_W", "Value"],
    ["ComponentMaskNode_W", "Result", "MultiplyNode[4]", "X"],
    ["ComponentMaskNode_XYZ[4]", "Result", "MultiplyNode[4]", "Y"],
    ["MultiplyNode[4]", "Result", "AddNode[2]", "Y"],
    ["DivideNode[2]", "Result", "ComponentMaskNode_X", "Value"],
    ["ComponentMaskNode_X", "Result", "MultiplyNode[1]", "X"],
    ["ComponentMaskNode_XYZ[1]", "Result", "MultiplyNode[1]", "Y"],
    ["MultiplyNode[1]", "Result", "AddNode[1]", "X"],
    ["DivideNode[2]", "Result", "ComponentMaskNode_Y", "Value"],
    ["ComponentMaskNode_Y", "Result", "MultiplyNode[2]", "X"],
    ["ComponentMaskNode_XYZ[2]", "Result", "MultiplyNode[2]", "Y"],
    ["MultiplyNode[2]", "Result", "AddNode[1]", "Y"],
    ["MultiplyNode[3]", "Result", "AddNode[2]", "X"],
    ["ComponentMaskNode_Z", "Result", "MultiplyNode[3]", "X"],
    ["DivideNode[2]", "Result", "ComponentMaskNode_Z", "Value"],
    ["ConstantFloatNode[2]", "Output", "DivideNode[2]", "Y"],
    ["ConstantFloatNode[2]", "Output", "OneMinusNode[2]", "Input"],
    ["OneMinusNode[2]", "Output", "SubtractNode[5]", "Y"],
    ["OneMinusNode[1]", "Output", "SubtractNode[5]", "X"],
    ["DivideNode[1]", "Result", "OneMinusNode[1]", "Input"],
    ["CombineNode[1]", "Result", "DivideNode[1]", "X"],
    ["LengthNode[3]", "Result", "CombineNode[1]", "Value1"],
    ["LengthNode[4]", "Result", "CombineNode[1]", "Value4"]
]

principle_node_type = "CombineNode"  # Optional; set to None if not used
principle_group = set()
node_id_to_group = {}
pattern_name = "VT_Layers_4ch"

def load_graph_links(json_data):
    links = []
    node_types = {}
    links_detailed = []

    for conn_id, conn in json_data.items():
        from_node = conn["From_Node"]
        to_node = conn["To_Node"]

        from_type = conn["From_Node_Type_Name"].split(" /")[0]
        to_type = conn["To_Node_Type_Name"].split(" /")[0]

        from_socket_id = conn["From_Socket"]
        to_socket_id = conn["To_Socket"]

        from_socket = conn["From_Socket_Name"]
        to_socket = conn["To_Socket_Name"]

        # Record actual link
        links.append((from_node, from_socket, to_node, to_socket))

        links_detailed.append((from_node, from_socket, from_socket_id, to_node, to_socket, to_socket_id))
        # Record types
        node_types[from_node] = from_type
        node_types[to_node] = to_type

    return links, node_types, links_detailed

def build_graph(links):
    forward_map = defaultdict(list)
    reverse_map = defaultdict(list)

    for from_node, from_sock, to_node, to_sock in links:
        forward_map[(from_node, from_sock)].append((to_node, to_sock))
        reverse_map[(to_node, to_sock)].append((from_node, from_sock))

    #print("REVERSE MAP SAMPLE:")
#    for k, v in list(reverse_map.items())[:10]:
        #print(k, "=>", v)
    return forward_map, reverse_map

def extract_pattern_types(pattern_links):
    pattern_node_types = {}
    for src, _, tgt, _ in pattern_links:
        for name in [src, tgt]:
            if name not in pattern_node_types:
                base = name.split("[")[0]
                pattern_node_types[name] = base
    return pattern_node_types

def build_candidate_pool(node_types, pattern_node_types):
    base_to_ids = defaultdict(set)
    for node_id, base_type in node_types.items():
        base_to_ids[base_type].add(node_id)
        if base_type == principle_node_type:
            principle_group.add(node_id)
            #print(f"Base = {node_id}")

    candidates = {}
    for pattern_node, base_type in pattern_node_types.items():
        candidates[pattern_node] = set(base_to_ids[base_type])

    return candidates

def apply_pattern_constraints(pattern_links, candidates, forward_map, reverse_map, principle_group):
    changed = True
    grouped_candidates = {}  # group_id -> role -> set(node_ids)
    node_id_to_group = {}    # node_id -> group_id
    deferred_group_propagation = defaultdict(list)

    while changed:
        changed = False

        for from_role, from_sock, to_role, to_sock in pattern_links:
            valid_from = set()
            valid_to = set()

            # FORWARD direction: from_role → to_role
            for from_node in candidates[from_role]:
                forward_targets = forward_map.get((from_node, from_sock), [])

                for to_node, actual_sock in forward_targets:
                    if to_node in candidates[to_role] and actual_sock == to_sock:
                        valid_from.add(from_node)
                        valid_to.add(to_node)

                        if from_node in principle_group:
                            node_id_to_group[from_node] = from_node

                        current_group = node_id_to_group.get(from_node)
                        if current_group:
                            if to_node not in node_id_to_group:
                                node_id_to_group[to_node] = current_group
                                changed = True
                            grouped_candidates.setdefault(current_group, {}).setdefault(from_role, set()).add(from_node)
                            grouped_candidates[current_group].setdefault(to_role, set()).add(to_node)
                        else:
                            deferred_group_propagation[from_node].append((to_node, to_role))

            # REVERSE direction: to_role → from_role
            for to_node in candidates[to_role]:
                reverse_sources = forward_map.get((from_node, from_sock), [])
                for (rev_target_node, rev_target_sock), reverse_sources in reverse_map.items():
                    if rev_target_node != to_node or rev_target_sock != to_sock:
                        continue
                    for source_node, actual_sock in reverse_sources:
                        #print(f"Reverse match candidate: {source_node} to {rev_target_node} via {actual_sock}")

                        if source_node in candidates[from_role] and actual_sock == from_sock:
                            #print(f"[MATCH] {source_node} feeds {to_node} on socket {to_sock}")
                            valid_from.add(source_node)
                            valid_to.add(to_node)

                            if to_node in principle_group:
                                node_id_to_group[source_node] = to_node

                            current_group = node_id_to_group.get(to_node)

                            if current_group:
                                if from_node not in node_id_to_group:
                                    node_id_to_group[from_node] = current_group
                                    changed = True
                                grouped_candidates.setdefault(current_group, {}).setdefault(to_role, set()).add(to_node)
                                grouped_candidates[current_group].setdefault(from_role, set()).add(from_node)
                            else:
                                deferred_group_propagation[to_node].append((from_node, from_role))

            # Candidate set filtering
            old_from = candidates[from_role]
            old_to = candidates[to_role]
            new_from = old_from & valid_from
            new_to = old_to & valid_to

            if new_from != old_from:
                candidates[from_role] = new_from
                changed = True

            if new_to != old_to:
                candidates[to_role] = new_to
                changed = True

            if not new_from or not new_to:
                return False  # Prune failed

    # Deferred group propagation
    new_deferred = defaultdict(list)
    for from_node, links in deferred_group_propagation.items():
        current_group = node_id_to_group.get(from_node)
        if current_group:
            for to_node, to_role in links:
                if to_node not in node_id_to_group:
                    node_id_to_group[to_node] = current_group
                    grouped_candidates.setdefault(current_group, {}).setdefault(to_role, set()).add(to_node)
                    changed = True
        else:
            new_deferred[from_node].extend(links)

    deferred_group_propagation = new_deferred

    #print("[INFO] Constraint propagation completed successfully.")
    return grouped_candidates

def propagate_groups_from_seed_nodes(candidates, pattern_links, forward_map, reverse_map):
    node_to_group = {}
    exhausted = set()
    frontier = collections.deque()

    # Track potential roles per node and candidates per role
    node_to_roles = defaultdict(set)   # node_id -> set of possible roles (e.g. "LengthNode[1]")
    role_to_candidates = defaultdict(set)  # role -> set of node_ids that can be that role

    #print("\nSeeding groups from principle_group:")
    for role, node_ids in candidates.items():
        for node_id in node_ids:
            if node_id in principle_group:
                group_id = f"{node_id}/{pattern_name}"  # Seed group = principle node itself
                node_to_group[node_id] = group_id
                frontier.append((node_id, group_id))
                # Principle nodes must have their pattern role known (usually themselves)
                node_to_roles[node_id].add(role)
                role_to_candidates[role].add(node_id)
                #print(f"  Seed: node {node_id} -> group {group_id}, role {role}")

    while frontier:
        current_node, current_group = frontier.popleft()
        if current_node in exhausted:
            continue

        #print(f"\nProcessing node {current_node} in group {current_group}")

        # Get all possible roles this node might have so far
        current_roles = node_to_roles.get(current_node, set())

        # We'll check each role pattern linked to this node's roles, to find connected nodes
        for role in current_roles:
        # Look at all pattern links where this role is 'from' (outgoing)
            for from_role, from_socket, to_role, to_socket in pattern_links:
                #print(f"current node: {current_node}, 'role': {role}, from role: {from_role}, to role: {to_role}")
                if from_role != role:
                    continue

                # Check all forward connections of current_node on from_socket
                forward_targets = forward_map.get((current_node, from_socket), [])
                for to_node, actual_to_socket in forward_targets:
                    if to_node in candidates[to_role] and actual_to_socket == to_socket:
                        if to_node == from_socket:
                            to_node = from_socket
                    else:
                        continue
                    if actual_to_socket != to_socket:
                        continue

                    # Assign group and roles
                    if to_node not in node_to_group:
                        node_to_group[to_node] = current_group
                        frontier.append((to_node, current_group))
                        #print(f"  Forward link: {current_node}({role}) -> {to_node} ({to_role}) [new group assignment]")
                    #else:
                        #print(f"  Forward link: {current_node}({role}) -> {to_node} ({to_role}) [already in group {node_to_group[to_node]}]")

                    # Assign possible role to to_node
                    if to_role not in node_to_roles[to_node]:
                        node_to_roles[to_node].add(to_role)
                        role_to_candidates[to_role].add(to_node)

            # Look at all pattern links where this role is 'to' (incoming)
            for from_role, from_socket, to_role, to_socket in pattern_links:
                if to_role != role:
                    continue

                # Check all reverse connections of current_node on to_socket
                reverse_sources = reverse_map.get((current_node, to_socket), [])
                for from_node, actual_from_socket in reverse_sources:
                    if from_node in candidates[from_role] and actual_from_socket == from_socket:
                        if to_node == from_socket:
                            to_node = from_socket
                    else:
                        continue
                    if from_node not in node_to_group:
                        node_to_group[from_node] = current_group
                        frontier.append((from_node, current_group))
                        #print(f"  Reverse link: {current_node}({role}) <- {from_node} ({from_role}) [new group assignment]")
                    #else:
                        #print(f"  Reverse link: {current_node}({role}) <- {from_node} ({from_role}) [already in group {node_to_group[from_node]}]")

                    # Assign possible role to from_node
                    if from_role not in node_to_roles[from_node]:
                        node_to_roles[from_node].add(from_role)
                        role_to_candidates[from_role].add(from_node)

        exhausted.add(current_node)

    return node_to_group, node_to_roles, role_to_candidates

def refine_candidates_by_socket_connectivity(node_to_group, node_to_roles, role_to_candidates, pattern_links, forward_map, reverse_map):
    # We'll build fresh mappings to avoid mutating during iteration
    new_node_to_roles = {node: set() for node in node_to_roles}
    new_role_to_candidates = {role: set() for role in role_to_candidates}

    # For quick lookup: role → group (optional, if needed)
    # But assuming roles are unique strings, group can be inferred if needed externally

    # For each role, check each candidate node:
    for role, candidates in role_to_candidates.items():
        from_role, from_sock, to_role, to_sock = None, None, None, None
        # Find pattern_links involving this role (as from_role or to_role)
        related_links = [link for link in pattern_links if role == link[0] or role == link[2]]

        for node_id in candidates:
            # Check if node_id satisfies all pattern links for this role
            matches_all = True

            for link in related_links:
                f_role, f_sock, t_role, t_sock = link

                if role == f_role:
                    # node_id should have a forward connection on f_sock to some candidate in t_role
                    targets = forward_map.get((node_id, f_sock), [])
                    # target node must be candidate in role_to_candidates[t_role] with matching socket t_sock
                    if not any((target_node in role_to_candidates.get(t_role, set()) and actual_sock == t_sock)
                               for target_node, actual_sock in targets):
                        matches_all = False
                        break

                elif role == t_role:
                    # node_id should have reverse connection on t_sock from some candidate in f_role
                    # Find sources from reverse_map
                    sources = reverse_map.get((node_id, t_sock), [])
                    if not any((source_node in role_to_candidates.get(f_role, set()) and actual_sock == f_sock)
                               for source_node, actual_sock in sources):
                        matches_all = False
                        break

            if matches_all:
                new_role_to_candidates[role].add(node_id)
                new_node_to_roles.setdefault(node_id, set()).add(role)

    # Remove empty entries to keep things tidy
    new_node_to_roles = {k: v for k, v in new_node_to_roles.items() if v}
    new_role_to_candidates = {k: v for k, v in new_role_to_candidates.items() if v}

    return node_to_group, new_node_to_roles, new_role_to_candidates

def find_external_connections(forward_map, reverse_map, matched_nodes, node_to_roles=None):
    start_nodes = set()
    end_nodes = set()
    contained_nodes = set()

    for (from_node, from_sock), targets in forward_map.items():
        for (to_node, to_sock) in targets:
            if to_node in matched_nodes and from_node not in matched_nodes:
                start_nodes.add(to_node)
            elif from_node in matched_nodes and to_node not in matched_nodes:
                end_nodes.add(from_node)

    contained_nodes = matched_nodes - start_nodes - end_nodes

    if node_to_roles:
        def attach_roles(nodes):
            return {
                str(node): next(iter(node_to_roles.get(node, {"Unknown"})))
                for node in sorted(nodes)
            }
        return attach_roles(start_nodes), attach_roles(end_nodes), attach_roles(contained_nodes)
    else:
        return sorted(start_nodes), sorted(end_nodes),  sorted(contained_nodes)

def build_grouped_candidates(node_to_group, node_to_roles):
    grouped_candidates = defaultdict(lambda: defaultdict(set))

    for node_id, group_id in node_to_group.items():
        roles = node_to_roles.get(node_id, set())
        for role in roles:
            grouped_candidates[group_id][role].add(node_id)

    # Optional: convert sets to sorted lists for clean printing
    for group_id, role_map in grouped_candidates.items():
        for role, nodes in role_map.items():
            role_map[role] = sorted(nodes)

    return dict(grouped_candidates)

def build_ng_pattern_blocks_by_group(grouped_candidates, group_to_starts, group_to_ends, pattern_links, graph_links, links_detailed):

    # Build name → socket lookup from pattern_links
    from collections import defaultdict
    name_to_input_socket = defaultdict(set)
    name_to_output_socket = defaultdict(set)

    name_to_input_socket_all = defaultdict(set)
    name_to_output_socket_all = defaultdict(set)

    id_to_input_socket_all = defaultdict(set)
    id_to_output_socket_all = defaultdict(set)

    id_to_input_name = defaultdict(set)
    id_to_output_name = defaultdict(set)

    for link in graph_links:
        if len(link) != 4:
            continue
        out_name, out_socket, in_name, in_socket = link
        name_to_output_socket_all[out_name].add(out_socket)
        name_to_input_socket_all[in_name].add(in_socket)

    for link in pattern_links:
        if len(link) != 4:
            continue
        out_name, out_socket, in_name, in_socket = link
        name_to_output_socket[out_name].add(out_socket)
        name_to_input_socket[in_name].add(in_socket)

    for detailed_link in links_detailed:
        if len(detailed_link) != 6:
            continue
        out_name, out_socket, out_socket_id, in_name, in_socket, in_socket_id = detailed_link
        id_to_input_socket_all[in_name].add(in_socket_id)
        id_to_output_socket_all[out_name].add(out_socket_id)

        id_to_input_name[in_socket_id].add(in_name)
        id_to_output_name[out_socket_id].add(out_name)

    #for node_id, socket_names in name_to_input_socket_all.items():
        #print(f"{node_id}: {[repr(s) for s in socket_names]}")

    ng_pattern_blocks = {}

    for group_id, role_to_nodes in grouped_candidates.items():
        group_node_ids = set(chain.from_iterable(role_to_nodes.values()))

        starts = group_to_starts.get(group_id, {})
        ends = group_to_ends.get(group_id, {})

        _, name_part = group_id.split("/", 1)

        group_data = {
            "Node_Id": group_id,
            "Node_Name": name_part,
            "Node_Type": name_part,
            "Is_NodeGroup": True,
            "Location": {"x": "0", "y": "0"},
            "m_Inputs": {"Connectors": []},
            "m_Outputs": {"Connectors": []}
        }

        # INPUTS
        for node_id, node_name in starts.items():
            if node_id not in group_node_ids:
                continue

            socket_id = None
            socket_names = name_to_input_socket_all.get(node_id, {""})
            socket_id = id_to_input_socket_all.get(node_id, {""})

            #pprint(socket_id)

            #for socket_id in id_to_input_socket_all:
            #    print(id_to_input_name)
            for socket in socket_names:
                for socket_id in socket_id:
                #print(f"Adding connector: Socket_Id={node_id}, Conn_Name={socket}, Conn_name_2={node_name}")
                    group_data["m_Inputs"]["Connectors"].append({
                        "Socket_Id": socket_id,
                        "Conn_Type": "z:Ref",
                        "Conn_Name": socket,
                        "Conn_name_2": node_name
                    })

                group_data["m_Inputs"]["Connectors"] = interleave_connectors(group_data["m_Inputs"]["Connectors"])
                #group_data["m_Inputs"]["Connectors"].sort(key=lambda x: x["Conn_name_2"])#x["Socket_Id"])  # or use Conn_Name

        # OUTPUTS
        for node_id, node_name in ends.items():
            if node_id not in group_node_ids:
                continue

            socket_names = name_to_output_socket_all.get(node_id, {""})
            socket_id = id_to_output_socket_all.get(node_id, {""})
            for socket in socket_names:
                for socket_id in socket_id:
                    group_data["m_Outputs"]["Connectors"].append({
                        "Socket_Id": socket_id,
                        "Conn_Type": "z:Ref",
                        "Conn_Name": socket,
                        "Conn_name_2": node_name
                    })

                group_data["m_Outputs"]["Connectors"] = interleave_connectors(group_data["m_Outputs"]["Connectors"])

        ng_pattern_blocks[group_id] = group_data

    return ng_pattern_blocks

def interleave_connectors(connector_list, name_key="Conn_name_2"):
    grouped = defaultdict(list)
    for conn in connector_list:
        match = re.match(r"([^\[]+)\[(\d+)\]", conn.get(name_key, ""))
        if match:
            prefix, index = match.groups()
            grouped[prefix].append((int(index), conn))
        else:
            grouped[""].append((0, conn))  # fallback group for unmatched
    for prefix in grouped:
        grouped[prefix].sort(key=lambda x: x[0])

        sorted_prefixes = sorted(grouped.keys())  # ensure consistent alphabetical interleaving

    max_len = max(len(v) for v in grouped.values())
    interleaved = []
    for i in range(max_len):
        for prefix in sorted_prefixes:
            group = grouped[prefix]
            if i < len(group):
                interleaved.append(group[i][1])

    return interleaved

def export_to_json_pseudonode(output_path, combined_output):
    with open(output_path, 'w', encoding='utf-8') as f_out:
        json.dump(combined_output, f_out, indent=2)
    print(f"[Info] Wrote pattern sequence data to '{output_path}'")

# === MAIN DRIVER ===
def run(json_data_path, ng_blocks_out):

    with open(json_data_path) as f:
        json_data = json.load(f)

    #print("[INFO] Building graph...")
    graph_links, node_types, links_detailed = load_graph_links(json_data)
    forward_map, reverse_map = build_graph(graph_links)

    #print("[INFO] Processing pattern...")
    pattern_node_types = extract_pattern_types(pattern_links)
    candidates = build_candidate_pool(node_types, pattern_node_types)

    #print("[INFO] Applying structural constraints...")
    node_to_group, node_to_roles, role_to_candidates = propagate_groups_from_seed_nodes(candidates, pattern_links, forward_map, reverse_map)

    # Neaten - mostly just removes the extraneous combine nodes, now.
    node_to_group, node_to_roles, role_to_candidates = refine_candidates_by_socket_connectivity(
        node_to_group, node_to_roles, role_to_candidates,
        pattern_links, forward_map, reverse_map
    )

    grouped_candidates = build_grouped_candidates(node_to_group, node_to_roles)

    ng_nodes = {}
    ng_pattern_blocks = {}

    group_to_starts = {}
    group_to_ends = {}

    for group_id, role_to_nodes in grouped_candidates.items():
        matched_nodes = set(chain.from_iterable(role_to_nodes.values()))
        starts, ends, contained = find_external_connections(forward_map, reverse_map, matched_nodes, node_to_roles)

        group_data = {
            "start": (starts),
            "end": (ends),
            "contained": (contained)
        }

        ng_nodes[group_id] = group_data

        group_to_starts[group_id] = starts
        group_to_ends[group_id] = ends

    ng_pattern_blocks = build_ng_pattern_blocks_by_group(grouped_candidates, group_to_starts, group_to_ends, pattern_links, graph_links, links_detailed)

    combined_output = {
        "ng_nodes": ng_nodes,
        "ng_pattern_blocks": ng_pattern_blocks
    }

    export_to_json_pseudonode(ng_blocks_out, combined_output)

# === Example Usage ===
if __name__ == "__main__":

## regex to get input file name and make it "node_sequence_CHAR_BASE_VT.json"
    ng_blocks_out = r"F:\test\wrapper_script_test_output6\node_sequence_CHAR_BASE_VT_pseudonode_03.json"
    json_data_path = r"F:\test\wrapper_script_test_output_ngblocks\stage_3_tmp_CHAR_BASE_VT.json"
#    json_data_path = sys.argv[1] #-- Uses Stage3's output.
#    output_path = sys.argv[2]
    run(json_data_path, ng_blocks_out)
