from __future__ import annotations

from backend.toon.models import SceneGraph


MATERIALS = [
    {"id": "floor_concrete", "color_hex": "#c4c9d2", "roughness": 0.85},
    {"id": "wall_plaster", "color_hex": "#f3f4f6", "roughness": 0.75},
    {"id": "facade_panel", "color_hex": "#d1d5db", "roughness": 0.55, "metalness": 0.15},
    {"id": "facade_accent", "color_hex": "#64748b", "roughness": 0.45, "metalness": 0.25},
    {"id": "roof_dark", "color_hex": "#374151", "roughness": 0.65},
    {"id": "glass_clear", "color_hex": "#93c5fd", "roughness": 0.05, "transmission": 0.85, "opacity": 0.55, "transparent": True},
    {"id": "wood_warm", "color_hex": "#a16207", "roughness": 0.7},
    {"id": "fabric_blue", "color_hex": "#4068a8", "roughness": 0.9},
    {"id": "pool_water", "color_hex": "#0ea5e9", "roughness": 0.1, "transmission": 0.6, "opacity": 0.75, "transparent": True},
    {"id": "garage_metal", "color_hex": "#6b7280", "roughness": 0.4, "metalness": 0.35},
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
    floor_height = max(room.height for room in rooms) if rooms else 3.0
    max_floor_index = max(room.floor for room in rooms)
    num_floors = max(getattr(scene.house, "num_floors", 1) or 1, max_floor_index + 1)
    max_building_height = num_floors * floor_height
    center_x = (min_x + max_x) / 2
    center_z = (min_z + max_z) / 2
    features = getattr(scene.house, "features", []) or []

    meshes.append(_mesh("foundation", "Foundation", [center_x, -0.15, center_z], [total_width + 1.2, 0.3, total_depth + 1.2], "floor_concrete"))

    # Unified tower envelope so multi-storey buildings read clearly in the viewer.
    for floor_idx in range(num_floors):
        y_base = floor_idx * floor_height
        y_center = y_base + floor_height / 2
        meshes.append(_mesh(
            f"tower_shell_f{floor_idx}",
            "Walls",
            [center_x, y_center, center_z + total_depth / 2 - 0.05],
            [total_width + 0.4, floor_height - 0.15, 0.22],
            "facade_panel" if floor_idx % 2 == 0 else "facade_accent",
        ))
        for wx in (-total_width * 0.3, 0, total_width * 0.3):
            meshes.append(_mesh(
                f"tower_window_f{floor_idx}_{wx:.1f}",
                "Windows",
                [center_x + wx, y_base + floor_height * 0.55, center_z + total_depth / 2 + 0.02],
                [1.6, 1.4, 0.06],
                "glass_clear",
            ))

    for index, room in enumerate(rooms):
        prefix = f"room_{index}_{room.name}"
        floor_offset = room.floor * room.height
        meshes.append(_mesh(f"{prefix}_floor", "Floor Slabs", [room.x, floor_offset + 0.03, room.y], [room.width, 0.06, room.depth], "floor_concrete"))
        meshes.extend(_room_walls(prefix, room.x, room.y, room.width, room.depth, room.height, floor_offset))
        meshes.extend(_room_windows(prefix, room))
        meshes.extend(_room_doors(prefix, room))
        meshes.extend(_interiors(prefix, room))

    roof_y = max_building_height + 0.15
    meshes.append(_mesh("roof", "Roof", [center_x, roof_y, center_z], [total_width + 1.4, 0.35, total_depth + 1.4], "roof_dark", "box"))

    if "pool" in features:
        meshes.append(_mesh("pool", "Foundation", [center_x + total_width / 2 + 2.5, 0.05, center_z], [4.5, 0.12, 3.0], "pool_water"))
    if "garage" in features:
        meshes.append(_mesh("garage", "Walls", [center_x - total_width / 2 - 2.0, 1.4, center_z + total_depth / 4], [4.0, 2.8, 3.5], "garage_metal"))

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
        "total_height_m": max_building_height,
    }


def _room_walls(prefix: str, x: float, z: float, width: float, depth: float, height: float, floor_offset: float = 0.0) -> list[dict]:
    thickness = 0.18
    return [
        _mesh(f"{prefix}_wall_front", "Walls", [x, floor_offset + height / 2, z + depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_back", "Walls", [x, floor_offset + height / 2, z - depth / 2], [width, height, thickness], "wall_plaster"),
        _mesh(f"{prefix}_wall_left", "Walls", [x - width / 2, floor_offset + height / 2, z], [thickness, height, depth], "wall_plaster"),
        _mesh(f"{prefix}_wall_right", "Walls", [x + width / 2, floor_offset + height / 2, z], [thickness, height, depth], "wall_plaster"),
    ]


def _room_windows(prefix: str, room) -> list[dict]:
    meshes = []
    floor_offset = room.floor * room.height
    for index, window in enumerate(room.windows):
        position, scale = _opening_transform(room, window.side, window.x, window.y, window.width, 1.0, y=floor_offset + room.height * 0.58)
        meshes.append(_mesh(f"{prefix}_window_{index}", "Windows", position, scale, "glass_clear"))
    return meshes


def _room_doors(prefix: str, room) -> list[dict]:
    meshes = []
    seen = set()
    floor_offset = room.floor * room.height
    for door in room.doors:
        if door.id in seen:
            continue
        seen.add(door.id)
        position, scale = _opening_transform(room, door.side, door.x, door.y, door.width, 2.1, y=floor_offset + 1.05)
        meshes.append(_mesh(f"{prefix}_{door.id}", "Doors", position, scale, "wood_warm"))
    return meshes


def _interiors(prefix: str, room) -> list[dict]:
    floor_offset = room.floor * room.height
    if room.room_type == "bedroom":
        return [_mesh(f"{prefix}_bed", "Interior", [room.x, floor_offset + 0.32, room.y], [2.0, 0.55, 1.6], "fabric_blue")]
    if room.room_type == "living_room":
        return [_mesh(f"{prefix}_sofa", "Interior", [room.x, floor_offset + 0.45, room.y], [2.4, 0.8, 0.9], "fabric_blue")]
    if room.room_type == "dining_room":
        return [_mesh(f"{prefix}_table", "Interior", [room.x, floor_offset + 0.45, room.y], [1.8, 0.12, 1.0], "wood_warm")]
    return []


def _floor_plan(scene: SceneGraph) -> dict:
    rooms = scene.house.rooms
    walls = []
    doors = []
    windows = []
    for room in rooms:
        walls.extend([
            {"id": f"{room.name}_north", "room": room.name, "x1": room.left, "y1": room.top, "x2": room.right, "y2": room.top, "thickness": 0.18},
            {"id": f"{room.name}_south", "room": room.name, "x1": room.left, "y1": room.bottom, "x2": room.right, "y2": room.bottom, "thickness": 0.18},
            {"id": f"{room.name}_west", "room": room.name, "x1": room.left, "y1": room.bottom, "x2": room.left, "y2": room.top, "thickness": 0.18},
            {"id": f"{room.name}_east", "room": room.name, "x1": room.right, "y1": room.bottom, "x2": room.right, "y2": room.top, "thickness": 0.18},
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
