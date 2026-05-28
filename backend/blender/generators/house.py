from __future__ import annotations

from typing import Any

from backend.toon.models import Room, SceneGraph


MATERIALS = {
    "floor": ("Floor warm concrete", (0.62, 0.64, 0.68, 1.0), 0.85, 0.0),
    "wall": ("Soft white plaster", (0.92, 0.9, 0.86, 1.0), 0.78, 0.0),
    "roof": ("Charcoal flat roof", (0.18, 0.22, 0.28, 0.82), 0.65, 0.0),
    "glass": ("Pale blue glass", (0.55, 0.82, 1.0, 0.45), 0.04, 0.0),
    "wood": ("Warm walnut", (0.52, 0.28, 0.12, 1.0), 0.58, 0.0),
    "fabric": ("Deep blue fabric", (0.14, 0.24, 0.48, 1.0), 0.9, 0.0),
    "metal": ("Dark metal", (0.12, 0.13, 0.14, 1.0), 0.35, 0.2),
}


def create_room(scene_or_room: SceneGraph | Room, room: Room | None = None) -> list[Any]:
    bpy = _bpy()
    mats = _materials(bpy)
    target = room or scene_or_room
    if not isinstance(target, Room):
        raise TypeError("create_room expects a Room or SceneGraph plus Room")

    objects = []
    objects.append(_cube(bpy, f"{target.name}_floor", (target.x, 0.03, target.z), (target.width, 0.06, target.depth), mats["floor"]))
    objects.append(create_wall(target, "front"))
    objects.append(create_wall(target, "back"))
    objects.append(create_wall(target, "left"))
    objects.append(create_wall(target, "right"))
    objects.extend(create_windows(target))
    objects.extend(create_door(target))
    objects.extend(create_interior(target))
    return objects


def create_wall(room: Room, side: str):
    bpy = _bpy()
    mats = _materials(bpy)
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
    return _cube(bpy, f"{room.name}_wall_{side}", position, scale, mats["wall"])


def create_windows(room: Room) -> list[Any]:
    bpy = _bpy()
    mats = _materials(bpy)
    objects = []
    for index, window in enumerate(room.windows):
        position, scale = _opening_transform(room, window.side, window.x, window.y, window.width, 1.0, y=room.height * 0.58)
        objects.append(_cube(bpy, f"{room.name}_window_{index}", position, scale, mats["glass"], bevel=0.02))
    return objects


def create_door(room: Room) -> list[Any]:
    bpy = _bpy()
    mats = _materials(bpy)
    objects = []
    seen = set()
    for door in room.doors:
        if door.id in seen:
            continue
        seen.add(door.id)
        position, scale = _opening_transform(room, door.side, door.x, door.y, door.width, 2.1, y=1.05)
        objects.append(_cube(bpy, f"{room.name}_{door.id}", position, scale, mats["wood"], bevel=0.03))
    if not objects:
        objects.append(_cube(
            bpy,
            f"{room.name}_entry_door",
            (room.x - min(room.width * 0.25, 1.5), 1.05, room.bottom - 0.04),
            (0.9, 2.1, 0.07),
            mats["wood"],
            bevel=0.03,
        ))
    return objects


def create_interior(room: Room) -> list[Any]:
    bpy = _bpy()
    mats = _materials(bpy)
    if room.room_type == "bedroom":
        return [
            _cube(bpy, f"{room.name}_bed_base", (room.x, 0.28, room.z), (2.0, 0.45, 1.55), mats["fabric"], bevel=0.08),
            _cube(bpy, f"{room.name}_pillow", (room.x, 0.62, room.z - 0.45), (1.65, 0.18, 0.35), mats["wall"], bevel=0.09),
            _cube(bpy, f"{room.name}_nightstand", (room.x + 1.45, 0.35, room.z - 0.35), (0.55, 0.7, 0.55), mats["wood"], bevel=0.04),
        ]
    if room.room_type == "living_room":
        return [
            _cube(bpy, f"{room.name}_sofa", (room.x - 1.0, 0.42, room.z), (2.5, 0.75, 0.9), mats["fabric"], bevel=0.08),
            _cube(bpy, f"{room.name}_coffee_table", (room.x + 1.5, 0.28, room.z), (1.4, 0.18, 0.75), mats["wood"], bevel=0.04),
            _cube(bpy, f"{room.name}_tv_wall", (room.x, 1.1, room.z - room.depth / 2 + 0.08), (2.2, 1.1, 0.08), mats["metal"], bevel=0.03),
        ]
    if room.room_type == "dining_room":
        return [
            _cube(bpy, f"{room.name}_dining_table", (room.x, 0.45, room.z), (1.8, 0.12, 1.0), mats["wood"], bevel=0.04),
        ]
    return []


def create_roof(scene: SceneGraph):
    bpy = _bpy()
    mats = _materials(bpy)
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
        mats["roof"],
        bevel=0.08,
    )


def _opening_transform(room: Room, side: str, x: float, y_plan: float, width: float, height: float, y: float):
    thickness = 0.08
    if side == "front":
        return (x, y, room.bottom - 0.04), (width, height, thickness)
    if side == "back":
        return (x, y, room.top + 0.04), (width, height, thickness)
    if side == "left":
        return (room.left - 0.04, y, y_plan), (thickness, height, width)
    if side == "right":
        return (room.right + 0.04, y, y_plan), (thickness, height, width)
    return (x, y, y_plan), (width, height, thickness)


def _cube(
    bpy,
    name: str,
    position: tuple[float, float, float],
    scale: tuple[float, float, float],
    material=None,
    bevel: float = 0.015,
):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new(name="soft_edges", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def _materials(bpy) -> dict[str, Any]:
    existing = {mat.name: mat for mat in bpy.data.materials}
    output = {}
    for key, (name, color, roughness, metallic) in MATERIALS.items():
        if name in existing:
            output[key] = existing[name]
            continue
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = color
        principled = mat.node_tree.nodes.get("Principled BSDF")
        if principled:
            principled.inputs["Base Color"].default_value = color
            principled.inputs["Roughness"].default_value = roughness
            principled.inputs["Metallic"].default_value = metallic
            if color[3] < 1.0:
                mat.blend_method = "BLEND"
                mat.use_screen_refraction = True
                principled.inputs["Alpha"].default_value = color[3]
        output[key] = mat
    return output


def _bpy():
    try:
        import bpy
    except ImportError as exc:
        raise RuntimeError("bpy is only available when running inside Blender") from exc
    return bpy
