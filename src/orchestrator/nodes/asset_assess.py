"""ASSET-ASSESSOR node -- stub for asset assessment module (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetAssessAgent(AgentBase):
    """Assesses discovered assets for criticality and scope. Stub implementation."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-assessor", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "asset-assessor is a stub: asset assessment module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state["current_stage"] = "asset-assessor"
        return state
