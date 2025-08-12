# Nodegraph Processing Pipeline Overview

This document outlines the five-stage processing pipeline used to convert raw LSMG nodegraph files into Blender-compatible data, with accurate node and socket data types and structure.

In brief summary: If you give it a BG3 LSMG (material template) file, it will produce a JSON file that can be used in Blender (with the appropriate companion script in Blender) to rebuild a nodegraph.
Also potentially works with other UE4-based material nodegraphs' XML-like documents, but this is untested.

-harpoon


 -----
# Stage 1: LSMG_stage1_xml_block_extractor.py
    Input example: CHAR_Fur.lsmg
    Output example: stage_1_tmp_CHAR_Fur.txt

# Stage 2: LSMG_stage2_txt_to_json.py
    Input example: stage_1_tmp_CHAR_Fur.txt
    Output example: stage_2_tmp_CHAR_Fur.json

# Stage 3: LSMG_stage3_chains_from_json.py
    Input example: stage_2_tmp_CHAR_Fur.json
    Output example: stage_3_tmp_CHAR_Fur.json

# Stage 4: LSMG_stage4_forward_tracer.py
    Input example: stage_3_tmp_CHAR_Fur.json
    Output example: stage_4_tmp_CHAR_Fur.json

`( Stage 4.5: Getting nodes/sockets.
    Run `BLENDER_export_native_node_data.py` to get native sockets.
    (Key names should match the LSMG node_type.)

    For nodegroups, run `BLENDER_export_frames_for_nodegroup_gen_to_json.py`,
    with frame names as the node_type.
    See `Core_Script_Overview.md` for slightly more detail. )`

# Stage 5: LSMG_stage5_merge_2and5_final_output_ngblocks_vers.py
    Input Example:
        `stage_2_tmp_CHAR_Fur.json`
        `stage_4_tmp_CHAR_Fur.json`
        `blender_native_node_ref.json`
        `blender_exported_nodegroups_for_gen`
    Output Example: `stage_5_tmp_CHAR_Fur.json`
	* Will also produce a _missing_nodes.json if any missing nodes are found.
	*	Note: These files are input automatically by the wrapper, and do not need to be separately added. Any file locations/folders are provided at the Wrapper level.
	*	Currently, only the LSMG file and the script are given as CLI commands.
---

# Wrapper: LSMG_5Stage_Wrapper_jsonvers.py
	Input example: CHAR_Fur.lsmg
		* + native_node_ref and frame_exported_nodegroups
	Output example: stage_5_tmp.json


## Stage 1 – Block Compression (Lexical Preprocessing)

**Purpose:**
Break the raw, non-XML-parseable file into discrete structural blocks.

**Challenges:**
- The file resembles XML but is malformed and deeply nested.
- Single nodes can span hundreds of lines.
- Requires manual nesting compression and block recognition.

**Outcome:**
- Each logical block (e.g. one node, or a connection) is compressed into a small number of lines.
- Output is a cleaned-up list of blocks ready for parsing.

---

## Stage 2 – Initial Parsing (Syntactic Pass)

**Purpose:**
Extract all essential node and connection data.

**Process:**
- Identify all nodes, their properties, inputs, outputs.
- Identify all connections (edges), linking socket IDs.

**Output:**
- A JSON file with:
  - A list of nodes (with identifiers and socket info).
  - A list of connections (each linking FromSocketID → ToSocketID).
- Enough data to build a **basic Blender nodegraph** (no types yet).

---

## Stage 3 – Chain Generation (Graph Mapping)

**Purpose:**
Convert connection data into meaningful directional chains.

**Details:**
- Traverse connection data to create **branches** of linked nodes.
- Convert raw socket-to-socket links into high-level flow paths (leaf → terminal).

**Note:**
- This stage does not yet assign any types — it builds *structure only*.

---

## Stage 4 – Dependency Typing (Semantic Pass)

**Purpose:**
Perform **forward-tracing data type inference** along chains.

**Process:**
- Starting from known data types, propagate type information forward.
- Apply overrides and exceptions:
  - Enum-based nodes (e.g. Mix, Clamp)
  - Node-specific type exceptions (e.g. DotProduct always outputs Scalar)
  - Socket-specific overrides where applicable

**Output:**
- A new JSON structure mapping:
  - Each node to its inferred **data type**
  - Each chain to its **typed flow path**

---

## Stage 5 – Merge + Type Annotation (IR Normalization)

