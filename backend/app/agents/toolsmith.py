"""
Toolsmith Agent.

Responsible for:
- Generating Python tools automatically
- Registering tools in Supabase
- Validating tools before use
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db
from app.llm import get_llm


TOOLSMITH_PROMPT = """You are a tool-creating agent in the AEGIS autonomous system.
Given a task description, generate a Python tool that accomplishes it.

Task: {task_description}

The tool must follow this format:
```python
def run(input: dict) -> dict:
    \"\"\"Brief description of what this tool does.\"\"\"
    # Implementation
    return {{"result": "output"}}
```

Requirements:
- Use only standard library imports
- Handle errors gracefully
- Return results as a dict
- Keep it simple and focused

Respond with ONLY the Python code, no markdown formatting."""


class ToolsmithAgent(BaseAgent):
    name = "toolsmith"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate tools for steps that require them."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])

        tools_created = []
        for step in steps:
            if step.get("requires_tool"):
                # TODO: Generate and register tool via LLM
                tools_created.append(step.get("name"))

        state["tools_created"] = tools_created
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            f"[Toolsmith] Created {len(tools_created)} tools"
        ]

        return state
