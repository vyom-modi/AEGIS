"""
Planner Agent.

Responsible for:
- Decomposing goals into structured execution plans
- Checking for pre-installed skill tools and including them in plans
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

{tools_context}

Output a JSON plan with the following structure:
{{
    "steps": [
        {{
            "name": "step name",
            "description": "what this step does",
            "agent": "which agent should handle this",
            "requires_tool": true
        }}
    ]
}}

Important rules:
- Be specific and actionable. Each step should be a concrete task.
- Set "requires_tool" to true for ANY step that involves code execution, computation, data processing, or testing.
- Steps that are purely planning, research, or documentation can set "requires_tool" to false.
- If available tools are listed above, design steps that can leverage them.
- Make at least 3-5 steps for typical goals.
Respond with ONLY the JSON, no other text."""


class PlannerAgent(BaseAgent):
    name = "planner"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate an execution plan for the goal."""
        goal = state.get("goal")
        if not goal:
            raise ValueError("goal is required in state")

        db = get_db()

        # Check for pre-installed skill tools
        tools_context = ""
        skill_id = goal.get("skill_id")

        if skill_id:
            # Goal was created from a skill — find installed tools
            tools = db.table("tools").select(
                "id, name, description, trust_score"
            ).eq("skill_id", skill_id).execute()

            if tools.data:
                tool_list = "\n".join(
                    f"- {t['name']}: {t['description']} (trust: {t['trust_score']})"
                    for t in tools.data
                )
                tools_context = (
                    f"Available pre-installed tools for this goal:\n{tool_list}\n"
                    "Design your plan steps to USE these tools where applicable. "
                    "Name the steps to match the tool names when possible."
                )
                # Store tool info in state for executor
                state["skill_tools"] = tools.data
        
        if not tools_context:
            # Also check for any generally available tools
            all_tools = db.table("tools").select(
                "id, name, description, trust_score"
            ).gte("trust_score", 0.6).limit(10).execute()

            if all_tools.data:
                tool_list = "\n".join(
                    f"- {t['name']}: {t['description']} (trust: {t['trust_score']})"
                    for t in all_tools.data
                )
                tools_context = (
                    f"Available tools in the system:\n{tool_list}\n"
                    "You may design steps that leverage these tools."
                )

        llm = get_llm()
        prompt = PLANNER_PROMPT.format(
            title=goal["title"],
            description=goal["description"],
            tools_context=tools_context,
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
            + (f" (skill-aware, {len(state.get('skill_tools', []))} tools available)"
               if state.get("skill_tools") else "")
        ]

        return state
