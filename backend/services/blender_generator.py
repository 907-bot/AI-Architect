#!/usr/bin/env python3
"""
Blender Geometry Generator
Generates enterprise-grade 3D building models using Blender's Python API

Usage:
    blender --background --python generate_building.py -- specimen.json house.glb
"""
import bpy
import bmesh
import json
import sys
import os
from math import radians, pi

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Clear all materials
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# ============================================================
# MATERIAL DEFINITIONS
# ============================================================
def create_material(name, color, roughness=0.5, metallic=0.0, transmission=0.0):
    """Create PBR material"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Set PBR properties
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if transmission > 0:
        bsdf.inputs['Transmission Weight'].default_value = transmission
    
    # Link
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Position
    output.location = (300, 0)
    bsdf.location = (0, 0)
    
    return mat

# Create materials
MATERIALS = {
    "concrete": create_material("concrete", (0.6, 0.6, 0.6), 0.85, 0.0),
    "plaster_white": create_material("plaster_white", (0.96, 0.96, 0.94), 0.9, 0.0),
    "plaster_beige": create_material("plaster_beige", (0.91, 0.86, 0.78), 0.85, 0.0),
    "brick_red": create_material("brick_red", (0.55, 0.23, 0.23), 0.85, 0.0),
    "brick_dark": create_material("brick_dark", (0.4, 0.26, 0.13), 0.8, 0.0),
    "glass_clear": create_material("glass_clear", (0.53, 0.8, 1.0), 0.05, 0.1, 0.9),
    "glass_tinted": create_material("glass_tinted", (0.25, 0.31, 0.38), 0.15, 0.2, 0.6),
    "frame_black": create_material("frame_black", (0.1, 0.1, 0.1), 0.3, 0.7),
    "frame_white": create_material("frame_white", (0.9, 0.9, 0.9), 0.35, 0.5),
    "wood_oak": create_material("wood_oak", (0.55, 0.35, 0.17), 0.6, 0.0),
    "roof_tiles_red": create_material("roof_tiles_red", (0.7, 0.13, 0.13), 0.65, 0.0),
    "roof_slate": create_material("roof_slate", (0.29, 0.29, 0.29), 0.6, 0.0),
    "roof_metal": create_material("roof_metal", (0.38, 0.44, 0.5), 0.4, 0.5),
    "metal_dark": create_material("metal_dark", (0.15, 0.15, 0.15), 0.25, 0.8),
    "metal_grey": create_material("metal_grey", (0.44, 0.44, 0.44), 0.3, 0.7),
    "grass": create_material("grass", (0.29, 0.49, 0.14), 0.95, 0.0),
    "patio_stone": create_material("patio_stone", (0.56, 0.5, 0.44), 0.8, 0.0),
}

# Collection for our building
building_collection = bpy.data.collections.new("Building")
bpy.context.scene.collection.children.link(building_collection)

# ============================================================
# GEOMETRY FUNCTIONS
# ============================================================
def create_box(name, size, location, material_name=None):
    """Create a Box primitive"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    
    # Apply scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Add bevel for realism
    bpy.ops.object.modifier_add(type='BEVEL')
    bevel = obj.modifiers[-1]
    bevel.width = 0.02
    bevel.segments = 3
    
    # Assign material if provided
    if material_name and material_name in MATERIALS:
        obj.data.materials.append(MATERIALS[material_name])
    else:
        obj.data.materials.append(MATERIALS["concrete"])
    
    # Move to collection
    if building_collection and obj.name not in building_collection.objects:
        building_collection.objects.link(obj)
    
    return obj

