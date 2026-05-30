from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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
from backend.services.render_queue import render_queue
from backend.services.llm.extractor import extract_building_schema_sync

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = ROOT / "exports"


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    toon: Optional[str] = None
    ollama_model: Optional[str] = None
    style: Optional[str] = "modern"
    render_quality: Optional[str] = "medium"


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
# ROUTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_complex_building(prompt: str) -> bool:
    """Route to procedural pipeline for multi-storey / feature-rich buildings."""
    p = prompt.lower()
    return any(t in p for t in [
        "storey", "story", "floor", "apartment", "office", "hotel",
        "commercial", "pool", "swimming", "garage", "parking",
        "skyscraper", "tower", "mall", "warehouse",
    ])


def _schema_to_scene_graph(schema: dict) -> dict:
    """Minimal scene_graph for frontend floor-plan view from building schema."""
    floor_h = schema.get("floor_height", 3.2)
    bw = schema.get("width", 20.0)
    bd = schema.get("depth", 15.0)
    floors = schema.get("floors", 3)
    rooms = [
        {
            "name": f"floor_{i+1}_main",
            "type": "living_room",
            "width": bw, "depth": bd, "height": floor_h,
            "floor": i,
            "position": {"x": 0, "y": i * floor_h, "z": 0},
            "plan": {"x": 0, "y": 0, "width": bw, "depth": bd},
            "doors": [], "windows": [],
        }
        for i in range(floors)
    ]
    return {
        "version": "0.2",
        "house": {
            "name": schema.get("building_type", "building"),
            "style": schema.get("style", "modern"),
            "roof": {"kind": schema.get("roof_style", "flat")},
            "adjacency": [], "circulation": [], "rooms": rooms,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# FLOOR ASSIGNMENT (existing logic — unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def apply_prompt_metadata(scene, prompt: str = "") -> None:
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


def assign_floors_to_scene(scene, prompt: str = ""):
    apply_prompt_metadata(scene, prompt)
    rooms = scene.house.rooms
    if not rooms:
        return
    if any(getattr(room, "floor", 0) > 0 for room in rooms):
        return

    prompt_lower = prompt.lower() if prompt else ""
    requested = infer_floor_count(prompt_lower)
    if requested and requested > 1:
        _distribute_rooms_to_floors(scene.house, min(requested, scene.house.num_floors or requested))
        return

    is_two_story   = any(w in prompt_lower for w in ["2 floor","2 story","two floor","two story","double story","2-floor","2-story"])
    is_three_story = any(w in prompt_lower for w in ["3 floor","3 story","three floor","three story","3-floor","3-story"])

    assigned_by_name = False
    for room in rooms:
        name_lower = room.name.lower()
        if any(w in name_lower for w in ["ground","floor0","floor_0","level0","level_0","f0","l0"]):
            room.floor = 0; assigned_by_name = True
        elif any(w in name_lower for w in ["first","floor1","floor_1","level1","level_1","f1","l1"]):
            has_ground = any(any(w in r.name.lower() for w in ["ground","floor0","floor_0"]) for r in rooms)
            room.floor = 1 if (has_ground or is_two_story or is_three_story) else 0
            assigned_by_name = True
        elif any(w in name_lower for w in ["second","floor2","floor_2","level2","level_2","f2","l2"]):
            room.floor = 1 if is_two_story else 2; assigned_by_name = True
        elif any(w in name_lower for w in ["third","floor3","floor_3","level3","level_3","f3","l3"]):
            room.floor = 2; assigned_by_name = True

    if not assigned_by_name:
        if is_three_story:
            for room in rooms:
                rt = room.room_type
                if rt in ["living_room","hallway","kitchen","dining_room"]: room.floor = 0
                elif rt in ["bedroom","bathroom"]: room.floor = 1 if "1" in room.name or "one" in room.name else 2
                else: room.floor = 0
        elif is_two_story:
            for room in rooms:
                room.floor = 1 if room.room_type in ["bedroom","bathroom","study"] else 0


def _distribute_rooms_to_floors(house, num_floors: int):
    rooms = house.rooms
    if not rooms or num_floors <= 1:
        return
    ground_types = {"living_room","hallway","kitchen","dining_room","garage","utility"}
    upper_types  = {"bedroom","bathroom","study","office"}
    for room in rooms:
        if room.room_type in ground_types:
            room.floor = 0
        elif room.room_type in upper_types:
            room.floor = min(1, num_floors - 1)
        else:
            room.floor = 0


# ─────────────────────────────────────────────────────────────────────────────
# BLENDER EXPORT — NEW procedural worker (no bpy import in FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

def _export_with_building_worker(schema: dict, stem: str) -> str | None:
    """
    Call backend/workers/blender_worker.py INSIDE Blender subprocess.
    bpy is available there. Never imported here in FastAPI.
    """
    blender_bin = _find_blender()
    if not blender_bin:
        print("[BuildingWorker] Blender not found.")
        return None

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    glb_path = EXPORTS_DIR / f"{stem}_{stamp}.glb"
    schema["output_path"] = str(glb_path)
    schema.setdefault("seed", stamp % 100000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(schema, tf, indent=2)
        schema_path = tf.name

    worker = ROOT / "backend" / "workers" / "blender_worker.py"
    print(f"[BuildingWorker] Using Blender: {blender_bin}")
    print(f"[BuildingWorker] Worker: {worker}")

    try:
        result = subprocess.run(
            [blender_bin, "--background", "--python", str(worker), "--", schema_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        # Surface key Blender log lines
        for line in (result.stdout or "").splitlines():
            if "[BlenderWorker]" in line or "Error" in line or "Traceback" in line:
                print(f"[Blender] {line}")
        if result.returncode != 0:
            print(f"[BuildingWorker] Blender exited {result.returncode}")
            print(result.stderr[-600:] if result.stderr else "")
            return None
    except subprocess.TimeoutExpired:
        print("[BuildingWorker] Timed out after 180s")
        return None
    except Exception as exc:
        print(f"[BuildingWorker] Exception: {exc}")
        return None
    finally:
        try:
            os.unlink(schema_path)
        except OSError:
            pass

    if not glb_path.exists():
        print(f"[BuildingWorker] GLB not created at {glb_path}")
        return None

    print(f"[BuildingWorker] Success → {glb_path} ({glb_path.stat().st_size // 1024} KB)")
    return f"/exports/{glb_path.name}"


# ─────────────────────────────────────────────────────────────────────────────
# BLENDER EXPORT — legacy TOON pipeline (simple houses)
# ─────────────────────────────────────────────────────────────────────────────

def _export_with_blender(toon: str, stem: str) -> str | None:
    blender_bin = _find_blender()
    if not blender_bin:
        return None

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    toon_path = EXPORTS_DIR / f"{stem}_{stamp}.toon"
    glb_path  = EXPORTS_DIR / f"{stem}_{stamp}.glb"
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

    return f"/exports/{glb_path.name}" if glb_path.exists() else None


def _find_blender() -> str | None:
    blender_bin = shutil.which("blender")
    if not blender_bin:
        mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if mac.exists():
            blender_bin = str(mac)
    return blender_bin


def _check_docker_blender() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "nytimes/blender:latest"],
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            vr = subprocess.run(
                ["docker", "run", "--rm", "nytimes/blender:latest", "blender", "--version"],
                capture_output=True, text=True, timeout=30,
            )
            v = vr.stdout.split("\n")[0] if vr.returncode == 0 else "Blender (Docker)"
            return True, v
    except Exception:
        pass
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate(body: GenerateRequest):
    prompt = body.prompt or "Modern 2 bedroom house"

    # ── Route 1: Explicit TOON provided ──────────────────────────────────────
    if body.toon:
        toon = body.toon
        scene = parse_toon(toon)
        assign_floors_to_scene(scene, prompt)
        geometry = compile_scene(scene)
        glb_path = _export_with_blender(toon, "house")
        payload = _response(toon, scene.to_dict(), geometry, glb_path)
        payload["planner"] = "provided-toon"
        return payload

    # ── Route 2: Complex building → JSON schema → blender_worker.py ──────────
    if _is_complex_building(prompt):
        schema = extract_building_schema_sync(prompt)
        schema["style"] = body.style or schema.get("style", "modern")
        glb_path = _export_with_building_worker(schema, "house")

        features = []
        if schema.get("pool"):    features.append("swimming pool")
        if schema.get("garage"):  features.append("garage")
        if schema.get("balconies", True): features.append("balcony")

        floors = schema.get("floors", 3)
        btype  = schema.get("building_type", "building")

        nbc = calculate_nbc_compliance(schema)
        return {
            "success": True,
            "toon": "",
            "scene_graph": _schema_to_scene_graph(schema),
            "geometry": {"floors": floors, "schema": schema},
            "glb_path": glb_path or "",
            "model_path": glb_path or "",
            "blender_rendered": glb_path is not None,
            "compliance": nbc,
            "message": (
                f"Built. Your **{floors}-floor {btype}** is ready. "
                f"Blender exported {glb_path}; viewer is synchronised to the "
                f"SceneGraph layout. Planner: procedural-architecture. "
                f"Features: {', '.join(features)}.\n"
                f'Try: "Make it taller", "Add a pool", or "Change walls to red brick".'
            ),
            "tags": [f"{floors}F {btype}"] + features[:4],
            "planner": "procedural-architecture",
            "schema": schema,
        }

    # ── Route 3: Simple house → TOON → blender/main.py ───────────────────────
    toon, planner = prompt_to_toon_with_ollama(prompt, body.ollama_model)
    scene = parse_toon(toon)
    assign_floors_to_scene(scene, prompt)
    style = body.style or infer_style(prompt) or scene.house.style
    scene.house.style = style
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["planner"] = planner
    payload["style"] = style
    return payload


@router.post("/edit")
async def edit(body: EditRequest):
    toon, scene, changed = edit_toon(body.toon, body.instruction)
    assign_floors_to_scene(scene, body.instruction)
    geometry = compile_scene(scene)
    glb_path = _export_with_blender(toon, "house_edit")
    payload = _response(toon, scene.to_dict(), geometry, glb_path)
    payload["changed"] = changed
    return payload


@router.get("/diagnostic")
async def diagnostic():
    blender = _find_blender()
    worker  = ROOT / "backend" / "workers" / "blender_worker.py"
    return {
        "pipeline": "procedural-architecture-v2",
        "blender_found": blender is not None,
        "blender_path": blender,
        "worker_exists": worker.exists(),
        "worker_path": str(worker),
    }


@router.get("/blender-status")
async def blender_status():
    docker_available, docker_version = _check_docker_blender()
    if docker_available:
        return {"available": True, "version": docker_version,
                "path": "nytimes/blender:latest (Docker)", "docker": True}
    blender_bin = _find_blender()
    if blender_bin:
        try:
            result = subprocess.run([blender_bin, "--version"],
                capture_output=True, text=True, timeout=5)
            return {"available": True,
                    "version": result.stdout.strip() if result.returncode == 0 else "unknown",
                    "path": blender_bin,
                    "styles": ["modern","villa","colonial","contemporary","craftsman"],
                    "render_presets": ["preview","medium","cinematic","production"]}
        except Exception as e:
            return {"available": False, "error": str(e)}
    return {"available": False, "reason": "Blender not found in PATH"}


@router.get("/ollama-status")
async def ollama_status():
    from backend.toon.ollama import check_ollama_connection
    available, model, error = check_ollama_connection()
    if available:
        return {"available": True, "model": model or "llama3.1", "version": "Ollama connected"}
    return {"available": False, "model": None, "error": error or "Ollama not running"}


@router.get("/redis-status")
async def redis_status():
    return await render_queue.health_check()


@router.get("/blender-mcp-status")
async def blender_mcp_status():
    url = "http://127.0.0.1:8765/health"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as response:
            payload = json.loads(response.read().decode())
        return {"available": response.status == 200 and payload.get("status") == "ok",
                "url": url, "service": payload.get("service")}
    except Exception as e:
        return {"available": False, "url": url, "error": str(e)}


@router.get("/stack-status")
async def stack_status():
    blender     = await blender_status()
    ollama      = await ollama_status()
    redis       = await redis_status()
    blender_mcp = await blender_mcp_status()
    return {"backend": {"available": True}, "frontend": {"available": True},
            "blender": blender, "ollama": ollama,
            "redis": redis, "blender_mcp": blender_mcp}


@router.get("/house-styles")
async def get_house_styles():
    return {"styles": [
        {"id": "modern",       "name": "Modern Minimalist",    "description": "Clean lines, flat roofs, neutral colors"},
        {"id": "villa",        "name": "Mediterranean Villa",  "description": "Warm tones, terracotta roofs"},
        {"id": "colonial",     "name": "Colonial American",    "description": "Symmetric facade, white trim"},
        {"id": "contemporary", "name": "Contemporary Modern",  "description": "Bold contrasts, large windows"},
        {"id": "craftsman",    "name": "Craftsman Bungalow",   "description": "Warm wood tones, pitched roofs"},
    ]}


@router.post("/sketchfab/drag-drop")
async def sketchfab_drag_drop(body: DragDropRequest):
    scale_map = {"bedroom":1.0,"living":1.2,"kitchen":0.9,"bathroom":0.8,
                 "landscape":2.0,"outdoor":1.6,"facade":1.3,"exterior":1.8,"interior":1.2}
    position = dict(body.drop_position)
    position["y"] = 0.0 if body.room_context != "exterior" else 0.05
    scale = scale_map.get(body.room_context or "interior", 1.2) if body.auto_scale else 1.0
    return {"placement_id": f"placed-{int(time.time()*1000)}-{body.asset_uid}",
            "asset_uid": body.asset_uid, "scene_id": "mvp-local",
            "position": position, "rotation": {"x":0.0,"y":0.0,"z":0.0},
            "scale": scale, "glb_url": None, "local_path": None,
            "bounds": {"width":scale,"height":scale,"depth":scale},
            "status": "placed_with_frontend_fallback"}


def _response(toon, scene_graph, geometry, glb_path):
    return {"success": True, "toon": toon, "scene_graph": scene_graph,
            "geometry": geometry, "glb_path": glb_path, "model_path": glb_path,
            "blender_rendered": glb_path is not None,
            "message": "Generated scene graph and Blender model." if glb_path
                       else "Generated scene graph. Blender not available."}

# ─────────────────────────────────────────────────────────────────────────────
# NBC 2016 COMPLIANCE
# ─────────────────────────────────────────────────────────────────────────────

def calculate_nbc_compliance(schema: dict) -> dict:
    """
    Indian NBC 2016 basic zoning checks.
    Returns a compliance dict compatible with the frontend ComplianceData type.
    """
    floors      = schema.get("floors", 3)
    bw          = schema.get("width",  20.0)
    bd          = schema.get("depth",  15.0)
    floor_h     = schema.get("floor_height", 3.2)
    btype       = schema.get("building_type", "apartment")
    plot_w      = bw + 16          # assume 8m setback each side
    plot_d      = bd + 16
    plot_area   = plot_w * plot_d
    footprint   = bw * bd
    total_floor_area = footprint * floors

    far_actual  = round(total_floor_area / plot_area, 2)
    cov_actual  = round((footprint / plot_area) * 100, 1)

    # NBC 2016 typical limits (Group C residential / commercial)
    far_limit   = 3.5 if btype in ("apartment", "office", "hotel") else 2.0
    cov_limit   = 60.0 if btype == "villa" else 50.0
    height_limit = 45.0   # metres (Group B/C without fire NOC)
    actual_h    = floors * floor_h

    issues: list[str] = []
    if far_actual > far_limit:
        issues.append(f"FAR {far_actual} exceeds NBC limit of {far_limit} for {btype}.")
    if cov_actual > cov_limit:
        issues.append(f"Ground coverage {cov_actual}% exceeds {cov_limit}% NBC limit.")
    if actual_h > height_limit:
        issues.append(f"Height {actual_h:.1f}m exceeds {height_limit}m — fire NOC required.")
    if floor_h < 2.75:
        issues.append("Floor height below 2.75m NBC minimum for habitable spaces.")

    vastu: list[str] = []
    vastu.append("Orient main entrance towards North or East for Vastu compliance.")
    if schema.get("pool"):
        vastu.append("Swimming pool best placed in North-East quadrant (Vastu Shastra).")
    if schema.get("garage"):
        vastu.append("Garage is ideal in South-East or North-West zone.")

    return {
        "compliant":              len(issues) == 0,
        "issues":                 issues,
        "actual_far":             far_actual,
        "allowed_far":            far_limit,
        "actual_coverage_pct":    cov_actual,
        "allowed_coverage_pct":   cov_limit,
        "actual_height_m":        round(actual_h, 1),
        "allowed_height_m":       height_limit,
        "vastu_suggestions":      vastu,
        "seismic_guideline":      "Zone III — ductile detailing required per IS 13920.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# BOQ / COST ESTIMATE
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/cost-estimate")
async def cost_estimate(
    floors: int = 3,
    width: float = 20.0,
    depth: float = 15.0,
    floor_height: float = 3.2,
    building_type: str = "apartment",
    style: str = "modern",
):
    """GET /api/cost-estimate — returns BOQ + cost breakdown in USD and INR."""
    footprint   = width * depth
    total_area  = footprint * floors
    perimeter   = 2 * (width + depth)
    wall_area   = perimeter * floors * floor_height * 0.75  # 75% solid (windows 25%)
    slab_vol    = footprint * 0.25 * (floors + 1)           # 250mm slabs
    found_vol   = footprint * 0.6                           # 600mm foundation

    # Material quantities
    concrete_m3 = slab_vol + found_vol
    steel_kg    = concrete_m3 * 90                          # 90 kg/m³ RCC
    brick_nos   = int(wall_area * 60)                       # 60 bricks/m²
    glass_m2    = perimeter * floors * floor_height * 0.25 # 25% glazing
    paint_m2    = wall_area * 2                             # both sides

    # Rates (INR per unit, 2024 India)
    rates_inr = {
        "concrete_rcc": 7500,   # /m³
        "steel_tmt":    75,     # /kg
        "brickwork":    60,     # /brick (laid)
        "glass_upvc":   1200,   # /m²
        "paint":        45,     # /m²
        "tiles_floor":  850,    # /m²
        "electrical":   total_area * 300,
        "plumbing":     total_area * 250,
        "finishing":    total_area * 1500,
    }
    subtotals_inr = {
        "Structure & Concrete":    concrete_m3 * rates_inr["concrete_rcc"],
        "Reinforcement Steel":     steel_kg    * rates_inr["steel_tmt"],
        "Brickwork & Masonry":     brick_nos   * rates_inr["brickwork"],
        "Glazing & Windows":       glass_m2    * rates_inr["glass_upvc"],
        "Painting & Plaster":      paint_m2    * rates_inr["paint"],
        "Flooring & Tiles":        total_area  * rates_inr["tiles_floor"],
        "Electrical Works":        rates_inr["electrical"],
        "Plumbing & Sanitation":   rates_inr["plumbing"],
        "Interior & Finishing":    rates_inr["finishing"],
    }
    total_inr = sum(subtotals_inr.values())
    usd_rate  = 83.5   # approximate

    return {
        "building": {"floors": floors, "width": width, "depth": depth,
                     "footprint_m2": round(footprint, 1), "total_area_m2": round(total_area, 1)},
        "quantities": {
            "concrete_m3":   round(concrete_m3, 1),
            "steel_kg":      round(steel_kg),
            "brick_nos":     brick_nos,
            "glass_m2":      round(glass_m2, 1),
            "paint_m2":      round(paint_m2, 1),
            "floor_area_m2": round(total_area, 1),
        },
        "cost_breakdown_inr": {k: round(v) for k, v in subtotals_inr.items()},
        "total_inr":   round(total_inr),
        "total_usd":   round(total_inr / usd_rate),
        "cost_per_sqft_inr": round(total_inr / (total_area * 10.764)),
        "currency_note": "Indicative estimate. Rates vary by location and contractor.",
    }
