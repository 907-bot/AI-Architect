"""
Scene Builder — Converts Canonical Scene Graph into Blender scene.
AI NEVER touches Blender internals directly.
The AI fills the scene graph; this module deterministically builds geometry.
"""
from typing import Dict, Any, List, Optional
import json
import structlog
import math

log = structlog.get_logger()


class BlenderSceneBuilder:
    """
    Builds a Blender scene from a canonical scene graph.
    Uses Blender's Python API (bpy) when running inside Blender.
    Uses deterministic math when called externally for validation.
    """

    def __init__(self, scene_graph: Dict[str, Any]):
        self.sg = scene_graph
        self._bpy = None
        self._try_import_bpy()

    def _try_import_bpy(self):
        try:
            import bpy
            self._bpy = bpy
            log.info("blender_python_available")
        except ImportError:
            log.info("blender_python_not_available_using_validation_mode")

    def _has_bpy(self) -> bool:
        return self._bpy is not None

    # =====================================================
    # MATERIALS
    # =====================================================

    def create_materials(self) -> Dict[str, Any]:
        """Create Blender materials from scene graph materials."""
        mats = {}
        for m in self.sg.get("materials", []):
            mid = m.get("id", "default")
            name = m.get("name", "Material")
            color = m.get("color_rgb", "#CCCCCC")
            roughness = m.get("roughness", 0.5)
            metallic = m.get("metallic", 0.0)

            if self._has_bpy():
                bpy = self._bpy
                mat = bpy.data.materials.new(name=name)
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    r, g, b = self._hex_to_rgb(color)
                    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
                    bsdf.inputs["Roughness"].default_value = roughness
                    bsdf.inputs["Metallic"].default_value = metallic
                mats[mid] = mat
            else:
                mats[mid] = {"id": mid, "name": name, "color": color, "roughness": roughness, "metallic": metallic}
        return mats

    # =====================================================
    # ROOMS
    # =====================================================

    def create_room(self, room: Dict[str, Any], materials: Dict[str, Any]):
        """Create a room box with walls, floor, ceiling."""
        name = room.get("name", "Room")
        w = room.get("width", 5.0)
        d = room.get("depth", 5.0)
        h = room.get("height", 3.0)
        pos = room.get("position", {"x": 0, "y": 0, "z": 0})
        mat_id = room.get("material_id", "")

        if self._has_bpy():
            bpy = self._bpy
            # Floor
            bpy.ops.mesh.primitive_plane_add(size=1, location=(pos["x"], pos["z"], pos["y"]))
            floor = bpy.context.object
            floor.name = f"{name}_floor"
            floor.scale = (w, d, 1)
            if mat_id in materials:
                floor.data.materials.append(materials[mat_id])

            # Walls
            wall_height = h
            half_w = w / 2
            half_d = d / 2

            wall_positions = [
                (pos["x"], pos["z"] - half_d, pos["y"] + wall_height / 2, w, 0.1),  # front
                (pos["x"], pos["z"] + half_d, pos["y"] + wall_height / 2, w, 0.1),  # back
                (pos["x"] - half_w, pos["z"], pos["y"] + wall_height / 2, 0.1, d),  # left
                (pos["x"] + half_w, pos["z"], pos["y"] + wall_height / 2, 0.1, d),  # right
            ]
            for i, (wx, wz, wy, sw, sd) in enumerate(wall_positions):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, wz, wy))
                wall = bpy.context.object
                wall.name = f"{name}_wall_{i}"
                wall.scale = (sw, sd, wall_height / 2)
                if mat_id in materials:
                    wall.data.materials.append(materials[mat_id])

            # Ceiling
            bpy.ops.mesh.primitive_plane_add(size=1, location=(pos["x"], pos["z"], pos["y"] + h))
            ceiling = bpy.context.object
            ceiling.name = f"{name}_ceiling"
            ceiling.scale = (w, d, 1)
        else:
            log.info("room_geometry_computed", name=name, width=w, depth=d, height=h)

    def create_all_rooms(self):
        """Create all rooms in the scene."""
        mats = self.create_materials()
        for room in self.sg.get("rooms", []):
            self.create_room(room, mats)
        log.info("all_rooms_created", count=len(self.sg.get("rooms", [])))

    # =====================================================
    # FURNITURE
    # =====================================================

    def place_furniture(self, furniture: Dict[str, Any], materials: Dict[str, Any]):
        """Place a furniture item in the scene."""
        ftype = furniture.get("furniture_type", "table")
        pos = furniture.get("position", {"x": 0, "y": 0, "z": 0})
        scale = furniture.get("scale", {"x": 1, "y": 1, "z": 1})
        rot = furniture.get("rotation", {"pitch": 0, "yaw": 0, "roll": 0})

        if self._has_bpy():
            bpy = self._bpy
            bpy.ops.mesh.primitive_cube_add(size=1, location=(pos["x"], pos["z"], pos["y"]))
            obj = bpy.context.object
            obj.name = f"furniture_{ftype}"
            obj.scale = (scale["x"], scale["y"], scale["z"])
            obj.rotation_euler = (rot["pitch"], rot["roll"], rot["yaw"])

    def place_all_furniture(self):
        """Place all furniture items in the scene."""
        mats = self.create_materials()
        for room in self.sg.get("rooms", []):
            for furn in room.get("furniture", []):
                self.place_furniture(furn, mats)
        log.info("all_furniture_placed")

    # =====================================================
    # LIGHTING
    # =====================================================

    def setup_lighting(self):
        """Set up scene lighting from scene graph data."""
        lights = []
        for room in self.sg.get("rooms", []):
            for light in room.get("lights", []):
                lights.append(light)

        if self._has_bpy():
            bpy = self._bpy
            for light in lights:
                ltype = light.get("light_type", "point")
                pos = light.get("position", {"x": 0, "y": 0, "z": 0})
                color = light.get("color_rgb", "#FFFFFF")
                intensity = light.get("intensity", 1.0)

                bpy_type = {"point": "POINT", "directional": "SUN", "spot": "SPOT", "ambient": "POINT"}
                bpy.ops.object.light_add(type=bpy_type.get(ltype, "POINT"), location=(pos["x"], pos["z"], pos["y"]))
                light_obj = bpy.context.object
                light_obj.name = f"light_{ltype}"
                light_obj.data.energy = intensity * 1000
                r, g, b = self._hex_to_rgb(color)
                light_obj.data.color = (r, g, b)

        log.info("lighting_setup", light_count=len(lights))

    # =====================================================
    # CAMERA
    # =====================================================

    def setup_cameras(self):
        """Set up camera views for rendering."""
        if not self._has_bpy():
            return
        bpy = self._bpy
        cameras = [
            {"name": "Front_View", "loc": (0, -15, 3), "rot": (0, 0, 0)},
            {"name": "Top_View", "loc": (0, 0, 20), "rot": (math.radians(90), 0, 0)},
            {"name": "Perspective", "loc": (12, -12, 6), "rot": (math.radians(60), 0, math.radians(45))},
        ]
        for cam in cameras:
            bpy.ops.object.camera_add(location=cam["loc"])
            camera = bpy.context.object
            camera.name = cam["name"]
            camera.rotation_euler = cam["rot"]

    # =====================================================
    # FULL SCENE BUILD
    # =====================================================

    def build_full_scene(self) -> Dict[str, Any]:
        """Build the complete Blender scene from the scene graph."""
        log.info("building_full_scene")

        if self._has_bpy():
            bpy = self._bpy
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete()

        mats = self.create_materials()
        self.create_all_rooms()
        self.place_all_furniture()
        self.setup_lighting()
        self.setup_cameras()

        # Apply design style parameters
        design_system = self.sg.get("design_system", {})
        if design_system and self._has_bpy():
            bpy = self._bpy
            bpy.context.scene.render.engine = "CYCLES"
            bpy.context.scene.cycles.samples = 128
            bpy.context.scene.render.resolution_x = 1920
            bpy.context.scene.render.resolution_y = 1080

        result = {
            "status": "success",
            "room_count": len(self.sg.get("rooms", [])),
            "material_count": len(self.sg.get("materials", [])),
            "furniture_count": sum(
                len(r.get("furniture", [])) for r in self.sg.get("rooms", [])
            ),
        }
        log.info("scene_build_complete", **result)
        return result

    # =====================================================
    # UTILITIES
    # =====================================================

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    @staticmethod
    def validate_scene_graph(sg: Dict[str, Any]) -> List[str]:
        """Validate a scene graph for rendering readiness."""
        errors = []
        if not sg.get("rooms"):
            errors.append("No rooms defined")
        for i, room in enumerate(sg.get("rooms", [])):
            if not room.get("width") or not room.get("depth"):
                errors.append(f"Room {i}: missing dimensions")
            if not room.get("position"):
                errors.append(f"Room {i}: missing position")
        return errors
