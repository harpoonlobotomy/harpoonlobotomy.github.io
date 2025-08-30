## Supports adding materials to multiple selected objects at once. Observes 'Enabled' flag for parameter updates. Also updates UV Map indexes per material.

# Written for Blender 4.3
# - harpoonlobotomy

import bpy
import sqlite3
import re
import os
import sys
from pathlib import Path
from bpy.props import StringProperty, BoolProperty
from bpy.types import Panel
import importlib.util
import argparse
from datetime import datetime
from collections import defaultdict


# === CONFIG ===
SQLITE_PATH = r"F:\BG3 Extract PAKs\Asset Management Core\Master_Asset_Database.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG_GROUPS = {
    "image_textures": False,
    "scalar_params": False,
    "VTs": False,
    "general_setup": True,
    "rgb_params": False
}


# === PROPERTY GROUP ===
class BG3_MaterialBuilderProps(bpy.types.PropertyGroup):
    visualbank_name: StringProperty(
        name="VisualBank Name",
        default="DEC_GEN_StuffedHead_Wolf_Rich_A",
        description="VisualBank name for GR2 import"
    )
    object_id_override: StringProperty(name="ObjectID Override", default="")
    material_name_override: StringProperty(name="Mat.Name Override", default="")
    force_new_template_file: BoolProperty(name="Force Template File Creation", default=False)
    force_new_template: BoolProperty(name="Force Template Regeneration", default=False)
    disable_patterns: BoolProperty(name="Disable Patterns", default=False)
    new_nodegroups: BoolProperty(name="Recreate Nodegroups", default=False)
    reuse_existing: BoolProperty(name="Reuse Existing Material", default=True)
    force_add_all: BoolProperty(name="Force Add All Parameters", default=False)
    create_missing_nodes: BoolProperty(name="Create Missing Nodes", default=False)
    dry_run: BoolProperty(name="Dry Run (Debug Only)", default=False)

#--- Debug prints
def debug_print(groups, *args, **kwargs): #             ---------- debug_print("nodegroup_creation", "Setting up node:")
    if isinstance(groups, str):
        groups = [groups]
    if any(DEBUG_GROUPS.get(g, False) for g in groups):
        print(*args, **kwargs)

