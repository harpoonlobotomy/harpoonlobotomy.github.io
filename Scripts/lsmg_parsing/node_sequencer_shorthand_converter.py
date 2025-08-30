"""
Started Saturday evening, 9/8/25.

Finished 3.23pm, 11/8/25.
 Script to dictate nodegroup blueprints by text, instead of relying on the Frame framework.
"""

import os
import json
from pprint import pprint
import copy
from collections import defaultdict

## ----- CONFIG ---- ##
output_path = r"F:\Python_Scripts\9_8_25\blueprint_test_output_2.json"
input_file = r"F:\Python_Scripts\Template_Generator\selected_nodes_output_test2.json"

native_file = r"F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI_changing_things_8_8_25\blender_native_node_ref_2.json"
#--------#

alt_names = [
    ["clamp", "constantclamp"],
    ["subt", "subtract"],
    ["gpin", "GroupInput"],
    ["gpout", "GroupOutput"]
]

def node_list(input_data):

#Exists to take the informal list of nodes and assign them to socket names.

    for nodegroup in input_data:
        nodegroup_data = input_data[nodegroup]
        links = nodegroup_data.get("Links")

        socket_map = {}

        for feedernode, outputsock, eaternode, inputsock in links:

            if feedernode not in socket_map:
                socket_map[feedernode] = {"inputs": [], "outputs": []}
            if eaternode not in socket_map:
                socket_map[eaternode] = {"inputs": [], "outputs": []}

            socket_map[feedernode]["outputs"].append(outputsock)
            socket_map[eaternode]["inputs"].append(inputsock)

    return socket_map

def get_native_node_details(native_data, socket_map, alt_names):

    nativename = {}
    node_dict = {}
    blender_nodename_dict = {}

    for entry in native_data:
        entry_mixed = entry
        entry_lower = entry.lower()
        nativename[entry_lower] = entry_mixed

        native_attrs = native_data[entry]
        for attr in native_attrs:
            tempattr = attr
        if tempattr == "type":
            native_val = native_attrs["type"]
            print(native_val)
            if "ShaderNode" in native_val:
                temp, typename = native_val.split("ShaderNode", 1)

        blender_nodename_dict.update({entry_lower: typename})
    print(blender_nodename_dict)
    for node in socket_map:
        suffix = None
        if "." in node:
            node_base, suffix = node.split(".", 1)
        else:
            node_base = node
        for entry, real in alt_names:
            if node_base == entry:
                node_base = real

        if node_base == "mix":
            node_base = "linearinterpolate"
        if "col" in node:
            cleanname = node_base + "node" + "_color"
        elif "vec" in node:
            cleanname = node_base + "node" + "_vector"
        else:
            cleanname = node_base + "node"

        if "GroupInput" not in node_base and "GroupOutput" not in node_base:
            for entry in nativename:
                if entry == cleanname:
                    realname = nativename[entry]
                    node_dict[node] = {realname: copy.deepcopy(native_data[realname])}

        else:
            if node not in node_dict:
                node_dict[node] = {node_base: {"inputs": [], "outputs": []}}
                #print(node_dict[node_base])

    return node_dict, blender_nodename_dict

def clean_links(socket_map, nodes, native_data):

    badlynamedsocks = {}

    for node in nodes:
        for sockmap in socket_map:
            if node == sockmap:
                node_attrs = next(iter(nodes[node].values()))
                sockmap_socks = socket_map[sockmap]
                #print(sockmap_socks)
                def get_sockets(node, node_attrs, sockmap_socks, direction, badlynamedsocks, socket_map):
                    if direction in node_attrs and sockmap_socks.get(direction):
                        nodesock = node_attrs[direction]
                        mapsock = sockmap_socks[direction]
                        if mapsock is not None:
                            nodestrings = set()
                            for sock in nodesock:
                                nodestrings.add(sock["identifier"].lower())
                                nodestrings.add(sock["name"].lower())
                            missing = [m for m in mapsock if m not in nodestrings]
                            if missing:
                                if node not in badlynamedsocks:
                                    badlynamedsocks[node] = {"inputs": [], "outputs": []}
                                badlynamedsocks[node].update({direction: missing})

                direction = "inputs"
                get_sockets(node, node_attrs, sockmap_socks, direction, badlynamedsocks, socket_map)
                direction = "outputs"
                get_sockets(node, node_attrs, sockmap_socks, direction, badlynamedsocks, socket_map)

    return badlynamedsocks

