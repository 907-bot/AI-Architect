from __future__ import annotations

import re

from backend.toon.models import House, Room, Roof, SceneGraph


class ToonParseError(ValueError):
    pass


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?x\d+(?:\.\d+)?|\d+(?:\.\d+)?|[{}]")


class _Parser:
    def __init__(self, text: str):
        self.tokens = TOKEN_RE.findall(text)
        self.index = 0

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
            elif token == "ROOF":
                house.roof = Roof(kind=self._identifier())
            else:
                raise ToonParseError(f"Unexpected token {token!r}")
        self._expect("}")
        self._layout_rooms(house.rooms)
        return SceneGraph(house=house)

    def _room(self) -> Room:
        name = self._identifier()
        width = 4.0
        depth = 4.0
        height = 3.0
        self._expect("{")
        while not self._peek("}"):
            key = self._next()
            if key == "size":
                width, depth = self._dimensions(self._next())
            elif key == "height":
                height = float(self._next())
            else:
                raise ToonParseError(f"Unsupported ROOM property {key!r}")
        self._expect("}")
        return Room(name=name, width=width, depth=depth, height=height)

    def _layout_rooms(self, rooms: list[Room]) -> None:
        living_rooms = [room for room in rooms if room.room_type == "living_room"]
        other_rooms = [room for room in rooms if room.room_type != "living_room"]

        if living_rooms and other_rooms:
            living = living_rooms[0]
            living.x = 0.0
            living.z = -living.depth / 2

            cursor_x = 0.0
            for room in other_rooms:
                room.x = cursor_x + room.width / 2
                room.z = room.depth / 2 + 0.4
                cursor_x += room.width

            total_width = cursor_x
            for room in other_rooms:
                room.x -= total_width / 2

            for extra in living_rooms[1:]:
                extra.x = living.x + living.width + extra.width / 2
                extra.z = living.z
            return

        cursor_x = 0.0
        max_depth = max((room.depth for room in rooms), default=0.0)
        for room in rooms:
            room.x = cursor_x + room.width / 2
            room.z = max_depth / 2
            cursor_x += room.width

        total_width = cursor_x
        for room in rooms:
            room.x -= total_width / 2
            room.z -= max_depth / 2

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
