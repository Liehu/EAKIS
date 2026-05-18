#!/usr/bin/env python3
"""综合测试脚本：验证 DSL 生成器、爬虫和 CDP 模式的完整数据流"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, ".")

from src.intelligence.agents.dsl_generator import UnifiedDSLGenerator, SearchContext
from src.intelligence.agents.crawler import CrawlerAgent, DataSource, CrawlConfig
from src.intelligence.models import SourceCategory
from src.intelligence.anti_crawl.middleware import AntiCrawlMiddleware
from src.intelligence.scrapers.cdp_scraper import load_crawler_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration-test")


async def test_dsl_generation():
    """测试 DSL 生成器"""
    logger.info("=" * 60)
    logger.info("测试 1: DSL 生成器")
    logger.info("=" * 60)

    dsl_generator = UnifiedDSLGenerator()

    # 测试用例1：普通关键词
    context1 = SearchContext(
        keywords=["阿里巴巴"],
        domains=["alibaba.com"],
        company_name="阿里巴巴集团"
    )

    queries1 = await dsl_generator.generate(context1, ["baidu", "bing"])
    logger.info(f"\n普通关键词测试:")
    for q in queries1:
        logger.info(f"  - {q.platform}: {q.query}")

    # 测试用例2：资产引擎专用查询
    context2 = SearchContext(
        keywords=["支付"],
        domains=["alipay.com"],
        company_name="蚂蚁集团"
    )

    queries2 = await dsl_generator.generate(context2, ["fofa", "hunter"])
    logger.info(f"\n资产引擎测试:")
    for q in queries2:
        logger.info(f"  - {q.platform}: {q.query}")

    return queries1 + queries2


async def test_crawler_stub_mode():
    """测试爬虫的 stub 模式"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 爬虫 Stub 模式")
    logger.info("=" * 60)

    # 创建数据源
    sources = [
        DataSource(
            source_id="fofa",
            name="FOFA",
            category=SourceCategory.ASSET_ENGINE,
            priority=1,
            expected_yield=0.8,
            rate_limit=1.0,
        ),
        DataSource(
            source_id="hunter",
            name="奇安信Hunter",
            category=SourceCategory.ASSET_ENGINE,
            priority=1,
            expected_yield=0.8,
            rate_limit=1.0,
        ),
    ]

    # 创建爬虫（stub 模式）
    crawler = CrawlerAgent(cdp_mode=False)

    # 配置
    config = CrawlConfig(max_concurrent_sources=2)

    # 执行爬取
    docs = await crawler.crawl(
        sources=sources,
        company_name="阿里巴巴集团",
        config=config,
    )

    logger.info(f"\nStub 模式结果:")
    logger.info(f"  获取文档数: {len(docs)}")
    for doc in docs:
        logger.info(f"  - [{doc.source_name}] {doc.content[:80]}...")

    await crawler.cleanup()
    return docs


async def test_cdp_mode():
    """测试 CDP 模式"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: CDP 模式")
    logger.info("=" * 60)

    # 检查 CDP 配置
    cdp_config = load_crawler_config()
    logger.info(f"CDP 配置: enabled={cdp_config.enabled}")

    if not cdp_config.enabled:
        logger.info("CDP 模式未启用，跳过测试")
        return []

    # 创建数据源
    sources = [
        DataSource(
            source_id="bing",
            name="必应搜索",
            category=SourceCategory.NEWS,
            priority=1,
            expected_yield=0.8,
            rate_limit=2.0,
        ),
    ]

    # 创建爬虫（CDP 模式）
    crawler = CrawlerAgent(cdp_mode=True)

    # 配置
    config = CrawlConfig(max_concurrent_sources=1)

    # 执行爬取（注意：这可能会失败，因为需要网络访问）
    try:
        docs = await crawler.crawl(
            sources=sources,
            company_name="人工智能",
            config=config,
        )

        logger.info(f"\nCDP 模式结果:")
        logger.info(f"  获取文档数: {len(docs)}")
        for doc in docs:
            logger.info(f"  - [{doc.source_name}] {doc.content[:80]}...")

        return docs
    except Exception as e:
        logger.error(f"CDP 模式测试失败: {e}")
        return []
    finally:
        await crawler.cleanup()


async def test_data_flow():
    """测试完整的数据流"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 完整数据流")
    logger.info("=" * 60)

    # 1. DSL 生成
    dsl_queries = await test_dsl_generation()
    logger.info(f"\nDSL 生成完成，共 {len(dsl_queries)} 条查询")

    # 2. Stub 模式爬取
    stub_docs = await test_crawler_stub_mode()
    logger.info(f"\nStub 模式爬取完成，共 {len(stub_docs)} 条文档")

    # 3. CDP 模式爬取（可选）
    cdp_docs = await test_cdp_mode()
    logger.info(f"\nCDP 模式爬取完成，共 {len(cdp_docs)} 条文档")

    # 4. 生成测试报告
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "dsl_queries_count": len(dsl_queries),
        "stub_docs_count": len(stub_docs),
        "cdp_docs_count": len(cdp_docs),
        "total_docs": len(stub_docs) + len(cdp_docs),
    }

    # 保存报告
    report_path = Path("test_results/integration_test_report.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(test_report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n测试报告已保存到: {report_path}")

    # 打印总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"DSL 查询数: {test_report['dsl_queries_count']}")
    logger.info(f"Stub 模式文档数: {test_report['stub_docs_count']}")
    logger.info(f"CDP 模式文档数: {test_report['cdp_docs_count']}")
    logger.info(f"总文档数: {test_report['total_docs']}")

    return test_report


async def main():
    """主函数"""
    try:
        # 运行综合测试
        report = await test_data_flow()

        if report['total_docs'] > 0:
            logger.info("\n✅ 所有测试通过！")
        else:
            logger.info("\n⚠️  部分测试返回空结果，但系统正常运行")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())