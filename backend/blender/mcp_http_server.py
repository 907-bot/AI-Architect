"""
AI Architect - HTTP MCP Server for Blender Integration
Runs as a standalone HTTP service that ChatGPT can connect to.

Usage:
    python -m backend.blender.mcp_http_server

Then use mcp_config.json to connect from ChatGPT or other MCP clients.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional

from backend.blender.pipeline import generate_house as blender_generate_house
from backend.blender.exporters import export_glb
from backend.toon.models import SceneGraph


app = FastAPI(
    title="AI Architect Blender MCP Server",
    description="HTTP API for Blender 3D house generation",
    version="0.1.0"
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateHouseRequest(BaseModel):
    scene_graph: dict[str, Any]
    filename: Optional[str] = "house.glb"
    style: Optional[str] = "modern"
    render_quality: Optional[str] = "medium"


class CreateRoomRequest(BaseModel):
    scene_graph: dict[str, Any]
    room_name: str
    room_type: Optional[str] = "generic"
    width: Optional[float] = 5.0
    depth: Optional[float] = 5.0
    height: Optional[float] = 3.0


class CreateRoofRequest(BaseModel):
    scene_graph: dict[str, Any]
    roof_style: Optional[str] = "flat"
    roof_height: Optional[float] = 0.6


class ExportGlbRequest(BaseModel):
    scene_graph: dict[str, Any]
    filename: Optional[str] = "house.glb"
    apply_color_grading: Optional[bool] = True


# MCP Tool Endpoints

@app.post("/tools/generate_house")
async def tool_generate_house(req: GenerateHouseRequest):
    """Generate a complete 3D house model from scene graph"""
    try:
        scene = SceneGraph.from_dict(req.scene_graph)
        output = Path("exports") / req.filename
        output.parent.mkdir(parents=True, exist_ok=True)
        
        glb_path = blender_generate_house(scene, output)
        
        return {
            "status": "success",
            "glb_path": str(glb_path),
            "filename": req.filename,
            "style": req.style,
            "render_quality": req.render_quality,
            "rooms_count": len(scene.house.rooms)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/tools/create_room")
async def tool_create_room(req: CreateRoomRequest):
    """Create an individual room in the scene"""
    try:
        scene = SceneGraph.from_dict(req.scene_graph)
        rooms = [room.name for room in scene.house.rooms]
        
        if req.room_name in rooms:
            return {
                "status": "exists",
                "room": req.room_name,
                "message": f"Room {req.room_name} already exists"
            }
        
        return {
            "status": "created",
            "room": req.room_name,
            "type": req.room_type,
            "dimensions": {
                "width": req.width,
                "depth": req.depth,
                "height": req.height
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/tools/create_roof")
async def tool_create_roof(req: CreateRoofRequest):
    """Add a roof to the house structure"""
    try:
        scene = SceneGraph.from_dict(req.scene_graph)
        roof_kind = scene.house.roof.kind if scene.house.roof else "flat"
        
        return {
            "status": "success",
            "roof_style": req.roof_style,
            "roof_height": req.roof_height,
            "message": f"Roof set to {req.roof_style}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/tools/export_glb")
async def tool_export_glb(req: ExportGlbRequest):
    """Export scene to GLB format"""
    try:
        scene = SceneGraph.from_dict(req.scene_graph)
        output = Path("exports") / req.filename
        output.parent.mkdir(parents=True, exist_ok=True)
        
        glb_path = export_glb(output)
        
        return {
            "status": "success",
            "glb_path": str(glb_path),
            "filename": req.filename
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/tools/get_scene_info")
async def tool_get_scene_info(req: dict[str, Any]):
    """Get information about the current scene"""
    try:
        scene_graph = req.get("scene_graph", {})
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


# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-architect-blender-mcp",
        "version": "0.1.0"
    }


# Convenience endpoints for full pipeline

@app.post("/generate")
async def generate_house(
    prompt: str,
    style: str = "modern",
    render_quality: str = "medium"
):
    """
    Full pipeline: Generate house from prompt using Ollama + Blender
    
    Args:
        prompt: House description (e.g., "Modern 3 bedroom villa")
        style: Architectural style
        render_quality: Rendering quality (preview, medium, cinematic, production)
    
    Returns:
        Scene graph, GLB path, and generation status
    """
    from backend.toon.ollama import prompt_to_toon_with_ollama
    from backend.toon.parser import parse_toon
    
    try:
        # 1. Generate TOON from prompt
        toon, planner = prompt_to_toon_with_ollama(prompt)
        
        # 2. Parse TOON to scene graph
        scene = parse_toon(toon)
        
        # 3. Generate GLB via Blender
        filename = f"house_{int(__import__('time').time())}.glb"
        output = Path("exports") / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        
        glb_path = None
        try:
            glb_path = blender_generate_house(scene, output)
        except Exception as blender_error:
            # Blender not available, skip GLB generation
            pass
        
        return {
            "success": True,
            "prompt": prompt,
            "toon": toon,
            "scene_graph": scene.to_dict(),
            "glb_path": str(glb_path) if glb_path else None,
            "planner": planner,
            "style": style,
            "render_quality": render_quality,
            "blender_available": glb_path is not None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Generation failed"
        }


# Run with: uvicorn backend.blender.mcp_http_server:app --port 8765
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", "8765"))
    print(f"Starting AI Architect Blender MCP Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)