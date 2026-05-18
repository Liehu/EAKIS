#!/usr/bin/env python3
"""DSL 生成 + 通用搜索引擎查询 联动测试.

测试目标：以 "福建联通" 为主关键词，组合动作词（打造/发布/招标）+ 对象词（系统/平台），
验证 DSL 生成器对普通搜索引擎（百度/Bing/Google/搜狗）和资产搜索引擎（FOFA/Hunter）
的 DSL 输出质量，以及 CDP 爬虫的 URL 构建逻辑。

运行方式：
    # 仅测试 DSL 生成（不需要浏览器）
    python3 scripts/test_dsl_general_search.py

    # 测试 CDP URL 构建（不需要浏览器）
    python3 scripts/test_dsl_general_search.py --test-url

    # 完整测试含 CDP 爬取（需要 Playwright + Chromium）
    python3 scripts/test_dsl_general_search.py --cdp

    # 指定搜索引擎
    python3 scripts/test_dsl_general_search.py --engines baidu bing
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

sys.path.insert(0, ".")

from src.intelligence.agents.dsl_generator import (
    SearchContext,
    UnifiedDSLGenerator,
    EngineType,
)
from src.intelligence.engine_specs import load_engine_specs
from src.intelligence.models import DslQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test-dsl-general")

# =============================================================================
# 测试数据
# =============================================================================

TARGET = {
    "company_name": "福建联通",
    "domains": ["chinaunicom.com", "fj.chinaunicom.com"],
    "industry": "telecom",
}

ACTION_WORDS = ["打造", "发布", "招标"]
OBJECT_WORDS = ["系统", "平台"]


def build_search_contexts() -> list[SearchContext]:
    """构建多个搜索上下文，覆盖不同关键词组合。"""
    contexts = []

    for action in ACTION_WORDS:
        for obj in OBJECT_WORDS:
            contexts.append(
                SearchContext(
                    keywords=[f"福建联通 {action} {obj}"],
                    domains=TARGET["domains"],
                    company_name=TARGET["company_name"],
                    filters={"_scenario": f"{action}_{obj}"},
                )
            )

    contexts.append(
        SearchContext(
            keywords=["福建联通"],
            domains=TARGET["domains"],
            company_name=TARGET["company_name"],
        )
    )

    for action in ACTION_WORDS:
        contexts.append(
            SearchContext(
                keywords=[f"福建联通 {action}"],
                domains=TARGET["domains"],
                company_name=TARGET["company_name"],
            )
        )

    return contexts


# =============================================================================
# 测试 1: DSL 生成质量验证（资产引擎 + 普通搜索引擎）
# =============================================================================


async def test_dsl_generation() -> tuple[list[dict], float]:
    """测试 DSL 生成器对所有引擎的 DSL 生成质量。"""
    logger.info("=" * 70)
    logger.info("测试 1: DSL 生成质量验证")
    logger.info("=" * 70)

    generator = UnifiedDSLGenerator()
    contexts = build_search_contexts()

    all_engines = generator.get_supported_engines()
    asset_engines = generator.get_supported_engines(EngineType.ASSET)
    general_engines = generator.get_supported_engines(EngineType.GENERAL)

    logger.info(f"已加载引擎 ({len(all_engines)}): {all_engines}")
    logger.info(f"  资产引擎 ({len(asset_engines)}): {asset_engines}")
    logger.info(f"  普通搜索 ({len(general_engines)}): {general_engines}")

    total_queries = 0
    failed_queries = 0
    results = []

    for i, ctx in enumerate(contexts):
        scenario = ctx.filters.get("_scenario", "general") if ctx.filters else "general"
        logger.info(f"\n--- 上下文 {i + 1}/{len(contexts)}: {ctx.keywords} (场景: {scenario}) ---")

        # 资产引擎 DSL
        for engine in asset_engines:
            queries = await generator.generate(context=ctx, engines=[engine], use_llm=False)
            for q in queries:
                total_queries += 1
                valid = _validate_asset_dsl(engine, q)
                if not valid:
                    failed_queries += 1
                tag = "PASS" if valid else "FAIL"
                logger.info(f"  [{tag}] 资产-{engine}: {q.query}")
                results.append({
                    "context": ctx.keywords, "scenario": scenario,
                    "engine_type": "asset", "engine": engine,
                    "query": q.query, "valid": valid,
                })

        # 普通搜索引擎 DSL
        for engine in general_engines:
            queries = await generator.generate(context=ctx, engines=[engine], use_llm=False)
            for q in queries:
                total_queries += 1
                valid = _validate_general_dsl(engine, q)
                if not valid:
                    failed_queries += 1
                tag = "PASS" if valid else "FAIL"
                logger.info(f"  [{tag}] 搜索-{engine}: {q.query}")
                results.append({
                    "context": ctx.keywords, "scenario": scenario,
                    "engine_type": "general", "engine": engine,
                    "query": q.query, "valid": valid,
                })

    pass_rate = (total_queries - failed_queries) / max(total_queries, 1) * 100
    logger.info(f"\nDSL 生成汇总: {total_queries} 条查询, {failed_queries} 条失败, 通过率 {pass_rate:.1f}%")
    return results, pass_rate


def _validate_asset_dsl(engine: str, q: DslQuery) -> bool:
    if not q.query or len(q.query) < 3:
        return False
    specs = load_engine_specs()
    spec = specs.get(engine)
    if spec:
        has_field = any(f in q.query for f in spec.fields)
        has_operator = any(op in q.query for op in spec.operators if op not in ("(", ")") and len(op) > 1)
        if not (has_field or has_operator):
            logger.warning(f"    资产 {engine} DSL 缺少字段/操作符: {q.query}")
            return False
    if not any(kw in q.query for kw in ["福建联通", "联通", "unicom"]):
        logger.warning(f"    资产 {engine} DSL 缺少目标关键词: {q.query}")
        return False
    return True


def _validate_general_dsl(engine: str, q: DslQuery) -> bool:
    if not q.query or len(q.query) < 3:
        return False
    if not any(kw in q.query for kw in ["福建联通", "联通", "unicom"]):
        logger.warning(f"    搜索 {engine} DSL 缺少目标关键词: {q.query}")
        return False
    return True


# =============================================================================
# 测试 2: 跨引擎 DSL 转换
# =============================================================================


def test_dsl_translation() -> list[dict]:
    """测试资产引擎和普通搜索引擎之间的 DSL 转换。"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 2: 跨引擎 DSL 转换")
    logger.info("=" * 70)

    generator = UnifiedDSLGenerator()
    results = []

    test_cases = [
        # (源引擎, DSL, 目标引擎, 描述, 预期包含)
        ("fofa", 'title="福建联通" && body="平台"', "baidu", "资产→普通", ["intitle:", "福建联通", "平台"]),
        ("fofa", 'domain="chinaunicom.com" && title="后台"', "bing", "资产→普通", ["site:chinaunicom.com", "intitle:", "后台"]),
        ("fofa", 'title="福建联通" && org="联通"', "baidu", "资产→普通(保留未知字段)", ["intitle:", "福建联通"]),
        ("baidu", 'site:chinaunicom.com intitle:"福建联通 招标"', "fofa", "普通→资产", ['domain="chinaunicom.com"', 'title="福建联通 招标"']),
        ("bing", 'intitle:"福建联通 系统" site:fj.chinaunicom.com', "hunter", "普通→资产", ['title="福建联通 系统"', 'domain="fj.chinaunicom.com"']),
    ]

    for from_engine, dsl, to_engine, desc, expected_parts in test_cases:
        translated = generator.translate_dsl(dsl, from_engine, to_engine)
        valid = translated is not None and len(translated) >= 3
        # 验证预期部分
        if valid:
            for part in expected_parts:
                if part not in translated:
                    logger.warning(f"    转换结果缺少预期内容: {part}")
                    valid = False

        tag = "PASS" if valid else "FAIL"
        logger.info(f"  [{tag}] {desc}: {from_engine} → {to_engine}")
        logger.info(f"         原始: {dsl}")
        logger.info(f"         转换: {translated}")
        if not valid:
            logger.info(f"         预期包含: {expected_parts}")
        results.append({
            "description": desc, "from_engine": from_engine, "to_engine": to_engine,
            "original": dsl, "translated": translated, "valid": valid,
        })

    return results


# =============================================================================
# 测试 3: CDP URL 构建验证
# =============================================================================


def test_cdp_url_building() -> list[dict]:
    """测试 CDP 爬虫的搜索 URL 构建逻辑。"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 3: CDP URL 构建验证")
    logger.info("=" * 70)

    import yaml
    from src.core.config_paths import CRAWLER_YAML

    if not CRAWLER_YAML.exists():
        logger.error("CDP 配置文件不存在: %s", CRAWLER_YAML)
        return []

    with open(CRAWLER_YAML, "r", encoding="utf-8") as f:
        crawler_data = yaml.safe_load(f)

    cdp_engines = crawler_data.get("cdp_engines", {})
    logger.info(f"已配置 CDP 引擎: {list(cdp_engines.keys())}")

    generator = UnifiedDSLGenerator()
    specs = load_engine_specs()
    results = []

    test_queries = ["福建联通 打造 系统", "福建联通 招标 平台", "福建联通 发布 系统"]

    for engine_name, engine_cfg in cdp_engines.items():
        search_url = engine_cfg.get("search_url", "")
        query_param = engine_cfg.get("query_param", "q")
        has_spec = engine_name in specs
        logger.info(f"\n--- 引擎: {engine_name} (spec={'有' if has_spec else '无'}, URL: {search_url}) ---")

        for raw_query in test_queries:
            context = SearchContext(
                keywords=[raw_query],
                domains=TARGET["domains"],
                company_name=TARGET["company_name"],
            )

            dsl_results = generator._generate_via_template(context=context, engines=[engine_name])
            if dsl_results:
                dsl_query = dsl_results[0].query
            else:
                dsl_query = raw_query
                if not has_spec:
                    logger.info(f"  [WARN] {engine_name} 无引擎规格，DSL 降级为原始查询")

            params = {query_param: dsl_query}
            full_url = f"{search_url}?{urlencode(params)}"

            parsed = urlparse(full_url)
            query_params = parse_qs(parsed.query)

            url_valid = (
                parsed.scheme in ("http", "https")
                and parsed.netloc
                and query_param in query_params
            )

            # 额外验证：DSL 中应包含目标关键词
            dsl_has_target = any(kw in dsl_query for kw in ["福建联通", "联通"])

            tag = "PASS" if url_valid and dsl_has_target else "FAIL"
            logger.info(f"  [{tag}] 原始: {raw_query}")
            logger.info(f"         DSL:  {dsl_query}")
            logger.info(f"         URL:  {full_url[:120]}")

            results.append({
                "engine": engine_name, "raw_query": raw_query, "dsl_query": dsl_query,
                "full_url": full_url, "url_valid": url_valid, "dsl_has_target": dsl_has_target,
                "valid": url_valid and dsl_has_target,
            })

    return results


# =============================================================================
# 测试 4: Crawler 路由验证（无实际爬取）
# =============================================================================


def test_crawler_routing():
    """验证 CrawlerAgent 的爬虫路由逻辑。"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 4: Crawler 路由验证")
    logger.info("=" * 70)

    from src.intelligence.agents.crawler import _build_scraper_map
    from src.intelligence.models import DataSource, SourceCategory, DslQuery

    results = []

    # 非 CDP 模式
    scrapers_no_cdp = _build_scraper_map(cdp_mode=False, cdp_manager=None)
    logger.info(f"非 CDP 模式爬虫数: {len(scrapers_no_cdp)}")
    logger.info(f"  资产引擎爬虫: {[k for k in scrapers_no_cdp if k in ('fofa', 'hunter', 'quake', 'censys', 'shodan', 'zoomeye')]}")
    logger.info(f"  普通搜索爬虫: {[k for k in scrapers_no_cdp if k in ('baidu', 'bing', 'google')]}")

    # 验证普通搜索引擎在非 CDP 模式下没有专门的爬虫（应降级为 stub）
    for engine in ("baidu", "bing", "google"):
        has_scraper = engine in scrapers_no_cdp
        logger.info(f"  [{engine}] 非CDP模式有爬虫: {has_scraper}")
        results.append({"engine": engine, "cdp_mode": False, "has_scraper": has_scraper})

    # CDP 模式
    try:
        scrapers_cdp = _build_scraper_map(cdp_mode=True, cdp_manager=None)
        logger.info(f"\nCDP 模式爬虫数: {len(scrapers_cdp)}")
        for engine in ("baidu", "bing", "google"):
            has_scraper = engine in scrapers_cdp
            logger.info(f"  [{engine}] CDP模式有爬虫: {has_scraper}")
            results.append({"engine": engine, "cdp_mode": True, "has_scraper": has_scraper})
    except Exception as e:
        logger.warning(f"CDP 模式爬虫构建失败（可能缺少 Playwright）: {e}")
        results.append({"error": str(e), "cdp_mode": True})

    return results


# =============================================================================
# 测试 5: CDP 实际爬取（可选）
# =============================================================================


async def test_cdp_crawl():
    """使用 CDP 爬虫实际爬取百度（需要 Playwright + Chromium）。"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 5: CDP 实际爬取")
    logger.info("=" * 70)

    try:
        from src.intelligence.scrapers.cdp_scraper import CDPScraper, load_crawler_config
        from src.intelligence.config import CrawlConfig
    except ImportError as e:
        logger.error(f"CDP 爬虫模块导入失败: {e}")
        return []

    cdp_config = load_crawler_config()
    if not cdp_config.enabled:
        logger.warning("CDP 模式未启用，跳过实际爬取")
        return []

    results = []
    for query in ["福建联通 招标 平台"]:
        logger.info(f"\n--- CDP 爬取 [baidu]: {query} ---")
        try:
            scraper = CDPScraper(engine_name="baidu", config=cdp_config)
            docs = await scraper.scrape(query, CrawlConfig())
            logger.info(f"  获取 {len(docs)} 条结果")
            for j, doc in enumerate(docs[:5]):
                logger.info(f"  [{j + 1}] {doc.content[:100]}...")
            results.append({"query": query, "doc_count": len(docs),
                            "docs": [{"content": d.content[:200], "url": d.source_url} for d in docs[:5]]})
        except Exception as e:
            logger.error(f"  CDP 爬取失败: {e}")
            results.append({"query": query, "doc_count": 0, "error": str(e)})

    return results


# =============================================================================
# 主函数
# =============================================================================


def save_results(all_results: dict):
    output_dir = Path("./test_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"dsl_general_search_test_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"测试结果已保存: {output_file}")


async def run_all(args):
    all_results = {"target": TARGET, "timestamp": datetime.now().isoformat()}

    # 测试 1: DSL 生成
    dsl_results, pass_rate = await test_dsl_generation()
    all_results["dsl_generation"] = dsl_results
    all_results["dsl_pass_rate"] = pass_rate

    # 测试 2: 跨引擎转换
    translation_results = test_dsl_translation()
    all_results["dsl_translation"] = translation_results
    trans_pass = sum(1 for r in translation_results if r["valid"])
    trans_total = len(translation_results)

    # 测试 3: CDP URL 构建
    if args.test_url or args.cdp:
        url_results = test_cdp_url_building()
        all_results["cdp_url_building"] = url_results
        url_pass = sum(1 for r in url_results if r.get("valid"))
        url_total = len(url_results)
    else:
        url_pass = url_total = 0

    # 测试 4: Crawler 路由
    routing_results = test_crawler_routing()
    all_results["crawler_routing"] = routing_results

    # 测试 5: CDP 实际爬取
    if args.cdp:
        cdp_results = await test_cdp_crawl()
        all_results["cdp_crawl"] = cdp_results

    # 汇总
    logger.info("\n" + "=" * 70)
    logger.info("测试汇总")
    logger.info("=" * 70)
    logger.info(f"目标企业: {TARGET['company_name']}")
    logger.info(f"域名: {', '.join(TARGET['domains'])}")
    logger.info(f"关键词组合: {len(ACTION_WORDS)}x{len(OBJECT_WORDS)} = {len(ACTION_WORDS) * len(OBJECT_WORDS)} 组合")
    logger.info(f"DSL 生成: {pass_rate:.0f}% 通过")
    logger.info(f"跨引擎转换: {trans_pass}/{trans_total} 通过")
    if url_total:
        logger.info(f"CDP URL 构建: {url_pass}/{url_total} 通过")

    if args.save:
        save_results(all_results)

    if pass_rate < 80:
        logger.warning("DSL 生成通过率低于 80%")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="DSL + 通用搜索引擎联动测试")
    parser.add_argument("--cdp", action="store_true", help="启用 CDP 实际爬取")
    parser.add_argument("--test-url", action="store_true", help="测试 CDP URL 构建")
    parser.add_argument("--engines", nargs="+", help="指定测试引擎")
    parser.add_argument("--save", action="store_true", default=True, help="保存测试结果")
    args = parser.parse_args()

    return asyncio.run(run_all(args))


if __name__ == "__main__":
    sys.exit(main())
