"""
Plans API Routes.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.schemas import PlanResponse

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/{goal_id}", response_model=list[PlanResponse])
async def get_plans(goal_id: UUID):
    """Get all plans for a goal."""
    db = get_db()
    result = (
        db.table("plans")
        .select("*")
        .eq("goal_id", str(goal_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
