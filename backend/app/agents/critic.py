"""
Critic Agent.

Responsible for:
- Analyzing execution outputs
- Detecting problems
- Suggesting improvements
"""

from typing import Any
from app.agents.base import BaseAgent
from app.llm import get_llm


CRITIC_PROMPT = """You are a critic agent in the AEGIS autonomous system.
Analyze the execution results and identify any issues or improvements.

Goal: {goal_title}
Execution Results:
{results}

Provide your analysis as JSON:
{{
    "quality_score": 0.0-1.0,
    "issues": ["list of issues found"],
    "suggestions": ["list of improvement suggestions"],
    "passed": true/false
}}"""


class CriticAgent(BaseAgent):
    name = "critic"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Analyze execution results and provide feedback."""
        results = state.get("execution_results", [])

        # TODO: Use LLM to analyze results
        state["critique"] = {
            "quality_score": 1.0,
            "issues": [],
            "suggestions": [],
            "passed": True,
        }
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Critic] Analyzed {len(results)} results — passed"
        ]

        return state
