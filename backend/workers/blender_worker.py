"""
backend/workers/blender_worker.py
Photorealistic Procedural Architecture — Multi-Style
Runs INSIDE Blender subprocess (bpy available here — never import in FastAPI)

Usage: blender --background --python backend/workers/blender_worker.py -- schema.json
"""
import bpy, sys, json, os, math, random
from mathutils import Vector

# ══════════════════════════════════════════════════════════════════════════════
# 1. ARG / SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
def get_schema():
    argv = sys.argv
    try:
        path = argv[argv.index("--") + 1]
    except (ValueError, IndexError):
        raise RuntimeError("Pass schema path after --")
    with open(path) as f:
        return json.load(f)

# ══════════════════════════════════════════════════════════════════════════════
# 2. STYLE CONFIGS
# ══════════════════════════════════════════════════════════════════════════════
STYLE_CONFIGS = {
    "modern": {
        "wall_color":    (0.82, 0.80, 0.78), "wall_rough": 0.85,
        "roof_color":    (0.15, 0.15, 0.17), "roof_type": "flat",
        "glass_tint":    (0.72, 0.88, 0.98), "glass_alpha": 0.12,
        "frame_color":   (0.08, 0.08, 0.09), "frame_metal": 0.9,
        "accent_color":  (0.25, 0.45, 0.65),
        "slab_offset":   0.15,               "overhang": 0.4,
        "window_ratio":  0.70,               "bay_width": 3.8,
        "ground_color":  (0.20, 0.18, 0.14), "grass_color": (0.18, 0.45, 0.15),
        "sky_turbidity": 2.5,
    },
    "japanese": {
        "wall_color":    (0.92, 0.88, 0.80), "wall_rough": 0.75,
        "roof_color":    (0.22, 0.22, 0.25), "roof_type": "pagoda",
        "glass_tint":    (0.90, 0.95, 0.88), "glass_alpha": 0.30,
        "frame_color":   (0.30, 0.18, 0.08), "frame_metal": 0.0,
        "accent_color":  (0.62, 0.12, 0.08),
        "slab_offset":   0.0,                "overhang": 1.2,
        "window_ratio":  0.55,               "bay_width": 3.2,
        "ground_color":  (0.22, 0.19, 0.14), "grass_color": (0.12, 0.38, 0.10),
        "sky_turbidity": 1.5,
    },
    "villa": {
        "wall_color":    (0.92, 0.87, 0.78), "wall_rough": 0.88,
        "roof_color":    (0.65, 0.30, 0.18), "roof_type": "hip",
        "glass_tint":    (0.78, 0.90, 0.72), "glass_alpha": 0.18,
        "frame_color":   (0.82, 0.78, 0.68), "frame_metal": 0.05,
        "accent_color":  (0.70, 0.45, 0.22),
        "slab_offset":   0.0,                "overhang": 0.8,
        "window_ratio":  0.50,               "bay_width": 3.5,
        "ground_color":  (0.28, 0.22, 0.15), "grass_color": (0.22, 0.52, 0.18),
        "sky_turbidity": 2.0,
    },
    "asian": {
        "wall_color":    (0.88, 0.82, 0.72), "wall_rough": 0.80,
        "roof_color":    (0.58, 0.12, 0.08), "roof_type": "curved",
        "glass_tint":    (0.72, 0.88, 0.80), "glass_alpha": 0.20,
        "frame_color":   (0.55, 0.08, 0.05), "frame_metal": 0.1,
        "accent_color":  (0.80, 0.62, 0.10),
        "slab_offset":   0.0,                "overhang": 1.0,
        "window_ratio":  0.45,               "bay_width": 3.0,
        "ground_color":  (0.22, 0.18, 0.12), "grass_color": (0.15, 0.40, 0.12),
        "sky_turbidity": 2.0,
    },
    "industrial": {
        "wall_color":    (0.52, 0.48, 0.44), "wall_rough": 0.95,
        "roof_color":    (0.28, 0.28, 0.30), "roof_type": "shed",
        "glass_tint":    (0.60, 0.72, 0.78), "glass_alpha": 0.08,
        "frame_color":   (0.18, 0.18, 0.20), "frame_metal": 0.95,
        "accent_color":  (0.72, 0.32, 0.08),
        "slab_offset":   0.0,                "overhang": 0.2,
        "window_ratio":  0.65,               "bay_width": 4.5,
        "ground_color":  (0.18, 0.16, 0.14), "grass_color": (0.14, 0.32, 0.10),
        "sky_turbidity": 4.0,
    },
    "scandinavian": {
        "wall_color":    (0.95, 0.93, 0.90), "wall_rough": 0.80,
        "roof_color":    (0.18, 0.18, 0.20), "roof_type": "steep_gable",
        "glass_tint":    (0.82, 0.90, 0.95), "glass_alpha": 0.10,
        "frame_color":   (0.88, 0.85, 0.80), "frame_metal": 0.05,
        "accent_color":  (0.62, 0.30, 0.15),
        "slab_offset":   0.0,                "overhang": 0.6,
        "window_ratio":  0.52,               "bay_width": 3.0,
        "ground_color":  (0.25, 0.22, 0.18), "grass_color": (0.16, 0.42, 0.14),
        "sky_turbidity": 1.8,
    },
    "colonial": {
        "wall_color":    (0.95, 0.93, 0.90), "wall_rough": 0.85,
        "roof_color":    (0.22, 0.20, 0.22), "roof_type": "gable",
        "glass_tint":    (0.80, 0.90, 0.82), "glass_alpha": 0.15,
        "frame_color":   (0.95, 0.93, 0.90), "frame_metal": 0.0,
        "accent_color":  (0.12, 0.18, 0.38),
        "slab_offset":   0.0,                "overhang": 0.5,
        "window_ratio":  0.42,               "bay_width": 3.2,
        "ground_color":  (0.25, 0.22, 0.16), "grass_color": (0.20, 0.50, 0.18),
        "sky_turbidity": 2.2,
    },
    "classical": {
        "wall_color":    (0.93, 0.90, 0.84), "wall_rough": 0.80,
        "roof_color":    (0.55, 0.35, 0.25), "roof_type": "pitched",
        "glass_tint":    (0.65, 0.80, 0.70), "glass_alpha": 0.20,
        "frame_color":   (0.85, 0.82, 0.75), "frame_metal": 0.0,
        "accent_color":  (0.65, 0.52, 0.30),
        "slab_offset":   0.0,                "overhang": 0.6,
        "window_ratio":  0.45,               "bay_width": 3.4,
        "ground_color":  (0.28, 0.24, 0.18), "grass_color": (0.22, 0.52, 0.18),
        "sky_turbidity": 2.0,
    },
}

def get_style(name):
    return STYLE_CONFIGS.get(name, STYLE_CONFIGS["modern"])

# ══════════════════════════════════════════════════════════════════════════════
# 3. SCENE UTILS
# ══════════════════════════════════════════════════════════════════════════════
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):  bpy.data.collections.remove(c)
    for m in list(bpy.data.meshes):       bpy.data.meshes.remove(m)

