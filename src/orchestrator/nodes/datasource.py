"""OSINT-DATASOURCE node -- selects OSINT data sources via IntelligenceModule."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class DatasourceAgent(AgentBase):
    """Selects appropriate OSINT data sources for the target company."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="osint-datasource", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        company_name = state.get("company_name", "")
        industry = state.get("industry")

        try:
            from src.intelligence.module import IntelligenceModule

            module = IntelligenceModule()
            result = await module.run(
                task_id=task_id,
                company_name=company_name,
                industry=industry,
                domains=state.get("domains"),
                keywords=state.get("keywords"),
            )

            sources = module.get_sources()
            state["metadata"] = {
                **state.get("metadata", {}),
                "sources": sources,
                "collection_result": {
                    "status": result.status.value,
                    "total_sources": result.total_sources,
                    "total_documents": result.total_documents,
                },
            }
            logger.info(
                "datasource selected %d sources for %s",
                len(sources),
                task_id,
                extra={"task_id": task_id},
            )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"osint-datasource: {exc}")
            state["errors"] = errors
            logger.exception(
                "datasource failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "osint-datasource"
        return state