# === VISUALBANK FUNCTIONS ===
def get_visualbank_data(visualbank_name):
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT UUID, LocalPath FROM VisualBanks WHERE Name = ?
    """, (visualbank_name,))
    result = cursor.fetchone()
    conn.close()
    return {'UUID': result[0], 'LocalPath': result[1]} if result else None

def import_gr2(gr2_path):
    gr2_folder = str(Path(gr2_path).parent)
    gr2_filename = Path(gr2_path).name
    bpy.ops.import_scene.dos2de_collada('EXEC_DEFAULT', directory=gr2_folder, files=[{"name": gr2_filename}])

# === MAIN EXECUTION FUNCTION ===
def create_objects_queue(context):

    selected_objects = set(bpy.context.selected_objects)

    objects_queue = []
    if len(selected_objects) > 1:
        print(f"{len(selected_objects)} selected: can only do one at a time currently.")
    obj_count = len(selected_objects)
    print("obj_count:", obj_count)
    print("---------------Objects in queue: ----------------")
    for object in enumerate(selected_objects):
        objects_queue.append(object)
        print(object)

    #deselect all objects here and test again.
    if bpy.context.selected_objects:
        for obj in bpy.context.selected_objects:
            obj.select_set(False) #---------- it does deselect, but that doesn't fix it...
            print(f"Deselected {obj}")

    return objects_queue, obj_count

def run_material_application(context, objects_queue, index):

    errors = []

    def get_object_for_material_application(context, objects_queue, index):

        print(index)
        for i, object in objects_queue:
            print("---------------Objects in queue: ----------------")
            print(f"i, object:")
            print(i, object)
            print("index:")
            print(index)

            if i == index:
                obj = object
                bpy.context.view_layer.objects.active = obj
                return obj
            else:
                print("failed because i != index")

    obj = get_object_for_material_application(context, objects_queue, index)

    props = context.scene.bg3_matbuilder_props

    if not obj:
        print("[ERROR] No object selected.")
        return None, None
    if obj.type != 'MESH':
        err = "Object {obj.name} is not mesh type."
        print(err)
        errors.append(err)
        return obj.name, errors

    debug_print("general_setup", f"\n" * 5)
    debug_print("general_setup", f"\n" + "="*40)
    print("=== Material generation started at", datetime.now(), "===")
    debug_print("general_setup", f"="*40 + "\n")
    print("\n" * 1)

    # === Derive base name ===
    override_name = props.object_id_override.strip()
    mesh_name = re.sub(r"\.\d{3}$", "", override_name if override_name else obj.name)
    material_name = props.material_name_override.strip()


    if material_name:
        print(f"Starting search for material name: {material_name}")
        ## i have to get this to a comparable state:
        object_id = "//" + material_name
        print(object_id)

        apply_material_from_db(
            obj, ## is fine
            object_id, ## can get this from selected I guess? Feels like a waste. Would rather just add a placeholder and avoid needing it.
            force_new_template=props.force_new_template,
            force_new_template_file=props.force_new_template_file,
            disable_patterns=props.disable_patterns,
            new_nodegroups=props.new_nodegroups,
            reuse_existing=props.reuse_existing,
            force_add_all=props.force_add_all,
            create_missing_nodes=props.create_missing_nodes,
            dry_run=props.dry_run
        )

    elif mesh_name:
        print(f"Starting search for {mesh_name}...")

        # === Search for full ObjectID ===
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ObjectID FROM VisualBank_Objects")
        candidates = cursor.fetchall()
        conn.close()

        found_id = None
        for (candidate,) in candidates:
            parts = candidate.split(".")
            if len(parts) >= 3 and parts[1] == mesh_name:
                found_id = candidate
                break

        if found_id:
            object_id = found_id
            debug_print("general_setup", f"[INFO] Found ObjectID: {object_id}")
        else:
            debug_print("general_setup", f"[ERROR] No matching ObjectID found for name '{mesh_name}'")
            err = "[ERROR] No matching ObjectID found"
            errors.append(err)

            return obj.name, errors

        apply_material_from_db(
            obj,
            object_id,
            force_new_template=props.force_new_template,
            force_new_template_file=props.force_new_template_file,
            disable_patterns=props.disable_patterns,
            new_nodegroups=props.new_nodegroups,
            reuse_existing=props.reuse_existing,
            force_add_all=props.force_add_all,
            create_missing_nodes=props.create_missing_nodes,
            dry_run=props.dry_run
        )
    return object_id, errors

def template_generator(template_data):

    def is_console_visible():
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        return hwnd != 0 and ctypes.windll.user32.IsWindowVisible(hwnd)

    script_path = r"F:\Python_Scripts\Template_Generator\CURRENT\BLENDER_Temp_Gen_01.py"

    spec = importlib.util.spec_from_file_location("template_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not is_console_visible():
        bpy.ops.wm.console_toggle()

    template_mat = module.run(template_data)
    return template_mat

# === MATERIAL APPLICATION LOGIC ===
def apply_material_from_db(obj, object_id, force_new_template=False, force_new_template_file=False, disable_patterns=False, new_nodegroups=False, reuse_existing=True, force_add_all=False, create_missing_nodes=False, dry_run=False):

    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()


    if "//" in object_id:
        name = object_id.split("//")[1]
        print(object_id)
        print("becomes:")
        print(name)
        object_id = "None"

    def get_material_starting_data(conn, cursor, obj, object_id):
        debug_print("general_setup", f"[INFO] Selected object: {obj.name}")
        debug_print("general_setup", f"[INFO] Using ObjectID: {object_id}")

        cursor.execute("""
            SELECT UUID, Name FROM Materials
            WHERE UUID IN (
                SELECT Material_UUID
                FROM VisualBank_Objects
                WHERE ObjectID = ?
            )
        """, (object_id,))
        materials = cursor.fetchall()

        if not materials:
            print(f"[ERROR] No materials found for ObjectID '{object_id}'")
            conn.close()
            return

        # Filter out VFX_ if multiple found
        material_uuid, name = materials[0]
        if len(materials) > 1:
            non_vfx = [m for m in materials if not m[1].startswith("VFX_")]
            if non_vfx:
                material_uuid, name = non_vfx[0]
                debug_print("general_setup", f"[INFO] More than one material found. Using: {name} [{material_uuid}]")
            else:
                debug_print("general_setup", f"[INFO] All materials are VFX. Using: {name} [{material_uuid}]")

        cursor.execute("SELECT SourceFile FROM Materials WHERE UUID = ?", (material_uuid,))
        mat_result = cursor.fetchone()
        if not mat_result:
            debug_print("general_setup", f"[ERROR] No material entry for UUID '{material_uuid}'")
            conn.close()
            mat_result = None
            return mat_result, None

        else:
            debug_print("general_setup", f"Mat result: {mat_result}")
                ## swapping to give it the full localpath instead of just the name.
        template_name = os.path.splitext(os.path.basename(mat_result[0]))[0]
        debug_print("general_setup", f"[INFO] Template Material Name: {template_name}")

        print("This is mat result::")
        print(mat_result) ## mat_result == just sourcefile
        conn.close()
        return mat_result, template_name, name, material_uuid


    if object_id != "None":
        print(f"Object ID exists. It is: {object_id}")
        sourcefile, template_name, name, material_uuid = get_material_starting_data(conn, cursor, obj, object_id)

    else:
        print(f"Searching database for materials of the name `{name}`...")
        # === Search for Material name ===
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT UUID, SourceFile FROM Materials WHERE Name = ?", (name,))
        candidates = cursor.fetchall()
        #print(candidates)
        conn.close()
        material_uuid, sourcefile = candidates[0]
        print(f"Material UUID: {material_uuid} // Sourcefile: {sourcefile}")
        template_name = os.path.splitext(os.path.basename(sourcefile[0]))[0]
        print("")
        print(f"Template name: template_name")

    template_data = {
        "template_path": str(sourcefile),
        "template_name": template_name,
        "force_new_template": force_new_template,
        "force_new_template_file": force_new_template_file,
        "disable_patterns": disable_patterns,
        "recreate_nodegroups": new_nodegroups
    }

    if force_new_template or force_new_template_file or new_nodegroups:
        template_mat = template_generator(template_data)
    else:
        template_mat = bpy.data.materials.get(template_name)

    if not template_mat:
        print(f"[WARN] Template material '{template_name}' could not be found locally. Attempting to generate...")
        template_mat = template_generator(template_data)  ## changed from just the name to the full filepath.

    if not template_mat:
        print(f"[WARN] Template material '{template_name}' could not be found anywhere.")
        if not force_add_all:
            print("[FALLBACK] Enabling Force Add All mode.")
            force_add_all = True

    if reuse_existing:
        existing = bpy.data.materials.get(f"{template_name}_Instance") if template_mat else None
        if existing:
            print(f"[INFO] Reusing existing material instance '{existing.name}'")
            new_mat = existing
        else:
            new_mat = template_mat.copy() if template_mat else bpy.data.materials.new(name="FallbackMaterial")
            new_mat.name = name
    else:
        new_mat = template_mat.copy() if template_mat else bpy.data.materials.new(name="FallbackMaterial")
        new_mat.name = name

    if dry_run:
        print("[DRY RUN] Would assign material and apply parameters")
        print(f"[DRY RUN] Material: {new_mat.name}")
        cursor.execute("SELECT ParameterName, Value FROM Material_ScalarParameters WHERE Material_UUID = ?", (material_uuid,))
        for param, value in cursor.fetchall():
            print(f"[DRY RUN] Scalar: {param} = {value}")
        cursor.execute("SELECT ParameterName, Texture_UUID FROM Material_Texture2DParameters WHERE Material_UUID = ?", (material_uuid,))
        for param, tex_uuid in cursor.fetchall():
            cursor.execute("SELECT LocalPath FROM Textures WHERE UUID = ?", (tex_uuid,))
            tex_result = cursor.fetchone()
            path = tex_result[0] if tex_result else "<missing>"
            print(f"[DRY RUN] Texture: {param} = {path}")
        print("\n[DRY RUN] === Checking Virtual Textures ===")
        cursor.execute("""
            SELECT VirtualTexture_UUID
            FROM Material_VirtualTextureParameters
            WHERE Material_UUID = ?
        """, (material_uuid,))
        vt_results = cursor.fetchall()
        if vt_results:
            for (vt_uuid,) in vt_results:
                print(f"  [DRY RUN] Virtual Texture UUID: {vt_uuid}")
        else:
            print("  [DRY RUN] No virtual texture associated with this material.")
        conn.close()
        return

    if not obj.material_slots:
        obj.data.materials.append(new_mat)
        #print("!---------------- obj.data.materials.append(new_mat)")
    else:
        i = obj.active_material_index
        obj.material_slots[i if 0 <= i < len(obj.material_slots) else 0].material = new_mat
        #print("This else has triggered.")
        #print(obj.material_slots[i if 0 <= i < len(obj.material_slots) else 0].material)

    print(f"[INFO] Assigned new material '{new_mat.name}' to object '{obj.name}'")


    new_mat.use_nodes = True
    nodes = new_mat.node_tree.nodes

    # === Node stacking positions ===
    scalar_y = 0
    tex_y = 0
    scalar_x = -600
    tex_x = -300


    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    # === SCALAR PARAMS ===
    print("\n[INFO] === Applying Scalar Parameters ===")
    cursor.execute("""
        SELECT ParameterName, Value, Enabled
        FROM Material_ScalarParameters
        WHERE Material_UUID = ?
    """, (material_uuid,))

    for param, value_raw, enabled in cursor.fetchall():
        try:
            value = float(value_raw)
        except:
            debug_print("scalar_params", f"  [FAIL] Scalar '{param}' not float: {value_raw}")
            continue
        if enabled == "True":
            node = next((n for n in nodes if n.label == param), None)
            if not node and (force_add_all or create_missing_nodes):
                node = nodes.new(type='ShaderNodeValue')
                node.label = node.name = param
                node.location = (scalar_x, scalar_y)
                scalar_y -= 200
                debug_print("scalar_params", f"  [INFO] Created missing VALUE node for '{param}'")
            if node:
                if node.type == 'VALUE':
                    node.outputs[0].default_value = value
                    debug_print("scalar_params", f"  [OK] Set Value '{param}' = {value}")
                elif node.type == 'RGB':
                    node.outputs[0].default_value = (value, value, value, 1)
                    debug_print("scalar_params", f"  [OK] Set RGB '{param}' = ({value}, {value}, {value})")
                else:
                    debug_print("scalar_params", f"  [WARN] Node '{param}' is type '{node.type}'")
            else:
                debug_print("scalar_params", f"  [MISS] Node '{param}' not found")
        else:
            pass
            #print(f"Scalar parameter `{param}` skipped, because it's marked Enabled: False in the database.")


    # === RGB PARAMS ===
    print("\n[INFO] === Applying RGB Parameters ===")
    cursor.execute("""
        SELECT ParameterName, Value, Enabled
        FROM Material_Vector3Parameters
        WHERE Material_UUID = ?
    """, (material_uuid,))

    for param, value_raw, enabled in cursor.fetchall():
        if enabled == "True":
            try:
                value = tuple(float(p) for p in value_raw.strip().split())
                debug_print("RGB_params", f"{value}; enabled? {enabled}")
                if len(value) != 3:
                    raise ValueError(f"Expected 3 components, got {len(value)} in {value_raw}")
            except:
                debug_print("RGB_params", f"  [FAIL] RGB '{param}' not vector: {value_raw}")
                continue
            node = next((n for n in nodes if n.label == param), None)
    #        tempnode = next((n for n in nodes if node.type == "RGB"), None)# if n.label == param), None)
            debug_print("RGB_params", f"Node found: {node}")
    #        if tempnode.label == param:
    #            node = tempnode
    #        print(f"Found node: {node.label} for {label}")

            if not node and (force_add_all or create_missing_nodes):
                node = nodes.new(type='ShaderNodeValue')
                node.label = node.name = param
                node.location = (scalar_x, scalar_y)
                scalar_y -= 200
                debug_print("RGB_params", f"  [INFO] Created missing VALUE node for '{param}'")
            if node:
                if node.type == 'RGB':
                    node.outputs[0].default_value = (*value, 1.0)  # RGBA

                    debug_print("RGB_params", f"  [OK] Set RGB '{param}' = ({value_raw})")
                else:
                    debug_print("RGB_params", f"  [WARN] Node '{param}' is type '{node.type}'")
            else:
                debug_print("RGB_params", f"  [MISS] Node '{param}' not found")
        else:
            pass
            #print(f"RGB `{param}` skipped, because it's marked Enabled: False in the database.")

    # === TEXTURE PARAMS ===
    print("\n[INFO] === Applying Texture Parameters ===")
    cursor.execute("""
        SELECT ParameterName, Texture_UUID, GroupName, Enabled
        FROM Material_Texture2DParameters
        WHERE Material_UUID = ?
    """, (material_uuid,))

    print(f" -----------  Material UUID: {material_uuid}  --------")
    all_tex_results = set()
    unnamed_tex_results = set()
    used_tex_nodes = set()
    used_tex_nodegroups = set()
    disabled_uuids = set()
    #--- adding section here to pre-get the parameters if I can, so that if there is only one unnamed parameter, it can default to an unused texture ng.

    rows = cursor.fetchall()

    #print(list(node.label)

    for param, tex_uuid, groupname, enabled in rows:
        if enabled == "True":
            cursor.execute("SELECT LocalPath, SRGB FROM Textures WHERE UUID = ?", (tex_uuid,))
            tex_result = cursor.fetchone()
            if tex_result:
                all_tex_results.add(tex_result)
                if not param:
                    unnamed_tex_results.add(tex_result)
                    continue
            if not tex_result:
                #print(f"  [MISS] Texture UUID '{tex_uuid}' not found")
                continue
    debug_print("image_textures", f"All texture results: {len(all_tex_results)}")
    debug_print("image_textures", f"Texture results without parameters: {len(unnamed_tex_results)}")
    tex_result = None
    all_tex_uuids = set()
    enabled_params = set()
    param_to_uuid = {}
    nodegroup_to_uuid = {}
    used_uuids = set()
    index = 0
    ### actual part starts here, don't break this bit.

## -----------------------NEED TO IMPLEMENT THE ENABLED FLAG HERE. NOT ALL PARAMS SHOULD BE UPDATED. ---------## !! ::


    for param, tex_uuid, groupname, enabled in rows:
        #print("Not adding any materials in matgen temporarily. Remove this later.")
        #continue
        all_tex_uuids.add(tex_uuid)
        if enabled == "True":
            enabled_params.add(tex_uuid)
            print(f"This is a texture that is enabled: {param}, {groupname}")
            cursor.execute("SELECT LocalPath, SRGB FROM Textures WHERE UUID = ?", (tex_uuid,))
            tex_result = cursor.fetchone()
            if not tex_result:
                debug_print("image_textures", f"  [MISS] Texture UUID '{tex_uuid}' not found")
                continue

            debug_print("image_textures", f"Starting search for {param} in image texture nodegroups.")
            local_path, srgb_raw = tex_result
            srgb_flag = str(srgb_raw).strip().lower() == "true"
            color_space = "sRGB" if srgb_flag else "Non-Color"
            label = param if param else "<unnamed>"
            groupname = groupname
    #        print(f"Param: {param}, UUID: {tex_uuid}, GroupName: {groupname}")

            if param == "":
                base = os.path.basename(local_path).lower()
                param = base

            if param:

                debug_print("image_textures", f"{groupname} says it's param. Param is `{param}`. ")
                if ".dds" in param:
                    param, _ = param.split(".")
                    debug_print("image_textures", f"[DDS FILE].dds filename parameter - setting split param name: {param}.")
                param_to_uuid[tex_uuid] = param
                tex_nodegroup = next((n for n in nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name.split(" - ")[0].lower() == param.lower()), None)

                if tex_nodegroup:
                    param_to_uuid[tex_uuid] = tex_nodegroup.node_tree.name.lower()
                    debug_print("image_textures", f"   Nodegroup found: {(tex_nodegroup.node_tree.name.lower())}")
                    nodegroup_to_uuid[tex_nodegroup.node_tree.name.lower()] = tex_uuid
                    #used_tex_nodes.add(tex_nodegroup)
                else:
                    debug_print("image_textures", "Could not find tex nodegroup.")
                    if len(all_tex_results) - len(used_tex_nodes) < 2:
                        debug_print("image_textures", "Only one unused image texture remaining.")
                        tex_nodegroup = next((n for n in nodes if n.type == 'GROUP' and "Texture2DNode" in n.name and n.node_tree and n not in used_tex_nodes), None)
                        if tex_nodegroup:
                            debug_print("image_textures", "Tex nodegroup found by using the only one left.")

                if tex_nodegroup and tex_nodegroup.type == 'GROUP':
                    #for n intex_nodegroup.node_tree.nodes:
                    debug_print("image_textures", f"{param} found an image texture nodegroup; looking for the image texture node inside: {tex_nodegroup}")
                    node = next((n for n in tex_nodegroup.node_tree.nodes if n.type == "TEX_IMAGE"), None)
                    debug_print("image_textures", f"{(node)}")

## should this be one tab further to the left????
                    if not tex_nodegroup and (force_add_all or create_missing_nodes):
                        node = nodes.new(type='ShaderNodeTexImage')
                        node.label = node.name = label
                        node.location = (tex_x, tex_y)
                        tex_y -= 300
                        debug_print("image_textures", f"  [INFO] Created missing TEX_IMAGE node for '{label}'")
##-----------

                    if node and node.type == 'TEX_IMAGE':
                        try:
                            old_tex_nodegroup = tex_nodegroup
                            new_tree = tex_nodegroup.node_tree.copy()   # duplicate datablock
                            tex_nodegroup.node_tree = new_tree          # reassign this node to point at the copy

                            #print(f"New nodegroup: {tex_nodegroup}")
                            node = next((n for n in tex_nodegroup.node_tree.nodes if n.type == "TEX_IMAGE"), None)
                            if node.image:
                                #if node.image.path == local_path, do not make new. ::todo
                                node.image = node.image.copy()
                            img = bpy.data.images.load(local_path, check_existing=True)
                            node.image = img
                            img = bpy.data.images.load(local_path, check_existing=True)
                            node.image = img
                            node.image.colorspace_settings.name = color_space
                            debug_print("image_textures", f"  [OK] Set Image '{label}' = {os.path.basename(local_path)} ({color_space})")
                            used_tex_nodes.add(node)
                            used_tex_nodegroups.add(old_tex_nodegroup)
                            used_uuids.add(tex_uuid)

                            #print(f"Added image to nodegroup {old_tex_nodegroup}, param: {param}")
                        except Exception as e:
                            debug_print("image_textures", f"  [FAIL] Failed to load image for '{label}': {e}")
                    elif node:
                        debug_print("image_textures", f"  [WARN] Node '{label}' is type '{node.type}', not TEX_IMAGE")
                    else:
                        debug_print("image_textures", f"  [MISS] Node '{label}' not found")
        else:
            disabled_uuids.add(tex_uuid)
            if not param:
                param = index
                index += 1
            #param_to_uuid[tex_uuid] = param
            #print(f"Texture `{param}` skipped, because it's marked Enabled: False in the database.")

    all_texture_nodes_set = set()
    all_texture_nodegroups_set = set()

    for nodegroup in nodes:
        if nodegroup.type == 'GROUP' and "Texture2DNode" in nodegroup.name and nodegroup.node_tree:
            node = next((n for n in nodegroup.node_tree.nodes if n.type == "TEX_IMAGE"), None)
            if node:
                all_texture_nodes_set.add(node) ## is objects, not instances (I think)
                all_texture_nodegroups_set.add(nodegroup)

    debug_print("image_textures", f"Are there are more texture nodes present than are used? : {len(all_texture_nodegroups_set)} > {len(used_tex_nodes)}")


    #used_tex_nodegroups
    #all_tex_results = set()
    #unnamed_tex_results = set()
    #used_tex_nodes = set()
    #used_tex_nodegroups = set()
    #disabled_uuids = set()
    #all_tex_uuids = set()
    #enabled_params = set()
    #print(f" length of all_texture_nodegroups_set: {len(all_texture_nodegroups_set)}")
    #print(f"length of all tex uuids: {len(all_tex_uuids)}")
    #print(f"length of all enabled_params: {len(enabled_params)}")
    #print(f" length of unnamed tex results: {len(unnamed_tex_results)}")
    #print(f" length of disabled_uuids: {len(disabled_uuids)}")

    enabled_uuids = all_tex_uuids - disabled_uuids
    #print(f"enabled uuids:: {enabled_uuids}")
    unused_uuids = enabled_uuids - used_uuids
    #print(f"Unused uuids: {unused_uuids}")

    unused_texture_nodegroups = set()

    unused_texture_nodegroups = all_texture_nodes_set - used_tex_nodes ## is actually nodes, but called 'nodegroups' to save me having to change variable names in testing.
    unused_texture_nodegroups2 = all_texture_nodegroups_set - used_tex_nodegroups # -- actually nodegroups
    debug_print("image_textures", "Used tex nodes:")

    debug_print("image_textures", used_tex_nodes)
    debug_print("image_textures", "")
    unused_texnodes_names = set()

    debug_print("image_textures", "unused tex nodes:")
    debug_print("image_textures", unused_texture_nodegroups)
    debug_print("image_textures", "")
    #print(nodegroup_to_uuid)
    if unused_uuids:
        #print("Not adding any materials in matgen temporarily. Remove this later.")
        #continue
        for nodegroup in unused_texture_nodegroups2:
            node = nodegroup.node_tree
            label = node.name
            label_parts = label.split(" - ")

            if label_parts[0] == "Texture2D":
                label = label_parts[1]
            else:
                label = label_parts[0]

            print(f"node name as label: {label}")

            if node in used_tex_nodes:
                print(f"Node {node} in used_tex_nodes")
                continue


            else:

                cursor.execute("SELECT UUID, LocalPath, SRGB FROM Textures WHERE Template = ?", (label,))
                debug_print(f"image_textures", f"Node label searched for by label: {label}")
                found_texture = cursor.fetchone()
                if found_texture:
                    print(f"found texture by label: {label}")
                    #continue
                    uuid, local_path, srgb_raw = found_texture

                elif unused_uuids:
                    print("Nothing found by the label.")
                    print(label)
    #    param_to_uuid[tex_uuid] = tex_nodegroup.node_tree.name.lower()
    #    debug_print("image_textures", f"   Nodegroup found: {(tex_nodegroup.node_tree.name.lower())}")
    #    nodegroup_to_uuid[tex_nodegroup.node_tree.name.lower()] = tex_uuid
                    for uuid in unused_uuids:
                        uuid_test = uuid
                    #nodegroup_to_uuid[tex_nodegroup.node_tree.name.lower()] = tex_uuid
                    #param_to_uuid[uuid] = param
                    #for uuid in
                    cursor.execute("SELECT LocalPath, SRGB, Template FROM Textures WHERE UUID = ?", (uuid_test,))
                    debug_print(f"image_textures", f"Node label searched for by UUID: {uuid_test}")
                    found_texture = cursor.fetchone()
                    if found_texture:
                        print(f"found texture by uuid: {uuid_test}")
                        #continue
                        local_path, srgb_raw, label = found_texture
                        uuid = uuid_test

            if uuid:
                if uuid in disabled_uuids:
                    print(f"UUID {uuid}/ is disabled. Not continuing.")
                    continue
                srgb_flag = str(srgb_raw).strip().lower() == "true"
                color_space = "sRGB" if srgb_flag else "Non-Color"

                debug_print("image_textures", f"Found texture == `{found_texture}`")
                try:
                    print(f"Found a texture, apparently. Node: {node}. Label: {label} ")

                    img = bpy.data.images.load(local_path, check_existing=True)
                    node.image = img
                    node.image.colorspace_settings.name = color_space
                    debug_print("image_textures", f"  [OK] Set Image '{label}' = {os.path.basename(local_path)} ({color_space})")
                    used_tex_nodes.add(node)
                except Exception as e:
                    debug_print("image_textures", f"  [FAIL] Failed to load image for '{label}': {e}")

            else:
                debug_print("image_textures", f"  [MISS] Texture label '{label}' not found in database.")
                unused_texnodes_names.add(node.name)
                continue

    # === UPDATE UV MAP SELECTION === #
    print("\n[INFO] === Updating UV Map Selection. ===")
    uvmap_nodes = set()
    uvmap_frames = {}
    uv_index_pairs = {}
    delete_uv_frames = True
    #nodes = new_mat.node_tree.nodes
    for node in nodes:
        if node.type == "UVMAP":
            uvmap_nodes.add(node)
        if node.type == "FRAME" and "Index" in node.label:
            frame_loc_full = node.location
            uvmap_frames[node] = node.location

    from mathutils import Vector
    for uvmap in uvmap_nodes:
        location = uvmap.location
        offset = Vector((25.0, +40.0))
        likely_frame_location = location + offset
        for entry in uvmap_frames:
            frame_location = uvmap_frames[entry]
            if frame_location == likely_frame_location:
                uv_index_pairs[uvmap] = entry
                index_label = entry.label.split("_")[1]
                idx = int(index_label)
                uv_map_names = [uv.name for uv in obj.data.uv_layers]
                if uv_map_names:
                    uvmap.uv_map = uv_map_names[idx] ## set it to the UV index given in the file
                    #print(f"Set UV map to {uv_map_names[idx]}")
    if delete_uv_frames:
        for node in uvmap_frames:
            nodes.remove(node)

    # === VIRTUAL TEXTURE PARAMS  ===
    print("\n[INFO] === Applying Virtual Texture Parameters ===")
    cursor.execute("""
        SELECT VirtualTexture_UUID
        FROM Material_VirtualTextureParameters
        WHERE Material_UUID = ?
    """, (material_uuid,))
    vt_results = cursor.fetchall()


    if not vt_results:
        debug_print("VTs", "  [INFO] No virtual textures found.")
    else:
        for (vt_uuid,) in vt_results:

            debug_print("VTs", f"  [INFO] VT UUID: {vt_uuid}")

            # Step 1: Find GTexFileName
            cursor.execute("""
                SELECT GTexFileName
                FROM VirtualTextureBanks
                WHERE VirtualTexture_ID = ?
            """, (vt_uuid,))
            bank_result = cursor.fetchone()
            if not bank_result:
                debug_print("VTs", f"  [MISS] No VirtualTextureBank entry for UUID {vt_uuid}")
                continue

            gtex_filename = bank_result[0]

            # Step 2: Fetch all matching VT_Files
            cursor.execute("""
                SELECT TypeName, LocalPath
                FROM VirtualTexture_Files
                WHERE GTexFileName = ?
            """, (gtex_filename,))
            vt_files = cursor.fetchall()

            if not vt_files:
                debug_print("VTs", f"  [MISS] No VT_Files found for GTexFileName {gtex_filename}")
                continue

            nodegroup = next((n for n in nodes if "VirtualTextureNode" in n.name), None)
            debug_print("VTs", f"Found VirtualTextureNode nodegroup for {vt_uuid}")
            if nodegroup:
                nodegroups = list((n for n in nodes if "VirtualTextureNode" in n.name))
                if len(nodegroups) > 1:
                    debug_print("VTs", "More than one VT nodegroup found in this material. Not implemented yet...") #, will assign randomly...??")

                else:
                    debug_print("VTs", "Only one nodegroup - continuing.")

            if nodegroup and nodegroup.type == 'GROUP':
                vt_data = {}
                vt_nodes = set()

                for typename, local_path in vt_files:
                    label = typename
                    color_space = "sRGB" if typename.lower() == "albedo" else "Non-Color"
                    if not label:
                        debug_print("VTs", f"  [MISS] Node '{label}' not found")

                    node = next((n for n in nodegroup.node_tree.nodes if n.label == label), None)
                    vt_nodes.add(node)
                    vt_data[node] = label, local_path, color_space

                    if not node and (force_add_all or create_missing_nodes):
                        node = nodes.new(type='ShaderNodeTexImage')
                        node.label = node.name = label
                        node.location = (tex_x, tex_y)
                        tex_y -= 300
                        debug_print("VTs", f"  [INFO] Created missing TEX_IMAGE node for '{label}'")

                    elif node:
                        debug_print("VTs", f"  [WARN] Node '{label}' is type '{node.type}', not TEX_IMAGE")


                    if len(vt_nodes) == 3:
                        new_tree = nodegroup.node_tree.copy()   # duplicate datablock
                        nodegroup.node_tree = new_tree          # reassign this node to point at the copy

                        for imagenode in vt_nodes:
                            try:
                                #print("cancelling VTs temporarily.")
                                #continue
                                label, local_path, color_space = vt_data[imagenode]
                                print(label, local_path)
                                node = next((n for n in nodegroup.node_tree.nodes if n.label == label), None)
                                if node.image:
                                    node.image = node.image.copy()
                                img = bpy.data.images.load(local_path, check_existing=True)
                                node.image = img

                                img = bpy.data.images.load(local_path, check_existing=True)
                                node.image = img
                                node.image.colorspace_settings.name = color_space
                                debug_print("VTs", f"  [OK] Set VT Image '{label}' = {os.path.basename(local_path)} ({color_space})")

                            except Exception as e:
                                debug_print("VTs", f"  [FAIL] Failed to load VT image for '{label}': {e}")


    print("Finished all VTs.")
    #print(f"# ------------- MATERIAL APPLICATION FOR {object_id} COMPLETE --------------------#")

# === PANELS ===
class BG3_PT_MaterialBuilderShaderPanel(Panel):
    bl_label = "BG3 Material Builder"
    bl_idname = "BG3_PT_material_builder_shader"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Mat_Builder'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bg3_matbuilder_props

        # === NEW: Import UI ===
        layout.prop(props, "visualbank_name")
        layout.operator("bg3.import_visualbank", text="Import VisualBank GR2")
        layout.separator()

        # === Existing: Material Builder UI ===
        layout.label(text="Apply BG3 Material")
        layout.prop(props, "object_id_override")
        layout.prop(props, "material_name_override")
        layout.separator()
        layout.prop(props, "force_new_template_file")
        layout.prop(props, "force_new_template")
        layout.prop(props, "disable_patterns")
        layout.prop(props, "new_nodegroups")
        layout.prop(props, "reuse_existing")
        layout.prop(props, "force_add_all")
        layout.prop(props, "create_missing_nodes")
        layout.prop(props, "dry_run")
        layout.operator("bg3.run_material_logic", text="Create Material")

class BG3_PT_MaterialBuilder3DViewPanel(Panel):
    bl_label = "BG3 Material Builder"
    bl_idname = "BG3_PT_material_builder_3dview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mat_Builder'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bg3_matbuilder_props

        # === NEW: Import UI ===
        layout.prop(props, "visualbank_name")
        layout.operator("bg3.import_visualbank", text="Import VisualBank GR2")
        layout.separator()

        # === Existing: Material Builder UI ===
        layout.label(text="Apply BG3 Material")
        layout.prop(props, "object_id_override")
        layout.prop(props, "material_name_override")
        layout.prop(props, "force_new_template_file")
        layout.prop(props, "force_new_template")
        layout.prop(props, "disable_patterns")
        layout.prop(props, "new_nodegroups")
        layout.prop(props, "reuse_existing")
        layout.prop(props, "force_add_all")
        layout.prop(props, "create_missing_nodes")
        layout.prop(props, "dry_run")
        layout.operator("bg3.run_material_logic", text="Create Material")

# === BUTTON HANDLERS ===
class BG3_OT_ImportVisualBank(bpy.types.Operator):
    bl_idname = "bg3.import_visualbank"
    bl_label = "Import VisualBank GR2"

    def execute(self, context):
        props = context.scene.bg3_matbuilder_props
        vb_name = props.visualbank_name.strip()
        if not vb_name:
            self.report({'ERROR'}, "VisualBank name is empty")
            return {'CANCELLED'}

        vb_data = get_visualbank_data(vb_name)
        if not vb_data:
            self.report({'ERROR'}, f"VisualBank '{vb_name}' not found in DB")
            return {'CANCELLED'}
    ####### :: add a thing here to give a list of potential matches to pick from to try again. ##############

        existing_objects = set(bpy.context.scene.objects)
        import_gr2(vb_data['LocalPath'])
        new_objects = [obj for obj in bpy.context.scene.objects if obj not in existing_objects and obj.type == 'MESH']

        # Delete LOD objects ending with _LOD\d+
        lod_pattern = re.compile(r'.*_LOD\d+$')
        lod_objects = [obj for obj in new_objects if lod_pattern.match(obj.name)]

        for obj in lod_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

        self.report({'INFO'}, f"Deleted {len(lod_objects)} LOD mesh{'es' if len(lod_objects) != 1 else ''}")

        if not new_objects or all(obj in lod_objects for obj in new_objects):
            self.report({'WARNING'}, "No non-LOD mesh objects remain after deletion")

        return {'FINISHED'}

class BG3_OT_RunMaterialLogic(bpy.types.Operator):
    bl_idname = "bg3.run_material_logic"
    bl_label = "Run Material Logic"

    def execute(self, context):
        index = 0
        objects_queue, obj_count = create_objects_queue(context)

        objects_materialed = []
        error_compilation = []

        while index < obj_count:
            obj_name, errors = run_material_application(context, objects_queue, index)
            objects_materialed.append(obj_name)
            index += 1
            print("")
            print(f"Material application complete for {obj_name}.")
            for err in errors:
                err = obj_name + ": " + err
                error_compilation.append(err)

        if len(objects_materialed) > 1:
            print(f"These objects were processed: {objects_materialed}.")
        if error_compilation:
            print("The following errors occurred:")
            print(error_compilation)
        else:
            print("There were no major errors.")
        print()

        return {'FINISHED'}

# === REGISTRATION ===
classes = (
    BG3_MaterialBuilderProps,
    BG3_OT_ImportVisualBank,
    BG3_OT_RunMaterialLogic,
    BG3_PT_MaterialBuilderShaderPanel,
    BG3_PT_MaterialBuilder3DViewPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bg3_matbuilder_props = bpy.props.PointerProperty(type=BG3_MaterialBuilderProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.bg3_matbuilder_props

if __name__ == "__main__":
    register()
