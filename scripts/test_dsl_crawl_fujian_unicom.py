#!/usr/bin/env python3
"""DSL 生成 + 通用搜索引擎爬取 联动测试

以 "福建联通" + ("打造"/"发布"/"招标") + ("系统"/"平台") 为主要关键词，
仅使用普通搜索引擎（必应为主，百度/搜狗为辅），不调用资产引擎。
输出前 50 条网页数据，格式为 JSON。

运行方式：
    python3 scripts/test_dsl_crawl_fujian_unicom.py
"""

import asyncio
import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, ".")

from src.intelligence.agents.dsl_generator import (
    SearchContext,
    UnifiedDSLGenerator,
    EngineType,
)
from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument
from src.intelligence.scrapers.cdp_scraper import CDPScraper, load_crawler_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test-fujian-unicom")

# =============================================================================
# 测试参数
# =============================================================================

TARGET = "福建联通"
DOMAINS = ["chinaunicom.com", "fj.chinaunicom.com"]
ACTION_WORDS = ["打造", "发布", "招标"]
OBJECT_WORDS = ["系统", "平台"]
MAX_RESULTS = 50
OUTPUT_DIR = Path("./test_results")


def build_queries() -> list[str]:
    """构建关键词组合查询列表。"""
    queries = []
    for action in ACTION_WORDS:
        for obj in OBJECT_WORDS:
            queries.append(f"{TARGET} {action} {obj}")
    return queries


# =============================================================================
# Step 1: DSL 生成（模板模式，不依赖 LLM）
# =============================================================================


def generate_dsls(generator: UnifiedDSLGenerator, queries: list[str]) -> dict[str, list[dict]]:
    """为每个查询生成 DSL。对普通搜索引擎，使用精确短语匹配更有效。"""
    target_engines = ["bing"]
    cdp_config = load_crawler_config()
    for extra in ("sogou", "so360", "baidu"):
        if extra in cdp_config.cdp_engines:
            target_engines.append(extra)

    logger.info(f"使用搜索引擎: {target_engines}")

    results = {e: [] for e in target_engines}

    for raw_query in queries:
        # 变体1：带域名限制的 DSL
        context_with_site = SearchContext(
            keywords=[raw_query],
            domains=DOMAINS,
            company_name=TARGET,
        )
        # 变体2：不带域名限制的 DSL
        context_no_site = SearchContext(
            keywords=[raw_query],
            company_name=TARGET,
        )

        for engine in target_engines:
            dsl_with_site = generator._generate_via_template(context=context_with_site, engines=[engine])
            dsl1 = dsl_with_site[0].query if dsl_with_site else raw_query

            dsl_no_site = generator._generate_via_template(context=context_no_site, engines=[engine])
            dsl2 = dsl_no_site[0].query if dsl_no_site else raw_query

            # 对普通搜索，精确短语 + 原始关键词组合通常效果更好
            # 所以额外生成一个直接使用原始关键词的变体
            dsl_direct = f'"{TARGET}" {raw_query.replace(TARGET, "").strip()}'

            results[engine].append({
                "raw_query": raw_query,
                "dsl": dsl_direct,  # 使用更精确的 DSL
                "dsl_template": dsl2,
                "dsl_with_site": dsl1,
            })
            logger.info(f"  [{engine}] {raw_query}")
            logger.info(f"    -> 精确: {dsl_direct}")
            logger.info(f"    -> 模板: {dsl2}")
            logger.info(f"    -> 站内: {dsl1}")

    return results


# =============================================================================
# Step 2: CDP 爬取（直接 Playwright，不依赖 CDPScraper 内部 DSL 二次生成）
# =============================================================================


async def _resolve_redirect(url: str, timeout: float = 5.0) -> str:
    """跟随 HTTP 重定向获取最终 URL。"""
    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            for _ in range(5):
                try:
                    resp = await client.head(url, allow_redirects=False)
                except Exception:
                    break
                if resp.status_code in (301, 302, 303, 307, 308):
                    url = str(resp.headers.get("location", url))
                else:
                    break
    except Exception:
        pass
    return url


