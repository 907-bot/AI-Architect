"""
backend/unreal/ue5_setup.py
=============================
AI Architect → Unreal Engine 5 Automation Script
Run this INSIDE Unreal Engine's Python console or via:
  Edit → Execute Python Script → select this file

Requirements:
  - UE5.3 or later
  - Plugins enabled: Python Editor Script Plugin, Interchange Framework,
    GLTFExporter, Nanite Meshes, Lumen
  - Copy your exported .glb file next to this script OR update GLB_PATH below

Usage:
  1. Open Unreal Engine 5
  2. Enable: Edit → Plugins → Python Editor Script Plugin ✓
  3. Enable: Edit → Plugins → Interchange Framework ✓
  4. Edit → Execute Python Script → select this file
     OR paste into: Tools → Python Script → Run
"""

import unreal
import os
import json
import math

# ─── CONFIG — edit these ──────────────────────────────────────────────────────
GLB_PATH          = os.path.join(os.path.dirname(__file__), "building.glb")
META_PATH         = GLB_PATH.replace(".glb", "_meta.json")
UE_DESTINATION    = "/Game/AIArchitect/Buildings/Current/"
UE_MATERIALS_PATH = "/Game/AIArchitect/Materials/"
UE_LEVEL_PATH     = "/Game/AIArchitect/Maps/ArchitectScene"
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str):
    unreal.log(f"[AI Architect] {msg}")

def load_meta() -> dict:
    if os.path.exists(META_PATH):
        with open(META_PATH) as f:
            return json.load(f)
    return {}

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORT GLB VIA INTERCHANGE
# ══════════════════════════════════════════════════════════════════════════════
def import_glb(glb_path: str, destination: str) -> list:
    """Import GLB using UE5 Interchange plugin. Returns list of imported assets."""
    log(f"Importing GLB: {glb_path}")

    if not os.path.exists(glb_path):
        unreal.log_error(f"[AI Architect] GLB not found: {glb_path}")
        return []

    # Ensure destination content directory exists
    unreal.EditorAssetLibrary.make_directory(destination)

    # Build Interchange import task
    import_task = unreal.AssetImportTask()
    import_task.filename         = glb_path
    import_task.destination_path = destination
    import_task.replace_existing = True
    import_task.automated        = True
    import_task.save             = True

    # Use GLTF/GLB specific options if available
    try:
        gltf_options = unreal.GLTFImportOptions()
        gltf_options.import_meshes    = True
        gltf_options.import_materials = True
        gltf_options.import_textures  = True
        gltf_options.import_lights    = False   # We create our own lights
        gltf_options.import_cameras   = False   # We create our own camera
        import_task.options = gltf_options
    except AttributeError:
        pass   # Older UE version — use defaults

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([import_task])

    # Collect imported assets
    imported = []
    for asset_path in unreal.EditorAssetLibrary.list_assets(destination, recursive=True):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset:
            imported.append(asset)

    log(f"Imported {len(imported)} assets")
    return imported

# ══════════════════════════════════════════════════════════════════════════════
# 2. ENABLE NANITE ON ALL STATIC MESHES
# ══════════════════════════════════════════════════════════════════════════════
def enable_nanite(assets: list) -> int:
    """Enable Nanite on every StaticMesh in the asset list."""
    count = 0
    for asset in assets:
        if not isinstance(asset, unreal.StaticMesh):
            continue
        try:
            nanite_settings = asset.get_editor_property("nanite_settings")
            nanite_settings.set_editor_property("enabled", True)
            asset.set_editor_property("nanite_settings", nanite_settings)
            unreal.EditorAssetLibrary.save_asset(asset.get_path_name())
            count += 1
        except Exception as e:
            unreal.log_warning(f"[AI Architect] Nanite skip {asset.get_name()}: {e}")
    log(f"Nanite enabled on {count} meshes")
    return count

# ══════════════════════════════════════════════════════════════════════════════
# 3. PBR MATERIAL LIBRARY — Blender name → UE5 material instance
# ══════════════════════════════════════════════════════════════════════════════

