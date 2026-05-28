"""
AI Architect — Enhanced Blender Scene Builder
Generates realistic 3D house models inspired by real architectural designs
Supports multiple house styles with proper materials and color grading
"""
import bpy
import math
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class HouseStyle:
    """House style configuration with materials and colors"""
    name: str
    wall_color: tuple  # RGB 0-1
    roof_color: tuple
    floor_color: tuple
    trim_color: tuple
    window_frame_color: tuple
    door_color: tuple
    foundation_color: tuple
    lighting_warmth: float  # Kelvin temperature
    ambient_strength: float


# House style presets inspired by real architectural designs
HOUSE_STYLES = {
    "modern": HouseStyle(
        name="Modern Minimalist",
        wall_color=(0.95, 0.95, 0.93),  # Off-white concrete
        roof_color=(0.15, 0.15, 0.18),  # Dark gray flat roof
        floor_color=(0.75, 0.7, 0.65),  # Light concrete
        trim_color=(0.9, 0.88, 0.85),  # White trim
        window_frame_color=(0.2, 0.2, 0.22),  # Black frames
        door_color=(0.25, 0.22, 0.2),  # Dark wood
        foundation_color=(0.6, 0.58, 0.55),  # Gray foundation
        lighting_warmth=5500,
        ambient_strength=0.35,
    ),
    "villa": HouseStyle(
        name="Mediterranean Villa",
        wall_color=(0.92, 0.88, 0.78),  # Warm cream/tan
        roof_color=(0.65, 0.35, 0.25),  # Terracotta tiles
        floor_color=(0.7, 0.55, 0.4),  # Terracotta floor
        trim_color=(1.0, 1.0, 1.0),  # White trim
        window_frame_color=(0.85, 0.82, 0.75),  # Cream frames
        door_color=(0.5, 0.25, 0.15),  # Dark wood door
        foundation_color=(0.5, 0.45, 0.4),  # Stone foundation
        lighting_warmth=4000,
        ambient_strength=0.4,
    ),
    "colonial": HouseStyle(
        name="Colonial American",
        wall_color=(0.88, 0.85, 0.8),  # Soft beige
        roof_color=(0.25, 0.2, 0.15),  # Dark brown shingles
        floor_color=(0.55, 0.4, 0.25),  # Hardwood floor
        trim_color=(1.0, 1.0, 1.0),  # White trim
        window_frame_color=(1.0, 1.0, 1.0),  # White frames
        door_color=(0.4, 0.15, 0.1),  # Red painted door
        foundation_color=(0.65, 0.62, 0.58),  # Stone
        lighting_warmth=4500,
        ambient_strength=0.35,
    ),
    "contemporary": HouseStyle(
        name="Contemporary Modern",
        wall_color=(0.92, 0.9, 0.88),  # Light gray
        roof_color=(0.1, 0.1, 0.12),  # Near black
        floor_color=(0.85, 0.82, 0.78),  # Light stone
        trim_color=(0.15, 0.15, 0.18),  # Black trim
        window_frame_color=(0.15, 0.15, 0.18),  # Black frames
        door_color=(0.15, 0.15, 0.18),  # Black door
        foundation_color=(0.5, 0.5, 0.48),  # Dark gray
        lighting_warmth=5000,
        ambient_strength=0.3,
    ),
    " Craftsman": HouseStyle(
        name="Craftsman Bungalow",
        wall_color=(0.82, 0.75, 0.65),  # Warm brown
        roof_color=(0.3, 0.25, 0.2),  # Dark brown
        floor_color=(0.5, 0.35, 0.2),  # Dark hardwood
        trim_color=(0.9, 0.85, 0.75),  # Natural wood
        window_frame_color=(0.85, 0.78, 0.68),  # Wood frames
        door_color=(0.35, 0.2, 0.12),  # Dark wood
        foundation_color=(0.55, 0.5, 0.45),  # Stone
        lighting_warmth=4200,
        ambient_strength=0.4,
    ),
}


