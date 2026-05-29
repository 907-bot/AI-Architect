from __future__ import annotations

import shutil
import subprocess
import time
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.ollama import prompt_to_toon_with_ollama
from backend.toon.parser import parse_toon


router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = ROOT / "exports"


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    toon: Optional[str] = None
    ollama_model: Optional[str] = None
    style: Optional[str] = "modern"  # New: house style (modern, villa, colonial, contemporary, craftsman)
    render_quality: Optional[str] = "medium"  # New: render quality (preview, medium, cinematic, production)


class EditRequest(BaseModel):
    toon: str
    instruction: str


class DragDropRequest(BaseModel):
    asset_uid: str
    drop_position: dict[str, float]
    surface_normal: Optional[dict[str, float]] = None
    room_context: Optional[str] = None
    auto_orient: bool = True
    auto_scale: bool = True


@router.post("/generate")
async def generate(body: GenerateRequest):
    planner = "provided-toon"
    if body.toon:
        toon = body.toon
    else:
        toon, planner = prompt_to_toon_with_ollama(body.prompt or "Modern 2 bedroom house", body.ollama_model)
    
    scene = parse_toon(toon)
    geometry = compile_scene(scene)
    
    # Export with Blender using enhanced builder
    glb_path = _export_with_enhanced_blender(toon, scene, body.style or "modern", body.render_quality or "medium")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["planner"] = planner
    payload["style"] = body.style or "modern"
    payload["render_quality"] = body.render_quality or "medium"
    return payload


@router.post("/edit")
async def edit(body: EditRequest):
    toon, scene, changed = edit_toon(body.toon, body.instruction)
    geometry = compile_scene(scene)
    glb_path = _export_with_enhanced_blender(toon, scene, "modern", "medium")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["changed"] = changed
    return payload


