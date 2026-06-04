from __future__ import annotations

import re

from backend.toon.models import SceneGraph
from backend.toon.parser import parse_toon

# ── Vocabulary helpers ────────────────────────────────────────────────────────
_WORD_TO_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _parse_floor_count(text: str) -> int:
    """Extract a floor count (≥1) from text, defaulting to 1."""
    digit_match = re.search(r"(\d+)", text)
    if digit_match:
        return max(1, min(int(digit_match.group(1)), 10))
    for word, num in _WORD_TO_NUM.items():
        if word in text:
            return num
    return 1


def edit_toon(existing_toon: str, instruction: str) -> tuple[str, SceneGraph, list[str]]:
    scene = parse_toon(existing_toon)
    changed: list[str] = []
    text = instruction.lower()

    # ── Floor addition ────────────────────────────────────────────────────────
    # Matches: "add a floor", "add 1 floor", "add one more floor",
    #          "one more floor", "+1 floor", "extra floor"
    _add_floor = (
        ("add" in text or "+" in text or "extra" in text or "more floor" in text)
        and "floor" in text
        and not any(w in text for w in ("remove", "reduc", "decreas", "fewer", "less", "subtract"))
    )
    if _add_floor:
        floors_to_add = _parse_floor_count(
            re.sub(r"(add|more|floor|extra|one|a|the)\b", "", text)
        ) if re.search(r"\d+", text) else _parse_floor_count(text)
        current_floors = scene.house.num_floors or 1
        scene.house.num_floors = current_floors + floors_to_add
        changed.append(f"+{floors_to_add} floor(s)")

    # ── Floor removal ─────────────────────────────────────────────────────────
    # Matches: "remove a floor", "remove 1 floor", "decrease floors",
    #          "fewer floors", "reduce floors", "subtract a floor"
    _remove_floor = (
        any(w in text for w in ("remove", "reduc", "decreas", "fewer", "less floor", "subtract"))
        and "floor" in text
    )
    if _remove_floor and not _add_floor:
        floors_to_remove = _parse_floor_count(text)
        current_floors = scene.house.num_floors or 1
        scene.house.num_floors = max(1, current_floors - floors_to_remove)
        changed.append(f"-{floors_to_remove} floor(s)")

    # ── Garage addition ───────────────────────────────────────────────────────
    if "garage" in text and ("add" in text or "include" in text or "with" in text):
        garage_exists = any("garage" in room.name.lower() for room in scene.house.rooms)
        if not garage_exists:
            from backend.toon.models import Room
            garage = Room(
                name="Garage",
                width=5.0,
                depth=6.0,
                height=3.0,
                room_type_hint="garage",
                floor=0
            )
            scene.house.rooms.append(garage)
            changed.append("garage")

    # ── Room resizing ─────────────────────────────────────────────────────────
    _generic_enlarge = any(w in text for w in ("larger", "bigger", "wider", "increase", "grow"))
    _generic_shrink  = any(w in text for w in ("smaller", "narrower", "reduce", "decrease", "shrink"))
    _targets_all_rooms = any(w in text for w in ("all rooms", "rooms", "room sizes", "all floors"))

    for room in scene.house.rooms:
        normalized = room.name.lower().replace("_", " ")
        room_mentioned = (normalized in text or room.name.lower() in text)

        # Apply if room name is explicitly mentioned OR if a generic "all rooms" intent is detected
        if room_mentioned or (_targets_all_rooms and (_generic_enlarge or _generic_shrink)):
            if _generic_enlarge:
                room.width = round(room.width * 1.2, 2)
                room.depth = round(room.depth * 1.2, 2)
                if room.name not in changed:
                    changed.append(room.name)
            elif _generic_shrink:
                room.width = round(max(2.0, room.width * 0.85), 2)
                room.depth = round(max(2.0, room.depth * 0.85), 2)
                if room.name not in changed:
                    changed.append(room.name)

    # ── Roof style ────────────────────────────────────────────────────────────
    # Matches: "flat roof", "gable roof", "change roof to gable", "use hip"
    roof_match = re.search(r"(flat|gable|hip|shed)\s+roof", text) \
              or re.search(r"roof\s+(?:to|style|type|is|=)?\s*(flat|gable|hip|shed)", text)
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
        name = room.name.replace(" ", "_")
        lines.extend(["", f"  ROOM {name} {{", f"    size {room.width:g}x{room.depth:g}", f"    height {room.height:g}", "  }"])
    lines.extend(["", f"  ROOF {scene.house.roof.kind}", "}"])
    return "\n".join(lines)


