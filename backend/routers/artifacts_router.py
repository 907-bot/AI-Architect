"""
Artifacts API — Progressive artifact generation and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from backend.config import settings
from backend.services.artifacts import (
    artifact_pipeline, ArtifactStage, ArtifactType,
    get_output_modes, OutputMode,
)

log = structlog.get_logger()
router = APIRouter()


# =====================================================
# SCHEMAS
# =====================================================

class GenerateArtifactRequest(BaseModel):
    scene_id: str
    stage: str
    output_mode: str = "fast_preview"
    scene_graph: Dict[str, Any]


class ArtifactResponse(BaseModel):
    scene_id: str
    stage: str
    artifact_type: str
    status: str
    url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ProgressiveGenerateRequest(BaseModel):
    scene_id: str
    scene_graph: Dict[str, Any]
    output_mode: str = "fast_preview"


class ProgressiveGenerateResponse(BaseModel):
    scene_id: str
    output_mode: str
    artifacts: List[ArtifactResponse]
    status: str


# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/output-modes")
async def list_output_modes():
    """List all available output modes with descriptions."""
    return {"output_modes": get_output_modes()}


@router.post("/generate", response_model=ArtifactResponse)
async def generate_artifact(request: GenerateArtifactRequest):
    """Generate a single artifact stage."""
    try:
        stage = ArtifactStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")

    rec = await artifact_pipeline.generate_artifact(
        scene_id=request.scene_id,
        stage=stage,
        scene_graph=request.scene_graph,
        output_mode=request.output_mode,
    )

    return ArtifactResponse(
        scene_id=rec.scene_id,
        stage=rec.stage.value,
        artifact_type=rec.artifact_type.value,
        status=rec.status.value,
        url=rec.url,
        preview_url=rec.preview_url,
        error=rec.error,
        metadata=rec.metadata,
    )


@router.post("/generate-progressive", response_model=ProgressiveGenerateResponse)
async def generate_progressive(request: ProgressiveGenerateRequest):
    """Generate all artifacts for a given output mode progressively."""
    if request.output_mode not in [m.value for m in OutputMode]:
        raise HTTPException(status_code=400, detail=f"Invalid output mode: {request.output_mode}")

    results = await artifact_pipeline.generate_progressive(
        scene_id=request.scene_id,
        scene_graph=request.scene_graph,
        output_mode=request.output_mode,
    )

    status_val = "completed"
    errors = [r.error for r in results if r.error]
    if errors:
        status_val = "partial" if any(r.status.value == "completed" for r in results) else "failed"

    return ProgressiveGenerateResponse(
        scene_id=request.scene_id,
        output_mode=request.output_mode,
        artifacts=[
            ArtifactResponse(
                scene_id=r.scene_id,
                stage=r.stage.value,
                artifact_type=r.artifact_type.value,
                status=r.status.value,
                url=r.url,
                preview_url=r.preview_url,
                error=r.error,
                metadata=r.metadata,
            )
            for r in results
        ],
        status=status_val,
    )


@router.get("/{scene_id}")
async def get_scene_artifacts(scene_id: str):
    """Get all artifacts for a scene."""
    records = artifact_pipeline.get_artifacts(scene_id)
    return {
        "scene_id": scene_id,
        "artifacts": [r.to_dict() for r in records],
        "urls": artifact_pipeline.get_artifact_urls(scene_id),
    }


@router.get("/{scene_id}/urls")
async def get_scene_artifact_urls(scene_id: str):
    """Get artifact URLs for a scene."""
    return {
        "scene_id": scene_id,
        "urls": artifact_pipeline.get_artifact_urls(scene_id),
    }
