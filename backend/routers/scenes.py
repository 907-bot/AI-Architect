"""
Scenes API routes - Core scene management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import structlog

from backend.database.models import Scene, Project, User, SceneVersion
from backend.database.client import db_client
from backend.routers.auth import get_current_user
from backend.models.scene_graph import SceneGraph

log = structlog.get_logger()
router = APIRouter()


def get_db() -> Session:
    """Dependency injection"""
    with db_client.SessionLocal() as session:
        yield session


# =====================================================
# SCHEMAS
# =====================================================

class SceneCreate(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    generation_prompt: Optional[str] = None


class SceneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scene_graph: Optional[Dict[str, Any]] = None


class SceneResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SceneDetailResponse(SceneResponse):
    scene_graph: Dict[str, Any]
    generation_prompt: Optional[str]
    asset_urls: Dict[str, Any]
    room_tags: Optional[List[str]] = None


# =====================================================
# CREATE SCENE
# =====================================================

@router.post("", response_model=SceneResponse)
async def create_scene(
    request: SceneCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new scene in a project
    """
    log.info(
        "create_scene",
        user_id=user.id,
        project_id=request.project_id,
        scene_name=request.name
    )
    
    try:
        # Verify project exists and belongs to user
        project = db.query(Project).filter(
            Project.id == request.project_id,
            Project.user_id == user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Create scene with default scene graph
        scene = Scene(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=user.id,
            name=request.name,
            description=request.description,
            generation_prompt=request.generation_prompt,
            status="draft",
            version=1,
            scene_graph={
                "rooms": [],
                "walls": [],
                "windows": [],
                "doors": [],
                "stairs": [],
                "furniture": [],
                "materials": [],
                "lighting": [],
                "navigation": []
            },
            asset_urls={
                "glb": None,
                "splat": None,
                "thumbnail": None,
                "preview_frames": []
            }
        )
        
        db.add(scene)
        db.commit()
        db.refresh(scene)
        
        log.info("scene_created", scene_id=scene.id, project_id=project.id)
        
        return SceneResponse(
            id=str(scene.id),
            project_id=str(scene.project_id),
            name=scene.name,
            description=scene.description,
            status=scene.status,
            version=scene.version,
            created_at=scene.created_at,
            updated_at=scene.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("create_scene_error", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scene"
        )


# =====================================================
# LIST SCENES
# =====================================================

@router.get("", response_model=List[SceneResponse])
async def list_scenes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List scenes (filtered by project or status)
    """
    log.info("list_scenes", user_id=user.id, skip=skip, limit=limit)
    
    try:
        query = db.query(Scene).filter(Scene.user_id == user.id)
        
        if project_id:
            query = query.filter(Scene.project_id == project_id)
        
        if status_filter:
            query = query.filter(Scene.status == status_filter)
        
        scenes = query.offset(skip).limit(limit).all()
        
        return [
            SceneResponse(
                id=str(s.id),
                project_id=str(s.project_id),
                name=s.name,
                description=s.description,
                status=s.status,
                version=s.version,
                created_at=s.created_at,
                updated_at=s.updated_at,
                completed_at=s.completed_at
            )
            for s in scenes
        ]
        
    except Exception as e:
        log.error("list_scenes_error", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list scenes"
        )


# =====================================================
# GET SCENE DETAILS
# =====================================================

@router.get("/{scene_id}", response_model=SceneDetailResponse)
async def get_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete scene details with scene graph
    """
    log.info("get_scene", scene_id=scene_id, user_id=user.id)
    
    try:
        scene = db.query(Scene).filter(
            Scene.id == scene_id,
            Scene.user_id == user.id
        ).first()
        
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene not found"
            )
        
        return SceneDetailResponse(
            id=str(scene.id),
            project_id=str(scene.project_id),
            name=scene.name,
            description=scene.description,
            status=scene.status,
            version=scene.version,
            created_at=scene.created_at,
            updated_at=scene.updated_at,
            completed_at=scene.completed_at,
            scene_graph=scene.scene_graph,
            generation_prompt=scene.generation_prompt,
            asset_urls=scene.asset_urls,
            room_tags=scene.room_tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("get_scene_error", error=str(e), scene_id=scene_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scene"
        )


# =====================================================
# UPDATE SCENE
# =====================================================

@router.put("/{scene_id}", response_model=SceneDetailResponse)
async def update_scene(
    scene_id: str,
    request: SceneUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update scene and create version history
    """
    log.info("update_scene", scene_id=scene_id, user_id=user.id)
    
    try:
        scene = db.query(Scene).filter(
            Scene.id == scene_id,
            Scene.user_id == user.id
        ).first()
        
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene not found"
            )
        
        # Save current state to version history
        if request.scene_graph:
            version = SceneVersion(
                id=uuid.uuid4(),
                scene_id=scene.id,
                version_number=scene.version,
                scene_graph=scene.scene_graph,
                change_description="Auto-save",
                created_by=user.id
            )
            db.add(version)
        
        # Update scene
        if request.name:
            scene.name = request.name
        if request.description is not None:
            scene.description = request.description
        if request.scene_graph:
            scene.scene_graph = request.scene_graph
            scene.version += 1
            scene.status = "draft"
        
        scene.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(scene)
        
        log.info("scene_updated", scene_id=scene.id, version=scene.version)
        
        return SceneDetailResponse(
            id=str(scene.id),
            project_id=str(scene.project_id),
            name=scene.name,
            description=scene.description,
            status=scene.status,
            version=scene.version,
            created_at=scene.created_at,
            updated_at=scene.updated_at,
            completed_at=scene.completed_at,
            scene_graph=scene.scene_graph,
            generation_prompt=scene.generation_prompt,
            asset_urls=scene.asset_urls,
            room_tags=scene.room_tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("update_scene_error", error=str(e), scene_id=scene_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update scene"
        )


# =====================================================
# DELETE SCENE
# =====================================================

@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete scene and its version history
    """
    log.info("delete_scene", scene_id=scene_id, user_id=user.id)
    
    try:
        scene = db.query(Scene).filter(
            Scene.id == scene_id,
            Scene.user_id == user.id
        ).first()
        
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene not found"
            )
        
        db.delete(scene)
        db.commit()
        
        log.info("scene_deleted", scene_id=scene_id)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("delete_scene_error", error=str(e), scene_id=scene_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete scene"
        )
