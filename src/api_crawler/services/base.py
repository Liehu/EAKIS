from __future__ import annotations

from abc import ABC, abstractmethod

from src.api_crawler.models import CDPTrafficItem, CapturedRequest


class BaseBrowserClient(ABC):
    @abstractmethod
    async def navigate_and_interact(
        self,
        url: str,
        already_captured: list[str],
    ) -> list[CapturedRequest]:
        ...


class BaseCDPClient(ABC):
    @abstractmethod
    async def capture_traffic(self, url: str) -> list[CDPTrafficItem]:
        ...

    @abstractmethod
    async def capture_batch(self, urls: list[str]) -> list[CDPTrafficItem]:
        ...
