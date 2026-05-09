"""ASSET-ASSESS node -- integrates with asset discovery assessor."""
from __future__ import annotations

from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetAssessAgent(AgentBase):
    """Assesses discovered assets for criticality and scope."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-assessor", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        assets = state.get("assets", [])
        logger.info(
            "Asset assessment for task %s: %d assets to assess",
            task_id,
            len(assets),
            extra={"task_id": task_id},
        )

        state["asset_assess_result"] = {
            "total_assets": len(assets),
            "high_confidence": sum(
                1 for a in assets if a.get("confidence", 0) >= 0.85
            ),
            "medium_confidence": sum(
                1 for a in assets if 0.65 <= a.get("confidence", 0) < 0.85
            ),
            "needs_review": sum(
                1 for a in assets if a.get("confidence", 0) < 0.65
            ),
        }
        state["current_stage"] = "asset-assessor"
        return state
