from __future__ import annotations

from backend.toon.models import Door, House, Room, Window


PUBLIC_TYPES  = {"living_room", "dining_room", "kitchen", "hallway"}
PRIVATE_TYPES = {"bedroom", "bathroom"}
SPECIAL_TYPES = {"pool", "garage"}


def optimize_layout(house: House) -> None:
    if not house.rooms:
        return

    # Separate special rooms (pool, garage) — laid out independently
    special = [r for r in house.rooms if r.room_type in SPECIAL_TYPES]
    structural = [r for r in house.rooms if r.room_type not in SPECIAL_TYPES]

    if not structural:
        return

    # Group structural rooms by floor and lay each floor out independently
    floors = sorted(set(r.floor for r in structural))
    for floor_num in floors:
        floor_rooms = [r for r in structural if r.floor == floor_num]
        _layout_floor(floor_rooms)

    # Pool: place to the right of the building
    building_right = max((r.x + r.width / 2 for r in structural), default=0)
    for i, room in enumerate(r for r in special if r.room_type == "pool"):
        room.x = building_right + room.width / 2 + 3.0
        room.y = 0.0

    # Garage: place to the left
    building_left = min((r.x - r.width / 2 for r in structural), default=0)
    for i, room in enumerate(r for r in special if r.room_type == "garage"):
        room.x = building_left - room.width / 2 - 3.0
        room.y = 0.0

    _build_adjacency(house)
    _place_doors_and_windows(house)
    _build_circulation(house)


def _layout_floor(rooms: list[Room]) -> None:
    """Lay out one floor's rooms in 2D (x/y plan). floor.y is plan-depth, not height."""
    if not rooms:
        return

    living   = _first(rooms, "living_room")
    bedrooms = [r for r in rooms if r.room_type == "bedroom"]
    bathrooms = [r for r in rooms if r.room_type == "bathroom"]
    kitchens = [r for r in rooms if r.room_type == "kitchen"]
    dining   = _first(rooms, "dining_room")
    hallway  = _first(rooms, "hallway")

    if living:
        living.x = 0.0
        living.y = -living.depth / 2

    rear_rooms = bedrooms + bathrooms
    if rear_rooms:
        total_width = sum(r.width for r in rear_rooms)
        cursor = -total_width / 2
        for room in rear_rooms:
            room.x = cursor + room.width / 2
            room.y = room.depth / 2 + 0.8
            cursor += room.width

    if hallway:
        rear_top = max((r.top for r in rear_rooms), default=2.8)
        front_bottom = living.top if living else 0.0
        hallway.width = max(1.4, hallway.width)
        hallway.depth = max(2.0, rear_top - front_bottom)
        hallway.x = 0.0
        hallway.y = front_bottom + hallway.depth / 2

    side_x = max((r.right for r in rear_rooms), default=3.0) + 2.2
    if kitchens:
        kitchens[0].x = side_x
        kitchens[0].y = living.y if living else 0.0
    if dining:
        dining.x = side_x
        dining.y = (kitchens[0].top + dining.depth / 2 + 0.3) if kitchens else 0.0


def _build_adjacency(house: House) -> None:
    structural = [r for r in house.rooms if r.room_type not in SPECIAL_TYPES]
    # Only connect rooms on the same floor
    edges: list[tuple[str, str]] = []
    floors = sorted(set(r.floor for r in structural))
    for floor_num in floors:
        rooms = [r for r in structural if r.floor == floor_num]
        living  = _first(rooms, "living_room")
        hallway = _first(rooms, "hallway")
        kitchen = _first(rooms, "kitchen")
        dining  = _first(rooms, "dining_room")
        if living and hallway:
            edges.append((living.name, hallway.name))
        if kitchen and living:
            edges.append((living.name, kitchen.name))
        if kitchen and dining:
            edges.append((kitchen.name, dining.name))
        elif dining and living:
            edges.append((living.name, dining.name))
        connector = hallway or living
        if connector:
            for room in rooms:
                if room.room_type in PRIVATE_TYPES:
                    edges.append((connector.name, room.name))
    house.adjacency = _unique_edges(edges)


def _place_doors_and_windows(house: House) -> None:
    for room in house.rooms:
        room.doors = []
        room.windows = []
    room_by_name = {room.name: room for room in house.rooms}
    for index, (left_name, right_name) in enumerate(house.adjacency):
        left  = room_by_name[left_name]
        right = room_by_name[right_name]
        x    = (left.x + right.x) / 2
        y    = (left.y + right.y) / 2
        side = _door_side(left, right)
        door = Door(
            id=f"door_{index}_{left.name}_{right.name}",
            room_a=left.name, room_b=right.name,
            x=x, y=y, side=side,
        )
        left.doors.append(door)
        right.doors.append(door)
    for room in house.rooms:
        if room.room_type not in SPECIAL_TYPES:
            room.windows.extend(_windows_for_room(room))


def _windows_for_room(room: Room) -> list[Window]:
    side = "front" if room.room_type in PUBLIC_TYPES else "back"
    y = room.bottom if side == "front" else room.top
    return [Window(
        id=f"{room.name}_{side}_window",
        room=room.name,
        x=room.x, y=y,
        width=min(2.4, max(1.2, room.width * 0.42)),
        side=side,
    )]


def _build_circulation(house: House) -> None:
    room_by_name = {room.name: room for room in house.rooms}
    paths = []
    for left_name, right_name in house.adjacency:
        left  = room_by_name[left_name]
        right = room_by_name[right_name]
        paths.append({
            "from": left.name, "to": right.name,
            "points": [
                {"x": left.x,  "y": left.y},
                {"x": (left.x + right.x) / 2, "y": (left.y + right.y) / 2},
                {"x": right.x, "y": right.y},
            ],
        })
    house.circulation = paths


def _door_side(room: Room, other: Room) -> str:
    dx = other.x - room.x
    dy = other.y - room.y
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "back" if dy > 0 else "front"


def _first(rooms: list[Room], room_type: str) -> Room | None:
    return next((r for r in rooms if r.room_type == room_type), None)


def _unique_edges(edges: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    output = []
    for left, right in edges:
        key = tuple(sorted((left, right)))
        if key in seen:
            continue
        seen.add(key)
        output.append((left, right))
    return output
