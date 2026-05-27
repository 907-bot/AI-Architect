"""
Assets API — Sketchfab Search, Download, Placement, Drag-and-Drop
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog
import uuid
import asyncio

from backend.sketchfab_client import get_sketchfab_manager, CACHE_DIR

log = structlog.get_logger()
router = APIRouter()

# ====================================================
# SCHEMAS
# ====================================================

class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None        # furniture, architecture, decor, exterior
    context: Optional[str] = None         # interior, exterior, landscape
    max_results: int = 24

class SearchResult(BaseModel):
    uid: str
    name: str
    description: str
    thumbnail: str
    author: str
    vertex_count: Optional[int]
    face_count: Optional[int]
    is_downloadable: bool
    license: str
    tags: List[str]
    view_count: int
    like_count: int

class PlaceAssetRequest(BaseModel):
    uid: str
    scene_id: str
    position: Dict[str, float]            # {x, y, z}
    rotation: Optional[Dict[str, float]] = {"x": 0, "y": 0, "z": 0}
    scale: Optional[float] = 1.0
    room_id: Optional[str] = None
    room_type: Optional[str] = None      # bedroom, living, kitchen, exterior

class DragDropRequest(BaseModel):
    """Frontend sends this when user drags from palette to canvas"""
    asset_uid: str
    drop_position: Dict[str, float]      # Raycast hit point on floor/plane
    surface_normal: Optional[Dict[str, float]] = {"x": 0, "y": 1, "z": 0}
    room_context: Optional[str] = None   # Which room user dropped into
    auto_orient: bool = True             # Snap to surface normal
    auto_scale: bool = True              # Scale to fit room context

class AssetPlacementResponse(BaseModel):
    placement_id: str
    asset_uid: str
    scene_id: str
    position: Dict[str, float]
    rotation: Dict[str, float]
    scale: float
    glb_url: Optional[str]
    local_path: Optional[str]
    bounds: Optional[Dict[str, Any]]     # bbox for collision

# ====================================================
# SEARCH SKETCHFAB
# ====================================================

@router.post("/search", response_model=List[SearchResult])
async def search_sketchfab(request: SearchRequest):
    """
    Search Sketchfab for 3D assets.
    Context-aware: "interior" context prioritizes furniture/decor.
    """
    manager = get_sketchfab_manager()
    results = await manager.search(
        query=request.query,
        category=request.category,
        context=request.context,
        max_results=request.max_results
    )
    log.info("asset_search", query=request.query, context=request.context, results=len(results))
    return results


# ====================================================
# GET ASSET DETAILS + DOWNLOAD
# ====================================================

@router.get("/{uid}")
async def get_asset(uid: str):
    """
    Get full asset metadata + download info.
    Returns local cache path if already downloaded.
    """
    manager = get_sketchfab_manager()
    asset = await manager.get_asset(uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ====================================================
# PLACE ASSET IN SCENE (with smart positioning)
# ====================================================

@router.post("/place", response_model=AssetPlacementResponse)
async def place_asset(request: PlaceAssetRequest):
    """
    Place a Sketchfab asset into a scene with intelligent positioning.
    """
    manager = get_sketchfab_manager()
    asset = await manager.get_asset(request.uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found or not downloadable")

    # Auto-scale based on room type
    scale = request.scale
    if request.room_type:
        scale_multipliers = {
            "bedroom": 1.0,
            "living": 1.2,
            "kitchen": 0.9,
            "bathroom": 0.8,
            "exterior": 1.5,
            "landscape": 2.0
        }
        scale *= scale_multipliers.get(request.room_type, 1.0)

    placement = AssetPlacementResponse(
        placement_id=str(uuid.uuid4()),
        asset_uid=request.uid,
        scene_id=request.scene_id,
        position=request.position,
        rotation=request.rotation or {"x": 0, "y": 0, "z": 0},
        scale=scale,
        glb_url=asset.get("download_url"),
        local_path=asset.get("local_path"),
        bounds={"width": 1.0, "height": 1.0, "depth": 1.0}  # TODO: parse from GLB
    )

    log.info("asset_placed", uid=request.uid, scene=request.scene_id, room=request.room_type)
    return placement


# ====================================================
# DRAG-AND-DROP ENDPOINT (Frontend → Backend)
# ====================================================

@router.post("/drag-drop", response_model=AssetPlacementResponse)
async def drag_drop_asset(request: DragDropRequest):
    """
    Handle drag-and-drop from asset palette to 3D canvas.
    Returns placement data immediately — GLB download happens async in background.
    Frontend uses public fallback GLBs while the real model downloads.
    """
    manager = get_sketchfab_manager()

    # Get metadata only (fast — no download)
    meta = await manager.direct.get_model_details(request.asset_uid)
    if not meta:
        raise HTTPException(status_code=404, detail="Asset not found")

    pos = request.drop_position.copy()
    if request.room_context in ["bedroom", "living", "kitchen", "bathroom"]:
        pos["y"] = 0.0
    elif request.room_context == "exterior":
        pos["y"] = 0.05

    rotation = {"x": 0, "y": 0, "z": 0}
    if request.auto_orient and request.surface_normal:
        import math
        nx, ny, nz = request.surface_normal.get("x",0), request.surface_normal.get("y",1), request.surface_normal.get("z",0)
        if ny > 0.9:
            dx, dz = -pos.get("x",0), -pos.get("z",0)
            rotation["y"] = math.atan2(dx, dz)

    scale = 1.5
    if request.auto_scale and request.room_context:
        scale_map = {"bedroom": 1.0, "living": 1.2, "kitchen": 0.9, "bathroom": 0.8, "exterior": 2.0}
        scale = scale_map.get(request.room_context, 1.5)

    # Check if already cached
    cache_path = CACHE_DIR / f"{request.asset_uid}.glb"

    # Trigger background download if we have a token
    local_path = None
    glb_url = None
    if cache_path.exists():
        local_path = str(cache_path)
        glb_url = None  # frontend builds URL from local_path
    else:
        # Start background download — don't wait for it
        asyncio.create_task(manager.get_or_download(request.asset_uid))

    placement = AssetPlacementResponse(
        placement_id=str(uuid.uuid4()),
        asset_uid=request.asset_uid,
        scene_id="current",
        position=pos,
        rotation=rotation,
        scale=scale,
        glb_url=glb_url,
        local_path=local_path,
        bounds={"width": scale, "height": scale * 0.5, "depth": scale}
    )

    log.info("drag_drop_placed", uid=request.asset_uid, cached=cache_path.exists())
    return placement


# ====================================================
# UPLOAD USER MODEL (for drag-drop of local files)
# ====================================================

@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    room_type: str = Form("interior"),
    name: str = Form(None)
):
    """
    Accept user-uploaded GLB/GLTF files for drag-and-drop.
    Saves to local cache and returns placement-ready metadata.
    """
    from backend.sketchfab_client import CACHE_DIR
    import shutil

    uid = str(uuid.uuid4())
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["glb", "gltf", "obj", "fbx"]:
        raise HTTPException(status_code=400, detail="Only GLB/GLTF/OBJ/FBX supported")

    cache_path = CACHE_DIR / f"{uid}.{ext}"
    with open(cache_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    log.info("asset_uploaded", uid=uid, filename=file.filename, size=cache_path.stat().st_size)

    return {
        "uid": uid,
        "name": name or file.filename,
        "local_path": str(cache_path),
        "format": ext,
        "room_type": room_type,
        "ready": True
    }


# ====================================================
# INTERIOR / EXTERIOR PRESET CATALOGS
# ====================================================

INTERIOR_CATALOG = {
    "living": [
        {"query": "sofa couch modern", "category": "furniture"},
        {"query": "coffee table", "category": "furniture"},
        {"query": "tv stand television", "category": "furniture"},
        {"query": "floor lamp", "category": "decor"},
        {"query": "rug carpet", "category": "decor"},
        {"query": "bookshelf", "category": "furniture"}
    ],
    "bedroom": [
        {"query": "bed double modern", "category": "furniture"},
        {"query": "wardrobe closet", "category": "furniture"},
        {"query": "nightstand bedside", "category": "furniture"},
        {"query": "dresser chest", "category": "furniture"},
        {"query": "table lamp", "category": "decor"}
    ],
    "kitchen": [
        {"query": "refrigerator fridge", "category": "furniture"},
        {"query": "kitchen stove oven", "category": "furniture"},
        {"query": "kitchen sink", "category": "furniture"},
        {"query": "dining table chairs", "category": "furniture"},
        {"query": "kitchen island", "category": "furniture"}
    ],
    "bathroom": [
        {"query": "toilet modern", "category": "furniture"},
        {"query": "shower cabin", "category": "furniture"},
        {"query": "bathroom sink vanity", "category": "furniture"},
        {"query": "bathtub", "category": "furniture"},
        {"query": "mirror bathroom", "category": "decor"}
    ]
}

EXTERIOR_CATALOG = {
    "landscape": [
        {"query": "tree realistic", "category": "nature"},
        {"query": "bush hedge", "category": "nature"},
        {"query": "flower pot planter", "category": "decor"},
        {"query": "garden bench", "category": "furniture"},
        {"query": "fountain", "category": "architecture"}
    ],
    "facade": [
        {"query": "window frame", "category": "architecture"},
        {"query": "front door", "category": "architecture"},
        {"query": "balcony railing", "category": "architecture"},
        {"query": "awning canopy", "category": "architecture"},
        {"query": "shutter blind", "category": "decor"}
    ],
    "outdoor": [
        {"query": "outdoor table set", "category": "furniture"},
        {"query": "bbq grill", "category": "furniture"},
        {"query": "swimming pool", "category": "architecture"},
        {"query": "garage door", "category": "architecture"},
        {"query": "driveway car", "category": "vehicle"}
    ]
}

@router.get("/catalog/{room_type}")
async def get_catalog(room_type: str):
    """
    Get curated Sketchfab search queries for a room type.
    Frontend uses these to populate the drag-and-drop palette.
    """
    if room_type in INTERIOR_CATALOG:
        return {"type": "interior", "items": INTERIOR_CATALOG[room_type]}
    elif room_type in EXTERIOR_CATALOG:
        return {"type": "exterior", "items": EXTERIOR_CATALOG[room_type]}
    else:
        # Generic fallback
        return {"type": "generic", "items": [{"query": room_type, "category": None}]}


# ====================================================
# HEALTH
# ====================================================

@router.get("/health")
async def assets_health():
    return {
        "status": "ok",
        "service": "assets",
        "sketchfab_configured": bool(get_sketchfab_manager().direct.api_token),
        "mcp_enabled": get_sketchfab_manager().use_mcp
    }