def create_wall_with_openings(spec):
    """Create walls with window/door cutouts"""
    width = spec.get("width", 10)
    depth = spec.get("depth", 8)
    height = spec.get("height", 3)
    
    # Create main wall
    wall = create_box("wall_main", (width, 0.15, height), (0, depth/2, height/2), "plaster_white")
    
    # Window cuts
    windows = spec.get("windows", [])
    for i, win in enumerate(windows):
        wx, wy, wz = win.get("position", [0, 0, 1.5])
        ww, wh = win.get("size", [1.2, 1.5])
        
        # Create window hole using boolean
        bpy.ops.mesh.primitive_cube_add(size=1)
        window_cut = bpy.context.active_object
        window_cut.name = f"window_cut_{i}"
        window_cut.scale = (ww, 0.2, wh)
        window_cut.location = (wx, wy, wz)
        bpy.ops.object.transform_apply(scale=True)
        
        # Boolean modifier
        mod = wall.modifiers.new(name=f"WindowBool_{i}", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = window_cut
        
        # Hide cutter
        bpy.context.view_mode = "OBJECT"
        window_cut.hide_viewport = True
        window_cut.hide_render = True
    
    return wall

def create_window_frame(spec):
    """Create detailed window with frame and glass"""
    x, y, z = spec.get("position", [0, 0, 1.5])
    width = spec.get("width", 1.2)
    height = spec.get("height", 1.5)
    
    objects = []
    
    # Glass pane
    glass = create_box(f"window_glass", (width - 0.1, 0.02, height - 0.1), (x, y, z), "glass_clear")
    objects.append(glass)
    
    # Frame - 4 sides
    frame_thickness = 0.05
    # Top
    objects.append(create_box(f"frame_top", (width, frame_thickness, frame_thickness), 
                      (x, y, z + height/2 - frame_thickness/2), "frame_black"))
    # Bottom
    objects.append(create_box(f"frame_bottom", (width, frame_thickness, frame_thickness), 
                      (x, y, z - height/2 + frame_thickness/2), "frame_black"))
    # Left
    objects.append(create_box(f"frame_left", (frame_thickness, frame_thickness, height), 
                      (x - width/2 + frame_thickness/2, y, z), "frame_black"))
    # Right
    objects.append(create_box(f"frame_right", (frame_thickness, frame_thickness, height), 
                      (x + width/2 - frame_thickness/2, y, z), "frame_black"))
    
    return objects

def create_door(spec):
    """Create door with frame"""
    x, y, z = spec.get("position", [0, 0, 1.1])
    width = spec.get("width", 1.0)
    height = spec.get("height", 2.2)
    
    # Door panel
    door = create_box("door_panel", (width - 0.1, 0.05, height - 0.1), (x, y, z), "wood_oak")
    
    # Door frame
    frame = create_box("door_frame", (width + 0.1, 0.05, height + 0.1), (x, y, z), "frame_black")
    
    # Handle
    handle = create_box("door_handle", (0.08, 0.04, 0.15), 
                     (x + width/3, y + 0.04, z), "metal_grey")
    
    return [door, frame, handle]

def create_roof(spec):
    """Create roof - supports flat, gable, hip styles"""
    width = spec.get("width", 10)
    depth = spec.get("depth", 8)
    style = spec.get("style", "gable")
    pitch = spec.get("pitch", 30)  # degrees
    
    objects = []
    
    if style == "flat":
        # Flat roof with slight edge
        objects.append(create_box("roof", (width * 0.95, depth * 0.95, 0.1), 
                            (0, 0, spec.get("height", 3) + 0.05), "roof_metal"))
        # Parapet
        objects.append(create_box("parapet", (width * 0.96, 0.08, 0.15),
                           (0, depth/2, spec.get("height", 3) + 0.1), "plaster_white"))
    
    elif style == "gable":
        # Two sloping planes
        angle = radians(pitch)
        slope_height = (width/2) * abs(1 / (1 / (angle * 2)))
        
        # Front slope
        objects.append(create_box("roof_front", (width * 1.02, depth * 0.15, slope_height),
                             (0, depth/2, spec.get("height", 3) + slope_height/2), "roof_tiles_red"))
        # Back slope
        objects.append(create_box("roof_back", (width * 1.02, depth * 0.15, slope_height),
                            (0, -depth/2, spec.get("height", 3) + slope_height/2), "roof_tiles_red"))
        # Ridge
        ridge_height = slope_height * 1.1
        objects.append(create_box("ridge", (width * 1.02, 0.1, 0.1),
                           (0, 0, spec.get("height", 3) + ridge_height), "roof_slate"))
    
    elif style == "hip":
        # Hip roof - pyramid shape
        hip_height = min(width, depth) * 0.3
        objects.append(create_box("roof_hip", (width * 0.95, depth * 0.95, hip_height),
                        (0, 0, spec.get("height", 3) + hip_height/2), "roof_slate"))
    
    return objects

def create_foundation(spec):
    """Create foundation slab"""
    width = spec.get("width", 10)
    depth = spec.get("depth", 8)
    thickness = spec.get("thickness", 0.3)
    
    objects = []
    
    # Main slab
    objects.append(create_box("foundation", (width + 0.5, depth + 0.5, thickness),
                          (0, 0, -thickness/2), "concrete"))
    
    # Stepping
    objects.append(create_box("step", (1.0, depth * 0.6, thickness * 0.3),
                         (0, depth/2 + 0.3, thickness * 0.15), "patio_stone"))
    
    return objects

def create_garage(spec):
    """Create garage structure"""
    x_offset = spec.get("x_offset", -6)
    width = spec.get("width", 4)
    depth = spec.get("depth", 5)
    
    objects = []
    
    # Garage body
    objects.append(create_box("garage_body", (width, depth, 2.5),
                       (x_offset, 0, 1.25), "plaster_white"))
    
    # Garage door
    objects.append(create_box("garage_door", (width * 0.8, 0.1, 2.2),
                       (x_offset, depth/2 - 0.05, 1.1), "metal_dark"))
    
    # Roof
    objects.append(create_box("garage_roof", (width + 0.2, depth + 0.2, 0.1),
                        (x_offset, 0, 2.55), "roof_metal"))
    
    return objects

def create_pool(spec):
    """Create swimming pool"""
    width = spec.get("width", 4)
    depth = spec.get("depth", 8)
    depth_water = spec.get("water_depth", 1.5)
    
    objects = []
    
    # Pool basin
    objects.append(create_box("pool_basin", (width, depth, depth_water),
                   (3, -2, -depth_water/2), "patio_stone"))
    
    # Water (blue, transparent)
    objects.append(create_box("pool_water", (width - 0.2, depth - 0.2, depth_water - 0.1),
                   (3, -2, 0.05), "glass_tinted"))
    
    # Coping
    objects.append(create_box("pool_coping", (width + 0.3, 0.2, 0.08),
                         (3, -2 + depth/2 + 0.1, 0.04), "patio_stone"))
    
    return objects

def create_landscape(spec):
    """Create landscape features"""
    width = spec.get("width", 12)
    depth = spec.get("depth", 15)
    
    objects = []
    
    # Ground/grass
    objects.append(create_box("ground", (width + 2, depth + 2, 0.1),
                          (0, 0, -0.15), "grass"))
    
    # Path
    objects.append(create_box("path", (0.8, 1.5, 0.05),
                        (0, depth/2 - 0.5, -0.05), "patio_stone"))
    
    # Shrubs (simplified spheres)
    for sx in [-3, 3]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(sx, depth/2 - 1, 0.1))
        shrub = bpy.context.active_object
        shrub.name = f"shrub_{sx}"
        shrub.data.materials.append(MATERIALS["grass"])
        objects.append(shrub)
    
    return objects