class EnhancedBlenderSceneBuilder:
    """Enhanced scene builder with real house designs and color grading"""
    
    def __init__(self, scene_graph: Dict[str, Any]):
        self.sg = scene_graph
        self.style_name = scene_graph.get("style", "modern")
        self.style = HOUSE_STYLES.get(self.style_name, HOUSE_STYLES["modern"])
        self.created_objects = []
        
    def clear_scene(self):
        """Clear all objects from the scene"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Clear orphan data blocks
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)
        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)
    
    def create_material(self, name: str, color: tuple, roughness: float = 0.5, 
                        metallic: float = 0.0, specular: float = 0.5) -> bpy.types.Material:
        """Create a PBR material with given properties"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
            bsdf.inputs["Specular IOR Level"].default_value = specular
        
        return mat
    
    def create_material_with_texture(self, name: str, color: tuple, 
                                     texture_type: str = "noise") -> bpy.types.Material:
        """Create material with procedural texture"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        
        # Remove default output
        output = nodes.get("Material Output")
        
        # Create texture nodes
        if texture_type == "noise":
            noise = nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 5.0
            noise.inputs["Detail"].default_value = 8.0
            
            mix = nodes.new("ShaderNodeMixRGB")
            mix.blend_type = "OVERLAY"
            mix.inputs["Fac"].default_value = 0.15
            
            # Connect texture to color variation
            mat.node_tree.links.new(noise.outputs["Fac"], mix.inputs["Factor"])
            mix.inputs[1].default_value = (*color, 1.0)
            mix.inputs[2].default_value = (*tuple(max(0, c - 0.05) for c in color), 1.0)
            
            if bsdf:
                mat.node_tree.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
                bsdf.inputs["Roughness"].default_value = 0.6
        
        return mat
    
    def build_foundation(self, width: float, depth: float, x: float, z: float):
        """Build house foundation"""
        thickness = 0.3
        height = 0.4
        
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, height/2))
        foundation = bpy.context.object
        foundation.name = "Foundation"
        foundation.scale = (width + 0.4, depth + 0.4, height)
        
        # Apply material
        foundation_mat = self.create_material("Foundation_Mat", self.style.foundation_color, roughness=0.9)
        foundation.data.materials.append(foundation_mat)
        
        # Add subdivisions for better look
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.subdivide(number_cuts=2)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.created_objects.append(foundation)
        return foundation
    
    def build_walls(self, width: float, depth: float, height: float, 
                    x: float, z: float, y_offset: float = 0) -> List[bpy.types.Object]:
        """Build walls with proper thickness and openings"""
        walls = []
        wall_thickness = 0.2
        
        wall_mat = self.create_material_with_texture("Walls_Mat", self.style.wall_color, "noise")
        trim_mat = self.create_material("Trim_Mat", self.style.trim_color, roughness=0.3)
        
        # Front wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z + depth/2, y_offset + height/2))
        front = bpy.context.object
        front.name = "Wall_Front"
        front.scale = (width, wall_thickness, height)
        front.data.materials.append(wall_mat)
        walls.append(front)
        
        # Back wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z - depth/2, y_offset + height/2))
        back = bpy.context.object
        back.name = "Wall_Back"
        back.scale = (width, wall_thickness, height)
        back.data.materials.append(wall_mat)
        walls.append(back)
        
        # Left wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x - width/2, z, y_offset + height/2))
        left = bpy.context.object
        left.name = "Wall_Left"
        left.scale = (wall_thickness, depth, height)
        left.data.materials.append(wall_mat)
        walls.append(left)
        
        # Right wall
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, z, y_offset + height/2))
        right = bpy.context.object
        right.name = "Wall_Right"
        right.scale = (wall_thickness, depth, height)
        right.data.materials.append(wall_mat)
        walls.append(right)
        
        self.created_objects.extend(walls)
        return walls
    
    def build_roof(self, width: float, depth: float, x: float, z: float, 
                   roof_height: float = 0.6, roof_style: str = "flat") -> bpy.types.Object:
        """Build roof based on style"""
        roof_mat = self.create_material("Roof_Mat", self.style.roof_color, roughness=0.7)
        
        if roof_style in ["gable", "pitched"]:
            # Gabled roof
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, roof_height))
            roof = bpy.context.object
            roof.name = "Roof_Gable"
            roof.scale = (width + 0.5, depth + 0.5, roof_height)
            
            # Apply shader for gable effect
            self._apply_gable_shader(roof)
            
        elif roof_style == "hip":
            # Hip roof - simplified as pyramid
            bpy.ops.mesh.primitive_cone_add(vertices=4, size=1,
                location=(x, z, roof_height * 0.5))
            roof = bpy.context.object
            roof.name = "Roof_Hip"
            roof.scale = (width * 0.7, depth * 0.7, roof_height * 1.5)
            
        else:
            # Flat roof
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, roof_height))
            roof = bpy.context.object
            roof.name = "Roof_Flat"
            roof.scale = (width + 0.4, depth + 0.4, 0.15)
        
        roof.data.materials.append(roof_mat)
        self.created_objects.append(roof)
        return roof
    
    def _apply_gable_shader(self, roof):
        """Apply shader to create gable roof effect"""
        mat = bpy.data.materials.new(name="Roof_Gable_Mat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*self.style.roof_color, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.6
            
        roof.data.materials.append(mat)
    
    def build_floor(self, width: float, depth: float, x: float, z: float, y: float = 0):
        """Build floor plane"""
        floor_mat = self.create_material("Floor_Mat", self.style.floor_color, roughness=0.8)
        
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, z, y + 0.01))
        floor = bpy.context.object
        floor.name = "Floor"
        floor.scale = (width, depth, 1)
        
        # Add subdivisions
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.subdivide(number_cuts=4)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        floor.data.materials.append(floor_mat)
        self.created_objects.append(floor)
        return floor
    
    def build_windows(self, width: float, depth: float, height: float,
                      x: float, z: float, y_offset: float = 0,
                      window_positions: List[dict] = None):
        """Build windows with frames and glass"""
        if window_positions is None:
            window_positions = [
                {"side": "front", "count": 2, "height_offset": 0.6},
                {"side": "back", "count": 1, "height_offset": 0.6},
            ]
        
        glass_mat = self.create_material("Glass_Mat", (0.6, 0.75, 0.85), 
                                         roughness=0.05, metallic=0.0, specular=1.0)
        frame_mat = self.create_material("WindowFrame_Mat", self.style.window_frame_color, roughness=0.3)
        
        for pos in window_positions:
            side = pos.get("side", "front")
            count = pos.get("count", 1)
            height_off = pos.get("height_offset", 0.6)
            
            window_width = 1.2
            window_height = 1.4
            
            if side == "front":
                z_pos = z + depth/2 + 0.1
                for i in range(count):
                    x_offset = (i - (count-1)/2) * (width / (count + 1))
                    self._create_window(x + x_offset, z_pos, y_offset + height_off * height,
                                       window_width, window_height, glass_mat, frame_mat)
            
            elif side == "back":
                z_pos = z - depth/2 - 0.1
                self._create_window(x, z_pos, y_offset + height_off * height,
                                   window_width, window_height, glass_mat, frame_mat)
    
    def _create_window(self, x: float, z: float, y: float, 
                       width: float, height: float,
                       glass_mat, frame_mat):
        """Create a single window with frame"""
        # Glass pane
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, z, y))
        window = bpy.context.object
        window.name = "Window_Glass"
        window.scale = (width, 0.02, height)
        window.data.materials.append(glass_mat)
        
        # Frame
        frame_thickness = 0.05
        # Top frame
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, y + height/2))
        top = bpy.context.object
        top.name = "Window_Frame_Top"
        top.scale = (width + frame_thickness, frame_thickness, frame_thickness)
        top.data.materials.append(frame_mat)
        
        # Bottom frame
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, y - height/2))
        bottom = bpy.context.object
        bottom.name = "Window_Frame_Bottom"
        bottom.scale = (width + frame_thickness, frame_thickness, frame_thickness)
        bottom.data.materials.append(frame_mat)
        
        self.created_objects.extend([window, top, bottom])
    
    def build_door(self, x: float, z: float, y_offset: float = 0, height: float = 2.2):
        """Build entrance door"""
        door_mat = self.create_material("Door_Mat", self.style.door_color, roughness=0.5)
        frame_mat = self.create_material("DoorFrame_Mat", self.style.trim_color, roughness=0.3)
        
        door_width = 0.9
        door_height = height
        
        # Door panel
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, y_offset + door_height/2))
        door = bpy.context.object
        door.name = "Door"
        door.scale = (door_width, 0.08, door_height)
        door.data.materials.append(door_mat)
        
        # Door frame
        frame_thickness = 0.08
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, z, y_offset + door_height/2))
        frame = bpy.context.object
        frame.name = "Door_Frame"
        frame.scale = (door_width + frame_thickness, frame_thickness, door_height + frame_thickness)
        frame.data.materials.append(frame_mat)
        
        self.created_objects.extend([door, frame])
    
    def build_terrain(self, width: float, depth: float):
        """Build surrounding terrain"""
        terrain_mat = self.create_material("Terrain_Mat", (0.35, 0.55, 0.3), roughness=0.95)
        
        # Main ground
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.02))
        ground = bpy.context.object
        ground.name = "Terrain"
        ground.scale = (width * 3, depth * 3, 1)
        
        # Add some noise to terrain
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.subdivide(number_cuts=8)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        ground.data.materials.append(terrain_mat)
        self.created_objects.append(ground)
        
        return ground
    
    def setup_lighting(self, style: str = "interior"):
        """Setup scene lighting with color grading"""
        # Sun light
        sun_rotation = (math.radians(45), 0, math.radians(-30))
        bpy.ops.object.light_add(type='SUN', location=(20, -15, 25))
        sun = bpy.context.object
        sun.name = "Sun"
        sun.rotation_euler = sun_rotation
        sun.data.energy = 2.5
        sun.data.color = (1.0, 0.95, 0.9)  # Warm sunlight
        
        # Ambient light
        bpy.ops.object.light_add(type='AREA', location=(0, 0, 8))
        ambient = bpy.context.object
        ambient.name = "Ambient"
        ambient.data.energy = self.style.ambient_strength * 500
        ambient.data.color = (0.95, 0.95, 1.0)  # Cool ambient
        ambient.scale = (30, 30, 1)
        
        # Fill lights for softer shadows
        bpy.ops.object.light_add(type='AREA', location=(-10, 10, 6))
        fill = bpy.context.object
        fill.name = "Fill_Light"
        fill.data.energy = 200
        fill.data.color = (0.9, 0.92, 1.0)  # Cool fill
        
        self.created_objects.extend([sun, ambient, fill])
    
    def apply_color_grading(self):
        """Apply color grading through compositor"""
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree
        
        # Clear existing nodes
        for node in tree.nodes:
            tree.nodes.remove(node)
        
        # Create compositor nodes
        nodes = tree.nodes
        links = tree.links
        
        # Render layer
        render_layer = nodes.new('CompositorNodeRLayers')
        render_layer.location = (0, 0)
        
        # Exposure node
        exposure = nodes.new('CompositorNodeExposure')
        exposure.location = (300, 0)
        exposure.inputs["Exposure"].default_value = 0.0  # Neutral
        exposure.inputs["Offset"].default_value = 0.02  # Slight lift
        
        # Color balance
        color_balance = nodes.new('CompositorNodeColorBalance')
        color_balance.location = (500, 0)
        
        # Lift/Gamma/Gain controls for cinematic look
        lift = color_balance.inputs["Lift"]
        gamma = color_balance.inputs["Gamma"]
        gain = color_balance.inputs["Gain"]
        
        # Cinematic color grade - lifted blacks, warm highlights
        lift.default_value = (0.95, 0.95, 0.98, 1)  # Slight blue lift
        gamma.default_value = (1.02, 1.0, 0.98, 1)  # Slight warm gamma
        gain.default_value = (1.0, 0.98, 0.95, 1)  # Warm highlights
        
        # Contrast
        contrast = nodes.new('CompositorNodeContrast')
        contrast.location = (700, 0)
        contrast.inputs["Contrast"].default_value = 1.1
        contrast.inputs["Clip"].default_value = (0.0, 1.0)
        
        # Vignette
        vignette = nodes.new('CompositorNodeVignette')
        vignette.location = (900, 0)
        vignette.inputs["Scale"].default_value = 0.8
        vignette.inputs["Smoothness"].default_value = 0.5
        
        # Output
        composite = nodes.new('CompositorNodeComposite')
        composite.location = (1100, 0)
        
        # Connect nodes
        links.new(render_layer.outputs["Image"], exposure.inputs["Image"])
        links.new(exposure.outputs["Image"], color_balance.inputs["Image"])
        links.new(color_balance.outputs["Image"], contrast.inputs["Image"])
        links.new(contrast.outputs["Image"], vignette.inputs["Image"])
        links.new(vignette.outputs["Image"], composite.inputs["Image"])
    
    def setup_camera(self, view: str = "perspective", target: tuple = (0, 0, 1.5)):
        """Setup camera for rendering"""
        if view == "perspective":
            # 3-point perspective view
            cam_pos = (15, -12, 8)
            bpy.ops.object.camera_add(location=cam_pos)
            camera = bpy.context.object
            camera.name = "Camera_Perspective"
            
        elif view == "top":
            # Top orthographic view
            cam_pos = (0, 0, 25)
            bpy.ops.object.camera_add(location=cam_pos)
            camera = bpy.context.object
            camera.name = "Camera_Top"
            camera.rotation_euler = (math.radians(90), 0, 0)
            # Set orthographic
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = 20
            
        elif view == "front":
            # Front elevation
            cam_pos = (0, -15, 5)
            bpy.ops.object.camera_add(location=cam_pos)
            camera = bpy.context.object
            camera.name = "Camera_Front"
            camera.rotation_euler = (math.radians(90), 0, 0)
            
        elif view == "drone":
            # Drone flythrough path
            cam_pos = (20, -20, 10)
            bpy.ops.object.camera_add(location=cam_pos)
            camera = bpy.context.object
            camera.name = "Camera_Drone"
        
        else:
            # Default perspective
            cam_pos = (12, -10, 7)
            bpy.ops.object.camera_add(location=cam_pos)
            camera = bpy.context.object
            camera.name = "Camera_Default"
        
        # Point camera at target
        direction = (
            target[0] - camera.location[0],
            target[1] - camera.location[1],
            target[2] - camera.location[2]
        )
        
        # Calculate rotation
        import mathutils
        rot = mathutils.Vector(direction).to_euler()
        camera.rotation_euler = (math.radians(90) + rot.x, 0, math.radians(180) + rot.z)
        
        # Set as active camera
        bpy.context.scene.camera = camera
        
        # Configure render settings
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 128
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        self.created_objects.append(camera)
        return camera
    
    def build_from_scene_graph(self) -> Dict[str, Any]:
        """Build complete scene from scene graph"""
        self.clear_scene()
        
        # Get house configuration
        house = self.sg.get("house", self.sg)
        rooms = house.get("rooms", [])
        
        # Calculate overall dimensions
        if rooms:
            all_x = [r.get("x", 0) for r in rooms] + [r.get("x", 0) + r.get("width", 5) for r in rooms]
            all_z = [r.get("y", 0) for r in rooms] + [r.get("y", 0) + r.get("depth", 5) for r in rooms]
            width = max(all_x) - min(all_x) if len(all_x) > 1 else 15
            depth = max(all_z) - min(all_z) if len(all_z) > 1 else 12
            center_x = (max(all_x) + min(all_x)) / 2 if len(all_x) > 1 else 0
            center_z = (max(all_z) + min(all_z)) / 2 if len(all_z) > 1 else 0
        else:
            width, depth = 15, 12
            center_x, center_z = 0, 0
        
        height = 3.0  # Default room height
        roof_style = house.get("roof", {}).get("kind", "flat")
        
        # Build terrain
        self.build_terrain(width, depth)
        
        # Build foundation
        self.build_foundation(width, depth, center_x, center_z)
        
        # Build walls
        self.build_walls(width, depth, height, center_x, center_z, y_offset=0.4)
        
        # Build floor
        self.build_floor(width, depth, center_x, center_z, y=0.4)
        
        # Build roof
        self.build_roof(width, depth, center_x, center_z, roof_height=height + 0.6, roof_style=roof_style)
        
        # Build windows
        self.build_windows(width, depth, height, center_x, center_z, y_offset=0.4)
        
        # Build entrance door
        self.build_door(center_x, center_z + depth/2 + 0.1, y_offset=0.4, height=2.2)
        
        # Setup lighting
        self.setup_lighting()
        
        # Apply color grading
        self.apply_color_grading()
        
        # Setup camera
        self.setup_camera("perspective", target=(center_x, center_z, height/2 + 0.4))
        
        return {
            "status": "success",
            "style": self.style_name,
            "rooms_built": len(rooms),
            "objects_created": len(self.created_objects),
            "render_ready": True,
        }


def build_scene_from_toon(toon_path: str, output_path: str, style: str = "modern") -> str:
    """Main function to build scene from TOON file"""
    # Parse TOON file
    with open(toon_path, 'r') as f:
        toon_data = json.load(f)
    
    # Create builder
    builder = EnhancedBlenderSceneBuilder(toon_data)
    
    # Build scene
    result = builder.build_from_scene_graph()
    
    # Render
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    
    return output_path


if __name__ == "__main__":
    import sys
    
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    toon_path = None
    output_path = "exports/house.glb"
    style = "modern"
    
    for i, arg in enumerate(args):
        if arg == "--toon" and i + 1 < len(args):
            toon_path = args[i + 1]
        elif arg == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
        elif arg == "--style" and i + 1 < len(args):
            style = args[i + 1]
    
    if toon_path:
        build_scene_from_toon(toon_path, output_path, style)
        print(f"Scene built and saved to: {output_path}")