# Map our Blender material names to UE5 parameter sets
MATERIAL_PARAMS = {
    "concrete":    {"BaseColor":(0.62,0.60,0.58,1), "Roughness":0.90, "Metallic":0.0},
    "facade":      {"BaseColor":(0.82,0.80,0.78,1), "Roughness":0.85, "Metallic":0.0},
    "slab":        {"BaseColor":(0.72,0.70,0.68,1), "Roughness":0.92, "Metallic":0.0},
    "glass":       {"BaseColor":(0.72,0.88,0.98,1), "Roughness":0.02, "Metallic":0.0,
                    "Opacity":0.12, "Refraction":1.45},
    "glass_panel": {"BaseColor":(0.72,0.88,0.98,1), "Roughness":0.04, "Metallic":0.0,
                    "Opacity":0.18, "Refraction":1.45},
    "frame":       {"BaseColor":(0.08,0.08,0.09,1), "Roughness":0.25, "Metallic":0.85},
    "steel":       {"BaseColor":(0.65,0.65,0.67,1), "Roughness":0.12, "Metallic":1.0},
    "railing":     {"BaseColor":(0.12,0.12,0.14,1), "Roughness":0.20, "Metallic":0.90},
    "roof":        {"BaseColor":(0.15,0.15,0.17,1), "Roughness":0.75, "Metallic":0.0},
    "roof_tile":   {"BaseColor":(0.58,0.28,0.18,1), "Roughness":0.65, "Metallic":0.0},
    "wood_dark":   {"BaseColor":(0.28,0.18,0.08,1), "Roughness":0.80, "Metallic":0.0},
    "wood_light":  {"BaseColor":(0.62,0.45,0.28,1), "Roughness":0.75, "Metallic":0.0},
    "grass":       {"BaseColor":(0.18,0.48,0.15,1), "Roughness":1.00, "Metallic":0.0},
    "ground":      {"BaseColor":(0.22,0.18,0.14,1), "Roughness":1.00, "Metallic":0.0},
    "asphalt":     {"BaseColor":(0.12,0.12,0.13,1), "Roughness":0.95, "Metallic":0.0},
    "pool_water":  {"BaseColor":(0.04,0.52,0.78,1), "Roughness":0.00, "Metallic":0.0,
                    "Opacity":0.65, "Refraction":1.33},
    "pool_tile":   {"BaseColor":(0.78,0.90,0.95,1), "Roughness":0.15, "Metallic":0.0},
    "accent":      {"BaseColor":(0.55,0.08,0.05,1), "Roughness":0.60, "Metallic":0.1},
    "marble":      {"BaseColor":(0.92,0.90,0.88,1), "Roughness":0.08, "Metallic":0.0},
    "bark":        {"BaseColor":(0.30,0.20,0.12,1), "Roughness":0.90, "Metallic":0.0},
    "foliage_a":   {"BaseColor":(0.18,0.48,0.15,1), "Roughness":1.00, "Metallic":0.0,
                    "SubsurfaceColor":(0.08,0.25,0.06,1), "SubsurfaceAmount":0.15},
    "white_paint": {"BaseColor":(0.95,0.93,0.90,1), "Roughness":0.78, "Metallic":0.0},
    "terracotta":  {"BaseColor":(0.70,0.38,0.22,1), "Roughness":0.82, "Metallic":0.0},
    "corrugated":  {"BaseColor":(0.48,0.48,0.50,1), "Roughness":0.35, "Metallic":0.70},
    "bamboo":      {"BaseColor":(0.72,0.78,0.38,1), "Roughness":0.60, "Metallic":0.0},
}

