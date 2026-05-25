"""
Orchestrator Agent - Master coordinator of the multi-agent system.
Routes tasks to specialized agents and manages the overall workflow.
CRITICAL: Every LLM call MUST return ONLY valid SceneGraph JSON — no markdown, no prose.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import structlog
import asyncio
from backend.models.openrouter import OpenRouterClient
from backend.models.scene_graph import (
    SceneGraph, SceneValidator, ArchitecturalStyle
)
from backend.database.models import Scene, AgentExecution

log = structlog.get_logger()

MAX_RETRIES = 3

# The strict system prompt that enforces SceneGraph JSON-only output.
SCENE_GRAPH_PROMPT_TEMPLATE = """You are an architectural scene generator. Your output is fed DIRECTLY into a 3D rendering engine.

CRITICAL RULES:
1. Return ONLY valid JSON matching the schema below.
2. NO explanation. NO markdown. NO prose. NO code fences. NO commentary.
3. The JSON MUST be parseable by Python's json.loads() on the first attempt.
4. Every room MUST have walls, doors, and windows arrays (can be empty).
5. Use meters for all dimensions.
6. Generate at least 1 room. Generate at least 1 material referenced by rooms.

SCENE GRAPH SCHEMA (you MUST follow this exactly):
{{
  "style": "modern" | "contemporary" | "traditional" | "minimalist" | "indian_contemporary" | "japanese_minimal" | "scandinavian" | "modern_luxury" | "brutalist" | "cyberpunk",
  "rooms": [
    {{
      "id": "unique_string_id",
      "room_type": "bedroom" | "kitchen" | "bathroom" | "living_room" | "dining_room" | "hallway" | "garage" | "laundry" | "office" | "storage" | "staircase",
      "name": "Human readable name",
      "floor_number": 0,
      "position": {{"x": 0.0, "y": 0.0, "z": 0.0}},
      "width": 5.0,
      "depth": 5.0,
      "height": 3.0,
      "material_id": "material_id_reference",
      "walls": [
        {{
          "id": "wall_id",
          "room_id": "room_id",
          "start_point": {{"x": -2.5, "y": 0, "z": -2.5}},
          "end_point": {{"x": 2.5, "y": 0, "z": -2.5}},
          "height": 3.0,
          "thickness": 0.2,
          "material_id": "material_id",
          "doors": [],
          "windows": []
        }}
      ],
      "doors": [],
      "windows": [],
      "furniture": [],
      "lights": []
    }}
  ],
  "stairs": [],
  "materials": [
    {{
      "id": "material_id",
      "name": "Material Name",
      "material_type": "wood" | "concrete" | "glass" | "fabric" | "metal" | "plastic" | "tile" | "carpet" | "paint",
      "color_rgb": "#CCCCCC",
      "roughness": 0.5,
      "metallic": 0.0
    }}
  ],
  "lights": [],
  "navigation": {{
    "navigation_meshes": [],
    "walkthrough_points": [],
    "drone_path_nodes": []
  }}
}}

Now, given the user request, return ONLY the JSON object. No other text."""


class OrchestratorAgent:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client
        self.agent_name = "orchestrator"
        self.agent_role = "primary"

    async def process_prompt(
        self,
        user_prompt: str,
        scene_id: str,
        user_id: str,
        db=None
    ) -> Dict[str, Any]:
        execution_id = None
        start_time = datetime.utcnow()

        try:
            log.info("orchestrator_start", scene_id=scene_id, user_id=user_id, prompt=user_prompt[:100])

            intent = await self._extract_intent(user_prompt)
            log.info("intent_extracted", scene_id=scene_id, intent=intent)

            plan = await self._create_plan(intent, user_prompt)
            log.info("plan_created", scene_id=scene_id, agents=plan.get("agents", []))

            scene_graph = await self._generate_scene_graph_strict(plan, user_prompt, scene_id)

            is_valid, errors = SceneValidator.validate_scene_graph(scene_graph)
            if not is_valid:
                log.warning("scene_validation_failed", scene_id=scene_id, errors=errors)
                return {
                    "status": "warning",
                    "scene_graph": scene_graph,
                    "validation_errors": errors,
                    "agent_plan": plan
                }

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
            log.info("orchestrator_success", scene_id=scene_id, execution_time_ms=execution_time)

            return {
                "status": "success",
                "scene_graph": scene_graph,
                "agent_plan": plan,
                "execution_time_ms": execution_time,
                "validation_errors": []
            }

        except Exception as e:
            log.error("orchestrator_error", scene_id=scene_id, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "scene_graph": None,
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            }

    async def _extract_intent(self, prompt: str) -> Dict[str, Any]:
        system_prompt = """You are an architectural AI that extracts design intent.

Return ONLY valid JSON with these fields:
- "style": string (one of: modern, traditional, minimalist, contemporary, indian_contemporary)
- "rooms": { "bedrooms": int, "bathrooms": int, "other": int }
- "features": list of strings
- "constraints": list of strings
- "budget": "low" | "medium" | "high"
- "summary": one-sentence summary

