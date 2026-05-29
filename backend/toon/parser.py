from __future__ import annotations

import re

from backend.toon.models import House, Room, Roof, SceneGraph
from backend.scene_graph.layout import optimize_layout


class ToonParseError(ValueError):
    pass


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?x\d+(?:\.\d+)?|\d+(?:\.\d+)?|[{}]")


class _Parser:
    def __init__(self, text: str):
        self.tokens = TOKEN_RE.findall(text)
        self.index = 0
        self.current_floor = 0

    def parse(self) -> SceneGraph:
        self._expect("HOUSE")
        name = self._identifier()
        house = House(name=name)
        self._expect("{")
        while not self._peek("}"):
            token = self._next()
            if token == "STYLE":
                house.style = self._identifier()
            elif token == "ROOM":
                house.rooms.append(self._room())
            elif token == "FLOOR":
                self.current_floor = int(self._next())
            elif token == "FLOORS":
                house.num_floors = int(self._next())
            elif token == "ADJACENT":
                left = self._identifier()
                right = self._identifier()
                house.adjacency.append((left, right))
            elif token == "ROOF":
                house.roof = Roof(kind=self._identifier())
            else:
                raise ToonParseError(f"Unexpected token {token!r}")
        self._expect("}")
        optimize_layout(house)
        return SceneGraph(house=house)

    def _room(self) -> Room:
        name = self._identifier()
        room_type = None
        width = 4.0
        depth = 4.0
        height = 3.0
        x = None
        y = None
        floor = self.current_floor
        self._expect("{")
        while not self._peek("}"):
            key = self._next()
            if key == "size":
                width, depth = self._dimensions(self._next())
            elif key == "height":
                height = float(self._next())
            elif key == "type":
                room_type = self._identifier()
            elif key in {"position", "at"}:
                x, y = self._dimensions(self._next())
            elif key == "floor":
                floor = int(self._next())
            else:
                raise ToonParseError(f"Unsupported ROOM property {key!r}")
        self._expect("}")
        return Room(
            name=name,
            width=width,
            depth=depth,
            height=height,
            x=x or 0.0,
            y=y or 0.0,
            room_type_hint=room_type,
            floor=floor,
        )

    def _dimensions(self, value: str) -> tuple[float, float]:
        if "x" not in value:
            raise ToonParseError(f"Expected dimensions like 8x6, got {value!r}")
        width, depth = value.split("x", 1)
        return float(width), float(depth)

    def _identifier(self) -> str:
        token = self._next()
        if token in {"{", "}"}:
            raise ToonParseError(f"Expected identifier, got {token!r}")
        return token

    def _peek(self, token: str) -> bool:
        return self.index < len(self.tokens) and self.tokens[self.index] == token

    def _expect(self, token: str) -> None:
        found = self._next()
        if found != token:
            raise ToonParseError(f"Expected {token!r}, got {found!r}")

    def _next(self) -> str:
        if self.index >= len(self.tokens):
            raise ToonParseError("Unexpected end of TOON")
        token = self.tokens[self.index]
        self.index += 1
        return token


def parse_toon(text: str) -> SceneGraph:
    return _Parser(text).parse()
