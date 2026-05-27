from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.parser import parse_toon
from backend.toon.planner import prompt_to_toon


router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = ROOT / "exports"


class GenerateRequest(BaseModel):
    prompt: str | None = None
    toon: str | None = None


class EditRequest(BaseModel):
    toon: str
    instruction: str


@router.post("/generate")
async def generate(body: GenerateRequest):
    toon = body.toon or prompt_to_toon(body.prompt or "Modern 2 bedroom house")
    scene = parse_toon(toon)
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house")
    return _response(toon, scene.to_dict(), geometry, glb_path)


@router.post("/edit")
async def edit(body: EditRequest):
    toon, scene, changed = edit_toon(body.toon, body.instruction)
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house_edit")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["changed"] = changed
    return payload


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


def _export_with_blender(toon: str, stem: str) -> str | None:
    blender_bin = shutil.which("blender")
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