NO markdown. NO prose. JSON only."""

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

        if not response or not isinstance(response, str):
            log.error("intent_extraction_empty_response", metadata=metadata)
            raise RuntimeError("Empty response from LLM during intent extraction")

        for attempt in range(MAX_RETRIES):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                if attempt < MAX_RETRIES - 1:
                    log.warning("intent_extraction_retry", attempt=attempt + 1)
                    response, metadata = await self.client.call(
                        messages=messages, agent_type="orchestrator",
                        agent_id=f"orchestrator_retry_{attempt}",
                        max_tokens=1500, temperature=0.3
                    )
                else:
                    log.warning("intent_extraction_json_failed",
                                response=response[:200], metadata=metadata)
                    return {
                        "style": "modern",
                        "rooms": {"bedrooms": 3, "bathrooms": 2, "other": 1},
                        "features": [], "constraints": [],
                        "budget": "medium", "summary": prompt[:100],
                        "_warning": "intent_extraction_json_failed"
                    }
        return {
            "style": "modern",
            "rooms": {"bedrooms": 3, "bathrooms": 2, "other": 1},
            "features": [], "constraints": [],
            "budget": "medium", "summary": prompt[:100],
            "_warning": "intent_extraction_exhausted"
        }

    async def _create_plan(self, intent: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        system_prompt = """Return ONLY valid JSON for the agent execution plan:
{
  "agents": [
    {"name": "planner", "priority": 1, "input": {...}},
    {"name": "layout", "priority": 2, "input": {...}},
    {"name": "geometry", "priority": 3, "input": {...}},
    {"name": "asset", "priority": 4, "input": {...}},
    {"name": "visualization", "priority": 5, "input": {...}}
  ],
  "parallelizable_groups": [["asset", "visualization"]]
}
JSON only. NO markdown."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Intent: {json.dumps(intent)}\nOriginal prompt: {prompt}"}
        ]

        response, _ = await self.client.call(
            messages=messages, agent_type="orchestrator",
            max_tokens=1500, temperature=0.2
        )

        if not response:
            log.error("plan_creation_empty_response")
            raise RuntimeError("Empty response during plan creation")

        for attempt in range(MAX_RETRIES):
            try:
                plan = json.loads(response)
                return plan
            except json.JSONDecodeError:
                if attempt < MAX_RETRIES - 1:
                    log.warning("plan_creation_retry", attempt=attempt + 1)
                    response, _ = await self.client.call(
                        messages=messages, agent_type="orchestrator",
                        max_tokens=1500, temperature=0.2
                    )
                else:
                    log.warning("plan_creation_json_failed", response=response[:200])
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

    async def _generate_scene_graph_strict(
        self,
        plan: Dict[str, Any],
        user_prompt: str,
        scene_id: str
    ) -> SceneGraph:
        """
        Generate scene graph via LLM with strict schema enforcement + retry.
        NEVER lets invalid JSON reach the rest of the system.
        """
        schema_str = SceneGraph.schema_json_str()

        system_prompt = SCENE_GRAPH_PROMPT_TEMPLATE

        # Include intent from plan
        intent_summary = plan.get("agents", [{}])[0].get("input", {}) if plan.get("agents") else {}

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User request: {user_prompt}\n\nStyle: {intent_summary.get('style', 'modern')}\nRooms: {intent_summary.get('rooms', {})}\nFeatures: {intent_summary.get('features', [])}\n\nGenerate the scene graph JSON matching the schema exactly."}
        ]

        response, metadata = await self.client.call(
            messages=messages, agent_type="orchestrator",
            agent_id=f"scene_gen_{scene_id}",
            max_tokens=4000, temperature=0.4
        )

        if not response:
            log.error("scene_generation_empty_response")
            # Return a minimal valid scene graph as emergency fallback
            return self._emergency_scene_graph(user_prompt)

        for attempt in range(MAX_RETRIES):
            # Try to parse and validate
            success, scene, error_msg = SceneValidator.validate_llm_output(response)
            if success:
                scene.compute_properties()
                log.info("scene_generation_success", scene_id=scene_id, attempt=attempt + 1)
                return scene

            log.warning("scene_generation_retry", attempt=attempt + 1, error=error_msg,
                        response_preview=str(response)[:200])

            if attempt < MAX_RETRIES - 1:
                # Retry with explicit error feedback
                retry_prompt = (
                    f"Your previous output failed validation: {error_msg}\n\n"
                    f"Original request: {user_prompt}\n\n"
                    f"Return ONLY valid JSON matching the scene graph schema. "
                    f"Ensure it is parseable by json.loads(). No markdown. No prose."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": retry_prompt}
                ]
                response, metadata = await self.client.call(
                    messages=messages, agent_type="orchestrator",
                    agent_id=f"scene_gen_{scene_id}_retry_{attempt}",
                    max_tokens=4000, temperature=0.4
                )
            else:
                log.error("scene_generation_all_retries_failed", scene_id=scene_id)
                return self._emergency_scene_graph(user_prompt)

        return self._emergency_scene_graph(user_prompt)

    def _emergency_scene_graph(self, prompt: str) -> SceneGraph:
        """Return a minimal valid scene so the system never crashes with None."""
        log.warning("emergency_scene_graph_fallback", prompt=prompt[:80])
        sg = SceneGraph(
            style=ArchitecturalStyle.MODERN,
            rooms=[],
            stairs=[],
            materials=[],
            lights=[],
            navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []}
        )
        sg.compute_properties()
        return sg


async def create_orchestrator_agent(openrouter_client: OpenRouterClient) -> OrchestratorAgent:
    return OrchestratorAgent(openrouter_client)
