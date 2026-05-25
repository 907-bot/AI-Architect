"""
Tests for typed WebSocket event schemas
"""
from backend.models.events import (
    EventType, ConnectionEstablished, AgentPhaseEvent,
    PingEvent, PongEvent, make_agent_event
)


def test_connection_established():
    event = ConnectionEstablished(client_id="abc123")
    d = event.model_dump()
    assert d["type"] == "connection.established"
    assert d["client_id"] == "abc123"
    assert "timestamp" in d


def test_ping_pong():
    ping = PingEvent()
    pong = PongEvent()
    assert ping.type == "ping"
    assert pong.type == "pong"


def test_agent_event():
    event = make_agent_event(
        EventType.ORCHESTRATOR_STARTED,
        agent="orchestrator",
        phase="started",
        message="Generation started",
        scene_id="scene_123",
        data={"prompt": "test"},
        progress_pct=10,
    )
    d = event.model_dump()
    assert isinstance(event, AgentPhaseEvent)
    assert d["type"] == "agent.orchestrator.started"
    assert d["agent"] == "orchestrator"
    assert d["phase"] == "started"
    assert d["scene_id"] == "scene_123"
    assert d["progress_pct"] == 10
    assert d["data"]["prompt"] == "test"


def test_event_type_enum_values():
    assert EventType.ORCHESTRATOR_COMPLETE.value == "agent.orchestrator.complete"
    assert EventType.SCENE_VALIDATED.value == "scene.validated"
    assert EventType.ARTIFACT_FLOORPLAN.value == "artifact.floorplan"
    assert EventType.ERROR_GENERAL.value == "error.general"


def test_agent_event_round_trip():
    event = make_agent_event(
        "agent.custom",
        agent="test_agent",
        phase="processing",
        message="Running test",
    )
    d = event.model_dump()
    restored = AgentPhaseEvent(**d)
    assert restored.type == "agent.custom"
    assert restored.agent == "test_agent"
    assert restored.phase == "processing"
