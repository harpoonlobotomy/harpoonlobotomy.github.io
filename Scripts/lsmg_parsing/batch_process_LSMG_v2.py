import os
import subprocess
import sys

print(f"[DEBUG] Starting {__file__}", file=sys.stderr)
print(f"[DEBUG] Args: {sys.argv}", file=sys.stderr)

# === CONFIG ===
INPUT_ROOT = r"D:\input\folder\like\Baldurs Gate 3\Data\Editor\Mods\Shared\Assets\Materials"
OUTPUT_ROOT = r"F:\output\folder"

EXTRACT_SCRIPT = "xml_block_extractor_for_cli_v1_enums.py"
PARSE_SCRIPT = "LSMG_to_JSON_for_CLI_v2.py"

def process_file(xml_path, relative_path):
    base_name = os.path.splitext(os.path.basename(xml_path))[0]
    temp_txt_path = os.path.join(OUTPUT_ROOT, base_name + ".txt")
    json_output_path = os.path.join(OUTPUT_ROOT, base_name + ".json")

    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    # Step 1: Run extract_blocks.py
    try:
        with open(temp_txt_path, 'w', encoding='utf-8') as txt_out:
            subprocess.run(["python", EXTRACT_SCRIPT, xml_path], stdout=txt_out, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] extract_blocks failed on {xml_path}: {e}")
        return

    # Step 2: Run parse_blocks.py
    try:
        with open(json_output_path, 'w', encoding='utf-8') as json_out:
            subprocess.run(["python", PARSE_SCRIPT, temp_txt_path], stdout=json_out, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] parse_blocks failed on {temp_txt_path}: {e}")
        return

    print(f"Processed: {xml_path} -> {json_output_path}")

def walk_and_process():
    for root, dirs, files in os.walk(INPUT_ROOT):
        rel_root = os.path.relpath(root, INPUT_ROOT)
        for file in files:
            if file.lower().endswith(".lsmg"):
                xml_path = os.path.join(root, file)
                rel_path = os.path.normpath(rel_root)
                process_file(xml_path, rel_path)

if __name__ == "__main__":
    walk_and_process()
