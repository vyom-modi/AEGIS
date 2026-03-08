"""
Planner Agent.

Responsible for:
- Decomposing goals into structured execution plans
- Outputting JSON plan with steps
"""

import json
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db
from app.llm import get_llm


PLANNER_PROMPT = """You are a planning agent in the AEGIS autonomous system.
Given a goal, create a detailed execution plan.

Goal Title: {title}
Goal Description: {description}

Output a JSON plan with the following structure:
{{
    "steps": [
        {{
            "name": "step name",
            "description": "what this step does",
            "agent": "which agent should handle this",
            "requires_tool": false
        }}
    ]
}}

Be specific and actionable. Each step should be a concrete task.
Respond with ONLY the JSON, no other text."""


class PlannerAgent(BaseAgent):
    name = "planner"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate an execution plan for the goal."""
        goal = state.get("goal")
        if not goal:
            raise ValueError("goal is required in state")

        llm = get_llm()
        prompt = PLANNER_PROMPT.format(
            title=goal["title"],
            description=goal["description"],
        )

        response = await llm.ainvoke(prompt)
        plan_text = response.content.strip()

        # Try to parse the JSON from the response
        try:
            # Handle markdown code blocks
            if "```" in plan_text:
                plan_text = plan_text.split("```")[1]
                if plan_text.startswith("json"):
                    plan_text = plan_text[4:]
                plan_text = plan_text.strip()
            plan_json = json.loads(plan_text)
        except json.JSONDecodeError:
            plan_json = {"steps": [], "raw_response": plan_text}

        # Store plan in database
        db = get_db()
        result = db.table("plans").insert({
            "goal_id": state["goal_id"],
            "plan_json": plan_json,
            "score": 0.0,
        }).execute()

        plan_id = result.data[0]["id"] if result.data else None

        state["plan"] = plan_json
        state["plan_id"] = plan_id
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Planner] Generated plan with {len(plan_json.get('steps', []))} steps"
        ]

        return state
