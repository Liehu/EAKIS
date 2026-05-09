"""RAG knowledge-base client — incremental indexing with Qdrant + in-memory fallback."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from src.intelligence.models import CleanedDocument
from src.intelligence.services.base import BaseRAGClient
from src.intelligence.services.embeddings import StubEmbeddingService
from src.shared.metrics import RAG_UPSERT_COUNT, RAG_SEARCH_COUNT

logger = logging.getLogger("eakis.rag.client")


class QdrantRAGClient(BaseRAGClient):
    """Production RAG client backed by Qdrant vector store.

    Requires ``qdrant-client`` to be installed and a running Qdrant instance.
    All qdrant_client imports are deferred to construction time so that the
    rest of the module (InMemoryRAGClient, StubRAGClient) works without it.
    """

    def __init__(self, client: Any = None) -> None:
        from src.core.settings import get_settings
        from src.intelligence.services.embeddings import EmbeddingService

        settings = get_settings()
        self._embedding = EmbeddingService()
        self._collection = settings.qdrant_collection
        self._vector_size = self._embedding.vector_size

        if client is not None:
            self._client = client
        else:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        from qdrant_client import models

        existing = self._client.get_collections().collections
        names = [c.name for c in existing]
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=self._vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'", self._collection)

    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        from qdrant_client import models

        if not docs:
            return 0

        texts = [d.content for d in docs]
        vectors = await self._embedding.embed_texts(texts)

        points = []
        for doc, vec in zip(docs, vectors):
            payload: dict[str, Any] = {
                "task_id": task_id,
                "content": doc.content,
                "source_type": doc.source_type.value,
                "source_name": doc.source_name,
                "source_url": doc.source_url,
                "published_at": doc.published_at.isoformat() if doc.published_at else None,
                "quality_score": doc.quality_score,
                "entities": doc.entities,
                "checksum": doc.checksum,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{task_id}:{doc.checksum}"))
            points.append(models.PointStruct(id=point_id, vector=vec, payload=payload))

        batch_size = 100
        for start in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=self._collection,
                points=points[start : start + batch_size],
            )

        RAG_UPSERT_COUNT.inc(len(docs))
        logger.info("Upserted %d documents into RAG (task=%s)", len(docs), task_id)
        return len(docs)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        from qdrant_client import models

        query_vector = await self._embedding.embed_query(query)
        qdrant_filter = self._build_filter(filter) if filter else None

        hits = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            with_payload=True,
        )

        RAG_SEARCH_COUNT.inc()
        return [
            {
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "content"},
            }
            for hit in hits
        ]

    async def delete_by_task(self, task_id: str) -> int:
        from qdrant_client import models

        result, _ = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="task_id", match=models.MatchValue(value=task_id))]
            ),
            limit=10000,
            with_payload=False,
        )
        if result:
            ids = [p.id for p in result]
            self._client.delete(
                collection_name=self._collection,
                points_selector=models.PointIdsList(points=ids),
            )
            logger.info("Deleted %d documents from RAG (task=%s)", len(ids), task_id)
            return len(ids)
        return 0

    async def health_check(self) -> dict[str, Any]:
        try:
            info = self._client.get_collection(self._collection)
            return {
                "status": "healthy",
                "collection": self._collection,
                "vector_count": info.points_count,
                "vector_size": self._vector_size,
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    @staticmethod
    def _build_filter(filter: dict[str, Any]) -> Any:
        from qdrant_client import models

        conditions: list[models.FieldCondition] = []
        for key, value in filter.items():
            if isinstance(value, list):
                conditions.append(models.FieldCondition(key=key, match=models.MatchAny(any=value)))
            else:
                conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
        return models.Filter(must=conditions)


class InMemoryRAGClient(BaseRAGClient):
    """In-memory RAG client for development and testing (no Qdrant dependency)."""

    def __init__(self, embedding: StubEmbeddingService | None = None) -> None:
        self._embedding = embedding or StubEmbeddingService()
        self._documents: dict[str, dict[str, Any]] = {}
        self._vectors: dict[str, list[float]] = {}
        self._task_index: dict[str, set[str]] = {}
        self._checksum_index: dict[str, str] = {}

    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        if not docs:
            return 0

        vectors = await self._embedding.embed_texts([d.content for d in docs])
        count = 0

        for doc, vec in zip(docs, vectors):
            doc_id = f"{task_id}:{doc.checksum}"
            if doc_id in self._documents:
                continue

            self._documents[doc_id] = {
                "task_id": task_id,
                "content": doc.content,
                "source_type": doc.source_type.value,
                "source_name": doc.source_name,
                "source_url": doc.source_url,
                "published_at": doc.published_at.isoformat() if doc.published_at else None,
                "quality_score": doc.quality_score,
                "entities": doc.entities,
                "checksum": doc.checksum,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
            self._vectors[doc_id] = vec
            self._task_index.setdefault(task_id, set()).add(doc_id)
            self._checksum_index[doc.checksum] = doc_id
            count += 1

        RAG_UPSERT_COUNT.inc(count)
        logger.info("Upserted %d documents into in-memory RAG (task=%s)", count, task_id)
        return count

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._documents:
            return []

        query_vec = await self._embedding.embed_query(query)

        scored: list[tuple[float, str]] = []
        for doc_id, vec in self._vectors.items():
            doc = self._documents[doc_id]
            if filter and not self._matches_filter(doc, filter):
                continue
            score = self._cosine_similarity(query_vec, vec)
            scored.append((score, doc_id))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_results = scored[:top_k]

        RAG_SEARCH_COUNT.inc()
        return [
            {
                "content": self._documents[doc_id]["content"],
                "score": round(score, 4),
                "metadata": {k: v for k, v in self._documents[doc_id].items() if k != "content"},
            }
            for score, doc_id in top_results
        ]

    async def delete_by_task(self, task_id: str) -> int:
        doc_ids = self._task_index.pop(task_id, set())
        for doc_id in doc_ids:
            doc = self._documents.pop(doc_id, None)
            if doc and doc.get("checksum"):
                self._checksum_index.pop(doc["checksum"], None)
            self._vectors.pop(doc_id, None)
        if doc_ids:
            logger.info("Deleted %d docs from in-memory RAG (task=%s)", len(doc_ids), task_id)
        return len(doc_ids)

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "collection": "in-memory",
            "vector_count": len(self._documents),
            "vector_size": self._embedding.vector_size,
        }

    async def get_stats(self) -> dict[str, Any]:
        return {
            "total_documents": len(self._documents),
            "total_tasks": len(self._task_index),
            "vector_size": self._embedding.vector_size,
        }

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _matches_filter(doc: dict[str, Any], filter: dict[str, Any]) -> bool:
        for key, value in filter.items():
            doc_val = doc.get(key)
            if isinstance(value, list):
                if doc_val not in value:
                    return False
            elif doc_val != value:
                return False
        return True


class StubRAGClient(BaseRAGClient):
    """Legacy stub for backward compatibility."""

    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        return len(docs)

    async def search(self, query: str, top_k: int = 10, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [
            {"content": f"RAG模拟结果：{query}相关的历史情报", "score": 0.85, "metadata": {"source": "stub"}}
        ]


def create_rag_client(use_stubs: bool | None = None) -> BaseRAGClient:
    """Factory: create the appropriate RAG client based on settings."""
    from src.core.settings import get_settings

    settings = get_settings()
    use_stubs = use_stubs if use_stubs is not None else settings.rag_use_stubs

    if not use_stubs:
        try:
            return QdrantRAGClient()
        except Exception:
            logger.warning("Qdrant unavailable, falling back to InMemoryRAGClient")

    return InMemoryRAGClient()
