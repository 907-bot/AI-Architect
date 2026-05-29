from __future__ import annotations

import re

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def infer_floor_count(text: str) -> int | None:
    lowered = text.lower()
    match = re.search(r"(\d+)\s*[- ]?(?:floor|storey|story|level)s?", lowered)
    if match:
        return max(1, min(int(match.group(1)), 12))
    for label, count in WORD_NUMBERS.items():
        if re.search(rf"{label}\s*[- ]?(?:floor|storey|story|level)s?", lowered):
            return count
    return None


def infer_style(text: str) -> str:
    lowered = text.lower()
    if "apartment" in lowered or "high-rise" in lowered or "highrise" in lowered:
        return "contemporary"
    for style in ("contemporary", "modern", "villa", "colonial", "craftsman", "minimalist", "brutalist"):
        if style in lowered:
            return style
    return "modern"


def infer_features(text: str) -> list[str]:
    lowered = text.lower()
    features: list[str] = []
    if "pool" in lowered or "swimming" in lowered:
        features.append("pool")
    if "garage" in lowered:
        features.append("garage")
    if "garden" in lowered or "landscape" in lowered:
        features.append("garden")
    if "balcony" in lowered or "balconies" in lowered:
        features.append("balcony")
    if "apartment" in lowered:
        features.append("apartment")
    return features


def is_highrise(floor_count: int, features: list[str]) -> bool:
    return floor_count >= 3 or "apartment" in features
