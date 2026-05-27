from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp.server import FastMCP

from backend.blender.pipeline import generate_house as blender_generate_house
from backend.toon.models import SceneGraph


mcp_server = FastMCP("ai-architect-blender", "0.1.0")


@mcp_server.tool()
def generate_house(scene_graph: dict[str, Any], filename: str = "house.glb") -> dict[str, Any]:
    scene = SceneGraph.from_dict(scene_graph)
    output = Path("exports") / filename
    return {"glb_path": blender_generate_house(scene, output)}


@mcp_server.tool()
def create_room(scene_graph: dict[str, Any], room_name: str) -> dict[str, Any]:
    scene = SceneGraph.from_dict(scene_graph)
    rooms = [room.name for room in scene.house.rooms]
    if room_name not in rooms:
        return {"status": "error", "detail": f"Room {room_name!r} not found", "rooms": rooms}
    return {"status": "ok", "room": room_name}


@mcp_server.tool()
def create_roof(scene_graph: dict[str, Any]) -> dict[str, Any]:
    scene = SceneGraph.from_dict(scene_graph)
    return {"status": "ok", "roof": scene.house.roof.kind}


@mcp_server.tool()
def export_glb(scene_graph: dict[str, Any], filename: str = "house.glb") -> dict[str, Any]:
    return generate_house(scene_graph, filename)
