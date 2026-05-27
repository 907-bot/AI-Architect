from __future__ import annotations

import re

from backend.toon.models import SceneGraph
from backend.toon.parser import parse_toon


def edit_toon(existing_toon: str, instruction: str) -> tuple[str, SceneGraph, list[str]]:
    scene = parse_toon(existing_toon)
    changed: list[str] = []
    text = instruction.lower()

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
    for room in scene.house.rooms:
        lines.extend(["", f"  ROOM {room.name} {{", f"    size {room.width:g}x{room.depth:g}", f"    height {room.height:g}", "  }"])
    lines.extend(["", f"  ROOF {scene.house.roof.kind}", "}"])
    return "\n".join(lines)
