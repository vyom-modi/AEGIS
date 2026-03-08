"""
GoalManager Agent.

Responsible for:
- Storing goals in Supabase
- Scheduling executions
- Maintaining goal lifecycle state
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class GoalManagerAgent(BaseAgent):
    name = "goal_manager"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process a goal: validate, persist, and prepare for planning.
        """
        db = get_db()
        goal_id = state.get("goal_id")

        if not goal_id:
            raise ValueError("goal_id is required in state")

        # Fetch goal from database
        result = db.table("goals").select("*").eq("id", goal_id).execute()
        if not result.data:
            raise ValueError(f"Goal {goal_id} not found")

        goal = result.data[0]

        # Update status to active
        db.table("goals").update({"status": "active"}).eq("id", goal_id).execute()

        state["goal"] = goal
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[GoalManager] Loaded goal: {goal['title']}"
        ]

        return state
