"""
Executor Agent.

Responsible for:
- Executing tasks
- Running tools
- Running Python in sandbox
- Streaming logs
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class ExecutorAgent(BaseAgent):
    name = "executor"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute tasks from the plan."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])
        db = get_db()

        results = []
        for i, step in enumerate(steps):
            # Create a task record
            task_result = db.table("tasks").insert({
                "plan_id": state.get("plan_id"),
                "name": step.get("name", f"Step {i + 1}"),
                "description": step.get("description", ""),
                "status": "running",
                "assigned_agent": step.get("agent", "executor"),
                "retries": 0,
            }).execute()

            task_id = task_result.data[0]["id"] if task_result.data else None

            # TODO: Actually execute the step using sandbox
            # For now, mark as completed
            if task_id:
                db.table("tasks").update(
                    {"status": "completed"}
                ).eq("id", task_id).execute()

                # Record run
                db.table("runs").insert({
                    "task_id": task_id,
                    "logs": f"Executed: {step.get('name', 'unnamed')}",
                    "success": True,
                    "token_cost": 0.0,
                    "latency": 0.0,
                }).execute()

            results.append({
                "step": step.get("name"),
                "task_id": task_id,
                "status": "completed",
            })

        state["execution_results"] = results
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Executor] Executed {len(results)} tasks"
        ]

        return state
