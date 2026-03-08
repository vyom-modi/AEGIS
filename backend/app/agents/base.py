"""
Base Agent — Abstract interface for all AEGIS agents.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Base class for all AEGIS agents.

    Every agent must implement execute() which takes a state dict
    and returns an updated state dict. This is compatible with
    LangGraph's node function signature.
    """

    name: str = "base"

    @abstractmethod
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's task.

        Args:
            state: The current workflow state dict, passed through
                   the LangGraph graph.

        Returns:
            Updated state dict with this agent's contributions.
        """
        ...

    def __repr__(self) -> str:
        return f"<Agent: {self.name}>"
