"""
Monitor Agent.

Responsible for:
- Computing comprehensive telemetry metrics
- Storing metrics in Supabase
- Detecting performance degradation
- Triggering self-improvement strategies
"""

from datetime import datetime, timezone
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class MonitorAgent(BaseAgent):
    name = "monitor"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Compute and store comprehensive telemetry metrics."""
        db = get_db()
        results = state.get("execution_results", [])
        critique = state.get("critique", {})

        # Calculate metrics
        total_tasks = len(results)
        successful = sum(1 for r in results if r.get("status") == "completed")
        failed = total_tasks - successful
        success_rate = successful / total_tasks if total_tasks > 0 else 0.0
        quality_score = critique.get("quality_score", 0.0)

        # Calculate average latency
        latencies = [r.get("latency", 0.0) for r in results if r.get("latency")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Count tools created
        tools_count = len(state.get("tools_created", []))

        # Build metrics list
        metrics = [
            {"metric_name": "success_rate", "value": round(success_rate, 4)},
            {"metric_name": "tasks_executed", "value": float(total_tasks)},
            {"metric_name": "tasks_completed", "value": float(successful)},
            {"metric_name": "tasks_failed", "value": float(failed)},
            {"metric_name": "quality_score", "value": round(quality_score, 4)},
            {"metric_name": "avg_latency_s", "value": round(avg_latency, 4)},
            {"metric_name": "tools_generated", "value": float(tools_count)},
        ]

        # Always store verified status
        is_verified = 1.0 if state.get("verified", False) else 0.0
        metrics.append({"metric_name": "verified", "value": is_verified})

        # Store all metrics
        for metric in metrics:
            try:
                db.table("metrics").insert(metric).execute()
            except Exception:
                pass

        # Self-improvement check: compare with historical success rates
        improvement_triggered = False
        try:
            history = (
                db.table("metrics")
                .select("value")
                .eq("metric_name", "success_rate")
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )

            if len(history.data) >= 3:
                recent_rates = [h["value"] for h in history.data[:3]]
                avg_recent = sum(recent_rates) / len(recent_rates)

                if avg_recent < 0.5:
                    improvement_triggered = True
                    db.table("metrics").insert({
                        "metric_name": "self_improvement_triggered",
                        "value": 1.0,
                    }).execute()

        except Exception:
            pass

        state["metrics"] = {
            "success_rate": success_rate,
            "tasks_executed": total_tasks,
            "tasks_completed": successful,
            "quality_score": quality_score,
            "avg_latency": avg_latency,
            "tools_generated": tools_count,
            "improvement_triggered": improvement_triggered,
        }
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Monitor] Telemetry: {successful}/{total_tasks} tasks OK, "
            f"quality={quality_score:.0%}, latency={avg_latency:.2f}s"
            + (" — ⚠ self-improvement triggered" if improvement_triggered else "")
        ]

        return state
