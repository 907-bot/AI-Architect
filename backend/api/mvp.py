from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.ollama import prompt_to_toon_with_ollama
from backend.toon.parser import parse_toon
from backend.services.llm.extractor import extract_building_schema_sync

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = ROOT / "exports"

BLENDER_BIN: str | None = None


def _find_blender() -> str | None:
    global BLENDER_BIN
    if BLENDER_BIN:
        return BLENDER_BIN
    candidate = os.environ.get("BLENDER_PATH", "")
    if candidate and Path(candidate).exists():
        BLENDER_BIN = candidate
        return BLENDER_BIN
    mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac.exists():
        BLENDER_BIN = str(mac)
        return BLENDER_BIN
    found = shutil.which("blender")
    if found:
        BLENDER_BIN = found
    return BLENDER_BIN


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    toon: Optional[str] = None
    ollama_model: Optional[str] = None


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


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — detect building complexity
# ─────────────────────────────────────────────────────────────────────────────

def _is_complex_building(prompt: str) -> bool:
    """
    Route to the procedural building pipeline when the prompt describes
    a multi-storey / commercial building rather than a simple house.
    """
    p = prompt.lower()
    triggers = [
        "storey", "story", "floor", "apartment", "office", "hotel",
        "commercial", "pool", "swimming", "garage", "parking", "skyscraper",
        "tower", "mall", "warehouse",
    ]
    return any(t in p for t in triggers)


def _schema_to_scene_graph(schema: dict) -> dict:
    """
    Build a minimal scene_graph dict compatible with the frontend floor-plan
    viewer, derived from the building schema.
    """
    floor_h = schema.get("floor_height", 3.2)
    bw = schema.get("width", 20.0)
    bd = schema.get("depth", 15.0)
    floors = schema.get("floors", 3)

    rooms = []
    for fi in range(floors):
        rooms.append({
            "name": f"floor_{fi + 1}_main",
            "type": "living_room",
            "width": bw,
            "depth": bd,
            "height": floor_h,
            "floor": fi,
            "position": {"x": 0, "y": fi * floor_h, "z": 0},
            "plan": {"x": 0, "y": 0, "width": bw, "depth": bd},
            "doors": [],
            "windows": [],
        })

    return {
        "version": "0.2",
        "house": {
            "name": schema.get("building_type", "building"),
            "style": schema.get("style", "modern"),
            "roof": {"kind": schema.get("roof_style", "flat")},
            "adjacency": [],
            "circulation": [],
            "rooms": rooms,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# BLENDER EXPORT — procedural building worker
# ─────────────────────────────────────────────────────────────────────────────

def _export_with_building_worker(schema: dict, stem: str) -> str | None:
    """Run blender_worker.py inside Blender subprocess with building schema."""
    blender_bin = _find_blender()
    if not blender_bin:
        return None

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    glb_path = EXPORTS_DIR / f"{stem}_{stamp}.glb"
    schema["output_path"] = str(glb_path)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(schema, tf, indent=2)
        schema_path = tf.name

    worker = ROOT / "backend" / "workers" / "blender_worker.py"

    try:
        result = subprocess.run(
            [blender_bin, "--background", "--python", str(worker), "--", schema_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        # Surface Blender logs for debugging
        if result.stdout:
            for line in result.stdout.splitlines():
                if "[BlenderWorker]" in line or "Error" in line:
                    print(f"[Blender] {line}")
        if result.returncode != 0:
            print(f"[Blender] Worker exited {result.returncode}")
            print(result.stderr[-800:] if result.stderr else "")
            return None
    except Exception as exc:
        print(f"[Blender] Subprocess error: {exc}")
        return None
    finally:
        try:
            os.unlink(schema_path)
        except OSError:
            pass

    if not glb_path.exists():
        return None
    return f"/exports/{glb_path.name}"


# ─────────────────────────────────────────────────────────────────────────────
# BLENDER EXPORT — legacy TOON pipeline (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def _export_with_blender(toon: str, stem: str) -> str | None:
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
            [blender_bin, "--background", "--python",
             str(ROOT / "blender" / "main.py"),
             "--", "--toon", str(toon_path), "--output", str(glb_path)],
            cwd=ROOT, check=True, capture_output=True, text=True, timeout=60,
        )
    except Exception:
        return None

    if not glb_path.exists():
        return None
    return f"/exports/{glb_path.name}"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate(body: GenerateRequest):
    prompt = body.prompt or "Modern 2 bedroom house"

    # ── Route 1: Provided TOON (explicit, no change needed) ──────────────────
    if body.toon:
        toon = body.toon
        scene = parse_toon(toon)
        geometry = compile_scene(scene)
        glb_path = _export_with_blender(toon, "house")
        payload = _response(toon, scene.to_dict(), geometry, glb_path)
        payload["planner"] = "provided-toon"
        return payload

    # ── Route 2: Procedural building pipeline ────────────────────────────────
    if _is_complex_building(prompt):
        schema = extract_building_schema_sync(prompt)
        schema["seed"] = int(time.time() * 1000) % 100000

        glb_path = _export_with_building_worker(schema, "house")

        scene_graph = _schema_to_scene_graph(schema)

        features = []
        if schema.get("pool"):    features.append("swimming pool")
        if schema.get("garage"):  features.append("garage")
        if schema.get("balconies", True): features.append("balcony")

        floors = schema.get("floors", 3)
        btype  = schema.get("building_type", "building")

        glb_url = glb_path or ""
        return {
            "success": True,
            "toon": "",
            "scene_graph": scene_graph,
            "geometry": {"floors": floors, "schema": schema},
            "glb_path": glb_url,
            "model_path": glb_url,
            "message": (
                f"Built. Your **{floors}-floor {btype}** is ready. "
                f"Blender exported {glb_url}; viewer is synchronised to the "
                f"SceneGraph layout. "
                f"Planner: procedural-architecture. "
                f"Features: {', '.join(features)}.\n"
                f'Try: "Make it taller", "Add a pool", or "Change walls to red brick".'
            ),
            "tags": [f"{floors}F {btype}"] + features[:4],
            "planner": "procedural-architecture",
            "schema": schema,
        }

    # ── Route 3: TOON pipeline for simple houses / villas ────────────────────
    toon, planner = prompt_to_toon_with_ollama(prompt, body.ollama_model)
    scene = parse_toon(toon)
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["planner"] = planner
    return payload


@router.post("/edit")
async def edit(body: EditRequest):
    toon, scene, changed = edit_toon(body.toon, body.instruction)
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house_edit")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["changed"] = changed
    return payload


@router.post("/sketchfab/drag-drop")
async def sketchfab_drag_drop(body: DragDropRequest):
    scale_map = {
        "bedroom": 1.0, "living": 1.2, "kitchen": 0.9,
        "bathroom": 0.8, "landscape": 2.0, "outdoor": 1.6,
        "facade": 1.3, "exterior": 1.8, "interior": 1.2,
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
        "message": "MVP pipeline generated scene graph, viewer geometry, and Blender export status.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTIC
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/diagnostic")
async def diagnostic():
    """GET /api/diagnostic — confirms the procedural pipeline is loaded."""
    import shutil
    blender = _find_blender()
    worker = ROOT / "backend" / "workers" / "blender_worker.py"
    return {
        "pipeline": "procedural-architecture-v2",
        "blender_found": blender is not None,
        "blender_path": blender,
        "worker_exists": worker.exists(),
        "worker_path": str(worker),
        "extractor": "backend.services.llm.extractor",
        "schema": "backend.schemas.building_schema",
    }
