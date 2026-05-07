"""PENTEST-EXECUTOR node -- stub for pentest execution (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class TestExecAgent(AgentBase):
    """Executes generated penetration test cases against targets. Stub."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="pentest-executor", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "pentest-executor is a stub: test execution module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state["current_stage"] = "pentest-executor"
        return state
