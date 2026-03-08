"""
Goals API Routes.

CRUD operations for goals and mission launching.
"""

import asyncio
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.database import get_db
from app.models.schemas import GoalCreate, GoalResponse, MissionLaunchResponse
from app.orchestrator.graph import run_mission

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse)
async def create_goal(goal: GoalCreate):
    """Create a new goal."""
    db = get_db()
    insert_data = {
        "title": goal.title,
        "description": goal.description,
        "status": "pending",
        "schedule": goal.schedule,
    }
    if goal.skill_id:
        insert_data["skill_id"] = goal.skill_id

    result = db.table("goals").insert(insert_data).execute()

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


async def _execute_mission(goal_id: str):
    """Background task to run the full orchestration pipeline."""
    db = get_db()
    try:
        result = await run_mission(goal_id)

        # Update goal status based on result
        verified = result.get("verified", False)
        new_status = "completed" if verified else "failed"

        db.table("goals").update({
            "status": new_status,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", goal_id).execute()

    except Exception as e:
        # Mark goal as failed on error
        db.table("goals").update({
            "status": "failed",
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", goal_id).execute()

        # Log the error as a metric
        db.table("metrics").insert({
            "metric_name": "mission_error",
            "value": 1.0,
        }).execute()

        print(f"[AEGIS] Mission failed for goal {goal_id}: {e}")


@router.post("/{goal_id}/launch", response_model=MissionLaunchResponse)
async def launch_mission(goal_id: UUID, background_tasks: BackgroundTasks):
    """
    Launch a mission for a goal.

    Triggers the full agent orchestration pipeline in the background:
    GoalManager → Planner → Decomposer → Executor → Critic → Verifier → Memory → Monitor
    """
    db = get_db()

    # Verify goal exists
    goal = db.table("goals").select("*").eq("id", str(goal_id)).execute()
    if not goal.data:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Prevent re-launching already running goals
    if goal.data[0]["status"] == "running":
        raise HTTPException(status_code=409, detail="Goal is already running")

    # Update goal status to running
    db.table("goals").update({"status": "running"}).eq("id", str(goal_id)).execute()

    # Launch the orchestrator pipeline in background
    background_tasks.add_task(_execute_mission, str(goal_id))

    return MissionLaunchResponse(
        goal_id=goal_id,
        plan_id=goal_id,  # Plan ID assigned during execution
        status="launched",
        message="Mission launched — agents are processing the goal",
    )
