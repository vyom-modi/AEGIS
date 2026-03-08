"""
Executor Agent.

Responsible for:
- Executing tasks from the plan
- Looking up pre-installed skill tools from Supabase
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

        # Build tool lookup from multiple sources:
        # 1. Tools created by Toolsmith during this mission
        # 2. Pre-installed skill tools (from planner)
        # 3. Fuzzy-match from the tools table by step name
        tools_map = {}   # name -> code
        tools_ids = {}   # name -> id

        # Source 1: Tools created by Toolsmith in this run
        tools_created = state.get("tools_created", [])
        for tool in tools_created:
            tool_name = tool.get("name", "").lower().replace(" ", "_")
            tool_id = tool.get("tool_id")
            if tool_id:
                tools_ids[tool_name] = tool_id
                try:
                    record = db.table("tools").select("code").eq("id", tool_id).execute()
                    if record.data:
                        tools_map[tool_name] = record.data[0].get("code", "")
                except Exception:
                    pass

        # Source 2: Pre-installed skill tools (set by planner)
        skill_tools = state.get("skill_tools", [])
        for tool in skill_tools:
            tool_name = tool.get("name", "").lower().replace(" ", "_")
            tool_id = tool.get("id")
            if tool_id and tool_name not in tools_map:
                tools_ids[tool_name] = tool_id
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
                # Find matching tool code
                code, tool_id = self._find_tool(
                    step_name, tools_map, tools_ids, db
                )

                if code:
                    # Wrap tool code with a run() call
                    full_code = (
                        code
                        + '\n\nresult = run({"task": "'
                        + step_name.replace('"', '\\"')
                        + '"})\nprint(result)'
                    )

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

                    # Update tool trust score based on execution result
                    if tool_id:
                        self._update_trust(db, tool_id, success)
                else:
                    success = True
                    logs = f"Tool not found for '{step_name}', marking as simulated"
            else:
                # Non-tool steps are considered completed
                success = True
                logs = f"Completed: {step_name}"

            latency = time.time() - start_time

            # Update task status and record run
            if task_id:
                db.table("tasks").update({
                    "status": "completed" if success else "failed",
                }).eq("id", task_id).execute()

                db.table("runs").insert({
                    "task_id": task_id,
                    "logs": logs[:1000],
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

    def _find_tool(
        self, step_name: str, tools_map: dict, tools_ids: dict, db
    ) -> tuple[str, str | None]:
        """
        Find the best matching tool for a step.

        Search order:
        1. Exact key match in tools_map (from Toolsmith or skill tools)
        2. Partial match by key substring
        3. Search Supabase tools table by name similarity
        """
        step_key = step_name.lower().replace(" ", "_")

        # 1. Exact match
        if step_key in tools_map:
            return tools_map[step_key], tools_ids.get(step_key)

        # 2. Partial match
        for key, code in tools_map.items():
            if key in step_key or step_key in key:
                return code, tools_ids.get(key)

        # 3. Search DB for tools with similar names
        try:
            # Search for tools where the name is contained in the step name
            all_tools = db.table("tools").select(
                "id, name, code, trust_score"
            ).gte("trust_score", 0.3).execute()

            if all_tools.data:
                step_words = set(step_key.split("_"))
                best_match = None
                best_overlap = 0

                for tool in all_tools.data:
                    tool_words = set(
                        tool["name"].lower().replace("-", "_").split("_")
                    )
                    overlap = len(step_words & tool_words)
                    if overlap > best_overlap and overlap >= 2:
                        best_overlap = overlap
                        best_match = tool

                if best_match:
                    return best_match["code"], best_match["id"]
        except Exception:
            pass

        return "", None

    def _update_trust(self, db, tool_id: str, success: bool):
        """Update tool trust score based on execution result."""
        try:
            tool_rec = db.table("tools").select(
                "trust_score"
            ).eq("id", tool_id).execute()
            if tool_rec.data:
                old_score = tool_rec.data[0]["trust_score"]
                new_score = (
                    min(old_score + 0.1, 1.0)
                    if success
                    else max(old_score - 0.15, 0.1)
                )
                db.table("tools").update({
                    "trust_score": round(new_score, 2)
                }).eq("id", tool_id).execute()
        except Exception:
            pass
