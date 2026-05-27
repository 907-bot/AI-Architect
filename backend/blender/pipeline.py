from __future__ import annotations

from pathlib import Path

from backend.blender.exporters import export_glb
from backend.blender.generators import create_roof, create_room
from backend.toon.models import SceneGraph


def generate_house(scene: SceneGraph, output_path: str | Path) -> str:
    try:
        import bpy
    except ImportError as exc:
        raise RuntimeError("Blender generation must run inside Blender with bpy available") from exc

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    for room in scene.house.rooms:
        create_room(room)
    if scene.house.rooms:
        create_roof(scene)
        _add_context(bpy, scene)

    return export_glb(output_path)


def _add_context(bpy, scene: SceneGraph) -> None:
    rooms = scene.house.rooms
    min_x = min(room.x - room.width / 2 for room in rooms)
    max_x = max(room.x + room.width / 2 for room in rooms)
    min_z = min(room.z - room.depth / 2 for room in rooms)
    max_z = max(room.z + room.depth / 2 for room in rooms)
    center_x = (min_x + max_x) / 2
    center_z = (min_z + max_z) / 2
    width = max_x - min_x
    depth = max_z - min_z

    bpy.ops.object.light_add(type="SUN", location=(0, 10, 0))
    sun = bpy.context.object
    sun.name = "architectural_sun"
    sun.data.energy = 2.5
    sun.rotation_euler = (0.85, 0.0, 0.55)

    bpy.ops.object.light_add(type="AREA", location=(center_x, 7.0, center_z))
    area = bpy.context.object
    area.name = "soft_interior_fill"
    area.data.energy = 450
    area.data.size = max(width, depth)

    bpy.ops.object.camera_add(location=(center_x + width * 0.95, 7.0, center_z + depth * 1.15), rotation=(1.1, 0.0, 2.38))
    bpy.context.scene.camera = bpy.context.object
