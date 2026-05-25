"""
Typed WebSocket event schemas for real-time communication.
All events follow a strict type + payload envelope.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    # Connection lifecycle
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_CLOSED = "connection.closed"
    PING = "ping"
    PONG = "pong"

    # Session management
    SESSION_JOINED = "session.joined"
    SESSION_LEFT = "session.left"
    SESSION_ERROR = "session.error"

    # Agent lifecycle phases
    ORCHESTRATOR_STARTED = "agent.orchestrator.started"
    ORCHESTRATOR_COMPLETE = "agent.orchestrator.complete"
    ORCHESTRATOR_FAILED = "agent.orchestrator.failed"

    PLANNER_PHASE = "agent.planner"
    LAYOUT_PHASE = "agent.layout"
    GEOMETRY_PHASE = "agent.geometry"
    ASSET_PHASE = "agent.asset"
    VISUALIZATION_PHASE = "agent.visualization"
    EVALUATION_PHASE = "agent.evaluation"
    COMPLIANCE_PHASE = "agent.compliance"

    # Scene updates
    SCENE_CREATED = "scene.created"
    SCENE_UPDATED = "scene.updated"
    SCENE_DELETED = "scene.deleted"
    SCENE_VALIDATED = "scene.validated"
    SCENE_INVALID = "scene.invalid"

    # Artifact delivery
    ARTIFACT_FLOORPLAN = "artifact.floorplan"
    ARTIFACT_PREVIEW = "artifact.preview"
    ARTIFACT_RENDER = "artifact.render"
    ARTIFACT_WALKTHROUGH = "artifact.walkthrough"
    ARTIFACT_GLTF = "artifact.gltf"

    # Progress
    PROGRESS_STEP = "progress.step"
    PROGRESS_PERCENT = "progress.percent"

    # Error
    ERROR_GENERAL = "error.general"
    ERROR_VALIDATION = "error.validation"


class BaseEvent(BaseModel):
    type: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None
    scene_id: Optional[str] = None


class ConnectionEstablished(BaseEvent):
    type: str = EventType.CONNECTION_ESTABLISHED
    client_id: str
    message: str = "Connected to AI Architect"


class PingEvent(BaseEvent):
    type: str = EventType.PING


class PongEvent(BaseEvent):
    type: str = EventType.PONG


class SessionJoined(BaseEvent):
    type: str = EventType.SESSION_JOINED
    session_id: str


class SessionLeft(BaseEvent):
    type: str = EventType.SESSION_LEFT
    session_id: str


class AgentPhaseEvent(BaseEvent):
    type: str
    agent: str
    phase: str  # started, processing, complete, failed
    message: str
    data: Optional[Dict[str, Any]] = None
    progress_pct: Optional[int] = None
    duration_ms: Optional[int] = None


class SceneUpdateEvent(BaseEvent):
    type: str = EventType.SCENE_UPDATED
    change_type: str  # geometry, material, lighting, furniture
    changes: Dict[str, Any]


class SceneValidatedEvent(BaseEvent):
    type: str = EventType.SCENE_VALIDATED
    valid: bool
    errors: List[str] = []


class ProgressEvent(BaseEvent):
    type: str = EventType.PROGRESS_PERCENT
    percent: int
    label: str


class ArtifactEvent(BaseEvent):
    type: str
    artifact_url: str
    artifact_type: str  # png, gltf, glb, mp4, ifc
    preview_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ErrorEvent(BaseEvent):
    type: str = EventType.ERROR_GENERAL
    error: str
    detail: Optional[str] = None


def make_agent_event(
    event_type: EventType,
    agent: str,
    phase: str,
    message: str,
    scene_id: Optional[str] = None,
    session_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    progress_pct: Optional[int] = None,
) -> AgentPhaseEvent:
    return AgentPhaseEvent(
        type=event_type.value if isinstance(event_type, EventType) else event_type,
        agent=agent,
        phase=phase,
        message=message,
        scene_id=scene_id,
        session_id=session_id,
        data=data,
        progress_pct=progress_pct,
    )