**Purpose:**
Combine raw node metadata with discovered data types to produce a Blender-usable format.

**Process:**
- Merge stage 2 (raw nodes + sockets) with stage 4 (node data types).
- Assign **socket-level types** using:
  - Node data type
  - Socket role and position
  - Known socket overrides
  - Native and Nodegroup node and socket mapping file
- Map to:
  - Blender native node classes (e.g. ShaderNodeVectorMath)
  - Node operations (e.g. Multiply, Dot Product)
  - Mix Node blend_type and data_type (Eg 'Color, Multiply' for 'Mix Color' set to 'Multiply')
  - Nodegroup replacements where needed (e.g. custom 'Power_vector')

**Output:**
- A fully enriched JSON representation of the nodegraph:
  - Accurate data types at node and socket level
  - Identified Blender node classes or nodegroup substitutes
  - Connection structure ready for Blender import
  - Also supports nodeblock replacement - for specific sequences where accurate nodebranch replication is impossible due to blender limitations (eg 4 channel vectors).
		The node sequence generator will add flags to affected nodes, which will then be read by the template generator in Blender where they will be replaced by a custom nodegroup that accurately replicates the function.

---

## Notes on Design Philosophy

- Each stage is modular and debuggable.
- Earlier stages are **intentionally verbose**, trading off complexity for clarity.
- Later stages refine and annotate without mutating earlier assumptions.
- Consolidation into fewer scripts is theoretically possible, but not currently beneficial.
- A wrapper script (`LSMG_5Stage_Wrapper_jsonvers.py`) compiles these into one toolchain, so the number of scripts does not impact usability.

---

harpoonlobotomy, July 2025



---

# Changelog:

27/07/25

Updated the Stage5 and Wrapper scripts to use a JSON-type nodegroup file instead of the original .txt file.
Replaced the text file with the new .json version.

Now, the focus is on remaking the blender integration scripts.
Hopefully not too many more changes to these LSMG scripts; that'll just depend on if I realise I've missed something I'll need later.

-harpoon

----

5/8/25

Updated stages 1, 3 and 5 slightly to fix... something. I've genuinely forgotten what, but I do remember being pleased. 
Also added the current version of the nodesequence_tracer script - it finds (currently just one) specific pattern within a nodegraph (using the output from Stage3) and reports back;
I'm amending the Blender Template Generator script to use this bulk-replacement so replicate 4-channel-specific portions of nodetrees. Currently, just the main VT_Layer pattern, but it's potentially expandable. 

Also: Added new variants of the Stage 5 script and the Wrapper, and a CLI version of the node sequence tracer script that all work together, and add the relevant details of the nodegroup into the final output file. 

The Blender templategen doesn't account for it yet, but it's in the works. Next few days, maybe. 

I've worked on almost 500 scripts in 3 months now. I'm still rubbish at it, but I'm starting to be quicker at figuring out what's wrong and now and then, actually doing something good. I came at this backwards, starting with pretty intense stuff I couldn't even understand and now getting to grips with the basics. I really love it, actually. Didn't expect that.

I want to look into what would be required to adapt the 5StageScripts to import more general UE material files. 

Next up: 
> Incorporate the nodegroup_blocks into the TempGen, and actually finish the nodegroup_blocks script - not much left, but I'm tired. 
> Update the TempGen and MatGen to work together; currently, MatGen needs the Template pre-generated. I want to hook them together so that if the template is missing, MatGen will call Tempgen, pass it the required filename and it'll run the rest. 
	(Including, hopefully, triggering the 5StageScripts to run on said file, so the MatGen would go from data-base-only to generated-template entirely within itself. That's the dream, I think.
> Adapt the nodegroup_blocks script to use an external Pattern file, so I can set it to find any number of specific sequences with specific replacements. 
> Change how TempGen 'finds' Nodegroups. Currently you have to re-parse (or manually add) the 'is_nodegroup' flag for them to be recognised, which is just silly. I'll use a dynamic list from the nodegroup file instead.
> At some point actually make things in Blender again.
> There was more, but I'm genuinely really tired. 

- Harpoon.

----

12/8/25
Updated everything, again. Nodegroup blocks are now completely integrated into the TempGen, though not yet integrated that into the MatGen.  TempGen is much better now. 
Also added a nodegroup writer script, so you can provide nodegroup details and desired links in specific shorthand and it will generate the framed_nodegroups JSON output format, to avoid the 'frame' framework if desired. 

- harpoon