def add_box(name, loc, dims, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj

def add_cylinder(name, loc, r, h, mat=None, verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj

def add_cone(name, loc, r, h, verts=8, mat=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, depth=h, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj

def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# ══════════════════════════════════════════════════════════════════════════════
# 4. PHOTOREALISTIC MATERIAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
_mat_cache = {}

def mat(name, base, rough=0.5, metal=0.0, alpha=1.0, transmission=0.0,
        bump=0.0, noise_scale=60.0, wave=False, brick=False, emission=None):
    if name in _mat_cache:
        return _mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()

    out  = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    out.location  = (500,0); bsdf.location = (200,0)

    bsdf.inputs["Base Color"].default_value   = (*base[:3], 1.0)
    bsdf.inputs["Roughness"].default_value    = rough
    bsdf.inputs["Metallic"].default_value     = metal
    bsdf.inputs["Alpha"].default_value        = alpha
    for sp in ("Specular IOR Level","Specular"):
        if sp in bsdf.inputs:
            bsdf.inputs[sp].default_value = 0.5; break
    if transmission > 0:
        for tr in ("Transmission Weight","Transmission"):
            if tr in bsdf.inputs:
                bsdf.inputs[tr].default_value = transmission; break
        m.blend_method = "BLEND"
    if alpha < 1.0:
        m.blend_method = "BLEND"
    if emission:
        for em in ("Emission Color","Emission"):
            if em in bsdf.inputs:
                bsdf.inputs[em].default_value = (*emission[:3],1.0); break
        bsdf.inputs["Emission Strength"].default_value = 3.0

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-800,0)

    if brick:
        # Realistic brick texture
        brk = nt.nodes.new("ShaderNodeTexBrick")
        brk.location = (-400, 100)
        brk.inputs["Scale"].default_value      = 8.0
        brk.inputs["Mortar Size"].default_value = 0.04
        brk.inputs["Color1"].default_value = (*base[:3],1.0)
        brk.inputs["Color2"].default_value = (
            min(1,base[0]*0.8), min(1,base[1]*0.75), min(1,base[2]*0.7), 1.0)
        brk.inputs["Mortar"].default_value = (0.72,0.70,0.68,1.0)
        nt.links.new(coord.outputs["Generated"], brk.inputs["Vector"])
        nt.links.new(brk.outputs["Color"], bsdf.inputs["Base Color"])
        # Bump from brick
        bmp2 = nt.nodes.new("ShaderNodeBump")
        bmp2.location = (0,0)
        bmp2.inputs["Strength"].default_value = 0.5
        bmp2.inputs["Distance"].default_value = 0.003
        nt.links.new(brk.outputs["Fac"], bmp2.inputs["Height"])
        nt.links.new(bmp2.outputs["Normal"], bsdf.inputs["Normal"])
    elif wave:
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.location = (-400,100)
        wv.wave_type = "BANDS"
        wv.inputs["Scale"].default_value     = noise_scale
        wv.inputs["Distortion"].default_value = 2.0
        wv.inputs["Detail"].default_value    = 6.0
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.location = (-200, 100)
        cr.color_ramp.elements[0].color = (*[c*0.85 for c in base[:3]],1.0)
        cr.color_ramp.elements[1].color = (*[min(1,c*1.1) for c in base[:3]],1.0)
        nt.links.new(coord.outputs["Generated"], wv.inputs["Vector"])
        nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
        if bump > 0:
            bmp2 = nt.nodes.new("ShaderNodeBump")
            bmp2.inputs["Strength"].default_value = bump
            bmp2.inputs["Distance"].default_value = 0.002
            nt.links.new(wv.outputs["Fac"], bmp2.inputs["Height"])
            nt.links.new(bmp2.outputs["Normal"], bsdf.inputs["Normal"])
    elif bump > 0:
        ns = nt.nodes.new("ShaderNodeTexNoise")
        ns.location = (-400,100)
        ns.inputs["Scale"].default_value     = noise_scale
        ns.inputs["Detail"].default_value    = 12.0
        ns.inputs["Roughness"].default_value = 0.65
        ns.inputs["Distortion"].default_value = 0.3
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.location = (-200, 100)
        cr.color_ramp.elements[0].color = (*[c*0.88 for c in base[:3]],1.0)
        cr.color_ramp.elements[1].color = (*[min(1,c*1.08) for c in base[:3]],1.0)
        nt.links.new(coord.outputs["Generated"], ns.inputs["Vector"])
        nt.links.new(ns.outputs["Fac"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
        bmp2 = nt.nodes.new("ShaderNodeBump")
        bmp2.inputs["Strength"].default_value = bump
        bmp2.inputs["Distance"].default_value = 0.003
        nt.links.new(ns.outputs["Fac"], bmp2.inputs["Height"])
        nt.links.new(bmp2.outputs["Normal"], bsdf.inputs["Normal"])

    _mat_cache[name] = m
    return m

def build_material_set(sc):
    """Build the full material palette for a given style config."""
    _mat_cache.clear()
    wc = sc["wall_color"];    wr = sc["wall_rough"]
    rc = sc["roof_color"]
    gc = sc["glass_tint"];    ga = sc["glass_alpha"]
    fc = sc["frame_color"];   fm = sc["frame_metal"]
    ac = sc["accent_color"]
    gr = sc["ground_color"]
    gs = sc["grass_color"]

    return {
        # Structural
        "wall":        mat("wall",     wc, rough=wr,  bump=0.5, noise_scale=80),
        "wall_brick":  mat("wall_brk", wc, rough=0.9, brick=True),
        "wall_wood":   mat("wall_wd",  (0.48,0.32,0.18), rough=0.75, wave=True, noise_scale=20, bump=0.4),
        "slab":        mat("slab",     (0.72,0.70,0.68), rough=0.92, bump=0.3, noise_scale=60),
        "concrete":    mat("concrete", (0.62,0.60,0.58), rough=0.90, bump=0.5, noise_scale=70),
        "facade":      mat("facade",   wc,  rough=max(0.7,wr-0.05), bump=0.25, noise_scale=90),
        # Roof
        "roof":        mat("roof",     rc,  rough=0.70, bump=0.4, noise_scale=50),
        "roof_tile":   mat("roof_tile",rc,  rough=0.65, wave=True, noise_scale=12, bump=0.6),
        "roof_metal":  mat("roof_met", rc,  rough=0.25, metal=0.8, wave=True, noise_scale=30),
        # Glass & metal
        "glass":       mat("glass",    gc, rough=0.02, metal=0.0, alpha=ga, transmission=0.95),
        "glass_panel": mat("glass_p",  gc, rough=0.04, alpha=ga+0.06, transmission=0.90),
        "frame":       mat("frame",    fc, rough=0.2+fm*0.1, metal=fm),
        "steel":       mat("steel",    (0.65,0.65,0.67), rough=0.12, metal=0.95),
        "railing":     mat("rail",     fc, rough=0.2, metal=max(fm,0.7)),
        # Accent
        "accent":      mat("accent",   ac, rough=0.6, bump=0.2),
        "column":      mat("column",   wc, rough=0.75, bump=0.3),
        "wood_dark":   mat("wd_dark",  (0.28,0.18,0.08), rough=0.8, wave=True, noise_scale=15, bump=0.5),
        "wood_light":  mat("wd_light", (0.62,0.45,0.28), rough=0.75, wave=True, noise_scale=18, bump=0.4),
        # Ground
        "ground":      mat("ground",   gr, rough=1.0, bump=0.8, noise_scale=100),
        "grass":       mat("grass",    gs, rough=1.0, bump=0.6, noise_scale=80),
        "pavement":    mat("pave",     (0.60,0.58,0.55), rough=0.88, bump=0.3),
        "asphalt":     mat("asphalt",  (0.12,0.12,0.13), rough=0.95, bump=0.5),
        "gravel":      mat("gravel",   (0.48,0.46,0.42), rough=1.0, bump=0.7, noise_scale=40),
        "sand":        mat("sand",     (0.78,0.72,0.55), rough=1.0, bump=0.4, noise_scale=50),
        # Water & pool
        "pool_water":  mat("pw",       (0.04,0.52,0.78), rough=0.0, alpha=0.65, transmission=0.85),
        "pool_tile":   mat("ptile",    (0.78,0.90,0.95), rough=0.15, bump=0.1),
        # Nature
        "bark":        mat("bark",     (0.30,0.20,0.12), rough=0.9, bump=0.7, noise_scale=25),
        "foliage_a":   mat("fol_a",    gs, rough=1.0, bump=0.5),
        "foliage_b":   mat("fol_b",    (gs[0]*0.75, gs[1]*0.82, gs[2]*0.72), rough=1.0),
        "foliage_dark":mat("fol_dk",   (0.06,0.28,0.06), rough=1.0),
        # Japanese-specific
        "shoji":       mat("shoji",    (0.95,0.93,0.88), rough=0.9, alpha=0.7),
        "bamboo":      mat("bamboo",   (0.72,0.78,0.38), rough=0.6, wave=True, noise_scale=8, bump=0.3),
        "tatami":      mat("tatami",   (0.72,0.68,0.42), rough=0.85, wave=True, noise_scale=10),
        "stone_zen":   mat("stone_z",  (0.52,0.52,0.50), rough=0.92, bump=0.5),
        # Villa-specific
        "terracotta":  mat("terra",    (0.70,0.38,0.22), rough=0.82, bump=0.6, noise_scale=25),
        "plaster":     mat("plaster",  wc, rough=0.82, bump=0.45, noise_scale=55),
        "marble":      mat("marble",   (0.92,0.90,0.88), rough=0.08, bump=0.15, noise_scale=30),
        # Colonial / Classical
        "white_paint": mat("wht_pnt",  (0.95,0.93,0.90), rough=0.78, bump=0.2),
        "brick_red":   mat("brk_red",  (0.62,0.28,0.18), rough=0.9, brick=True),
        # Industrial
        "corten":      mat("corten",   (0.52,0.28,0.15), rough=0.85, bump=0.6),
        "corrugated":  mat("corrug",   (0.48,0.48,0.50), rough=0.35, metal=0.7, wave=True, noise_scale=25),
        "exposed_conc":mat("exp_conc", (0.55,0.53,0.52), rough=0.92, bump=0.6, noise_scale=65),
        # Misc
        "door":        mat("door",     fc, rough=0.4, metal=fm*0.5),
        "path":        mat("path",     (0.65,0.63,0.60), rough=0.9),
        "water":       mat("water",    (0.05,0.40,0.65), rough=0.0, alpha=0.55, transmission=0.88),
        "dark_metal":  mat("dk_met",   (0.10,0.10,0.12), rough=0.18, metal=0.92),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 5. RENDER SETUP
# ══════════════════════════════════════════════════════════════════════════════
def setup_render(samples=128):
    sc = bpy.context.scene
    sc.render.engine      = "CYCLES"
    sc.cycles.samples     = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoiser    = "OPENIMAGEDENOISE"
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080

def setup_lighting(bw, bd, total_h, sc_cfg, style_name):
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree; nt.nodes.clear()
    out  = nt.nodes.new("ShaderNodeOutputWorld")
    sky  = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type  = "HOSEK_WILKIE"
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation  = math.radians(215)
    sky.turbidity = sc_cfg.get("sky_turbidity", 2.5)
    bg   = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.3
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Generated"], sky.inputs["Vector"])
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # Key sun
    bpy.ops.object.light_add(type="SUN", location=(bw*2, -bd*2, total_h*3))
    sun = bpy.context.active_object
    sun.data.energy = 4.5 if style_name == "japanese" else 5.5
    sun.data.angle  = math.radians(0.53)
    sun.rotation_euler = (math.radians(48), 0, math.radians(215))

    # Soft fill
    bpy.ops.object.light_add(type="AREA", location=(-bw*2.5, bd*2.5, total_h*1.8))
    fill = bpy.context.active_object
    fill.data.energy = 250 if style_name == "industrial" else 320
    fill.data.size   = 28.0
    fill.rotation_euler = (math.radians(-38), 0, math.radians(-45))

    # Rim light (back)
    bpy.ops.object.light_add(type="AREA", location=(0, bd*3, total_h*2))
    rim = bpy.context.active_object
    rim.data.energy = 120
    rim.data.size   = 20.0
    rim.rotation_euler = (math.radians(60), 0, math.radians(0))

def setup_camera(bw, bd, total_h):
    dist = max(bw, bd) * 2.6
    loc  = (dist*0.85, -dist*1.05, total_h*0.82)
    bpy.ops.object.camera_add(location=loc)
    cam  = bpy.context.active_object
    cam.name = "ArchCam"
    bpy.context.scene.camera = cam
    dx = -loc[0]; dy = -loc[1]; dz = total_h*0.4-loc[2]
    cam.rotation_euler = (
        math.atan2(math.sqrt(dx**2+dy**2), -dz) - math.pi/2,
        0,
        math.atan2(dx, -dy))
    cam.data.lens   = 35
    cam.data.clip_end = 2000

# ══════════════════════════════════════════════════════════════════════════════
# 6. TERRAIN
# ══════════════════════════════════════════════════════════════════════════════
def generate_terrain(bw, bd, M, style_name):
    plot = max(bw, bd) + 55
    add_box("Ground",   (0,0,-0.3),      (plot,plot,0.6),        M["ground"])
    add_box("Grass",    (0,0,0.02),      (plot-2,plot-2,0.04),   M["grass"])
    pad_w, pad_d = bw+10, bd+10
    pave_mat = M["sand"] if style_name in ("villa","japanese") else M["pavement"]
    add_box("BasePad",  (0,0,0.06),      (pad_w,pad_d,0.12),     pave_mat)

    # Style-specific ground treatment
    if style_name == "japanese":
        # Gravel garden strips
        add_box("GravelN", (0,  pad_d/2+1.5, 0.08), (pad_w+3, 3.0, 0.08), M["gravel"])
        add_box("GravelS", (0, -pad_d/2-1.5, 0.08), (pad_w+3, 3.0, 0.08), M["gravel"])
    elif style_name == "villa":
        add_box("Courtyard", (0, bd/2+4, 0.08), (bw*0.5, 6, 0.08), M["sand"])

    # Perimeter paths
    pw = 1.8
    for name,loc,dims in [
        ("Path_N", (0,  pad_d/2+pw/2, 0.10), (pad_w+pw*2, pw, 0.06)),
        ("Path_S", (0, -pad_d/2-pw/2, 0.10), (pad_w+pw*2, pw, 0.06)),
        ("Path_E", ( pad_w/2+pw/2, 0, 0.10), (pw, pad_d, 0.06)),
        ("Path_W", (-pad_w/2-pw/2, 0, 0.10), (pw, pad_d, 0.06)),
    ]:
        add_box(name, loc, dims, M["path"])

# ══════════════════════════════════════════════════════════════════════════════
# 7. FOUNDATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_foundation(bw, bd, M, style_name):
    fh = 0.75 if style_name != "japanese" else 0.4
    add_box("Foundation", (0,0,fh/2), (bw,bd,fh), M["slab"])
    # Plinth band
    add_box("Plinth", (0,0,fh+0.05), (bw+0.3,bd+0.3,0.1), M["concrete"])
    if style_name in ("colonial","classical"):
        # Stone base course
        add_box("BaseCourse", (0,0,fh+0.12), (bw+0.15,bd+0.15,0.25), M["white_paint"])
    return fh

# ══════════════════════════════════════════════════════════════════════════════
# 8. FLOOR SLABS
# ══════════════════════════════════════════════════════════════════════════════
def generate_floors(bw, bd, num_floors, floor_h, base_z, M):
    t = 0.28
    for i in range(num_floors+1):
        z = base_z + i*floor_h
        add_box(f"Slab_{i}", (0,0,z+t/2), (bw,bd,t), M["slab"])
        if i < num_floors:
            add_box(f"SlabEdge_{i}", (0,0,z+t+0.02), (bw+0.15,bd+0.15,0.04), M["concrete"])

# ══════════════════════════════════════════════════════════════════════════════
# 9. STYLE-SPECIFIC WALLS + WINDOWS
# ══════════════════════════════════════════════════════════════════════════════
def generate_walls(bw, bd, num_floors, floor_h, base_z, M, sc_cfg, style_name):
    wt     = 0.28
    wr     = sc_cfg["window_ratio"]
    bay_w  = sc_cfg["bay_width"]
    win_h  = floor_h * 0.52
    sill   = floor_h * 0.18
    span_h = floor_h - win_h - sill

    for fi in range(num_floors):
        fz = base_z + fi*floor_h
        # Choose wall material per style
        if style_name == "industrial":
            wall_mat = M["brick_red"] if fi == 0 else M["exposed_conc"]
        elif style_name == "japanese":
            wall_mat = M["wall_wood"] if fi == 0 else M["wall"]
        elif style_name == "villa":
            wall_mat = M["plaster"]
        else:
            wall_mat = M["facade"]

        for side,cy,is_glazed in [
            ("N",  bd/2-wt/2,  True),
            ("S", -(bd/2-wt/2),True),
            ("E",  None,        False),
            ("W",  None,        False),
        ]:
            if side == "E":
                cx =  bw/2-wt/2
                _side_wall(f"Wall_E_{fi}", cx, 0, "X", bw, bd, fz, floor_h, wt, wall_mat, M, style_name, False)
            elif side == "W":
                cx = -bw/2+wt/2
                _side_wall(f"Wall_W_{fi}", cx, 0, "X", bw, bd, fz, floor_h, wt, wall_mat, M, style_name, True)
            else:
                _glazed_wall(f"Wall_{side}_{fi}", bw, cy, fz, floor_h, wt,
                             wr, bay_w, win_h, sill, span_h, M, sc_cfg, style_name, side=="S")

def _side_wall(name, cx, cy, axis, bw, bd, fz, floor_h, wt, wall_mat, M, style_name, is_left):
    if axis == "X":
        add_box(name, (cx, 0, fz+floor_h/2), (wt, bd, floor_h), wall_mat)
        # Narrow strip window
        sw = 1.0
        ox = cx + (wt*0.15 if cx > 0 else -wt*0.15)
        add_box(f"{name}_win", (ox, 0, fz+floor_h*0.5), (0.04, sw, floor_h*0.5), M["glass"])
        add_box(f"{name}_fr",  (ox, 0, fz+floor_h*0.5), (0.07, sw+0.1, floor_h*0.5+0.06), M["frame"])
        if style_name == "japanese" and is_left:
            # Shoji screen accent
            add_box(f"{name}_shoji", (cx-0.02, 0, fz+floor_h*0.5), (0.04, bd*0.5, floor_h*0.7), M["shoji"])

def _glazed_wall(prefix, bw, cy, fz, floor_h, wt, wr, bay_w, win_h, sill, span_h, M, sc_cfg, style_name, is_south):
    nbays = max(3, int(bw/bay_w))
    bw_actual = bw/nbays
    ww = bw_actual * wr
    col_w = (bw_actual - ww)/2
    sign = 1 if is_south else -1

    for wi in range(nbays):
        cx = -bw/2 + bw_actual*(wi+0.5)
        fm = M["frame"]

        # Columns
        for tag,xo in [("L",cx-ww/2-col_w/2),("R",cx+ww/2+col_w/2)]:
            add_box(f"{prefix}_col{tag}{wi}", (xo,cy,fz+floor_h/2), (col_w,wt,floor_h), M["facade"])

        # Sill
        add_box(f"{prefix}_sill{wi}", (cx,cy,fz+sill/2), (ww,wt,sill), M["facade"])
        # Spandrel
        z_sp = fz+sill+win_h+span_h/2
        add_box(f"{prefix}_span{wi}", (cx,cy,z_sp), (ww,wt,span_h), M["concrete"])

        # Glass
        gy = cy + sign*wt*0.06
        gz = fz+sill+win_h/2
        add_box(f"{prefix}_glass{wi}", (cx,gy,gz), (ww-0.04,0.04,win_h-0.04), M["glass"])

        # Frame
        for tag,z_off in [("T",gz+win_h/2-0.03),("B",gz-win_h/2+0.03)]:
            add_box(f"{prefix}_fh{tag}{wi}", (cx,gy,z_off), (ww,0.06,0.07), fm)
        for tag,xo in [("L",cx-ww/2+0.03),("R",cx+ww/2-0.03)]:
            add_box(f"{prefix}_fv{tag}{wi}", (xo,gy,gz), (0.07,0.06,win_h), fm)
        # Mullion
        add_box(f"{prefix}_mull{wi}", (cx,gy,gz), (0.05,0.04,win_h), fm)

        # Style-specific window treatments
        if style_name == "japanese":
            # Shoji sliding panel below window
            add_box(f"{prefix}_shoji{wi}", (cx,gy-0.01,gz-win_h/2-sill/2), (ww-0.1,0.04,sill-0.04), M["shoji"])
        elif style_name in ("villa","colonial","classical"):
            # Arched window head
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=ww/2-0.04,depth=0.04,
                location=(cx,gy,gz+win_h/2))
            arch = bpy.context.active_object
            arch.name = f"{prefix}_arch{wi}"
            arch.scale.z = 0.45
            bpy.ops.object.transform_apply(scale=True)
            assign(arch, M["glass"])
        elif style_name == "colonial":
            # Pediment above window
            add_box(f"{prefix}_ped{wi}", (cx,gy-0.01,gz+win_h/2+0.12), (ww+0.1,0.04,0.12), M["white_paint"])

# ══════════════════════════════════════════════════════════════════════════════
# 10. STYLE-SPECIFIC ROOFS
# ══════════════════════════════════════════════════════════════════════════════
def generate_roof(bw, bd, top_z, M, sc_cfg, style_name):
    rt  = sc_cfg.get("roof_type","flat")
    oh  = sc_cfg.get("overhang",0.4)
    t   = 0.35

    if rt == "flat" or style_name == "modern":
        _roof_flat(bw, bd, top_z, oh, t, M)
    elif rt == "pagoda" or style_name == "japanese":
        _roof_pagoda(bw, bd, top_z, oh, t, M)
    elif rt == "hip" or style_name == "villa":
        _roof_hip(bw, bd, top_z, oh, t, M)
    elif rt == "curved" or style_name == "asian":
        _roof_curved(bw, bd, top_z, oh, t, M)
    elif rt == "shed" or style_name == "industrial":
        _roof_shed(bw, bd, top_z, oh, t, M)
    elif rt in ("steep_gable","gable","pitched") or style_name in ("scandinavian","colonial","classical"):
        _roof_gable(bw, bd, top_z, oh, t, M, steep=(style_name=="scandinavian"))
    else:
        _roof_flat(bw, bd, top_z, oh, t, M)

def _roof_flat(bw, bd, top_z, oh, t, M):
    add_box("Roof_Slab", (0,0,top_z+t/2), (bw+oh*2,bd+oh*2,t), M["roof"])
    ph, pt = 1.0, 0.22
    for name,loc,dims in [
        ("Par_N",(0,  bd/2+oh,top_z+t+ph/2),(bw+oh*2,pt,ph)),
        ("Par_S",(0, -bd/2-oh,top_z+t+ph/2),(bw+oh*2,pt,ph)),
        ("Par_E",( bw/2+oh,0, top_z+t+ph/2),(pt,bd+oh*2+pt*2,ph)),
        ("Par_W",(-bw/2-oh,0, top_z+t+ph/2),(pt,bd+oh*2+pt*2,ph)),
    ]:
        add_box(name,loc,dims, M["facade"])
    # Cap
    cap = top_z+t+ph
    for name,loc,dims in [
        ("Cap_N",(0,  bd/2+oh,cap),(bw+oh*2+0.05,pt+0.06,0.04)),
        ("Cap_S",(0, -bd/2-oh,cap),(bw+oh*2+0.05,pt+0.06,0.04)),
        ("Cap_E",( bw/2+oh,0, cap),(pt+0.06,bd+oh*2+pt*2+0.05,0.04)),
        ("Cap_W",(-bw/2-oh,0, cap),(pt+0.06,bd+oh*2+pt*2+0.05,0.04)),
    ]:
        add_box(name,loc,dims, M["concrete"])

def _roof_pagoda(bw, bd, top_z, oh, t, M):
    """Japanese curved pagoda-style roof with upturned eaves."""
    oh2 = oh*2.5
    add_box("Roof_Base", (0,0,top_z+t/2), (bw+oh2*2,bd+oh2*2,t), M["roof_tile"])
    # Upturned corners (angled boxes at corners)
    cr = oh2*0.9; ct = 0.12
    for xi,yi,rx,ry in [(1,1,20,-20),(1,-1,20,20),(-1,1,-20,-20),(-1,-1,-20,20)]:
        bpy.ops.mesh.primitive_cube_add(size=1,
            location=(xi*(bw/2+oh2*0.6), yi*(bd/2+oh2*0.6), top_z+t+ct/2))
        c = bpy.context.active_object; c.name = f"Eave_{xi}_{yi}"
        c.scale = (cr*0.6, cr*0.6, ct)
        c.rotation_euler = (0,0,math.radians(ry))
        bpy.ops.object.transform_apply(scale=True)
        assign(c, M["roof_tile"])
    # Ridge
    add_box("Ridge_NS", (0,0,top_z+t*2.5), (bw*0.55,0.4,t*0.8), M["roof"])
    add_box("Ridge_knob", (0,0,top_z+t*3.2), (0.5,0.5,0.5), M["accent"])
    # Overhang fascia
    for name,loc,dims in [
        ("Fascia_N",(0, bd/2+oh2, top_z+t-0.06),(bw+oh2*2,0.12,0.12)),
        ("Fascia_S",(0,-bd/2-oh2, top_z+t-0.06),(bw+oh2*2,0.12,0.12)),
    ]:
        add_box(name,loc,dims, M["wood_dark"])

def _roof_hip(bw, bd, top_z, oh, t, M):
    """Mediterranean hip roof with terracotta tiles."""
    add_box("Roof_Base", (0,0,top_z+t/2), (bw+oh*2,bd+oh*2,t), M["roof"])
    rh = min(bw,bd)*0.26
    # Four hip faces as tapered boxes
    for name,loc,dims,rot in [
        ("Hip_N",(0, bd/2+oh/2, top_z+t+rh/2),(bw+oh*2, oh, rh),(math.radians(-30),0,0)),
        ("Hip_S",(0,-bd/2-oh/2, top_z+t+rh/2),(bw+oh*2, oh, rh),(math.radians(30), 0,0)),
        ("Hip_E",( bw/2+oh/2,0, top_z+t+rh/2),(oh, bd+oh*2, rh),(0,math.radians(30),0)),
        ("Hip_W",(-bw/2-oh/2,0, top_z+t+rh/2),(oh, bd+oh*2, rh),(0,math.radians(-30),0)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.active_object; obj.name = name
        obj.scale = dims; obj.rotation_euler = rot
        bpy.ops.object.transform_apply(scale=True)
        assign(obj, M["roof_tile"])
    add_box("Roof_Peak", (0,0,top_z+t+rh), (bw*0.3, bd*0.3, 0.2), M["terracotta"])
    # Guttering
    for name,loc,dims in [
        ("Gutter_N",(0, bd/2+oh+0.06, top_z+t-0.06),(bw+oh*2+0.12,0.12,0.12)),
        ("Gutter_S",(0,-bd/2-oh-0.06, top_z+t-0.06),(bw+oh*2+0.12,0.12,0.12)),
    ]:
        add_box(name,loc,dims, M["steel"])

def _roof_curved(bw, bd, top_z, oh, t, M):
    """Chinese/Asian curved upswept roof."""
    oh2 = oh*2
    add_box("Roof_Base", (0,0,top_z+t/2), (bw+oh2*2,bd+oh2*2,t), M["roof_tile"])
    rh = min(bw,bd)*0.30
    # Curved ridge via stacked boxes
    for i in range(6):
        pct = i/5.0
        w   = (bw+oh2*2)*(1-pct*0.6)
        tz  = top_z+t+rh*pct
        add_box(f"CurveRidge_{i}", (0,0,tz), (w,bd*0.2,t*0.5), M["roof"])
    # Corner finials
    for xi,yi in [(1,1),(1,-1),(-1,1),(-1,-1)]:
        add_box(f"Finial_{xi}_{yi}",
            (xi*(bw/2+oh2*0.8), yi*(bd/2+oh2*0.8), top_z+t+0.3),
            (0.35,0.35,0.6), M["accent"])
    add_box("Ridge_Spine",(0,0,top_z+t+rh*0.85),(bw*0.4,0.5,0.35), M["accent"])

def _roof_shed(bw, bd, top_z, oh, t, M):
    """Industrial mono-pitch shed roof."""
    rh = bw*0.12
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,top_z+t/2+rh/4))
    roof = bpy.context.active_object; roof.name = "Roof_Shed"
    roof.scale = (bw+oh*2, bd+oh*2, t+rh/2)
    roof.rotation_euler = (0, math.radians(6), 0)
    bpy.ops.object.transform_apply(scale=True)
    assign(roof, M["corrugated"])
    # Guttering
    add_box("Gutter_High", ( bw/2+oh*0.8, 0, top_z+t+rh/4), (0.15,bd+oh*2,0.15), M["steel"])
    add_box("Gutter_Low",  (-bw/2-oh*0.8, 0, top_z+t-rh/4), (0.15,bd+oh*2,0.15), M["steel"])
    # Skylights
    for i in range(3):
        sx = -bw/2 + bw*(i+0.5)/3
        add_box(f"Skylight_{i}",(sx,0,top_z+t+rh*0.5+0.1),(bw/5, bd*0.35, 0.1), M["glass"])

def _roof_gable(bw, bd, top_z, oh, t, M, steep=False):
    """Gable/pitched roof for colonial/scandinavian."""
    add_box("Roof_Base",(0,0,top_z+t/2),(bw+oh*2,bd+oh*2,t), M["roof"])
    rh = bw*0.32 if steep else bw*0.22
    # Two pitched faces
    for name,y,rot in [
        ("Pitch_L",0, math.radians(-40 if steep else -30)),
        ("Pitch_R",0, math.radians( 40 if steep else  30)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,top_z+t+rh/2))
        p = bpy.context.active_object; p.name = name
        p.scale = (bw/2+oh, bd+oh*2, t)
        p.rotation_euler = rot if isinstance(rot, tuple) else (0, rot, 0)
        bpy.ops.object.transform_apply(scale=True)
        assign(p, M["roof_tile"] if not steep else M["roof"])
    add_box("Ridge",(0,0,top_z+t+rh),(bw*0.04,bd+oh*2,0.12), M["concrete"])
    # Gable ends
    for name,cy in [("Gable_N", bd/2+oh),("Gable_S",-bd/2-oh)]:
        add_box(name,(0,cy,top_z+t+rh/2),(bw+oh*2,t,rh), M["facade"])
    # Dormers (scandinavian)
    if steep and bw > 12:
        for di,dx in enumerate([-bw/4, bw/4]):
            dw,dh = 2.2, 1.6
            add_box(f"Dormer_{di}",(dx,-(bd/2+oh*0.4),top_z+t+rh*0.55),(dw,0.8,dh), M["facade"])
            add_box(f"DormerWin_{di}",(dx,-bd/2-oh*0.4+0.42,top_z+t+rh*0.55),(dw-0.3,0.06,dh-0.3), M["glass"])

# ══════════════════════════════════════════════════════════════════════════════
# 11. STYLE-SPECIFIC COLUMNS / FEATURES
# ══════════════════════════════════════════════════════════════════════════════
def generate_style_features(bw, bd, base_z, num_floors, floor_h, M, style_name):
    total_h = base_z + num_floors*floor_h

    if style_name == "colonial":
        _colonial_columns(bw, bd, base_z, total_h, M)
    elif style_name == "classical":
        _classical_portico(bw, bd, base_z, total_h, M)
    elif style_name == "japanese":
        _japanese_elements(bw, bd, base_z, total_h, M)
    elif style_name == "asian":
        _asian_columns(bw, bd, base_z, total_h, M)
    elif style_name == "industrial":
        _industrial_elements(bw, bd, base_z, total_h, M)
    elif style_name == "villa":
        _villa_arches(bw, bd, base_z, total_h, M)

def _colonial_columns(bw, bd, base_z, total_h, M):
    n = max(4, int(bw/3.5))
    for i in range(n):
        cx = -bw/2+0.5 + (bw-1)/(n-1)*i if n>1 else 0
        add_cylinder(f"Col_{i}", (cx,-bd/2-0.05,base_z+total_h/2), 0.22, total_h, M["white_paint"], verts=16)
    # Pediment
    add_box("Pediment",(0,-bd/2-0.1,total_h+0.3),(bw+0.5,0.3,0.8), M["white_paint"])
    add_box("PedimentTop",(0,-bd/2-0.1,total_h+0.75),(bw*0.7,0.25,0.55), M["white_paint"])

def _classical_portico(bw, bd, base_z, total_h, M):
    n = 6
    for i in range(n):
        cx = -bw/3 + (bw*0.67)/(n-1)*i if n>1 else 0
        add_cylinder(f"ClassCol_{i}", (cx,-bd/2+0.1,base_z+total_h/2), 0.28, total_h, M["marble"], verts=20)
    # Entablature
    add_box("Entablature",(0,-bd/2+0.1,total_h+0.18),(bw*0.72,0.55,0.35), M["marble"])
    add_box("Frieze",     (0,-bd/2+0.08,total_h+0.48),(bw*0.72,0.48,0.22), M["white_paint"])

def _japanese_elements(bw, bd, base_z, total_h, M):
    # Heavy corner timber columns
    for xi,yi in [(1,1),(1,-1),(-1,1),(-1,-1)]:
        cx, cy = xi*(bw/2-0.35), yi*(bd/2-0.35)
        add_box(f"TimberCol_{xi}_{yi}", (cx,cy,base_z+total_h/2), (0.3,0.3,total_h), M["wood_dark"])
    # Horizontal beams
    add_box("BeamN", (0, bd/2-0.18, base_z+total_h*0.88), (bw,0.22,0.22), M["wood_dark"])
    add_box("BeamS", (0,-bd/2+0.18, base_z+total_h*0.88), (bw,0.22,0.22), M["wood_dark"])
    # Engawa (deck)
    deck_d = 1.4
    add_box("Engawa", (0,-bd/2-deck_d/2, base_z+0.38), (bw,deck_d,0.1), M["wood_light"])
    # Step stones
    for si in range(4):
        add_box(f"StepStone_{si}", (-bw/6+si*bw/9, -bd/2-deck_d-0.3, 0.04),
                (0.55,0.55,0.08), M["stone_zen"])
    # Bamboo fence
    for bi in range(int(bw/0.5)):
        bx = -bw/2 + bi*0.5
        add_cylinder(f"Bamboo_{bi}", (bx,-bd/2-deck_d-0.8,0.8), 0.04, 1.6, M["bamboo"])
    add_box("BambooTop", (0,-bd/2-deck_d-0.8,1.62), (bw,0.06,0.06), M["bamboo"])

def _asian_columns(bw, bd, base_z, total_h, M):
    for xi,yi in [(1,-1),(-1,-1),(1,1),(-1,1)]:
        cx, cy = xi*(bw/2-0.45), yi*(bd/2-0.45)
        add_cylinder(f"AsianCol_{xi}_{yi}", (cx,cy,base_z+total_h/2), 0.32, total_h, M["accent"], verts=14)
        # Column base plinth
        add_box(f"ColBase_{xi}_{yi}", (cx,cy,base_z+0.2), (0.65,0.65,0.4), M["stone_zen"])
        # Column cap
        add_box(f"ColCap_{xi}_{yi}", (cx,cy,base_z+total_h-0.18), (0.65,0.65,0.36), M["accent"])
    # Decorative horizontal bands
    for fi in range(2):
        z = base_z + (fi+0.5)*(total_h/2)
        add_box(f"AsianBand_{fi}", (0,-bd/2-0.01,z), (bw+0.06,0.06,0.35), M["accent"])

def _industrial_elements(bw, bd, base_z, total_h, M):
    # Exposed steel I-beams on facade
    for i in range(max(2,int(bw/5))):
        cx = -bw/2+0.4 + (bw-0.8)/(max(2,int(bw/5))-1)*i if max(2,int(bw/5))>1 else 0
        add_box(f"Beam_{i}", (cx,-bd/2-0.06,base_z+total_h/2), (0.18,0.12,total_h), M["steel"])
    # Loading dock
    add_box("LoadingDock", (-bw/4,-bd/2-0.5,base_z), (bw/4,1.0,0.35), M["asphalt"])
    add_box("DockBumper",  (-bw/4,-bd/2-0.05,base_z+0.2),(bw/4-0.2,0.12,0.15), M["dark_metal"])

def _villa_arches(bw, bd, base_z, total_h, M):
    # Arched loggia on ground floor south face
    arch_w = 2.2; arch_h = 3.2; n = max(3,int(bw/arch_w/1.5))
    for i in range(n):
        cx = -bw/3 + (bw*0.67/(n-1))*i if n>1 else 0
        # Arch keystone
        add_box(f"ArchPier_{i}L", (cx-arch_w/2,-bd/2-0.12,base_z+arch_h/2),
                (0.28, 0.35, arch_h), M["plaster"])
        add_box(f"ArchPier_{i}R", (cx+arch_w/2,-bd/2-0.12,base_z+arch_h/2),
                (0.28, 0.35, arch_h), M["plaster"])
        bpy.ops.mesh.primitive_cylinder_add(vertices=14,radius=arch_w/2,depth=0.35,
            location=(cx,-bd/2-0.12,base_z+arch_h))
        arch = bpy.context.active_object; arch.name = f"ArchHead_{i}"
        arch.scale.z = 0.45; bpy.ops.object.transform_apply(scale=True)
        assign(arch, M["plaster"])
    add_box("VillaLoggia",(0,-bd/2-0.05,base_z+arch_h+0.3),(bw*0.68,0.3,0.3), M["plaster"])

# ══════════════════════════════════════════════════════════════════════════════
# 12. BALCONIES
# ══════════════════════════════════════════════════════════════════════════════
def generate_balconies(bw, bd, num_floors, floor_h, base_z, M, sc_cfg, style_name):
    bd_dep = 1.6; slab_t = 0.12; rail_h = 1.0; rail_t = 0.05
    n = max(3, int(bw/sc_cfg["bay_width"]))
    bay = bw/n; bw_actual = bay*0.82

    for fi in range(1, num_floors):
        fz = base_z + fi*floor_h
        for bi in range(n):
            cx = -bw/2+bay*(bi+0.5)
            by = -(bd/2+bd_dep/2)
            add_box(f"Bal_Slab_{fi}_{bi}", (cx,by,fz+slab_t/2), (bw_actual,bd_dep,slab_t), M["slab"])
            add_box(f"Bal_Soffit_{fi}_{bi}", (cx,by,fz-0.02), (bw_actual+0.04,bd_dep+0.04,0.04), M["concrete"])

            # Style-specific railings
            if style_name in ("modern","scandinavian","industrial"):
                # Glass panel railing
                add_box(f"Bal_Glass_{fi}_{bi}", (cx,by-bd_dep/2+0.02,fz+slab_t+rail_h/2),
                        (bw_actual-0.1,0.015,rail_h*0.85), M["glass_panel"])
                add_box(f"Bal_Rail_{fi}_{bi}", (cx,by-bd_dep/2+rail_t/2,fz+slab_t+rail_h),
                        (bw_actual,rail_t,0.05), M["steel"])
            elif style_name in ("japanese","asian"):
                # Wood lattice railing
                for ri in range(int(bw_actual/0.35)):
                    rx = cx-bw_actual/2+ri*0.35
                    add_box(f"BalLat_{fi}_{bi}_{ri}", (rx,by-bd_dep/2+0.04,fz+slab_t+rail_h/2),
                            (0.05,0.06,rail_h), M["wood_dark"])
                add_box(f"Bal_RailTop_{fi}_{bi}", (cx,by-bd_dep/2+0.04,fz+slab_t+rail_h),
                        (bw_actual,0.06,0.06), M["wood_dark"])
            else:
                # Stone balustrade
                for pi in range(int(bw_actual/0.45)+1):
                    px = cx-bw_actual/2+pi*0.45
                    add_box(f"BalPost_{fi}_{bi}_{pi}", (px,by-bd_dep/2+0.08,fz+slab_t+rail_h/2),
                            (0.12,0.12,rail_h), M["column"])
                add_box(f"Bal_Coping_{fi}_{bi}", (cx,by-bd_dep/2+0.06,fz+slab_t+rail_h),
                        (bw_actual+0.05,0.22,0.1), M["marble"] if style_name in ("villa","classical") else M["facade"])

# ══════════════════════════════════════════════════════════════════════════════
# 13. LOBBY / ENTRANCE
# ══════════════════════════════════════════════════════════════════════════════
def generate_lobby(bw, bd, base_z, M, style_name):
    lw = min(7.5, bw*0.42); ld = 2.8; lh = 4.0
    lx, ly = 0.0, -(bd/2+ld/2)

    if style_name == "japanese":
        # Torii-style gate
        add_box("Torii_L", (-lw/2-0.1, ly-ld/2, base_z+lh/2), (0.22,0.22,lh), M["accent"])
        add_box("Torii_R", ( lw/2+0.1, ly-ld/2, base_z+lh/2), (0.22,0.22,lh), M["accent"])
        add_box("Torii_Top",   (0, ly-ld/2, base_z+lh),     (lw+0.8, 0.22, 0.22), M["accent"])
        add_box("Torii_Top2",  (0, ly-ld/2, base_z+lh-0.5), (lw+0.4, 0.18, 0.14), M["accent"])
        return
    elif style_name == "asian":
        add_box("Gate_L", (-lw/2, ly-ld/2, base_z+lh/2), (0.3,0.3,lh), M["accent"])
        add_box("Gate_R", ( lw/2, ly-ld/2, base_z+lh/2), (0.3,0.3,lh), M["accent"])
        add_box("Gate_Top",(0, ly-ld/2, base_z+lh+0.12), (lw+1.0,0.3,0.35), M["roof"])
        return

    add_box("Lobby_Canopy", (lx,ly,base_z+lh+0.1), (lw+0.4,ld+0.4,0.15), M["concrete"])
    add_box("Lobby_Soffit", (lx,ly,base_z+lh-0.05), (lw,ld,0.1), M["facade"])
    for tag,xo in [("L",-lw/2),("R",lw/2)]:
        add_box(f"Lobby_Wall_{tag}",(xo,ly,base_z+lh/2),(0.2,ld,lh), M["facade"])
    add_box("Lobby_Glass",(lx,ly-ld/2+0.05,base_z+lh/2-0.3),(lw-0.4,0.04,lh-0.6), M["glass"])
    for tag,xo in [("L",-1.3),("R",1.3)]:
        add_box(f"DFrame_{tag}",(xo,ly-ld/2+0.06,base_z+1.15),(0.08,0.06,2.3), M["frame"])
    add_box("Lobby_Header",(lx,ly-ld/2+0.06,base_z+2.35),(2.9,0.06,0.14), M["frame"])
    for si in range(3):
        add_box(f"Step_{si}",(lx,-(bd/2+0.3+si*0.35),base_z-0.15+si*0.15),
                (lw+0.6,0.35,0.15), M["pavement"])

# ══════════════════════════════════════════════════════════════════════════════
# 14. STAIRCASE CORE
# ══════════════════════════════════════════════════════════════════════════════
def generate_staircase(bw, bd, num_floors, floor_h, base_z, M):
    sw, sd = 3.0, 5.0
    sx = bw/2-sw-0.8; sy = -bd/2+sd/2+0.8
    shaft_h = num_floors*floor_h+1.0
    add_box("StairCore",     (sx,sy,base_z+shaft_h/2),(sw+0.5,sd+0.5,shaft_h+0.3), M["concrete"])
    add_box("StairCore_Inn", (sx,sy,base_z+shaft_h/2),(sw,sd,shaft_h),             M["wall"])
    td, th = sd/16, floor_h/16
    for fi in range(num_floors-1):
        fz = base_z+fi*floor_h
        for step in range(16):
            add_box(f"Stair_{fi}_{step}",
                (sx, -bd/2+0.8+step*td+td/2, fz+step*th+th/2),
                (sw, td, th*(step+1)), M["slab"])

# ══════════════════════════════════════════════════════════════════════════════
# 15. POOL
# ══════════════════════════════════════════════════════════════════════════════
def generate_pool(bw, bd, pool_cfg, base_z, M, style_name):
    pw = float(pool_cfg.get("width",12)); pl = float(pool_cfg.get("length",6))
    pd = float(pool_cfg.get("depth",1.8)); wt = 0.3
    px = bw/2+pw/2+3.5; py = -(bd/4); pz = base_z
    dm = 2.0; dt = 0.25

    tile_mat = M["marble"] if style_name in ("villa","classical") else M["pool_tile"]
    add_box("Pool_Deck",(px,py,pz+dt/2),(pw+dm*2,pl+dm*2,dt), tile_mat)
    for name,loc,dims in [
        ("Pool_Wall_N",(px,py+pl/2-wt/2,pz-pd/2),(pw,wt,pd)),
        ("Pool_Wall_S",(px,py-pl/2+wt/2,pz-pd/2),(pw,wt,pd)),
        ("Pool_Wall_E",(px+pw/2-wt/2,py,pz-pd/2),(wt,pl,pd)),
        ("Pool_Wall_W",(px-pw/2+wt/2,py,pz-pd/2),(wt,pl,pd)),
        ("Pool_Floor", (px,py,pz-pd-0.15),(pw,pl,0.3)),
    ]:
        add_box(name,loc,dims, M["pool_tile"])
    add_box("Pool_Water",(px,py,pz-0.12),(pw-wt*2,pl-wt*2,0.08), M["pool_water"])

    # Deck chairs
    for ci,(cx,cy) in enumerate([
        (px-pw/2-0.6, py-pl/2-1.0),(px-pw/2-0.6, py+pl/2+0.4),
        (px+pw/2+0.6, py-pl/2-1.0),(px+pw/2+0.6, py+pl/2+0.4),
    ]):
        chair_mat = M["marble"] if style_name in ("villa","classical") else M["pavement"]
        add_box(f"Chair_{ci}",(cx,cy,pz+dt+0.2),(1.8,0.65,0.1), chair_mat)
        add_box(f"Back_{ci}", (cx,cy+0.2,pz+dt+0.55),(1.8,0.08,0.6), chair_mat)

    # Umbrella
    add_box("UmbPole",(px,py+pl/2+dm-0.5,pz+dt+1.2),(0.06,0.06,2.4), M["steel"])
    add_cone("UmbTop",(px,py+pl/2+dm-0.5,pz+dt+2.62),1.8,0.25,verts=8,
             mat=M["accent"])

    # Ladder
    for ri in range(5):
        add_box(f"Rung_{ri}",(px+pw/2-0.3,py+pl/2-0.3,pz-ri*0.32-0.15),(0.28,0.03,0.03), M["steel"])

    # Japanese style: add koi pond instead
    if style_name == "japanese":
        assign(bpy.data.objects.get("Pool_Water") or bpy.context.active_object,
               mat("koi", (0.05,0.32,0.42), rough=0.0, alpha=0.55, transmission=0.82))

# ══════════════════════════════════════════════════════════════════════════════
# 16. GARAGE
# ══════════════════════════════════════════════════════════════════════════════
def generate_garage(bw, bd, garage_cfg, base_z, M, style_name):
    cap = int(garage_cfg.get("capacity",2))
    bay_w = 3.4; bay_d = 7.0; gh = 3.0; gw = bay_w*cap; gt = 0.25
    gx = -(bw/2+gw/2+1.5); gy = -(bd/2-bay_d/2-1.0); gz = base_z+gh/2

    wall_mat = M["plaster"] if style_name == "villa" else M["facade"]
    add_box("Garage_Roof",(gx,gy,base_z+gh+gt/2),(gw+0.4,bay_d+0.4,gt), M["slab"])
    add_box("Garage_RoofEdge",(gx,gy,base_z+gh+gt+0.04),(gw+0.5,bay_d+0.5,0.08), M["concrete"])
    for name,loc,dims in [
        ("Garage_Back",(gx, gy+bay_d/2,gz),(gw,gt,gh)),
        ("Garage_L",   (gx-gw/2,gy,gz),   (gt,bay_d,gh)),
        ("Garage_R",   (gx+gw/2,gy,gz),   (gt,bay_d,gh)),
        ("Garage_Floor",(gx,gy,base_z+0.08),(gw,bay_d,0.16)),
    ]:
        assign(add_box(name,loc,dims, wall_mat),
               M["asphalt"] if "Floor" in name else wall_mat)

    # Overhead doors
    dh, dw = 2.5, bay_w*0.88
    for di in range(cap):
        dx = gx-gw/2+bay_w*(di+0.5)
        dy = gy-bay_d/2+gt/2+0.03
        for pi in range(4):
            pz = base_z+pi*(dh/4)+dh/8
            add_box(f"GD_{di}_p{pi}",(dx,dy,pz),(dw,0.06,dh/4-0.03), M["dark_metal"])
        add_box(f"GDFrame_{di}",(dx,dy,base_z+dh/2),(dw+0.12,0.10,dh+0.12), M["frame"])

    # Driveway with lane markings
    drive_l = 12.0
    add_box("Driveway",(gx,gy-bay_d/2-drive_l/2,base_z+0.04),(gw+1.0,drive_l,0.08), M["asphalt"])
    for di in range(cap-1):
        mx = gx-gw/2+bay_w*(di+1)
        add_box(f"Lane_{di}",(mx,gy-bay_d/2-drive_l/2,base_z+0.09),(0.08,drive_l,0.02),
                mat(f"wht_{di}",(0.9,0.9,0.9), rough=0.7))

# ══════════════════════════════════════════════════════════════════════════════
# 17. STYLE-SPECIFIC VEGETATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_vegetation(bw, bd, M, style_name, rng):
    # Safe positions (away from pool-right, garage-left, lobby-front)
    positions = [
        (-bw/2-5,  bd/2+6),( bw/2+5,  bd/2+6),(0,         bd/2+7),
        (-bw/2-6,  bd/4),  ( bw/2+6,  bd/2),
        (-bw/2-9, -bd/2-6),( bw/2+9, -bd/2-6),
        (-bw/2-4,  bd/2+2),(-bw/2-8,  bd/4),
        ( bw/2+7,  bd/2+3),
    ]
    fol = [M["foliage_a"], M["foliage_b"], M["foliage_dark"]]

    for i,(tx,ty) in enumerate(positions):
        h  = rng.uniform(4.5, 8.5)
        r  = rng.uniform(1.6, 3.0)
        fm = fol[i % 3]

        if style_name == "japanese":
            _tree_japanese(i, tx, ty, h, r, M, rng)
        elif style_name in ("villa","classical"):
            _tree_cypress(i, tx, ty, h, M)
        elif style_name == "industrial":
            _tree_simple(i, tx, ty, h*0.7, r*0.8, M, fm)
        else:
            _tree_layered(i, tx, ty, h, r, M, fm, rng)

    # Shrubs (style-aware, away from pool/garage)
    shrub_pos = [(-bw/2+2,bd/2+0.6),( bw/2-2,bd/2+0.6),
                 (-bw/4,  bd/2+0.6),(-bw/2+1,-(bd/2+0.6)),
                 ( bw/4, -(bd/2+0.6))]
    for si,(sx,sy) in enumerate(shrub_pos):
        if style_name == "japanese":
            add_box(f"MossRock_{si}",(sx,sy,rng.uniform(0.2,0.5)),
                    (rng.uniform(0.4,0.9),rng.uniform(0.4,0.9),rng.uniform(0.15,0.4)), M["stone_zen"])
        else:
            r = rng.uniform(0.45, 0.85)
            add_cone(f"Shrub_{si}",(sx,sy,r),r,r*1.2,verts=8,mat=M["foliage_a"])

def _tree_layered(i, tx, ty, h, r, M, fm, rng):
    add_cylinder(f"Trunk_{i}",(tx,ty,rng.uniform(0.7,1.1)),rng.uniform(0.15,0.25),rng.uniform(1.0,1.8),M["bark"],verts=8)
    for layer in range(3):
        lh = h*(0.5-layer*0.12); lr = r*(1.0-layer*0.25); lz = 1.5+h*(0.35+layer*0.18)
        add_cone(f"Can_{i}_{layer}",(tx,ty,lz),lr,lh,verts=9,mat=fm)

def _tree_japanese(i, tx, ty, h, r, M, rng):
    """Cherry / bonsai-style layered round canopy."""
    add_cylinder(f"JTrunk_{i}",(tx,ty,h*0.2),0.14,h*0.4,M["bark"],verts=7)
    for ci in range(5):
        cr = r*(0.5+rng.uniform(0,0.4)); ch = cr*0.55
        cx_ = tx+rng.uniform(-r*0.4,r*0.4); cy_ = ty+rng.uniform(-r*0.4,r*0.4)
        cz  = h*rng.uniform(0.3,0.75)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cr,location=(cx_,cy_,cz))
        c = bpy.context.active_object; c.name = f"JCan_{i}_{ci}"
        mat_choice = mat(f"jp_blossom_{i}_{ci}", (0.95,0.62,0.75) if ci%2==0 else (0.18,0.45,0.15), rough=1.0)
        assign(c, mat_choice)

def _tree_cypress(i, tx, ty, h, M):
    """Tall narrow cypress for villa/classical."""
    add_cylinder(f"CypTrunk_{i}",(tx,ty,h*0.3),0.08,h*0.6,M["bark"],verts=6)
    add_cone(f"CypCrown_{i}",(tx,ty,h*0.55),0.55,h*0.7,verts=8,mat=M["foliage_dark"])

def _tree_simple(i, tx, ty, h, r, M, fm):
    add_cylinder(f"IndTrunk_{i}",(tx,ty,h*0.25),0.12,h*0.5,M["bark"],verts=6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r,location=(tx,ty,h*0.55))
    c = bpy.context.active_object; c.name = f"IndCrown_{i}"
    assign(c, fm)

# ══════════════════════════════════════════════════════════════════════════════
# 18. EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def export_glb(output_path):
    # Remove cameras (they lock viewer orbit)
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
    )
    print(f"[BlenderWorker] Exported → {output_path}  ({os.path.getsize(output_path)//1024} KB)")

# ══════════════════════════════════════════════════════════════════════════════
# 19. MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    s           = get_schema()
    num_floors  = max(1, int(s.get("floors", 3)))
    bw          = float(s.get("width",   20.0))
    bd          = float(s.get("depth",   15.0))
    floor_h     = float(s.get("floor_height", 3.2))
    style_name  = s.get("style", "modern").lower()
    has_pool    = bool(s.get("pool"))
    has_garage  = bool(s.get("garage"))
    has_bals    = s.get("balconies", True)
    output_path = s.get("output_path", "/tmp/building.glb")
    pool_cfg    = s.get("pool",   {"width":12,"length":6,"depth":1.8}) if has_pool else {}
    garage_cfg  = s.get("garage", {"capacity":2}) if has_garage else {}

    sc_cfg    = get_style(style_name)
    total_h   = num_floors*floor_h+2.5
    rng       = random.Random(s.get("seed", 42))

    print(f"[BlenderWorker] Style={style_name} | {num_floors}F {bw}×{bd}m | pool={has_pool} garage={has_garage}")

    clear_scene()
    setup_render(samples=96)
    M = build_material_set(sc_cfg)

    generate_terrain(bw, bd, M, style_name)
    base_z = generate_foundation(bw, bd, M, style_name)
    generate_floors(bw, bd, num_floors, floor_h, base_z, M)
    generate_walls(bw, bd, num_floors, floor_h, base_z, M, sc_cfg, style_name)

    if has_bals and num_floors > 1:
        generate_balconies(bw, bd, num_floors, floor_h, base_z, M, sc_cfg, style_name)

    generate_lobby(bw, bd, base_z, M, style_name)
    generate_staircase(bw, bd, num_floors, floor_h, base_z, M)
    generate_roof(bw, bd, base_z+num_floors*floor_h, M, sc_cfg, style_name)
    generate_style_features(bw, bd, base_z, num_floors, floor_h, M, style_name)

    if has_pool:    generate_pool(bw, bd, pool_cfg, base_z, M, style_name)
    if has_garage:  generate_garage(bw, bd, garage_cfg, base_z, M, style_name)

    generate_vegetation(bw, bd, M, style_name, rng)
    setup_lighting(bw, bd, total_h, sc_cfg, style_name)
    setup_camera(bw, bd, total_h)

    export_glb(output_path)

    meta = {"status":"success","output_path":output_path,"style":style_name,
            "floors":num_floors,"width":bw,"depth":bd,
            "features":{"pool":has_pool,"garage":has_garage,"balconies":has_bals}}
    with open(output_path.replace(".glb","_meta.json"),"w") as f:
        json.dump(meta,f,indent=2)
    print("[BlenderWorker] DONE")

if __name__ == "__main__":
    main()
