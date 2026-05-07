"""OSINT-CRAWLER node -- crawls and cleans OSINT data via IntelligenceModule."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class CrawlerAgent(AgentBase):
    """Crawls and cleans OSINT intelligence documents."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="osint-crawler", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        company_name = state.get("company_name", "")

        try:
            from src.intelligence.module import IntelligenceModule

            module = IntelligenceModule()
            await module.run(
                task_id=task_id,
                company_name=company_name,
                industry=state.get("industry"),
                domains=state.get("domains"),
                keywords=state.get("keywords"),
            )

            documents = module.get_documents()
            state["intel_documents"] = documents
            logger.info(
                "crawler collected %d documents for %s",
                len(documents),
                task_id,
                extra={"task_id": task_id},
            )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"osint-crawler: {exc}")
            state["errors"] = errors
            logger.exception(
                "crawler failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "osint-crawler"
        return state
