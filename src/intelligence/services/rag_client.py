from typing import Any

from src.intelligence.models import CleanedDocument
from src.intelligence.services.base import BaseRAGClient


class StubRAGClient(BaseRAGClient):
    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        return len(docs)

    async def search(self, query: str, top_k: int = 10, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [
            {"content": f"RAG模拟结果：{query}相关的历史情报", "score": 0.85, "metadata": {"source": "stub"}}
        ]
