"""Unit tests for the RAG knowledge base (InMemoryRAGClient, EmbeddingService, StubEmbeddingService)."""

from __future__ import annotations

import pytest

from src.intelligence.models import CleanedDocument, SourceCategory
from src.intelligence.services.embeddings import StubEmbeddingService
from src.intelligence.services.rag_client import InMemoryRAGClient, StubRAGClient


def _make_doc(
    content: str = "测试文档内容关于Spring Boot微服务架构",
    source_type: SourceCategory = SourceCategory.NEWS,
    source_name: str = "测试新闻",
    checksum: str = "abc123",
    quality_score: float = 0.85,
    entities: list[str] | None = None,
) -> CleanedDocument:
    return CleanedDocument(
        content=content,
        source_type=source_type,
        source_name=source_name,
        source_url="https://example.com",
        published_at=None,
        quality_score=quality_score,
        entities=entities or ["Spring Boot"],
        checksum=checksum,
    )


# ---- StubEmbeddingService ----


class TestStubEmbeddingService:
    @pytest.mark.asyncio
    async def test_embed_texts_returns_vectors(self):
        svc = StubEmbeddingService(vector_dim=64)
        vectors = await svc.embed_texts(["hello", "world"])
        assert len(vectors) == 2
        for v in vectors:
            assert len(v) == 64
            assert abs(sum(x * x for x in v) - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_embed_query_returns_single_vector(self):
        svc = StubEmbeddingService()
        vec = await svc.embed_query("test query")
        assert len(vec) == svc.vector_size

    @pytest.mark.asyncio
    async def test_embed_texts_empty(self):
        svc = StubEmbeddingService()
        assert await svc.embed_texts([]) == []

    @pytest.mark.asyncio
    async def test_deterministic(self):
        svc = StubEmbeddingService()
        v1 = await svc.embed_query("same text")
        v2 = await svc.embed_query("same text")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_different_texts_differ(self):
        svc = StubEmbeddingService()
        v1 = await svc.embed_query("text A")
        v2 = await svc.embed_query("text B")
        assert v1 != v2

    def test_vector_size_property(self):
        svc = StubEmbeddingService(vector_dim=256)
        assert svc.vector_size == 256


# ---- InMemoryRAGClient ----


class TestInMemoryRAGClient:
    @pytest.mark.asyncio
    async def test_upsert_returns_count(self):
        client = InMemoryRAGClient()
        docs = [_make_doc(checksum="c1"), _make_doc(checksum="c2")]
        count = await client.upsert(docs, "task-1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_upsert_empty(self):
        client = InMemoryRAGClient()
        count = await client.upsert([], "task-1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_upsert_deduplicates_by_task_and_checksum(self):
        client = InMemoryRAGClient()
        docs = [_make_doc(checksum="c1"), _make_doc(checksum="c1")]
        count = await client.upsert(docs, "task-1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_same_checksum_different_task_is_allowed(self):
        client = InMemoryRAGClient()
        doc = _make_doc(checksum="c1")
        await client.upsert([doc], "task-1")
        count = await client.upsert([doc], "task-2")
        assert count == 1

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(content="Spring Boot 微服务", checksum="c1")], "task-1")
        results = await client.search("Spring Boot")
        assert len(results) == 1
        assert "Spring Boot" in results[0]["content"]
        assert results[0]["score"] > 0.0
        assert "metadata" in results[0]

    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        client = InMemoryRAGClient()
        results = await client.search("anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_top_k(self):
        client = InMemoryRAGClient()
        docs = [_make_doc(content=f"文档{i}", checksum=f"c{i}") for i in range(5)]
        await client.upsert(docs, "task-1")
        results = await client.search("文档", top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_with_task_id_filter(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(checksum="c1")], "task-A")
        await client.upsert([_make_doc(checksum="c2")], "task-B")
        results = await client.search("Spring Boot", top_k=10, filter={"task_id": "task-A"})
        assert len(results) == 1
        assert results[0]["metadata"]["task_id"] == "task-A"

    @pytest.mark.asyncio
    async def test_search_with_source_type_filter(self):
        client = InMemoryRAGClient()
        await client.upsert(
            [_make_doc(source_type=SourceCategory.NEWS, checksum="c1")],
            "task-1",
        )
        await client.upsert(
            [_make_doc(source_type=SourceCategory.OFFICIAL, checksum="c2")],
            "task-1",
        )
        results = await client.search("文档", top_k=10, filter={"source_type": "news"})
        assert len(results) == 1
        assert results[0]["metadata"]["source_type"] == "news"

    @pytest.mark.asyncio
    async def test_search_filter_no_match(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(checksum="c1")], "task-1")
        results = await client.search("Spring", filter={"task_id": "nonexistent"})
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_by_task(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(checksum="c1")], "task-1")
        await client.upsert([_make_doc(checksum="c2")], "task-2")
        deleted = await client.delete_by_task("task-1")
        assert deleted == 1
        results = await client.search("Spring", top_k=10, filter={"task_id": "task-1"})
        assert results == []
        results2 = await client.search("Spring", top_k=10, filter={"task_id": "task-2"})
        assert len(results2) == 1

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self):
        client = InMemoryRAGClient()
        deleted = await client.delete_by_task("no-such-task")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        client = InMemoryRAGClient()
        health = await client.health_check()
        assert health["status"] == "healthy"
        assert health["collection"] == "in-memory"
        assert health["vector_count"] == 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(checksum="c1")], "task-1")
        stats = await client.get_stats()
        assert stats["total_documents"] == 1
        assert stats["total_tasks"] == 1

    @pytest.mark.asyncio
    async def test_search_scoring_order(self):
        client = InMemoryRAGClient()
        await client.upsert(
            [_make_doc(content="Spring Boot 微服务开发指南", checksum="c1")],
            "task-1",
        )
        await client.upsert(
            [_make_doc(content="Python 数据分析入门", checksum="c2")],
            "task-1",
        )
        results = await client.search("Spring Boot 微服务", top_k=2)
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]

    @pytest.mark.asyncio
    async def test_metadata_excludes_content(self):
        client = InMemoryRAGClient()
        await client.upsert([_make_doc(checksum="c1")], "task-1")
        results = await client.search("Spring")
        assert "content" not in results[0]["metadata"]
        assert "task_id" in results[0]["metadata"]

    @pytest.mark.asyncio
    async def test_upsert_re_upsert_same_task_checksum(self):
        client = InMemoryRAGClient()
        doc = _make_doc(checksum="c1")
        await client.upsert([doc], "task-1")
        count = await client.upsert([doc], "task-1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_search_with_list_filter(self):
        client = InMemoryRAGClient()
        await client.upsert(
            [_make_doc(source_type=SourceCategory.NEWS, checksum="c1")],
            "task-1",
        )
        await client.upsert(
            [_make_doc(source_type=SourceCategory.OFFICIAL, checksum="c2")],
            "task-1",
        )
        results = await client.search("Spring", filter={"source_type": ["news", "official"]})
        assert len(results) == 2


# ---- StubRAGClient (backward compat) ----


class TestStubRAGClient:
    @pytest.mark.asyncio
    async def test_upsert_returns_count(self):
        client = StubRAGClient()
        count = await client.upsert([_make_doc()], "task-1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_search_returns_mock(self):
        client = StubRAGClient()
        results = await client.search("test query")
        assert len(results) == 1
        assert "模拟" in results[0]["content"]


# ---- Integration: Cleaner → InMemoryRAGClient ----


class TestCleanerRAGIntegration:
    @pytest.mark.asyncio
    async def test_cleaner_writes_to_rag(self):
        from src.intelligence.agents.cleaner import CleanerAgent
        from src.intelligence.models import RawDocument

        rag = InMemoryRAGClient()
        cleaner = CleanerAgent(rag)

        raw = [
            RawDocument(
                content=(
                    "Spring Boot 3.0 正式发布了全新版本，带来了多项重要新特性。"
                    "本次更新重点支持了虚拟线程技术，大幅提升了并发处理能力，"
                    "同时还增强了可观测性功能，为开发者提供了更好的监控和调试体验。"
                ),
                source_type=SourceCategory.NEWS,
                source_name="技术新闻",
            ),
        ]
        cleaned = await cleaner.clean(raw, "task-int-1")
        assert len(cleaned) == 1

        results = await rag.search("Spring Boot", top_k=5)
        assert len(results) == 1
        assert "Spring Boot" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_cleaner_dedup_before_rag(self):
        from src.intelligence.agents.cleaner import CleanerAgent
        from src.intelligence.models import RawDocument

        rag = InMemoryRAGClient()
        cleaner = CleanerAgent(rag)

        raw = [
            RawDocument(
                content=(
                    "这是重复的测试内容，用于验证清洗阶段的去重逻辑是否正常工作，"
                    "确保不会重复写入RAG知识库中。这段内容需要足够长才能通过质量检查。"
                ),
                source_type=SourceCategory.NEWS,
                source_name="A",
            ),
            RawDocument(
                content=(
                    "这是重复的测试内容，用于验证清洗阶段的去重逻辑是否正常工作，"
                    "确保不会重复写入RAG知识库中。这段内容需要足够长才能通过质量检查。"
                ),
                source_type=SourceCategory.NEWS,
                source_name="B",
            ),
        ]
        cleaned = await cleaner.clean(raw, "task-int-2")
        assert len(cleaned) == 1

        results = await rag.search("测试", top_k=10)
        assert len(results) == 1