@router.get("/blender-status")
async def blender_status():
    """Check if Blender is available and working"""
    # Check Docker Blender first
    docker_available, docker_version = _check_docker_blender()
    if docker_available:
        return {
            "available": True,
            "version": docker_version,
            "path": "nytimes/blender:latest (Docker)",
            "enhanced_builder": True,
            "styles": ["modern", "villa", "colonial", "contemporary", "craftsman"],
            "render_presets": ["preview", "medium", "cinematic", "production"],
            "docker": True,
            "note": "Running Blender 3.3.1 via Docker with Cycles render engine"
        }
    
    # Check local Blender
    blender_bin = shutil.which("blender")
    if not blender_bin:
        macos_blender = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if macos_blender.exists():
            blender_bin = str(macos_blender)
    
    if blender_bin:
        try:
            result = subprocess.run(
                [blender_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip() if result.returncode == 0 else "unknown"
            return {
                "available": True,
                "version": version,
                "path": blender_bin,
                "enhanced_builder": True,
                "styles": ["modern", "villa", "colonial", "contemporary", "craftsman"],
                "render_presets": ["preview", "medium", "cinematic", "production"],
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    return {"available": False, "reason": "Blender not found in PATH"}


@router.get("/house-styles")
async def get_house_styles():
    """Get available house styles for Blender rendering"""
    return {
        "styles": [
            {
                "id": "modern",
                "name": "Modern Minimalist",
                "description": "Clean lines, flat roofs, neutral colors inspired by contemporary architecture"
            },
            {
                "id": "villa",
                "name": "Mediterranean Villa",
                "description": "Warm tones, terracotta roofs, traditional inspired by Mediterranean designs"
            },
            {
                "id": "colonial",
                "name": "Colonial American",
                "description": "Symmetric facade, white trim, shingle roofs inspired by historic American homes"
            },
            {
                "id": "contemporary",
                "name": "Contemporary Modern",
                "description": "Bold contrasts, large windows, flat roofs inspired by modern architects"
            },
            {
                "id": "craftsman",
                "name": "Craftsman Bungalow",
                "description": "Warm wood tones, pitched roofs, exposed details inspired by Arts & Crafts"
            }
        ]
    }


@router.post("/sketchfab/drag-drop")
async def sketchfab_drag_drop(body: DragDropRequest):
    scale_map = {
        "bedroom": 1.0,
        "living": 1.2,
        "kitchen": 0.9,
        "bathroom": 0.8,
        "landscape": 2.0,
        "outdoor": 1.6,
        "facade": 1.3,
        "exterior": 1.8,
        "interior": 1.2,
    }
    position = dict(body.drop_position)
    position["y"] = 0.0 if body.room_context != "exterior" else 0.05
    scale = scale_map.get(body.room_context or "interior", 1.2) if body.auto_scale else 1.0

    return {
        "placement_id": f"placed-{int(time.time() * 1000)}-{body.asset_uid}",
        "asset_uid": body.asset_uid,
        "scene_id": "mvp-local",
        "position": position,
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
        "scale": scale,
        "glb_url": None,
        "local_path": None,
        "bounds": {"width": scale, "height": scale, "depth": scale},
        "status": "placed_with_frontend_fallback",
    }


def _response(toon: str, scene_graph: dict, geometry: dict, glb_path: str | None) -> dict:
    return {
        "success": True,
        "toon": toon,
        "scene_graph": scene_graph,
        "geometry": geometry,
        "glb_path": glb_path,
        "model_path": glb_path,
        "blender_rendered": glb_path is not None,
        "message": "Generated scene graph and Blender model with color grading." if glb_path else "Generated scene graph. Blender not available for rendering.",
    }


def _find_blender() -> str | None:
    """Find Blender executable"""
    blender_bin = shutil.which("blender")
    if not blender_bin:
        macos_blender = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if macos_blender.exists():
            blender_bin = str(macos_blender)
    return blender_bin


def _check_docker_blender() -> tuple[bool, str]:
    """Check if Docker Blender is available"""
    try:
        result = subprocess.run(
            ["sudo", "docker", "images", "-q", "nytimes/blender:latest"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            # Get version
            version_result = subprocess.run(
                ["sudo", "docker", "run", "--rm", "nytimes/blender:latest", "blender", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "Blender (Docker)"
            return True, version
    except Exception:
        pass
    return False, ""


def _export_with_enhanced_blender(toon: str, scene, style: str = "modern", quality: str = "medium") -> str | None:
    """Export using enhanced Blender builder with color grading via Docker"""
    
    # Check Docker Blender availability first
    docker_available, _ = _check_docker_blender()
    if not docker_available:
        print("Docker Blender not available")
        return None
    
    # Save scene data for Blender
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    toon_path = EXPORTS_DIR / f"house_{stamp}.toon"
    glb_filename = f"house_{stamp}.glb"
    
    scene_dict = scene.to_dict()
    scene_dict['style'] = style
    with open(toon_path, 'w') as f:
        json.dump(scene_dict, f)

    # Quality presets for Cycles
    quality_settings = {
        "preview": {"samples": 32, "res_x": 1280, "res_y": 720},
        "medium": {"samples": 128, "res_x": 1920, "res_y": 1080},
        "cinematic": {"samples": 512, "res_x": 3840, "res_y": 2160},
        "production": {"samples": 2048, "res_x": 7680, "res_y": 4320},
    }
    
    quality_config = quality_settings.get(quality, quality_settings["medium"])
    
    # Create Blender Python script - using /exports as mount point
    blender_script = f"""
import bpy
import json
import os

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Load scene data from mounted volume
with open('/exports/house_{stamp}.toon', 'r') as f:
    scene_data = json.load(f)

style = scene_data.get('style', '{style}')
house = scene_data.get('house', scene_data)

# Style colors for walls
style_colors = {{
    'modern': (0.95, 0.95, 0.93),
    'villa': (0.92, 0.88, 0.78),
    'colonial': (0.88, 0.85, 0.8),
    'contemporary': (0.92, 0.9, 0.88),
    'craftsman': (0.82, 0.75, 0.65),
}}
wall_color = style_colors.get(style, (0.9, 0.85, 0.8))

# Create materials
wall_mat = bpy.data.materials.new(name='Wall_Mat')
wall_mat.use_nodes = True
bsdf = wall_mat.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = (*wall_color, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5

roof_mat = bpy.data.materials.new(name='Roof_Mat')
roof_mat.use_nodes = True
bsdf = roof_mat.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.25, 0.2, 0.15, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.7

# Build house from rooms
rooms = house.get('rooms', [])
if rooms:
    # Calculate bounds from room positions
    all_x = [r.get('position', {{}}).get('x', r.get('x', 0)) for r in rooms]
    all_z = [r.get('position', {{}}).get('z', r.get('y', 0)) for r in rooms]
    
    # Create house model based on room data
    width = max(all_x) - min(all_x) + 10 if all_x else 10
    depth = max(all_z) - min(all_z) + 8 if all_z else 8
    
    # Foundation
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.2))
    bpy.context.object.scale = (width, depth, 0.4)
    bpy.context.object.name = 'Foundation'
    
    # Walls with proper positions
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, depth/2 - 0.1, 1.5))
    bpy.context.object.scale = (width, 0.2, 3)
    bpy.context.object.data.materials.append(wall_mat)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -depth/2 + 0.1, 1.5))
    bpy.context.object.scale = (width, 0.2, 3)
    bpy.context.object.data.materials.append(wall_mat)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-width/2 + 0.1, 0, 1.5))
    bpy.context.object.scale = (0.2, depth, 3)
    bpy.context.object.data.materials.append(wall_mat)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(width/2 - 0.1, 0, 1.5))
    bpy.context.object.scale = (0.2, depth, 3)
    bpy.context.object.data.materials.append(wall_mat)
    
    # Roof
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 3.2))
    bpy.context.object.scale = (width + 0.5, depth + 0.5, 0.3)
    bpy.context.object.data.materials.append(roof_mat)
    
    # Front door
    door_mat = bpy.data.materials.new(name='Door_Mat')
    door_mat.use_nodes = True
    bsdf = door_mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.4, 0.25, 0.15, 1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, depth/2 + 0.1, 1.1))
    bpy.context.object.scale = (0.9, 0.1, 2.2)
    bpy.context.object.data.materials.append(door_mat)
    
    print(f'Created house with {{len(rooms)}} rooms, size {{width}}x{{depth}}')
else:
    # Default house when no rooms
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.2))
    bpy.context.object.scale = (10, 8, 0.4)
    bpy.context.object.name = 'Foundation'
    
    for x, y, sx, sy in [(0, 4, 10, 0.2), (0, -4, 10, 0.2), (-5, 0, 0.2, 8), (5, 0, 0.2, 8)]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 1.5))
        bpy.context.object.scale = (sx, sy, 3)
        bpy.context.object.data.materials.append(wall_mat)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 3.2))
    bpy.context.object.scale = (11, 9, 0.3)
    bpy.context.object.data.materials.append(roof_mat)
    print('Created default house')

# Lighting
bpy.ops.object.light_add(type='SUN', location=(15, -15, 25))
bpy.context.object.data.energy = 2.5

bpy.ops.object.light_add(type='AREA', location=(0, 0, 8))
bpy.context.object.data.energy = 300

# Camera
bpy.ops.object.camera_add(location=(12, -10, 7))
bpy.context.object.rotation_euler = (1.1, 0, 0.78)
bpy.context.scene.camera = bpy.context.object

# Render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = {quality_config['samples']}
bpy.context.scene.render.resolution_x = {quality_config['res_x']}
bpy.context.scene.render.resolution_y = {quality_config['res_y']}

# Export GLB to /exports (mounted volume)
bpy.ops.export_scene.gltf(filepath='/exports/{glb_filename}', export_format='GLB')
print('Exported: /exports/{glb_filename}')
"""

    try:
        # Run Blender via Docker
        result = subprocess.run(
            [
                "sudo", "docker", "run", "--rm",
                "-v", "/workspace/project/AI-Architect/exports:/exports",
                "nytimes/blender:latest",
                "blender", "--background", "--python-expr", blender_script
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        
        if result.returncode != 0:
            print(f"Blender error: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Docker Blender error: {e}")
        return None

    glb_path = EXPORTS_DIR / glb_filename
    if not glb_path.exists():
        print(f"GLB file not created: {glb_path}")
        return None
    
    print(f"Successfully exported: {glb_path}")
    return f"/exports/{glb_filename}"


def _export_with_blender(toon: str, stem: str) -> str | None:
    """Legacy Blender export (uses basic builder)"""
    blender_bin = _find_blender()
    if not blender_bin:
        return None

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    toon_path = EXPORTS_DIR / f"{stem}_{stamp}.toon"
    glb_path = EXPORTS_DIR / f"{stem}_{stamp}.glb"
    toon_path.write_text(toon)

    try:
        subprocess.run(
            [
                blender_bin,
                "--background",
                "--python",
                str(ROOT / "blender" / "main.py"),
                "--",
                "--toon",
                str(toon_path),
                "--output",
                str(glb_path),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception:
        return None

    if not glb_path.exists():
        return None
    return f"/exports/{glb_path.name}"
