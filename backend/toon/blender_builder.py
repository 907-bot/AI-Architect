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
    house = scene_data.get('house', scene_data)
    
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
            'walls': (0.95, 0.95, 0.95, 1.0),
            'roof': (0.15, 0.15, 0.18, 1.0),
            'floor': (0.90, 0.88, 0.85, 1.0),
            'foundation': (0.50, 0.50, 0.55, 1.0),
        },
        'craftsman': {
            'walls': (0.85, 0.75, 0.60, 1.0),
            'roof': (0.40, 0.35, 0.25, 1.0),
            'floor': (0.65, 0.50, 0.35, 1.0),
            'foundation': (0.60, 0.58, 0.55, 1.0),
        },
    }
    
    colors = style_materials.get(style, style_materials['modern'])
    
    # Create materials
    def create_material(name, color, roughness=0.5, alpha=1.0):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color
            bsdf.inputs['Roughness'].default_value = roughness
            if alpha < 1.0:
                bsdf.inputs['Alpha'].default_value = alpha
        return mat
    
    wall_mat = create_material('Wall_Mat', colors['walls'], 0.6)
    roof_mat = create_material('Roof_Mat', colors['roof'], 0.7)
    floor_mat = create_material('Floor_Mat', colors['floor'], 0.4)
    foundation_mat = create_material('Foundation_Mat', colors['foundation'], 0.8)
    door_mat = create_material('Door_Mat', (0.35, 0.22, 0.12, 1.0), 0.5)
    glass_mat = create_material('Glass_Mat', (0.60, 0.75, 0.85, 0.3), 0.1, 0.3)
    glass_mat.blend_method = 'BLEND'
    
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
    
    # Calculate building bounds
    min_x = min(r.get('x', 0) - r.get('width', 10)/2 for r in rooms)
    max_x = max(r.get('x', 0) + r.get('width', 10)/2 for r in rooms)
    min_y = min(r.get('y', 0) - r.get('depth', 8)/2 for r in rooms)
    max_y = max(r.get('y', 0) + r.get('depth', 8)/2 for r in rooms)
    
    building_width = max_x - min_x + 1
    building_depth = max_y - min_y + 1
    
    # Get number of floors
    floor_nums = set(r.get('floor', 0) for r in rooms)
    num_floors = max(floor_nums) + 1 if floor_nums else 1
    num_floors = max(num_floors, 1)
    
    print(f"Building: {num_floors} floors, {building_width}m x {building_depth}m")
    
    # === BUILD FLOORS ===
    for floor_idx in range(num_floors):
        z_base = floor_idx * FLOOR_HEIGHT
        
        # Floor slab
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z_base + 0.1))
        obj = bpy.context.object
        obj.scale = (building_width, building_depth, 0.2)
        obj.name = f'Floor_{floor_idx}_Slab'
        obj.data.materials.append(floor_mat)
        
        # Interior ceiling (except top floor)
        if floor_idx < num_floors - 1:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z_base + FLOOR_HEIGHT - 0.1))
            obj = bpy.context.object
            obj.scale = (building_width, building_depth, 0.2)
            obj.name = f'Floor_{floor_idx}_Ceiling'
            obj.data.materials.append(floor_mat)
    
    # === BUILD EXTERIOR WALLS ===
    for floor_idx in range(num_floors):
        z_center = floor_idx * FLOOR_HEIGHT + FLOOR_HEIGHT / 2
        half_w = building_width / 2
        half_d = building_depth / 2
        
        # Front wall (with door cutout simulation - just solid for now)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, half_d - WALL_THICKNESS/2, z_center))
        obj = bpy.context.object
        obj.scale = (building_width, WALL_THICKNESS, FLOOR_HEIGHT)
        obj.name = f'Wall_F{floor_idx}_Front'
        obj.data.materials.append(wall_mat)
        
        # Back wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -half_d + WALL_THICKNESS/2, z_center))
        obj = bpy.context.object
        obj.scale = (building_width, WALL_THICKNESS, FLOOR_HEIGHT)
        obj.name = f'Wall_F{floor_idx}_Back'
        obj.data.materials.append(wall_mat)
        
        # Left wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(-half_w + WALL_THICKNESS/2, 0, z_center))
        obj = bpy.context.object
        obj.scale = (WALL_THICKNESS, building_depth, FLOOR_HEIGHT)
        obj.name = f'Wall_F{floor_idx}_Left'
        obj.data.materials.append(wall_mat)
        
        # Right wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(half_w - WALL_THICKNESS/2, 0, z_center))
        obj = bpy.context.object
        obj.scale = (WALL_THICKNESS, building_depth, FLOOR_HEIGHT)
        obj.name = f'Wall_F{floor_idx}_Right'
        obj.data.materials.append(wall_mat)
    
    # === BUILD ROOF ===
    roof_z = num_floors * FLOOR_HEIGHT
    roof_overhang = 0.4
    
    if style == 'modern':
        # Flat roof for modern style
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, roof_z + 0.3))
        obj = bpy.context.object
        obj.scale = (building_width/2 + roof_overhang, building_depth/2 + roof_overhang, 0.4)
        obj.name = 'Roof_Flat'
        obj.data.materials.append(roof_mat)
        
        # Roof edge trim
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, roof_z + 0.6))
        obj = bpy.context.object
        obj.scale = (building_width/2 + roof_overhang + 0.1, building_depth/2 + roof_overhang + 0.1, 0.1)
        obj.name = 'Roof_Edge'
        obj.data.materials.append(roof_mat)
    else:
        # Pitched roof
        roof_height = 2.5
        roof_overhang = 0.8
        
        # Main roof planes (gable style)
        verts = [
            (-half_w - roof_overhang, -half_d - roof_overhang, roof_z),
            (0, -half_d - roof_overhang, roof_z + roof_height),
            (-half_w - roof_overhang, half_d + roof_overhang, roof_z),
            (0, half_d + roof_overhang, roof_z + roof_height),
        ]
        
        mesh = bpy.data.meshes.new('Roof_Mesh')
        mesh.from_pydata(verts, [], [(0, 1, 2)])
        mesh.update()
        
        obj = bpy.data.objects.new('Roof_Left', mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(roof_mat)
        
        # Right roof plane
        verts2 = [
            (0, -half_d - roof_overhang, roof_z + roof_height),
            (half_w + roof_overhang, -half_d - roof_overhang, roof_z),
            (0, half_d + roof_overhang, roof_z + roof_height),
            (half_w + roof_overhang, half_d + roof_overhang, roof_z),
        ]
        
        mesh2 = bpy.data.meshes.new('Roof_Mesh2')
        mesh2.from_pydata(verts2, [], [(0, 1, 2)])
        mesh2.update()
        
        obj2 = bpy.data.objects.new('Roof_Right', mesh2)
        bpy.context.collection.objects.link(obj2)
        obj2.data.materials.append(roof_mat)
    
    # === ADD FOUNDATION ===
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.4))
    obj = bpy.context.object
    obj.scale = (half_w + 0.3, half_d + 0.3, 0.6)
    obj.name = 'Foundation'
    obj.data.materials.append(foundation_mat)
    
    # === ADD DOORS AND WINDOWS ===
    # Front door
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, half_d + 0.05, 1.2))
    obj = bpy.context.object
    obj.scale = (1.0, 0.08, 2.4)
    obj.name = 'Front_Door'
    obj.data.materials.append(door_mat)
    
    # Door frame
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, half_d + 0.08, 1.2))
    obj = bpy.context.object
    obj.scale = (1.2, 0.05, 2.6)
    obj.name = 'Door_Frame'
    obj.data.materials.append(wall_mat)
    
    # Windows - front and sides
    window_positions = [
        (half_w * 0.4, half_d + 0.01, FLOOR_HEIGHT * 0.6),   # Front right
        (-half_w * 0.4, half_d + 0.01, FLOOR_HEIGHT * 0.6),  # Front left
        (-half_w - 0.01, 0, FLOOR_HEIGHT * 0.6),              # Left side
        (half_w + 0.01, 0, FLOOR_HEIGHT * 0.6),             # Right side
        (-half_w - 0.01, -half_d * 0.3, FLOOR_HEIGHT * 0.6), # Back left
        (half_w + 0.01, -half_d * 0.3, FLOOR_HEIGHT * 0.6),  # Back right
    ]
    
    for i, (wx, wy, wz) in enumerate(window_positions):
        # Window frame
        bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, wy, wz))
        obj = bpy.context.object
        obj.scale = (0.05, 0.05, WINDOW_HEIGHT)
        obj.name = f'Window_{i}_Frame'
        obj.data.materials.append(wall_mat)
        
        # Window glass
        bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, wy, wz))
        obj = bpy.context.object
        # Adjust scale based on orientation
        if abs(wy) > 0.01:  # Front/back
            obj.scale = (WINDOW_WIDTH/2, 0.02, WINDOW_HEIGHT/2)
        else:  # Left/right
            obj.scale = (0.02, WINDOW_WIDTH/2, WINDOW_HEIGHT/2)
        obj.name = f'Window_{i}_Glass'
        obj.data.materials.append(glass_mat)
    
    # === ADD INTERIOR ROOM FLOORS ===
    for room in rooms:
        room_x = room.get('x', 0)
        room_y = room.get('y', 0)
        room_w = room.get('width', 4)
        room_d = room.get('depth', 4)
        room_floor = room.get('floor', 0)
        room_type = room.get('type', 'room')
        
        z = room_floor * FLOOR_HEIGHT + 0.15
        
        room_color = room_colors.get(room_type, room_colors['room'])
        room_mat = create_material(f"Room_{room_type}_{room_floor}", room_color, 0.3)
        
        bpy.ops.mesh.primitive_cube_add(size=1, location=(room_x, room_y, z))
        obj = bpy.context.object
        obj.scale = (room_w/2 - 0.2, room_d/2 - 0.2, 0.05)
        obj.name = f"Interior_{room_type}_{room_floor}"
        obj.data.materials.append(room_mat)
    
    # === LIGHTING ===
    # Sun light
    bpy.ops.object.light_add(type='SUN', location=(15, -15, 25))
    sun = bpy.context.object
    sun.data.energy = 3.0
    sun.rotation_euler = (0.5, 0.3, 0.8)
    sun.name = 'Sun'
    
    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 15))
    area = bpy.context.object
    area.data.energy = 300
    area.data.size = 10
    area.name = 'Fill_Light'
    
    # === CAMERA ===
    camera_dist = max(building_width, building_depth) * 2
    bpy.ops.object.camera_add(location=(camera_dist * 0.6, -camera_dist * 0.5, camera_dist * 0.4))
    camera = bpy.context.object
    camera.rotation_euler = (1.1, 0, 0.8)
    camera.name = 'Main_Camera'
    bpy.context.scene.camera = camera
    
    # === RENDER SETTINGS ===
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 128
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    
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
