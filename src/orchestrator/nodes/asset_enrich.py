"""ASSET-ENRICHER node -- stub for asset enrichment module (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetEnrichAgent(AgentBase):
    """Enriches assets with additional metadata. Stub implementation."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-enricher", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "asset-enricher is a stub: asset enrichment module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state["current_stage"] = "asset-enricher"
        return state
