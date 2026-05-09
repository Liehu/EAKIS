"""ASSET-ENRICHER node -- integrates with asset discovery enricher."""
from __future__ import annotations

from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetEnrichAgent(AgentBase):
    """Enriches assets with additional metadata."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-enricher", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        assets = state.get("assets", [])
        logger.info(
            "Asset enrichment for task %s: %d assets",
            task_id,
            len(assets),
            extra={"task_id": task_id},
        )

        state["asset_enrich_result"] = {
            "total_enriched": len(assets),
            "with_tech_stack": sum(
                1 for a in assets if a.get("tech_stack")
            ),
            "with_waf": sum(
                1 for a in assets if a.get("waf_detected")
            ),
        }
        state["current_stage"] = "asset-enricher"
        return state
