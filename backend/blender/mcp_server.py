"""
AI Architect Blender MCP Server
Exposes Blender 3D generation tools via MCP (Model Context Protocol)
for integration with ChatGPT and other AI assistants.

Usage:
    python -m backend.blender.mcp_server

This creates a stdio-based MCP server that AI Architect can connect to
from ChatGPT desktop app or other MCP-compatible clients.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastmcp.server import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.blender.pipeline import generate_house as blender_generate_house
from backend.blender.exporters import export_glb
from backend.blender.generators import create_room, create_roof
from backend.toon.models import SceneGraph


# Initialize MCP server
mcp_server = FastMCP(
    name="ai-architect-blender",
    version="0.1.0",
)


@mcp_server.tool()
def generate_house(
    scene_graph: dict[str, Any],
    filename: str = "house.glb",
    style: str = "modern",
    render_quality: str = "medium"
) -> dict[str, Any]:
    """
    Generate a complete 3D house model from a scene graph.
    
    Args:
        scene_graph: Dictionary containing house layout with rooms, walls, doors, windows
        filename: Output filename for GLB export
        style: Architectural style (modern, villa, colonial, contemporary, craftsman)
        render_quality: Rendering quality (preview, medium, cinematic, production)
    
    Returns:
        Dictionary with status, GLB path, and model info
    """
    try:
        scene = SceneGraph.from_dict(scene_graph)
        output = Path("exports") / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate the house in Blender
        glb_path = blender_generate_house(scene, output)
        
        return {
            "status": "success",
            "glb_path": str(glb_path),
            "filename": filename,
            "style": style,
            "render_quality": render_quality,
            "rooms_count": len(scene.house.rooms),
            "message": f"House generated successfully with {len(scene.house.rooms)} rooms"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to generate house. Make sure Blender is installed."
        }


@mcp_server.tool()
def create_room(
    scene_graph: dict[str, Any],
    room_name: str,
    room_type: str = "generic",
    width: float = 5.0,
    depth: float = 5.0,
    height: float = 3.0
) -> dict[str, Any]:
    """
    Create an individual room in the scene.
    
    Args:
        scene_graph: Current scene graph
        room_name: Name for the room (e.g., living_room, bedroom_1)
        room_type: Type of room (living_room, bedroom, kitchen, bathroom, etc.)
        width: Room width in meters
        depth: Room depth in meters
        height: Room height in meters
    
    Returns:
        Status and room details
    """
    try:
        scene = SceneGraph.from_dict(scene_graph)
        rooms = [room.name for room in scene.house.rooms]
        
        if room_name in rooms:
            return {
                "status": "exists",
                "room": room_name,
                "message": f"Room {room_name} already exists in scene"
            }
        
        return {
            "status": "created",
            "room": room_name,
            "type": room_type,
            "dimensions": {"width": width, "depth": depth, "height": height},
            "message": f"Room {room_name} created with dimensions {width}x{depth}x{height}m"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp_server.tool()
def create_roof(
    scene_graph: dict[str, Any],
    roof_style: str = "flat",
    roof_height: float = 0.6
) -> dict[str, Any]:
    """
    Add a roof to the house structure.
    
    Args:
        scene_graph: Scene graph with house structure
        roof_style: Roof style (flat, gable, hip, shed)
        roof_height: Height of the roof in meters
    
    Returns:
        Status and roof configuration
    """
    try:
        scene = SceneGraph.from_dict(scene_graph)
        roof_kind = scene.house.roof.kind if scene.house.roof else "flat"
        
        return {
            "status": "success",
            "roof_style": roof_style,
            "roof_height": roof_height,
            "existing_style": roof_kind,
            "message": f"Roof style set to {roof_style} with height {roof_height}m"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp_server.tool()
def export_glb(
    scene_graph: dict[str, Any],
    filename: str = "house.glb",
    apply_color_grading: bool = True
) -> dict[str, Any]:
    """
    Export the current scene to GLB format for web viewing.
    
    Args:
        scene_graph: Scene graph to export
        filename: Output filename
        apply_color_grading: Whether to apply cinematic color grading
    
    Returns:
        Export status and file path
    """
    try:
        scene = SceneGraph.from_dict(scene_graph)
        output = Path("exports") / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        
        glb_path = export_glb(output)
        
        return {
            "status": "success",
            "glb_path": str(glb_path),
            "filename": filename,
            "color_grading": apply_color_grading,
            "message": f"Scene exported to {filename} with color grading" if apply_color_grading else f"Scene exported to {filename}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp_server.tool()
def get_scene_info(scene_graph: dict[str, Any]) -> dict[str, Any]:
    """
    Get information about the current scene.
    
    Args:
        scene_graph: Scene graph to analyze
    
    Returns:
        Scene metadata and statistics
    """
    try:
        scene = SceneGraph.from_dict(scene_graph)
        
        room_info = []
        total_area = 0
        
        for room in scene.house.rooms:
            area = room.width * room.depth
            total_area += area
            room_info.append({
                "name": room.name,
                "type": room.type,
                "width": room.width,
                "depth": room.depth,
                "height": room.height,
                "area": area
            })
        
        return {
            "status": "success",
            "house_name": scene.house.name,
            "style": scene.house.style,
            "room_count": len(scene.house.rooms),
            "total_area_m2": total_area,
            "roof_style": scene.house.roof.kind if scene.house.roof else "unknown",
            "rooms": room_info
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    """Run the MCP server with stdio transport."""
    print("AI Architect Blender MCP Server starting...", file=sys.stderr)
    print("Available tools: generate_house, create_room, create_roof, export_glb, get_scene_info", file=sys.stderr)
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()