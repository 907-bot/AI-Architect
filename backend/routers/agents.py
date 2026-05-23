"""
Agents API routes - Scene generation and agent management
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncio
import structlog

from backend.database.models import Scene, User, AgentExecution, Project
from backend.database.client import db_client
from backend.routers.auth import get_current_user
from backend.models.openrouter import get_openrouter_client
from backend.agents.orchestrator import create_orchestrator_agent
from backend.config import settings

log = structlog.get_logger()
router = APIRouter()


def get_db() -> Session:
    """Dependency injection"""
    with db_client.SessionLocal() as session:
        yield session


# =====================================================
# SCHEMAS
# =====================================================

class GenerateSceneRequest(BaseModel):
    # Frontend-compatible fields
    scene_id: Optional[str] = None  # Can be derived from project_id if not provided
    prompt: str
    style: Optional[str] = "modern"
    budget: Optional[str] = "medium"
    # Additional frontend fields (optional)
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    plot_lat: Optional[float] = None
    plot_lng: Optional[float] = None
    plot_width: Optional[float] = None
    plot_depth: Optional[float] = None


class AgentExecutionResponse(BaseModel):
    id: str
    scene_id: Optional[str]
    agent_name: str
    agent_role: str
    status: str
    token_usage: Dict[str, int]
    execution_time_ms: Optional[int]
    model_used: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class GenerateSceneResponse(BaseModel):
    scene_id: str
    status: str
    message: str
    agent_executions: List[str]  # List of execution IDs


# =====================================================
# SIMPLIFIED DIRECT GENERATE - Works WITHOUT database dependency
# =====================================================

@router.post("/generate_direct", response_model=GenerateSceneResponse)
async def generate_scene_direct(
    request: GenerateSceneRequest,
    background_tasks: BackgroundTasks,
):
    """
    Simplified scene generation - returns mock success for frontend testing.
    Sends immediate WebSocket responses for snappy UI.
    """
    from backend.websocket_manager import ws_manager
    
    log.info(
        "generate_scene_direct_request",
        prompt=request.prompt[:50],
        project_id=request.project_id
    )
    
    scene_id = str(uuid.uuid4())
    client_id = request.client_id or "default"
    
    log.info("generate_direct_websocket", client_id=client_id, active_connections=list(ws_manager.active_connections.keys()))
    
    # Send WebSocket updates immediately (simulate agent chain)
    await ws_manager.send_to_client(client_id, {
        "type": "agent_update",
        "agent": "orchestrator",
        "message": "Processing prompt: " + request.prompt[:30],
        "data": {"intent": "generate_building"}
    })
    
    await ws_manager.send_to_client(client_id, {
        "type": "agent_update",
        "agent": "planner",
        "message": f"Planning: 2-story building on {request.plot_width or 20}x{request.plot_depth or 30}m plot",
        "data": {}
    })
    
    await ws_manager.send_to_client(client_id, {
        "type": "agent_update",
        "agent": "geometry",
        "message": "Generated 3D meshes for walls, floors, roof",
        "data": {
            "meshes": [
                {"id": "building_base", "type": "box", "position": [0, 1.5, 0], "scale": [8, 3, 10], "material_id": "plaster_white"}
            ]
        }
    })
    
    await ws_manager.send_to_client(client_id, {
        "type": "agent_update",
        "agent": "evaluation",
        "message": "Complete - design validated",
        "data": {
            "bear": {
                "enhanced_config": {
                    "meshes": [
                        {"id": "foundation", "type": "box", "position": [0, -0.1, 0], "scale": [8, 0.2, 10], "material_id": "concrete"},
                        {"id": "base", "type": "box", "position": [0, 1.5, 0], "scale": [8, 3, 10], "material_id": "plaster_white"},
                        {"id": "roof", "type": "box", "position": [0, 3.1, 0], "scale": [9, 0.2, 11], "material_id": "wood_oak"}
                    ]
                }
            }
        }
    })
    
    return GenerateSceneResponse(
        scene_id=scene_id,
        status="queued",
        message="Scene generation queued",
        agent_executions=[]
    )


# =====================================================
# GENERATE SCENE (async)
# =====================================================

@router.post("/generate", response_model=GenerateSceneResponse)
async def generate_scene(
    request: GenerateSceneRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger scene generation (asynchronous)
    """
    log.info(
        "generate_scene_request",
        scene_id=request.scene_id,
        user_id=user.id,
        prompt=request.prompt[:100]
    )
    
    try:
        # Verify scene exists and belongs to user
        scene = db.query(Scene).filter(
            Scene.id == request.scene_id,
            Scene.user_id == user.id
        ).first()
        
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene not found"
            )
        
        # Check if already generating
        if scene.status == "rendering":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scene is already being generated"
            )
        
        # Update scene status
        scene.status = "rendering"
        scene.generation_prompt = request.prompt
        scene.generation_parameters = {
            "style": request.style,
            "budget": request.budget
        }
        scene.render_started_at = datetime.utcnow()
        db.commit()
        
        # Add background task to generate scene
        background_tasks.add_task(
            _generate_scene_background,
            scene_id=str(scene.id),
            user_id=str(user.id),
            prompt=request.prompt
        )
        
        log.info(
            "generate_scene_queued",
            scene_id=scene.id,
            user_id=user.id
        )
        
        return GenerateSceneResponse(
            scene_id=str(scene.id),
            status="queued",
            message="Scene generation started",
            agent_executions=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error("generate_scene_error", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start scene generation"
        )


# =====================================================
# BACKGROUND: GENERATE SCENE
# =====================================================

async def _generate_scene_background(scene_id: str, user_id: str, prompt: str):
    """
    Background task to generate scene using orchestrator agent
    """
    db = db_client.SessionLocal()
    execution_ids = []
    
    try:
        log.info("background_generation_start", scene_id=scene_id)
        
        # Initialize OpenRouter client
        openrouter_client = get_openrouter_client(settings.openrouter_api_key)
        
        # Create orchestrator agent
        orchestrator = await create_orchestrator_agent(openrouter_client)
        
        # Run orchestration
        result = await orchestrator.process_prompt(
            user_prompt=prompt,
            scene_id=scene_id,
            user_id=user_id,
            db=db
        )
        
        # Update scene with result
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        
        if result["status"] == "success":
            scene.status = "completed"
            scene.scene_graph = result["scene_graph"].to_dict()
            scene.completed_at = datetime.utcnow()
            log.info("scene_generation_success", scene_id=scene_id)
        elif result["status"] == "warning":
            scene.status = "completed"
            scene.scene_graph = result["scene_graph"].to_dict()
            scene.completed_at = datetime.utcnow()
            log.warning("scene_generation_warning", scene_id=scene_id)
        else:
            scene.status = "failed"
            log.error("scene_generation_failed", scene_id=scene_id, error=result.get("error"))
        
        scene.render_completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        log.error("background_generation_error", error=str(e), scene_id=scene_id)
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        if scene:
            scene.status = "failed"
            db.commit()
    finally:
        db.close()


# =====================================================
# GET AGENT EXECUTION
# =====================================================

@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
async def get_agent_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get agent execution details
    """
    log.info("get_agent_execution", execution_id=execution_id, user_id=user.id)
    
    try:
        execution = db.query(AgentExecution).filter(
            AgentExecution.id == execution_id,
            AgentExecution.user_id == user.id
        ).first()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        return AgentExecutionResponse(
            id=str(execution.id),
            scene_id=str(execution.scene_id) if execution.scene_id else None,
            agent_name=execution.agent_name,
            agent_role=execution.agent_role,
            status=execution.status,
            token_usage=execution.token_usage,
            execution_time_ms=execution.execution_time_ms,
            model_used=execution.model_used,
            error_message=execution.error_message,
            created_at=execution.created_at,
            completed_at=execution.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("get_agent_execution_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution"
        )


# =====================================================
# LIST AGENT EXECUTIONS FOR SCENE
# =====================================================

@router.get("/{scene_id}/executions", response_model=List[AgentExecutionResponse])
async def list_scene_executions(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all agent executions for a scene
    """
    log.info("list_scene_executions", scene_id=scene_id, user_id=user.id)
    
    try:
        # Verify scene belongs to user
        scene = db.query(Scene).filter(
            Scene.id == scene_id,
            Scene.user_id == user.id
        ).first()
        
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene not found"
            )
        
        # Get executions
        executions = db.query(AgentExecution).filter(
            AgentExecution.scene_id == scene_id
        ).order_by(AgentExecution.created_at.desc()).all()
        
        return [
            AgentExecutionResponse(
                id=str(e.id),
                scene_id=str(e.scene_id) if e.scene_id else None,
                agent_name=e.agent_name,
                agent_role=e.agent_role,
                status=e.status,
                token_usage=e.token_usage,
                execution_time_ms=e.execution_time_ms,
                model_used=e.model_used,
                error_message=e.error_message,
                created_at=e.created_at,
                completed_at=e.completed_at
            )
            for e in executions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("list_scene_executions_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list executions"
        )


# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/health")
async def agents_health():
    """Health check for agents service"""
    return {"status": "ok", "service": "agents"}


# =====================================================
# PROCEDURAL GENERATION - High-quality building generator
# =====================================================

@router.post("/generate_simple")
async def generate_simple_fn(request: GenerateSceneRequest = None):
    print(">>> GEOMETRY AGENT STARTED")
    """Generate buildings procedurally"""
    import sys
    from fastapi.responses import JSONResponse
    import structlog
    log = structlog.get_logger()
    
    print(">>> GEOMETRY AGENT INIT", file=sys.stdout)
    print(">>> HANDLING REQUEST")
    log.info("GENERATE_SIMPLE_START", prompt=getattr(request, 'prompt', 'none'))
    try:
        # Parse request safely
        if request:
            prompt = str(request.prompt) if request.prompt else "villa"
            pw = int(request.plot_width or 20)
            pd = int(request.plot_depth or 30)
        else:
            prompt = "villa"
            pw = 20
            pd = 30
            
        
        print(">>> IMPORTING SMART ARCHITECT", file=sys.stdout)
        from backend.services.architect import architect
        
        p = prompt.lower()
        bt = "villa" if "villa" in p else "house"
        sty = "modern"
        fl = 2
        
        
        print(">>> CALLING PROCEDURAL", file=sys.stdout)
        res = generate_building(btype=bt, style=sty, floors=fl, pw=pw, pd=pd, beds=3, garage=True, pool=False, garden=True)
        
        print(">>> RETURNING RESPONSE", file=sys.stdout)
        return JSONResponse(content={
            "scene_id": str(uuid.uuid4()),
            "status": "completed",
            "message": f"Generated {result.get('element_count', 0)} elements",
            "scene_data": {"geometry": {"meshes": result["meshes"], "materials": result["materials"]}}
        })
    except Exception as e:
        return JSONResponse(content={
            "scene_id": str(uuid.uuid4()),
            "status": "error",
            "message": str(e),
            "scene_data": {}
        }, status_code=500)


@router.post("/agents/modify")
async def modify_building(request: ModifyRequest):
    """Modify existing building by adding/removing features"""
    try:
        from backend.services.chat_agent import ChatArchitect, update_building
        from backend.services.architect import MATERIALS
        
        # Get current meshes from prior generation
        current_meshes = request.meshes or []
        current_materials = request.materials or list(MATERIALS.keys())
        
        # Use chat architect
        ca = update_building(current_meshes, current_materials)
        result = ca.modify(request.command)
        
        if "error" in result:
            return JSONResponse(content={"status": "error", "message": result["error"]})
        
        return JSONResponse(content={
            "status": "completed",
            "message": result["message"],
            "scene_data": {
                "geometry": {"meshes": result["meshes"], "materials": result["materials"]},
                "element_count": result["count"]
            }
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


class ModifyRequest(BaseModel):
    command: str
    meshes: Optional[List[Dict]] = None
    materials: Optional[List[Dict]] = None
