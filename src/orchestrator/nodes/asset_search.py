"""ASSET-SEARCH node -- integrates with asset discovery module."""
from __future__ import annotations

from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class AssetSearchAgent(AgentBase):
    """Discovers network assets associated with the target."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="asset-search", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        try:
            from src.asset_discovery.module import AssetDiscoveryModule

            module = AssetDiscoveryModule()
            dsl_queries = state.get("dsl_queries", [])
            if not dsl_queries:
                dsl_queries = [
                    {"platform": "fofa", "query": state.get("company_name", "")},
                    {"platform": "hunter", "query": state.get("company_name", "")},
                ]

            result = await module.run(
                task_id=task_id,
                dsl_queries=dsl_queries,
                company_name=state.get("company_name"),
                target_domains=state.get("domains"),
                target_icp_entity=state.get("company_name"),
                target_ip_ranges=state.get("ip_ranges"),
            )

            state["assets"] = module.get_assets(page=1, page_size=10000)[0]
            state["asset_search_result"] = {
                "status": result.status.value,
                "total_searched": result.total_searched,
                "total_confirmed": result.total_confirmed,
                "total_enriched": result.total_enriched,
                "by_asset_type": result.by_asset_type,
                "avg_confidence": result.avg_confidence,
            }
            logger.info(
                "Asset search completed for task %s: %d assets found",
                task_id,
                result.total_enriched,
                extra={"task_id": task_id},
            )

        except Exception as e:
            logger.exception(
                "Asset search failed for task %s: %s",
                task_id,
                e,
                extra={"task_id": task_id},
            )
            state.setdefault("assets", [])
            state["asset_search_error"] = str(e)

        state["current_stage"] = "asset-search"
        return state
