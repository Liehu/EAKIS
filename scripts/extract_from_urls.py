"""
从预收集的 URL JSON 文件提取全文并调用 LLM 结构化提取。

用法: python3 scripts/extract_from_urls.py [--url-file FILE] [--output FILE]

输入 JSON 格式: {"公司名": [{"title": "...", "url": "..."}, ...]}
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

RESULTS_DIR = PROJECT_ROOT / "test_results"

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("url_extract")
logger.setLevel(logging.INFO)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9"}


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


def _playwright_extract(ssl_urls: list[tuple[str, str, str]]) -> dict[str, list[dict]]:
    """Playwright fallback for SSL-failed URLs."""
    from playwright.sync_api import sync_playwright
    results: dict[str, list[dict]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--ignore-certificate-errors"],
        )
        ctx = browser.new_context(
            locale="zh-CN", timezone_id="Asia/Chongqing", user_agent=_UA, ignore_https_errors=True,
        )
        page = ctx.new_page()
        for company, title, url in ssl_urls:
            try:
                page.goto(url, wait_until="commit", timeout=15000)
                actual_url = page.url
                content = _httpx_extract(actual_url)
                if not content:
                    page.goto(actual_url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    text = page.inner_text("body") or ""
                    content = re.sub(r"\s+", " ", text).strip()
                if content and len(content) >= 80:
                    if company not in results:
                        results[company] = []
                    results[company].append({
                        "title": title, "url": actual_url,
                        "content": content[:5000], "word_count": len(content),
                    })
            except Exception:
                pass
            time.sleep(0.5)
        browser.close()
    return results


def extract_all_content(company_urls: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Phase 1: httpx for all URLs; Phase 2: Playwright for failures."""
    all_docs: dict[str, list[dict]] = {}
    ssl_fail: list[tuple[str, str, str]] = []

    for company, urls in company_urls.items():
        docs = []
        for u in urls:
            url, title = u["url"], u["title"]
            content = _httpx_extract(url)
            if content and len(content) >= 80:
                docs.append({"title": title, "url": url, "content": content, "word_count": len(content)})
            else:
                ssl_fail.append((company, title, url))
        if docs:
            all_docs[company] = docs

    if ssl_fail:
        logger.info("  Playwright 降级处理 %d 条 URL", len(ssl_fail))
        pw_docs = _playwright_extract(ssl_fail)
        for company, docs in pw_docs.items():
            if company not in all_docs:
                all_docs[company] = []
            all_docs[company].extend(docs)

    for company, docs in all_docs.items():
        logger.info("  [最终] %s: %d 篇", company[:20], len(docs))

    return all_docs


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


def extract_all_companies(all_docs: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
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


def build_output(all_extractions: dict[str, list[dict]], company_docs: dict[str, list[dict]]) -> dict:
    success_count = 0
    company_summaries = []
    for company, extractions in all_extractions.items():
        ok = [e for e in extractions if e["status"] == "ok"]
        fail = [e for e in extractions if e["status"] != "ok"]
        success_count += len(ok)
        company_results = []
        for e in ok:
            ext = e["extraction"]
            # LLM may return a list instead of object; unwrap
            if isinstance(ext, list):
                for item in ext:
                    if isinstance(item, dict) and item.get("summary"):
                        company_results.append({"title": e["source_title"], "url": e["source_url"], **item})
                continue
            if ext:
                company_results.append({"title": e["source_title"], "url": e["source_url"], **ext})
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
    print(f"  批量企业资产提取结果（MCP搜索+提取）")
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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="从预收集URL提取企业资产")
    parser.add_argument("--url-file", type=str, default=str(RESULTS_DIR / "mcp_search_urls.json"), help="URL JSON文件")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    args = parser.parse_args()

    with open(args.url_file, "r", encoding="utf-8") as f:
        company_urls = json.load(f)

    print(f"\n{'='*70}")
    print(f"  URL提取 + LLM结构化 — {len(company_urls)} 家企业")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    print("[Step 1] httpx + trafilatura 提取全文...")
    all_docs = extract_all_content(company_urls)

    total_docs = sum(len(d) for d in all_docs.values())
    companies_with_docs = sum(1 for d in all_docs.values() if d)
    logger.info("提取完成，%d 家企业共 %d 篇文档", companies_with_docs, total_docs)

    if total_docs == 0:
        print("  未提取到任何文档。")
        return

    print(f"\n[Step 2] LLM 结构化提取（%d 篇文档）...", total_docs)
    all_extractions = extract_all_companies(all_docs)

    output = build_output(all_extractions, all_docs)
    print_summary(output)

    RESULTS_DIR.mkdir(exist_ok=True)
    if args.output:
        output_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"mcp_extract_{ts}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {output_path}")


if __name__ == "__main__":
    main()
