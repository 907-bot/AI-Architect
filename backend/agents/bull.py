"""
Bull Agent - Pushes for creativity, grandeur, and immersive realism.
Increases scene detail and visual quality.
"""
from typing import Dict, Any
import json
import structlog
from backend.models.openrouter_client import OpenRouterClient

log = structlog.get_logger()

class BullAgent:
    def __init__(self, client: OpenRouterClient):
        self.client = client
        self.agent_name = "bull"
    
    async def process(self, scene_graph: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """Review the scene graph and suggest creative enhancements."""
        log.info("bull_evaluating", scene_id=scene_graph.get("scene_id"))
        
        system_prompt = """You are the Bull Agent in an architectural AI system.
        Your goal is to MAXIMIZE creativity, immersion, realism, and aesthetic quality.
        You should suggest enhancements to materials, lighting, layout flow, and decorative elements.
        
        Review the provided scene graph JSON and the original intent. 
        Return a JSON object containing proposed enhancements:
        {
            "enhancements": [
                {"type": "material_upgrade", "target": "floor", "suggestion": "marble_white", "reasoning": "..."},
                {"type": "add_light", "target": "living_room", "suggestion": "add ambient spot light", "reasoning": "..."}
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
            log.error("bull_agent_error", error=str(e))
            return {"enhancements": [], "approved": True}

async def create_bull_agent(client: OpenRouterClient) -> BullAgent:
    return BullAgent(client)
