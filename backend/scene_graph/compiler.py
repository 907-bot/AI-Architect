from __future__ import annotations

from backend.toon.models import SceneGraph


MATERIALS = [
    {"id": "floor_concrete", "color_hex": "#b8bec8", "roughness": 0.9},
    {"id": "wall_plaster", "color_hex": "#eef1f4", "roughness": 0.82},
    {"id": "roof_dark", "color_hex": "#4b5563", "roughness": 0.75, "opacity": 0.72, "transparent": True},
    {"id": "glass_clear", "color_hex": "#bfe7ff", "roughness": 0.08, "transmission": 0.7, "opacity": 0.42, "transparent": True},
    {"id": "wood_warm", "color_hex": "#a16207", "roughness": 0.7},
    {"id": "fabric_blue", "color_hex": "#4068a8", "roughness": 0.9},
]


def compile_scene(scene: SceneGraph) -> dict:
    meshes = []
    rooms = scene.house.rooms
    if not rooms:
        return {
            "meshes": [],
            "rooms": [],
            "floor_plan": {"rooms": [], "walls": [], "doors": [], "windows": [], "circulation": [], "adjacency": []},
            "style": scene.house.style,
            "materials": MATERIALS,
        }

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
        meshes.append(_mesh(f"{prefix}_floor", "Floor Slabs", [room.x, 0.03, room.y], [room.width, 0.06, room.depth], "floor_concrete"))
        meshes.extend(_room_walls(prefix, room.x, room.y, room.width, room.depth, room.height))
        meshes.extend(_room_windows(prefix, room))
        meshes.extend(_room_doors(prefix, room))
        meshes.extend(_interiors(prefix, room))

    roof_y = height + 0.2
    roof_type = "prism" if scene.house.roof.kind in {"gable", "hip"} else "box"
    meshes.append(_mesh("roof", "Roof", [0, roof_y, 0], [total_width + 1.2, 0.4 if roof_type == "box" else 1.2, total_depth + 1.2], "roof_dark", roof_type))

    return {
        "meshes": meshes,
        "rooms": [
            {
                "id": room.name,
                "name": room.name,
                "type": room.room_type,
                "x": room.x,
                "y": room.y,
                "width_m": room.width,
                "height_m": room.depth,
                "depth_m": room.depth,
                "area_m2": round(room.width * room.depth, 2),
            }
            for room in rooms
        ],
        "floor_plan": _floor_plan(scene),
        "adjacency": [{"from": left, "to": right} for left, right in scene.house.adjacency],
        "circulation": scene.house.circulation,
        "materials": MATERIALS,
        "style": scene.house.style,
        "roof": scene.house.roof.kind,
        "total_height_m": height,
    }


