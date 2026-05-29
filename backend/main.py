"""
AI Architect — FastAPI Main Application
Production-ready multi-agent architectural AI platform
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog
import json
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from pydantic import BaseModel
from datetime import datetime

from backend.config import settings
from backend.routers import projects, agents, scenes, assets, auth, compliance
from backend.routers.artifacts_router import router as artifacts_router
from backend.routers.render_jobs_router import router as render_jobs_router
from backend.routers.styles_router import router as styles_router
from backend.routers.assets_router import router as assets_library_router
from backend.routers.sketchfab_assets import router as sketchfab_router
from backend.api import router as mvp_router
from backend.websocket_manager import ws_manager
from backend.database.client import db_client
from backend.config import settings
from backend.utils.toon import toon_encode, toon_decode, TOON_CONTENT_TYPE
from backend.services.artifacts import artifact_pipeline
from backend.services.render_queue import render_queue
from backend.services.storage import storage_manager

log = structlog.get_logger()


# =====================================================
# STARTUP / SHUTDOWN
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — DB failures are non-fatal."""

    log.info(
        "app_startup",
        app=settings.app_name,
        version=settings.app_version,
    )

    # Try to init DB but never let it stop the server from starting
    try:
        await db_client.init_db()
    except Exception as e:
        log.error("database_init_failed", error=str(e),
                  note="Server continuing — procedural endpoints are unaffected")

    db_ok = db_client.health_check()
    if db_ok:
        log.info("database_connected")
    else:
        log.warning("database_unavailable — DB-dependent routes will return 503; "
                    "generate_simple / procedural routes work fine without DB")

    storage_backend = getattr(settings, 'artifact_storage_backend', 'local')
    if storage_backend == 'r2' and settings.cloudflare_r2_endpoint:
        storage_manager.initialize(settings)
        log.info("artifact_storage_r2_initialized")
    else:
        storage_manager.initialize()
        log.info("artifact_storage_local_initialized")

    redis_url = settings.render_queue_redis_url or settings.upstash_redis_url
    if redis_url:
        render_queue.initialize(redis_url)
        log.info("render_queue_redis_initialized")
    else:
        render_queue.initialize()
        log.info("render_queue_local_initialized")

    from backend.websocket_manager import ws_manager
    async def notify_artifact_progress(payload):
        try:
            scene_id = payload.get("scene_id", "")
            await ws_manager.broadcast(payload, subscription_id=scene_id)
        except Exception:
            pass
    artifact_pipeline.on_progress(notify_artifact_progress)
    log.info("artifact_pipeline_initialized")
    yield

    log.info("app_shutdown")


# =====================================================
# APP INITIALIZATION
# =====================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-native Spatial Architecture Platform",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


