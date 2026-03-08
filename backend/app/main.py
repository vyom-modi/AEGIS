"""
AEGIS — FastAPI Application Entry Point.

Mounts API routes, WebSocket endpoints, static file serving,
and provides a health check.
"""

from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AEGIS",
    description="Autonomous Execution & Governance Intelligent System",
    version="0.1.0",
)

# CORS — allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if (FRONTEND_DIR / "static").exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR / "static")),
        name="static",
    )


# ── Health Check ──────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


# ── Frontend Page Serving ─────────────────────

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard page."""
    return FileResponse(str(FRONTEND_DIR / "templates" / "dashboard.html"))


@app.get("/mission")
async def serve_mission():
    """Serve the mission page."""
    return FileResponse(str(FRONTEND_DIR / "templates" / "mission.html"))


@app.get("/tools")
async def serve_tools():
    """Serve the tools page."""
    return FileResponse(str(FRONTEND_DIR / "templates" / "tools.html"))


@app.get("/agents")
async def serve_agents():
    """Serve the agents page."""
    return FileResponse(str(FRONTEND_DIR / "templates" / "agents.html"))


# ── WebSocket — Live Logs ─────────────────────

class ConnectionManager:
    """Manages WebSocket connections for live log streaming."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)

    async def broadcast(self, task_id: str, message: str):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                await connection.send_text(message)


ws_manager = ConnectionManager()


@app.websocket("/ws/logs/{task_id}")
async def websocket_logs(websocket: WebSocket, task_id: str):
    """Stream live logs for a task via WebSocket."""
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast(task_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)
