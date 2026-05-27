from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Room:
    name: str
    width: float
    depth: float
    height: float = 3.0
    floor: int = 0
    x: float = 0.0
    z: float = 0.0

    @property
    def room_type(self) -> str:
        lowered = self.name.lower()
        if "bed" in lowered:
            return "bedroom"
        if "living" in lowered or "lounge" in lowered:
            return "living_room"
        if "dining" in lowered:
            return "dining_room"
        if "kitchen" in lowered:
            return "kitchen"
        if "bath" in lowered:
            return "bathroom"
        return "room"


@dataclass
class Roof:
    kind: str = "flat"


@dataclass
class House:
    name: str
    style: str = "modern"
    rooms: list[Room] = field(default_factory=list)
    roof: Roof = field(default_factory=Roof)


@dataclass
class SceneGraph:
    house: House
    version: str = "0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "house": {
                "name": self.house.name,
                "style": self.house.style,
                "roof": {"kind": self.house.roof.kind},
                "rooms": [
                    {
                        "name": room.name,
                        "type": room.room_type,
                        "width": room.width,
                        "depth": room.depth,
                        "height": room.height,
                        "floor": room.floor,
                        "position": {"x": room.x, "y": room.floor * room.height, "z": room.z},
                    }
                    for room in self.house.rooms
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneGraph":
        house_data = data.get("house", data)
        rooms = [
            Room(
                name=room["name"],
                width=float(room["width"]),
                depth=float(room["depth"]),
                height=float(room.get("height", 3.0)),
                floor=int(room.get("floor", 0)),
                x=float(room.get("position", {}).get("x", room.get("x", 0.0))),
                z=float(room.get("position", {}).get("z", room.get("z", 0.0))),
            )
            for room in house_data.get("rooms", [])
        ]
        return cls(
            house=House(
                name=house_data.get("name", "house"),
                style=house_data.get("style", "modern"),
                rooms=rooms,
                roof=Roof(house_data.get("roof", {}).get("kind", "flat")),
            ),
            version=data.get("version", "0.1"),
        )
