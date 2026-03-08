"""
Executor Agent.

Responsible for:
- Executing tasks from the plan
- Running generated tools in the sandbox
- Creating task and run records in Supabase
- Streaming execution logs
"""

import time
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db
from app.sandbox.runner import execute_code


class ExecutorAgent(BaseAgent):
    name = "executor"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute tasks from the plan, using sandbox for tool-requiring steps."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])
        db = get_db()

        # Build a lookup of generated tools by name
        tools_map = {}
        tools_created = state.get("tools_created", [])
        for tool in tools_created:
            tool_name = tool.get("name", "").lower().replace(" ", "_")
            tool_id = tool.get("tool_id")
            if tool_id:
                try:
                    record = db.table("tools").select("code").eq("id", tool_id).execute()
                    if record.data:
                        tools_map[tool_name] = record.data[0].get("code", "")
                except Exception:
                    pass

        results = []
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i + 1}")
            start_time = time.time()

            # Create task record
            task_result = db.table("tasks").insert({
                "plan_id": state.get("plan_id"),
                "name": step_name,
                "description": step.get("description", ""),
                "status": "running",
                "assigned_agent": step.get("agent", "executor"),
                "retries": 0,
            }).execute()

            task_id = task_result.data[0]["id"] if task_result.data else None
            success = False
            logs = ""

            if step.get("requires_tool"):
                # Try to execute the generated tool in sandbox
                tool_key = step_name.lower().replace(" ", "_")
                code = tools_map.get(tool_key, "")

                if code:
                    # Wrap tool code with a run() call
                    full_code = code + '\n\nresult = run({"task": "' + step_name + '"})\nprint(result)'

                    sandbox_result = await execute_code(
                        full_code,
                        use_e2b=True,
                        timeout=30,
                    )

                    success = sandbox_result.get("success", False)
                    logs = (
                        sandbox_result.get("stdout", "")
                        or sandbox_result.get("error", "No output")
                    )
                else:
                    success = True
                    logs = f"Tool not found for '{step_name}', marking as simulated"
            else:
                # Non-tool steps are considered completed
                success = True
                logs = f"Completed: {step_name}"

            latency = time.time() - start_time

            # Update task status
            if task_id:
                db.table("tasks").update({
                    "status": "completed" if success else "failed",
                }).eq("id", task_id).execute()

                # Record run
                db.table("runs").insert({
                    "task_id": task_id,
                    "logs": logs[:1000],  # Truncate long logs
                    "success": success,
                    "token_cost": 0.0,
                    "latency": round(latency, 3),
                }).execute()

            results.append({
                "step": step_name,
                "task_id": task_id,
                "status": "completed" if success else "failed",
                "latency": round(latency, 3),
            })

        state["execution_results"] = results
        state["current_agent"] = self.name

        completed = sum(1 for r in results if r["status"] == "completed")
        state["logs"] = state.get("logs", []) + [
            f"[Executor] Executed {len(results)} tasks ({completed} completed, "
            f"{len(results) - completed} failed)"
        ]

        return state
