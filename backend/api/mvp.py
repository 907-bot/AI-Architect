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


@router.get("/ollama-status")
async def ollama_status():
    """Check if Ollama is available and working"""
    from backend.toon.ollama import check_ollama_connection
    
    available, model, error = check_ollama_connection()
    
    if available:
        return {
            "available": True,
            "model": model or "llama3.1",
            "version": "Ollama connected",
            "note": "Local AI is ready for TOON generation"
        }
    else:
        return {
            "available": False,
            "model": None,
            "error": error or "Ollama not running",
            "note": "Using deterministic fallback. Install Ollama: ollama serve && ollama pull llama3.1"
        }


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
    """Export using enhanced Blender builder with multi-floor support"""
    
    # Find Blender executable (local first, then Docker)
    blender_bin = _find_blender()
    use_docker = False
    
    if not blender_bin:
        # Check Docker Blender availability
        docker_available, _ = _check_docker_blender()
        if docker_available:
            use_docker = True
        else:
            print("Blender not available - using procedural fallback")
            return None
    else:
        print(f"Using local Blender: {blender_bin}")
    
    # Save scene data for Blender
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    toon_filename = f"house_{stamp}.toon"
    toon_path = EXPORTS_DIR / toon_filename
    glb_filename = f"house_{stamp}.glb"
    
    scene_dict = scene.to_dict()
    scene_dict['style'] = style
    
    # Ensure floors information is present
    rooms = scene_dict.get('house', scene_dict).get('rooms', [])
    if rooms:
        for i, room in enumerate(rooms):
            if 'floor' not in room:
                z_pos = room.get('position', {}).get('z', room.get('z', 0))
                room['floor'] = int(z_pos // 3.5) if z_pos > 3 else 0
    
    with open(toon_path, 'w') as f:
        json.dump(scene_dict, f)

    # Import and use the enhanced builder
    try:
        from backend.toon.blender_builder import build_enhanced_house
        
        if use_docker:
            # For Docker, we need to run Blender with the script
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{EXPORTS_DIR}:/exports",
                "-v", f"{ROOT}:/workspace",
                "-w", "/workspace",
                "nytimes/blender:latest",
                "blender", "--background",
                "--python", "backend/toon/blender_builder.py",
                "--",
                str(toon_path),
                str(EXPORTS_DIR / glb_filename)
            ]
            result = subprocess.run(docker_cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        else:
            # Local Blender
            result = subprocess.run(
                [blender_bin, "--background",
                 "--python", str(ROOT / "backend" / "toon" / "blender_builder.py"),
                 "--", str(toon_path), str(EXPORTS_DIR / glb_filename)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
        
        if result.returncode != 0:
            print(f"Blender error: {result.stderr[:500] if result.stderr else 'Unknown'}")
            return None
        
        print(result.stdout)
        
    except ImportError as e:
        print(f"Could not import blender_builder: {e}")
        return None
    except Exception as e:
        print(f"Blender execution error: {e}")
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
