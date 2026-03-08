"""
Mission Status API Routes.

Provides detailed status of mission execution including
all plans, tasks, runs, and agent logs.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/{goal_id}/status")
async def get_mission_status(goal_id: UUID):
    """
    Get full mission status for a goal — goal, plans, tasks, and runs.
    """
    db = get_db()

    # Get goal
    goal = db.table("goals").select("*").eq("id", str(goal_id)).execute()
    if not goal.data:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Get plans
    plans = (
        db.table("plans")
        .select("*")
        .eq("goal_id", str(goal_id))
        .order("created_at", desc=True)
        .execute()
    )

    # Get tasks for each plan
    plan_ids = [p["id"] for p in plans.data]
    tasks = []
    for pid in plan_ids:
        t = db.table("tasks").select("*").eq("plan_id", pid).order("created_at").execute()
        tasks.extend(t.data)

    # Get runs for each task
    task_ids = [t["id"] for t in tasks]
    runs = []
    for tid in task_ids:
        r = db.table("runs").select("*").eq("task_id", tid).execute()
        runs.extend(r.data)

    return {
        "goal": goal.data[0],
        "plans": plans.data,
        "tasks": tasks,
        "runs": runs,
    }
