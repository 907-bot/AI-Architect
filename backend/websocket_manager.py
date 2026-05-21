"""
WebSocket Manager - Real-time communication for agents and scene updates
Handles client connections, message routing, and event broadcasting
"""
from fastapi import WebSocket
from typing import Dict, List, Set, Optional, Callable, Any
import json
import structlog
from datetime import datetime
from collections import defaultdict

log = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates
    """
    
    def __init__(self):
        # Active connections: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Client subscriptions: {client_id: {scene_id, agent_id, ...}}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Message handlers
        self.handlers: Dict[str, Callable] = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "ping": self._handle_ping,
            "get_status": self._handle_get_status
        }
    
    async def connect(self, client_id: str, websocket: WebSocket):
        """
        Accept new WebSocket connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        
        log.info(
            "websocket_connected",
            client_id=client_id,
            active_connections=len(self.active_connections)
        )
        
        # Send welcome message
        await self._send_message(
            websocket,
            {
                "type": "connection_established",
                "client_id": client_id,
                "message": "Connected to AI Architect"
            }
        )
    
    def disconnect(self, client_id: str):
        """
        Handle client disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        
        log.info(
            "websocket_disconnected",
            client_id=client_id,
            active_connections=len(self.active_connections)
        )
    
    async def handle_message(self, client_id: str, data: Dict[str, Any]):
        """
        Route incoming WebSocket message
        """
        try:
            message_type = data.get("type")
            
            log.info(
                "websocket_message",
                client_id=client_id,
                message_type=message_type
            )
            
            # Route to handler
            handler = self.handlers.get(message_type)
            if handler:
                await handler(client_id, data)
            else:
                log.warning("unknown_message_type", message_type=message_type)
                
        except Exception as e:
            log.error(
                "websocket_message_error",
                client_id=client_id,
                error=str(e)
            )
    
    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        """
        Subscribe to scene/agent updates
        """
        subscription_id = data.get("subscription_id")
        
        if subscription_id:
            self.subscriptions[client_id].add(subscription_id)
            
            log.info(
                "client_subscribed",
                client_id=client_id,
                subscription_id=subscription_id
            )
            
            await self._send_message(
                self.active_connections[client_id],
                {
                    "type": "subscribed",
                    "subscription_id": subscription_id
                }
            )
    
    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        """
        Unsubscribe from updates
        """
        subscription_id = data.get("subscription_id")
        
        if subscription_id and subscription_id in self.subscriptions[client_id]:
            self.subscriptions[client_id].discard(subscription_id)
            
            log.info(
                "client_unsubscribed",
                client_id=client_id,
                subscription_id=subscription_id
            )
    
    async def _handle_ping(self, client_id: str, data: Dict[str, Any]):
        """
        Handle ping keepalive
        """
        await self._send_message(
            self.active_connections[client_id],
            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
        )
    
    async def _handle_get_status(self, client_id: str, data: Dict[str, Any]):
        """
        Get connection status
        """
        await self._send_message(
            self.active_connections[client_id],
            {
                "type": "status",
                "client_id": client_id,
                "subscriptions": list(self.subscriptions.get(client_id, [])),
                "active_connections": len(self.active_connections)
            }
        )
    
    async def broadcast(self, message: Dict[str, Any], subscription_id: Optional[str] = None):
        """
        Broadcast message to all connected clients
        
        If subscription_id is provided, only send to clients subscribed to it
        """
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            # Check if client is subscribed (if filtering by subscription)
            if subscription_id and subscription_id not in self.subscriptions.get(client_id, set()):
                continue
            
            try:
                await self._send_message(websocket, message)
            except Exception as e:
                log.error(
                    "broadcast_error",
                    client_id=client_id,
                    error=str(e)
                )
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """
        Send message to specific client
        """
        if client_id not in self.active_connections:
            log.warning("client_not_connected", client_id=client_id)
            return
        
        try:
            await self._send_message(self.active_connections[client_id], message)
        except Exception as e:
            log.error(
                "send_to_client_error",
                client_id=client_id,
                error=str(e)
            )
            self.disconnect(client_id)
    
    async def notify_agent_update(
        self,
        scene_id: str,
        agent_name: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Notify all connected clients about agent execution
        """
        message = {
            "type": "agent_update",
            "scene_id": scene_id,
            "agent_name": agent_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if result:
            message["result"] = result
        
        if error:
            message["error"] = error
        
        await self.broadcast(message, subscription_id=scene_id)
        
        log.info(
            "agent_update_broadcast",
            scene_id=scene_id,
            agent_name=agent_name,
            status=status
        )
    
    async def notify_scene_update(
        self,
        scene_id: str,
        change_type: str,
        changes: Dict[str, Any]
    ):
        """
        Notify about scene changes
        """
        message = {
            "type": "scene_update",
            "scene_id": scene_id,
            "change_type": change_type,
            "changes": changes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message, subscription_id=scene_id)
        
        log.info(
            "scene_update_broadcast",
            scene_id=scene_id,
            change_type=change_type
        )
    
    async def notify_render_progress(
        self,
        scene_id: str,
        progress_percent: int,
        estimated_remaining_sec: Optional[int] = None
    ):
        """
        Notify about rendering progress
        """
        message = {
            "type": "render_progress",
            "scene_id": scene_id,
            "progress_percent": progress_percent,
            "estimated_remaining_sec": estimated_remaining_sec,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message, subscription_id=scene_id)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_subscription_count(self, subscription_id: str) -> int:
        """Get number of clients subscribed to a topic"""
        count = 0
        for subs in self.subscriptions.values():
            if subscription_id in subs:
                count += 1
        return count
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message via WebSocket with error handling
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            log.error("websocket_send_error", error=str(e))
            raise


# Global instance
ws_manager = WebSocketManager()
