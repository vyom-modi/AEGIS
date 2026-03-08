"""
Goals API Routes.

CRUD operations for goals and mission launching.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.schemas import GoalCreate, GoalResponse, MissionLaunchResponse

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse)
async def create_goal(goal: GoalCreate):
    """Create a new goal."""
    db = get_db()
    result = db.table("goals").insert({
        "title": goal.title,
        "description": goal.description,
        "status": "pending",
        "schedule": goal.schedule,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create goal")

    return result.data[0]


@router.get("", response_model=list[GoalResponse])
async def list_goals():
    """List all goals, newest first."""
    db = get_db()
    result = db.table("goals").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: UUID):
    """Get a specific goal by ID."""
    db = get_db()
    result = db.table("goals").select("*").eq("id", str(goal_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Goal not found")

    return result.data[0]


@router.post("/{goal_id}/launch", response_model=MissionLaunchResponse)
async def launch_mission(goal_id: UUID):
    """
    Launch a mission for a goal.

    This triggers the full agent orchestration pipeline:
    GoalManager → Planner → Decomposer → Executor → Critic → Verifier
    """
    db = get_db()

    # Verify goal exists
    goal = db.table("goals").select("*").eq("id", str(goal_id)).execute()
    if not goal.data:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Update goal status
    db.table("goals").update({"status": "running"}).eq("id", str(goal_id)).execute()

    # TODO: Trigger orchestrator pipeline (Phase 2)
    # For now, create a placeholder plan
    plan_result = db.table("plans").insert({
        "goal_id": str(goal_id),
        "plan_json": {"steps": [], "status": "pending"},
        "score": 0.0,
    }).execute()

    if not plan_result.data:
        raise HTTPException(status_code=500, detail="Failed to create plan")

    return MissionLaunchResponse(
        goal_id=goal_id,
        plan_id=plan_result.data[0]["id"],
        status="launched",
        message="Mission launched — orchestrator will process the goal",
    )
