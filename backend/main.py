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
    """Application lifecycle management"""
    
    # STARTUP
    log.info(
        "app_startup",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment if hasattr(settings, 'environment') else 'unknown'
    )
    
    # Initialize database
    try:
        await db_client.init_db()
        log.info("database_initialized")
    except Exception as e:
        log.error("database_init_failed", error=str(e))
    
    # Health check database
    if db_client.health_check():
        log.info("database_health_check_passed")
    else:
        log.error("database_health_check_failed")
    
    yield
    
    # SHUTDOWN
    log.info("app_shutdown")


# =====================================================
# APP INITIALIZATION
# =====================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-native Spatial Architecture Platform — Generate, visualize, and explore buildings with Multi-Agent AI + 3D Gaussian Splatting",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# =====================================================
# MIDDLEWARE
# =====================================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Number"],
)

# GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# =====================================================
# GLOBAL EXCEPTION HANDLERS
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    log.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )


# =====================================================
# ROUTERS
# =====================================================

app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(scenes.router, prefix="/api/scenes", tags=["scenes"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])


# =====================================================
# WEBSOCKET
# =====================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time agent updates and scene streaming
    """
    await ws_manager.connect(client_id, websocket)
    log.info("websocket_connected", client_id=client_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Route WebSocket messages
            await ws_manager.handle_message(client_id, data)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        log.info("websocket_disconnected", client_id=client_id)
    
    except Exception as e:
        log.error("websocket_error", client_id=client_id, error=str(e))
        await ws_manager.disconnect(client_id)


# =====================================================
# HEALTH & STATUS ENDPOINTS
# =====================================================

@app.get("/health")
async def health_check():
    """
    Application health check
    """
    db_healthy = db_client.health_check()
    
    return {
        "status": "ok" if db_healthy else "degraded",
        "version": settings.app_version,
        "database": "connected" if db_healthy else "disconnected"
    }


@app.get("/status")
async def status():
    """
    Application status and metrics
    """
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "description": "AI Architect — Multi-Agent Spatial Architecture Platform",
        "features": [
            "Multi-Agent Orchestration (LangGraph)",
            "3D Gaussian Splatting Rendering",
            "Real-time Scene Generation",
            "Procedural Architecture",
            "Semantic Scene Understanding",
            "Drone Navigation AI",
            "WebSocket Real-time Sync",
            "PostgreSQL + pgvector"
        ],
        "api_docs": "/api/docs",
        "api_version": settings.app_version
    }


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
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
            "assets": "/api/assets"
        }
    }


# =====================================================
# STARTUP LOGGING
# =====================================================

@app.on_event("startup")
async def startup():
    """Startup event"""
    log.info("api_server_started", port=8000)


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event"""
    log.info("api_server_stopped")
