# Blender Template Generator Pileline:

# Wrapper script ## --
Runs all 5 parse/processor scripts and produces stage_5_tmp_CHAR_BASE_VT.json for use with template generator script.

Stage 5's script requires Native Nodes doc ("blender_native_node_ref.json") and the nodegroups doc ("frame_exported_nodegroups_3.json").
The nodegroups doc is also used in the template generator itself. Both still require updating, as any as-yet undiscovered nodes have not been added,
and any as-yet undiscovered nodegroups have not been created.

# Required docs:
To generate the native nodes doc, the nodes must be present and linked in a blender file, and exported via a script (BLENDER_export_native_node_data.py).
To generate the nodegroups doc, the nodegroups must be ungrouped and added to a Frame, with 'group input' and 'group output' represented by reroute nodes, labelled "input0/[SocketName]"; the input/output and numeral here will be translated to group input/output sockets, and the [SocketName] applied to that socket.
Currently this is still quite a manual process.

This is the state of things as of 31/7/25.