def create_master_material(mat_path: str, is_translucent=False, has_subsurface=False):
    """Create a master M_Arch material in UE5 content browser."""
    try:
        mat_factory = unreal.MaterialFactoryNew()
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat_name    = "M_Arch_Translucent" if is_translucent else (
                      "M_Arch_Subsurface"  if has_subsurface  else "M_Arch_Base")
        mat = asset_tools.create_asset(mat_name, mat_path, unreal.Material, mat_factory)

        # Set blend mode
        if is_translucent:
            mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        if has_subsurface:
            mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)

        # Add parameter nodes (BaseColor, Roughness, Metallic, Opacity)
        params = {
            "BaseColor": (unreal.MaterialExpressionVectorParameter, (-400, 0)),
            "Roughness":  (unreal.MaterialExpressionScalarParameter, (-400,-200)),
            "Metallic":   (unreal.MaterialExpressionScalarParameter, (-400,-350)),
        }
        if is_translucent:
            params["Opacity"] = (unreal.MaterialExpressionScalarParameter, (-400,-500))

        nodes = {}
        for param_name, (node_type, pos) in params.items():
            node = unreal.MaterialEditingLibrary.create_material_expression(
                mat, node_type, pos[0], pos[1])
            node.set_editor_property("parameter_name", param_name)
            if param_name == "BaseColor":
                node.set_editor_property("default_value", unreal.LinearColor(0.8,0.8,0.8,1.0))
            else:
                node.set_editor_property("default_value", 0.5)
            nodes[param_name] = node

        # Wire to material output
        ml = unreal.MaterialEditingLibrary
        ml.connect_material_property(nodes["BaseColor"],  "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        ml.connect_material_property(nodes["Roughness"],  "",    unreal.MaterialProperty.MP_ROUGHNESS)
        ml.connect_material_property(nodes["Metallic"],   "",    unreal.MaterialProperty.MP_METALLIC)
        if is_translucent and "Opacity" in nodes:
            ml.connect_material_property(nodes["Opacity"], "", unreal.MaterialProperty.MP_OPACITY)

        unreal.MaterialEditingLibrary.recompile_material(mat)
        unreal.EditorAssetLibrary.save_asset(mat.get_path_name())
        log(f"Created master material: {mat_name}")
        return mat
    except Exception as e:
        unreal.log_warning(f"[AI Architect] Material creation skipped: {e}")
        return None

def apply_material_to_mesh(mesh: unreal.StaticMesh, mat_name_hint: str,
                           mat_path: str) -> bool:
    """Find best-matching material params and create a material instance."""
    # Find closest param set
    params = None
    for key in MATERIAL_PARAMS:
        if key in mat_name_hint.lower():
            params = MATERIAL_PARAMS[key]; break
    if not params:
        params = MATERIAL_PARAMS["facade"]

    is_glass = "Opacity" in params and params.get("Opacity", 1.0) < 0.5
    master_name = "M_Arch_Translucent" if is_glass else "M_Arch_Base"
    master_full = f"{mat_path}{master_name}"

    if not unreal.EditorAssetLibrary.does_asset_exist(master_full):
        return False

    master = unreal.EditorAssetLibrary.load_asset(master_full)
    if not master:
        return False

    # Create instance
    inst_name = f"MI_{mat_name_hint[:30]}"
    inst_path = f"{mat_path}Instances/{inst_name}"

    try:
        inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            inst_name, f"{mat_path}Instances/",
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(inst, master)

        c = params.get("BaseColor", (0.8,0.8,0.8,1))
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
            inst, "BaseColor", unreal.LinearColor(*c))
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            inst, "Roughness", params.get("Roughness", 0.7))
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            inst, "Metallic",  params.get("Metallic",  0.0))
        if is_glass:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                inst, "Opacity", params.get("Opacity", 0.15))

        unreal.EditorAssetLibrary.save_asset(inst.get_path_name())

        # Assign to mesh slot 0 (or all slots)
        for i in range(mesh.get_num_sections(0)):
            mesh.set_material(i, inst)
        unreal.EditorAssetLibrary.save_asset(mesh.get_path_name())
        return True
    except Exception as e:
        unreal.log_warning(f"[AI Architect] MI create fail {inst_name}: {e}")
        return False

