#!/usr/bin/env python3
"""CDP 模式测试脚本

测试普通搜索引擎的 CDP 爬虫功能
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.intelligence.agents.crawler import CrawlerAgent
from src.intelligence.config import CrawlConfig
from src.intelligence.models import DataSource, SourceCategory
from src.intelligence.anti_crawl.middleware import AntiCrawlMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cdp-test")


async def test_cdp_mode():
    """测试 CDP 模式"""
    logger.info("=" * 60)
    logger.info("CDP 模式测试")
    logger.info("=" * 60)

    # 创建数据源
    sources = [
        DataSource(
            source_id="baidu",
            name="百度搜索",
            category=SourceCategory.NEWS,
            priority=1,
            expected_yield=0.8,
            rate_limit=2.0,
        ),
        DataSource(
            source_id="bing",
            name="必应搜索",
            category=SourceCategory.NEWS,
            priority=1,
            expected_yield=0.8,
            rate_limit=2.0,
        ),
        DataSource(
            source_id="google",
            name="谷歌搜索",
            category=SourceCategory.NEWS,
            priority=2,
            expected_yield=0.8,
            rate_limit=2.0,
        ),
    ]

    # 创建爬虫（启用 CDP 模式）
    crawler = CrawlerAgent(cdp_mode=True)

    # 配置
    config = CrawlConfig(max_concurrent_sources=2)

    # 执行爬取
    logger.info("开始爬取...")
    docs = await crawler.crawl(
        sources=sources,
        company_name="人工智能",
        config=config,
    )

    # 输出结果
    logger.info(f"\n爬取完成，共获取 {len(docs)} 条文档")
    for doc in docs:
        logger.info(f"[{doc.source_name}] {doc.content[:100]}...")

    # 清理
    await crawler.cleanup()


if __name__ == "__main__":
    asyncio.run(test_cdp_mode())