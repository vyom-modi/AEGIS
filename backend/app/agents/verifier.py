"""
Verifier Agent.

Responsible for:
- Verifying correctness of execution results
- Cross-referencing critique analysis
- Updating plan scores in Supabase
- Final pass/fail determination
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class VerifierAgent(BaseAgent):
    name = "verifier"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Verify execution results and update plan score.

        Uses the Critic's analysis to make a final determination
        and persists the quality score to the plan record.
        """
        critique = state.get("critique", {})
        quality_score = critique.get("quality_score", 0.0)
        passed = critique.get("passed", False)

        # Verify based on multiple signals
        execution_results = state.get("execution_results", [])
        total_tasks = len(execution_results)
        completed_tasks = sum(
            1 for r in execution_results if r.get("status") == "completed"
        )

        # Calculate composite verification
        completion_rate = completed_tasks / max(total_tasks, 1)
        composite_score = (quality_score * 0.6) + (completion_rate * 0.4)
        verified = passed and completion_rate > 0.5

        # Update the plan score in Supabase
        plan_id = state.get("plan_id")
        if plan_id:
            try:
                db = get_db()
                db.table("plans").update({
                    "score": composite_score,
                }).eq("id", plan_id).execute()
            except Exception as e:
                state["logs"] = state.get("logs", []) + [
                    f"[Verifier] Failed to update plan score: {e}"
                ]

        state["verified"] = verified
        state["verification_score"] = composite_score
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Verifier] Composite score: {composite_score:.0%} "
            f"(quality: {quality_score:.0%}, completion: {completion_rate:.0%}) — "
            f"{'VERIFIED ✓' if verified else 'REJECTED ✗'}"
        ]

        return state
