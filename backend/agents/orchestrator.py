"""
Orchestrator Agent - Master coordinator of the multi-agent system
Routes tasks to specialized agents and manages the overall workflow
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import structlog
from backend.models.openrouter import OpenRouterClient
from backend.models.scene_graph import SceneGraph, GenerationParameters, SceneValidator
from backend.database.models import Scene, AgentExecution

log = structlog.get_logger()


class OrchestratorAgent:
    """
    Master orchestrator that:
    1. Parses user prompts
    2. Extracts architectural intent
    3. Dispatches to specialized agents
    4. Manages multi-agent conversation
    5. Handles error recovery
    """
    
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client
        self.agent_name = "orchestrator"
        self.agent_role = "primary"
    
    async def process_prompt(
        self,
        user_prompt: str,
        scene_id: str,
        user_id: str,
        db = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Process user prompt and orchestrate agents
        
        Returns:
            {
                "status": "success" | "error",
                "scene_graph": SceneGraph | None,
                "agent_plan": List of agents to invoke,
                "metadata": execution metadata
            }
        """
        
        execution_id = None
        start_time = datetime.utcnow()
        
        try:
            # Log execution start
            log.info(
                "orchestrator_start",
                scene_id=scene_id,
                user_id=user_id,
                prompt=user_prompt[:100]
            )
            
            # Step 1: Extract architectural intent
            intent = await self._extract_intent(user_prompt)
            log.info("intent_extracted", scene_id=scene_id, intent=intent)
            
            # Step 2: Plan agent sequence
            plan = await self._create_plan(intent, user_prompt)
            log.info("plan_created", scene_id=scene_id, agents=plan["agents"])
            
            # Step 3: Dispatch to specialized agents (stubbed for now)
            # In production, these would be actual agent implementations
            scene_graph = await self._dispatch_agents(plan, user_prompt, scene_id)
            
            # Step 4: Validate scene
            is_valid, errors = SceneValidator.validate_scene_graph(scene_graph)
            if not is_valid:
                log.warning("scene_validation_failed", scene_id=scene_id, errors=errors)
                return {
                    "status": "warning",
                    "scene_graph": scene_graph,
                    "validation_errors": errors,
                    "agent_plan": plan
                }
            
            # Update scene in database if db provided
            if db:
                scene = db.query(Scene).filter(Scene.id == scene_id).first()
                if scene:
                    scene.scene_graph = scene_graph.to_dict()
                    scene.version += 1
                    scene.status = "completed"
                    scene.completed_at = datetime.utcnow()
                    db.commit()
                    log.info("scene_updated", scene_id=scene_id, version=scene.version)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log.info(
                "orchestrator_success",
                scene_id=scene_id,
                execution_time_ms=execution_time
            )
            
            return {
                "status": "success",
                "scene_graph": scene_graph,
                "agent_plan": plan,
                "execution_time_ms": execution_time,
                "validation_errors": []
            }
            
        except Exception as e:
            log.error(
                "orchestrator_error",
                scene_id=scene_id,
                error=str(e),
                traceback=True
            )
            return {
                "status": "error",
                "error": str(e),
                "scene_graph": None,
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            }
    
    async def _extract_intent(self, prompt: str) -> Dict[str, Any]:
        """
        Extract architectural intent from user prompt
        
        Returns:
            {
                "style": str,
                "rooms": Dict,
                "features": List,
                "constraints": List,
                "budget": str
            }
        """
        
        system_prompt = """You are an architectural AI that extracts design intent from natural language.
        
        Analyze the user prompt and extract:
        1. Architectural style (modern, traditional, minimalist, etc.)
        2. Room requirements (bedrooms, bathrooms, kitchens, etc.)
        3. Key features (garage, patio, open plan, etc.)
        4. Constraints (budget, lot size, accessibility, etc.)
        5. Budget level (low, medium, high)

        Return a JSON object with these fields."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response, metadata = await self.client.call(
            messages=messages,
            agent_type="orchestrator",
            agent_id=f"orchestrator_{datetime.utcnow().timestamp()}",
            max_tokens=1500,
            temperature=0.3
        )
        
        try:
            # Parse JSON response
            intent = json.loads(response)
            return intent
        except json.JSONDecodeError:
            log.warning("intent_extraction_json_failed", response=response[:200])
            return {
                "style": "modern",
                "rooms": {"bedrooms": 3, "bathrooms": 2},
                "features": [],
                "constraints": [],
                "budget": "medium"
            }
    
    async def _create_plan(self, intent: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Create agent execution plan based on intent
        
        Returns:
            {
                "agents": [
                    {"name": "planner", "priority": 1},
                    {"name": "geometry", "priority": 2},
                    ...
                ],
                "parallelizable": List of agents that can run in parallel
            }
        """
        
        system_prompt = """You are a workflow planner for architectural AI.

        Given the architectural intent, create an execution plan:
        1. Planner Agent - Interprets requirements
        2. Layout Agent - Generates floorplan
        3. Geometry Agent - Creates 3D geometry
        4. Asset Agent - Assigns furniture/materials
        5. Visualization Agent - Prepares for rendering

        Return JSON: {
            "agents": [
                {"name": "planner", "priority": 1, "input": {...}},
                {"name": "layout", "priority": 2, "input": {...}},
                ...
            ],
            "parallelizable_groups": [
                ["asset", "visualization"]
            ]
        }"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Intent: {json.dumps(intent)}\nOriginal prompt: {prompt}"}
        ]
        
        response, _ = await self.client.call(
            messages=messages,
            agent_type="orchestrator",
            max_tokens=1500,
            temperature=0.2
        )
        
        try:
            plan = json.loads(response)
            return plan
        except json.JSONDecodeError:
            log.warning("plan_creation_json_failed", response=response[:200])
            # Default plan
            return {
                "agents": [
                    {"name": "planner", "priority": 1},
                    {"name": "layout", "priority": 2},
                    {"name": "geometry", "priority": 3},
                    {"name": "asset", "priority": 4},
                    {"name": "visualization", "priority": 5}
                ],
                "parallelizable_groups": []
            }
    
    async def _dispatch_agents(
        self,
        plan: Dict[str, Any],
        user_prompt: str,
        scene_id: str
    ) -> SceneGraph:
        """
        Dispatch to specialized agents and aggregate results
        
        STUBBED: In production, would call actual agent implementations
        """
        
        # For MVP, create a basic scene graph from the prompt
        log.info("agents_dispatch_stubbed", agents=[a["name"] for a in plan["agents"]])
        
        # Create minimal valid scene graph
        scene_graph = SceneGraph(
            rooms=[],
            stairs=[],
            materials=[],
            lights=[],
            navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []}
        )
        
        scene_graph.compute_properties()
        return scene_graph


# ====================================================
# Agent Factory
# ====================================================

async def create_orchestrator_agent(openrouter_client: OpenRouterClient) -> OrchestratorAgent:
    """Factory to create orchestrator agent"""
    return OrchestratorAgent(openrouter_client)
