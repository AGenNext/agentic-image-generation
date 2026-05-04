from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict

from agents.multi_agent import CriticAgent, GeneratorAgent, PlannerAgent
from tools.image_tools import improve_image


class AgentState(TypedDict, total=False):
    user_prompt: str
    refined_prompt: str
    image: str
    feedback: str
    score: float
    accept: bool
    iterations: int
    max_iterations: int
    history: List[Dict[str, Any]]
    backend: str
    meta: Dict[str, Any]


NodeName = Literal["planner", "generator", "critic", "improver", "end"]


class LangGraphAgent:
    """LangGraph-style DAG coordinator for planner/generator/critic/improver flow."""

    def __init__(self, max_iterations: int = 3):
        self.planner = PlannerAgent()
        self.generator = GeneratorAgent()
        self.critic = CriticAgent()
        self.default_max_iterations = max_iterations

        self._edges: Dict[NodeName, List[NodeName]] = {
            "planner": ["generator"],
            "generator": ["critic"],
            "critic": ["improver", "end"],
            "improver": ["generator"],
            "end": [],
        }

    def planner_node(self, state: AgentState) -> AgentState:
        result = self.planner.plan(prompt=state["user_prompt"], context={"history": state.get("history", [])})
        state["refined_prompt"] = result["refined_prompt"]
        state.setdefault("history", []).append({"node": "planner", "notes": result["plan_notes"]})
        return state

    def generator_node(self, state: AgentState) -> AgentState:
        result = self.generator.generate(prompt=state["refined_prompt"])
        state["image"] = result["image"]
        state["backend"] = result["backend"]
        state["meta"] = result["meta"]
        state.setdefault("history", []).append(
            {"node": "generator", "backend": result["backend"], "meta": result["meta"]}
        )
        return state

    def critic_node(self, state: AgentState) -> AgentState:
        iteration = state.get("iterations", 0)
        critique = self.critic.critique(
            prompt=state["refined_prompt"],
            image=state["image"],
            iteration=iteration,
        )
        state["feedback"] = critique["feedback"]
        state["score"] = critique["score"]
        state["accept"] = critique["accept"]
        state.setdefault("history", []).append({"node": "critic", **critique})
        return state

    def improver_node(self, state: AgentState) -> AgentState:
        improved = improve_image(prompt=state["refined_prompt"], feedback=state["feedback"])
        state["refined_prompt"] = improved["improved_prompt"]
        state["iterations"] = state.get("iterations", 0) + 1
        state.setdefault("history", []).append(
            {"node": "improver", "improved_prompt": state["refined_prompt"], "reason": state["feedback"]}
        )
        return state

    def _next_node(self, current: NodeName, state: AgentState) -> NodeName:
        if current == "critic":
            if state.get("accept", False):
                return "end"
            if state.get("iterations", 0) >= state.get("max_iterations", self.default_max_iterations):
                return "end"
            return "improver"

        next_nodes = self._edges[current]
        return next_nodes[0] if next_nodes else "end"

    def run(self, prompt: str, max_iterations: int | None = None) -> AgentState:
        state: AgentState = {
            "user_prompt": prompt,
            "iterations": 0,
            "max_iterations": max_iterations or self.default_max_iterations,
            "history": [],
        }

        node: NodeName = "planner"
        while node != "end":
            if node == "planner":
                state = self.planner_node(state)
            elif node == "generator":
                state = self.generator_node(state)
            elif node == "critic":
                state = self.critic_node(state)
            elif node == "improver":
                state = self.improver_node(state)
            node = self._next_node(node, state)

        return state
