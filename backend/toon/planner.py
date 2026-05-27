from __future__ import annotations

import re


STYLE_WORDS = ("modern", "contemporary", "traditional", "minimalist", "brutalist", "scandinavian")
ROOF_WORDS = ("flat", "gable", "hip", "shed")


def prompt_to_toon(prompt: str) -> str:
    text = prompt.lower()
    style = next((word for word in STYLE_WORDS if word in text), "modern")
    roof = next((word for word in ROOF_WORDS if word in text), "flat")
    bedroom_count = _count_before_word(text, "bedroom", default=1 if "bedroom" in text else 2)
    wants_dining = "dining" in text
    wants_kitchen = "kitchen" in text

    rooms = [("living_room", "8x6")]
    rooms.extend((f"bedroom_{i + 1}", "5x5") for i in range(bedroom_count))
    if wants_kitchen:
        rooms.append(("kitchen", "4x4"))
    if wants_dining:
        rooms.append(("dining_room", "5x4"))

    lines = [f"HOUSE {style}_house {{", f"  STYLE {style}"]
    for name, size in rooms:
        lines.extend(["", f"  ROOM {name} {{", f"    size {size}", "  }"])
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
