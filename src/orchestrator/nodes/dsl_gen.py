"""OSINT-DSL node -- generates DSL queries via IntelligenceModule."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class DslGenAgent(AgentBase):
    """Generates platform-specific DSL queries for OSINT data collection."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="osint-dsl", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        company_name = state.get("company_name", "")
        industry = state.get("industry")

        try:
            from src.intelligence.module import IntelligenceModule

            module = IntelligenceModule()
            keywords = state.get("keywords", [])
            domains = state.get("domains", [])

            await module.datasource_agent.select_sources(company_name, industry)
            dsl_queries = await module.dsl_agent.generate(keywords, domains)

            queries_data = [
                {"platform": q.platform, "query": q.query, "valid": q.syntax_valid}
                for q in dsl_queries
            ]
            state["metadata"] = {
                **state.get("metadata", {}),
                "dsl_queries": queries_data,
            }
            logger.info(
                "dsl_gen produced %d queries for %s",
                len(queries_data),
                task_id,
                extra={"task_id": task_id},
            )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"osint-dsl: {exc}")
            state["errors"] = errors
            logger.exception(
                "dsl_gen failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "osint-dsl"
        return state
