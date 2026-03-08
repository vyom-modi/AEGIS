"""
Monitor Agent.

Responsible for:
- Computing success rate, latency, cost
- Storing telemetry metrics in Supabase
- Triggering self-improvement if performance degrades
"""

from datetime import datetime, timezone
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class MonitorAgent(BaseAgent):
    name = "monitor"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Compute and store telemetry metrics."""
        db = get_db()
        results = state.get("execution_results", [])

        # Calculate metrics
        total_tasks = len(results)
        successful = sum(1 for r in results if r.get("status") == "completed")
        success_rate = successful / total_tasks if total_tasks > 0 else 0.0

        # Store metrics
        metrics = [
            {"metric_name": "success_rate", "value": success_rate},
            {"metric_name": "tasks_executed", "value": float(total_tasks)},
        ]

        for metric in metrics:
            db.table("metrics").insert(metric).execute()

        # TODO: Check for performance degradation and trigger self-improvement

        state["metrics"] = {
            "success_rate": success_rate,
            "tasks_executed": total_tasks,
        }
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Monitor] Success rate: {success_rate:.0%} ({successful}/{total_tasks})"
        ]

        return state
