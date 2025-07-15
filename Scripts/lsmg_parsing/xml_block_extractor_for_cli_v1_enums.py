#includes 'dirty'/noisy Nodeblocks at the end for location data

import re
import sys

if len(sys.argv) < 2:
    print("Usage: python extract_blocks.py input.xml [output.txt]")
    sys.exit(1)

input_path = sys.argv[1]
output_path = sys.argv[2] if len(sys.argv) > 2 else None

with open(input_path, 'r', encoding='utf-8') as f:
    xml_data = f.read()


OUTPUT_FILE = r"F:\Python_Scripts\LSMG_scripts\test.txt"
ISOLATE_LINES = False  # Run simple isolate lines function
ISOLATE_TAG = "Collapsed"
ISOLATE_FOLLOWING = 4

ENABLE_TRIM_ENDTAGS = False  # or False to disable

RUN_BLOCK_PARSER = False  # Run original block extractor
RUN_PARENT_EXCLUDE_NESTED = True  # Run new parent-exclude-nested extractor

PARENT_BLOCK_PATTERNS = [
    {
        "tag": "Node",
        "include": ["Location", "m_Inputs", "m_Outputs"],
        "preserve_starts": ["<d21p1:x>", "m_Inputs", "m_Outputs"]
    },
    {
        "tag": "m_Inputs",
        "include": ["NodeConnector", "Node"],
    },
    {
        "tag": "m_Outputs",
        "include": ["NodeConnector"],
    },
    {
        "tag": "m_Connections",
        "exclude": ["Tag", "RenderFlag", "m_Connections", "Node", "Enabled", "DummyInputBounds", "Collapsed", "NameSize", "m_Inputs", "m_Outputs", "DummyOutputBounds"],  # maybe this one allows Name
        "preserve_starts": ["Node", "m_Inputs", "m_Outputs"]
    },
    {
        "tag": "Node",
        "exclude": ["d2p1:ExportAsPreset", "Collapsed", "DummyInputBounds", "DummyOutputBounds", "ImageFileName", "NameSize", "NodeDescription", "RefreshConnectorNamesImage", "OriginalName", "RenderFlag", "NodeConnector"]
    },
    {
        "tag": "NodeConnection",
        "exclude": ["m_Connections", "d2p1:ExportAsPreset", "Collapsed", "DummyInputBounds", "DummyOutputBounds", "ImageFileName", "NameSize", "NodeDescription", "RefreshConnectorNamesImage", "OriginalName", "RenderFlag", "NodeConnector"]
    },
]


def tag_line(tag_name, attrs=None, self_close=False, open_only=False):
    attr_pattern = ""
    if attrs:
        attr_pattern = "".join([fr'\s+{re.escape(k)}="[^"]+"' for k in attrs])
    # Optional i:type attribute with namespace prefix
    optional_itype = r'(?:\s+i:type="[a-zA-Z0-9_]+:[^"]+")?'

    # Compose full pattern with optional i:type after required attrs
 #   if self_close:
    if self_close:
        pattern = fr'^<{tag_name}{attr_pattern}{optional_itype}\s*/>$'
    elif open_only:
        pattern = fr'^<{tag_name}{attr_pattern}{optional_itype}>$'
    else:
        pattern = fr'^<{tag_name}{attr_pattern}{optional_itype}>.*</{tag_name}>$'
    return re.compile(pattern)


# === BLOCK PATTERNS ===
BLOCK_PATTERNS = [
    {
        "name": "NodeConnectorBlock",
        "length": 4,
        "matchers": [
            tag_line("NodeConnector", attrs={"z:Id": ""}, open_only=True),
            tag_line("Enabled"),
            tag_line("Name", attrs={"z:Id": ""}),
            tag_line("Node", attrs={"z:Ref": "", "i:nil": ""}, self_close=True)
        ]

    },
]
# --- Existing functions like isolate_lines_with_following, extract_all_blocks here ---