def rename_sockets(nodes, missingnodes, socket_map):

    transpose_keys = {
    "Value": ".1",
    "Vector": ".1",
    "A_": ".1",
    "Value_001": ".2",
    "Vector_001": ".2",
    "B_": ".2",
    "Factor_Float": ".f"
    }

    output_keys = {
    "Result": ".1",
    "Output": ".1",
    "Value": ".1",
    "Vector": ".1"
    }

    renamed_socks = {}

    def replace_socknames(missingnodes, socketmap, node, node_attrs, direction, keys, renamed_socks):
        missingsocks = missingnodes[node][direction]

        #print(f"Node {node} does not yet have proper socket names for {missingsocks}.")
        node_attrs = next(iter(nodes[node].values()))
        #print(missingsocks)
        identifiers = [item['identifier'] for item in node_attrs[direction]]
        #print(f"Node_sockmap: {node_sockmap}")

        for missingsocks in missingnodes[node][direction]:
            sock = missingsocks
            #print(sock)
            #print(f"This socket, {missingsocks}, for node {node} is in {direction}.")
            for attr in node_attrs:
                if attr == direction:
                    input_identifiers = [item['identifier'] for item in node_attrs[direction]]
                    #print(f"Your options for {sock} are: {identifiers}.")
                    #print(f"Do you want to rename {missingsocks} to {input_identifiers[0]}?")

                    for socket in identifiers:
                        #print(f"Sockets: {socket}")
                        if sock not in renamed_socks:
                            #print(missingsocks)
                            for k, v in keys.items():
                                if v in sock and k in socket:
                                    #print(f"changed {sock} to {socket} because of {k}")
                                    #print(f"Looking for {sock} in socket map:")
                                    if sock == missingsocks:
                                        #print(f"{socket} //  Socket_name == missingsocks: {sock}")
                                        sockmap = socket_map[node][direction]
                                        if node not in renamed_socks:
                                            renamed_socks[node] = {}
                                        renamed_socks[node].update({sock: socket})
                                        try:
                                            idx = sockmap.index(sock)  # find where 'result' is
                                            #print(f"sockmap: {sockmap}, index: {idx}")
                                            sockmap[idx] = socket   # replace it

                                        except ValueError:
                                            #print("ValueError")
                                            pass  # original_name not found, nothing to do

                                    missingsocks = socket
                                    break

    for node in missingnodes:

        if "GroupInput" not in node and "GroupOutput" not in node:
            nodestrings = set()
            direction = "inputs"
            replace_socknames(missingnodes, socket_map, node, nodes, direction, transpose_keys, renamed_socks)
            direction = "outputs"
            replace_socknames(missingnodes, socket_map, node, nodes, direction, output_keys, renamed_socks)

    #print(renamed_socks)
    #print(socket_map)
    return renamed_socks

#nodes: {'add.col.1': {'AddNode_color': {'autohide': True, 'inputs': [{'identifier': 'Value', 'index': 0, 'is_linked': True, 'name': 'Value', 'type': 'VALUE'}, {'identifier': 'Value_001', 'index': 1, 'is_linked': True, 'name': 'Value', 'type': 'VALUE'}], 'operation': 'ADD', 'outputs': [{'identifier': 'Value', 'index': 0, 'is_linked': True, 'name': 'Value', 'type': 'VALUE'}], 'type': 'ShaderNodeMath'}
#socket_map: {'add.col.1': {'inputs': ['inputsock.2', 'inputsock.3'], 'outputs': ['result']}, 'mult.vec.1': {'inputs': ['inputsock.1'], 'outputs': []}, 'add.vec.2': {'inputs': [], 'outputs': ['outputsock.2']}, 'add.3': {'inputs': [], 'outputs': ['outputsock.3']}}

