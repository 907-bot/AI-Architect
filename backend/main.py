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

from backend.config import settings
from backend.routers import projects, agents, scenes, assets, auth
from backend.websocket_manager import ws_manager
from backend.database.client import db_client

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


# =====================================================
# MIDDLEWARE
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Number"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


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
app.include_router(agents.router,   prefix="/api/agents",   tags=["agents"])
app.include_router(scenes.router,   prefix="/api/scenes",   tags=["scenes"])
app.include_router(assets.router,   prefix="/api/assets",   tags=["assets"])


# =====================================================
# WEBSOCKET
# =====================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await ws_manager.connect(client_id, websocket)
    log.info("websocket_connected", client_id=client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(client_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        log.info("websocket_disconnected", client_id=client_id)
    except Exception as e:
        log.error("websocket_error", client_id=client_id, error=str(e))
        await ws_manager.disconnect(client_id)


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
            "9 Camera Projections + Drone Flyby",
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
        }
    }