# ══════════════════════════════════════════════════════════════════════════════
# 4. LEVEL SETUP — Sky, Lumen, Sun, Camera
# ══════════════════════════════════════════════════════════════════════════════
def setup_level(meta: dict):
    """Set up lighting, sky atmosphere, Lumen GI and camera in current level."""
    log("Setting up level lighting and atmosphere...")
    editor_world = unreal.EditorLevelLibrary.get_editor_world()

    # ── Sky Atmosphere ────────────────────────────────────────────────────────
    existing_sky = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.SkyAtmosphere)
    if not existing_sky:
        sky_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SkyAtmosphere,
            unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        sky_actor.set_actor_label("SkyAtmosphere")

    # ── Volumetric Clouds ─────────────────────────────────────────────────────
    try:
        existing_clouds = unreal.GameplayStatics.get_all_actors_of_class(
            editor_world, unreal.VolumetricCloud)
        if not existing_clouds:
            cloud = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.VolumetricCloud,
                unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
            cloud.set_actor_label("VolumetricClouds")
    except AttributeError:
        pass   # VolumetricCloud not available in this UE version

    # ── Sky Light ─────────────────────────────────────────────────────────────
    existing_sl = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.SkyLight)
    sl_actor = existing_sl[0] if existing_sl else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
    sl_comp = sl_actor.get_component_by_class(unreal.SkyLightComponent)
    if sl_comp:
        sl_comp.set_editor_property("real_time_capture", True)
        sl_comp.set_editor_property("intensity", 1.5)
        sl_comp.set_editor_property("cast_shadows", True)

    # ── Directional Light (Sun) ───────────────────────────────────────────────
    existing_dl = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.DirectionalLight)
    dl_actor = existing_dl[0] if existing_dl else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0,0,5000), unreal.Rotator(-45, 215, 0))
    dl_actor.set_actor_rotation(unreal.Rotator(-48, 215, 0), False)
    dl_comp = dl_actor.get_component_by_class(unreal.DirectionalLightComponent)
    if dl_comp:
        dl_comp.set_editor_property("intensity",            10.0)
        dl_comp.set_editor_property("light_color",          unreal.LinearColor(1.0, 0.97, 0.88, 1.0))
        dl_comp.set_editor_property("cast_shadows",         True)
        dl_comp.set_editor_property("dynamic_shadow_distance_movable_light", 50000.0)
        dl_comp.set_editor_property("shadow_amount",        0.85)
        dl_comp.set_editor_property("atmosphere_sun_light", True)
        dl_comp.set_editor_property("cast_ray_tracing_shadows", True)
    dl_actor.set_actor_label("SunLight")

    # ── Post Process Volume (Lumen + Exposure + Color Grade) ──────────────────
    existing_pp = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.PostProcessVolume)
    pp_actor = existing_pp[0] if existing_pp else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PostProcessVolume, unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
    pp_comp = pp_actor.get_component_by_class(unreal.PostProcessComponent)
    pp_actor.set_actor_label("PostProcessVolume_Arch")

    try:
        pp_actor.set_editor_property("unbound", True)
        settings = pp_actor.settings

        # Lumen Global Illumination
        settings.set_editor_property("lumen_gi_enabled",                   True)
        settings.set_editor_property("lumen_reflection_enabled",            True)
        settings.set_editor_property("lumen_scene_lighting_quality",        1.0)
        settings.set_editor_property("lumen_scene_detail",                  1.0)
        settings.set_editor_property("lumen_final_gather_quality",          1.0)
        settings.set_editor_property("lumen_max_trace_distance",            20000.0)
        settings.set_editor_property("lumen_ray_lighting_mode",
            unreal.LumenRayLightingModeOverride.LUMEN_RAY_LIGHTING_MODE_SURFACE_CACHE)

        # ACES Filmic Tone Mapping
        settings.set_editor_property("auto_exposure_method",
            unreal.AutoExposureMethod.AEM_HISTOGRAM)
        settings.set_editor_property("auto_exposure_bias",                  1.0)
        settings.set_editor_property("auto_exposure_min_brightness",        0.5)
        settings.set_editor_property("auto_exposure_max_brightness",        2.0)

        # Color grading for architectural realism
        settings.set_editor_property("film_slope",                          0.88)
        settings.set_editor_property("film_toe",                            0.55)
        settings.set_editor_property("film_shoulder",                       0.26)
        settings.set_editor_property("film_black_clip",                     0.0)
        settings.set_editor_property("film_white_clip",                     0.04)

        # Ambient Occlusion
        settings.set_editor_property("ambient_occlusion_intensity",         0.6)
        settings.set_editor_property("ambient_occlusion_radius",            400.0)

        # Bloom (subtle)
        settings.set_editor_property("bloom_intensity",                     0.35)
        settings.set_editor_property("bloom_threshold",                     0.8)

        # Depth of Field (cinematic)
        settings.set_editor_property("depth_of_field_method",
            unreal.DepthOfFieldMethod.DOFM_CIRCLE_DOF)
        settings.set_editor_property("depth_of_field_fstop",               4.0)
        settings.set_editor_property("depth_of_field_focal_distance",       1800.0)

        pp_actor.set_editor_property("settings", settings)
    except Exception as e:
        unreal.log_warning(f"[AI Architect] PP settings partial: {e}")

    # ── Camera ────────────────────────────────────────────────────────────────
    bw = meta.get("width",  20.0)
    bd = meta.get("depth",  15.0)
    fh = meta.get("floors", 3) * 3.2
    dist = max(bw, bd) * 200   # UE units (1 cm = 1 UE unit, so 1 m = 100 uu)
    cam_loc = unreal.Vector(dist*0.85, -dist*1.05, fh*80)

    existing_cams = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.CameraActor)
    cam_actor = existing_cams[0] if existing_cams else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.CameraActor, cam_loc, unreal.Rotator(-25, 135, 0))
    cam_actor.set_actor_location(cam_loc, False, False)
    cam_actor.set_actor_rotation(unreal.Rotator(-25, 135, 0), False)
    cam_actor.set_actor_label("ArchCamera")
    cam_comp = cam_actor.get_component_by_class(unreal.CameraComponent)
    if cam_comp:
        cam_comp.set_editor_property("field_of_view", 55.0)

    # ── Exponential Height Fog ────────────────────────────────────────────────
    try:
        existing_fog = unreal.GameplayStatics.get_all_actors_of_class(
            editor_world, unreal.ExponentialHeightFog)
        fog = existing_fog[0] if existing_fog else unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.ExponentialHeightFog, unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
        fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        if fog_comp:
            fog_comp.set_editor_property("fog_density",              0.02)
            fog_comp.set_editor_property("fog_inscattering_color",
                unreal.LinearColor(0.55, 0.70, 0.90, 1.0))
            fog_comp.set_editor_property("volumetric_fog",           True)
            fog_comp.set_editor_property("volumetric_fog_scattering_distribution", 0.2)
    except Exception as e:
        unreal.log_warning(f"[AI Architect] Fog: {e}")

    log("Level lighting setup complete")

