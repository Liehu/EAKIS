from __future__ import annotations

import logging
from typing import Any

from src.intelligence.agents.cleaner import CleanerAgent
from src.intelligence.agents.crawler import CrawlerAgent
from src.intelligence.agents.datasource import DataSourceAgent
from src.intelligence.agents.dsl import DSLAgent
from src.intelligence.config import IntelligenceConfig
from src.intelligence.models import (
    CleanedDocument,
    CollectionResult,
    CollectionStatus,
    DataSource,
    DslQuery,
    RawDocument,
    SourceCategory,
)
from src.intelligence.services.base import BaseLLMClient, BaseRAGClient, BaseScraper
from src.intelligence.services.llm_client import StubLLMClient
from src.intelligence.services.rag_client import StubRAGClient
from src.shared.event_bus import EventBus

logger = logging.getLogger("eakis.intelligence")


class IntelligenceModule:
    def __init__(
        self,
        config: IntelligenceConfig | None = None,
        llm_client: BaseLLMClient | None = None,
        rag_client: BaseRAGClient | None = None,
        event_bus: EventBus | None = None,
        scraper_overrides: dict[str, BaseScraper] | None = None,
    ) -> None:
        self.config = config or IntelligenceConfig()
        self.rag_client = rag_client or StubRAGClient()
        self.llm_client = llm_client or StubLLMClient()
        self.event_bus = event_bus or EventBus()

        self.datasource_agent = DataSourceAgent(self.rag_client)
        self.dsl_agent = DSLAgent(self.llm_client)
        self.crawler_agent = CrawlerAgent(event_bus=self.event_bus, scraper_overrides=scraper_overrides)
        self.cleaner_agent = CleanerAgent(self.rag_client)

        self._sources: list[DataSource] = []
        self._dsl_queries: list[DslQuery] = []
        self._raw_docs: list[RawDocument] = []
        self._cleaned_docs: list[CleanedDocument] = []
        self._status: CollectionStatus = CollectionStatus.PENDING

    async def run(
        self,
        task_id: str,
        company_name: str,
        industry: str | None = None,
        domains: list[str] | None = None,
        keywords: list[str] | None = None,
        enabled_categories: list[SourceCategory] | None = None,
    ) -> CollectionResult:
        self._status = CollectionStatus.RUNNING
        errors: list[str] = []

        try:
            self._sources = await self.datasource_agent.select_sources(
                company_name, industry, enabled_categories
            )
            logger.info("[%s] 数据源选择完成：%d 个", task_id, len(self._sources))

            if keywords:
                platforms = [s.name.lower() for s in self._sources if s.category == SourceCategory.ASSET_ENGINE]
                self._dsl_queries = await self.dsl_agent.generate(keywords, domains, platforms or None)
                logger.info("[%s] DSL生成完成：%d 条", task_id, len(self._dsl_queries))

            self._raw_docs = await self.crawler_agent.crawl(
                self._sources, self._dsl_queries, company_name, self.config.crawl
            )
            logger.info("[%s] 爬取完成：%d 条原始文档", task_id, len(self._raw_docs))

            self._cleaned_docs = await self.cleaner_agent.clean(
                self._raw_docs, task_id, self.config.clean
            )
            logger.info("[%s] 清洗完成：%d 条有效文档", task_id, len(self._cleaned_docs))

            failed = sum(1 for s in self._sources if s.error_message)
            self._status = CollectionStatus.PARTIAL_FAILURE if failed else CollectionStatus.COMPLETED

        except Exception as e:
            self._status = CollectionStatus.FAILED
            errors.append(str(e))
            logger.exception("[%s] 情报采集失败", task_id)

        return CollectionResult(
            task_id=task_id,
            status=self._status,
            total_sources=len(self._sources),
            total_documents=len(self._raw_docs),
            cleaned_documents=len(self._cleaned_docs),
            avg_quality_score=(
                sum(d.quality_score for d in self._cleaned_docs) / len(self._cleaned_docs)
                if self._cleaned_docs else 0.0
            ),
            errors=errors,
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "status": self._status.value,
            "sources": [
                {
                    "source_id": s.source_id,
                    "name": s.name,
                    "category": s.category.value,
                    "priority": s.priority,
                    "expected_yield": s.expected_yield,
                    "status": s.status.value if hasattr(s.status, "value") else s.status,
                    "items_crawled": s.items_crawled,
                    "error_message": s.error_message,
                }
                for s in self._sources
            ],
            "dsl_queries": [
                {"platform": q.platform, "query": q.query, "valid": q.syntax_valid}
                for q in self._dsl_queries
            ],
            "total_raw": len(self._raw_docs),
            "total_cleaned": len(self._cleaned_docs),
            "avg_quality": (
                sum(d.quality_score for d in self._cleaned_docs) / len(self._cleaned_docs)
                if self._cleaned_docs else 0.0
            ),
        }

    def get_documents(self, min_quality: float = 0.0, limit: int = 500) -> list[dict[str, Any]]:
        docs = [d for d in self._cleaned_docs if d.quality_score >= min_quality][:limit]
        return [
            {
                "source_type": d.source_type.value,
                "source_name": d.source_name,
                "source_url": d.source_url,
                "content": d.content,
                "quality_score": d.quality_score,
                "entities": d.entities,
                "checksum": d.checksum,
                "published_at": d.published_at.isoformat() if d.published_at else None,
            }
            for d in docs
        ]

    def get_dsl_queries(self) -> list[dict[str, Any]]:
        return [
            {"platform": q.platform, "query": q.query, "valid": q.syntax_valid}
            for q in self._dsl_queries
        ]

    def get_sources(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": s.source_id,
                "name": s.name,
                "category": s.category.value,
                "priority": s.priority,
                "expected_yield": s.expected_yield,
                "status": s.status.value if hasattr(s.status, "value") else s.status,
                "items_crawled": s.items_crawled,
                "error_message": s.error_message,
            }
            for s in self._sources
        ]
