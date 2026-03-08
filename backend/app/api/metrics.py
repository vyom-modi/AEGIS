"""
Metrics API Routes.
"""

from fastapi import APIRouter
from app.database import get_db
from app.models.schemas import MetricResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricResponse])
async def get_metrics():
    """Get all telemetry metrics, most recent first."""
    db = get_db()
    result = (
        db.table("metrics")
        .select("*")
        .order("timestamp", desc=True)
        .limit(100)
        .execute()
    )
    return result.data
