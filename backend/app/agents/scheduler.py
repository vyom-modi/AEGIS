"""
Scheduler Agent.

Responsible for:
- Detecting failed tasks for retry
- Updating task retry counts
- Checking if goals have recurrence schedules
- Queueing re-execution of scheduled goals
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


MAX_RETRIES = 3


class SchedulerAgent(BaseAgent):
    name = "scheduler"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Handle task retries and goal scheduling."""
        db = get_db()
        results = state.get("execution_results", [])

        # --- Retry Logic ---
        retried = 0
        for result in results:
            if result.get("status") == "failed":
                task_id = result.get("task_id")
                if not task_id:
                    continue

                try:
                    # Fetch current retry count
                    task = db.table("tasks").select("retries").eq("id", task_id).execute()
                    current_retries = task.data[0]["retries"] if task.data else 0

                    if current_retries < MAX_RETRIES:
                        db.table("tasks").update({
                            "retries": current_retries + 1,
                            "status": "pending",  # Reset to pending for retry
                        }).eq("id", task_id).execute()
                        retried += 1
                except Exception:
                    pass

        # --- Schedule Check ---
        goal = state.get("goal", {})
        schedule = goal.get("schedule")
        schedule_info = ""

        if schedule and schedule.lower() not in ("", "once", "none"):
            schedule_info = f" | Goal scheduled: {schedule}"
            # Update goal status back to pending for next scheduled run
            try:
                db.table("goals").update({
                    "status": "pending",
                }).eq("id", state.get("goal_id")).execute()
            except Exception:
                pass

        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Scheduler] {retried} tasks queued for retry (max {MAX_RETRIES})"
            + schedule_info
        ]

        return state