async def crawl_bing(queries: list[dict], max_results: int) -> list[RawDocument]:
    """使用 Playwright 直接爬取 Bing 搜索结果，支持翻页。"""
    import base64 as b64mod
    from playwright.async_api import async_playwright

    docs: list[RawDocument] = []
    search_url = "https://cn.bing.com/search"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            locale="zh-CN",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        page.set_default_timeout(30000)

        for item in queries:
            if len(docs) >= max_results:
                break

            query = item["dsl"]
            logger.info(f"[bing] 爬取: {query}")

            # 每个查询翻 3 页以获取更多结果
            for page_num in range(3):
                if len(docs) >= max_results:
                    break

                try:
                    params = {"q": query}
                    if page_num > 0:
                        params["first"] = str(page_num * 10 + 1)
                    full_url = f"{search_url}?{urlencode(params)}"

                    resp = await page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                    if not resp or resp.status != 200:
                        continue

                    try:
                        await page.wait_for_selector("#b_results", timeout=8000)
                    except Exception:
                        title = await page.title()
                        if "验证" in title or "captcha" in title.lower():
                            logger.warning(f"[bing] 触发验证码")
                            await asyncio.sleep(5)
                        continue

                    results = await page.query_selector_all(".b_algo")
                    page_count = 0

                    for result in results:
                        if len(docs) >= max_results:
                            break
                        try:
                            h2 = await result.query_selector("h2")
                            title_text = await h2.inner_text() if h2 else ""
                            link = await result.query_selector("h2 a")
                            href = await link.get_attribute("href") if link else ""

                            # 解析 Bing 跳转链接 - 使用 cite 元素获取 display URL
                            display_url = ""
                            if "bing.com/ck/a" in href:
                                cite = await result.query_selector("cite")
                                if cite:
                                    cite_text = await cite.inner_text()
                                    # cite 格式: "https://domain.com › path › ..."
                                    display_url = cite_text.split("›")[0].split("…")[0].strip()
                                # 通过重定向解析真实 URL（后台批量处理）
                                real_url = await _resolve_redirect(href)
                                if real_url and "bing.com" not in real_url:
                                    href = real_url
                                elif display_url and display_url.startswith("http"):
                                    href = display_url
                            else:
                                display_url = href

                            caption = await result.query_selector(".b_caption p")
                            snippet = await caption.inner_text() if caption else ""

                            if title_text and href and href.startswith("http"):
                                docs.append(RawDocument(
                                    content=f"标题: {title_text}\n链接: {href}\n摘要: {snippet}",
                                    source_type=0,
                                    source_name="Bing",
                                    source_url=href,
                                    published_at=datetime.now(timezone.utc),
                                ))
                                page_count += 1
                        except Exception:
                            pass

                    logger.info(f"[bing] 第{page_num+1}页: +{page_count}条 (累计{len(docs)}条)")

                except Exception as e:
                    logger.error(f"[bing] 爬取失败: {e}")

            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()

    return docs


async def crawl_sogou(queries: list[dict], max_results: int) -> list[RawDocument]:
    """使用 Playwright 直接爬取搜狗搜索结果。"""
    import random
    from playwright.async_api import async_playwright

    docs: list[RawDocument] = []
    search_url = "https://www.sogou.com/web"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        page.set_default_timeout(30000)

        for item in queries:
            if len(docs) >= max_results:
                break

            query = item["dsl"]
            logger.info(f"[sogou] 爬取: {query}")

            try:
                full_url = f"{search_url}?{urlencode({'query': query})}"
                resp = await page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                if not resp or resp.status != 200:
                    logger.warning(f"[sogou] HTTP {resp.status if resp else 'None'}")
                    await asyncio.sleep(3)
                    continue

                try:
                    await page.wait_for_selector(".results", timeout=8000)
                except Exception:
                    title = await page.title()
                    logger.warning(f"[sogou] 等待结果超时 (title={title})")
                    continue

                results = await page.query_selector_all(".vrwrap")
                logger.info(f"[sogou] 找到 {len(results)} 条结果")

                for result in results:
                    if len(docs) >= max_results:
                        break
                    try:
                        h3 = await result.query_selector("h3 a")
                        title_text = await h3.inner_text() if h3 else ""
                        href = await h3.get_attribute("href") if h3 else ""
                        ft = await result.query_selector(".ft")
                        snippet = await ft.inner_text() if ft else ""

                        if title_text and href:
                            docs.append(RawDocument(
                                content=f"标题: {title_text}\n链接: {href}\n摘要: {snippet}",
                                source_type=0,
                                source_name="Sogou",
                                source_url=href,
                                published_at=datetime.now(timezone.utc),
                            ))
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"[sogou] 爬取失败: {e}")

            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()

    return docs


async def crawl_all(dsl_map: dict) -> list[RawDocument]:
    """串行爬取多个搜索引擎，汇总去重。"""
    import random
    all_docs: list[RawDocument] = []

    # Bing 优先（已验证可访问）
    if "bing" in dsl_map and dsl_map["bing"]:
        remaining = MAX_RESULTS - len(all_docs)
        if remaining > 0:
            logger.info(f"\n=== 开始爬取 Bing（目标 {remaining} 条）===")
            batch = await crawl_bing(dsl_map["bing"], remaining)
            logger.info(f"Bing 返回 {len(batch)} 条")
            all_docs.extend(batch)

    # Sogou 补充
    if "sogou" in dsl_map and dsl_map["sogou"] and len(all_docs) < MAX_RESULTS:
        remaining = MAX_RESULTS - len(all_docs)
        logger.info(f"\n=== 开始爬取 Sogou（目标 {remaining} 条）===")
        batch = await crawl_sogou(dsl_map["sogou"], remaining)
        logger.info(f"Sogou 返回 {len(batch)} 条")
        all_docs.extend(batch)

    return all_docs


