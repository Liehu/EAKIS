"""ASSET-SEARCH node -- stub for asset discovery module (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetSearchAgent(AgentBase):
    """Discovers network assets associated with the target. Stub implementation."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-search", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "asset-search is a stub: asset discovery module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state.setdefault("assets", [])
        state["current_stage"] = "asset-search"
        return state