# ══════════════════════════════════════════════════════════════════════════════
# 5. PLACE BUILDING IN LEVEL
# ══════════════════════════════════════════════════════════════════════════════
def place_building_in_level(assets: list):
    """Spawn all static meshes from imported assets into the current level."""
    log("Placing building meshes in level...")
    spawned = 0
    editor_world = unreal.EditorLevelLibrary.get_editor_world()

    for asset in assets:
        if not isinstance(asset, unreal.StaticMesh):
            continue
        try:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
                asset,
                unreal.Vector(0, 0, 0),
                unreal.Rotator(0, 0, 0))
            if actor:
                actor.set_actor_label(f"Arch_{asset.get_name()}")
                actor.set_actor_scale3d(unreal.Vector(100, 100, 100))  # 1m = 100 UE units
                spawned += 1
        except Exception as e:
            unreal.log_warning(f"[AI Architect] Spawn fail {asset.get_name()}: {e}")

    log(f"Placed {spawned} mesh actors in level")

# ══════════════════════════════════════════════════════════════════════════════
# 6. ENABLE PATH TRACING (optional — for final renders)
# ══════════════════════════════════════════════════════════════════════════════
def enable_path_tracing():
    """Switch to Path Tracing renderer for ultra-photorealistic output."""
    try:
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(),
            "r.AntiAliasingMethod 4"         # TAA
        )
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(),
            "r.PathTracing 1"
        )
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(),
            "r.PathTracing.MaxBounces 16"
        )
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(),
            "r.PathTracing.SamplesPerPixel 2048"
        )
        log("Path Tracing enabled — 2048 SPP, 16 bounces")
    except Exception as e:
        unreal.log_warning(f"[AI Architect] Path tracing: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 7. SAVE LEVEL
# ══════════════════════════════════════════════════════════════════════════════
def save_level():
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("Level saved")

# ══════════════════════════════════════════════════════════════════════════════
# 8. FULL PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def run_full_pipeline():
    log("=" * 60)
    log("AI Architect → Unreal Engine 5 Import Pipeline")
    log("=" * 60)

    meta = load_meta()
    style = meta.get("style", "modern")
    log(f"Building: {meta.get('floors',3)}F {style} | {meta.get('width',20)}x{meta.get('depth',15)}m")

    # Step 1: Import GLB
    assets = import_glb(GLB_PATH, UE_DESTINATION)
    if not assets:
        unreal.log_error("[AI Architect] Import failed — check GLB_PATH")
        return

    # Step 2: Enable Nanite
    enable_nanite(assets)

    # Step 3: Create master materials + apply
    unreal.EditorAssetLibrary.make_directory(f"{UE_MATERIALS_PATH}Instances/")
    create_master_material(UE_MATERIALS_PATH, is_translucent=False)
    create_master_material(UE_MATERIALS_PATH, is_translucent=True)

    applied = 0
    for asset in assets:
        if isinstance(asset, unreal.StaticMesh):
            mat_hint = asset.get_name().lower()
            if apply_material_to_mesh(asset, mat_hint, UE_MATERIALS_PATH):
                applied += 1
    log(f"Applied materials to {applied} meshes")

    # Step 4: Place in level
    place_building_in_level(assets)

    # Step 5: Setup lighting, Lumen, sky
    setup_level(meta)

    # Step 6: Save
    save_level()

    log("=" * 60)
    log("DONE — Building is live in UE5 with Lumen GI + Nanite")
    log("Tip: Press F in viewport to focus on building")
    log("Tip: Run enable_path_tracing() for final photorealistic render")
    log("=" * 60)

# Run automatically when executed via Execute Python Script
if __name__ == "__main__":
    run_full_pipeline()
