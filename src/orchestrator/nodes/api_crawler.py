"""APICRAWL-BROWSER node -- discovers API interfaces via ApiCrawlerModule."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class ApiCrawlerAgent(AgentBase):
    """Crawls web assets to discover and classify API interfaces."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="apicrawl-browser", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        assets = state.get("assets", [])

        try:
            from src.api_crawler.module import ApiCrawlerModule

            module = ApiCrawlerModule()
            await module.run(task_id=task_id, assets=assets)

            interfaces = module.get_interfaces()
            state["interfaces"] = interfaces
            logger.info(
                "api_crawler discovered %d interfaces for %s",
                len(interfaces),
                task_id,
                extra={"task_id": task_id},
            )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"apicrawl-browser: {exc}")
            state["errors"] = errors
            logger.exception(
                "api_crawler failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "apicrawl-browser"
        return state