class ApiResponseWrapperMiddleware(BaseHTTPMiddleware):
    """Wrap /api/* responses into a canonical envelope.
    Supports TOON (Accept: application/x-toon) for compact token-oriented encoding.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        try:
            path = request.url.path
        except Exception:
            return response

        if not path.startswith("/api/"):
            return response

        use_toon = TOON_CONTENT_TYPE in request.headers.get("accept", "")

        try:
            body = await response.body()
        except Exception:
            return response

        if not body:
            return response

        try:
            original = json.loads(body)
        except Exception:
            return response

        if isinstance(original, dict) and original.get("success") is not None:
            return response

        envelope = {
            "success": 200 <= response.status_code < 400,
            "data": original,
            "metadata": {"path": path, "status_code": response.status_code},
        }

        if isinstance(original, dict) and ("scene_graph" in original or "rooms" in original or "geometry" in original):
            envelope["scene"] = original

        if use_toon:
            toon_body = toon_encode(envelope)
            from fastapi.responses import Response
            return Response(
                content=toon_body,
                status_code=response.status_code,
                media_type=TOON_CONTENT_TYPE,
                headers=dict(response.headers),
            )

        return JSONResponse(envelope, status_code=response.status_code)


# =====================================================
# MIDDLEWARE
# =====================================================

# NOTE: FastAPI applies middleware in reverse registration order.
# CORSMiddleware must be registered FIRST so it runs first on every request,
# including OPTIONS preflight — before ApiResponseWrapperMiddleware touches them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Number"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(ApiResponseWrapperMiddleware)


# Temporary debug endpoints to assist with deployment initialization problems.
# These endpoints are intentionally simple and should be removed or secured for production.


class DebugInitRequest(BaseModel):
    secret: str


@app.post("/debug/db_init")
async def debug_db_init(body: DebugInitRequest):
    """Trigger database initialization remotely. Requires matching secret to avoid misuse.

    Accepts JSON body: {"secret": "..."}
    Use this from CI or Railway console when automatic init fails.
    """
    if not getattr(settings, "debug_secret", None):
        return {"status": "error", "detail": "No debug secret configured"}

    if body.secret != settings.debug_secret:
        return {"status": "error", "detail": "Invalid secret"}

    try:
        await db_client.init_db()
        return {"status": "ok", "detail": "db initialized"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}





# =====================================================
# GLOBAL EXCEPTION HANDLERS
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_type=type(exc).__name__
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


# =====================================================
# ROUTERS
# =====================================================

app.include_router(auth.router,     prefix="/api/auth",     tags=["authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(scenes.router, prefix="/api/scenes", tags=["scenes"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["compliance"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(render_jobs_router, prefix="/api/render-jobs", tags=["render-jobs"])
app.include_router(styles_router, prefix="/api", tags=["styles"])
app.include_router(assets_library_router, prefix="/api/assets-library", tags=["assets-library"])
app.include_router(sketchfab_router, prefix="/api/sketchfab", tags=["sketchfab"])
app.include_router(mvp_router, prefix="/api", tags=["mvp-pipeline"])
app.include_router(mvp_router, tags=["mvp-pipeline"])

# Serve cached GLB files from Sketchfab
import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles
_sketchfab_cache = _os.path.join(_os.path.dirname(__file__), "..", "cache", "sketchfab")
_os.makedirs(_sketchfab_cache, exist_ok=True)
app.mount("/cache/sketchfab", _StaticFiles(directory=_sketchfab_cache), name="sketchfab_cache")
_exports_dir = _os.path.join(_os.path.dirname(__file__), "..", "exports")
_os.makedirs(_exports_dir, exist_ok=True)
app.mount("/exports", _StaticFiles(directory=_exports_dir), name="exports")


# =====================================================
# WEBSOCKET — legacy (client_id) + session-based
# =====================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, format: str = "json"):
    """
    Legacy WebSocket endpoint (client_id-based).
    Appends ?format=toon to use compact token-oriented encoding.
    """
    fmt = format or websocket.query_params.get("format", "json")
    await ws_manager.connect(client_id, websocket, fmt=fmt)
    log.info("websocket_connected_legacy", client_id=client_id, format=fmt)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw) if raw.startswith("{") or raw.startswith("[") else toon_decode(raw)
            await ws_manager.handle_message(client_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        log.info("websocket_disconnected_legacy", client_id=client_id)
    except Exception as e:
        log.error("websocket_error_legacy", client_id=client_id, error=str(e))
        ws_manager.disconnect(client_id)


@app.websocket("/ws/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str, format: str = "json"):
    """
    Session-based WebSocket endpoint.
    Appends ?format=toon for compact token-oriented encoding.
    """
    fmt = format or websocket.query_params.get("format", "json")
    client_id = f"session_{session_id}_{datetime.utcnow().timestamp()}"
    await ws_manager.join_session(session_id, client_id, websocket, fmt=fmt)
    log.info("websocket_session_connected", session_id=session_id, client_id=client_id, format=fmt)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw) if raw.startswith("{") or raw.startswith("[") else toon_decode(raw)
            msg_type = data.get("type", data.get("event", "unknown"))
            if msg_type == "ping":
                await ws_manager.send_to_client(client_id,
                    {"type": "pong", "session_id": session_id,
                     "timestamp": datetime.utcnow().isoformat()})
            else:
                data["session_id"] = session_id
                await ws_manager.broadcast_session(session_id, data)
    except WebSocketDisconnect:
        ws_manager.leave_session(session_id, client_id)
        ws_manager.disconnect(client_id)
        log.info("websocket_session_disconnected", session_id=session_id, client_id=client_id)
    except Exception as e:
        log.error("websocket_session_error", session_id=session_id, client_id=client_id, error=str(e))
        ws_manager.leave_session(session_id, client_id)
        ws_manager.disconnect(client_id)


# =====================================================
# HEALTH & STATUS
# =====================================================

@app.get("/health")
async def health_check():
    db_healthy = db_client.health_check()
    return {
        "status": "ok",          # Server is always ok — DB is optional
        "version": settings.app_version,
        "database": "connected" if db_healthy else "unavailable (procedural mode)",
    }


@app.get("/status")
async def status():
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "description": "AI Architect — Multi-Agent Spatial Architecture Platform",
        "features": [
            "Procedural Building Generation (no DB required)",
            "Indian NBC / Vastu Compliance Audit",
            "Real-time WebSocket Agent Updates",
            "Multi-Agent Orchestration (LangGraph)",
            "3D Gaussian Splatting Rendering",
            "Real-time Scene Generation",
            "Procedural Architecture",
            "Semantic Scene Understanding",
            "Drone Navigation AI",
            "WebSocket Real-time Sync",
            "PostgreSQL + pgvector",
            "Progressive Artifact Pipeline",
            "Blender Cloud Rendering",
            "Design Style Engine",
            "Multi-Output Modes",
            "Render Job Queue",
            "PBR Material Library",
            "Cloudflare R2 Storage",
            "9 Camera Projections + Drone Flyby"
        ],
        "api_docs": "/api/docs",
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Architect",
        "documentation": "/api/docs",
        "health": "/health",
        "status": "/status",
        "api": {
            "auth": "/api/auth",
            "projects": "/api/projects",
            "scenes": "/api/scenes",
            "agents": "/api/agents",
            "assets": "/api/assets",
            "artifacts": "/api/artifacts",
            "render-jobs": "/api/render-jobs",
            "styles": "/api/styles",
            "assets-library": "/api/assets-library"
        }
    }
