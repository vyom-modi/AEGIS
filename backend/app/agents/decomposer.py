"""
Decomposer Agent.

Responsible for:
- Refining unclear or complex tasks
- Breaking tasks into sub-tasks if needed
"""

from typing import Any
from app.agents.base import BaseAgent
from app.llm import get_llm


DECOMPOSER_PROMPT = """You are a task decomposer in the AEGIS autonomous system.
Given a task that may be vague or complex, break it down into clear, actionable sub-steps.

Task: {name}
Description: {description}

If the task is already clear and actionable, return it as-is.
If it needs decomposition, break it into 2-5 concrete sub-steps.

Respond in JSON:
{{
    "is_clear": true/false,
    "sub_steps": [
        {{"name": "step name", "description": "what to do"}}
    ]
}}"""


class DecomposerAgent(BaseAgent):
    name = "decomposer"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Refine and decompose tasks if needed."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])

        if not steps:
            state["logs"] = state.get("logs", []) + [
                "[Decomposer] No steps to decompose"
            ]
            return state

        # TODO: Iterate through steps and decompose complex ones
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Decomposer] Reviewed {len(steps)} steps"
        ]

        return state
