from __future__ import annotations

from backend.toon.models import SceneGraph


MATERIALS = [
    {"id": "floor_concrete", "color_hex": "#b8bec8", "roughness": 0.9},
    {"id": "wall_plaster", "color_hex": "#eef1f4", "roughness": 0.82},
    {"id": "roof_dark", "color_hex": "#4b5563", "roughness": 0.75},
    {"id": "glass_clear", "color_hex": "#bfe7ff", "roughness": 0.08, "transmission": 0.7, "opacity": 0.42, "transparent": True},
    {"id": "wood_warm", "color_hex": "#a16207", "roughness": 0.7},
    {"id": "fabric_blue", "color_hex": "#4068a8", "roughness": 0.9},
]


def compile_scene(scene: SceneGraph) -> dict:
    meshes = []
    rooms = scene.house.rooms
    if not rooms:
        return {"meshes": [], "rooms": [], "style": scene.house.style, "materials": MATERIALS}

    min_x = min(room.x - room.width / 2 for room in rooms)
    max_x = max(room.x + room.width / 2 for room in rooms)
    min_z = min(room.z - room.depth / 2 for room in rooms)
    max_z = max(room.z + room.depth / 2 for room in rooms)
    total_width = max_x - min_x
    total_depth = max_z - min_z
    height = max(room.height for room in rooms)

    meshes.append(_mesh("foundation", "Foundation", [0, -0.15, 0], [total_width + 1, 0.3, total_depth + 1], "floor_concrete"))

    for index, room in enumerate(rooms):
        prefix = f"room_{index}_{room.name}"
        meshes.append(_mesh(f"{prefix}_floor", "Floor Slabs", [room.x, 0.03, room.z], [room.width, 0.06, room.depth], "floor_concrete"))
        meshes.extend(_room_walls(prefix, room.x, room.z, room.width, room.depth, room.height))
        meshes.extend(_room_windows(prefix, room.x, room.z, room.width, room.depth, room.height))
        meshes.extend(_interiors(prefix, room))

    roof_y = height + 0.2
    roof_type = "prism" if scene.house.roof.kind in {"gable", "hip"} else "box"
    meshes.append(_mesh("roof", "Roof", [0, roof_y, 0], [total_width + 1.2, 0.4 if roof_type == "box" else 1.2, total_depth + 1.2], "roof_dark", roof_type))

    return {
        "meshes": meshes,
        "rooms": [
            {"id": room.name, "name": room.name, "x": room.x, "y": room.z, "width_m": room.width, "height_m": room.depth}
            for room in rooms
        ],
        "materials": MATERIALS,
        "style": scene.house.style,
        "roof": scene.house.roof.kind,
        "total_height_m": height,
    }


def _room_walls(prefix: str, x: float, z: float, width: float, depth: float, height: float) -> list[dict]:
    thickness = 0.18
    return [
        _mesh(f"{prefix}_wall_front", "Walls", [x, height / 2, z + depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_back", "Walls", [x, height / 2, z - depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_left", "Walls", [x - width / 2, height / 2, z], [thickness, height, depth], "wall_plaster"),
        _mesh(f"{prefix}_wall_right", "Walls", [x + width / 2, height / 2, z], [thickness, height, depth], "wall_plaster"),
    ]


def _room_windows(prefix: str, x: float, z: float, width: float, depth: float, height: float) -> list[dict]:
    return [
        _mesh(f"{prefix}_window_front", "Windows", [x, height * 0.58, z + depth / 2 + 0.02], [min(2.2, width * 0.45), 1.0, 0.05], "glass_clear"),
        _mesh(f"{prefix}_window_back", "Windows", [x, height * 0.58, z - depth / 2 - 0.02], [min(2.2, width * 0.45), 1.0, 0.05], "glass_clear"),
    ]


def _interiors(prefix: str, room) -> list[dict]:
    if room.room_type == "bedroom":
        return [_mesh(f"{prefix}_bed", "Interior", [room.x, 0.32, room.z], [2.0, 0.55, 1.6], "fabric_blue")]
    if room.room_type == "living_room":
        return [_mesh(f"{prefix}_sofa", "Interior", [room.x, 0.45, room.z], [2.4, 0.8, 0.9], "fabric_blue")]
    if room.room_type == "dining_room":
        return [_mesh(f"{prefix}_table", "Interior", [room.x, 0.45, room.z], [1.8, 0.12, 1.0], "wood_warm")]
    return []


def _mesh(mesh_id: str, group: str, position: list[float], scale: list[float], material: str, mesh_type: str = "box") -> dict:
    return {
        "id": mesh_id,
        "component_group": group,
        "type": mesh_type,
        "position": position,
        "scale": scale,
        "material_id": material,
    }
