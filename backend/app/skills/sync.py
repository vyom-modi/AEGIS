"""
Skill Sync Worker.

Fetches skills from the Anthropic skills GitHub repository:
- Reads the skills index via GitHub API
- Downloads each SKILL.md via raw.githubusercontent.com
- Parses and upserts into Supabase skills table
- Fetches LICENSE files when present
"""

import asyncio
import httpx
from typing import Any
from app.database import get_db
from app.skills.parser import parse_skill_md, generate_slug


GITHUB_API_BASE = "https://api.github.com/repos/anthropics/skills/contents"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/anthropics/skills/main"
SKILLS_PATH = "skills"


async def fetch_skill_index() -> list[dict[str, str]]:
    """Fetch the list of skill folders from GitHub API."""
    url = f"{GITHUB_API_BASE}/{SKILLS_PATH}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        items = resp.json()

    return [
        {"name": item["name"], "path": item["path"]}
        for item in items
        if item["type"] == "dir"
    ]


async def fetch_skill_md(skill_path: str) -> str | None:
    """Fetch the raw SKILL.md content for a skill folder."""
    url = f"{GITHUB_RAW_BASE}/{skill_path}/SKILL.md"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.text
    return None


async def fetch_license(skill_path: str) -> str | None:
    """Fetch LICENSE file if present."""
    for filename in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        url = f"{GITHUB_RAW_BASE}/{skill_path}/{filename}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text[:2000]  # Truncate
    return None


async def sync_anthropic_skills() -> dict[str, Any]:
    """
    Synchronize skills from the Anthropic repo into Supabase.

    Returns a summary of the sync operation.
    """
    db = get_db()

    # Fetch skill index
    skill_dirs = await fetch_skill_index()

    synced = 0
    skipped = 0
    errors = []

    for skill_dir in skill_dirs:
        skill_name = skill_dir["name"]
        skill_path = skill_dir["path"]

        try:
            # Fetch SKILL.md
            raw_md = await fetch_skill_md(skill_path)
            if not raw_md:
                skipped += 1
                continue

            # Parse
            parsed = parse_skill_md(raw_md)
            slug = generate_slug(parsed["name"])

            # Fetch license
            license_text = await fetch_license(skill_path)

            # Build metadata
            metadata = {
                "skill_type": parsed["skill_type"],
                "has_scripts": parsed["has_scripts"],
                "code_block_count": len(parsed["code_blocks"]),
                "python_blocks": len([
                    b for b in parsed["code_blocks"]
                    if b["language"] in ("python", "py")
                ]),
                "sections": [s["title"] for s in parsed["sections"]],
                "examples_count": len(parsed["examples"]),
            }
            if license_text:
                metadata["license_text"] = license_text

            source_url = f"https://github.com/anthropics/skills/tree/main/{skill_path}"

            # Upsert into Supabase (by slug)
            existing = db.table("skills").select("id").eq("slug", slug).execute()

            if existing.data:
                # Update
                db.table("skills").update({
                    "name": parsed["name"],
                    "description": parsed["description"][:500],
                    "license": parsed.get("license") or "Unknown",
                    "version": parsed.get("version"),
                    "source_url": source_url,
                    "raw_markdown": raw_md[:10000],
                    "metadata": metadata,
                    "last_scanned_at": "now()",
                }).eq("slug", slug).execute()
            else:
                # Insert
                db.table("skills").insert({
                    "name": parsed["name"],
                    "slug": slug,
                    "description": parsed["description"][:500],
                    "license": parsed.get("license") or "Unknown",
                    "version": parsed.get("version"),
                    "source_url": source_url,
                    "raw_markdown": raw_md[:10000],
                    "metadata": metadata,
                }).execute()

            synced += 1

            # Small delay to avoid rate limits
            await asyncio.sleep(0.3)

        except Exception as e:
            errors.append({"skill": skill_name, "error": str(e)})

    return {
        "total": len(skill_dirs),
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
    }


async def import_skill_from_url(url: str) -> dict[str, Any]:
    """
    Import a single skill from any SKILL.md URL.

    Accepts raw GitHub URLs or regular GitHub URLs.
    """
    # Normalize URL to raw format
    raw_url = url
    if "github.com" in url and "raw.githubusercontent.com" not in url:
        raw_url = url.replace("github.com", "raw.githubusercontent.com")
        raw_url = raw_url.replace("/blob/", "/")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(raw_url)
        resp.raise_for_status()
        raw_md = resp.text

    parsed = parse_skill_md(raw_md)
    slug = generate_slug(parsed["name"])

    db = get_db()

    # Check if already exists
    existing = db.table("skills").select("id").eq("slug", slug).execute()
    if existing.data:
        return {"status": "exists", "slug": slug, "id": existing.data[0]["id"]}

    metadata = {
        "skill_type": parsed["skill_type"],
        "has_scripts": parsed["has_scripts"],
        "code_block_count": len(parsed["code_blocks"]),
        "python_blocks": len([
            b for b in parsed["code_blocks"]
            if b["language"] in ("python", "py")
        ]),
        "source": "custom_url",
    }

    result = db.table("skills").insert({
        "name": parsed["name"],
        "slug": slug,
        "description": parsed["description"][:500],
        "license": parsed.get("license") or "Unknown",
        "source_url": url,
        "raw_markdown": raw_md[:10000],
        "metadata": metadata,
    }).execute()

    return {
        "status": "imported",
        "slug": slug,
        "id": result.data[0]["id"] if result.data else None,
    }
