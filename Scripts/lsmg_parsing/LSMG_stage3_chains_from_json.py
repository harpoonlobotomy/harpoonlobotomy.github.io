#create connection blocks that include internal sockets of both to and from nodes
#working internal socket names and enums added when present

import json

def build_internal_socket_map(nodes):
    """
    Build mapping of external socket ID → (node_id, internal_socket_name)
    by searching Internal_Connectors, m_Inputs.Connectors, and m_Outputs.Connectors.
    Falls back to "" if no socket name is available.
    """
    socket_map = {}

    for node_id, node_data in nodes.items():
        # Internal connectors

        # Input connectors
        for conn in node_data.get("m_Inputs", {}).get("Connectors", []):
            socket_id = conn.get("Socket_Id")
            conn_name = conn.get("Conn_Name", "")
            if socket_id:
                socket_map[socket_id] = (node_id, conn_name)

        # Output connectors
        for conn in node_data.get("m_Outputs", {}).get("Connectors", []):
            socket_id = conn.get("Socket_Id")
            conn_name = conn.get("Conn_Name", "")
            if socket_id:
                socket_map[socket_id] = (node_id, conn_name)

        for conn in node_data.get("Internal_Connectors", []):
            socket_id = conn.get("ID") or conn.get("Socket_Id")
            internal_socket_name = conn.get("Socket", "")
            if socket_id:
                socket_map[socket_id] = (node_id, internal_socket_name)

    return socket_map

def build_enum_map_from_nodes(nodes):
    """
    Build a mapping of socket_id -> enum_value by scanning all connectors in all nodes.
    """
    enum_map = {}

    for node_data in nodes.values():
        for group_key in ["m_Inputs", "m_Outputs"]:
            connectors = node_data.get(group_key, {}).get("Connectors", [])
            for conn in connectors:
                socket_id = conn.get("Socket_Id")
                enum_val = conn.get("Enum")
                if socket_id and enum_val is not None:
                    enum_map[socket_id] = enum_val
        # Also check internal connectors if needed
        for conn in node_data.get("Internal_Connectors", []):
            socket_id = conn.get("ID") or conn.get("Socket_Id")
            enum_val = conn.get("Enum")
            if socket_id and enum_val is not None:
                enum_map[socket_id] = enum_val

    return enum_map

def enrich_connections_with_internal_sockets(data):
    """
    Enrich the Connections dict with:
    - From_Node and From_Internal_Socket
    - To_Node and To_Internal_Socket
    - From_Node_Type_Name
    - To_Node_Type_Name
    """
    nodes = data.get("Nodes", {})
    connections = data.get("Connections", {})

    socket_map = build_internal_socket_map(nodes)
    enum_map = build_enum_map_from_nodes(nodes)  # get enum info here
    enriched_connections = {}

    for conn_id, conn in connections.items():
        from_socket = conn.get("From_Socket")
        to_socket = conn.get("To_Socket")

        from_node, from_internal = socket_map.get(from_socket, (None, None))
        to_node, to_internal = socket_map.get(to_socket, (None, None))

        # Build formatted labels
        from_label = None
        if from_node and from_node in nodes:
            node_data = nodes[from_node]
            from_label = f"{node_data.get('Node_Type', '')} / {node_data.get('Node_Name', '')}"

        to_label = None
        if to_node and to_node in nodes:
            node_data = nodes[to_node]
            to_label = f"{node_data.get('Node_Type', '')} / {node_data.get('Node_Name', '')}"

        # Find from_socket_name from nodes structure if possible
        if from_node and from_socket:
            from_node_data = nodes.get(from_node, {})
            # Search m_Inputs and m_Outputs connectors for matching Socket_Id
            for group_key in ["m_Inputs", "m_Outputs"]:
                for c in from_node_data.get(group_key, {}).get("Connectors", []):
                    if c.get("Socket_Id") == from_socket:
                        from_socket_name = c.get("Conn_Name", "")
                        break

        # Same for to_socket_name
        if to_node and to_socket:
            to_node_data = nodes.get(to_node, {})
            for group_key in ["m_Inputs", "m_Outputs"]:
                for c in to_node_data.get(group_key, {}).get("Connectors", []):
                    if c.get("Socket_Id") == to_socket:
                        to_socket_name = c.get("Conn_Name", "")
                        break

        # Same for to_socket_name
        if to_node and to_socket:
            to_node_data = nodes.get(to_node, {})
            for group_key in ["m_Inputs", "m_Outputs"]:
                for c in to_node_data.get(group_key, {}).get("Connectors", []):
                    if c.get("Socket_Id") == to_socket:
                        to_socket_name = c.get("Conn_Name", "")
                        break

        enriched_conn = {
            "z:Id": conn_id,
            "From_Node": from_node,
            "From_Node_Type_Name": from_label,
            "From_Internal_Socket": from_internal,
            "From_Socket": from_socket,
        }

        from_enum = enum_map.get(from_socket)
        if from_enum:
            enriched_conn["From_Socket_Enum"] = from_enum

        enriched_conn.update({
            "From_Socket_Name": from_socket_name,
            "To_Node": to_node,
            "To_Node_Type_Name": to_label,
            "To_Socket": to_socket,
        })

        to_enum = enum_map.get(to_socket)
        if to_enum:
            enriched_conn["To_Socket_Enum"] = to_enum

        enriched_conn.update({
            "To_Socket_Name": to_socket_name,
            "To_Internal_Socket": to_internal,
        })

        enriched_connections[conn_id] = enriched_conn

    return enriched_connections

def run(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = enrich_connections_with_internal_sockets(data)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2)
        print(f"Wrote structured JSON to: {output_path}")


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python LSMG_stage3_chains_from_json.py input.json [output.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "enriched_output.json"

    run(input_path, output_path)
