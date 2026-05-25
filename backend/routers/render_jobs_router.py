"""
Render Jobs API — Queue and manage render jobs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from backend.services.render_queue import render_queue, JobStatus

log = structlog.get_logger()
router = APIRouter()


# =====================================================
# SCHEMAS
# =====================================================

class EnqueueRenderRequest(BaseModel):
    scene_id: str
    job_type: str = "still"  # still, walkthrough, gltf_export, obj_export, floorplan
    output_mode: str = "fast_preview"
    payload: Dict[str, Any] = {}
    preset: str = "medium"  # preview, medium, cinematic, production


class EnqueueRenderResponse(BaseModel):
    job_id: str
    scene_id: str
    job_type: str
    status: str
    message: str


class RenderJobResponse(BaseModel):
    job_id: str
    scene_id: str
    job_type: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


# =====================================================
# ENDPOINTS
# =====================================================

@router.post("/enqueue", response_model=EnqueueRenderResponse)
async def enqueue_render_job(request: EnqueueRenderRequest):
    """Enqueue a new render job."""
    job_id = await render_queue.enqueue(
        scene_id=request.scene_id,
        job_type=request.job_type,
        payload={
            "output_mode": request.output_mode,
            "preset": request.preset,
            **request.payload,
        },
    )

    return EnqueueRenderResponse(
        job_id=job_id,
        scene_id=request.scene_id,
        job_type=request.job_type,
        status=JobStatus.QUEUED.value,
        message=f"Render job queued for scene {request.scene_id}",
    )


@router.get("/{job_id}", response_model=RenderJobResponse)
async def get_render_job(job_id: str):
    """Get render job status and result."""
    job = await render_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")

    result = await render_queue.get_result(job_id)

    return RenderJobResponse(
        job_id=job_id,
        scene_id=job.get("scene_id", ""),
        job_type=job.get("job_type", ""),
        status=job.get("status", "unknown"),
        created_at=job.get("created_at"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error=job.get("error"),
        result=result,
    )


@router.get("/scene/{scene_id}", response_model=List[RenderJobResponse])
async def list_scene_render_jobs(scene_id: str):
    """List all render jobs for a scene."""
    jobs = await render_queue.list_jobs(scene_id=scene_id)
    return [
        RenderJobResponse(
            job_id=j.get("job_id", ""),
            scene_id=j.get("scene_id", ""),
            job_type=j.get("job_type", ""),
            status=j.get("status", "unknown"),
            created_at=j.get("created_at"),
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
            error=j.get("error"),
        )
        for j in jobs
    ]


@router.post("/{job_id}/cancel")
async def cancel_render_job(job_id: str):
    """Cancel a queued render job."""
    success = await render_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Render job not found")
    return {"status": "cancelled", "job_id": job_id}


@router.get("/queue/length")
async def get_queue_length():
    """Get the current render queue length."""
    length = await render_queue.get_queue_length()
    return {"queue_length": length}
