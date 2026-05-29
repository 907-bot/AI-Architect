from __future__ import annotations

import re


STYLE_WORDS = ("modern", "contemporary", "traditional", "minimalist", "brutalist", "scandinavian")
ROOF_WORDS = ("flat", "gable", "hip", "shed")


def prompt_to_toon(prompt: str) -> str:
    text = prompt.lower()
    style = next((word for word in STYLE_WORDS if word in text), "modern")

    floor_count = _count_before_word(
        text.replace("storey", "floor").replace("story", "floor"),
        "floor", default=1
    )
    floor_count = max(1, min(floor_count, 20))

    is_apartment = "apartment" in text or floor_count >= 3
    roof = next((word for word in ROOF_WORDS if word in text), "flat" if is_apartment else "gable")

    wants_pool     = any(w in text for w in ("pool", "swimming"))
    wants_garage   = "garage" in text or "parking" in text
    bedroom_count  = _count_before_word(text, "bedroom", default=1 if "bedroom" in text else 2)
    bathroom_count = _count_before_word(text, "bathroom", default=1)
    wants_dining   = "dining" in text or "villa" in text or "family" in text
    wants_kitchen  = "kitchen" in text or "villa" in text or "house" in text or is_apartment

    rooms = []
    for floor in range(floor_count):
        suffix = f"_f{floor}" if floor_count > 1 else ""
        rooms.append((f"living_room{suffix}",   "living_room", "8x6", floor))
        rooms.append((f"hallway{suffix}",        "hallway",     "2x5", floor))
        if wants_kitchen:
            rooms.append((f"kitchen{suffix}",    "kitchen",     "4x4", floor))
        if wants_dining:
            rooms.append((f"dining_room{suffix}", "dining_room", "5x4", floor))
        for i in range(bedroom_count):
            rooms.append((f"bedroom_{i+1}{suffix}", "bedroom", "5x5", floor))
        for i in range(bathroom_count):
            rooms.append((f"bathroom_{i+1}{suffix}", "bathroom", "3x3", floor))

    if wants_pool:
        rooms.append(("swimming_pool", "pool",   "10x6", 0))
    if wants_garage:
        rooms.append(("garage",        "garage", "6x6",  0))

    lines = [
        f"HOUSE {style}_{'apartment' if is_apartment else 'house'} {{",
        f"  STYLE {style}"
    ]
    for name, room_type, size, floor in rooms:
        lines.extend([
            "",
            f"  ROOM {name} {{",
            f"    type {room_type}",
            f"    size {size}",
            f"    floor {floor}",
            "  }"
        ])
    lines.extend(["", f"  ROOF {roof}", "}"])
    return "\n".join(lines)


def _count_before_word(text: str, word: str, default: int) -> int:
    match = re.search(rf"(\d+)\s*[- ]?{word}s?", text)
    if match:
        return max(1, min(int(match.group(1)), 20))
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    for label, count in words.items():
        if re.search(rf"{label}\s+{word}s?", text):
            return count
    return default