def compile_nodes_and_links(nodes, socket_map, input_data, renamed_socks, blender_nodename_dict):

    #Like the function says. Compile each 'nodegroup' to send to output func.
    for nodegroup in input_data:
        #print(nodegroup)
        nodegroup_data = input_data[nodegroup]
        ng_details = nodegroup_data.get("NG_Details")  #<-- has sockets
        #pprint(ng_details)
        internal_nodes = nodegroup_data.get("nodes")  #<-- has internal nodes
        #pprint(internal_nodes)
        links = nodegroup_data.get("Links") #<-- has links.
        ng_details["name"] = nodegroup
        #print(ng_details)

    ng_interface = set()

    for outernode in nodes:
        for node in nodes[outernode]:
            if node == "GroupInput" or node == "GroupOutput":
                ng_interface.add(outernode)
                inputs = {}
                outputs = {}
                if node == "GroupInput":
                    used = set()
                    gpin_sockmap = socket_map[outernode]["outputs"]
                    idx = 0
                    for socket in gpin_sockmap:
                        if socket in used:
                            continue
                        else:
                            used.add(socket)
                            for sockets in ng_details["sockets"]:
                                if "outputs" in sockets:
                                    outputs = ng_details["sockets"]["inputs"]
                                    outputs.update({
                                        str(idx): socket
                                    })
                                    idx += 1

                if node == "GroupOutput":
                    used = set()
                    gpout_sockmap = socket_map[outernode]["inputs"]
                    idx = 0
                    for socket in gpout_sockmap:
                        if socket in used:
                            continue
                        else:
                            used.add(socket)
                            for sockets in ng_details["sockets"]:
                                if "inputs" in sockets:
                                    outputs = ng_details["sockets"]["outputs"]
                                    outputs.update({
                                        str(idx): socket
                                    })
                                    idx += 1

    internal_nodes = []
    x = -200
    y = 100

    nodetype_counts = defaultdict(int)
    lastnamedict = {}

    for node in nodes:
        for realname in nodes[node]:
            if realname.lower() in blender_nodename_dict:
                findname = realname.lower()
                nodetype = blender_nodename_dict[findname]
                if nodetype:
                    count = nodetype_counts[nodetype]
                    nodetype_counts[nodetype] += 1

                    if count == 0:
                        unique_nodetype = nodetype
                        lastnamedict.update({node: unique_nodetype})
                    else:
                        unique_nodetype = f"{nodetype}.{count:03d}"
                        lastnamedict.update({node: unique_nodetype})
                        print(lastnamedict)

        seen_nodes = set()
        optional_keys = ["operation", "data_type", "blend_type", "autohide"]
        if node not in ng_interface:
            if node not in seen_nodes:
                node_attrs = next(iter(nodes[node].values()))

                int_node = {
                    "name": unique_nodetype,
                    "type": node_attrs["type"],
                }
                print(int_node)
                for key in optional_keys:
                    if key in node_attrs:
                        int_node[key] = node_attrs[key]
                int_node["location"] = [x, y]
                x += 100
                y -= 50

                seen_nodes.add(node)
                internal_nodes.append(int_node)
    for link in links:
        print(link)
    all_links = []
    for feedernode, outputsock, eaternode, inputsock in links:
        if feedernode in renamed_socks:
            for k, v in renamed_socks[feedernode].items():
                if k == outputsock:
                    outsock = v
                    if feedernode in lastnamedict:
                        feedernode = lastnamedict[feedernode]

        if eaternode in renamed_socks:
            for k, v in renamed_socks[eaternode].items():
                if k == inputsock:
                    insock = v
                    if eaternode in lastnamedict:
                        eaternode = lastnamedict[eaternode]

        insock = inputsock
        outsock = outputsock
        print(f"{outputsock} = {outsock}")

        if not outsock:
            print("No outsock for {feedernode}, {outputsock}, {eaternode}, {inputsock}")
            print(link)
        if eaternode == "gpout":
            eaternode = "GroupOutput"
            insock = inputsock
        if feedernode == "gpin":
            feedernode = "GroupInput"
            outsock = outputsock


        links = [feedernode, outsock, eaternode, insock]
        print(links)
        all_links.append(links)

    ng_details["nodes"] = internal_nodes
    ng_details["links"] = all_links
    blueprints = {}

    for nodegroup in input_data:
        blueprints = {
            nodegroup: ng_details,
        }

    return blueprints

def output_blueprint(blueprints, output_path):

    with open(output_path, 'w', encoding='utf-8') as f_out:
        json.dump(blueprints, f_out, indent=2)
    print(f"[Info] Wrote reordered data to '{output_path}'")

def run(input_data, native_file, output_path):

    with open(native_file, "r", encoding="utf-8") as f:
        native_data = json.load(f)

    with open(input_file, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    socket_map = node_list(input_data)
    node_dict, blender_nodename_dict = get_native_node_details(native_data, socket_map, alt_names)
    missingnodes = clean_links(socket_map, node_dict, native_data)
    renamed_socks = rename_sockets(node_dict, missingnodes, socket_map)
    blueprints = compile_nodes_and_links(node_dict, socket_map, input_data, renamed_socks, blender_nodename_dict)
    output_blueprint(blueprints, output_path)

run(input_file, native_file, output_path)