def create_chimney(spec):
    """Create chimney"""
    x, y = spec.get("position", [2, 1])
    width = spec.get("width", 0.5)
    height = spec.get("height", 1.5)
    roof_y = spec.get("roof_height", 3)
    
    objects = []
    
    # Chimney body
    objects.append(create_box("chimney", (width, width, height),
                       (x, y, roof_y + height/2), "brick_red"))
    
    # Cap
    cap_size = width * 1.3
    objects.append(create_box("chimney_cap", (cap_size, cap_size, 0.05),
                        (x, y, roof_y + height + 0.025), "roof_slate"))
    
    return objects

# ============================================================
# MAIN BUILDING GENERATOR
# ============================================================
def generate_building(spec):
    """Generate complete building from specification"""
    all_objects = []
    
    # Foundation
    if spec.get("foundation", True):
        all_objects.extend(create_foundation({
            "width": spec.get("width", 10),
            "depth": spec.get("depth", 8),
            "thickness": 0.3
        }))
    
    # Walls + windows
    walls = spec.get("walls", {})
    wall_spec = {
        "width": spec.get("width", 10),
        "depth": spec.get("depth", 8),
        "height": spec.get("floor_height", 3),
        "windows": walls.get("windows", [])
    }
    create_wall_with_openings(wall_spec)
    
    # Doors
    if spec.get("door"):
        all_objects.extend(create_door(spec["door"]))
    
    # Windows
    for win in walls.get("windows", []):
        all_objects.extend(create_window_frame(win))
    
    # Roof
    all_objects.extend(create_roof({
        "width": spec.get("width", 10),
        "depth": spec.get("depth", 8),
        "style": spec.get("roof_style", "gable"),
        "pitch": spec.get("roof_pitch", 30),
        "height": spec.get("floor_height", 3)
    }))
    
    # Chimney
    if spec.get("chimney", True):
        all_objects.extend(create_chimney({
            "position": [2, 1],
            "roof_height": spec.get("floor_height", 3)
        }))
    
    # Garage
    if spec.get("garage", False):
        all_objects.extend(create_garage({
            "x_offset": -spec.get("width", 10) * 0.5 - 2
        }))
    
    # Pool
    if spec.get("pool", False):
        all_objects.extend(create_pool({}))
    
    # Landscape
    if spec.get("landscape", True):
        all_objects.extend(create_landscape({
            "width": spec.get("width", 10),
            "depth": spec.get("depth", 8)
        }))
    
    # Join objects
    bpy.ops.object.select_all(action='SELECT')
    if all_objects:
        bpy.context.selected_objects = all_objects
        try:
            bpy.ops.object.join()
        except:
            pass
    
    return all_objects

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    # Get arguments
    args = sys.argv
    args = args[args.index("--") + 1:] if "--" in args else args[1:]
    
    if len(args) >= 2:
        spec_file = args[0]
        output_file = args[1]
        
        # Load spec
        with open(spec_file, 'r') as f:
            spec = json.load(f)
        
        # Generate
        generate_building(spec)
        
        # Export
        bpy.ops.export_scene.gltf(
            filepath=output_file,
            export_format='GLB',
            use_selection=False,
            export_apply=True
        )
        
        print(f"Exported to {output_file}")
    else:
        print("Usage: blender --background --python generate_building.py -- spec.json output.glb")