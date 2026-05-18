#!/usr/bin/env python3
"""全文内容提取端到端测试.

使用福建联通的搜索结果 URL，验证 trafilatura 正文提取效果。

运行方式：
    # 使用内置测试 URL
    python scripts/test_content_extraction.py

    # 指定搜索引擎结果 JSON 文件
    python scripts/test_content_extraction.py --input test_results/fujian_unicom_crawl_20260515_113341.json

    # 指定单个 URL
    python scripts/test_content_extraction.py --url https://fjca.miit.gov.cn/xwdt/xydt/art/2025/art_b8a7742d0f824d04849852c4fd199e00.html
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

from src.intelligence.agents.content_extractor import ContentExtractorAgent
from src.intelligence.config import ExtractionConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.content_extractor import FastPageExtractor
from src.intelligence.services.title_dedup import TitleDeduplicator, title_similarity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test-extraction")

SAMPLE_URLS = [
    "https://fjca.miit.gov.cn/xwdt/xydt/art/2025/art_b8a7742d0f824d04849852c4fd199e00.html",
    "https://fjca.miit.gov.cn/ztzl/cqdn/art/2022/art_213759f03eed45abb69a8258bfb2c957.html",
    "http://www.fj.xinhuanet.com/20250531/8b78d1bf6f6d45e0ae3e403886fcb77b/c.html",
    "http://iot.china.com.cn/content/2023-09/12/content_42517212.html",
    "https://www.thepaper.cn/newsDetail_forward_9503975",
    "https://fj.sina.cn/news/2025-04-21/detail-inetxncu5046871.d.html",
    "https://fj.sina.cn/news/2025-02-26/detail-inemuvpm8940850.d.html",
]


async def test_single_url(url: str, extractor: FastPageExtractor) -> dict:
    """测试单个 URL 的提取效果。"""
    start = time.monotonic()
    result = await extractor.extract(url)
    elapsed = time.monotonic() - start

    return {
        "url": url,
        "method": result.extraction_method,
        "title": result.title[:80] if result.title else "",
        "word_count": result.word_count,
        "content_preview": result.main_content[:200] if result.main_content else "",
        "elapsed_ms": round(elapsed * 1000),
        "needs_cdp": extractor.detect_needs_cdp(
            await extractor._fetch_html(url) if result.extraction_method == "failed" else ""
        ) if result.extraction_method == "failed" else False,
    }


async def test_title_dedup():
    """测试标题相似度去重。"""
    logger.info("=" * 60)
    logger.info("测试 1: 标题相似度去重")
    logger.info("=" * 60)

    dedup = TitleDeduplicator(threshold=0.9)

    titles = [
        "福建联通两大智·云数据中心启用 以更精的网络打造坚实底座",
        "福建联通两大智·云数据中心启用 以更精的网络打造坚实底座 ",
        "福建联通：擘画低空经济发展新图景",
        "以数为擎 打造福建工业互联网第一品牌",
    ]

    for title in titles:
        is_dup = dedup.is_duplicate(title)
        logger.info("  %s (%s)", title[:50], "重复" if is_dup else "新标题")
        if not is_dup:
            dedup.add(title)

    assert dedup.stats["seen_titles"] == 3, f"期望 3 个唯一标题，实际 {dedup.stats['seen_titles']}"
    logger.info("标题去重测试通过 ✓\n")


async def test_content_extraction(urls: list[str], max_urls: int = 5):
    """测试正文提取效果。"""
    logger.info("=" * 60)
    logger.info("测试 2: 正文内容提取（%d 条 URL）", min(len(urls), max_urls))
    logger.info("=" * 60)

    extractor = FastPageExtractor(timeout=20.0)
    results = []

    for url in urls[:max_urls]:
        logger.info("  提取中: %s", url[:80])
        result = await test_single_url(url, extractor)
        results.append(result)

        status = "✓" if result["word_count"] > 0 else "✗"
        logger.info(
            "  %s [%s] %d 字 | %.0fms | %s",
            status,
            result["method"],
            result["word_count"],
            result["elapsed_ms"],
            result["title"],
        )
        if result["content_preview"]:
            logger.info("    预览: %s...", result["content_preview"][:100])

    success = sum(1 for r in results if r["word_count"] > 0)
    logger.info("\n提取结果: %d/%d 成功", success, len(results))

    return results


async def test_pipeline_integration(input_json: str | None):
    """测试 ContentExtractorAgent 管线集成。"""
    logger.info("=" * 60)
    logger.info("测试 3: ContentExtractorAgent 管线集成")
    logger.info("=" * 60)

    if input_json:
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for item in data.get("results", [])[:5]:
            docs.append(RawDocument(
                content=f"标题: {item.get('title', '')}\n链接: {item.get('url', '')}\n摘要: {item.get('snippet', '')}",
                source_type=SourceCategory.NEWS,
                source_name=item.get("source_engine", "Test"),
                source_url=item.get("url"),
            ))
    else:
        docs = [
            RawDocument(
                content=f"标题: 新闻{i}\n链接: {url}\n摘要: ...",
                source_type=SourceCategory.NEWS,
                source_name="Test",
                source_url=url,
            )
            for i, url in enumerate(SAMPLE_URLS[:3])
        ]
        docs.append(RawDocument(
            content='{"domain":"example.com"}',
            source_type=SourceCategory.ASSET_ENGINE,
            source_name="Fofa",
            source_url=None,
        ))

    logger.info("输入: %d 条文档（%d 条有 URL）", len(docs), sum(1 for d in docs if d.source_url))

    agent = ContentExtractorAgent(cdp_enabled=False)
    config = ExtractionConfig(
        max_concurrent_extractions=3,
        min_content_length=50,
    )

    start = time.monotonic()
    result_docs = await agent.extract(docs, config)
    elapsed = time.monotonic() - start

    enriched = [d for d in result_docs if "extraction_method" in d.metadata]
    passthrough = [d for d in result_docs if "extraction_method" not in d.metadata]

    logger.info("耗时: %.1fs", elapsed)
    logger.info("结果: %d 条增强, %d 条透传", len(enriched), len(passthrough))

    for doc in enriched[:3]:
        wc = doc.metadata.get("extraction_word_count", 0)
        method = doc.metadata.get("extraction_method", "")
        logger.info("  [%s] %s 字 — %s", method, wc, doc.source_name)

    for doc in passthrough:
        logger.info("  [透传] %s — %s", doc.source_type.value, (doc.source_url or "无URL")[:60])

    logger.info("Agent 管线集成测试通过 ✓\n")
    return result_docs


async def main():
    parser = argparse.ArgumentParser(description="全文内容提取测试")
    parser.add_argument("--input", type=str, help="搜索结果 JSON 文件路径")
    parser.add_argument("--url", type=str, help="测试单个 URL")
    parser.add_argument("--max-urls", type=int, default=5, help="最大测试 URL 数")
    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        urls = [item["url"] for item in data.get("results", []) if item.get("url")]
    else:
        urls = SAMPLE_URLS

    await test_title_dedup()
    await test_content_extraction(urls, max_urls=args.max_urls)
    await test_pipeline_integration(args.input)

    logger.info("=" * 60)
    logger.info("全部测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
