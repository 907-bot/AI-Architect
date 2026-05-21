"""
Multi-Agent Orchestration Graph (LangGraph)
Coordinates Bull, Bear, and Skeptic adversarial debate.
"""
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
import structlog

from backend.agents.bull import BullAgent
from backend.agents.bear import BearAgent
from backend.agents.skeptic import SkepticAgent
from backend.models.openrouter_client import openrouter

log = structlog.get_logger()

class AgentState(TypedDict):
    scene_id: str
    intent: Dict[str, Any]
    scene_graph: Dict[str, Any]
    bull_enhancements: List[Dict[str, Any]]
    bear_reductions: List[Dict[str, Any]]
    skeptic_issues: List[Dict[str, Any]]
    iteration: int
    is_valid: bool

class ArchitectureGraph:
    def __init__(self):
        self.bull = BullAgent(openrouter)
        self.bear = BearAgent(openrouter)
        self.skeptic = SkepticAgent(openrouter)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Define Nodes
        workflow.add_node("bull_evaluate", self._node_bull)
        workflow.add_node("bear_evaluate", self._node_bear)
        workflow.add_node("skeptic_evaluate", self._node_skeptic)
        workflow.add_node("resolve_conflicts", self._node_resolve)

        # Define Edges
        workflow.set_entry_point("bull_evaluate")
        workflow.add_edge("bull_evaluate", "bear_evaluate")
        workflow.add_edge("bear_evaluate", "skeptic_evaluate")
        workflow.add_edge("skeptic_evaluate", "resolve_conflicts")
        
        # Conditional Edges for looping
        workflow.add_conditional_edges(
            "resolve_conflicts",
            self._should_continue,
            {
                "continue": "bull_evaluate",
                "end": END
            }
        )
        return workflow.compile()

    async def _node_bull(self, state: AgentState) -> AgentState:
        result = await self.bull.process(state["scene_graph"], state["intent"])
        return {"bull_enhancements": result.get("enhancements", [])}

    async def _node_bear(self, state: AgentState) -> AgentState:
        result = await self.bear.process(state["scene_graph"], state["intent"])
        return {"bear_reductions": result.get("reductions", [])}

    async def _node_skeptic(self, state: AgentState) -> AgentState:
        result = await self.skeptic.process(state["scene_graph"], state["intent"])
        return {
            "skeptic_issues": result.get("issues", []),
            "is_valid": result.get("is_valid", True)
        }

    async def _node_resolve(self, state: AgentState) -> AgentState:
        log.info("resolving_adversarial_conflict", iteration=state["iteration"])
        # Here we would merge enhancements/reductions and fix issues.
        # For now, increment iteration.
        return {"iteration": state["iteration"] + 1}

    def _should_continue(self, state: AgentState) -> str:
        # Stop if valid or max iterations reached
        if state["is_valid"] or state["iteration"] >= 3:
            return "end"
        return "continue"

    async def run(self, initial_state: AgentState) -> AgentState:
        return await self.graph.ainvoke(initial_state)

