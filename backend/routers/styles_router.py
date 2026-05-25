"""
Styles API — Design style management and preview.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from backend.models.canonical_scene import DesignStyle
from backend.services.style_engine import (
    list_available_styles,
    apply_style_to_design_system,
    get_materials_for_style,
    get_lighting_for_style,
)

router = APIRouter()


@router.get("/styles")
async def get_styles():
    """List all available design styles."""
    return {"styles": list_available_styles()}


@router.get("/styles/{style_id}")
async def get_style_detail(style_id: str):
    """Get detailed configuration for a specific style."""
    try:
        style = DesignStyle(style_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Style not found: {style_id}")

    ds = apply_style_to_design_system(style)
    return {
        "style": style_id,
        "design_system": ds.model_dump(),
        "materials": get_materials_for_style(style),
        "lighting": get_lighting_for_style(style),
    }


@router.get("/styles/{style_id}/materials")
async def get_style_materials(style_id: str):
    """Get material palette for a design style."""
    try:
        style = DesignStyle(style_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Style not found: {style_id}")
    return {
        "style": style_id,
        "materials": get_materials_for_style(style),
    }
