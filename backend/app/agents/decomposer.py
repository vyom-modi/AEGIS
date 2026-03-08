"""
Decomposer Agent.

Responsible for:
- Refining unclear or complex tasks
- Breaking tasks into sub-tasks if needed
- Uses LLM to evaluate task clarity
"""

import json
from typing import Any
from app.agents.base import BaseAgent
from app.llm import get_llm


DECOMPOSER_PROMPT = """You are a task decomposer in the AEGIS autonomous system.
Given a list of plan steps, evaluate each one and refine if needed.

Goal: {goal_title}

Steps to evaluate:
{steps_json}

For each step:
1. If the step is already clear and actionable, keep it as-is
2. If a step is vague, rewrite it to be specific and actionable
3. If a step is too complex, break it into 2-3 sub-steps

Return a JSON array of refined steps. Each step must have:
- "name": concise step title
- "description": what to do, specifically
- "agent": which agent type should handle it
- "requires_tool": true if this step needs generated Python code

Return ONLY valid JSON, no markdown formatting."""


class DecomposerAgent(BaseAgent):
    name = "decomposer"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Refine and decompose tasks using LLM analysis."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])

        if not steps:
            state["logs"] = state.get("logs", []) + [
                "[Decomposer] No steps to decompose"
            ]
            return state

        goal = state.get("goal", {})
        goal_title = goal.get("title", "Unknown goal")

        try:
            llm = get_llm()
            prompt = DECOMPOSER_PROMPT.format(
                goal_title=goal_title,
                steps_json=json.dumps(steps, indent=2),
            )

            response = await llm.ainvoke(prompt)
            content = response.content.strip()

            # Parse JSON from response (handle markdown code blocks)
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            refined_steps = json.loads(content)

            # Update plan with refined steps
            state["plan"]["steps"] = refined_steps

            state["logs"] = state.get("logs", []) + [
                f"[Decomposer] Refined {len(steps)} steps → {len(refined_steps)} steps"
            ]

        except Exception as e:
            # On failure, keep original steps
            state["logs"] = state.get("logs", []) + [
                f"[Decomposer] LLM refinement failed, keeping original steps: {e}"
            ]

        state["current_agent"] = self.name
        return state
