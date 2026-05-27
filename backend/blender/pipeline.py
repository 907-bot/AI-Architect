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

    return export_glb(output_path)
