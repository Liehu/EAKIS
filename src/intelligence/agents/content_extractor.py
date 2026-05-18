"""内容提取 Agent — 从搜索结果 URL 抓取全文并智能提取正文。

插入在 CrawlerAgent 和 CleanerAgent 之间，负责：
  1. 从搜索结果中解析标题，按标题相似度去重（≥90% 相似视为转载）
  2. 仅对去重后的唯一 URL 抓取全文（节省带宽）
  3. 双模式提取：Fast (httpx+trafilatura) / CDP (Playwright+trafilatura)
  4. 失败容错：单 URL 失败保留原始 snippet
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from src.intelligence.anti_crawl.middleware import AntiCrawlMiddleware
from src.intelligence.config import ExtractionConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.content_extractor import (
    CDPPageExtractor,
    ExtractedContent,
    FastPageExtractor,
)
from src.intelligence.services.title_dedup import TitleDeduplicator
from src.shared.event_bus import EventBus
from src.shared.metrics import EXTRACTION_CDP_FALLBACK, EXTRACTION_COUNT, EXTRACTION_DURATION

logger = logging.getLogger("eakis.intelligence.content_extractor")

_DEFAULT_SKIP_PATTERNS = [
    r"baidu\.com/s\?",
    r"bing\.com/search",
    r"google\.com/search",
    r"sogou\.com/web",
    r"so\.com/s",
    r"\.(pdf|zip|rar|exe|jpg|png|gif|svg|mp4)$",
]

_DEFAULT_CDP_DOMAINS = [
    "mp.weixin.qq.com",
    "weibo.com",
    "x.com",
    "twitter.com",
]

# 匹配 snippet 格式："标题: xxx\n链接: xxx\n摘要: xxx"
_SNIPPET_TITLE_RE = re.compile(r"^标题[:\s]\s*(.+?)(?:\n|$)")


def _extract_title_from_snippet(content: str) -> str:
    """从搜索结果 snippet 中解析标题。

    CDP 爬虫返回格式: "标题: {title}\n链接: {url}\n摘要: {snippet}"
    """
    m = _SNIPPET_TITLE_RE.match(content)
    if m:
        return m.group(1).strip()
    # 尝试第一行作为标题
    first_line = content.split("\n")[0].strip()
    for prefix in ("标题: ", "标题:", "title: "):
        if first_line.lower().startswith(prefix):
            return first_line[len(prefix):].strip()
    return first_line if first_line else ""


class ContentExtractorAgent:
    """从搜索结果 URL 抓取并提取全文内容。"""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        anti_crawl: AntiCrawlMiddleware | None = None,
        cdp_enabled: bool = False,
    ) -> None:
        self.event_bus = event_bus
        self.anti_crawl = anti_crawl
        self.cdp_enabled = cdp_enabled
        self._fast = FastPageExtractor()
        self._cdp: CDPPageExtractor | None = None
        self._skip_patterns = [re.compile(p) for p in _DEFAULT_SKIP_PATTERNS]
        self._cdp_domains = set(_DEFAULT_CDP_DOMAINS)
        self._stats: dict[str, int] = {}

    async def extract(
        self,
        documents: list[RawDocument],
        config: ExtractionConfig | None = None,
    ) -> list[RawDocument]:
        """从搜索结果 URL 提取全文内容。

        流水线:
          1. 筛选候选文档（有 URL、非搜索引擎页、非资产引擎）
          2. 按标题相似度去重（先去重，避免重复爬取）
          3. 并发抓取去重后的 URL 全文
          4. 失败容错，保留原始 snippet

        Returns:
            增强后的 RawDocument 列表，content 字段为提取的正文。
        """
        config = config or ExtractionConfig()
        self._stats = {}

        if not config.enabled:
            logger.info("全文提取已禁用，跳过")
            return documents

        if self.anti_crawl and not self.anti_crawl._initialized:
            await self.anti_crawl.initialize()

        if config.skip_url_patterns:
            self._skip_patterns = [re.compile(p) for p in config.skip_url_patterns]
        if config.cdp_required_domains:
            self._cdp_domains = set(config.cdp_required_domains)

        # Step 1: 筛选候选文档
        candidates, passthrough = self._filter_candidates(documents)

        if not candidates:
            logger.info("没有需要提取全文的文档（%d 条直接透传）", len(passthrough))
            return documents

        # Step 2: 按标题相似度去重（爬取前，节省带宽）
        unique_candidates, title_dup_count = self._dedup_by_title(candidates, config)
        self._stats["title_dup_skipped"] = title_dup_count

        logger.info(
            "内容提取：%d 条候选，标题去重后 %d 条待提取，%d 条透传",
            len(candidates), len(unique_candidates), len(passthrough),
        )

        if not unique_candidates:
            return passthrough + candidates

        # Step 3: 并发抓取全文
        semaphore = asyncio.Semaphore(config.max_concurrent_extractions)
        tasks = [self._extract_single(doc, config, semaphore) for doc in unique_candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 4: 收集结果
        enriched: list[RawDocument] = []
        failures = 0
        for doc, result in zip(unique_candidates, results):
            if isinstance(result, Exception):
                logger.warning("提取失败 %s: %s", doc.source_url, result)
                enriched.append(doc)
                failures += 1
                EXTRACTION_COUNT.labels(method="fast", status="failed").inc()
            else:
                enriched.append(result)

        self._stats["total_candidates"] = len(candidates)
        self._stats["unique_to_extract"] = len(unique_candidates)
        self._stats["extracted"] = len(enriched) - failures
        self._stats["failed"] = failures
        self._stats["passthrough"] = len(passthrough)

        final_docs = passthrough + enriched

        if self.event_bus:
            await self.event_bus.publish("osint.extraction.complete", self._stats)

        logger.info(
            "内容提取完成：%d 条增强，%d 条标题去重（跳过爬取），%d 条失败，%d 条透传",
            len(enriched) - failures, title_dup_count, failures, len(passthrough),
        )

        return final_docs

    def _filter_candidates(
        self,
        documents: list[RawDocument],
    ) -> tuple[list[RawDocument], list[RawDocument]]:
        """筛选有 URL 且不是搜索引擎结果页的文档。"""
        candidates: list[RawDocument] = []
        passthrough: list[RawDocument] = []

        for doc in documents:
            url = doc.source_url

            if not url:
                passthrough.append(doc)
                continue

            if doc.source_type == SourceCategory.ASSET_ENGINE:
                passthrough.append(doc)
                continue

            if self._should_skip_url(url):
                passthrough.append(doc)
                continue

            candidates.append(doc)

        return candidates, passthrough

    def _dedup_by_title(
        self,
        documents: list[RawDocument],
        config: ExtractionConfig,
    ) -> tuple[list[RawDocument], int]:
        """按标题相似度去重（爬取前执行，节省带宽）。

        从每条文档的 content 中解析标题，使用 SequenceMatcher 比对。
        相似度 ≥ threshold 的视为同一篇新闻的转载，只保留第一条。
        """
        if not config.title_dedup_enabled:
            return documents, 0

        deduper = TitleDeduplicator(threshold=config.title_similarity_threshold)
        kept: list[RawDocument] = []
        dup_count = 0

        for doc in documents:
            title = _extract_title_from_snippet(doc.content)
            if not title:
                kept.append(doc)
                continue
            if deduper.is_duplicate(title):
                dup_count += 1
                logger.debug("标题去重跳过（不爬取）: %s", title[:60])
                continue
            deduper.add(title)
            kept.append(doc)

        return kept, dup_count

    def _should_skip_url(self, url: str) -> bool:
        for pattern in self._skip_patterns:
            if pattern.search(url):
                return True
        return False

    def _needs_cdp(self, url: str, config: ExtractionConfig) -> bool:
        if not config.auto_cdp_fallback:
            return False
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        for cdp_domain in self._cdp_domains:
            if cdp_domain in domain:
                return True
        return False

    async def _extract_single(
        self,
        doc: RawDocument,
        config: ExtractionConfig,
        semaphore: asyncio.Semaphore,
    ) -> RawDocument:
        """提取单个文档的全文内容。"""
        async with semaphore:
            url = doc.source_url
            if not url:
                return doc

            ctx = None
            try:
                headers = {}
                if self.anti_crawl:
                    ctx = await self.anti_crawl.before_request("content_extractor")
                    if ctx.headers:
                        headers = ctx.headers

                start = time.monotonic()
                extracted = await self._fast.extract(url, headers=headers)
                elapsed = time.monotonic() - start

                # CDP 降级
                needs_cdp = self._needs_cdp(url, config) and self.cdp_enabled
                content_failed = extracted.extraction_method == "failed" and config.auto_cdp_fallback and self.cdp_enabled
                if needs_cdp or content_failed:
                    EXTRACTION_CDP_FALLBACK.inc()
                    if not self._cdp:
                        self._cdp = CDPPageExtractor(
                            timeout=config.cdp_mode_timeout,
                            wait_for_content=config.cdp_wait_for_content,
                        )
                    extracted = await self._cdp.extract(url, headers=headers)
                    EXTRACTION_DURATION.labels(method="cdp").observe(time.monotonic() - start)
                else:
                    EXTRACTION_DURATION.labels(method="fast").observe(elapsed)

                if ctx:
                    await self.anti_crawl.after_request(ctx, success=bool(extracted.main_content))

                if extracted.main_content and len(extracted.main_content) >= config.min_content_length:
                    EXTRACTION_COUNT.labels(method=extracted.extraction_method, status="success").inc()
                    return RawDocument(
                        content=extracted.main_content,
                        source_type=doc.source_type,
                        source_name=extracted.title or doc.source_name,
                        source_url=url,
                        published_at=extracted.publish_date or doc.published_at,
                        metadata={
                            **doc.metadata,
                            "extraction_method": extracted.extraction_method,
                            "original_title": extracted.title,
                            "original_author": extracted.author,
                            "extraction_word_count": extracted.word_count,
                        },
                    )
                else:
                    EXTRACTION_COUNT.labels(method="fast", status="insufficient_content").inc()
                    return doc

            except Exception:
                if ctx:
                    await self.anti_crawl.after_request(ctx, success=False)
                raise

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def cleanup(self) -> None:
        self._cdp = None
