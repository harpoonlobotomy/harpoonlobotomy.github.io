## To run:
## command prompt: python "F:\Python_Scripts\LSMG_scripts\FINAL_LSMG_to_JSON_for_CLI\LSMG_5Stage_Wrapper.py" "D:\Steam\steamapps\common\Baldurs Gate 3\Data\Editor\Mods\Shared\Assets\Materials\Characters\CHAR_Fur.lsmg" --temp-dir "F:\test\wrapper_script_test_output"
#or
## command prompt: python LSMG_5Stage_Wrapper.py CHAR_Fur.lsmg --temp-dir wrapper_script_test_output

import os
import sys
import importlib.util
import argparse

# Get the directory this script is in
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def import_script(script_filename, module_name):
    script_path = os.path.join(SCRIPT_DIR, script_filename)
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def make_temp_path(stage_name, input_basename, use_named_tmp, temp_dir, ext=".json"):
    if use_named_tmp:
        return os.path.join(temp_dir, f"{stage_name}_tmp_{input_basename}{ext}")
    else:
        return os.path.join(temp_dir, f"{stage_name}_tmp{ext}")


def run_pipeline(input_lsmg_path, use_named_tmp=True, temp_dir="temp_pipeline_outputs"):
    os.makedirs(temp_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_lsmg_path))[0]

    # Import all stage scripts from SCRIPT_DIR
    LSMG_stage1_xml_block_extractor = import_script("LSMG_stage1_xml_block_extractor.py", "stage1")
    LSMG_stage2_txt_to_json = import_script("LSMG_stage2_txt_to_json.py", "stage2")
    LSMG_stage3_chains_from_json = import_script("LSMG_stage3_chains_from_json.py", "stage3")
    LSMG_stage4_forward_tracer = import_script("LSMG_stage4_forward_tracer.py", "stage4")
    LSMG_stage5_merge_2and5_final_output = import_script("LSMG_stage5_merge_2and5_final_output.py", "stage5")

    # Stage 1
    txt_out = make_temp_path("stage_1", base_name, use_named_tmp, temp_dir, ext=".txt")
    LSMG_stage1_xml_block_extractor.run(input_lsmg_path, txt_out)
    print(f"{base_name} Stage One completed.")

    # Stage 2
    json2_out = make_temp_path("stage_2", base_name, use_named_tmp, temp_dir)
    LSMG_stage2_txt_to_json.run(txt_out, json2_out)
    print(f"{base_name} Stage Two completed.")

    # Stage 3
    json3_out = make_temp_path("stage_3", base_name, use_named_tmp, temp_dir)
    LSMG_stage3_chains_from_json.run(json2_out, json3_out)
    print(f"{base_name} Stage Three completed.")

    # Stage 4
    json4_out = make_temp_path("stage_4", base_name, use_named_tmp, temp_dir)
    LSMG_stage4_forward_tracer.run(json3_out, json4_out)
    print(f"{base_name} Stage Four completed.")

    # Stage 5 (with bundled reference files)
    blender_ref = os.path.join(SCRIPT_DIR, "blender_native_node_ref.json")
    exported_groups = os.path.join(SCRIPT_DIR, "blender_nodegroups_for_generation.txt")
    final_out = make_temp_path("stage_5", base_name, use_named_tmp, temp_dir)

    LSMG_stage5_merge_2and5_final_output.run(
        json2_out, json4_out, blender_ref, exported_groups, final_out
    )
    print(f"{base_name} Stage Five completed.")

    print(f"Pipeline completed. Final output: {final_out}")

# CLI entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LSMG processing pipeline.")
    parser.add_argument("input_file", help="Input LSMG file (e.g., CHAR_Fur.lsmg)")
    parser.add_argument("--named-temp", action="store_true", help="Use input-name-based temp files")
    parser.add_argument("--temp-dir", default="temp_pipeline_outputs", help="Folder to store temporary/intermediate outputs")

    args = parser.parse_args()
    run_pipeline(args.input_file, use_named_tmp=args.named_temp, temp_dir=args.temp_dir)
