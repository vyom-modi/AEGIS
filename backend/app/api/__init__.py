"""
AEGIS API Package.

Registers all route modules with the FastAPI router.
"""

from fastapi import APIRouter

from app.api.goals import router as goals_router
from app.api.plans import router as plans_router
from app.api.tasks import router as tasks_router
from app.api.tools import router as tools_router
from app.api.metrics import router as metrics_router
from app.api.missions import router as missions_router

api_router = APIRouter(prefix="/api")

api_router.include_router(goals_router)
api_router.include_router(plans_router)
api_router.include_router(tasks_router)
api_router.include_router(tools_router)
api_router.include_router(metrics_router)
api_router.include_router(missions_router)
