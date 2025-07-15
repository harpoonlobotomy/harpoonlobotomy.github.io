LSMG parsing scripts:

Run "batch_process_LSMG_v2.py" with desired input and output folder set in the script.

It runs:
>  xml_block_extractor_for_cli_v1_enums.py (breaks the LSMG into blocks, outputs a txt file)
>  LSMG_to_JSON_for_CLI_v2.py (parses the text file to get clean 'node' and 'connection' blocks for use with Blender template generation script, outputs JSON)

Created by harpoonlobotomy, with a lot of coding help from ChatGPT because I've not coded before this project, and had a lot of ambitions. Still weeks of work, though; getting the parsers right was a little more difficult than I expected, but, finally, they do work.

These are designed to be compatible with a Blender companion script that creates the nodegraph as a new material. 

They also provide data to another script that generates custom nodegroups, though that still needs more work before its worth sharing.

I don't think anyone's really dug into the LSMG files before; I suppose there's not much point unless you're using the LSF files directly. I have those parsed with companion blender scripts too, although that blender script links into a sqlite database, using a wide variety of source files to build a map from 'selected GR2 asset' to all material assets and parameters. 

//Maybe I should add the LSMG data to the database. Would make sense. I'll add all the database scripts later, perhaps.//

Anyway -- I'm just sharing these here in case anyone else out there has been wanting to recreate the BG3 shaders from scratch in blender like I did; I legitimately couldn't find any resources to do this, and so - poor quality code and all - now there's something, at least. There are a number of features that just don't apply in Blender (like TAA dithering, shadow switches) but the nodegroups are still complete, and all parts that can function in Blender space, do.

(It took me a good few days to even understand how to interpret the LSMG files, but I think I'm kind of an expert now?)

-harpoon
