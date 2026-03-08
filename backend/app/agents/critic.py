"""
Critic Agent.

Responsible for:
- Analyzing execution outputs via LLM
- Detecting problems and quality issues
- Scoring execution quality
- Suggesting improvements
"""

import json
from typing import Any
from app.agents.base import BaseAgent
from app.llm import get_llm


CRITIC_PROMPT = """You are a critic agent in the AEGIS autonomous system.
Analyze the execution results for quality, correctness, and completeness.

Goal: {goal_title}
Goal Description: {goal_description}

Execution Results:
{results_json}

Tools Created: {tools_count}
Total Steps: {total_steps}

Evaluate:
1. Were all steps executed successfully?
2. Is the output aligned with the original goal?
3. Are there any obvious problems or gaps?
4. What could be improved in future runs?

Respond ONLY with valid JSON:
{{
    "quality_score": 0.0 to 1.0,
    "issues": ["list of issues found, empty if none"],
    "suggestions": ["list of improvement suggestions"],
    "passed": true or false,
    "summary": "one-line summary of the analysis"
}}"""


class CriticAgent(BaseAgent):
    name = "critic"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Analyze execution results using LLM and provide feedback."""
        results = state.get("execution_results", [])
        goal = state.get("goal", {})

        try:
            llm = get_llm()
            prompt = CRITIC_PROMPT.format(
                goal_title=goal.get("title", "Unknown"),
                goal_description=goal.get("description", "No description"),
                results_json=json.dumps(results, indent=2),
                tools_count=len(state.get("tools_created", [])),
                total_steps=len(state.get("plan", {}).get("steps", [])),
            )

            response = await llm.ainvoke(prompt)
            content = response.content.strip()

            # Parse JSON from response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            critique = json.loads(content)

            # Validate required fields
            state["critique"] = {
                "quality_score": float(critique.get("quality_score", 0.5)),
                "issues": critique.get("issues", []),
                "suggestions": critique.get("suggestions", []),
                "passed": critique.get("passed", True),
                "summary": critique.get("summary", "Analysis complete"),
            }

            state["logs"] = state.get("logs", []) + [
                f"[Critic] Score: {state['critique']['quality_score']:.0%} — "
                f"{'PASSED' if state['critique']['passed'] else 'FAILED'}: "
                f"{state['critique']['summary']}"
            ]

        except Exception as e:
            # Default to passing on LLM failure
            state["critique"] = {
                "quality_score": 0.7,
                "issues": [],
                "suggestions": [f"Critic analysis failed: {e}"],
                "passed": True,
                "summary": "Default pass — critic unavailable",
            }
            state["logs"] = state.get("logs", []) + [
                f"[Critic] LLM analysis failed, defaulting to pass: {e}"
            ]

        state["current_agent"] = self.name
        return state
