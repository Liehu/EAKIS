"""KW-GENERATOR node -- generates, ranks, and expands keywords from summaries."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class KeywordGenAgent(AgentBase):
    """Generates and ranks keywords from intelligence summaries."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="kw-generator", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        company_name = state.get("company_name", "")
        industry = state.get("industry")

        try:
            from src.keywords.generator import KeywordGeneratorAgent as CoreGenerator
            from src.keywords.summarizer import StructuredSummary
            from src.keywords.ranker import KeywordRanker
            from src.keywords.expander import KeywordExpander
            from src.shared.llm_client import LLMClient

            llm = self.llm_client or LLMClient()
            ranker = KeywordRanker(domain=industry)
            generator = CoreGenerator(llm, ranker)

            summary_text = state.get("summary", "")
            summary = StructuredSummary(raw_text=summary_text)

            generated = await generator.generate(company_name, industry, summary)
            ranked = ranker.rank(generated.all)

            expander = KeywordExpander(llm)
            if ranked:
                expansion_results = await expander.expand(
                    ranked[:20], company_name=company_name,
                )
                for result in expansion_results:
                    ranked.extend(result.expanded)
                ranked = ranker.rank(ranked)

            state["keywords"] = [c.word for c in ranked]
            logger.info(
                "keyword_gen produced %d keywords for %s",
                len(ranked),
                task_id,
                extra={"task_id": task_id},
            )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"kw-generator: {exc}")
            state["errors"] = errors
            logger.exception(
                "keyword_gen failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "kw-generator"
        return state
