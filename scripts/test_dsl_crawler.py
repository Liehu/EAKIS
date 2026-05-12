#!/usr/bin/env python3
"""DSL + Crawler 联调测试脚本.

使用现有代码进行测试，无需额外业务代码。

配置方式：
1. 编辑 config/engines/engines.yaml，填写 API 密钥
   - fofa.api_key + fofa.email
   - hunter.api_key
   - quake.api_key

2. 运行测试

运行方式：
    # Stub 模式（默认）
    python scripts/test_dsl_crawler.py

    # 真实模式（需要配置 API Key）
    FOFA_API_KEY=your_key HUNTER_API_KEY=your_key python scripts/test_dsl_crawler.py --real
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, ".")

from src.intelligence.agents.crawler import CrawlerAgent
from src.intelligence.agents.dsl import DSLAgent
from src.intelligence.agents.datasource import DataSourceAgent
from src.intelligence.config import CrawlConfig, IntelligenceConfig
from src.intelligence.models import DataSource, SourceCategory
from src.intelligence.services.base import BaseLLMClient, BaseRAGClient, BaseScraper
from src.intelligence.services.llm_client import StubLLMClient
from src.intelligence.services.rag_client import StubRAGClient
from src.intelligence.services.generic_scraper import build_scraper_map
from src.core.config_paths import get_engine_specs

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dsl-crawler-test")

# 预设测试目标
PRESET_TARGETS = {
    "example": {
        "company_name": "Example Corporation",
        "domains": ["example.com", "example.org"],
        "keywords": ["example", "test", "demo"],
        "industry": "tech",
    },
    "alibaba": {
        "company_name": "阿里巴巴集团",
        "domains": ["alibaba.com", "aliyun.com", "taobao.com"],
        "keywords": ["阿里巴巴", "阿里云", "淘宝", "支付"],
        "industry": "ecommerce",
    },
    "tencent": {
        "company_name": "腾讯",
        "domains": ["tencent.com", "qq.com", "wechat.com"],
        "keywords": ["腾讯", "微信", "QQ", "支付"],
        "industry": "tech",
    },
}


class DSLCrawlerTester:
    def __init__(self, real_mode: bool = False):
        self.real_mode = real_mode
        self.results = {
            "dsl_queries": [],
            "crawled_docs": [],
            "errors": [],
        }

    def get_target(self, preset: str = "example") -> dict:
        """获取测试目标"""
        if preset in PRESET_TARGETS:
            return PRESET_TARGETS[preset]
        return PRESET_TARGETS["example"]

    async def test_dsl_generation(self, target: dict) -> list:
        """测试 DSL 生成"""
        logger.info("=" * 60)
        logger.info("步骤 1: DSL 查询生成")
        logger.info("=" * 60)

        llm_client = StubLLMClient()
        dsl_agent = DSLAgent(llm_client)

        keywords = target.get("keywords", [])
        domains = target.get("domains", [])

        # 根据模式选择平台
        engine_specs = get_engine_specs()
        if self.real_mode:
            # 真实模式：只使用已配置 API Key 的引擎
            platforms = [k for k, v in engine_specs.items()
                        if v.get("enabled") and v.get("api_key")]
            if not platforms:
                logger.warning("未配置任何有效的 API Key，降级为 stub 模式")
                platforms = ["fofa", "hunter", "quake"]
            logger.info(f"真实模式启用的平台: {', '.join(platforms)}")
        else:
            platforms = ["fofa", "hunter", "quake"]

        logger.info(f"目标平台: {', '.join(platforms)}")
        logger.info(f"关键词: {', '.join(keywords)}")
        logger.info(f"域名: {', '.join(domains)}")

        dsl_queries = await dsl_agent.generate(keywords, domains, platforms)

        logger.info(f"\n生成的 DSL 查询 ({len(dsl_queries)} 条):")
        for query in dsl_queries:
            logger.info(f"  [{query.platform}] {query.query}")
            self.results["dsl_queries"].append({
                "platform": query.platform,
                "query": query.query,
                "valid": query.syntax_valid,
            })

        return dsl_queries

    async def test_crawler(self, target: dict, dsl_queries: list) -> list:
        """测试爬虫"""
        logger.info("\n" + "=" * 60)
        logger.info("步骤 2: 资产爬取")
        logger.info("=" * 60)

        # 构建数据源
        sources = []
        for query in dsl_queries:
            sources.append(DataSource(
                source_id=query.platform,
                name=query.platform.upper(),
                category=SourceCategory.ASSET_ENGINE,
                priority=8,
                expected_yield=0.8,
                rate_limit=2.0,
            ))

        # 构建爬虫映射
        if self.real_mode:
            # 真实模式：使用带配置的爬虫
            scrapers = build_scraper_map()
            logger.info(f"使用真实爬虫，已配置的引擎: {', '.join(scrapers.keys())}")
        else:
            scrapers = None
            logger.info("使用 stub 爬虫")

        crawler = CrawlerAgent(scraper_overrides=scrapers)

        crawl_config = CrawlConfig(max_concurrent_sources=3)

        docs = await crawler.crawl(
            sources=sources,
            dsl_queries=dsl_queries,
            company_name=target.get("company_name", ""),
            config=crawl_config,
        )

        logger.info(f"\n爬取完成，共获取 {len(docs)} 条文档")

        # 统计各平台的文档数
        from collections import Counter
        source_counts = Counter(doc.source_name for doc in docs)
        for source, count in source_counts.items():
            logger.info(f"  [{source}] {count} 条")

        self.results["crawled_docs"] = [
            {
                "source": doc.source_name,
                "content": doc.content[:200],
                "url": doc.source_url,
            }
            for doc in docs
        ]

        return docs

    def save_results(self, target: dict):
        """保存测试结果"""
        output_dir = Path("./test_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"dsl_crawler_test_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "target": target,
                "mode": "real" if self.real_mode else "stub",
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"\n测试结果已保存到: {output_file}")

    def print_summary(self):
        """打印测试总结"""
        logger.info("\n" + "=" * 60)
        logger.info("测试总结")
        logger.info("=" * 60)
        logger.info(f"模式: {'真实 API' if self.real_mode else 'Stub'}")
        logger.info(f"DSL 查询数: {len(self.results['dsl_queries'])}")
        logger.info(f"爬取文档数: {len(self.results['crawled_docs'])}")
        logger.info(f"错误数: {len(self.results['errors'])}")

        if self.results["errors"]:
            logger.warning("\n错误列表:")
            for error in self.results["errors"]:
                logger.warning(f"  - {error}")


async def main():
    parser = argparse.ArgumentParser(description="DSL + Crawler 联调测试")
    parser.add_argument("--real", action="store_true", help="使用真实 API（需要配置 API Key）")
    parser.add_argument("--preset", default="example", choices=["example", "alibaba", "tencent"],
                       help="预设测试目标")
    parser.add_argument("--company", help="公司名称（覆盖预设）")
    parser.add_argument("--domains", nargs="+", help="域名列表")
    parser.add_argument("--keywords", nargs="+", help="关键词列表")

    args = parser.parse_args()

    tester = DSLCrawlerTester(real_mode=args.real)

    # 获取测试目标
    target = tester.get_target(args.preset)

    # 覆盖目标参数
    if args.company:
        target["company_name"] = args.company
    if args.domains:
        target["domains"] = args.domains
    if args.keywords:
        target["keywords"] = args.keywords

    logger.info(f"测试目标: {target['company_name']}")
    logger.info(f"域名: {', '.join(target['domains'])}")
    logger.info(f"关键词: {', '.join(target['keywords'])}")

    # 执行测试
    try:
        dsl_queries = await tester.test_dsl_generation(target)
        docs = await tester.test_crawler(target, dsl_queries)
        tester.print_summary()
        tester.save_results(target)

        logger.info("\n✓ 测试完成")

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
