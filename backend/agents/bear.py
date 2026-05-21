"""
Bear Agent - Optimizes for performance, cost, and efficiency.
Reduces polygon count, standardizes dimensions, controls complexity.
"""
from typing import Dict, Any
import json
import structlog
from backend.models.openrouter_client import OpenRouterClient

log = structlog.get_logger()

class BearAgent:
    def __init__(self, client: OpenRouterClient):
        self.client = client
        self.agent_name = "bear"
    
    async def process(self, scene_graph: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """Review the scene graph and suggest performance optimizations."""
        log.info("bear_evaluating", scene_id=scene_graph.get("scene_id"))
        
        system_prompt = """You are the Bear Agent in an architectural AI system.
        Your goal is to MINIMIZE cost, rendering overhead, polygon count, and structural complexity.
        You should suggest optimizations, material reductions, or layout simplifications to keep the project under budget and performant in 3D.
        
        Review the provided scene graph JSON and the original intent. 
        Return a JSON object containing proposed reductions:
        {
            "reductions": [
                {"type": "simplify_geometry", "target": "living_room_windows", "suggestion": "combine multiple windows into one large pane", "reasoning": "..."}
            ],
            "approved": true/false
        }"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Intent: {json.dumps(intent)}\nScene Graph: {json.dumps(scene_graph)}"}
        ]
        
        try:
            response = await self.client.chat(messages=messages, agent_id=self.agent_name, max_tokens=1000)
            return json.loads(response)
        except Exception as e:
            log.error("bear_agent_error", error=str(e))
            return {"reductions": [], "approved": True}

async def create_bear_agent(client: OpenRouterClient) -> BearAgent:
    return BearAgent(client)
