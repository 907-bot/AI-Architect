from __future__ import annotations

import shutil
import subprocess
import time
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.ollama import prompt_to_toon_with_ollama
from backend.toon.parser import parse_toon
from backend.toon.prompt_meta import infer_features, infer_floor_count, infer_style, is_highrise
from backend.scene_graph.layout import _distribute_rooms_to_floors
from backend.services.render_queue import render_queue


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


def apply_prompt_metadata(scene, prompt: str = "") -> None:
    """Align scene graph with explicit prompt requirements (floors, style, amenities)."""
    if not prompt:
        return
    house = scene.house
    house.features = list({*house.features, *infer_features(prompt)})
    house.style = infer_style(prompt) or house.style
    requested = infer_floor_count(prompt)
    if requested and requested > house.num_floors:
        house.num_floors = requested
    if is_highrise(house.num_floors, house.features):
        house.roof.kind = "flat"
    if requested and requested > 1 and not any(room.floor > 0 for room in house.rooms):
        _distribute_rooms_to_floors(house, house.num_floors)


def assign_floors_to_scene(scene, prompt: str = ""):
    """Helper to assign floor numbers to rooms based on room names or prompt heuristics"""
    apply_prompt_metadata(scene, prompt)
    rooms = scene.house.rooms
    if not rooms:
        return

    # Respect explicit FLOOR / floor assignments from the planner or TOON parser.
    if any(getattr(room, "floor", 0) > 0 for room in rooms):
        return
        
    prompt_lower = prompt.lower() if prompt else ""
    requested = infer_floor_count(prompt_lower)
    if requested and requested > 1:
        _distribute_rooms_to_floors(scene.house, min(requested, scene.house.num_floors or requested))
        return

    is_two_story = any(w in prompt_lower for w in ["2 floor", "2 story", "two floor", "two story", "double story", "2-floor", "2-story"])
    is_three_story = any(w in prompt_lower for w in ["3 floor", "3 story", "three floor", "three story", "3-floor", "3-story"])
    
    assigned_by_name = False
    for room in rooms:
        name_lower = room.name.lower()
        if any(w in name_lower for w in ["ground", "floor0", "floor_0", "level0", "level_0", "f0", "l0"]):
            room.floor = 0
            assigned_by_name = True
        elif any(w in name_lower for w in ["first", "floor1", "floor_1", "level1", "level_1", "f1", "l1"]):
            has_ground = any(any(w in r.name.lower() for w in ["ground", "floor0", "floor_0"]) for r in rooms)
            room.floor = 1 if (has_ground or is_two_story or is_three_story) else 0
            assigned_by_name = True
        elif any(w in name_lower for w in ["second", "floor2", "floor_2", "level2", "level_2", "f2", "l2"]):
            room.floor = 1 if is_two_story else 2
            assigned_by_name = True
        elif any(w in name_lower for w in ["third", "floor3", "floor_3", "level3", "level_3", "f3", "l3"]):
            room.floor = 2
            assigned_by_name = True

    if not assigned_by_name:
        if is_three_story:
            for room in rooms:
                rt = room.room_type
                if rt in ["living_room", "hallway", "kitchen", "dining_room"]:
                    room.floor = 0
                elif rt == "bedroom":
                    room.floor = 1 if "1" in room.name or "one" in room.name else 2
                elif rt == "bathroom":
                    room.floor = 1 if "1" in room.name or "one" in room.name else 2
                else:
                    room.floor = 0
        elif is_two_story:
            for room in rooms:
                rt = room.room_type
                if rt in ["bedroom", "bathroom", "study"]:
                    room.floor = 1
                else:
                    room.floor = 0


