"""
Memory Agent.

Responsible for:
- Storing execution summaries as strategies in Supabase
- Recording successful approaches for future recall
- Building institutional knowledge from past missions
"""

import json
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db
from app.llm import get_llm


MEMORY_PROMPT = """You are a memory agent in the AEGIS autonomous system.
Summarize this mission into a reusable strategy for future reference.

Goal: {goal_title}
Plan Steps: {steps_count}
Success Rate: {success_rate}
Critique: {critique_summary}

Create a brief strategy summary (2-3 sentences) describing:
1. What approach was taken
2. What worked or failed
3. Key lessons for similar goals

Respond with ONLY JSON:
{{
    "strategy_name": "short descriptive name",
    "description": "2-3 sentence strategy summary",
    "tags": ["tag1", "tag2"]
}}"""


class MemoryAgent(BaseAgent):
    name = "memory"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Store execution context as strategies for future recall."""
        db = get_db()
        goal = state.get("goal", {})
        results = state.get("execution_results", [])
        critique = state.get("critique", {})

        total = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        success_rate = completed / max(total, 1)

        try:
            llm = get_llm()
            prompt = MEMORY_PROMPT.format(
                goal_title=goal.get("title", "Unknown"),
                steps_count=total,
                success_rate=f"{success_rate:.0%}",
                critique_summary=critique.get("summary", "No critique available"),
            )

            response = await llm.ainvoke(prompt)
            content = response.content.strip()

            # Parse JSON
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            strategy_data = json.loads(content)

            # Store the strategy in Supabase
            strategy_json = {
                "goal_id": state.get("goal_id"),
                "approach": strategy_data.get("description", ""),
                "success_rate": success_rate,
                "tags": strategy_data.get("tags", []),
            }

            db.table("strategies").insert({
                "name": strategy_data.get("strategy_name", "Unknown strategy"),
                "strategy_json": strategy_json,
                "score": success_rate,
            }).execute()

            state["logs"] = state.get("logs", []) + [
                f"[Memory] Stored strategy: \"{strategy_data.get('strategy_name', 'unknown')}\""
            ]

        except Exception as e:
            state["logs"] = state.get("logs", []) + [
                f"[Memory] Failed to store strategy: {e}"
            ]

        state["current_agent"] = self.name
        return state
