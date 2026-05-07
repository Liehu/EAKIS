"""PENTEST-CASEGEN node -- stub for pentest case generation (not yet implemented)."""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class TestGenAgent(AgentBase):
    """Generates penetration test cases from classified interfaces. Stub."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="pentest-casegen", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")

        logger.warning(
            "pentest-casegen is a stub: test generation module not yet implemented "
            "for task %s",
            task_id,
            extra={"task_id": task_id},
        )
        state["current_stage"] = "pentest-casegen"
        return state
