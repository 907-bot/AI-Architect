"""
Asset Library API — Materials, furniture, HDRIs.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from backend.services.asset_library import asset_resolver

router = APIRouter()


@router.get("/materials")
async def list_materials():
    """List all PBR materials."""
    return {"materials": asset_resolver.list_all_materials()}


@router.get("/materials/{material_id}")
async def get_material(material_id: str):
    """Get a specific material by ID."""
    mat = asset_resolver.resolve_material_by_name(material_id)
    if not mat:
        return {"error": "Material not found"}, 404
    return {"material": mat}


@router.get("/furniture")
async def list_furniture():
    """List all furniture assets."""
    return {"furniture": asset_resolver.list_all_furniture()}


@router.get("/hdris")
async def list_hdris():
    """List all HDRI environments."""
    return {"hdris": asset_resolver.list_all_hdris()}


@router.get("/resolve")
async def resolve_assets(
    scene_id: str,
    style: str = "modern",
):
    """Resolve all assets for a scene configuration."""
    from backend.models.canonical_scene import DesignStyle
    try:
        ds = DesignStyle(style)
    except ValueError:
        ds = DesignStyle.MODERN

    return {
        "scene_id": scene_id,
        "style": style,
        "materials": asset_resolver.resolve_materials(ds),
        "hdri": asset_resolver.resolve_hdri("sunset_park"),
    }
