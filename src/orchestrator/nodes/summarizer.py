"""KW-SUMMARIZER node -- compresses intelligence documents into structured summaries."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class SummarizerAgent(AgentBase):
    """Summarizes intelligence documents for keyword extraction."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="kw-summarizer", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        try:
            from src.keywords.summarizer import SummarizerAgent as CoreSummarizer
            from src.shared.llm_client import LLMClient

            llm = self.llm_client or LLMClient()
            summarizer = CoreSummarizer(llm)

            documents = state.get("intel_documents", [])
            doc_texts = [
                d.get("content", "") if isinstance(d, dict) else str(d)
                for d in documents
            ]

            if doc_texts:
                summary = await summarizer.summarize(doc_texts)
                state["summary"] = summary.to_text()
                logger.info(
                    "summarizer processed %d docs for %s",
                    len(doc_texts),
                    task_id,
                    extra={"task_id": task_id},
                )
            else:
                state["summary"] = ""
                logger.warning(
                    "summarizer skipped: no documents for %s",
                    task_id,
                    extra={"task_id": task_id},
                )
        except Exception as exc:
            errors = state.get("errors", [])
            errors.append(f"kw-summarizer: {exc}")
            state["errors"] = errors
            logger.exception(
                "summarizer failed for %s",
                task_id,
                extra={"task_id": task_id},
            )

        state["current_stage"] = "kw-summarizer"
        return state
