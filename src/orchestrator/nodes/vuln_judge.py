"""PENTEST-JUDGE node -- stub for vulnerability judgment (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class VulnJudgeAgent(AgentBase):
    """Analyzes test results to confirm and classify vulnerabilities. Stub."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="pentest-judge", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "pentest-judge is a stub: vulnerability judgment module not yet "
            "implemented for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state.setdefault("vulnerabilities", [])
        state["current_stage"] = "pentest-judge"
        return state
