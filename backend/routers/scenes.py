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
from backend.models.scene_graph import SceneGraph, SceneValidator, SceneGraph as SceneGraphModel

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

class SceneCreate(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    generation_prompt: Optional[str] = None
    output_mode: Optional[str] = "fast_preview"


class SceneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scene_graph: Optional[Dict[str, Any]] = None
    output_mode: Optional[str] = None


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
            output_mode=request.output_mode or "fast_preview",
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
        
        # Validate scene_graph before returning
        validated_sg = scene.scene_graph
        if isinstance(validated_sg, dict):
            success, parsed, error_msg = SceneValidator.validate_llm_output(validated_sg)
            if success:
                validated_sg = parsed.to_dict()
            else:
                log.warning("get_scene_invalid_scene_graph", scene_id=scene_id, error=error_msg)

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
            scene_graph=validated_sg,
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


# =====================================================
# GENERATE TEST SCENE (no AI, returns hardcoded valid scene)
# =====================================================

@router.get("/generate-test", response_model=SceneDetailResponse)
async def generate_test_scene(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns a hardcoded fully-valid scene graph.
    Use this to test frontend rendering independent of AI generation.
    """
    log.info("generate_test_scene", user_id=user.id)

    test_scene_graph = {
        "style": "modern",
        "rooms": [
            {
                "id": "living_room_1",
                "room_type": "living_room",
                "name": "Living Room",
                "floor_number": 0,
                "position": {"x": 0, "y": 0, "z": 0},
                "width": 6.0,
                "depth": 5.0,
                "height": 3.0,
                "material_id": "floor_oak",
                "walls": [
                    {
                        "id": "wall_lr_1",
                        "room_id": "living_room_1",
                        "start_point": {"x": -3.0, "y": 0, "z": -2.5},
                        "end_point": {"x": 3.0, "y": 0, "z": -2.5},
                        "height": 3.0,
                        "thickness": 0.2,
                        "material_id": "wall_plaster",
                        "doors": [],
                        "windows": [
                            {
                                "id": "win_lr_1",
                                "room_id": "living_room_1",
                                "position": {"x": 0, "y": 1.5, "z": -2.5},
                                "width": 2.0,
                                "height": 1.5,
                                "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                                "material_id": "glass_clear",
                                "window_type": "sliding"
                            }
                        ]
                    }
                ],
                "doors": [
                    {
                        "id": "door_lr_1",
                        "room_id": "living_room_1",
                        "position": {"x": 2.5, "y": 0, "z": 0},
                        "width": 0.9,
                        "height": 2.1,
                        "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                        "material_id": "wood_oak",
                        "door_type": "swing",
                        "connects_to_room": "bedroom_1"
                    }
                ],
                "furniture": [
                    {
                        "id": "sofa_1",
                        "room_id": "living_room_1",
                        "furniture_type": "sofa",
                        "position": {"x": -1.5, "y": 0, "z": 1.0},
                        "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                        "scale": {"x": 2.0, "y": 0.8, "z": 0.9},
                        "model_id": "sofa_modern",
                        "material_id": "fabric_grey",
                        "metadata": {}
                    }
                ],
                "lights": [
                    {
                        "id": "light_lr_1",
                        "room_id": "living_room_1",
                        "light_type": "ambient",
                        "position": {"x": 0, "y": 2.8, "z": 0},
                        "color_rgb": "#FFF5E6",
                        "intensity": 0.8,
                        "range": None,
                        "angle": None
                    }
                ]
            },
            {
                "id": "bedroom_1",
                "room_type": "bedroom",
                "name": "Master Bedroom",
                "floor_number": 0,
                "position": {"x": 0, "y": 0, "z": 6},
                "width": 5.0,
                "depth": 4.0,
                "height": 3.0,
                "material_id": "floor_carpet",
                "walls": [
                    {
                        "id": "wall_br_1",
                        "room_id": "bedroom_1",
                        "start_point": {"x": -2.5, "y": 0, "z": -2.0},
                        "end_point": {"x": 2.5, "y": 0, "z": -2.0},
                        "height": 3.0,
                        "thickness": 0.2,
                        "material_id": "wall_plaster",
                        "doors": [
                            {
                                "id": "door_br_1",
                                "room_id": "bedroom_1",
                                "position": {"x": 0, "y": 0, "z": -2.0},
                                "width": 0.9,
                                "height": 2.1,
                                "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                                "material_id": "wood_oak",
                                "door_type": "swing",
                                "connects_to_room": "living_room_1"
                            }
                        ],
                        "windows": []
                    }
                ],
                "doors": [],
                "windows": [],
                "furniture": [
                    {
                        "id": "bed_1",
                        "room_id": "bedroom_1",
                        "furniture_type": "bed",
                        "position": {"x": 0, "y": 0, "z": 1.0},
                        "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                        "scale": {"x": 1.8, "y": 0.5, "z": 2.0},
                        "model_id": "bed_queen",
                        "material_id": "fabric_grey",
                        "metadata": {}
                    }
                ],
                "lights": [
                    {
                        "id": "light_br_1",
                        "room_id": "bedroom_1",
                        "light_type": "ambient",
                        "position": {"x": 0, "y": 2.8, "z": 0},
                        "color_rgb": "#FFF5E6",
                        "intensity": 0.6,
                        "range": None,
                        "angle": None
                    }
                ]
            }
        ],
        "stairs": [],
        "materials": [
            {
                "id": "wall_plaster",
                "name": "White Plaster",
                "material_type": "paint",
                "color_rgb": "#F5F5F0",
                "roughness": 0.9,
                "metallic": 0.0
            },
            {
                "id": "floor_oak",
                "name": "Oak Wood Floor",
                "material_type": "wood",
                "color_rgb": "#B88A44",
                "roughness": 0.6,
                "metallic": 0.0
            },
            {
                "id": "floor_carpet",
                "name": "Grey Carpet",
                "material_type": "carpet",
                "color_rgb": "#8B8B8B",
                "roughness": 0.95,
                "metallic": 0.0
            },
            {
                "id": "wood_oak",
                "name": "Oak Wood",
                "material_type": "wood",
                "color_rgb": "#8B5A2B",
                "roughness": 0.5,
                "metallic": 0.0
            },
            {
                "id": "glass_clear",
                "name": "Clear Glass",
                "material_type": "glass",
                "color_rgb": "#D4E8F0",
                "roughness": 0.0,
                "metallic": 0.1
            },
            {
                "id": "fabric_grey",
                "name": "Grey Fabric",
                "material_type": "fabric",
                "color_rgb": "#A8A8A8",
                "roughness": 0.9,
                "metallic": 0.0
            }
        ],
        "lights": [],
        "navigation": {
            "navigation_meshes": [],
            "walkthrough_points": [
                {"x": -5, "y": 1.6, "z": -5},
                {"x": 0, "y": 1.6, "z": 0},
                {"x": 5, "y": 1.6, "z": 5}
            ],
            "drone_path_nodes": [
                {"x": 10, "y": 8, "z": 10},
                {"x": -10, "y": 8, "z": -10},
                {"x": 0, "y": 12, "z": 0}
            ]
        }
    }

    return SceneDetailResponse(
        id="test-scene-001",
        project_id="test-project",
        name="Test Scene (Hardcoded)",
        description="A fully-valid hardcoded scene for frontend testing",
        status="completed",
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        scene_graph=test_scene_graph,
        generation_prompt="Generate a modern house with living room and bedroom",
        asset_urls={
            "glb": None,
            "splat": None,
            "thumbnail": None,
            "preview_frames": []
        },
        room_tags=["living_room", "bedroom"]
    )
