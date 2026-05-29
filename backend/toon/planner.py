from __future__ import annotations

import re

from backend.toon.prompt_meta import infer_features, infer_floor_count, infer_style, is_highrise


STYLE_WORDS = ("modern", "contemporary", "traditional", "minimalist", "brutalist", "scandinavian")
ROOF_WORDS = ("flat", "gable", "hip", "shed")


def prompt_to_toon(prompt: str) -> str:
    text = prompt.lower()
    style = infer_style(prompt)
    features = infer_features(prompt)
    is_apartment = "apartment" in features or "apartment" in text
    roof = "flat" if is_highrise(infer_floor_count(prompt) or 1, features) else next(
        (word for word in ROOF_WORDS if word in text), "flat"
    )
    floor_count = infer_floor_count(prompt) or 1
    floor_count = max(floor_count, _count_before_word(text, "floor", default=1))
    floor_count = max(floor_count, _count_before_word(text, "storey", default=1))
    floor_count = max(floor_count, _count_before_word(text, "story", default=1))
    floor_count = max(1, min(floor_count, 12))
    bedroom_count = _count_before_word(text, "bedroom", default=2 if is_apartment else (1 if "bedroom" in text else 2))
    bathroom_count = max(_count_before_word(text, "bathroom", default=1), min(2, floor_count))
    wants_dining = "dining" in text or "villa" in text or "family" in text
    wants_kitchen = "kitchen" in text or "villa" in text or "house" in text or is_apartment
    wants_balcony = "balcony" in text or floor_count > 1
    wants_garage = "garage" in text
    wants_pool = "pool" in text or "swimming" in text

    floor_rooms: dict[int, list[tuple[str, str, str]]] = {i: [] for i in range(floor_count)}
    floor_rooms[0].extend([("lobby", "hallway", "6x4") if is_apartment else ("living_room", "living_room", "8x6")])
    if not is_apartment:
        floor_rooms[0].append(("hallway", "hallway", "2x5"))
    if wants_kitchen:
        floor_rooms[0].append(("kitchen", "kitchen", "4x4"))
    if wants_dining:
        floor_rooms[0].append(("dining_room", "dining_room", "5x4"))
    if wants_garage:
        floor_rooms[0].append(("garage", "garage", "6x5"))

    units_per_upper = max(2, bedroom_count // max(floor_count - 1, 1) + 1)
    bed_i = 0
    bath_i = 0
    for floor_idx in range(1, floor_count):
        for _ in range(units_per_upper if is_apartment else 1):
            if bed_i < bedroom_count:
                floor_rooms[floor_idx].append((f"bedroom_{bed_i + 1}", "bedroom", "4x4" if is_apartment else "5x5"))
                bed_i += 1
            if bath_i < bathroom_count and floor_idx % 2 == 1:
                floor_rooms[floor_idx].append((f"bathroom_{bath_i + 1}", "bathroom", "3x3"))
                bath_i += 1
    while bed_i < bedroom_count:
        target_floor = min(1 + (bed_i % max(floor_count - 1, 1)), floor_count - 1)
        floor_rooms[target_floor].append((f"bedroom_{bed_i + 1}", "bedroom", "5x5"))
        bed_i += 1
    while bath_i < bathroom_count:
        target_floor = min(1 + (bath_i % max(floor_count - 1, 1)), floor_count - 1)
        floor_rooms[target_floor].append((f"bathroom_{bath_i + 1}", "bathroom", "3x3"))
        bath_i += 1
    if wants_balcony and floor_count > 1:
        for floor_idx in range(1, floor_count):
            floor_rooms[floor_idx].append((f"balcony_{floor_idx}", "balcony", "6x2"))

    name = "apartment_tower" if is_apartment else f"{style}_house"
    lines = [f"HOUSE {name} {{", f"  STYLE {style}", f"  FLOORS {floor_count}"]
    for floor_idx in range(floor_count):
        lines.extend(["", f"  FLOOR {floor_idx}"])
        for name, room_type, size in floor_rooms[floor_idx]:
            lines.extend(["", f"  ROOM {name} {{", f"    type {room_type}", f"    size {size}", "  }"])
    lines.extend(["", f"  ROOF {roof}", "}"])
    return "\n".join(lines)


def _count_before_word(text: str, word: str, default: int) -> int:
    match = re.search(rf"(\d+)\s*[- ]?{word}s?", text)
    if match:
        return max(1, min(int(match.group(1)), 12))
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
    }
    for label, count in words.items():
        if re.search(rf"{label}\s+{word}s?", text):
            return count
    return default
