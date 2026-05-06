from abc import ABC, abstractmethod
from typing import Any

from src.orchestrator.state import GlobalState


class AgentBase(ABC):
    def __init__(self, name: str, llm_client: Any) -> None:
        self.name = name
        self.llm_client = llm_client

    @abstractmethod
    async def run(self, state: GlobalState) -> GlobalState:
        ...
