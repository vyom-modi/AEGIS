"""
SKILL.md Parser.

Parses Anthropic Agent Skills SKILL.md files:
- YAML frontmatter (name, description, license)
- Python code fences from the markdown body
- Example commands and usage patterns
- Classifies skill type (executable vs instructional)
"""

import re
from typing import Any
import frontmatter


def parse_skill_md(raw_markdown: str) -> dict[str, Any]:
    """
    Parse a SKILL.md file into structured data.

    Returns:
        {
            "name": str,
            "description": str,
            "license": str | None,
            "version": str | None,
            "code_blocks": [{"language": str, "code": str}],
            "examples": [str],
            "has_scripts": bool,
            "skill_type": "executable" | "instructional",
            "sections": [{"title": str, "content": str}],
        }
    """
    # Parse YAML frontmatter
    post = frontmatter.loads(raw_markdown)

    name = post.get("name", "unknown-skill")
    description = post.get("description", "")
    license_info = post.get("license", None)
    version = post.get("version", None)

    body = post.content

    # Extract code blocks
    code_blocks = _extract_code_blocks(body)

    # Extract examples
    examples = _extract_examples(body)

    # Check for scripts/ references
    has_scripts = "scripts/" in body

    # Classify skill type
    python_blocks = [b for b in code_blocks if b["language"] in ("python", "py")]
    skill_type = "executable" if python_blocks or has_scripts else "instructional"

    # Extract section headers
    sections = _extract_sections(body)

    return {
        "name": name,
        "description": description,
        "license": license_info,
        "version": version,
        "code_blocks": code_blocks,
        "examples": examples,
        "has_scripts": has_scripts,
        "skill_type": skill_type,
        "sections": sections,
    }


def _extract_code_blocks(text: str) -> list[dict[str, str]]:
    """Extract fenced code blocks with language tags."""
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    blocks = []
    for lang, code in matches:
        blocks.append({
            "language": lang.lower() if lang else "text",
            "code": code.strip(),
        })

    return blocks


def _extract_examples(text: str) -> list[str]:
    """Extract example usage patterns from the markdown."""
    examples = []

    # Look for content under "Example" headers
    example_pattern = r"##?\s*Example[s]?.*?\n(.*?)(?=\n##?\s|\Z)"
    matches = re.findall(example_pattern, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        clean = match.strip()
        if clean:
            examples.append(clean[:500])  # Truncate long examples

    return examples


def _extract_sections(text: str) -> list[dict[str, str]]:
    """Extract markdown sections with their headers."""
    sections = []
    pattern = r"^(#{1,3})\s+(.+)$"

    current_title = None
    current_content = []

    for line in text.split("\n"):
        header = re.match(pattern, line)
        if header:
            if current_title:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_content).strip()[:300],
                })
            current_title = header.group(2)
            current_content = []
        else:
            current_content.append(line)

    if current_title:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_content).strip()[:300],
        })

    return sections


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a skill name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