# === BLOCK MATCHING FUNCTION ===
def try_match_block(lines, start_index, block_pattern):
    block_len = block_pattern["length"]
    if start_index + block_len > len(lines):
        return None
    candidate = lines[start_index:start_index + block_len]

    for i, matcher in enumerate(block_pattern["matchers"]):
        candidate_line = candidate[i].strip()

        if not matcher.match(candidate_line):
            print("MISMATCH on line", start_index + i, candidate_line)
            return None
        else:
            print("MATCH\n")

    return "\n".join(candidate)



# === MAIN BLOCK EXTRACTION ===
def extract_all_blocks(filepath):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.read().replace('\r\n', '\n').split('\n')

    blocks_found = []
    i = 0
    while i < len(lines):
        matched = False
        for pattern in BLOCK_PATTERNS:
            result = try_match_block(lines, i, pattern)
            if result:
                blocks_found.append((pattern["name"], result))
                i += pattern["length"]
                matched = True
                break
        if not matched:
            i += 1
    return blocks_found


# === ISOLATE TAG + FOLLOWING LINES ===
def isolate_lines_with_following(filepath, tag_start, following_lines):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.read().replace('\r\n', '\n').split('\n')
    matches = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith(f"<{tag_start}"):
            chunk = lines[i:i + 1 + following_lines]
            matches.append("\n".join(chunk))
        i += 1
    return matches
# --- Add build_block_index and exclude_nested_blocks from previous answer here ---


def build_block_index(lines):
    tag_open_re = re.compile(r'<(\w+)(?:\s|>)')
    tag_close_re = re.compile(r'</(\w+)>')
    self_closing_re = re.compile(r'<(\w+)(?:\s[^>]*)?/>')
    self_closing_ns_re = re.compile(r'<(\w+:\w+)(?:\s[^>]*)?/>')

    inline_tag_re = re.compile(r'^<(\w+)>\s*[^<]*\s*</\1>$')
    inline_tag_ns_re = re.compile(r'^<(\w+:\w+)(?:\s[^>]*)?>[^<]*</\1>$')

    stack = []
    blocks = []



    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Self-closing (no namespace)
        m = self_closing_re.match(stripped)
        if m:
            blocks.append({"tag": m.group(1), "start": i, "end": i})
            continue

        # Self-closing with namespace
        m = self_closing_ns_re.match(stripped)
        if m:
            blocks.append({"tag": m.group(1), "start": i, "end": i})
            continue

        # Inline (no namespace)
        m = inline_tag_re.match(stripped)
        if m:
            blocks.append({"tag": m.group(1), "start": i, "end": i})
            continue

        # Inline with namespace
        m = inline_tag_ns_re.match(stripped)
        if m:
            blocks.append({"tag": m.group(1), "start": i, "end": i})
            continue

        # Closing tags
        m = tag_close_re.match(stripped)
        if m:
            tag = m.group(1)
            for idx in range(len(stack) - 1, -1, -1):
                if stack[idx][0] == tag:
                    start_tag, start_line = stack.pop(idx)
                    blocks.append({"tag": tag, "start": start_line, "end": i})
                    break
            continue

        # Opening tag
        m = tag_open_re.match(stripped)
        if m:
            tag = m.group(1)
            if not stripped.endswith('/>') and not stripped.startswith('</'):
                stack.append((tag, i))

    return blocks

