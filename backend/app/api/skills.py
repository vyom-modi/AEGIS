"""
Skills API Routes.

Endpoints for browsing, syncing, importing, and installing
Anthropic Agent Skills.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.database import get_db
from app.skills.sync import sync_anthropic_skills, import_skill_from_url
from app.skills.generator import generate_tool_from_skill
from pydantic import BaseModel


router = APIRouter(prefix="/skills", tags=["skills"])


class SkillImportRequest(BaseModel):
    url: str


class SkillInstallResponse(BaseModel):
    success: bool
    tool_id: str | None = None
    tool_name: str | None = None
    trust_score: float = 0.0
    recommendation: str = ""
    error: str | None = None


# ── Background sync state ────────────────────
_sync_status = {"running": False, "last_result": None}


async def _run_sync():
    """Background sync job."""
    global _sync_status
    _sync_status["running"] = True
    try:
        result = await sync_anthropic_skills()
        _sync_status["last_result"] = result
    except Exception as e:
        _sync_status["last_result"] = {"error": str(e)}
    finally:
        _sync_status["running"] = False


@router.get("")
async def list_skills(
    installed: bool | None = None,
    skill_type: str | None = None,
):
    """List all skills, with optional filters."""
    db = get_db()
    query = db.table("skills").select("*").order("created_at", desc=True)

    if installed is not None:
        query = query.eq("installed", installed)

    result = query.execute()

    skills = result.data
    # Filter by skill_type in metadata if requested
    if skill_type:
        skills = [
            s for s in skills
            if s.get("metadata", {}).get("skill_type") == skill_type
        ]

    return skills


@router.post("/sync")
async def sync_skills(background_tasks: BackgroundTasks):
    """Trigger a sync from the Anthropic skills repo."""
    if _sync_status["running"]:
        return {"status": "already_running", "message": "Sync is already in progress"}

    background_tasks.add_task(_run_sync)
    return {"status": "started", "message": "Syncing skills from Anthropic repo..."}


@router.get("/sync/status")
async def get_sync_status():
    """Get the current sync status."""
    return {
        "running": _sync_status["running"],
        "last_result": _sync_status["last_result"],
    }


@router.get("/{skill_id}")
async def get_skill(skill_id: UUID):
    """Get a specific skill by ID."""
    db = get_db()
    result = db.table("skills").select("*").eq("id", str(skill_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Skill not found")

    return result.data[0]


@router.post("/{skill_id}/install")
async def install_skill(skill_id: UUID):
    """
    Install a skill by generating a validated AEGIS tool from it.

    The tool is validated, trust-scored, and registered.
    """
    result = await generate_tool_from_skill(str(skill_id))

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Installation failed"),
        )

    return SkillInstallResponse(
        success=True,
        tool_id=result.get("tool_id"),
        tool_name=result.get("tool_name"),
        trust_score=result.get("trust_score", 0),
        recommendation=result.get("recommendation", ""),
    )


@router.post("/import-url")
async def import_skill_url(body: SkillImportRequest):
    """Import a skill from any SKILL.md URL."""
    try:
        result = await import_skill_from_url(body.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
