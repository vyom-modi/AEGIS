"""
Tasks API Routes.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.schemas import TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID):
    """Get a specific task by ID."""
    db = get_db()
    result = db.table("tasks").select("*").eq("id", str(task_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")

    return result.data[0]


@router.get("/plan/{plan_id}", response_model=list[TaskResponse])
async def get_tasks_by_plan(plan_id: UUID):
    """Get all tasks for a plan."""
    db = get_db()
    result = (
        db.table("tasks")
        .select("*")
        .eq("plan_id", str(plan_id))
        .order("created_at")
        .execute()
    )
    return result.data
