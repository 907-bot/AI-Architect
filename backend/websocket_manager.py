"""
WebSocket Manager v2 — session-based + typed event support.
Backward compatible with /ws/{client_id} but adds /ws/session/{session_id}.
"""

from fastapi import WebSocket
from typing import Dict, Set, Optional, Callable, Any, List
from datetime import datetime
from collections import defaultdict
import structlog
import json

from backend.models.events import (
    EventType, BaseEvent, ConnectionEstablished, PingEvent, PongEvent,
    AgentPhaseEvent, SceneUpdateEvent, ProgressEvent, ArtifactEvent,
    ErrorEvent, make_agent_event, SessionJoined, SessionLeft
)
from backend.utils.toon import toon_encode, toon_decode, TOON_CONTENT_TYPE

log = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections with session-based routing and typed events.
    """

    def __init__(self):
        # Legacy: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Session-based: {session_id: {client_id: websocket}}
        self.session_connections: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
        # Reverse lookup: {client_id: {session_ids}}
        self.client_sessions: Dict[str, Set[str]] = defaultdict(set)
        # Subscriptions legacy: {client_id: {subscription_id}}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)
        # Format per client: "json" or "toon"
        self.client_formats: Dict[str, str] = defaultdict(lambda: "json")
        # Handlers
        self.handlers: Dict[str, Callable] = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            EventType.PING.value: self._handle_ping,
            "ping": self._handle_ping,
            "get_status": self._handle_get_status,
        }

    # ============== Legacy (client_id-based) ==============

    async def connect(self, client_id: str, websocket: WebSocket, fmt: str = "json"):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        self.client_formats[client_id] = fmt if fmt in ("json", "toon") else "json"
        log.info("websocket_connected", client_id=client_id, format=fmt, active=len(self.active_connections))
        await self._send(websocket, ConnectionEstablished(
            client_id=client_id, message=f"Connected to AI Architect (format={fmt})"
        ).model_dump())

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        self.subscriptions.pop(client_id, None)
        self.client_formats.pop(client_id, None)
        for session_id in list(self.client_sessions.get(client_id, set())):
            self.session_connections.get(session_id, {}).pop(client_id, None)
            if not self.session_connections.get(session_id):
                self.session_connections.pop(session_id, None)
        self.client_sessions.pop(client_id, None)
        log.info("websocket_disconnected", client_id=client_id)

    # ============== Session-based ==============

    async def join_session(self, session_id: str, client_id: str, websocket: WebSocket, fmt: str = "json"):
        await websocket.accept()
        self.session_connections[session_id][client_id] = websocket
        self.client_sessions[client_id].add(session_id)
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        self.client_formats[client_id] = fmt if fmt in ("json", "toon") else "json"

        log.info("session_joined", session_id=session_id, client_id=client_id, format=fmt)
        await self._send(websocket, SessionJoined(session_id=session_id).model_dump())

    async def leave_session(self, session_id: str, client_id: str):
        self.session_connections.get(session_id, {}).pop(client_id, None)
        self.client_sessions.get(client_id, set()).discard(session_id)
        if not self.session_connections.get(session_id):
            self.session_connections.pop(session_id, None)
        log.info("session_left", session_id=session_id, client_id=client_id)

    def get_session_clients(self, session_id: str) -> List[str]:
        return list(self.session_connections.get(session_id, {}).keys())

    # ============== Message handling ==============

    async def handle_message(self, client_id: str, data: Dict[str, Any]):
        try:
            msg_type = data.get("type", data.get("event", "unknown"))
            log.info("websocket_message", client_id=client_id, type=msg_type)
            handler = self.handlers.get(msg_type)
            if handler:
                await handler(client_id, data)
            else:
                log.warning("unknown_message_type", type=msg_type)
        except Exception as e:
            log.error("websocket_message_error", client_id=client_id, error=str(e))

    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        sub_id = data.get("subscription_id")
        if sub_id:
            self.subscriptions[client_id].add(sub_id)
            log.info("client_subscribed", client_id=client_id, subscription_id=sub_id)
            if client_id in self.active_connections:
                await self._send(self.active_connections[client_id], {
                    "type": "subscribed", "subscription_id": sub_id
                })

    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        sub_id = data.get("subscription_id")
        if sub_id and sub_id in self.subscriptions.get(client_id, set()):
            self.subscriptions[client_id].discard(sub_id)

    async def _handle_ping(self, client_id: str, data: Dict[str, Any]):
        if client_id in self.active_connections:
            await self._send(self.active_connections[client_id],
                             PongEvent().model_dump())

    async def _handle_get_status(self, client_id: str, data: Dict[str, Any]):
        if client_id in self.active_connections:
            await self._send(self.active_connections[client_id], {
                "type": "status",
                "client_id": client_id,
                "subscriptions": list(self.subscriptions.get(client_id, [])),
                "active_connections": len(self.active_connections),
                "sessions": list(self.client_sessions.get(client_id, set())),
            })

    # ============== Sending (TOON-aware) ==============

    async def _send(self, websocket: WebSocket, message: Dict[str, Any], client_id: Optional[str] = None):
        try:
            if isinstance(message, BaseEvent):
                message = message.model_dump()
            fmt = self.client_formats.get(client_id or "", "json")
            if fmt == "toon":
                await websocket.send_text(toon_encode(message))
            else:
                await websocket.send_json(message)
        except Exception as e:
            log.error("websocket_send_error", error=str(e))
            raise

    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        if client_id not in self.active_connections:
            log.warning("client_not_connected", client_id=client_id)
            return
        try:
            await self._send(self.active_connections[client_id], message, client_id)
        except Exception as e:
            log.error("send_to_client_error", client_id=client_id, error=str(e))
            self.disconnect(client_id)

    async def send_to_session(self, session_id: str, message: Dict[str, Any], exclude_client: Optional[str] = None):
        connections = self.session_connections.get(session_id, {})
        for cid, ws in connections.items():
            if cid == exclude_client:
                continue
            try:
                await self._send(ws, message)
            except Exception as e:
                log.error("session_send_error", session_id=session_id, client_id=cid, error=str(e))

    async def broadcast(self, message: Dict[str, Any], subscription_id: Optional[str] = None):
        disconnected = []
        for client_id, websocket in list(self.active_connections.items()):
            if subscription_id and subscription_id not in self.subscriptions.get(client_id, set()):
                continue
            try:
                await self._send(websocket, message)
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)

    async def broadcast_session(self, session_id: str, message: Dict[str, Any]):
        await self.send_to_session(session_id, message)

    # ============== Typed event helpers ==============

    async def notify_agent_update(
        self,
        agent: str,
        phase: str,
        message: str,
        scene_id: Optional[str] = None,
        session_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ):
        event = make_agent_event(
            EventType.ORCHESTRATOR_STARTED if phase == "started"
            else EventType.ORCHESTRATOR_FAILED if phase == "failed"
            else EventType.ORCHESTRATOR_COMPLETE,
            agent=agent, phase=phase, message=message,
            scene_id=scene_id, session_id=session_id, data=data,
        )
        payload = event.model_dump()
        if client_id:
            await self.send_to_client(client_id, payload)
        elif session_id:
            await self.broadcast_session(session_id, payload)
        else:
            await self.broadcast(payload, subscription_id=scene_id)

    async def notify_scene_update(self, scene_id: str, change_type: str, changes: Dict[str, Any]):
        event = SceneUpdateEvent(scene_id=scene_id, change_type=change_type, changes=changes)
        await self.broadcast(event.model_dump(), subscription_id=scene_id)

    async def notify_progress(self, scene_id: str, percent: int, label: str):
        event = ProgressEvent(percent=percent, label=label, scene_id=scene_id)
        await self.broadcast(event.model_dump(), subscription_id=scene_id)

    async def notify_artifact(self, scene_id: str, artifact_type: str, url: str,
                              preview_url: Optional[str] = None, metadata: Optional[Dict] = None):
        event = ArtifactEvent(
            type=f"artifact.{artifact_type}",
            artifact_url=url, artifact_type=artifact_type,
            preview_url=preview_url, metadata=metadata or {},
            scene_id=scene_id,
        )
        await self.broadcast(event.model_dump(), subscription_id=scene_id)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

    def get_session_count(self) -> int:
        return len(self.session_connections)


ws_manager = WebSocketManager()