def _room_walls(prefix: str, x: float, z: float, width: float, depth: float, height: float) -> list[dict]:
    thickness = 0.22  # Thicker walls for better visibility
    return [
        _mesh(f"{prefix}_wall_front", "Walls", [x, height / 2, z + depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_back", "Walls", [x, height / 2, z - depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_left", "Walls", [x - width / 2, height / 2, z], [thickness, height, depth], "wall_plaster"),
        _mesh(f"{prefix}_wall_right", "Walls", [x + width / 2, height / 2, z], [thickness, height, depth], "wall_plaster"),
    ]


def _room_windows(prefix: str, room) -> list[dict]:
    meshes = []
    for index, window in enumerate(room.windows):
        position, scale = _opening_transform(room, window.side, window.x, window.y, window.width, 1.2, y=room.height * 0.58)
        # Add window frame
        frame_scale = [scale[0] * 1.15, scale[1] * 1.15, scale[2] * 1.5]
        meshes.append(_mesh(f"{prefix}_window_frame_{index}", "Windows", position, frame_scale, "wall_plaster"))
        # Add glass
        meshes.append(_mesh(f"{prefix}_window_{index}", "Windows", position, scale, "glass_clear"))
    return meshes


def _room_doors(prefix: str, room) -> list[dict]:
    meshes = []
    seen = set()
    for door in room.doors:
        if door.id in seen:
            continue
        seen.add(door.id)
        # Door frame
        position, scale = _opening_transform(room, door.side, door.x, door.y, door.width, 2.2, y=1.1)
        frame_scale = [scale[0] * 1.2, scale[1] * 1.1, scale[2] * 1.5]
        meshes.append(_mesh(f"{prefix}_{door.id}_frame", "Doors", position, frame_scale, "wall_plaster"))
        # Door panel
        meshes.append(_mesh(f"{prefix}_{door.id}", "Doors", position, scale, "wood_warm"))
    return meshes


def _interiors(prefix: str, room) -> list[dict]:
    if room.room_type == "bedroom":
        return [_mesh(f"{prefix}_bed", "Interior", [room.x, 0.32, room.y], [2.0, 0.55, 1.6], "fabric_blue")]
    if room.room_type == "living_room":
        return [_mesh(f"{prefix}_sofa", "Interior", [room.x, 0.45, room.y], [2.4, 0.8, 0.9], "fabric_blue")]
    if room.room_type == "dining_room":
        return [_mesh(f"{prefix}_table", "Interior", [room.x, 0.45, room.y], [1.8, 0.12, 1.0], "wood_warm")]
    return []


def _floor_plan(scene: SceneGraph) -> dict:
    rooms = scene.house.rooms
    wall_thickness = 0.22  # Consistent with 3D model
    walls = []
    doors = []
    windows = []
    for room in rooms:
        walls.extend([
            {"id": f"{room.name}_north", "room": room.name, "x1": room.left, "y1": room.top, "x2": room.right, "y2": room.top, "thickness": wall_thickness},
            {"id": f"{room.name}_south", "room": room.name, "x1": room.left, "y1": room.bottom, "x2": room.right, "y2": room.bottom, "thickness": wall_thickness},
            {"id": f"{room.name}_west", "room": room.name, "x1": room.left, "y1": room.bottom, "x2": room.left, "y2": room.top, "thickness": wall_thickness},
            {"id": f"{room.name}_east", "room": room.name, "x1": room.right, "y1": room.bottom, "x2": room.right, "y2": room.top, "thickness": wall_thickness},
        ])
        for door in room.doors:
            if door.room_a != room.name:
                continue
            doors.append({
                "id": door.id,
                "room_a": door.room_a,
                "room_b": door.room_b,
                "x": door.x,
                "y": door.y,
                "width": door.width,
                "side": door.side,
            })
        windows.extend([
            {"id": window.id, "room": window.room, "x": window.x, "y": window.y, "width": window.width, "side": window.side}
            for window in room.windows
        ])

    return {
        "rooms": [
            {
                "id": room.name,
                "name": room.name,
                "type": room.room_type,
                "x": room.x,
                "y": room.y,
                "width": room.width,
                "depth": room.depth,
                "height": room.height,
                "area_m2": round(room.width * room.depth, 2),
            }
            for room in rooms
        ],
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "adjacency": [{"from": left, "to": right} for left, right in scene.house.adjacency],
        "circulation": scene.house.circulation,
    }


def _opening_transform(room, side: str, x: float, y_plan: float, width: float, height: float, y: float) -> tuple[list[float], list[float]]:
    thickness = 0.08
    if side == "front":
        return [x, y, room.bottom - 0.04], [width, height, thickness]
    if side == "back":
        return [x, y, room.top + 0.04], [width, height, thickness]
    if side == "left":
        return [room.left - 0.04, y, y_plan], [thickness, height, width]
    if side == "right":
        return [room.right + 0.04, y, y_plan], [thickness, height, width]
    return [x, y, y_plan], [width, height, thickness]


def _mesh(mesh_id: str, group: str, position: list[float], scale: list[float], material: str, mesh_type: str = "box") -> dict:
    return {
        "id": mesh_id,
        "component_group": group,
        "type": mesh_type,
        "position": position,
        "scale": scale,
        "material_id": material,
    }
