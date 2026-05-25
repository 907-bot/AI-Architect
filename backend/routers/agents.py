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
from backend.websocket_manager import ws_manager

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

class GenerateSceneRequest(BaseModel):
    scene_id: Optional[str] = None
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    prompt: str
    style: Optional[str] = "modern"
    budget: Optional[str] = "medium"
    output_mode: Optional[str] = "fast_preview"
    plot_lat: Optional[float] = None
    plot_lng: Optional[float] = None
    plot_width: Optional[float] = None
    plot_depth: Optional[float] = None
    wall_color: Optional[str] = "white"
    roof_style: Optional[str] = "gable"
    window_glass: Optional[str] = "clear"
    floors: Optional[int] = None
    has_balcony: Optional[bool] = True
    has_garage: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garden: Optional[bool] = True


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
        # Determine which scene to use/create
        scene = None

        if request.scene_id:
            # Use existing scene
            scene = db.query(Scene).filter(
                Scene.id == request.scene_id,
                Scene.user_id == user.id
            ).first()

            if not scene:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Scene not found"
                )

            if scene.status == "rendering":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Scene is already being generated"
                )

            # Update existing scene
            scene.status = "rendering"
            scene.generation_prompt = request.prompt
            scene.generation_parameters = {
                "style": request.style,
                "budget": request.budget,
                "output_mode": request.output_mode,
                "plot_lat": request.plot_lat,
                "plot_lng": request.plot_lng,
                "plot_width": request.plot_width,
                "plot_depth": request.plot_depth,
            }
            scene.render_started_at = datetime.utcnow()
            db.commit()

        elif request.project_id:
            # Create a new scene for the project
            project = db.query(Project).filter(
                Project.id == request.project_id,
                Project.user_id == user.id
            ).first()

            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )

            # Minimal default scene_graph (same shape as create_scene)
            default_scene_graph = {
                "rooms": [],
                "walls": [],
                "windows": [],
                "doors": [],
                "stairs": [],
                "furniture": [],
                "materials": [],
                "lighting": [],
                "navigation": []
            }

            scene = Scene(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=user.id,
                name=(request.prompt[:80] or "Auto-generated Scene"),
                description=None,
                generation_prompt=request.prompt,
                status="rendering",
                version=1,
                output_mode=request.output_mode or "fast_preview",
                scene_graph=default_scene_graph,
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

        else:
            # Neither scene_id nor project_id provided
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either scene_id or project_id must be provided"
            )

        # Add background task to generate scene. Pass client_id if provided so we can notify socket directly.
        background_tasks.add_task(
            _generate_scene_background,
            scene_id=str(scene.id),
            user_id=str(user.id),
            prompt=request.prompt,
            client_id=request.client_id
        )

        log.info(
            "generate_scene_queued",
            scene_id=scene.id,
            user_id=user.id,
            client_id=request.client_id
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

async def _generate_scene_background(scene_id: str, user_id: str, prompt: str, client_id: Optional[str] = None):
    """
    Background task to generate scene using orchestrator agent.
    Emits typed phase events for progressive artifact delivery.
    """
    if db_client.SessionLocal is None:
        log.warning('background_task_skipped_no_db')
        return
    db = db_client.SessionLocal()
    execution_ids = []
    openrouter_client = None

    async def _notify(event_type: str, agent: str, phase: str, message: str, data: Optional[Dict] = None, pct: Optional[int] = None):
        payload = {
            "type": event_type,
            "agent": agent,
            "phase": phase,
            "message": message,
            "scene_id": scene_id,
            "data": data,
            "progress_pct": pct,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            if client_id:
                await ws_manager.send_to_client(client_id, payload)
            # Also broadcast to session if client_id maps to one
            sessions = ws_manager.client_sessions.get(client_id or "", set())
            for sid in sessions:
                await ws_manager.broadcast_session(sid, payload)
            # Fallback broadcast
            await ws_manager.broadcast(payload, subscription_id=scene_id)
        except Exception:
            pass

    try:
        log.info("background_generation_start", scene_id=scene_id)
        await _notify("agent.orchestrator", "orchestrator", "started", "Generation started", {"prompt": prompt[:400]}, 0)

        # Phase 1: Intent extraction
        await _notify("agent.orchestrator", "orchestrator", "processing", "Extracting architectural intent", None, 10)
        openrouter_client = get_openrouter_client(settings.openrouter_api_key)
        orchestrator = await create_orchestrator_agent(openrouter_client)

        # Phase 2: Planning
        await _notify("agent.planner", "planner", "processing", "Creating architectural plan", None, 25)
        result = await orchestrator.process_prompt(
            user_prompt=prompt, scene_id=scene_id, user_id=user_id, db=db
        )

        # Phase 3: Geometry generation
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        sg = result.get("scene_graph") if isinstance(result, dict) else None
        if sg:
            await _notify("agent.geometry", "geometry", "processing", "Generating 3D geometry", None, 50)

            # Convert to dict for frontend compatibility
            geo_dict = sg.to_dict() if hasattr(sg, "to_dict") else (
                sg if isinstance(sg, dict) else {}
            )
            room_count = len(geo_dict.get("rooms", []))
            await _notify("agent.geometry", "geometry", "complete",
                          f"Generated {room_count} rooms", geo_dict, 70)

        # Phase 4: Assets & materials
        if scene and sg:
            materials = geo_dict.get("materials", []) if isinstance(geo_dict, dict) else []
            await _notify("agent.asset", "asset", "processing",
                          f"Assigning {len(materials)} materials", None, 85)

        # Phase 5: Generate artifacts from scene graph
        if sg and scene:
            from backend.services.artifacts import artifact_pipeline
            output_mode = getattr(scene, 'output_mode', 'fast_preview') or 'fast_preview'
            await _notify("artifact.pipeline", "pipeline", "processing",
                          f"Starting artifact generation ({output_mode})", None, 80)
            artifacts = await artifact_pipeline.generate_progressive(
                scene_id=scene_id,
                scene_graph=geo_dict if isinstance(geo_dict, dict) else {},
                output_mode=output_mode,
            )
            artifact_urls = artifact_pipeline.get_artifact_urls(scene_id)
            await _notify("artifact.pipeline", "pipeline", "complete",
                          f"Generated {len(artifacts)} artifacts", {"urls": artifact_urls}, 90)

        # Phase 6: Evaluation
        validation_errors = result.get("validation_errors", []) if isinstance(result, dict) else []
        is_success = isinstance(result, dict) and result.get("status") == "success"
        await _notify(
            "agent.evaluation" if is_success else "scene.invalid",
            "evaluation",
            "complete" if is_success else "failed",
            "Evaluation complete" if is_success else f"Validation issues: {len(validation_errors)}",
            result if isinstance(result, dict) else {},
            100
        )

        # Create AgentExecution record
        try:
            exec_record = AgentExecution(
                id=uuid.uuid4(),
                scene_id=scene.id if scene else None,
                project_id=scene.project_id if scene else None,
                user_id=user_id,
                agent_name="orchestrator",
                agent_role="primary",
                status=result.get("status", "error") if isinstance(result, dict) else "error",
                input_prompt=prompt,
                output_result=result if isinstance(result, dict) else {"result": str(result)},
                token_usage=(result.get("tokens_used", {}) if isinstance(result, dict) else {}),
                model_used=(result.get("agent_plan", {}).get("model") if isinstance(result, dict) else None)
            )
            db.add(exec_record)
        except Exception as e:
            log.warning("agent_execution_create_failed", error=str(e))

        if isinstance(result, dict) and result.get("status") == "success":
            if scene:
                scene.status = "completed"
                # scene_graph may be a SceneGraph object or dict
                sg = result.get("scene_graph")
                scene.scene_graph = sg.to_dict() if hasattr(sg, "to_dict") else sg
                scene.completed_at = datetime.utcnow()
            log.info("scene_generation_success", scene_id=scene_id)

        elif isinstance(result, dict) and result.get("status") == "warning":
            if scene:
                scene.status = "completed"
                sg = result.get("scene_graph")
                scene.scene_graph = sg.to_dict() if hasattr(sg, "to_dict") else sg
                scene.completed_at = datetime.utcnow()
            log.warning("scene_generation_warning", scene_id=scene_id, warnings=result.get("validation_errors"))

        else:
            if scene:
                scene.status = "failed"
            # Log full result for debugging
            log.error("scene_generation_failed", scene_id=scene_id, result=result)

        if scene:
            scene.render_completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        log.error("background_generation_error", error=str(e), scene_id=scene_id)
        try:
            await _notify("error.general", "orchestrator", "failed", str(e), None, 0)
        except Exception:
            pass
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
    """Generate buildings procedurally from a prompt + ConfigPanel options"""
    import sys
    from fastapi.responses import JSONResponse
    log.info("GENERATE_SIMPLE_START", prompt=getattr(request, 'prompt', 'none'))

    try:
        # --- Parse request safely ---
        prompt = str(request.prompt) if request and request.prompt else "villa"
        pw = float(request.plot_width or 20) if request else 20.0
        pd_val = float(request.plot_depth or 30) if request else 30.0

        # --- Fields from ConfigPanel (sent as extra JSON keys) ---
        cfg_wall_color  = request.wall_color  if request else "white"
        cfg_roof_style  = request.roof_style  if request else "gable"
        cfg_floors_hint = request.floors      if request else None
        cfg_garage      = request.has_garage  if request else None
        cfg_pool        = request.has_pool    if request else None
        cfg_garden      = request.has_garden  if request else True

        from backend.services.procedural import generate_building

        p = prompt.lower()

        # --- Building type ---
        if "apartment" in p or "flat" in p:
            bt = "apartment"
        elif "villa" in p:
            bt = "villa"
        else:
            bt = "house"

        # --- Floor count: prompt wins, then ConfigPanel, then default 2 ---
        floors = 2
        words = p.replace("-", " ").replace("storey", " floors").replace("story", " floors").split()
        for i, w in enumerate(words):
            if w.isdigit():
                floors = max(1, min(int(w), 10))
                break
        if cfg_floors_hint and floors == 2:   # only override if prompt didn't specify
            floors = max(1, min(int(cfg_floors_hint), 10))

        # --- Features: prompt wins, then ConfigPanel, then sensible default ---
        has_pool   = "pool"   in p if "pool"   in p else (cfg_pool   if cfg_pool   is not None else False)
        has_garage = "garage" in p if "garage" in p else (cfg_garage if cfg_garage is not None else True)
        has_garden = cfg_garden if cfg_garden is not None else True

        # --- Color scheme: prompt wins, then ConfigPanel ---
        if "cream" in p or "beige" in p:
            color_scheme = "cream"
        elif "red brick" in p or "red " in p:
            color_scheme = "red"
        elif "dark" in p or "black" in p:
            color_scheme = "dark"
        elif "white" in p:
            color_scheme = "white"
        else:
            # Fall back to ConfigPanel wall color selection
            color_scheme = cfg_wall_color or "white"

        # Roof style: ConfigPanel or gable default
        roof_style = cfg_roof_style or "gable"

        log.info("generate_simple_params", bt=bt, floors=floors, pool=has_pool,
                 garage=has_garage, garden=has_garden, color=color_scheme, roof=roof_style)

        res = generate_building(
            btype=bt, style="modern", floors=floors,
            pw=pw, pd=pd_val,
            beds=3,
            garage=has_garage, pool=has_pool, garden=has_garden,
            color_scheme=color_scheme, roof_style=roof_style
        )

        # --- Build NBC compliance data ---
        plot_area   = pw * pd_val
        floor_area  = pw * 0.6 * pd_val * 0.6 * floors      # approx footprint × floors
        actual_far  = round(floor_area / plot_area, 2) if plot_area > 0 else 0
        footprint   = pw * 0.6 * pd_val * 0.6
        coverage_pct = round((footprint / plot_area) * 100, 1) if plot_area > 0 else 0
        allowed_far  = 2.5
        allowed_cov  = 60.0

        issues = []
        if actual_far > allowed_far:
            issues.append(f"FAR of {actual_far} exceeds the NBC limit of {allowed_far}.")
        if coverage_pct > allowed_cov:
            issues.append(f"Ground coverage {coverage_pct}% exceeds the NBC limit of {allowed_cov}%.")

        compliance = {
            "compliant": len(issues) == 0,
            "issues": issues,
            "actual_far": actual_far,
            "allowed_far": allowed_far,
            "actual_coverage_pct": coverage_pct,
            "allowed_coverage_pct": allowed_cov,
            "vastu_suggestions": [
                "Main entrance is recommended in the North, East, or North-East corner.",
                "Kitchen is best placed in the South-East (Agneya) corner.",
                "Master bedroom performs best in the South-West zone.",
            ]
        }

        return JSONResponse(content={
            "scene_id": str(uuid.uuid4()),
            "status": "completed",
            "message": f"{bt.title()} — {floors} floor{'s' if floors != 1 else ''}",
            "scene_data": {
                "geometry": {
                    "meshes": res["meshes"],
                    "materials": res.get("materials", [])
                },
                "compliance": compliance
            }
        })

    except Exception as e:
        log.error("generate_simple_error", error=str(e))
        import traceback
        return JSONResponse(content={
            "scene_id": str(uuid.uuid4()),
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "scene_data": {}
        }, status_code=500)


@router.post("/modify")
async def modify_building(request: dict):
    """Modify existing building by adding/removing features"""
    try:
        from backend.services.chat_agent import ChatArchitect, update_building
        from backend.services.architect import MATERIALS
        
        # Get current meshes from prior generation
        current_meshes = request.meshes or []
        current_materials = request.materials or list(MATERIALS.keys())
        
        # Use chat architect
        ca = update_building(current_meshes, current_materials)
        result = ca.modify(request.get("command", ""))
        
        if "error" in result:
            return JSONResponse(content={"status": "error", "message": result["error"]})
        
        return JSONResponse(content={
            "status": "completed",
            "message": result["message"],
            "scene_data": {
                "geometry": {"meshes": result["meshes"], "materials": result.get("materials", [])},
                "element_count": len(result.get("meshes", []))
            }
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


class ModifyRequest(BaseModel):
    command: str
    meshes: Optional[List[Dict]] = None
    materials: Optional[List[Dict]] = None
