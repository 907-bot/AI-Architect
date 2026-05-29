from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Door:
    id: str
    room_a: str
    room_b: str | None
    x: float
    y: float
    width: float = 0.9
    side: str = "front"


@dataclass
class Window:
    id: str
    room: str
    x: float
    y: float
    width: float = 1.4
    side: str = "front"


@dataclass
class Room:
    name: str
    width: float
    depth: float
    height: float = 3.0
    floor: int = 0
    x: float = 0.0
    y: float = 0.0
    room_type_hint: str | None = None
    doors: list[Door] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)

    @property
    def room_type(self) -> str:
        if self.room_type_hint:
            return self.room_type_hint
        lowered = self.name.lower()
        if "bed" in lowered:
            return "bedroom"
        if "hall" in lowered or "corridor" in lowered:
            return "hallway"
        if "living" in lowered or "lounge" in lowered:
            return "living_room"
        if "dining" in lowered:
            return "dining_room"
        if "kitchen" in lowered:
            return "kitchen"
        if "bath" in lowered:
            return "bathroom"
        if "balcony" in lowered:
            return "balcony"
        if "garage" in lowered:
            return "garage"
        return "room"

    @property
    def z(self) -> float:
        return self.y

    @z.setter
    def z(self, value: float) -> None:
        self.y = value

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2

    @property
    def bottom(self) -> float:
        return self.y - self.depth / 2

    @property
    def top(self) -> float:
        return self.y + self.depth / 2


@dataclass
class Roof:
    kind: str = "flat"


@dataclass
class House:
    name: str
    style: str = "modern"
    num_floors: int = 1
    features: list[str] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    roof: Roof = field(default_factory=Roof)
    adjacency: list[tuple[str, str]] = field(default_factory=list)
    circulation: list[dict[str, Any]] = field(default_factory=list)


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
                "num_floors": self.house.num_floors,
                "features": list(self.house.features),
                "roof": {"kind": self.house.roof.kind},
                "adjacency": [
                    {"from": left, "to": right}
                    for left, right in self.house.adjacency
                ],
                "circulation": self.house.circulation,
                "rooms": [
                    {
                        "name": room.name,
                        "type": room.room_type,
                        "width": room.width,
                        "depth": room.depth,
                        "height": room.height,
                        "floor": room.floor,
                        "position": {"x": room.x, "y": room.floor * room.height, "z": room.y},
                        "plan": {"x": room.x, "y": room.y, "width": room.width, "depth": room.depth},
                        "doors": [
                            {
                                "id": door.id,
                                "room_a": door.room_a,
                                "room_b": door.room_b,
                                "x": door.x,
                                "y": door.y,
                                "width": door.width,
                                "side": door.side,
                            }
                            for door in room.doors
                        ],
                        "windows": [
                            {
                                "id": window.id,
                                "room": window.room,
                                "x": window.x,
                                "y": window.y,
                                "width": window.width,
                                "side": window.side,
                            }
                            for window in room.windows
                        ],
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
                y=float(room.get("plan", {}).get("y", room.get("position", {}).get("z", room.get("y", room.get("z", 0.0))))),
                room_type_hint=room.get("type"),
            )
            for room in house_data.get("rooms", [])
        ]
        room_by_name = {room.name: room for room in rooms}
        for room_data in house_data.get("rooms", []):
            room = room_by_name.get(room_data["name"])
            if not room:
                continue
            room.doors = [
                Door(
                    id=door.get("id", f"{room.name}_door"),
                    room_a=door.get("room_a", room.name),
                    room_b=door.get("room_b"),
                    x=float(door.get("x", room.x)),
                    y=float(door.get("y", room.y)),
                    width=float(door.get("width", 0.9)),
                    side=door.get("side", "front"),
                )
                for door in room_data.get("doors", [])
            ]
            room.windows = [
                Window(
                    id=window.get("id", f"{room.name}_window"),
                    room=window.get("room", room.name),
                    x=float(window.get("x", room.x)),
                    y=float(window.get("y", room.y)),
                    width=float(window.get("width", 1.4)),
                    side=window.get("side", "front"),
                )
                for window in room_data.get("windows", [])
            ]
        adjacency = [
            (edge.get("from"), edge.get("to"))
            for edge in house_data.get("adjacency", [])
            if edge.get("from") and edge.get("to")
        ]
        return cls(
            house=House(
                name=house_data.get("name", "house"),
                style=house_data.get("style", "modern"),
                num_floors=int(house_data.get("num_floors", 1) or 1),
                rooms=rooms,
                roof=Roof(house_data.get("roof", {}).get("kind", "flat")),
                adjacency=adjacency,
                circulation=house_data.get("circulation", []),
            ),
            version=data.get("version", "0.1"),
        )
