from __future__ import annotations

import re

from backend.toon.models import SceneGraph
from backend.toon.parser import parse_toon


def edit_toon(existing_toon: str, instruction: str) -> tuple[str, SceneGraph, list[str]]:
    scene = parse_toon(existing_toon)
    changed: list[str] = []
    text = instruction.lower()

    # Handle floor addition - increment by 1 instead of setting to absolute value
    if "add" in text and "floor" in text:
        # Extract number of floors to add (default to 1)
        # Handle both "add 1 floor" and "add one floor"
        word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        
        # Try digit pattern first
        floor_add_match = re.search(r"add\s+(\d+)\s*(?:more\s*)?floor", text)
        if floor_add_match:
            floors_to_add = int(floor_add_match.group(1))
        else:
            # Try word pattern
            for word, num in word_to_num.items():
                if re.search(rf"add\s+{word}\s*(?:more\s*)?floor", text):
                    floors_to_add = num
                    break
            else:
                floors_to_add = 1  # Default to 1 if no number specified
        
        current_floors = scene.house.num_floors or 1
        scene.house.num_floors = current_floors + floors_to_add
        changed.append(f"{floors_to_add} floor(s)")

    # Handle garage addition
    if "garage" in text and ("add" in text or "include" in text or "with" in text):
        # Check if garage room already exists
        garage_exists = any("garage" in room.name.lower() for room in scene.house.rooms)
        if not garage_exists:
            from backend.toon.models import Room
            # Add garage room
            garage = Room(
                name="Garage",
                width=5.0,
                depth=6.0,
                height=3.0,
                room_type="garage",
                floor=0
            )
            scene.house.rooms.append(garage)
            changed.append("garage")

    for room in scene.house.rooms:
        normalized = room.name.lower().replace("_", " ")
        if normalized in text or room.name.lower() in text:
            if any(word in text for word in ("larger", "bigger", "increase")):
                room.width = round(room.width * 1.2, 2)
                room.depth = round(room.depth * 1.2, 2)
                changed.append(room.name)
            if any(word in text for word in ("smaller", "reduce", "decrease")):
                room.width = round(max(2.0, room.width * 0.85), 2)
                room.depth = round(max(2.0, room.depth * 0.85), 2)
                changed.append(room.name)

    roof_match = re.search(r"(flat|gable|hip|shed)\s+roof", text)
    if roof_match:
        scene.house.roof.kind = roof_match.group(1)
        changed.append("roof")

    return scene_to_toon(scene), scene, changed


def scene_to_toon(scene: SceneGraph) -> str:
    lines = [f"HOUSE {scene.house.name} {{", f"  STYLE {scene.house.style}"]
    # Include floor count if it exists
    if scene.house.num_floors:
        lines.append(f"  FLOORS {scene.house.num_floors}")
    for room in scene.house.rooms:
        lines.extend(["", f"  ROOM {room.name} {{", f"    size {room.width:g}x{room.depth:g}", f"    height {room.height:g}", "  }"])
    lines.extend(["", f"  ROOF {scene.house.roof.kind}", "}"])
    return "\n".join(lines)
