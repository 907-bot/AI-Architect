"""
backend/workers/blender_worker.py

THIS SCRIPT RUNS INSIDE BLENDER PYTHON — NOT FASTAPI.
Invoked via:
  blender --background --python backend/workers/blender_worker.py -- /path/to/schema.json

bpy is available here because Blender provides it.
"""

import bpy
import sys
import json
import os
import math
import random

# ─────────────────────────────────────────────
# 1. ARGUMENT PARSING
# ─────────────────────────────────────────────

def get_schema_path() -> str:
    """Extract schema path from blender CLI args (everything after --)"""
    argv = sys.argv
    try:
        idx = argv.index("--")
        return argv[idx + 1]
    except (ValueError, IndexError):
        raise RuntimeError("No schema path passed. Usage: blender --background --python blender_worker.py -- schema.json")


def load_schema(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 2. SCENE HELPERS
# ─────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def new_material(name: str, r: float, g: float, b: float, alpha: float = 1.0,
                 roughness: float = 0.5, metallic: float = 0.0, specular: float = 0.5) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (r, g, b, alpha)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Specular IOR Level"].default_value = specular
    if alpha < 1.0:
        mat.blend_method = "BLEND"
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_box(name: str, loc: tuple, dims: tuple, mat: bpy.types.Material = None) -> bpy.types.Object:
    """Add a box mesh at location with given dimensions (x, y, z)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (dims[0], dims[1], dims[2])
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        assign_material(obj, mat)
    return obj


# ─────────────────────────────────────────────
# 3. MATERIAL LIBRARY
# ─────────────────────────────────────────────

def build_materials(style: str) -> dict:
    palette = {
        "modern":     {"concrete": (0.82, 0.80, 0.78), "glass": (0.55, 0.75, 0.95, 0.35),
                       "frame": (0.15, 0.15, 0.15),   "slab": (0.72, 0.70, 0.68),
                       "roof": (0.20, 0.20, 0.20),     "ground": (0.25, 0.22, 0.18),
                       "pool_water": (0.05, 0.55, 0.80, 0.7), "pool_tile": (0.80, 0.90, 0.95),
                       "asphalt": (0.18, 0.18, 0.18),  "railing": (0.70, 0.70, 0.72)},
        "classical":  {"concrete": (0.93, 0.90, 0.84), "glass": (0.65, 0.80, 0.70, 0.40),
                       "frame": (0.85, 0.82, 0.75),    "slab": (0.88, 0.85, 0.80),
                       "roof": (0.55, 0.35, 0.25),     "ground": (0.35, 0.30, 0.22),
                       "pool_water": (0.05, 0.55, 0.80, 0.7), "pool_tile": (0.90, 0.85, 0.70),
                       "asphalt": (0.28, 0.26, 0.22),  "railing": (0.75, 0.72, 0.65)},
    }
    p = palette.get(style, palette["modern"])

    def c(key): return p.get(key, (0.8, 0.8, 0.8))

    mats = {
        "concrete": new_material("concrete", *c("concrete"), roughness=0.85),
        "glass":    new_material("glass",    *c("glass"),    roughness=0.05, metallic=0.0, specular=1.0),
        "frame":    new_material("frame",    *c("frame"),    roughness=0.3, metallic=0.6),
        "slab":     new_material("slab",     *c("slab"),     roughness=0.9),
        "roof":     new_material("roof",     *c("roof"),     roughness=0.7),
        "ground":   new_material("ground",   *c("ground"),   roughness=1.0),
        "pool_water": new_material("pool_water", *c("pool_water"), roughness=0.0, metallic=0.0, specular=1.0),
        "pool_tile":  new_material("pool_tile",  *c("pool_tile"),  roughness=0.2),
        "asphalt":  new_material("asphalt",  *c("asphalt"),  roughness=0.95),
        "railing":  new_material("railing",  *c("railing"),  roughness=0.2, metallic=0.8),
        "grass":    new_material("grass",    0.20, 0.55, 0.18, roughness=1.0),
        "wood":     new_material("wood",     0.55, 0.38, 0.22, roughness=0.8),
        "white":    new_material("white",    0.95, 0.95, 0.95, roughness=0.8),
        "dark_metal": new_material("dark_metal", 0.12, 0.12, 0.14, roughness=0.2, metallic=0.9),
    }
    return mats


# ─────────────────────────────────────────────
# 4. TERRAIN / GROUND
# ─────────────────────────────────────────────

def generate_terrain(bw: float, bd: float, mats: dict):
    """Ground slab + grass surround."""
    plot_w = bw + 30
    plot_d = bd + 30
    # Main ground
    add_box("Ground_Plot", (0, 0, -0.25), (plot_w, plot_d, 0.5), mats["ground"])
    # Grass surround zones
    pad = 6
    add_box("Grass_Front", (0, -(bd / 2 + pad / 2), 0.05), (plot_w, pad, 0.1), mats["grass"])
    add_box("Grass_Back",  (0,  (bd / 2 + pad / 2), 0.05), (plot_w, pad, 0.1), mats["grass"])
    add_box("Grass_Left",  (-(bw / 2 + pad / 2), 0, 0.05), (pad, plot_d, 0.1), mats["grass"])
    add_box("Grass_Right", ( (bw / 2 + pad / 2), 0, 0.05), (pad, plot_d, 0.1), mats["grass"])


# ─────────────────────────────────────────────
# 5. FOUNDATION
# ─────────────────────────────────────────────

def generate_foundation(bw: float, bd: float, mats: dict) -> float:
    """Returns top-of-foundation Z."""
    fh = 0.6
    add_box("Foundation", (0, 0, fh / 2), (bw, bd, fh), mats["slab"])
    return fh


# ─────────────────────────────────────────────
# 6. FLOOR SLABS
# ─────────────────────────────────────────────

def generate_floors(bw: float, bd: float, num_floors: int, floor_h: float,
                    base_z: float, mats: dict) -> list:
    """Returns list of floor bottom Z positions."""
    floor_bottoms = []
    slab_t = 0.25
    for i in range(num_floors):
        z = base_z + i * floor_h + slab_t / 2
        add_box(f"FloorSlab_{i+1}", (0, 0, z), (bw, bd, slab_t), mats["slab"])
        floor_bottoms.append(base_z + i * floor_h)
    return floor_bottoms


# ─────────────────────────────────────────────
# 7. WALLS
# ─────────────────────────────────────────────

def generate_walls(bw: float, bd: float, num_floors: int, floor_h: float,
                   base_z: float, wall_t: float, mats: dict):
    """Exterior walls for all floors, with window gap spaces cut out by boolean logic via separate wall segments."""
    win_h = floor_h * 0.5
    win_w = 2.4
    win_gap = win_h * 0.25    # gap from floor to window bottom
    wall_above = floor_h - win_h - win_gap  # above window

    for floor_i in range(num_floors):
        fz = base_z + floor_i * floor_h  # floor bottom z

        # ── North Wall (y = +bd/2)
        _wall_with_windows("Wall_N", floor_i, bw, "N",
                           center_y= bd / 2 - wall_t / 2,
                           fz=fz, floor_h=floor_h, wall_t=wall_t,
                           win_w=win_w, win_h=win_h, win_gap=win_gap,
                           wall_above=wall_above, mats=mats)

        # ── South Wall (y = -bd/2)
        _wall_with_windows("Wall_S", floor_i, bw, "S",
                           center_y=-(bd / 2 - wall_t / 2),
                           fz=fz, floor_h=floor_h, wall_t=wall_t,
                           win_w=win_w, win_h=win_h, win_gap=win_gap,
                           wall_above=wall_above, mats=mats)

        # ── East Wall  (x = +bw/2)  — solid side walls
        z_mid = fz + floor_h / 2
        add_box(f"Wall_E_{floor_i+1}", ( bw / 2 - wall_t / 2, 0, z_mid),
                (wall_t, bd, floor_h), mats["concrete"])
        add_box(f"Wall_W_{floor_i+1}", (-bw / 2 + wall_t / 2, 0, z_mid),
                (wall_t, bd, floor_h), mats["concrete"])


def _wall_with_windows(prefix, floor_i, bw, side,
                       center_y, fz, floor_h, wall_t,
                       win_w, win_h, win_gap, wall_above, mats):
    """Generate a wall face with evenly spaced window openings."""
    num_wins = max(2, int(bw / 4.5))
    section_w = bw / num_wins
    win_w_clamped = min(win_w, section_w * 0.65)

    for wi in range(num_wins):
        cx = -bw / 2 + section_w * (wi + 0.5)

        # Solid column between windows
        col_w = (section_w - win_w_clamped) / 2

        # Left column
        add_box(f"{prefix}_{floor_i+1}_col_L{wi}",
                (cx - win_w_clamped / 2 - col_w / 2, center_y, fz + floor_h / 2),
                (col_w, wall_t, floor_h), mats["concrete"])
        # Right column
        add_box(f"{prefix}_{floor_i+1}_col_R{wi}",
                (cx + win_w_clamped / 2 + col_w / 2, center_y, fz + floor_h / 2),
                (col_w, wall_t, floor_h), mats["concrete"])

        # Below window
        add_box(f"{prefix}_{floor_i+1}_below{wi}",
                (cx, center_y, fz + win_gap / 2),
                (win_w_clamped, wall_t, win_gap), mats["concrete"])

        # Above window
        z_above = fz + win_gap + win_h + wall_above / 2
        add_box(f"{prefix}_{floor_i+1}_above{wi}",
                (cx, center_y, z_above),
                (win_w_clamped, wall_t, wall_above), mats["concrete"])

        # ── Window glass
        win_cx_y = center_y + (wall_t * 0.1 * (1 if "N" in prefix else -1))
        win_z = fz + win_gap + win_h / 2
        add_box(f"Win_Glass_{prefix}_{floor_i+1}_{wi}",
                (cx, win_cx_y, win_z),
                (win_w_clamped, 0.04, win_h), mats["glass"])

        # ── Window frame (top/bottom bars)
        for tag, z_off in [("T", win_z + win_h / 2), ("B", win_z - win_h / 2)]:
            add_box(f"Win_Frame_{prefix}_{floor_i+1}_{wi}_{tag}",
                    (cx, win_cx_y, z_off),
                    (win_w_clamped + 0.05, 0.06, 0.06), mats["frame"])
        # Side bars
        for tag, x_off in [("L", cx - win_w_clamped / 2), ("R", cx + win_w_clamped / 2)]:
            add_box(f"Win_Frame_{prefix}_{floor_i+1}_{wi}_{tag}",
                    (x_off, win_cx_y, win_z),
                    (0.06, 0.06, win_h + 0.05), mats["frame"])


# ─────────────────────────────────────────────
# 8. BALCONIES
# ─────────────────────────────────────────────

def generate_balconies(bw: float, bd: float, num_floors: int, floor_h: float,
                        base_z: float, wall_t: float, mats: dict):
    """Add balconies on front (south) face, every floor above ground."""
    bal_depth = 1.8
    bal_h = 0.12
    railing_h = 1.0
    railing_t = 0.06
    num_bals = max(2, int(bw / 5))
    section_w = bw / num_bals
    bal_w = section_w * 0.75

    for floor_i in range(1, num_floors):
        fz = base_z + floor_i * floor_h
        for bi in range(num_bals):
            cx = -bw / 2 + section_w * (bi + 0.5)
            by = -(bd / 2 + bal_depth / 2)

            # Slab
            add_box(f"Balcony_Slab_{floor_i}_{bi}",
                    (cx, by, fz + bal_h / 2),
                    (bal_w, bal_depth, bal_h), mats["slab"])

            # Front railing
            add_box(f"Balcony_Rail_F_{floor_i}_{bi}",
                    (cx, by - bal_depth / 2 + railing_t / 2, fz + bal_h + railing_h / 2),
                    (bal_w, railing_t, railing_h), mats["railing"])

            # Side railings
            for tag, x_off in [("L", cx - bal_w / 2 + railing_t / 2),
                                ("R", cx + bal_w / 2 - railing_t / 2)]:
                add_box(f"Balcony_Rail_{tag}_{floor_i}_{bi}",
                        (x_off, by, fz + bal_h + railing_h / 2),
                        (railing_t, bal_depth, railing_h), mats["railing"])

            # Glass panel
            add_box(f"Balcony_Glass_{floor_i}_{bi}",
                    (cx, by - bal_depth / 2 + 0.05, fz + bal_h + railing_h / 2),
                    (bal_w - 0.2, 0.02, railing_h * 0.8), mats["glass"])


# ─────────────────────────────────────────────
# 9. ROOF
# ─────────────────────────────────────────────

def generate_roof(bw: float, bd: float, top_z: float, style: str, mats: dict):
    roof_t = 0.4
    overhang = 0.5
    add_box("Roof_Slab",
            (0, 0, top_z + roof_t / 2),
            (bw + overhang * 2, bd + overhang * 2, roof_t), mats["roof"])

    if style == "flat":
        # Parapet walls
        p_h = 0.9
        p_t = 0.2
        top = top_z + roof_t
        for name, loc, dims in [
            ("Par_N", (0,  bd / 2 + overhang, top + p_h / 2), (bw + overhang * 2, p_t, p_h)),
            ("Par_S", (0, -bd / 2 - overhang, top + p_h / 2), (bw + overhang * 2, p_t, p_h)),
            ("Par_E", ( bw / 2 + overhang, 0, top + p_h / 2), (p_t, bd + overhang * 2 + p_t * 2, p_h)),
            ("Par_W", (-bw / 2 - overhang, 0, top + p_h / 2), (p_t, bd + overhang * 2 + p_t * 2, p_h)),
        ]:
            add_box(name, loc, dims, mats["concrete"])

    elif style == "pitched":
        # Simple pitched roof ridge
        ridge_h = bw * 0.18
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=(bw + overhang * 2) / 2,
                                        depth=ridge_h,
                                        location=(0, 0, top_z + roof_t + ridge_h / 2))
        ridge = bpy.context.active_object
        ridge.name = "Roof_Ridge"
        assign_material(ridge, mats["roof"])


# ─────────────────────────────────────────────
# 10. STAIRCASE
# ─────────────────────────────────────────────

def generate_staircase(bw: float, bd: float, num_floors: int, floor_h: float,
                        base_z: float, mats: dict):
    """Central interior staircase block per floor pair."""
    stair_w = 2.8
    stair_d = 5.0
    tread_h = floor_h / 16
    tread_d = stair_d / 16
    sx = bw / 2 - stair_w - 1.0

    for floor_i in range(num_floors - 1):
        fz = base_z + floor_i * floor_h
        for step in range(16):
            add_box(f"Stair_{floor_i}_{step}",
                    (sx, -bd / 2 + 1.0 + step * tread_d + tread_d / 2,
                     fz + step * tread_h + tread_h / 2),
                    (stair_w, tread_d, tread_h * (step + 1)), mats["slab"])

    # Stairwell shaft outline
    shaft_h = num_floors * floor_h
    add_box("Stairwell_Shaft",
            (sx, -bd / 2 + 1.0 + stair_d / 2, base_z + shaft_h / 2),
            (stair_w + 0.4, stair_d + 0.4, shaft_h + 0.2), mats["concrete"])


# ─────────────────────────────────────────────
# 11. SWIMMING POOL
# ─────────────────────────────────────────────

def generate_pool(bw: float, bd: float, pool_cfg: dict, base_z: float, mats: dict):
    pw = pool_cfg.get("width", 12.0)
    pl = pool_cfg.get("length", 6.0)
    pd = pool_cfg.get("depth", 1.8)

    # Position pool behind building
    px = bw / 2 + pw / 2 + 2.0
    py = 0.0
    pz = base_z

    # Surround deck
    deck_t = 0.3
    deck_margin = 1.2
    add_box("Pool_Deck",
            (px, py, pz + deck_t / 2),
            (pw + deck_margin * 2, pl + deck_margin * 2, deck_t), mats["pool_tile"])

    # Pool walls
    wall_t = 0.25
    for name, loc, dims in [
        ("Pool_Wall_N", (px, py + pl / 2 - wall_t / 2, pz - pd / 2),  (pw, wall_t, pd)),
        ("Pool_Wall_S", (px, py - pl / 2 + wall_t / 2, pz - pd / 2),  (pw, wall_t, pd)),
        ("Pool_Wall_E", (px + pw / 2 - wall_t / 2, py,  pz - pd / 2), (wall_t, pl, pd)),
        ("Pool_Wall_W", (px - pw / 2 + wall_t / 2, py,  pz - pd / 2), (wall_t, pl, pd)),
        ("Pool_Floor",  (px, py, pz - pd), (pw, pl, 0.3)),
    ]:
        add_box(name, loc, dims, mats["pool_tile"])

    # Water plane
    add_box("Pool_Water",
            (px, py, pz - 0.15),
            (pw - wall_t * 2, pl - wall_t * 2, 0.1), mats["pool_water"])

    # Ladder rungs
    for ri in range(4):
        add_box(f"Pool_Ladder_{ri}",
                (px + pw / 2 - 0.15, py + pl / 2 - 0.3, pz - ri * 0.45),
                (0.04, 0.4, 0.04), mats["railing"])


# ─────────────────────────────────────────────
# 12. GARAGE
# ─────────────────────────────────────────────

def generate_garage(bw: float, bd: float, garage_cfg: dict, base_z: float, mats: dict):
    capacity = garage_cfg.get("capacity", 2)
    bay_w = 3.2
    bay_d = 6.5
    gw = bay_w * capacity
    gh = 2.8

    # Position garage on side of building
    gx = -(bw / 2 + gw / 2 + 0.5)
    gy = bd / 2 - bay_d / 2 - 0.5
    gz = base_z + gh / 2

    # Roof slab
    add_box("Garage_Roof", (gx, gy, base_z + gh + 0.15), (gw + 0.3, bay_d + 0.3, 0.3), mats["slab"])

    # Side walls
    for name, loc, dims in [
        ("Garage_Wall_Back",  (gx, gy + bay_d / 2, gz), (gw, 0.25, gh)),
        ("Garage_Wall_Left",  (gx - gw / 2, gy, gz),    (0.25, bay_d, gh)),
        ("Garage_Wall_Right", (gx + gw / 2, gy, gz),    (0.25, bay_d, gh)),
        ("Garage_Floor",      (gx, gy, base_z + 0.1),   (gw, bay_d, 0.2)),
    ]:
        add_box(name, loc, dims, mats["asphalt"] if "Floor" in name else mats["concrete"])

    # Garage doors
    door_h = 2.4
    door_w = bay_w * 0.9
    for di in range(capacity):
        dx = gx - gw / 2 + bay_w * (di + 0.5)
        add_box(f"Garage_Door_{di}",
                (dx, gy - bay_d / 2 + 0.05, base_z + door_h / 2),
                (door_w, 0.06, door_h), mats["dark_metal"])

    # Driveway
    drive_w = gw + 2.0
    drive_l = 8.0
    add_box("Driveway",
            (gx, gy - bay_d / 2 - drive_l / 2, base_z),
            (drive_w, drive_l, 0.08), mats["asphalt"])


# ─────────────────────────────────────────────
# 13. TREES / VEGETATION
# ─────────────────────────────────────────────

def generate_trees(bw: float, bd: float, mats: dict):
    """Simple cone+cylinder trees scattered around plot."""
    positions = [
        (-bw / 2 - 4, -bd / 2 - 4),
        ( bw / 2 + 4, -bd / 2 - 4),
        (-bw / 2 - 4,  bd / 2 + 4),
        ( bw / 2 + 4,  bd / 2 + 4),
        (-bw / 2 - 2,  0),
        ( bw / 2 + 2,  0),
        (0, -bd / 2 - 5),
        (0,  bd / 2 + 5),
    ]
    for i, (tx, ty) in enumerate(positions):
        h = random.uniform(4.5, 7.0)
        r = random.uniform(1.5, 2.5)

        # Trunk
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=1.5, location=(tx, ty, 0.75))
        trunk = bpy.context.active_object
        trunk.name = f"Tree_Trunk_{i}"
        assign_material(trunk, mats["wood"])

        # Canopy
        bpy.ops.mesh.primitive_cone_add(radius1=r, depth=h, location=(tx, ty, 1.5 + h / 2))
        canopy = bpy.context.active_object
        canopy.name = f"Tree_Canopy_{i}"
        assign_material(canopy, mats["grass"])


# ─────────────────────────────────────────────
# 14. LIGHTING
# ─────────────────────────────────────────────

def setup_lighting(bw: float, bd: float, total_h: float):
    # Sun
    bpy.ops.object.light_add(type="SUN", location=(bw * 2, -bd * 2, total_h * 3))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(0), math.radians(30))

    # Ambient sky
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.53, 0.70, 0.90, 1.0)
        bg.inputs["Strength"].default_value = 0.8

    # Fill light
    bpy.ops.object.light_add(type="AREA", location=(-bw, bd, total_h * 2))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 500
    fill.data.size = 20.0


# ─────────────────────────────────────────────
# 15. CAMERA
# ─────────────────────────────────────────────

def setup_camera(bw: float, bd: float, total_h: float):
    dist = max(bw, bd) * 2.2
    bpy.ops.object.camera_add(
        location=(dist, -dist * 1.1, total_h * 0.9),
    )
    cam = bpy.context.active_object
    cam.name = "ArchCamera"
    bpy.context.scene.camera = cam

    # Point camera at building center
    bpy.ops.object.constraint_add(type="TRACK_TO")
    cam.constraints["Track To"].target = None
    cam.rotation_euler = (
        math.radians(60),
        0,
        math.radians(45),
    )


# ─────────────────────────────────────────────
# 16. EXPORT
# ─────────────────────────────────────────────

def export_glb(output_path: str):
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
        export_lights=True,
        export_cameras=True,
        export_normals=True,
        export_tangents=False,
        export_texcoords=True,
        export_colors=True,
    )
    print(f"[BlenderWorker] Exported GLB → {output_path}")


# ─────────────────────────────────────────────
# 17. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    schema_path = get_schema_path()
    print(f"[BlenderWorker] Loading schema: {schema_path}")
    schema = load_schema(schema_path)

    # ── Schema defaults
    building_type = schema.get("building_type", "apartment")
    num_floors    = max(1, schema.get("floors", 3))
    bw            = float(schema.get("width", 20.0))
    bd            = float(schema.get("depth", 15.0))
    floor_h       = float(schema.get("floor_height", 3.2))
    wall_t        = 0.3
    roof_style    = schema.get("roof_style", "flat")
    arch_style    = schema.get("style", "modern")
    has_pool      = schema.get("pool") not in (None, False, {})
    has_garage    = schema.get("garage") not in (None, False, {})
    has_balconies = schema.get("balconies", True)
    output_path   = schema.get("output_path", "/tmp/building.glb")

    pool_cfg   = schema.get("pool",   {"width": 12, "length": 6, "depth": 1.8}) if has_pool else {}
    garage_cfg = schema.get("garage", {"capacity": 2}) if has_garage else {}

    random.seed(schema.get("seed", 42))

    total_h = num_floors * floor_h + 1.0

    print(f"[BlenderWorker] Building: {building_type}, {num_floors} floors, {bw}m x {bd}m, style={arch_style}")
    print(f"[BlenderWorker] Pool={has_pool}, Garage={has_garage}, Balconies={has_balconies}")

    # ── Clear
    clear_scene()

    # ── Materials
    mats = build_materials(arch_style)

    # ── Terrain
    generate_terrain(bw, bd, mats)

    # ── Foundation
    foundation_top = generate_foundation(bw, bd, mats)

    # ── Floors
    base_z = foundation_top
    generate_floors(bw, bd, num_floors, floor_h, base_z, mats)

    # ── Walls + Windows
    generate_walls(bw, bd, num_floors, floor_h, base_z, wall_t, mats)

    # ── Balconies
    if has_balconies:
        generate_balconies(bw, bd, num_floors, floor_h, base_z, wall_t, mats)

    # ── Staircase
    generate_staircase(bw, bd, num_floors, floor_h, base_z, mats)

    # ── Roof
    top_z = base_z + num_floors * floor_h
    generate_roof(bw, bd, top_z, roof_style, mats)

    # ── Pool
    if has_pool:
        generate_pool(bw, bd, pool_cfg, base_z, mats)

    # ── Garage
    if has_garage:
        generate_garage(bw, bd, garage_cfg, base_z, mats)

    # ── Trees
    generate_trees(bw, bd, mats)

    # ── Lighting + Camera
    setup_lighting(bw, bd, total_h)
    setup_camera(bw, bd, total_h)

    # ── Export
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    export_glb(output_path)

    # ── Write metadata for FastAPI to read
    meta_path = output_path.replace(".glb", "_meta.json")
    meta = {
        "status": "success",
        "output_path": output_path,
        "building_type": building_type,
        "floors": num_floors,
        "width": bw,
        "depth": bd,
        "features": {
            "pool": has_pool,
            "garage": has_garage,
            "balconies": has_balconies,
            "staircase": True,
            "windows": True,
        }
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[BlenderWorker] Metadata → {meta_path}")
    print("[BlenderWorker] DONE")


if __name__ == "__main__":
    main()
