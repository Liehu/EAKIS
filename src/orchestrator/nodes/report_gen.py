"""REPORT-GEN node -- stub for report generation (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class ReportGenAgent(AgentBase):
    """Generates final assessment report from all gathered data. Stub."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="report-gen", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "report-gen is a stub: report generation module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state.setdefault("reports", [])
        state["current_stage"] = "report-gen"
        return state