# =============================================================================
# Step 3: 格式化输出
# =============================================================================


def format_results(docs: list[RawDocument]) -> list[dict]:
    """将 RawDocument 转换为输出 JSON 格式，按 URL 去重，过滤不相关结果。"""
    # 相关性关键词（标题中必须包含至少一个）
    # 优先高相关，也接受部分相关的通信行业信息
    relevance_keywords = [
        "联通", "unicom", "中国联通", "福建联通",
        "通信", "运营商", "电信", "移动",  # 行业相关
    ]

    output = []
    seen_urls = set()
    seen_titles = set()

    for doc in docs:
        url = doc.source_url or ""
        title = _extract_title(doc.content)

        # 过滤跳转链接
        if "bing.com/ck/a" in url:
            continue
        for prefix in ("http://www.baidu.com/link?url=", "https://www.baidu.com/link?url="):
            if url.startswith(prefix):
                continue

        # 基础过滤
        if not url.startswith("http"):
            continue

        # 相关性过滤：标题必须包含目标关键词
        if not any(kw in title for kw in relevance_keywords):
            continue

        # URL 去重
        if url in seen_urls:
            continue
        # 标题去重（避免同一文章不同 URL）
        if title in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title)

        output.append({
            "rank": len(output) + 1,
            "title": title,
            "url": url,
            "snippet": _extract_snippet(doc.content),
            "source_engine": doc.source_name,
            "collected_at": (doc.published_at or datetime.now(timezone.utc)).isoformat(),
        })

        if len(output) >= MAX_RESULTS:
            break

    return output


def _extract_title(content: str) -> str:
    for line in content.split("\n"):
        if line.startswith("标题:"):
            return line[3:].strip()
    return ""


def _extract_snippet(content: str) -> str:
    for line in content.split("\n"):
        if line.startswith("摘要:"):
            return line[3:].strip()
    return content[:200]


# =============================================================================
# 主函数
# =============================================================================


async def main():
    import random

    logger.info("=" * 60)
    logger.info("DSL 生成 + 通用搜索引擎爬取 联动测试")
    logger.info(f"目标: {TARGET}")
    logger.info(f"关键词组合: {ACTION_WORDS} x {OBJECT_WORDS}")
    logger.info(f"输出目标: 前 {MAX_RESULTS} 条")
    logger.info("=" * 60)

    # Step 1: DSL 生成
    logger.info("\n[Step 1] DSL 生成（模板模式，无需 LLM）...")
    generator = UnifiedDSLGenerator()
    queries = build_queries()
    logger.info(f"查询组合数: {len(queries)}")
    dsl_map = generate_dsls(generator, queries)

    # Step 2: CDP 爬取
    logger.info("\n[Step 2] 开始爬取...")
    docs = await crawl_all(dsl_map)
    logger.info(f"\n原始爬取结果: {len(docs)} 条")

    # Step 3: 格式化输出
    logger.info("\n[Step 3] 格式化去重...")
    results = format_results(docs)

    # 汇总信息
    summary = {
        "target": TARGET,
        "domains": DOMAINS,
        "action_words": ACTION_WORDS,
        "object_words": OBJECT_WORDS,
        "total_queries": len(queries),
        "total_raw_docs": len(docs),
        "total_unique_output": len(results),
        "engines_used": list(dsl_map.keys()),
        "dsl_generated": {
            engine: [
                {
                    "raw_query": q["raw_query"],
                    "dsl_broad": q["dsl"],
                    "dsl_site_scoped": q.get("dsl_with_site", ""),
                }
                for q in items
            ]
            for engine, items in dsl_map.items()
        },
    }

    # 输出到文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"fujian_unicom_crawl_{timestamp}.json"

    output_data = {
        "summary": summary,
        "results": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"结果已保存: {output_file}")
    logger.info(f"输出 {len(results)} 条去重后的网页数据")

    # 打印前 15 条预览
    logger.info("\n" + "=" * 60)
    logger.info(f"结果预览（共 {len(results)} 条，显示前 15 条）:")
    logger.info("=" * 60)
    for item in results[:15]:
        logger.info(f"  [{item['rank']:>2}] [{item['source_engine']}] {item['title']}")
        logger.info(f"       {item['url']}")

    if len(results) < MAX_RESULTS:
        logger.info(f"\n注意: 获取 {len(results)} 条，未达目标 {MAX_RESULTS} 条")

    return results


if __name__ == "__main__":
    asyncio.run(main())
