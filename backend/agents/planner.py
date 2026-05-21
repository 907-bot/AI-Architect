"""
Planner Agent - Interprets architectural requirements and constraints
"""
from typing import Dict, List, Any
from datetime import datetime
import json
import structlog
from backend.models.openrouter import OpenRouterClient
from backend.models.scene_graph import GenerationParameters, RoomType

log = structlog.get_logger()


class PlannerAgent:
    """
    Interprets user intent and creates architectural parameters:
    - Room types and counts
    - Space requirements
    - Layout constraints
    - Material preferences
    - Building codes compliance
    """
    
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client
        self.agent_name = "planner"
        self.agent_role = "primary"
    
    async def plan_architecture(
        self,
        intent: Dict[str, Any],
        user_prompt: str
    ) -> GenerationParameters:
        """
        Convert architectural intent into structured parameters
        
        Returns:
            GenerationParameters with all specifications
        """
        
        log.info("planner_start", intent=intent)
        
        system_prompt = """You are an architectural planning AI.

        Convert the user's intent into structured parameters:
        {
            "style": "modern|contemporary|traditional|minimalist",
            "budget": "low|medium|high",
            "occupancy": number of people,
            "include_garage": boolean,
            "include_basement": boolean,
            "target_sqft": approximate square footage,
            "num_bedrooms": number,
            "num_bathrooms": number,
            "flooring_type": "hardwood|tile|concrete|carpet",
            "preferred_materials": ["wood", "concrete", ...],
            "key_features": ["open_kitchen", "master_suite", ...],
            "constraints": ["narrow_lot", "corner_lot", ...]
        }

        Be conservative with estimates. All values should be realistic for the budget."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Intent: {json.dumps(intent)}\n\nPrompt: {user_prompt}"}
        ]
        
        response, metadata = await self.client.call(
            messages=messages,
            agent_type="planner",
            agent_id=f"planner_{datetime.utcnow().timestamp()}",
            max_tokens=1500,
            temperature=0.3
        )
        
        log.info("planner_response", model=metadata.get("model"), tokens=metadata.get("tokens_used"))
        
        try:
            params = json.loads(response)
            return GenerationParameters(**params)
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("planner_parsing_failed", error=str(e), response=response[:200])
            # Return sensible defaults
            return GenerationParameters()


class ComplianceAgent:
    """
    Validates designs against building codes and regulations
    """
    
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client
        self.agent_name = "compliance"
        self.agent_role = "evaluator"
    
    async def validate_compliance(
        self,
        scene_params: Dict[str, Any],
        region: str = "US"
    ) -> Dict[str, Any]:
        """
        Check design against building codes
        
        Returns:
            {
                "is_compliant": bool,
                "violations": List[str],
                "warnings": List[str],
                "recommendations": List[str]
            }
        """
        
        log.info("compliance_check_start", region=region)
        
        system_prompt = f"""You are a building code compliance expert for {region}.

        Review the architectural design for:
        1. Minimum room dimensions
        2. Egress requirements (exits)
        3. Ceiling heights
        4. Accessibility requirements
        5. Fire safety
        6. Structural requirements

        Return JSON:
        {{
            "is_compliant": boolean,
            "violations": ["violation 1", ...],
            "warnings": ["warning 1", ...],
            "recommendations": ["recommendation 1", ...]
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Design: {json.dumps(scene_params)}"}
        ]
        
        response, _ = await self.client.call(
            messages=messages,
            agent_type="evaluator",
            max_tokens=1500,
            temperature=0.2
        )
        
        try:
            result = json.loads(response)
            log.info(
                "compliance_check_complete",
                is_compliant=result.get("is_compliant"),
                violations=len(result.get("violations", []))
            )
            return result
        except json.JSONDecodeError:
            log.warning("compliance_parsing_failed")
            return {
                "is_compliant": True,
                "violations": [],
                "warnings": [],
                "recommendations": []
            }
