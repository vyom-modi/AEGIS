"""
AEGIS Pydantic Schemas.

Data models for API request/response validation and database mapping.
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Goals
# ──────────────────────────────────────────────

class GoalCreate(BaseModel):
    """Request body for creating a new goal."""
    title: str
    description: str
    schedule: Optional[str] = None
    skill_id: Optional[str] = None


class GoalResponse(BaseModel):
    """Goal as returned from the API."""
    id: UUID
    title: str
    description: str
    status: str = "pending"
    schedule: Optional[str] = None
    skill_id: Optional[str] = None
    created_at: datetime
    last_run_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# Plans
# ──────────────────────────────────────────────

class PlanResponse(BaseModel):
    """Execution plan for a goal."""
    id: UUID
    goal_id: UUID
    plan_json: dict[str, Any]
    score: Optional[float] = None
    created_at: datetime


# ──────────────────────────────────────────────
# Tasks
# ──────────────────────────────────────────────

class TaskResponse(BaseModel):
    """Individual task within a plan."""
    id: UUID
    plan_id: UUID
    name: str
    description: str
    status: str = "pending"
    assigned_agent: Optional[str] = None
    retries: int = 0
    created_at: datetime


# ──────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────

class RunResponse(BaseModel):
    """Execution run record for a task."""
    id: UUID
    task_id: UUID
    logs: Optional[str] = None
    success: bool = False
    token_cost: Optional[float] = None
    latency: Optional[float] = None
    created_at: datetime


# ──────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────

class ToolCreate(BaseModel):
    """Request body for registering a tool."""
    name: str
    code: str
    description: str


class ToolResponse(BaseModel):
    """Registered tool."""
    id: UUID
    name: str
    code: str
    description: str
    trust_score: float = 0.0
    created_at: datetime


# ──────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────

class MetricResponse(BaseModel):
    """Telemetry metric."""
    id: UUID
    metric_name: str
    value: float
    timestamp: datetime


# ──────────────────────────────────────────────
# Strategies
# ──────────────────────────────────────────────

class StrategyResponse(BaseModel):
    """Agent strategy record."""
    id: UUID
    name: str
    parameters: dict[str, Any]
    success_rate: float = 0.0


# ──────────────────────────────────────────────
# Mission Launch
# ──────────────────────────────────────────────

class MissionLaunchResponse(BaseModel):
    """Response after launching a mission."""
    goal_id: UUID
    plan_id: Optional[UUID] = None
    status: str = "launched"
    message: str = "Mission launched successfully"
