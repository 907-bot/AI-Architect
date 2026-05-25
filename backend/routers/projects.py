"""
Projects API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import structlog

from backend.database.models import Project, Scene, User
from backend.database.client import db_client
from backend.routers.auth import get_current_user

log = structlog.get_logger()
router = APIRouter()


def get_db() -> Session:
    """Safe DB dependency — raises 503 when database is unavailable."""
    if db_client.SessionLocal is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )
    with db_client.SessionLocal() as session:
        yield session


# =====================================================
# SCHEMAS
# =====================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_public: bool
    thumbnail_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    scene_count: int
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    scenes: List[dict] = []


# =====================================================
# CREATE PROJECT
# =====================================================

@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project
    """
    log.info("create_project", user_id=user.id, project_name=request.name)
    
    try:
        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        log.info("project_created", project_id=project.id, user_id=user.id)
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_public=project.is_public,
            thumbnail_url=project.thumbnail_url,
            created_at=project.created_at,
            updated_at=project.updated_at,
            scene_count=0
        )
        
    except Exception as e:
        db.rollback()
        log.error("create_project_error", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


# =====================================================
# LIST PROJECTS
# =====================================================

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List user's projects
    """
    log.info("list_projects", user_id=user.id, skip=skip, limit=limit)
    
    try:
        projects = db.query(Project).filter(
            Project.user_id == user.id
        ).offset(skip).limit(limit).all()
        
        result = []
        for project in projects:
            scene_count = db.query(Scene).filter(Scene.project_id == project.id).count()
            result.append(ProjectResponse(
                id=str(project.id),
                name=project.name,
                description=project.description,
                is_public=project.is_public,
                thumbnail_url=project.thumbnail_url,
                created_at=project.created_at,
                updated_at=project.updated_at,
                scene_count=scene_count
            ))
        
        return result
        
    except Exception as e:
        log.error("list_projects_error", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects"
        )


# =====================================================
# GET PROJECT
# =====================================================

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get project details with scenes
    """
    log.info("get_project", project_id=project_id, user_id=user.id)
    
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get scenes
        scenes = db.query(Scene).filter(Scene.project_id == project.id).all()
        
        return ProjectDetailResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_public=project.is_public,
            thumbnail_url=project.thumbnail_url,
            created_at=project.created_at,
            updated_at=project.updated_at,
            scene_count=len(scenes),
            scenes=[
                {
                    "id": str(s.id),
                    "name": s.name,
                    "status": s.status,
                    "created_at": s.created_at
                }
                for s in scenes
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("get_project_error", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project"
        )


# =====================================================
# UPDATE PROJECT
# =====================================================

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update project details
    """
    log.info("update_project", project_id=project_id, user_id=user.id)
    
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Update fields
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.is_public is not None:
            project.is_public = request.is_public
        
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        
        log.info("project_updated", project_id=project.id)
        
        scene_count = db.query(Scene).filter(Scene.project_id == project.id).count()
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_public=project.is_public,
            thumbnail_url=project.thumbnail_url,
            created_at=project.created_at,
            updated_at=project.updated_at,
            scene_count=scene_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("update_project_error", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


# =====================================================
# DELETE PROJECT
# =====================================================

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete project and all its scenes
    """
    log.info("delete_project", project_id=project_id, user_id=user.id)
    
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Delete cascades to scenes
        db.delete(project)
        db.commit()
        
        log.info("project_deleted", project_id=project_id)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("delete_project_error", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )
