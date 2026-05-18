"""
DSL 生成 + 普通搜索引擎爬取集成测试

测试目标：
1. DSL 生成器生成针对"福建联通"的搜索查询
2. CDP 爬虫使用生成的 DSL 在百度/Bing 执行搜索
3. 验证结果提取和数据格式
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.intelligence.agents.dsl_generator import SearchContext, UnifiedDSLGenerator
from src.intelligence.models import DataSource, SourceCategory
from src.intelligence.scrapers.cdp_scraper import CDPScraper, load_crawler_config
from src.intelligence.anti_crawl.ua_pool import AntiCrawlProfile

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(project_root / "test_results" / f"dsl_crawler_test_{datetime.now():%Y%m%d_%H%M%S}.log")
    ]
)
logger = logging.getLogger("eakis.test.dsl_crawler")


class DSLCrawlerIntegrationTest:
    """DSL 生成器 + CDP 爬虫集成测试"""

    def __init__(self, enable_cdp: bool = False):
        self.enable_cdp = enable_cdp
        self.dsl_generator = None
        self.cdp_config = None
        self.anti_crawl = None

    async def setup(self):
        """初始化测试环境"""
        logger.info("=" * 60)
        logger.info("初始化测试环境")
        logger.info("=" * 60)

        # 1. 初始化 DSL 生成器
        self.dsl_generator = UnifiedDSLGenerator()
        logger.info(f"DSL 生成器初始化完成，支持引擎: {self.dsl_generator.get_supported_engines()}")

        # 2. 加载 CDP 配置
        self.cdp_config = load_crawler_config()
        logger.info(f"CDP 模式: {'启用' if self.cdp_config.enabled else '禁用'}")

        # 3. 初始化反爬伪装
        if self.cdp_config.enabled:
            self.anti_crawl = AntiCrawlProfile()
            logger.info("反爬伪装: 已初始化 UA 池")

    async def test_dsl_generation(self):
        """测试 DSL 生成"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 1: DSL 生成")
        logger.info("=" * 60)

        # 构建搜索上下文
        context = SearchContext(
            keywords=["福建联通", "打造", "发布", "招标", "系统", "平台"],
            company_name="福建联通",
            filters={
                "target_type": "招投标信息",
                "time_range": "近一年"
            }
        )

        # 指定目标引擎（普通搜索引擎）
        target_engines = ["baidu", "bing"]

        logger.info(f"搜索关键词: {', '.join(context.keywords)}")
        logger.info(f"企业名称: {context.company_name}")
        logger.info(f"目标引擎: {', '.join(target_engines)}")

        # 生成 DSL（不使用 LLM，使用模板）
        queries = await self.dsl_generator.generate(
            context=context,
            engines=target_engines,
            use_llm=False  # 使用模板生成，避免 LLM 调用
        )

        logger.info(f"\n生成 {len(queries)} 条 DSL 查询:")
        for q in queries:
            logger.info(f"  [{q.platform}] {q.query} (valid={q.syntax_valid})")

        return queries

    async def test_dsl_translation(self):
        """测试跨引擎 DSL 转换"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 2: DSL 跨引擎转换")
        logger.info("=" * 60)

        # 百度 DSL → Bing DSL
        baidu_dsl = 'site:lt.unionpay.com intitle:"招标" OR "采购"'
        translated = self.dsl_generator.translate_dsl(
            dsl=baidu_dsl,
            from_engine="baidu",
            to_engine="bing"
        )
        logger.info(f"百度 → Bing: {baidu_dsl}")
        logger.info(f"  转换结果: {translated}")

        # Bing DSL → 百度 DSL
        bing_dsl = 'site:example.com intitle:"后台" filetype:pdf'
        translated = self.dsl_generator.translate_dsl(
            dsl=bing_dsl,
            from_engine="bing",
            to_engine="baidu"
        )
        logger.info(f"\nBing → 百度: {bing_dsl}")
        logger.info(f"  转换结果: {translated}")

    async def test_crawler_execution(self, queries):
        """测试爬虫执行（需要 CDP 模式启用）"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 3: CDP 爬虫执行")
        logger.info("=" * 60)

        if not self.cdp_config.enabled:
            logger.warning("CDP 模式未启用，跳过实际爬取测试")
            logger.info("如需测试爬取，请在 config/crawler.yaml 中设置 cdp_mode.enabled=true")
            return []

        if not self.enable_cdp:
            logger.info("CDP 测试被禁用（设置 enable_cdp=True 以启用）")
            return []

        all_docs = []

        for query in queries:
            if query.platform not in ["baidu", "bing"]:
                logger.info(f"跳过非普通搜索引擎: {query.platform}")
                continue

            logger.info(f"\n执行 [{query.platform}] 搜索...")
            logger.info(f"  查询 DSL: {query.query}")

            try:
                scraper = CDPScraper(
                    engine_name=query.platform,
                    anti_crawl=self.anti_crawl,
                    config=self.cdp_config
                )

                docs = await scraper.scrape(query.query)
                logger.info(f"  获取 {len(docs)} 条结果")

                for i, doc in enumerate(docs[:3], 1):  # 只显示前3条
                    logger.info(f"    结果 {i}: {doc.source_url}")
                    if doc.content:
                        content_preview = doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
                        logger.info(f"      内容: {content_preview}")

                all_docs.extend(docs)

            except Exception as e:
                logger.error(f"  [{query.platform}] 爬取失败: {e}")

        return all_docs

    async def test_engine_specs(self):
        """测试引擎规格配置"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 4: 引擎规格配置")
        logger.info("=" * 60)

        specs = self.dsl_generator.specs

        for engine_name in ["baidu", "bing"]:
            spec = specs.get(engine_name)
            if spec:
                logger.info(f"\n引擎: {engine_name} ({spec.display_name})")
                logger.info(f"  类型: {self.dsl_generator.get_engine_type(engine_name)}")
                logger.info(f"  字段: {list(spec.fields.keys())}")
                logger.info(f"  操作符: {spec.operators}")
                logger.info(f"  查询参数: {spec.query_param}")
                logger.info(f"  编码方式: {spec.query_encoding}")

    async def save_results(self, queries, docs):
        """保存测试结果"""
        results_dir = project_root / "test_results"
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = results_dir / f"dsl_crawler_test_{timestamp}.json"

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dsl_queries": [
                {
                    "platform": q.platform,
                    "query": q.query,
                    "valid": q.syntax_valid
                }
                for q in queries
            ],
            "documents": [
                {
                    "source_type": doc.source_type,
                    "source_name": doc.source_name,
                    "source_url": doc.source_url,
                    "content_preview": doc.content[:200] if doc.content else "",
                    "published_at": doc.published_at.isoformat() if doc.published_at else None
                }
                for doc in docs[:10]  # 只保存前10条
            ],
            "summary": {
                "total_queries": len(queries),
                "total_docs": len(docs)
            }
        }

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n测试结果已保存到: {result_file}")


async def main():
    """主测试流程"""
    # 创建测试实例
    # 设置 enable_cdp=True 来启用实际爬取测试
    test = DSLCrawlerIntegrationTest(enable_cdp=True)

    try:
        # 初始化
        await test.setup()

        # 测试引擎规格
        await test.test_engine_specs()

        # 测试 DSL 生成
        queries = await test.test_dsl_generation()

        # 测试 DSL 转换
        await test.test_dsl_translation()

        # 测试爬虫执行
        docs = await test.test_crawler_execution(queries)

        # 保存结果
        await test.save_results(queries, docs)

        logger.info("\n" + "=" * 60)
        logger.info("测试完成")
        logger.info("=" * 60)

    finally:
        logger.info("清理资源...")


if __name__ == "__main__":
    asyncio.run(main())
