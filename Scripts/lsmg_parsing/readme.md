# Nodegraph Processing Pipeline Overview

This document outlines the five-stage processing pipeline used to convert raw LSMG nodegraph files into Blender-compatible data, with accurate node and socket data types and structure.

In brief summary: If you give it a BG3 LSMG (material template) file, it will produce a JSON file that can be used in Blender (with the appropriate companion script in Blender) to rebuild a nodegraph.
Also potentially works with other UE4-based material nodegraphs' XML-like documents, but this is untested.

These scripts are all triggered as needed from within the Material_Generator script if run in Blender; it will find the required template file, trigger file generation, etc. Alternatively, the process can be triggered manually via CLI, with some scripts also able to run independently outside of this process entirely.

I believe this document is up to date as of 30/8/25.

-harpoonLobotomy


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
		*Supplementary:
			`pattern_mapping.json`
			`nodesequence_tracer_pseudonode_cli.py`
	Output example: stage_4_tmp_CHAR_Fur.json
		*Supplementary:
			`ng_blocks_tmp_CHAR_Fur.json` if any Pattern is found.

	[Note: Use of Patterns is on by default, can be turned off with cli command `--disabled_patterns`]
	

# Stage 5: LSMG_stage5_merge_2and5_final_output_ngblocks_vers.py
    Input Example:
        `stage_2_tmp_CHAR_Fur.json`
        `stage_4_tmp_CHAR_Fur.json`
        `native_node_ref.json`
        `nodegroup_blueprints.json`
		* Supplementary:
			`ng_blocks_tmp_CHAR_Fur.json` if Pattern was found.
    Output Example: `stage_5_tmp_CHAR_Fur.json`
	* Will also produce a _missing_nodes.json if any missing nodes are found.

---

# Wrapper: LSMG_5Stage_Wrapper_jsonvers.py
    Input example: CHAR_Fur.lsmg
      * + `native_node_ref.json` and `nodegroup_blueprints.json`
    Output example: stage_5_tmp.json

# Supplementary files:
    For native_node_ref:
      Run `BLENDER_export_native_node_data.py`.
    (Key names should match the LSMG node_type.)

    For nodegroups:
    Once nodegroups are created and present in Blender file, make that material Active and applied the the Active object.
      Run `BLENDER_export_nodegroup_data_whole.py`.

    For Patterns:
      `node_sequencer_shorthand_converter.py` can be used to assist, but socket & node names must be changed to match the input JSON; this is not yet automated.
      Pattern sequences must match exactly or the pattern will fail; this is intentional to reduce the chance of false positives, as those would be very bad.
      Patterns currently require the most hand-authoring of any part of the process. When the Pattern is finalised, and Pattern nodegroup provided in Nodegroup Blueprints .json, no futher manual intervention is required.


## Stage 1 – Block Compression (Lexical Preprocessing)

**Purpose:**
Break the raw, non-XML-parseable file into discrete structural blocks.

**Challenges:**
- The file resembles XML but is malformed and deeply nested.
- Single nodes can span many hundreds of lines.
- Requires manual nesting compression and block recognition.

**Outcome:**
- Each logical block (e.g. one node, or one to/from connection) is compressed into a small number of lines, isolated from the nesting.
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
- If not disabled, apply Pattern data to chains:
  - Amend node data, and create 'pseudonodes' to replace 'Pattern chains'.
  - `Pattern chains` are sequences of nodes that are impossible to replicate accurately within blender natively.
  - Where a Pattern Blueprint exists to replicate that function, it is inserted in the final nodegraph, replacing the original nodebranch section and taking on its connections.

**Output:**
- A new JSON structure mapping:
  - Each node to its inferred **data type**
  - Each chain to its **typed flow path**
- A Pattern JSON, if any pattern is found.
  - The Pattern JSON is used by the later script to identify the Pattern 'state' of nodes, to determine if they should be instanced or not and how their connection (input or output) should be passed on.

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
  - If relevant, Pattern role per node.

**Output:**
- A fully enriched JSON representation of the nodegraph:
  - Accurate data types at node and socket level
  - Identified Blender node classes or nodegroup substitutes
  - Connection structure ready for Blender import
  - Nodeblock replacement data


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

----

30/8/25
Updated everything again. Patterns are now fully integrated into the pipeline. Full script call integration is also achieved - only Matgen needs to be present in Blender. When run, if the Template is not found in the Blend, it will call Template_Generator. Template_Generator will look for the stage5 output file - if not found, it will call the wrapper script and produce the file automatically, at which point Template_Generator and Material_Generator will both run.

Added the ability to apply materials to multiple selected objects, instead of having to run them one at a time per asset.
Implemented reroute-skips, adding more flexibility for connecting to _Alpha and _W sockets for ComponentMask_W nodes.
Implemented material-level UV Map indexes, so reusing a template on a different asset no longer requires manual UV Map realignment.
Template_Generator now adds template-level image textures, and Material_Generator only adds images/parameters flagged as 'Enabled' for that material.

Still todo:
>  Recursive nodegroups; currently nodegroups can only be created at the 'top level', and inside of other nodegroups.
>  Finalise the Pattern generation process; still very manual and time consuming compared to other processes.
>  More Patterns need to be written, see above.
>  Need a proper document outlining which Templates have issues that require resolution. Most issues now are at the Template level, not the systemic.

- harpoon