def exclude_nested_blocks(lines, parent_start, parent_end, blocks, blacklist_tags, preserve_starts=None):
    """
    Given lines and full block index,
    remove lines corresponding to nested blocks inside parent,
    if block.tag in blacklist_tags and block is inside parent range.
    Optionally preserve the starting line of some tags.
    """
    preserve_starts = preserve_starts or []

    # Collect line ranges to exclude
    exclude_ranges = []
    for block in blocks:
        if block["tag"] in blacklist_tags:
            if (parent_start < block["start"] and block["end"] < parent_end
                ) or (
                    block["start"] == block["end"] and parent_start < block["start"] <= parent_end
                ):


                if block["tag"] in preserve_starts:
                    exclude_ranges.append((block["start"] + 1, block["end"]))  # skip just body
                else:
                    exclude_ranges.append((block["start"], block["end"]))     # skip full block

    # Merge overlapping or adjacent ranges
    exclude_ranges.sort()
    merged = []
    for start, end in exclude_ranges:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Build output excluding these ranges
    output = []
    exclude_idx = 0
    i = parent_start
    while i <= parent_end:
        if exclude_idx < len(merged) and merged[exclude_idx][0] <= i <= merged[exclude_idx][1]:
            i = merged[exclude_idx][1] + 1
            exclude_idx += 1
        else:
            output.append(lines[i])
            i += 1

    return output


def extract_parent_blocks_excluding_nested_sets(filepath, patterns):
    with open(filepath, encoding="utf-8-sig") as f:
        lines = f.read().replace('\r\n', '\n').split('\n')

    blocks = build_block_index(lines)
    output = []

    for pattern in patterns:
        parent_tag = pattern["tag"]
        include = pattern.get("include", None)
        exclude = pattern.get("exclude", None)

        # Enforce that only one of include or exclude is present
        if include is not None and exclude is not None:
            raise ValueError(f"Pattern for tag '{parent_tag}' cannot have both 'include' and 'exclude'")
        if include is None and exclude is None:
            # No filtering, blacklist empty
            blacklist = set()
        else:
            parent_blocks = [b for b in blocks if b["tag"] == parent_tag]

            for parent in parent_blocks:
                # Find all nested tags inside parent block
                nested_tags = {b["tag"] for b in blocks if parent["start"] < b["start"] and b["end"] < parent["end"]}

                if include is not None:
                    # Exclude all nested tags NOT in include list
                    blacklist_tags = nested_tags - set(include)
                else:
                    # exclude is present
                    blacklist_tags = set(exclude)

                # Call exclude_nested_blocks with computed blacklist
                cleaned_lines = exclude_nested_blocks(
                    lines,
                    parent["start"],
                    parent["end"],
                    blocks,
                    blacklist_tags,
                    preserve_starts=pattern.get("preserve_starts", [])
                )
                output.append((parent_tag, "\n".join(cleaned_lines)))

    return output

def trim_all_endtags_from_output_blocks(output_blocks):
    trimmed_blocks = []
    for name, block_text in output_blocks:
        lines = block_text.splitlines()
        lines = [line for line in lines if not line.lstrip().startswith("</")]
        trimmed_block_text = "\n".join(lines)
        trimmed_blocks.append((name, trimmed_block_text))
    return trimmed_blocks


# === MAIN ===
if __name__ == "__main__":
    output_blocks = []

    if ISOLATE_LINES:
        matches = isolate_lines_with_following(INPUT_FILE, ISOLATE_TAG, ISOLATE_FOLLOWING)
        for m in matches:
            print("----- MATCH -----")
            print(m)

    if RUN_BLOCK_PARSER:
        blocks = extract_all_blocks(INPUT_FILE)
        output_blocks.extend(blocks)

    if RUN_PARENT_EXCLUDE_NESTED:
        parent_blocks = extract_parent_blocks_excluding_nested_sets(input_path, PARENT_BLOCK_PATTERNS)
        output_blocks.extend(parent_blocks)

    if output_blocks:
        if ENABLE_TRIM_ENDTAGS:
            output_blocks = trim_all_endtags_from_output_blocks(output_blocks)


        output_text = ""
        for name, block in output_blocks:
            output_text += f"<!-- {name} -->\n"
            output_text += block + "\n\n"

        if output_path:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(output_text)
        else:
            print(output_text)

        if output_path:
            print(f"Extracted {len(output_blocks)} blocks to '{output_path}'")
        else:
            print(f"Extracted {len(output_blocks)} blocks to stdout")
