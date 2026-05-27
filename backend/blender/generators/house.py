from __future__ import annotations

from typing import Any

from backend.toon.models import Room, SceneGraph


def create_room(scene_or_room: SceneGraph | Room, room: Room | None = None) -> list[Any]:
    bpy = _bpy()
    target = room or scene_or_room
    if not isinstance(target, Room):
        raise TypeError("create_room expects a Room or SceneGraph plus Room")

    objects = []
    objects.append(_cube(bpy, f"{target.name}_floor", (target.x, 0.03, target.z), (target.width, 0.06, target.depth)))
    objects.append(create_wall(target, "front"))
    objects.append(create_wall(target, "back"))
    objects.append(create_wall(target, "left"))
    objects.append(create_wall(target, "right"))
    return objects


def create_wall(room: Room, side: str):
    bpy = _bpy()
    thickness = 0.18
    if side == "front":
        position = (room.x, room.height / 2, room.z + room.depth / 2)
        scale = (room.width, room.height, thickness)
    elif side == "back":
        position = (room.x, room.height / 2, room.z - room.depth / 2)
        scale = (room.width, room.height, thickness)
    elif side == "left":
        position = (room.x - room.width / 2, room.height / 2, room.z)
        scale = (thickness, room.height, room.depth)
    elif side == "right":
        position = (room.x + room.width / 2, room.height / 2, room.z)
        scale = (thickness, room.height, room.depth)
    else:
        raise ValueError(f"Unknown wall side {side!r}")
    return _cube(bpy, f"{room.name}_wall_{side}", position, scale)


def create_roof(scene: SceneGraph):
    bpy = _bpy()
    rooms = scene.house.rooms
    min_x = min(room.x - room.width / 2 for room in rooms)
    max_x = max(room.x + room.width / 2 for room in rooms)
    min_z = min(room.z - room.depth / 2 for room in rooms)
    max_z = max(room.z + room.depth / 2 for room in rooms)
    height = max(room.height for room in rooms)
    return _cube(
        bpy,
        "roof",
        (0, height + 0.2, 0),
        ((max_x - min_x) + 1.2, 0.4, (max_z - min_z) + 1.2),
    )


def _cube(bpy, name: str, position: tuple[float, float, float], scale: tuple[float, float, float]):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def _bpy():
    try:
        import bpy
    except ImportError as exc:
        raise RuntimeError("bpy is only available when running inside Blender") from exc
    return bpy
