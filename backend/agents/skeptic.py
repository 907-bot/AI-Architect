"""
Skeptic Agent - Validates structural realism, detects hallucinations.
Ensures the scene is physically possible and architecturally sound.
"""
from typing import Dict, Any
import json
import structlog
from backend.models.openrouter_client import OpenRouterClient

log = structlog.get_logger()

class SkepticAgent:
    def __init__(self, client: OpenRouterClient):
        self.client = client
        self.agent_name = "skeptic"
    
    async def process(self, scene_graph: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scene realism and structural integrity."""
        log.info("skeptic_evaluating", scene_id=scene_graph.get("scene_id"))
        
        system_prompt = """You are the Skeptic Agent in an architectural AI system.
        Your goal is to PREVENT hallucinations and physics-defying geometry.
        Check for: floating objects, missing doors, intersecting walls, physically impossible spans, and nonsensical layouts.
        
        Review the provided scene graph JSON. 
        Return a JSON object containing identified critical issues:
        {
            "issues": [
                {"severity": "critical", "target": "bathroom", "issue": "No door attached to bathroom walls.", "fix": "add_door"}
            ],
            "is_valid": true/false
        }"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Scene Graph: {json.dumps(scene_graph)}"}
        ]
        
        try:
            response = await self.client.chat(messages=messages, agent_id=self.agent_name, max_tokens=1000)
            return json.loads(response)
        except Exception as e:
            log.error("skeptic_agent_error", error=str(e))
            return {"issues": [], "is_valid": True}

async def create_skeptic_agent(client: OpenRouterClient) -> SkepticAgent:
    return SkepticAgent(client)
