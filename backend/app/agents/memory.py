"""
Memory Agent.

Responsible for:
- Storing embeddings in Supabase pgvector
- Retrieving relevant context for agents
"""

from typing import Any
from app.agents.base import BaseAgent
from app.database import get_db


class MemoryAgent(BaseAgent):
    name = "memory"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Store execution context as embeddings for future recall."""
        # TODO: Generate embeddings and store in pgvector
        state["current_agent"] = self.name
        state["logs"] = state.get("logs", []) + [
            "[Memory] Context stored for future reference"
        ]

        return state
