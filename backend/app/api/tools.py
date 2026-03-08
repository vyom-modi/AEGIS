"""
Tools API Routes.
"""

from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.schemas import ToolCreate, ToolResponse

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ToolResponse)
async def register_tool(tool: ToolCreate):
    """Register a new tool."""
    db = get_db()
    result = db.table("tools").insert({
        "name": tool.name,
        "code": tool.code,
        "description": tool.description,
        "trust_score": 0.0,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to register tool")

    return result.data[0]


@router.get("", response_model=list[ToolResponse])
async def list_tools():
    """List all registered tools."""
    db = get_db()
    result = db.table("tools").select("*").order("created_at", desc=True).execute()
    return result.data
