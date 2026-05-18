"""CDP 爬虫与 DSL 生成器集成演示

展示如何使用 CDP 爬虫自动采集搜索引擎数据，
并且使用 DSL 生成器创建优化的搜索语法。
"""

import asyncio
import logging
from pathlib import Path

from src.core.config_paths import CRAWLER_YAML
from src.intelligence.agents.dsl_generator import UnifiedDSLGenerator, SearchContext
from src.intelligence.anti_crawl.ua_pool import AntiCrawlProfile
from src.intelligence.scrapers.cdp_scraper import CDPScraperManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_dsl_generation():
    """演示 DSL 生成器的功能"""
    logger.info("=== 演示 DSL 生成器 ===")

    # 初始化 DSL 生成器
    dsl_gen = UnifiedDSLGenerator()

    # 创建搜索上下文
    context = SearchContext(
        keywords=["XX支付", "Spring Boot"],
        domains=["xx-payment.com"],
        filters={"filetype": "pdf"}
    )

    # 生成多个搜索引擎的 DSL
    engines = ["baidu", "bing", "google"]
    queries = await dsl_gen.generate(
        context=context,
        engines=engines,
        use_llm=False
    )

    logger.info("生成的搜索语法：")
    for query in queries:
        logger.info(f"- {query.platform}: {query.query}")


async def demonstrate_cdp_crawler():
    """演示 CDP 爬虫的使用"""
    logger.info("\n=== 演示 CDP 爬虫 ===")

    # 检查 CDP 模式是否启用
    from src.intelligence.scrapers.cdp_scraper import load_crawler_config
    config = load_crawler_config()
    logger.info(f"CDP 模式启用状态: {config.enabled}")
    if not config.enabled:
        logger.warning("请在 config/crawler.yaml 中启用 cdp_mode")
        return

    # 创建 CDP 管理器
    anti_crawl = AntiCrawlProfile()
    cdp_manager = CDPScraperManager(anti_crawl=anti_crawl, config=config)

    # 获取百度爬虫
    baidu_scraper = cdp_manager.get_scraper("baidu")

    logger.info("准备执行 CDP 爬取...")
    logger.info("注意：实际爬取需要 Playwright 依赖，此处仅为演示代码结构")

    # 示例查询
    query = "XX支付"
    logger.info(f"查询示例：{query}")

    # 注释掉实际执行，因为需要在有 Playwright 的环境中运行
    # docs = await baidu_scraper.scrape(query)
    # logger.info(f"获取到 {len(docs)} 条结果")


async def main():
    """主演示函数"""
    logger.info("开始 CDP + DSL 集成演示...")

    # 演示 DSL 生成
    await demonstrate_dsl_generation()

    # 演示 CDP 爬虫
    await demonstrate_cdp_crawler()

    logger.info("\n演示完成！")
    logger.info("\n使用说明：")
    logger.info("1. 在 config/crawler.yaml 中启用 cdp_mode: true")
    logger.info("2. 安装 Playwright 依赖: pip install playwright")
    logger.info("3. 安装浏览器: playwright install chromium")
    logger.info("4. 运行爬虫任务")


if __name__ == "__main__":
    asyncio.run(main())