@router.post("/generate")
async def generate(body: GenerateRequest):
    planner = "provided-toon"
    if body.toon:
        toon = body.toon
    else:
        toon, planner = prompt_to_toon_with_ollama(body.prompt or "Modern 2 bedroom house", body.ollama_model)
    
    scene = parse_toon(toon)
    assign_floors_to_scene(scene, body.prompt or "")
    style = body.style or infer_style(body.prompt or "") or scene.house.style
    scene.house.style = style
    geometry = compile_scene(scene)
    
    # Export with Blender using enhanced builder
    glb_path = _export_with_enhanced_blender(
        toon,
        scene,
        style,
        body.render_quality or "medium",
        body.prompt or "",
    )
    if not glb_path:
        print("Enhanced Docker Blender not available. Falling back to local Blender.")
        glb_path = _export_with_blender(toon, "house")
    
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["planner"] = planner
    payload["style"] = body.style or "modern"
    payload["render_quality"] = body.render_quality or "medium"
    return payload


@router.post("/edit")
async def edit(body: EditRequest):
    toon, scene, changed = edit_toon(body.toon, body.instruction)
    assign_floors_to_scene(scene, body.instruction)
    geometry = compile_scene(scene)
    
    glb_path = _export_with_enhanced_blender(toon, scene, "modern", "medium")
    if not glb_path:
        print("Enhanced Docker Blender not available. Falling back to local Blender.")
        glb_path = _export_with_blender(toon, "house")
        
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


@router.get("/redis-status")
async def redis_status():
    """Check Redis render queue health, with local queue fallback details."""
    return await render_queue.health_check()


@router.get("/blender-mcp-status")
async def blender_mcp_status():
    """Check the optional Blender HTTP MCP server."""
    url = "http://127.0.0.1:8765/health"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "available": response.status == 200 and payload.get("status") == "ok",
            "url": url,
            "service": payload.get("service"),
            "version": payload.get("version"),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {
            "available": False,
            "url": url,
            "error": str(e),
            "note": "Start with: python -m uvicorn backend.blender.mcp_http_server:app --host 0.0.0.0 --port 8765",
        }


@router.get("/stack-status")
async def stack_status():
    """Aggregate local development component status for the frontend."""
    blender = await blender_status()
    ollama = await ollama_status()
    redis = await redis_status()
    blender_mcp = await blender_mcp_status()
    return {
        "backend": {"available": True},
        "frontend": {"available": True},
        "blender": blender,
        "ollama": ollama,
        "redis": redis,
        "blender_mcp": blender_mcp,
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
            ["docker", "images", "-q", "nytimes/blender:latest"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            # Get version
            version_result = subprocess.run(
                ["docker", "run", "--rm", "nytimes/blender:latest", "blender", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "Blender (Docker)"
            return True, version
    except Exception:
        pass
    return False, ""


def _export_with_enhanced_blender(
    toon: str,
    scene,
    style: str = "modern",
    quality: str = "medium",
    prompt: str = "",
) -> str | None:
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
    scene_dict['render_quality'] = quality
    scene_dict['prompt'] = prompt
    house_dict = scene_dict.get('house', scene_dict)
    house_dict['features'] = list(getattr(scene.house, 'features', []) or infer_features(prompt))
    house_dict['num_floors'] = getattr(scene.house, 'num_floors', 1)
    
    # Ensure floors information is present
    rooms = scene_dict.get('house', scene_dict).get('rooms', [])
    if rooms:
        for i, room in enumerate(rooms):
            if 'floor' not in room:
                name_lower = room.get('name', '').lower()
                pos_y = room.get('position', {}).get('y', 0)
                if pos_y > 1.0:
                    room['floor'] = int(pos_y // 3.0)
                elif any(w in name_lower for w in ["first", "floor1", "floor_1", "level1", "level_1", "f1", "l1"]):
                    room['floor'] = 1
                elif any(w in name_lower for w in ["second", "floor2", "floor_2", "level2", "level_2", "f2", "l2"]):
                    room['floor'] = 1
                elif any(w in name_lower for w in ["third", "floor3", "floor_3", "level3", "level_3", "f3", "l3"]):
                    room['floor'] = 2
                else:
                    room['floor'] = 0
    
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
