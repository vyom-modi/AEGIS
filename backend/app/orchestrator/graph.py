"""
AEGIS Orchestrator — LangGraph Workflow Definition.

Defines the agent execution graph:
GoalManager → Planner → Decomposer → Toolsmith → Executor → Critic → Verifier → Memory → Monitor
"""

from typing import Any, TypedDict
from langgraph.graph import StateGraph, END

from app.agents.goal_manager import GoalManagerAgent
from app.agents.planner import PlannerAgent
from app.agents.decomposer import DecomposerAgent
from app.agents.toolsmith import ToolsmithAgent
from app.agents.executor import ExecutorAgent
from app.agents.critic import CriticAgent
from app.agents.verifier import VerifierAgent
from app.agents.memory import MemoryAgent
from app.agents.monitor import MonitorAgent


class AegisState(TypedDict, total=False):
    """State object passed through the agent graph."""
    goal_id: str
    goal: dict
    plan_id: str
    plan: dict
    execution_results: list
    critique: dict
    verified: bool
    tools_created: list
    metrics: dict
    current_agent: str
    logs: list[str]


# Instantiate agents
goal_manager = GoalManagerAgent()
planner = PlannerAgent()
decomposer = DecomposerAgent()
toolsmith = ToolsmithAgent()
executor = ExecutorAgent()
critic = CriticAgent()
verifier = VerifierAgent()
memory = MemoryAgent()
monitor = MonitorAgent()


def should_use_toolsmith(state: dict) -> str:
    """Decide whether to invoke the toolsmith based on plan steps."""
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    needs_tools = any(step.get("requires_tool") for step in steps)
    return "toolsmith" if needs_tools else "executor"


def build_graph() -> StateGraph:
    """Build and compile the AEGIS agent orchestration graph."""
    graph = StateGraph(AegisState)

    # Add nodes
    graph.add_node("goal_manager", goal_manager.execute)
    graph.add_node("planner", planner.execute)
    graph.add_node("decomposer", decomposer.execute)
    graph.add_node("toolsmith", toolsmith.execute)
    graph.add_node("executor", executor.execute)
    graph.add_node("critic", critic.execute)
    graph.add_node("verifier", verifier.execute)
    graph.add_node("memory", memory.execute)
    graph.add_node("monitor", monitor.execute)

    # Define edges
    graph.set_entry_point("goal_manager")
    graph.add_edge("goal_manager", "planner")
    graph.add_edge("planner", "decomposer")

    # Conditional: toolsmith if tools needed, else straight to executor
    graph.add_conditional_edges(
        "decomposer",
        should_use_toolsmith,
        {"toolsmith": "toolsmith", "executor": "executor"},
    )

    graph.add_edge("toolsmith", "executor")
    graph.add_edge("executor", "critic")
    graph.add_edge("critic", "verifier")
    graph.add_edge("verifier", "memory")
    graph.add_edge("memory", "monitor")
    graph.add_edge("monitor", END)

    return graph.compile()


# Pre-compiled graph instance
aegis_graph = build_graph()


async def run_mission(goal_id: str) -> dict[str, Any]:
    """
    Run the full AEGIS pipeline for a goal.

    Args:
        goal_id: UUID of the goal to process.

    Returns:
        Final state after all agents have executed.
    """
    initial_state: AegisState = {
        "goal_id": goal_id,
        "logs": [],
    }

    result = await aegis_graph.ainvoke(initial_state)
    return dict(result)
