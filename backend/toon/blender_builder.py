"""
Enhanced Blender Builder for multi-floor buildings
Handles style-based materials, proper floor stacking, roofs, doors, windows
"""
import bpy
import json
import math
import sys
import os

def build_enhanced_house(scene_data_path: str, output_path: str):
    """Build an enhanced multi-floor house model in Blender"""
    
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Load scene data
    with open(scene_data_path, 'r') as f:
        scene_data = json.load(f)
    
    style = scene_data.get('style', 'modern')
    prompt = scene_data.get('prompt', '').lower()
    render_quality = scene_data.get('render_quality', 'medium')
    house = scene_data.get('house', scene_data)
    features = set(house.get('features', []) or [])
    if 'pool' in prompt or 'swimming' in prompt:
        features.add('pool')
    if 'garage' in features or 'garage' in prompt:
        features.add('garage')
    if 'apartment' in prompt:
        features.add('apartment')
        style = style if style in {'contemporary', 'modern'} else 'contemporary'
    
    # Style materials
    style_materials = {
        'modern': {
            'walls': (0.92, 0.90, 0.88, 1.0),
            'roof': (0.20, 0.20, 0.22, 1.0),
            'floor': (0.85, 0.80, 0.75, 1.0),
            'foundation': (0.60, 0.55, 0.50, 1.0),
        },
        'villa': {
            'walls': (0.95, 0.88, 0.75, 1.0),
            'roof': (0.75, 0.35, 0.20, 1.0),
            'floor': (0.80, 0.65, 0.50, 1.0),
            'foundation': (0.65, 0.60, 0.55, 1.0),
        },
        'colonial': {
            'walls': (0.95, 0.95, 0.92, 1.0),
            'roof': (0.35, 0.35, 0.40, 1.0),
            'floor': (0.70, 0.55, 0.40, 1.0),
            'foundation': (0.70, 0.68, 0.65, 1.0),
        },
        'contemporary': {
            'walls': (0.88, 0.90, 0.94, 1.0),
            'roof': (0.22, 0.24, 0.28, 1.0),
            'floor': (0.78, 0.80, 0.84, 1.0),
            'foundation': (0.45, 0.47, 0.50, 1.0),
        },
        'apartment': {
            'walls': (0.82, 0.86, 0.92, 1.0),
            'roof': (0.18, 0.20, 0.24, 1.0),
            'floor': (0.72, 0.76, 0.82, 1.0),
            'foundation': (0.42, 0.44, 0.48, 1.0),
        },
        'craftsman': {
            'walls': (0.85, 0.75, 0.60, 1.0),
            'roof': (0.40, 0.35, 0.25, 1.0),
            'floor': (0.65, 0.50, 0.35, 1.0),
            'foundation': (0.60, 0.58, 0.55, 1.0),
        },
    }
    
    if 'apartment' in features:
        style = 'apartment'
    colors = style_materials.get(style, style_materials['modern'])
    
    # Create materials
    def create_material(name, color, roughness=0.5, alpha=1.0, metallic=0.0):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color
            bsdf.inputs['Roughness'].default_value = roughness
            if 'Metallic' in bsdf.inputs:
                bsdf.inputs['Metallic'].default_value = metallic
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.45
            if alpha < 1.0:
                bsdf.inputs['Alpha'].default_value = alpha
                mat.blend_method = 'BLEND'
        return mat

    def cube(name, location, scale, material, bevel=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.scale = scale
        obj.name = name
        obj.data.materials.append(material)
        if bevel > 0:
            modifier = obj.modifiers.new(name='Soft_Edges', type='BEVEL')
            modifier.width = bevel
            modifier.segments = 2
            try:
                modifier.affect = 'EDGES'
            except Exception:
                pass
            obj.modifiers.new(name='Weighted_Normals', type='WEIGHTED_NORMAL')
        return obj
    
    wall_mat = create_material('Wall_Mat', colors['walls'], 0.6)
    roof_mat = create_material('Roof_Mat', colors['roof'], 0.7)
    floor_mat = create_material('Floor_Mat', colors['floor'], 0.4)
    foundation_mat = create_material('Foundation_Mat', colors['foundation'], 0.8)
    door_mat = create_material('Door_Mat', (0.35, 0.22, 0.12, 1.0), 0.5)
    glass_mat = create_material('Glass_Mat', (0.60, 0.75, 0.85, 0.3), 0.1, 0.3)
    glass_mat.blend_method = 'BLEND'
    trim_mat = create_material('Architectural_Trim', (0.12, 0.16, 0.20, 1.0), 0.42)
    metal_mat = create_material('Dark_Metal', (0.04, 0.05, 0.06, 1.0), 0.35, 1.0, 0.25)
    water_mat = create_material('Pool_Water', (0.12, 0.55, 0.85, 0.45), 0.05, 0.45)
    water_mat.blend_method = 'BLEND'
    
    # Room colors
    room_colors = {
        'living_room': (0.90, 0.88, 0.82, 1.0),
        'bedroom': (0.88, 0.85, 0.90, 1.0),
        'bathroom': (0.85, 0.92, 0.90, 1.0),
        'kitchen': (0.92, 0.90, 0.82, 1.0),
        'dining_room': (0.88, 0.90, 0.85, 1.0),
        'hallway': (0.90, 0.90, 0.88, 1.0),
        'garage': (0.70, 0.70, 0.70, 1.0),
        'study': (0.88, 0.85, 0.80, 1.0),
        'room': (0.85, 0.85, 0.85, 1.0),
    }
    
    FLOOR_HEIGHT = 3.5
    WALL_THICKNESS = 0.25
    WINDOW_HEIGHT = 1.2
    WINDOW_WIDTH = 1.5
    
    # Get rooms and floors
    rooms = house.get('rooms', [])
    
    if not rooms:
        rooms = [{'x': 0, 'y': 0, 'width': 12, 'depth': 10, 'floor': 0, 'type': 'room'}]

    def room_plan_x(room):
        return float(room.get('x', room.get('plan', {}).get('x', room.get('position', {}).get('x', 0))))

    def room_plan_y(room):
        return float(room.get('y', room.get('plan', {}).get('y', room.get('position', {}).get('z', 0))))

    def room_width(room):
        return float(room.get('width', 4))

    def room_depth(room):
        return float(room.get('depth', 4))

    def room_floor(room):
        return int(room.get('floor', 0))

    def room_type(room):
        return room.get('type', 'room')
    
    # Calculate building bounds
    min_x = min(room_plan_x(r) - room_width(r)/2 for r in rooms)
    max_x = max(room_plan_x(r) + room_width(r)/2 for r in rooms)
    min_y = min(room_plan_y(r) - room_depth(r)/2 for r in rooms)
    max_y = max(room_plan_y(r) + room_depth(r)/2 for r in rooms)
    
    building_width = max_x - min_x + 1
    building_depth = max_y - min_y + 1
    
    # Get number of floors
    floor_nums = set(room_floor(r) for r in rooms)
    requested_floors = int(house.get('num_floors', scene_data.get('num_floors', 1)) or 1)
    num_floors = max(max(floor_nums) + 1 if floor_nums else 1, requested_floors)
    num_floors = max(num_floors, 1)
    
    print(f"Building: {num_floors} floors, {building_width}m x {building_depth}m")
    
    # === BUILD FLOORS ===
    for floor_idx in range(num_floors):
        z_base = floor_idx * FLOOR_HEIGHT
        
        # Floor slab
        cube(f'Floor_{floor_idx}_Slab', (0, 0, z_base + 0.1), (building_width, building_depth, 0.2), floor_mat, 0.03)
        
        # Interior ceiling (except top floor)
        if floor_idx < num_floors - 1:
            cube(f'Floor_{floor_idx}_Ceiling', (0, 0, z_base + FLOOR_HEIGHT - 0.1), (building_width, building_depth, 0.2), floor_mat, 0.03)
    
    # === BUILD EXTERIOR WALLS ===
    for floor_idx in range(num_floors):
        z_center = floor_idx * FLOOR_HEIGHT + FLOOR_HEIGHT / 2
        half_w = building_width / 2
        half_d = building_depth / 2
        
        # Front wall (with door cutout simulation - just solid for now)
        cube(f'Wall_F{floor_idx}_Front', (0, half_d - WALL_THICKNESS/2, z_center), (building_width, WALL_THICKNESS, FLOOR_HEIGHT), wall_mat, 0.015)
        
        # Back wall
        cube(f'Wall_F{floor_idx}_Back', (0, -half_d + WALL_THICKNESS/2, z_center), (building_width, WALL_THICKNESS, FLOOR_HEIGHT), wall_mat, 0.015)
        
        # Left wall
        cube(f'Wall_F{floor_idx}_Left', (-half_w + WALL_THICKNESS/2, 0, z_center), (WALL_THICKNESS, building_depth, FLOOR_HEIGHT), wall_mat, 0.015)
        
        # Right wall
        cube(f'Wall_F{floor_idx}_Right', (half_w - WALL_THICKNESS/2, 0, z_center), (WALL_THICKNESS, building_depth, FLOOR_HEIGHT), wall_mat, 0.015)

        # Horizontal floor belt and subtle vertical fins make tall buildings read as designed facades.
        cube(f'Facade_Belt_F{floor_idx}_Front', (0, half_d + 0.03, z_center + FLOOR_HEIGHT / 2 - 0.18), (building_width + 0.35, 0.08, 0.16), trim_mat, 0.02)
        cube(f'Facade_Belt_F{floor_idx}_Back', (0, -half_d - 0.03, z_center + FLOOR_HEIGHT / 2 - 0.18), (building_width + 0.35, 0.08, 0.16), trim_mat, 0.02)
        if num_floors < 4:
            for x in (-half_w * 0.55, 0, half_w * 0.55):
                cube(f'Facade_Fin_F{floor_idx}_{x:.1f}', (x, half_d + 0.06, z_center), (0.08, 0.12, FLOOR_HEIGHT * 0.35), trim_mat, 0.015)

        # Window band per floor (recessed glass + frame) — reads as real facade
        band_y = half_d + 0.04
        for wx in (-half_w * 0.32, 0, half_w * 0.32):
            cube(f'Win_Glass_F{floor_idx}_{wx:.1f}', (wx, band_y, z_center), (1.35, 0.04, 1.25), glass_mat, 0.02)
            cube(f'Win_Frame_F{floor_idx}_{wx:.1f}', (wx, band_y + 0.02, z_center), (1.45, 0.03, 1.35), trim_mat, 0.01)
    
    # === BUILD ROOF (always flat caps — avoids broken gable planes) ===
    roof_z = num_floors * FLOOR_HEIGHT
    roof_overhang = 0.5
    rw = building_width + roof_overhang
    rd = building_depth + roof_overhang
    cube('Roof_Flat', (0, 0, roof_z + 0.25), (rw, rd, 0.35), roof_mat, 0.05)
    cube('Roof_Parapet', (0, 0, roof_z + 0.55), (rw + 0.15, rd + 0.15, 0.12), trim_mat, 0.03)

    if num_floors >= 3 or 'apartment' in features or style in {'contemporary', 'modern', 'apartment'}:
        facade_width = building_width * 0.42
        for floor_idx in range(num_floors):
            z = floor_idx * FLOOR_HEIGHT + FLOOR_HEIGHT * 0.56
            cube(f'Curtain_Glass_F{floor_idx}', (0, half_d + 0.075, z), (facade_width, 0.035, FLOOR_HEIGHT * 0.64), glass_mat, 0.025)
            cube(f'Curtain_Mullion_Left_F{floor_idx}', (-facade_width / 2, half_d + 0.11, z), (0.05, 0.08, FLOOR_HEIGHT * 0.68), metal_mat, 0.01)
            cube(f'Curtain_Mullion_Right_F{floor_idx}', (facade_width / 2, half_d + 0.11, z), (0.05, 0.08, FLOOR_HEIGHT * 0.68), metal_mat, 0.01)
            for mullion_x in (-facade_width * 0.25, 0, facade_width * 0.25):
                cube(f'Curtain_Mullion_F{floor_idx}_{mullion_x:.1f}', (mullion_x, half_d + 0.11, z), (0.035, 0.08, FLOOR_HEIGHT * 0.62), metal_mat, 0.01)
    
    # === ADD FOUNDATION ===
    cube('Foundation', (0, 0, -0.4), (half_w + 0.3, half_d + 0.3, 0.6), foundation_mat, 0.04)
    
    # === ADD DOORS AND WINDOWS ===
    # Front door
    cube('Front_Door', (0, half_d + 0.05, 1.2), (1.0, 0.08, 2.4), door_mat, 0.03)
    
    # Door frame
    cube('Door_Frame', (0, half_d + 0.08, 1.2), (1.2, 0.05, 2.6), wall_mat, 0.025)
    cube('Entry_Canopy', (0, half_d + 0.55, 2.75), (1.9, 0.9, 0.16), trim_mat, 0.04)
    
    # Windows - front and sides
    window_positions = []
    for floor_idx in range(num_floors):
        z = floor_idx * FLOOR_HEIGHT + FLOOR_HEIGHT * 0.58
        window_positions.extend([
            (half_w * 0.42, half_d + 0.01, z),
            (-half_w * 0.42, half_d + 0.01, z),
            (0, half_d + 0.01, z),
            (-half_w - 0.01, half_d * 0.30, z),
            (-half_w - 0.01, -half_d * 0.30, z),
            (half_w + 0.01, half_d * 0.30, z),
            (half_w + 0.01, -half_d * 0.30, z),
        ])
    
    for i, (wx, wy, wz) in enumerate(window_positions):
        # Window frame
        cube(f'Window_{i}_Frame', (wx, wy, wz), (0.05, 0.05, WINDOW_HEIGHT), trim_mat, 0.01)
        
        # Window glass
        # Adjust scale based on orientation
        if abs(wy) > 0.01:  # Front/back
            scale = (WINDOW_WIDTH/2, 0.02, WINDOW_HEIGHT/2)
        else:  # Left/right
            scale = (0.02, WINDOW_WIDTH/2, WINDOW_HEIGHT/2)
        cube(f'Window_{i}_Glass', (wx, wy, wz), scale, glass_mat, 0.015)

    # Balconies are especially useful visual markers on multi-floor villas/apartments.
    if 'balcony' in prompt or num_floors > 1:
        for floor_idx in range(1, num_floors):
            z = floor_idx * FLOOR_HEIGHT + 1.05
            cube(f'Balcony_F{floor_idx}_Slab', (0, half_d + 0.95, z), (building_width * 0.32, 1.35, 0.18), floor_mat, 0.04)
            cube(f'Balcony_F{floor_idx}_Rail_Front', (0, half_d + 1.62, z + 0.55), (building_width * 0.34, 0.06, 0.55), glass_mat, 0.02)
            cube(f'Balcony_F{floor_idx}_Rail_Left', (-building_width * 0.17, half_d + 0.95, z + 0.55), (0.06, 1.28, 0.55), metal_mat, 0.015)
            cube(f'Balcony_F{floor_idx}_Rail_Right', (building_width * 0.17, half_d + 0.95, z + 0.55), (0.06, 1.28, 0.55), metal_mat, 0.015)

    if 'garage' in features or 'garage' in prompt:
        gx = -half_w - 2.25
        gy = half_d - 1.2
        cube('Garage_Volume', (gx, gy, 1.45), (3.2, 3.4, 2.9), wall_mat, 0.035)
        cube('Garage_Door', (gx, gy + 1.72, 1.15), (2.35, 0.08, 1.9), metal_mat, 0.025)

    if 'pool' in features or 'pool' in prompt:
        px = half_w + 3.8
        py = -half_d + 1.2
        cube('Pool_Basin', (px, py, -0.05), (4.8, 2.8, 0.18), foundation_mat, 0.05)
        cube('Pool_Water', (px, py, 0.08), (4.35, 2.35, 0.05), water_mat, 0.04)

    if 'garden' in prompt or 'villa' in prompt:
        lawn_mat = create_material('Landscape_Lawn', (0.18, 0.45, 0.22, 1.0), 0.9)
        stone_mat = create_material('Stone_Path', (0.42, 0.42, 0.40, 1.0), 0.85)
        cube('Landscape_Podium', (0, 0, -0.12), (building_width + 8, building_depth + 8, 0.08), lawn_mat, 0.02)
        cube('Entry_Walkway', (0, half_d + 3.0, 0.02), (2.2, 5.2, 0.04), stone_mat, 0.02)
    
    # === ADD INTERIOR ROOM FLOORS ===
    for room in rooms:
        room_x = room_plan_x(room)
        room_y = room_plan_y(room)
        room_w = room_width(room)
        room_d = room_depth(room)
        current_floor = room_floor(room)
        current_room_type = room_type(room)
        
        z = current_floor * FLOOR_HEIGHT + 0.15
        
        room_color = room_colors.get(current_room_type, room_colors['room'])
        room_mat = create_material(f"Room_{current_room_type}_{current_floor}", room_color, 0.3)
        
        cube(f"Interior_{current_room_type}_{current_floor}", (room_x, room_y, z), (max(room_w/2 - 0.2, 0.2), max(room_d/2 - 0.2, 0.2), 0.05), room_mat, 0.015)
    
    # Apply bevel/weighted normals so GLB looks less blocky
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        for mod in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception:
                pass
        obj.select_set(False)

    # === LIGHTING / WORLD ===
    world = bpy.context.scene.world
    if world and world.use_nodes:
        bg = world.node_tree.nodes.get('Background')
        if bg:
            bg.inputs[0].default_value = (0.55, 0.65, 0.82, 1.0)
            bg.inputs[1].default_value = 0.85

    bpy.ops.object.light_add(type='SUN', location=(20, -18, max(num_floors * FLOOR_HEIGHT + 8, 18)))
    sun = bpy.context.object
    sun.data.energy = 4.5
    sun.data.angle = 0.12
    sun.rotation_euler = (0.85, 0.15, 0.65)
    sun.name = 'Sun'

    bpy.ops.object.light_add(type='AREA', location=(-12, 10, num_floors * FLOOR_HEIGHT * 0.6))
    area = bpy.context.object
    area.data.energy = 450
    area.data.size = max(building_width, building_depth) * 1.2
    area.name = 'Fill_Light'
    
    # === CAMERA ===
    camera_dist = max(building_width, building_depth) * 2
    bpy.ops.object.camera_add(location=(camera_dist * 0.6, -camera_dist * 0.5, camera_dist * 0.4))
    camera = bpy.context.object
    camera.rotation_euler = (1.1, 0, 0.8)
    camera.name = 'Main_Camera'
    bpy.context.scene.camera = camera
    
    # === RENDER SETTINGS ===
    render_presets = {
        "preview": {"engine": "BLENDER_EEVEE", "samples": 32, "resolution_x": 1280, "resolution_y": 720},
        "medium": {"engine": "BLENDER_EEVEE", "samples": 128, "resolution_x": 1920, "resolution_y": 1080},
        "cinematic": {"engine": "CYCLES", "samples": 512, "resolution_x": 3840, "resolution_y": 2160},
        "production": {"engine": "CYCLES", "samples": 2048, "resolution_x": 3840, "resolution_y": 2160},
    }
    preset = render_presets.get(render_quality, render_presets["medium"])
    bpy.context.scene.render.engine = preset["engine"]
    bpy.context.scene.render.resolution_x = preset["resolution_x"]
    bpy.context.scene.render.resolution_y = preset["resolution_y"]
    if preset["engine"] == "CYCLES":
        bpy.context.scene.cycles.samples = preset["samples"]
        bpy.context.scene.cycles.use_denoising = True
    
    # === EXPORT ===
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=False,
        export_apply=True
    )
    
    print(f"Exported: {output_path}")
    print(f"Building: {num_floors} floors, {len(rooms)} rooms")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: blender --background --python blender_builder.py -- <scene.json> <output.glb>")
        sys.exit(1)
    
    scene_path = sys.argv[-2]
    output_path = sys.argv[-1]
    
    print(f"Building house from: {scene_path}")
    print(f"Output to: {output_path}")
    
    build_enhanced_house(scene_path, output_path)
