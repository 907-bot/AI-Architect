"""
backend/workers/blender_worker.py  — Photorealistic procedural architecture
Runs INSIDE Blender subprocess. Never import this in FastAPI.

Invoke:
  blender --background --python backend/workers/blender_worker.py -- schema.json
"""

import bpy
import sys, json, os, math, random

# ─────────────────────────────────────────────
# 1. ARG PARSING
# ─────────────────────────────────────────────

def get_schema_path():
    argv = sys.argv
    try:
        return argv[argv.index("--") + 1]
    except (ValueError, IndexError):
        raise RuntimeError("Pass schema path after --")

def load_schema(path):
    with open(path) as f:
        return json.load(f)

# ─────────────────────────────────────────────
# 2. SCENE UTILS
# ─────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

def add_box(name, loc, dims, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
    return obj

def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ─────────────────────────────────────────────
# 3. PBR MATERIAL LIBRARY
# ─────────────────────────────────────────────

def make_mat(name, base_color, roughness=0.5, metallic=0.0,
             specular=0.5, alpha=1.0, transmission=0.0,
             emission=None, bump_strength=0.0):
    """Create a full PBR Principled BSDF material."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out  = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bsdf.inputs["Base Color"].default_value   = (*base_color[:3], 1.0)
    bsdf.inputs["Roughness"].default_value    = roughness
    bsdf.inputs["Metallic"].default_value     = metallic
    bsdf.inputs["Alpha"].default_value        = alpha

    # Blender 4+ uses "Specular IOR Level", fallback for older
    for sp_name in ("Specular IOR Level", "Specular"):
        if sp_name in bsdf.inputs:
            bsdf.inputs[sp_name].default_value = specular
            break

    if transmission > 0:
        for tr_name in ("Transmission Weight", "Transmission"):
            if tr_name in bsdf.inputs:
                bsdf.inputs[tr_name].default_value = transmission
                break
        mat.blend_method = "BLEND"

    if alpha < 1.0:
        mat.blend_method = "BLEND"

    if emission:
        for em_name in ("Emission Color", "Emission"):
            if em_name in bsdf.inputs:
                bsdf.inputs[em_name].default_value = (*emission, 1.0)
                break
        bsdf.inputs["Emission Strength"].default_value = 2.0

    # Procedural bump for concrete / ground
    if bump_strength > 0.0:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value    = 80.0
        noise.inputs["Detail"].default_value   = 8.0
        noise.inputs["Roughness"].default_value = 0.6
        bump  = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value  = bump_strength
        bump.inputs["Distance"].default_value  = 0.005
        nt.links.new(noise.outputs["Fac"],    bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"],  bsdf.inputs["Normal"])

    out.location  = (300, 0)
    bsdf.location = (0, 0)
    return mat


def build_materials():
    m = {}

    # Structural
    m["concrete"]    = make_mat("concrete",    (0.78,0.76,0.74), roughness=0.88, bump_strength=0.4)
    m["concrete_dark"]= make_mat("concrete_dark",(0.55,0.53,0.51),roughness=0.9,  bump_strength=0.3)
    m["slab"]        = make_mat("slab",        (0.72,0.70,0.68), roughness=0.92, bump_strength=0.2)

    # Glass & Metal
    m["glass"]       = make_mat("glass",       (0.72,0.88,0.98), roughness=0.02,
                                metallic=0.0, specular=1.0, alpha=0.15, transmission=0.92)
    m["glass_tint"]  = make_mat("glass_tint",  (0.50,0.70,0.90), roughness=0.05,
                                metallic=0.0, specular=1.0, alpha=0.2, transmission=0.88)
    m["frame_black"] = make_mat("frame_black", (0.08,0.08,0.09), roughness=0.25, metallic=0.85)
    m["frame_silver"]= make_mat("frame_silver",(0.75,0.75,0.78), roughness=0.15, metallic=0.95)
    m["railing"]     = make_mat("railing",     (0.12,0.12,0.14), roughness=0.2,  metallic=0.9)
    m["steel"]       = make_mat("steel",       (0.65,0.65,0.67), roughness=0.1,  metallic=1.0)

    # Roof & Facade
    m["roof_dark"]   = make_mat("roof_dark",   (0.15,0.15,0.17), roughness=0.75)
    m["facade_white"]= make_mat("facade_white",(0.92,0.91,0.90), roughness=0.85, bump_strength=0.15)
    m["cladding"]    = make_mat("cladding",    (0.30,0.45,0.55), roughness=0.5)

    # Ground & Landscape
    m["ground"]      = make_mat("ground",      (0.22,0.18,0.14), roughness=1.0,  bump_strength=0.8)
    m["grass"]       = make_mat("grass",       (0.18,0.48,0.15), roughness=1.0,  bump_strength=0.6)
    m["asphalt"]     = make_mat("asphalt",     (0.12,0.12,0.13), roughness=0.95, bump_strength=0.5)
    m["pavement"]    = make_mat("pavement",    (0.60,0.58,0.55), roughness=0.85, bump_strength=0.3)
    m["path"]        = make_mat("path",        (0.70,0.68,0.65), roughness=0.9)

    # Pool
    m["pool_water"]  = make_mat("pool_water",  (0.04,0.52,0.78), roughness=0.0,
                                metallic=0.0, specular=1.0, alpha=0.65, transmission=0.8)
    m["pool_tile"]   = make_mat("pool_tile",   (0.78,0.90,0.95), roughness=0.15, bump_strength=0.1)
    m["pool_edge"]   = make_mat("pool_edge",   (0.90,0.88,0.85), roughness=0.2)

    # Wood & Nature
    m["wood"]        = make_mat("wood",        (0.42,0.28,0.16), roughness=0.8,  bump_strength=0.5)
    m["bark"]        = make_mat("bark",        (0.30,0.20,0.12), roughness=0.9,  bump_strength=0.6)
    m["foliage"]     = make_mat("foliage",     (0.12,0.42,0.10), roughness=1.0,  bump_strength=0.4)
    m["foliage2"]    = make_mat("foliage2",    (0.08,0.35,0.08), roughness=1.0)

    # Doors / Accent
    m["door_metal"]  = make_mat("door_metal",  (0.18,0.18,0.20), roughness=0.2,  metallic=0.8)
    m["lobby_glass"] = make_mat("lobby_glass", (0.80,0.92,1.00), roughness=0.01,
                                metallic=0.0, specular=1.0, alpha=0.10, transmission=0.95)

    return m

# ─────────────────────────────────────────────
# 4. RENDER ENGINE — CYCLES PBR
# ─────────────────────────────────────────────

def setup_cycles(samples=128):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.preview_samples = 32
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

# ─────────────────────────────────────────────
# 5. LIGHTING — Physical Sky
# ─────────────────────────────────────────────

def setup_lighting(bw, bd, total_h):
    # Physical sky world shader
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out   = nt.nodes.new("ShaderNodeOutputWorld")
    sky   = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "HOSEK_WILKIE"
    sky.sun_elevation  = math.radians(42)
    sky.sun_rotation   = math.radians(215)
    sky.altitude       = 100.0
    sky.turbidity      = 2.0
    bg    = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.2
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Generated"], sky.inputs["Vector"])
    nt.links.new(sky.outputs["Color"],  bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # Sun lamp
    bpy.ops.object.light_add(type="SUN", location=(bw*1.5, -bd*2, total_h*2.5))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 5.0
    sun.data.angle  = math.radians(0.5)
    sun.rotation_euler = (math.radians(48), math.radians(0), math.radians(215))

    # Soft fill from opposite side
    bpy.ops.object.light_add(type="AREA", location=(-bw*2, bd*2, total_h*1.5))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 300
    fill.data.size   = 25.0
    fill.rotation_euler = (math.radians(-40), 0, math.radians(-45))

# ─────────────────────────────────────────────
# 6. CAMERA
# ─────────────────────────────────────────────

def setup_camera(bw, bd, total_h):
    dist = max(bw, bd) * 2.5
    cam_loc = (dist * 0.9, -dist * 1.1, total_h * 0.85)
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.name = "ArchCamera"
    bpy.context.scene.camera = cam

    # Aim at building center slightly above base
    target_z = total_h * 0.4
    dx = 0 - cam_loc[0]
    dy = 0 - cam_loc[1]
    dz = target_z - cam_loc[2]
    cam.rotation_euler = (
        math.atan2(math.sqrt(dx**2 + dy**2), -dz) - math.pi/2,
        0,
        math.atan2(dx, -dy)
    )
    cam.data.lens = 35
    cam.data.clip_end = 2000

# ─────────────────────────────────────────────
# 7. TERRAIN
# ─────────────────────────────────────────────

def generate_terrain(bw, bd, m):
    plot = max(bw, bd) + 50
    # Base ground
    add_box("Ground", (0, 0, -0.3), (plot, plot, 0.6), m["ground"])
    # Grass surround (single large piece — no patches)
    add_box("Grass", (0, 0, 0.02), (plot - 2, plot - 2, 0.04), m["grass"])
    # Hardscape pad under building
    pad_w = bw + 8
    pad_d = bd + 8
    add_box("BasePad", (0, 0, 0.05), (pad_w, pad_d, 0.1), m["pavement"])
    # Perimeter path
    path_w = 1.8
    for name, loc, dims in [
        ("Path_N", (0,  pad_d/2 + path_w/2, 0.08), (pad_w + path_w*2, path_w, 0.06)),
        ("Path_S", (0, -pad_d/2 - path_w/2, 0.08), (pad_w + path_w*2, path_w, 0.06)),
        ("Path_E", ( pad_w/2 + path_w/2, 0, 0.08), (path_w, pad_d, 0.06)),
        ("Path_W", (-pad_w/2 - path_w/2, 0, 0.08), (path_w, pad_d, 0.06)),
    ]:
        add_box(name, loc, dims, m["path"])

# ─────────────────────────────────────────────
# 8. FOUNDATION
# ─────────────────────────────────────────────

def generate_foundation(bw, bd, m):
    fh = 0.8
    add_box("Foundation", (0, 0, fh/2), (bw, bd, fh), m["slab"])
    # Plinth detail strip
    add_box("Plinth", (0, 0, fh + 0.05), (bw + 0.3, bd + 0.3, 0.1), m["concrete_dark"])
    return fh

# ─────────────────────────────────────────────
# 9. FLOORS
# ─────────────────────────────────────────────

def generate_floors(bw, bd, num_floors, floor_h, base_z, m):
    slab_t = 0.28
    for i in range(num_floors + 1):  # +1 for roof slab
        z = base_z + i * floor_h
        add_box(f"Slab_{i}", (0, 0, z + slab_t/2), (bw, bd, slab_t), m["slab"])
        if i < num_floors:
            # Floor edge band
            add_box(f"SlabEdge_{i}", (0, 0, z + slab_t + 0.02),
                    (bw + 0.15, bd + 0.15, 0.04), m["concrete_dark"])

# ─────────────────────────────────────────────
# 10. WALLS WITH WINDOWS
# ─────────────────────────────────────────────

def generate_walls(bw, bd, num_floors, floor_h, base_z, m):
    wall_t = 0.28
    win_h  = floor_h * 0.52
    win_gap_bot = floor_h * 0.18    # sill height
    win_above   = floor_h - win_h - win_gap_bot

    for fi in range(num_floors):
        fz = base_z + fi * floor_h

        # North & South glazed facades
        for side, cy in [("N", bd/2 - wall_t/2), ("S", -(bd/2 - wall_t/2))]:
            _glazed_wall(f"Wall_{side}", fi, bw, cy, fz, floor_h,
                         wall_t, win_h, win_gap_bot, win_above, m, side=="S")

        # East & West — solid concrete with narrow strip windows
        for side, cx in [("E", bw/2 - wall_t/2), ("W", -(bw/2 - wall_t/2))]:
            # Solid panel
            add_box(f"Wall_{side}_{fi}", (cx, 0, fz + floor_h/2),
                    (wall_t, bd, floor_h), m["concrete"])
            # Narrow vertical strip window
            sw = 0.8
            add_box(f"Win_Strip_{side}_{fi}",
                    (cx + wall_t*0.1*(1 if side=="E" else -1), 0, fz + floor_h/2),
                    (0.04, sw, win_h), m["glass_tint"])


def _glazed_wall(prefix, fi, bw, cy, fz, floor_h, wall_t,
                 win_h, win_gap_bot, win_above, m, is_south):
    num_bays = max(3, int(bw / 3.8))
    bay_w    = bw / num_bays
    win_w    = bay_w * 0.72
    col_w    = (bay_w - win_w) / 2

    sign = 1 if is_south else -1

    for wi in range(num_bays):
        cx = -bw/2 + bay_w * (wi + 0.5)

        # Column (concrete between windows)
        for tag, x_off in [("L", cx - win_w/2 - col_w/2), ("R", cx + win_w/2 + col_w/2)]:
            add_box(f"{prefix}_{fi}_col{tag}{wi}",
                    (x_off, cy, fz + floor_h/2),
                    (col_w, wall_t, floor_h), m["facade_white"])

        # Sill panel
        add_box(f"{prefix}_{fi}_sill{wi}",
                (cx, cy, fz + win_gap_bot/2),
                (win_w, wall_t, win_gap_bot), m["facade_white"])

        # Spandrel (above window)
        z_span = fz + win_gap_bot + win_h + win_above/2
        add_box(f"{prefix}_{fi}_span{wi}",
                (cx, cy, z_span),
                (win_w, wall_t, win_above), m["concrete_dark"])

        # Glass pane
        gz = fz + win_gap_bot + win_h/2
        gy = cy + sign * wall_t * 0.05
        add_box(f"{prefix}_{fi}_glass{wi}",
                (cx, gy, gz),
                (win_w - 0.04, 0.035, win_h - 0.04), m["glass"])

        # Frame — top & bottom
        for tag, z_off in [("T", gz + win_h/2 - 0.03), ("B", gz - win_h/2 + 0.03)]:
            add_box(f"{prefix}_{fi}_fh{tag}{wi}",
                    (cx, gy, z_off),
                    (win_w, 0.05, 0.06), m["frame_black"])
        # Frame — sides
        for tag, x_off in [("L", cx - win_w/2 + 0.03), ("R", cx + win_w/2 - 0.03)]:
            add_box(f"{prefix}_{fi}_fv{tag}{wi}",
                    (x_off, gy, gz),
                    (0.06, 0.05, win_h), m["frame_black"])

        # Mullion (centre divider)
        add_box(f"{prefix}_{fi}_mull{wi}",
                (cx, gy, gz),
                (0.05, 0.04, win_h), m["frame_black"])

# ─────────────────────────────────────────────
# 11. BALCONIES
# ─────────────────────────────────────────────

def generate_balconies(bw, bd, num_floors, floor_h, base_z, m):
    bal_depth = 1.6
    slab_t    = 0.12
    rail_h    = 1.05
    rail_t    = 0.05
    num_bals  = max(3, int(bw / 4.0))
    bay_w     = bw / num_bals
    bal_w     = bay_w * 0.82

    for fi in range(1, num_floors):
        fz = base_z + fi * floor_h
        for bi in range(num_bals):
            cx = -bw/2 + bay_w * (bi + 0.5)
            by = -(bd/2 + bal_depth/2)

            # Slab
            add_box(f"Bal_Slab_{fi}_{bi}",
                    (cx, by, fz + slab_t/2),
                    (bal_w, bal_depth, slab_t), m["slab"])
            # Underside detail
            add_box(f"Bal_Soffit_{fi}_{bi}",
                    (cx, by, fz - 0.02),
                    (bal_w + 0.04, bal_depth + 0.04, 0.04), m["concrete_dark"])

            # Glass railing panel
            add_box(f"Bal_Glass_{fi}_{bi}",
                    (cx, by - bal_depth/2 + 0.02, fz + slab_t + rail_h/2),
                    (bal_w - 0.1, 0.015, rail_h * 0.85), m["glass_tint"])

            # Top handrail bar
            add_box(f"Bal_Rail_{fi}_{bi}",
                    (cx, by - bal_depth/2 + rail_t/2, fz + slab_t + rail_h),
                    (bal_w, rail_t, 0.05), m["frame_silver"])

            # Side posts
            for tag, x_off in [("L", cx - bal_w/2 + rail_t/2),
                                ("R", cx + bal_w/2 - rail_t/2)]:
                add_box(f"Bal_Post_{tag}_{fi}_{bi}",
                        (x_off, by, fz + slab_t + rail_h/2),
                        (rail_t, bal_depth, rail_h), m["frame_silver"])

# ─────────────────────────────────────────────
# 12. LOBBY ENTRANCE
# ─────────────────────────────────────────────

def generate_lobby(bw, bd, base_z, m):
    """Glass lobby canopy + entrance doors on south face."""
    lobby_w = min(8.0, bw * 0.45)
    lobby_d = 3.0
    lobby_h = 4.2
    lx = 0.0
    ly = -(bd/2 + lobby_d/2)
    lz = base_z

    # Canopy
    add_box("Lobby_Canopy", (lx, ly, lz + lobby_h + 0.1),
            (lobby_w + 0.4, lobby_d + 0.4, 0.15), m["concrete_dark"])
    # Canopy underlit
    add_box("Lobby_Soffit", (lx, ly, lz + lobby_h - 0.05),
            (lobby_w, lobby_d, 0.1), m["facade_white"])

    # Side walls
    for tag, x_off in [("L", -(lobby_w/2)), ("R", lobby_w/2)]:
        add_box(f"Lobby_Wall_{tag}", (x_off, ly, lz + lobby_h/2),
                (0.2, lobby_d, lobby_h), m["concrete"])

    # Glass facade
    add_box("Lobby_Glass", (lx, ly - lobby_d/2 + 0.05, lz + lobby_h/2 - 0.3),
            (lobby_w - 0.4, 0.04, lobby_h - 0.6), m["lobby_glass"])

    # Door frames
    for tag, x_off in [("L", -1.4), ("R", 1.4)]:
        add_box(f"Lobby_DoorFrame_{tag}",
                (x_off, ly - lobby_d/2 + 0.06, lz + 1.2),
                (0.08, 0.06, 2.4), m["frame_black"])
    # Door header
    add_box("Lobby_Header", (lx, ly - lobby_d/2 + 0.06, lz + 2.55),
            (3.2, 0.06, 0.15), m["frame_black"])

    # Steps
    for si in range(3):
        add_box(f"Lobby_Step_{si}",
                (lx, -(bd/2 + 0.3 + si * 0.35), lz - 0.15 + si * 0.15),
                (lobby_w + 0.6, 0.35, 0.15), m["pavement"])

# ─────────────────────────────────────────────
# 13. ROOF
# ─────────────────────────────────────────────

def generate_roof(bw, bd, top_z, style, m):
    t  = 0.35
    oh = 0.4
    add_box("Roof_Slab", (0, 0, top_z + t/2), (bw + oh*2, bd + oh*2, t), m["roof_dark"])

    if style == "flat":
        # Parapet
        ph = 1.0
        pt = 0.22
        for name, loc, dims in [
            ("Par_N",  (0,   bd/2+oh, top_z+t+ph/2), (bw+oh*2, pt, ph)),
            ("Par_S",  (0,  -bd/2-oh, top_z+t+ph/2), (bw+oh*2, pt, ph)),
            ("Par_E",  ( bw/2+oh, 0,  top_z+t+ph/2), (pt, bd+oh*2+pt*2, ph)),
            ("Par_W",  (-bw/2-oh, 0,  top_z+t+ph/2), (pt, bd+oh*2+pt*2, ph)),
        ]:
            add_box(name, loc, dims, m["facade_white"])
        # Parapet cap
        cap_t = 0.04
        cap_top = top_z + t + ph + cap_t/2
        for name, loc, dims in [
            ("Cap_N", (0,   bd/2+oh, cap_top), (bw+oh*2+0.05, pt+0.06, cap_t)),
            ("Cap_S", (0,  -bd/2-oh, cap_top), (bw+oh*2+0.05, pt+0.06, cap_t)),
            ("Cap_E", ( bw/2+oh, 0,  cap_top), (pt+0.06, bd+oh*2+pt*2+0.05, cap_t)),
            ("Cap_W", (-bw/2-oh, 0,  cap_top), (pt+0.06, bd+oh*2+pt*2+0.05, cap_t)),
        ]:
            add_box(name, loc, dims, m["concrete_dark"])

    elif style == "pitched":
        rh = bw * 0.22
        bpy.ops.mesh.primitive_cone_add(
            vertices=4, radius1=(bw+oh*2)/2, depth=rh,
            location=(0, 0, top_z+t+rh/2))
        r = bpy.context.active_object
        r.name = "Roof_Ridge"
        r.rotation_euler = (0, 0, math.radians(45))
        assign_mat(r, m["roof_dark"])

# ─────────────────────────────────────────────
# 14. STAIRCASE CORE
# ─────────────────────────────────────────────

def generate_staircase(bw, bd, num_floors, floor_h, base_z, m):
    sw   = 3.2
    sd   = 5.5
    sx   = bw/2 - sw - 0.8
    sy_c = -bd/2 + sd/2 + 0.8
    tread_h = floor_h / 18
    tread_d = sd / 18

    # Stair shaft (elevator/stair core)
    shaft_h = num_floors * floor_h + 1.0
    add_box("StairCore", (sx, sy_c, base_z + shaft_h/2),
            (sw + 0.5, sd + 0.5, shaft_h + 0.3), m["concrete_dark"])
    add_box("StairCore_Inner", (sx, sy_c, base_z + shaft_h/2),
            (sw, sd, shaft_h), m["concrete"])

    for fi in range(num_floors - 1):
        fz = base_z + fi * floor_h
        for step in range(18):
            add_box(f"Stair_{fi}_{step}",
                    (sx, -bd/2 + 0.8 + step * tread_d + tread_d/2,
                     fz + step * tread_h + tread_h/2),
                    (sw, tread_d, tread_h * (step + 1)), m["slab"])

# ─────────────────────────────────────────────
# 15. SWIMMING POOL (front-right, clearly visible)
# ─────────────────────────────────────────────

def generate_pool(bw, bd, pool_cfg, base_z, m):
    pw  = float(pool_cfg.get("width",  12.0))
    pl  = float(pool_cfg.get("length",  6.0))
    pd  = float(pool_cfg.get("depth",   1.8))
    wt  = 0.30

    # Place pool to the RIGHT of building, in front (south side)
    px = bw/2 + pw/2 + 4.0
    py = -(bd/2 - pl/2 - 1.0)   # aligned with front half
    pz = base_z

    deck_m = 2.0
    deck_t = 0.25

    # Deck (surrounding patio)
    add_box("Pool_Deck", (px, py, pz + deck_t/2),
            (pw + deck_m*2, pl + deck_m*2, deck_t), m["pool_edge"])

    # Pool shell walls
    for name, loc, dims in [
        ("Pool_Wall_N", (px, py + pl/2 - wt/2, pz - pd/2), (pw, wt, pd)),
        ("Pool_Wall_S", (px, py - pl/2 + wt/2, pz - pd/2), (pw, wt, pd)),
        ("Pool_Wall_E", (px + pw/2 - wt/2, py,  pz - pd/2), (wt, pl, pd)),
        ("Pool_Wall_W", (px - pw/2 + wt/2, py,  pz - pd/2), (wt, pl, pd)),
        ("Pool_Floor",  (px, py, pz - pd - 0.15), (pw, pl, 0.3)),
    ]:
        add_box(name, loc, dims, m["pool_tile"])

    # Water surface
    add_box("Pool_Water", (px, py, pz - 0.12),
            (pw - wt*2, pl - wt*2, 0.08), m["pool_water"])

    # Deck chairs (simple boxes)
    chair_positions = [(px - pw/2 - 0.6, py - pl/2 - 1.0),
                       (px - pw/2 - 0.6, py + pl/2 + 0.4),
                       (px + pw/2 + 0.6, py - pl/2 - 1.0),
                       (px + pw/2 + 0.6, py + pl/2 + 0.4)]
    for ci, (cx, cy) in enumerate(chair_positions):
        add_box(f"DeckChair_{ci}", (cx, cy, pz + deck_t + 0.2),
                (1.8, 0.65, 0.1), m["pavement"])
        add_box(f"ChairBack_{ci}", (cx, cy + 0.2, pz + deck_t + 0.55),
                (1.8, 0.08, 0.6), m["pavement"])

    # Diving board end marker
    add_box("Pool_Ladder_Post_A", (px + pw/2 - 0.15, py + pl/2 - 0.3, pz - 0.4),
            (0.05, 0.05, pd * 0.8), m["steel"])
    add_box("Pool_Ladder_Post_B", (px + pw/2 - 0.45, py + pl/2 - 0.3, pz - 0.4),
            (0.05, 0.05, pd * 0.8), m["steel"])
    for ri in range(5):
        add_box(f"Pool_Rung_{ri}",
                (px + pw/2 - 0.3, py + pl/2 - 0.3, pz - ri * 0.32 - 0.15),
                (0.28, 0.03, 0.03), m["steel"])

    # Umbrella (parasol)
    add_box("Umbrella_Pole", (px, py + pl/2 + deck_m - 0.5, pz + deck_t + 1.2),
            (0.06, 0.06, 2.4), m["steel"])
    bpy.ops.mesh.primitive_cone_add(
        vertices=8, radius1=1.8, depth=0.25,
        location=(px, py + pl/2 + deck_m - 0.5, pz + deck_t + 2.5 + 0.12))
    umb = bpy.context.active_object
    umb.name = "Umbrella_Top"
    assign_mat(umb, make_mat("umbrella", (0.85,0.15,0.15), roughness=0.9))

# ─────────────────────────────────────────────
# 16. GARAGE (left side, clearly visible)
# ─────────────────────────────────────────────

def generate_garage(bw, bd, garage_cfg, base_z, m):
    capacity = int(garage_cfg.get("capacity", 2))
    bay_w    = 3.4
    bay_d    = 7.0
    gh       = 3.0
    gw       = bay_w * capacity
    gt       = 0.25  # wall thickness

    # Place on the LEFT side, front-aligned so it's visible
    gx = -(bw/2 + gw/2 + 1.5)
    gy = -(bd/2 - bay_d/2 - 1.0)
    gz_mid = base_z + gh/2

    # Roof slab
    add_box("Garage_Roof", (gx, gy, base_z + gh + gt/2),
            (gw + 0.4, bay_d + 0.4, gt), m["slab"])
    # Roof edge
    add_box("Garage_RoofEdge", (gx, gy, base_z + gh + gt + 0.04),
            (gw + 0.5, bay_d + 0.5, 0.08), m["concrete_dark"])

    # Walls
    for name, loc, dims in [
        ("Garage_Wall_Back", (gx,  gy + bay_d/2, gz_mid), (gw, gt, gh)),
        ("Garage_Wall_L",    (gx - gw/2, gy,     gz_mid), (gt, bay_d, gh)),
        ("Garage_Wall_R",    (gx + gw/2, gy,     gz_mid), (gt, bay_d, gh)),
        ("Garage_Floor",     (gx, gy, base_z + 0.08),     (gw, bay_d, 0.16)),
    ]:
        mat = m["asphalt"] if "Floor" in name else m["concrete"]
        add_box(name, loc, dims, mat)

    # Overhead garage doors
    door_h  = 2.5
    door_w  = bay_w * 0.88
    panel_h = door_h / 4
    for di in range(capacity):
        dx = gx - gw/2 + bay_w * (di + 0.5)
        dy = gy - bay_d/2 + gt/2 + 0.03
        for pi in range(4):
            pz = base_z + pi * panel_h + panel_h/2
            add_box(f"GDoor_{di}_p{pi}",
                    (dx, dy, pz),
                    (door_w, 0.06, panel_h - 0.03), m["door_metal"])
        # Door frame
        add_box(f"GDoor_Frame_{di}",
                (dx, dy, base_z + door_h/2),
                (door_w + 0.12, 0.10, door_h + 0.12), m["frame_black"])

    # Driveway
    drive_l = 12.0
    add_box("Driveway", (gx, gy - bay_d/2 - drive_l/2, base_z + 0.04),
            (gw + 1.0, drive_l, 0.08), m["asphalt"])
    # Lane markings (white strips)
    for di in range(capacity - 1):
        mx = gx - gw/2 + bay_w * (di + 1)
        add_box(f"Lane_{di}", (mx, gy - bay_d/2 - drive_l/2, base_z + 0.09),
                (0.08, drive_l, 0.02), make_mat(f"white_{di}", (0.9,0.9,0.9), roughness=0.7))

# ─────────────────────────────────────────────
# 17. TREES & LANDSCAPING
# ─────────────────────────────────────────────

def generate_vegetation(bw, bd, m):
    rng = random.Random(7)

    positions = [
        (-bw/2 - 5, -bd/2 - 5, 0),
        ( bw/2 + 5, -bd/2 - 5, 0),
        (-bw/2 - 5,  bd/2 + 5, 0),
        ( bw/2 + 5,  bd/2 + 5, 0),
        (-bw/2 - 3,  0, 0),
        ( bw/2 + 3,  0, 0),
        (0,          bd/2 + 5, 0),
        (0,         -bd/2 - 5, 0),
        (-bw/2 - 8, -bd/4, 0),
        ( bw/2 + 8,  bd/4, 0),
    ]

    foliage_mats = [m["foliage"], m["foliage2"]]

    for i, (tx, ty, _) in enumerate(positions):
        h   = rng.uniform(5.0, 9.0)
        r   = rng.uniform(1.8, 3.2)
        fmat = foliage_mats[i % 2]

        # Trunk
        bpy.ops.mesh.primitive_cylinder_add(
            radius=rng.uniform(0.18, 0.28), depth=rng.uniform(1.2, 2.0),
            location=(tx, ty, rng.uniform(0.6, 1.0)))
        trunk = bpy.context.active_object
        trunk.name = f"Trunk_{i}"
        assign_mat(trunk, m["bark"])

        # Canopy layers
        for layer in range(3):
            lh = h * (0.5 - layer * 0.12)
            lr = r  * (1.0 - layer * 0.25)
            lz = 1.5 + h * (0.35 + layer * 0.18)
            bpy.ops.mesh.primitive_cone_add(
                vertices=8, radius1=lr, depth=lh,
                location=(tx, ty, lz))
            canopy = bpy.context.active_object
            canopy.name = f"Canopy_{i}_{layer}"
            assign_mat(canopy, fmat)

    # Hedge / shrubs along building base
    shrub_positions = [
        (-bw/2 + 2, -(bd/2 + 0.5)), (0, -(bd/2 + 0.5)),
        ( bw/2 - 2, -(bd/2 + 0.5)), (-bw/2 + 2, bd/2 + 0.5),
    ]
    for si, (sx, sy) in enumerate(shrub_positions):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=rng.uniform(0.5, 0.9),
            location=(sx, sy, rng.uniform(0.5, 0.9)))
        shrub = bpy.context.active_object
        shrub.name = f"Shrub_{si}"
        assign_mat(shrub, m["foliage"])

# ─────────────────────────────────────────────
# 18. EXPORT
# ─────────────────────────────────────────────

def export_glb(output_path):
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
    )
    print(f"[BlenderWorker] Exported GLB → {output_path}")

# ─────────────────────────────────────────────
# 19. MAIN
# ─────────────────────────────────────────────

def main():
    schema_path = get_schema_path()
    print(f"[BlenderWorker] Loading schema: {schema_path}")
    s = load_schema(schema_path)

    num_floors  = max(1, int(s.get("floors", 3)))
    bw          = float(s.get("width", 20.0))
    bd          = float(s.get("depth", 15.0))
    floor_h     = float(s.get("floor_height", 3.2))
    roof_style  = s.get("roof_style", "flat")
    arch_style  = s.get("style", "modern")
    has_pool    = bool(s.get("pool"))
    has_garage  = bool(s.get("garage"))
    has_bals    = s.get("balconies", True)
    output_path = s.get("output_path", "/tmp/building.glb")
    pool_cfg    = s.get("pool",   {"width": 12, "length": 6, "depth": 1.8}) if has_pool else {}
    garage_cfg  = s.get("garage", {"capacity": 2}) if has_garage else {}

    random.seed(s.get("seed", 42))
    total_h = num_floors * floor_h + 2.0

    print(f"[BlenderWorker] {num_floors}F {bw}x{bd}m | pool={has_pool} garage={has_garage}")

    clear_scene()
    setup_cycles(samples=96)

    m = build_materials()

    generate_terrain(bw, bd, m)
    base_z = generate_foundation(bw, bd, m)
    generate_floors(bw, bd, num_floors, floor_h, base_z, m)
    generate_walls(bw, bd, num_floors, floor_h, base_z, m)

    if has_bals:
        generate_balconies(bw, bd, num_floors, floor_h, base_z, m)

    generate_lobby(bw, bd, base_z, m)
    generate_staircase(bw, bd, num_floors, floor_h, base_z, m)
    generate_roof(bw, bd, base_z + num_floors * floor_h, roof_style, m)

    if has_pool:
        generate_pool(bw, bd, pool_cfg, base_z, m)

    if has_garage:
        generate_garage(bw, bd, garage_cfg, base_z, m)

    generate_vegetation(bw, bd, m)
    setup_lighting(bw, bd, total_h)
    setup_camera(bw, bd, total_h)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    export_glb(output_path)

    meta = {
        "status": "success", "output_path": output_path,
        "floors": num_floors, "width": bw, "depth": bd,
        "features": {"pool": has_pool, "garage": has_garage,
                     "balconies": has_bals, "lobby": True,
                     "staircase": True, "vegetation": True},
    }
    meta_path = output_path.replace(".glb", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print("[BlenderWorker] DONE")


if __name__ == "__main__":
    main()
