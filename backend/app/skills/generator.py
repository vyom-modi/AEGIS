"""
Skill Tool Generator.

Converts Anthropic Agent Skills into AEGIS tools:
1. Skills with Python code fences → extract and wrap as run() tool
2. Instructional skills → LLM generates a tool skeleton from description
3. Validates generated code via sandbox runner
4. Computes trust score and registers in Supabase
"""

import json
from typing import Any
from app.database import get_db
from app.llm import get_llm
from app.sandbox.runner import validate_code
from app.skills.parser import parse_skill_md
from app.skills.trust import compute_trust_score


TOOL_GEN_PROMPT = """You are a tool-generating agent in the AEGIS autonomous system.
Generate a Python tool based on this Anthropic Agent Skill.

Skill Name: {name}
Skill Description: {description}
Skill Type: {skill_type}

The tool MUST follow this exact format:
```python
def run(input: dict) -> dict:
    \"\"\"Brief description based on the skill.\"\"\"
    # Implementation using only standard library
    return {{"result": "output", "success": True}}
```

Rules:
- Use ONLY standard library imports (json, math, datetime, re, collections, etc.)
- Do NOT import: os, sys, subprocess, socket, http, urllib, pathlib
- Handle errors with try/except
- Return a dict with "result" and "success" keys
- Model the tool's behavior based on the skill description
- Keep the function focused and under 30 lines

Return ONLY the Python code. No markdown, no explanation."""


async def generate_tool_from_skill(skill_id: str) -> dict[str, Any]:
    """
    Generate an AEGIS tool from a skill record.

    Process:
    1. Fetch skill from Supabase
    2. Parse skill markdown for code blocks
    3. Generate or extract tool code
    4. Validate code safety
    5. Compute trust score
    6. Register tool in Supabase
    """
    db = get_db()

    # Fetch skill
    skill_result = db.table("skills").select("*").eq("id", skill_id).execute()
    if not skill_result.data:
        return {"success": False, "error": "Skill not found"}

    skill = skill_result.data[0]
    parsed = parse_skill_md(skill.get("raw_markdown", ""))

    # Try to extract Python code from code blocks
    python_blocks = [
        b for b in parsed["code_blocks"]
        if b["language"] in ("python", "py")
    ]

    code = None
    generated_by_llm = False

    if python_blocks:
        # Use the best Python code block
        best_block = _select_best_code_block(python_blocks)
        code = _wrap_as_tool(best_block, parsed["name"], parsed["description"])
    else:
        # LLM-assisted generation
        code = await _generate_with_llm(parsed)
        generated_by_llm = True

    if not code:
        return {"success": False, "error": "Could not generate tool code"}

    # Validate
    is_valid, error = validate_code(code)

    # Compute trust score
    is_anthropic = "anthropics/skills" in (skill.get("source_url") or "")
    trust_result = compute_trust_score(
        license_text=skill.get("license"),
        code_validates=is_valid,
        has_blocked_imports=not is_valid,
        is_anthropic_official=is_anthropic,
        has_python_code=bool(python_blocks),
    )

    if not is_valid and trust_result["recommendation"] == "blocked":
        return {
            "success": False,
            "error": f"Tool blocked: {error}",
            "trust_score": trust_result["trust_score"],
            "breakdown": trust_result["breakdown"],
        }

    # Register tool
    tool_name = parsed["name"].lower().replace(" ", "_").replace("-", "_")
    tool_record = db.table("tools").insert({
        "name": f"skill_{tool_name}",
        "description": parsed["description"][:200],
        "code": code,
        "trust_score": trust_result["trust_score"],
        "skill_id": skill_id,
        "auto_installed": trust_result["auto_install"],
    }).execute()

    tool_id = tool_record.data[0]["id"] if tool_record.data else None

    # Mark skill as installed
    db.table("skills").update({
        "installed": True,
        "trust_score": trust_result["trust_score"],
        "installed_at": "now()",
    }).eq("id", skill_id).execute()

    return {
        "success": True,
        "tool_id": tool_id,
        "tool_name": f"skill_{tool_name}",
        "trust_score": trust_result["trust_score"],
        "breakdown": trust_result["breakdown"],
        "recommendation": trust_result["recommendation"],
        "generated_by_llm": generated_by_llm,
        "code_valid": is_valid,
    }


def _select_best_code_block(blocks: list[dict]) -> str:
    """Select the most meaningful Python code block."""
    # Prefer blocks with function definitions
    for block in blocks:
        if "def " in block["code"]:
            return block["code"]

    # Prefer longer blocks
    blocks.sort(key=lambda b: len(b["code"]), reverse=True)
    return blocks[0]["code"]


def _wrap_as_tool(code: str, name: str, description: str) -> str:
    """Wrap extracted Python code as an AEGIS tool with run() function."""
    # If it already has a run() function, use as-is
    if "def run(" in code:
        return code

    # Wrap the code in a run() function
    indented = "\n".join(f"    {line}" for line in code.split("\n"))

    return f'''def run(input: dict) -> dict:
    """{description[:100]}"""
    try:
{indented}
        return {{"result": "completed", "success": True}}
    except Exception as e:
        return {{"result": str(e), "success": False}}'''


async def _generate_with_llm(parsed: dict) -> str | None:
    """Use LLM to generate a tool from the skill description."""
    try:
        llm = get_llm()
        prompt = TOOL_GEN_PROMPT.format(
            name=parsed["name"],
            description=parsed["description"][:300],
            skill_type=parsed["skill_type"],
        )

        response = await llm.ainvoke(prompt)
        code = response.content.strip()

        # Clean markdown code blocks
        if "```" in code:
            parts = code.split("```")
            code = parts[1] if len(parts) > 1 else code
            if code.startswith("python"):
                code = code[6:]
            code = code.strip()

        return code

    except Exception:
        return None
