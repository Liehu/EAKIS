"""
批量企业资产提取流水线

用法: python3 scripts/batch_asset_extract.py [--companies FILE] [--start N] [--count N]

流程:
  1. Playwright 搜索百度新闻链接
  2. 解析跳转获取真实 URL
  3. httpx + trafilatura 提取全文（SSL失败时降级 Playwright）
  4. 逐篇 LLM 结构化提取
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b:free")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

SEARCH_VERBS = ["打造", "发布", "招标"]
SEARCH_NOUNS = ["平台", "系统"]
MAX_URLS_PER_COMPANY = 8
LLM_CONCURRENCY = 3
RESULTS_DIR = PROJECT_ROOT / "test_results"

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("batch_extract")
logger.setLevel(logging.INFO)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9"}


# ---------------------------------------------------------------------------
# 默认企业列表
# ---------------------------------------------------------------------------

DEFAULT_COMPANIES = [
    "中广电移动网络有限公司福建分公司",
    "三明市数据集团有限公司",
    "福建省三明数字城服科技股份有限公司",
    "福建省大数据集团漳州有限公司",
    "国网福建省电力有限公司",
    "福建省配电售电有限责任公司",
    "福州亿力电力工程有限公司",
    "厦门电力工程集团有限公司",
    "福建省中禹水利水电工程有限公司",
    "福建沿海电力集团有限公司",
    "福建环三电力工程有限公司",
    "福建水利电力职业技术学院",
    "中闽能源股份有限公司",
    "福建省建筑轻纺设计院有限公司",
    "国网福建省电力有限公司厦门供电公司",
    "福建省宁德市东电发展有限公司",
    "厦门市政水务集团有限公司",
    "石狮市锦尚环境工程有限公司",
    "石狮市祥芝环境工程有限公司",
    "漳浦发展水务有限公司",
    "漳州市角美自来水有限公司",
    "福建水投集团闽清水务有限公司",
]


# ---------------------------------------------------------------------------
# Step 1: Playwright 搜索
# ---------------------------------------------------------------------------

def search_baidu_playwright(companies: list[str], start_idx: int = 0, count: int = 0) -> dict[str, list[dict]]:
    """用 Playwright 搜索百度，收集所有公司的新闻 URL。"""
    from playwright.sync_api import sync_playwright

    if count <= 0:
        count = len(companies)
    end_idx = min(start_idx + count, len(companies))
    subset = companies[start_idx:end_idx]

    results: dict[str, list[dict]] = {c: [] for c in subset}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--ignore-certificate-errors"],
        )
        ctx = browser.new_context(
            locale="zh-CN", timezone_id="Asia/Chongqing",
            user_agent=_UA, viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        for ci, company in enumerate(subset):
            queries = [f"{company} {v} {n}" for v in SEARCH_VERBS for n in SEARCH_NOUNS]
            company_urls: list[dict] = []
            seen_titles = set()

            # Anti-captcha: longer pause between companies
            if ci > 0:
                pause = 8 + (ci % 3) * 4  # 8s, 12s, 16s rotating
                logger.info("  等待 %ds 避免验证码...", pause)
                time.sleep(pause)

            for qi, q in enumerate(queries):
                try:
                    page.goto(f"https://www.baidu.com/s?wd={q}", wait_until="domcontentloaded", timeout=25000)
                    time.sleep(2)
                    html = page.content()

                    if "captcha" in html.lower()[:5000]:
                        time.sleep(3)
                        continue

                    links = page.query_selector_all("h3 a")
                    for link_el in links:
                        href = link_el.get_attribute("href") or ""
                        title = link_el.inner_text().strip()
                        if title and len(title) >= 8 and href not in [u["url"] for u in company_urls]:
                            company_urls.append({"title": title, "url": href, "engine": "baidu"})
                    time.sleep(1.5)
                except Exception as e:
                    logger.warning("搜索失败 [%s]: %s", company[:15], e)

            # Dedup by title similarity
            unique = []
            for u in company_urls:
                title = u["title"]
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique.append(u)

            results[company] = unique[:MAX_URLS_PER_COMPANY]
            logger.info("  [%d/%d] %s: %d 条 URL", start_idx + subset.index(company) + 1, end_idx, company[:20], len(results[company]))

        browser.close()
    return results


# ---------------------------------------------------------------------------
# Step 2: 解析跳转 URL + 提取全文
# ---------------------------------------------------------------------------

def resolve_and_extract(company_urls: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """解析跳转 URL 并提取全文。先用 httpx，SSL 失败时用 Playwright 降级。"""
    from playwright.sync_api import sync_playwright

    all_docs: dict[str, list[dict]] = {}
    ssl_fail_urls: list[tuple[str, str, str]] = []  # (company, title, url)

    # Phase 1: httpx 快速提取
    for company, urls in company_urls.items():
        docs = []
        for u in urls:
            url = u["url"]
            title = u["title"]
            # Skip redirect URLs that need browser resolution
            if "baidu.com/link" in url or "baidu.com/baidu.php" in url:
                ssl_fail_urls.append((company, title, url))
                continue
            content = _httpx_extract(url)
            if content and len(content) >= 80:
                docs.append({"title": title, "url": url, "content": content, "word_count": len(content)})
        if docs:
            all_docs[company] = docs
            logger.info("  [httpx] %s: %d/%d 篇", company[:20], len(docs), len(urls))

    if not ssl_fail_urls:
        return all_docs

    # Phase 2: Playwright 解析跳转 + SSL 降级
    logger.info("  Playwright 降级处理 %d 条 URL（百度跳转/SSL）", len(ssl_fail_urls))
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--ignore-certificate-errors"],
        )
        ctx = browser.new_context(
            locale="zh-CN", timezone_id="Asia/Chongqing", user_agent=_UA, ignore_https_errors=True,
        )
        page = ctx.new_page()

        for company, title, url in ssl_fail_urls:
            try:
                page.goto(url, wait_until="commit", timeout=15000)
                actual_url = page.url

                if "baidu.com" in actual_url:
                    # Still a redirect page, skip
                    continue

                # Now fetch the actual URL content via httpx
                content = _httpx_extract(actual_url)
                if not content:
                    # Last resort: extract directly from Playwright
                    page.goto(actual_url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    text = page.inner_text("body") or ""
                    content = re.sub(r"\s+", " ", text).strip()

                if content and len(content) >= 80:
                    h1 = page.query_selector("h1")
                    actual_title = h1.inner_text().strip() if h1 else title
                    if company not in all_docs:
                        all_docs[company] = []
                    all_docs[company].append({
                        "title": actual_title or title,
                        "url": actual_url,
                        "content": content[:5000],
                        "word_count": len(content),
                    })
            except Exception:
                pass
            time.sleep(0.5)

        browser.close()

    for company, docs in all_docs.items():
        logger.info("  [最终] %s: %d 篇", company[:20], len(docs))

    return all_docs


def _httpx_extract(url: str) -> str:
    try:
        import trafilatura
        from readability import Document
        with httpx.Client(timeout=15, follow_redirects=True, verify=False) as c:
            resp = c.get(url, headers=_HEADERS)
            resp.raise_for_status()
            html = resp.text
        main_content = trafilatura.extract(html, url=url, include_tables=True, favor_precision=True)
        if not main_content or len(main_content) < 80:
            doc = Document(html)
            main_content = re.sub(r"<[^>]+>", " ", doc.summary())
            main_content = re.sub(r"\s+", " ", main_content).strip()
        return main_content or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Step 3: LLM 提取
# ---------------------------------------------------------------------------

def load_prompt() -> tuple[str, str]:
    prompt_path = PROJECT_ROOT / "docs" / "prompts" / "asset_extraction_v1.yaml"
    with open(prompt_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", ""), data.get("user", "")


def call_llm_sync(system_prompt: str, user_prompt: str) -> str:
    async def _call():
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.05,
            "max_tokens": 2048,
        }
        async with httpx.AsyncClient(timeout=120) as c:
            resp = await c.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return re.sub(r"^```json?\s*|```\s*$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        return asyncio.get_event_loop().run_until_complete(_call())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_call())


def extract_all_companies(
    all_docs: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """对所有公司的所有文档逐篇调用 LLM。"""
    system_prompt, user_template = load_prompt()
    all_extractions: dict[str, list[dict]] = {}

    total_docs = sum(len(docs) for docs in all_docs.values())
    processed = 0

    for company, docs in all_docs.items():
        if not docs:
            continue
        extractions = []
        for doc in docs:
            processed += 1
            user_prompt = user_template.format(
                company_name=company,
                title=doc["title"],
                content=doc["content"][:3000],
            )
            try:
                response = call_llm_sync(system_prompt, user_prompt)
                parsed = json.loads(response)
                extractions.append({
                    "source_url": doc["url"],
                    "source_title": doc["title"],
                    "extraction": parsed,
                    "status": "ok",
                })
                logger.info("  [%d/%d] OK: %s -> %s", processed, total_docs, company[:15], doc["title"][:30])
            except json.JSONDecodeError as e:
                extractions.append({"source_url": doc["url"], "source_title": doc["title"], "status": "json_error", "error": str(e)})
                logger.warning("  [%d/%d] JSON失败: %s", processed, total_docs, company[:15])
            except Exception as e:
                extractions.append({"source_url": doc["url"], "source_title": doc["title"], "status": "error", "error": str(e)})
                logger.warning("  [%d/%d] 失败: %s -> %s", processed, total_docs, company[:15], str(e)[:60])

        all_extractions[company] = extractions

    return all_extractions


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def build_output(all_extractions: dict[str, list[dict]], company_docs: dict[str, list[dict]]) -> dict:
    success_count = 0
    result_list = []
    company_summaries = []

    for company, extractions in all_extractions.items():
        ok = [e for e in extractions if e["status"] == "ok"]
        fail = [e for e in extractions if e["status"] != "ok"]
        success_count += len(ok)

        company_results = []
        for e in ok:
            ext = e["extraction"]
            if ext:
                company_results.append({
                    "title": e["source_title"],
                    "url": e["source_url"],
                    **ext,
                })

        company_summaries.append({
            "company": company,
            "articles_extracted": len(company_docs.get(company, [])),
            "successful": len(ok),
            "failed": len(fail),
            "results": company_results,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_companies": len(all_extractions),
        "total_articles": success_count,
        "companies": company_summaries,
    }


def print_summary(output: dict) -> None:
    print(f"\n{'='*70}")
    print(f"  批量企业资产提取结果")
    print(f"  涉及 {output['total_companies']} 家企业，共 {output['total_articles']} 篇有效提取")
    print(f"{'='*70}")

    for cs in output["companies"]:
        print(f"\n  【{cs['company']}】成功 {cs['successful']} 篇")
        for i, r in enumerate(cs["results"], 1):
            summary = r.get("summary", "")
            print(f"    {i}. {summary}")
            print(f"       类型: {r.get('event_type', '?')} | 主单位: {r.get('main_org', '?')}")
            products = r.get("products", [])
            if products:
                print(f"       产品: {', '.join(products[:5])}")
            partners = r.get("partner_orgs", [])
            if partners:
                print(f"       协作: {', '.join(partners[:5])}")
            print(f"       来源: {r.get('url', '?')[:80]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="批量企业资产提取")
    parser.add_argument("--companies", type=str, default=None, help="企业列表 JSON 文件（每行一个公司名）")
    parser.add_argument("--start", type=int, default=0, help="从第 N 个企业开始")
    parser.add_argument("--count", type=int, default=0, help="处理 N 个企业（0=全部）")
    args = parser.parse_args()

    if args.companies:
        with open(args.companies, "r", encoding="utf-8") as f:
            companies = [line.strip() for line in f if line.strip()]
    else:
        companies = DEFAULT_COMPANIES

    start = args.start
    count = args.count if args.count > 0 else len(companies)
    end = min(start + count, len(companies))
    subset = companies[start:end]

    print(f"\n{'='*70}")
    print(f"  批量企业资产提取 — {len(subset)} 家企业")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # Step 1: 搜索
    print("[Step 1] Playwright 搜索百度新闻...")
    company_urls = search_baidu_playwright(companies, start, count)

    total_urls = sum(len(u) for u in company_urls.values())
    logger.info("搜索完成，共 %d 条 URL", total_urls)

    # Step 2: 提取全文
    print(f"\n[Step 2] 提取全文...")
    all_docs = resolve_and_extract(company_urls)

    total_docs = sum(len(d) for d in all_docs.values())
    companies_with_docs = sum(1 for d in all_docs.values() if d)
    logger.info("提取完成，%d 家企业共 %d 篇文档", companies_with_docs, total_docs)

    if total_docs == 0:
        print("  未提取到任何文档。")
        return

    # Step 3: LLM 提取
    print(f"\n[Step 3] LLM 结构化提取（%d 篇文档）...", total_docs)
    all_extractions = extract_all_companies(all_docs)

    # Build output
    output = build_output(all_extractions, all_docs)
    print_summary(output)

    # Save
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"batch_extract_{start}-{end-1}_{ts}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  结果已保存: {output_path}")


if __name__ == "__main__":
    main()
