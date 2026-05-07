from abc import ABC, abstractmethod
from typing import Any

from src.intelligence.config import CrawlConfig
from src.intelligence.models import CleanedDocument, RawDocument


class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, query: str, config: CrawlConfig) -> list[RawDocument]:
        ...


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        ...


class BaseRAGClient(ABC):
    @abstractmethod
    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 10, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...
