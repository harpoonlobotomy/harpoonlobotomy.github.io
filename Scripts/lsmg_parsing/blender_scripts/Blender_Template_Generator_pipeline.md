# Blender Template Generator Pileline:

# Wrapper script ## --
Runs all 5 parse/processor scripts and produces stage_5_tmp_CHAR_BASE_VT.json for use with template generator script. You must provide the LSMG file for this script to generate from.

Stage 5's script requires Native Nodes doc ("blender_native_node_ref.json") and the nodegroups doc ("frame_exported_nodegroups_6.json").
The nodegroups doc is also used in the template generator itself. Both still require updating, as any as-yet undiscovered nodes have not been added,
and any as-yet undiscovered nodegroups have not been created.

# Required docs:
To generate the native nodes doc, the nodes must be present and linked in a blender file, and exported via a script (BLENDER_export_native_node_data.py).
To generate the nodegroups doc, using BLENDER_export_frames_for_nodegroup_gen_to_json.py. The nodegroups must be ungrouped and added to a Frame, with 'group input' and 'group output' represented by reroute nodes, labelled "input0/[SocketName]"; the input/output and numeral here will be translated to group input/output sockets, and the [SocketName] applied to that socket.
Alternatively, to generate the nodegroups doc, nodegroup_blueprint_writer.py can be used with an input file to convert shorthand input with nodegroup details and links, and will output the same format as the 'export frames' script, and can be used by the nodegroup gen and templategen scripts in Blender.
(Currently this is still quite a manual process as each native node needs accurate name conversion and each nodegroup needs to be in the processor output. I'm looking at changing this, potentially.)

# Usage: 
To generate the templates, there must be an active object in Blender. Currently the templates must be created with BLENDER_template_generator.py directly, but I'm working on hooking it into the material generator for automatic template creation. 

This is the state of things as of 12/8/25.
