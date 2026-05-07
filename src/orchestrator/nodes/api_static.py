"""APICRAWL-STATIC node -- stub for static API analysis (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class ApiStaticAgent(AgentBase):
    """Performs static analysis on JavaScript bundles and config files. Stub."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="apicrawl-static", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "apicrawl-static is a stub: static analysis not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state["current_stage"] = "apicrawl-static"
        return state
