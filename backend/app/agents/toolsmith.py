"""
Toolsmith Agent.

Responsible for:
- Generating Python tools automatically via LLM
- Registering tools in Supabase
- Validating generated code before storage
"""

import json
from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db
from app.llm import get_llm
from app.sandbox.runner import validate_code


TOOLSMITH_PROMPT = """You are a tool-creating agent in the AEGIS autonomous system.
Generate a Python tool for the following task.

Task: {task_name}
Description: {task_description}

The tool MUST follow this exact format:
```python
def run(input: dict) -> dict:
    \"\"\"Brief description.\"\"\"
    # Implementation using only standard library
    return {{"result": "output", "success": True}}
```

Rules:
- Use ONLY standard library imports (json, math, datetime, re, collections, etc.)
- Do NOT import: os, sys, subprocess, socket, http, urllib, pathlib
- Handle errors with try/except
- Return a dict with at least "result" and "success" keys
- Keep the function focused and under 30 lines

Return ONLY the Python code. No markdown, no explanation."""


def _compute_trust_score(code: str) -> float:
    """
    Compute initial trust score for generated tool code.

    Scores based on:
    - Has a docstring (+0.1)
    - Has try/except error handling (+0.15)
    - Returns dict with 'success' key (+0.1)
    - Has a run() function (+0.15)
    - Under 30 lines (+0.1)
    - Uses only standard lib (+0.1)
    - Base score: 0.3
    """
    score = 0.3

    if '"""' in code or "'''" in code:
        score += 0.1

    if "try:" in code and "except" in code:
        score += 0.15

    if '"success"' in code or "'success'" in code:
        score += 0.1

    if "def run(" in code:
        score += 0.15

    lines = code.strip().split("\n")
    if len(lines) <= 30:
        score += 0.1

    # Penalize for using non-standard imports
    non_std = ["pandas", "numpy", "requests", "beautifulsoup", "scrapy"]
    if not any(lib in code.lower() for lib in non_std):
        score += 0.1

    return round(min(score, 1.0), 2)


class ToolsmithAgent(BaseAgent):
    name = "toolsmith"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate and register tools for steps that require them."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])
        db = get_db()

        tools_created = []
        for step in steps:
            if not step.get("requires_tool"):
                continue

            task_name = step.get("name", "Unknown task")
            task_desc = step.get("description", "")

            try:
                llm = get_llm()
                prompt = TOOLSMITH_PROMPT.format(
                    task_name=task_name,
                    task_description=task_desc,
                )

                response = await llm.ainvoke(prompt)
                code = response.content.strip()

                # Clean markdown code blocks if present
                if "```" in code:
                    parts = code.split("```")
                    code = parts[1] if len(parts) > 1 else code
                    if code.startswith("python"):
                        code = code[6:]
                    code = code.strip()

                # Validate the generated code
                is_valid, error = validate_code(code)
                if not is_valid:
                    state["logs"] = state.get("logs", []) + [
                        f"[Toolsmith] Tool for '{task_name}' failed validation: {error}"
                    ]
                    continue

                # Compute initial trust score based on code quality
                trust_score = _compute_trust_score(code)

                # Register the tool in Supabase
                tool_record = db.table("tools").insert({
                    "name": task_name.lower().replace(" ", "_"),
                    "description": task_desc[:200],
                    "code": code,
                    "trust_score": trust_score,
                }).execute()

                if tool_record.data:
                    tools_created.append({
                        "name": task_name,
                        "tool_id": tool_record.data[0]["id"],
                    })

            except Exception as e:
                state["logs"] = state.get("logs", []) + [
                    f"[Toolsmith] Failed to generate tool for '{task_name}': {e}"
                ]

        state["tools_created"] = tools_created
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Toolsmith] Created {len(tools_created)} tools: "
            + ", ".join(t["name"] for t in tools_created)
        ]

        return state
