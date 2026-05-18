"""
福建联通 企业资产提取 — 逐篇摘要流水线

流程：
  1. 通过搜索引擎获取新闻链接（支持 --url-file 直接传入已知 URL）
  2. httpx + trafilatura 提取全文
  3. 逐篇调用 LLM 提取结构化资产情报（非聚合）
"""

from __future__ import annotations

import argparse
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

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b:free")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

COMPANY_NAME = "福建联通"

SEARCH_QUERIES = [
    f'"{COMPANY_NAME}" 打造 系统',
    f'"{COMPANY_NAME}" 打造 平台',
    f'"{COMPANY_NAME}" 发布 系统',
    f'"{COMPANY_NAME}" 发布 平台',
    f'"{COMPANY_NAME}" 招标 系统',
    f'"{COMPANY_NAME}" 招标 平台',
    f'"{COMPANY_NAME}" 上线 平台',
    f'"{COMPANY_NAME}" 中标 系统',
]

MAX_EXTRACT_URLS = 20
LLM_CONCURRENCY = 3

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("asset_extract")
logger.setLevel(logging.INFO)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# Step 1: 搜索（支持搜索引擎 + URL 文件两种模式）
# ---------------------------------------------------------------------------

def _parse_bing_results(html: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in re.finditer(r'<li[^>]*class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL):
        link_m = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', item.group(1), re.DOTALL)
        if not link_m:
            continue
        title = re.sub(r"<[^>]+>", "", link_m.group(2)).strip()
        if title and link_m.group(1):
            results.append({"title": title, "url": link_m.group(1), "engine": "bing"})
    return results


def _parse_baidu_results(html: str) -> list[dict[str, str]]:
    if "captcha" in html.lower()[:3000] or "verify" in html.lower()[:3000]:
        return []
    results: list[dict[str, str]] = []
    for m in re.finditer(
        r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL,
    ):
        link, raw_title = m.group(1), m.group(2)
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        if title and link and "baidu.com/link" not in link:
            results.append({"title": title, "url": link, "engine": "baidu"})
    return results


async def _search_engine(
    client: httpx.AsyncClient, engine: str, query: str
) -> list[dict[str, str]]:
    """单次搜索请求，返回解析后的结果。"""
    if engine == "bing":
        url = "https://cn.bing.com/search"
        params = {"q": query, "count": "10", "setlang": "zh-Hans"}
        parser = _parse_bing_results
    else:  # baidu
        url = "https://www.baidu.com/s"
        params = {"wd": query, "rn": "10"}
        parser = _parse_baidu_results

    try:
        resp = await client.get(url, params=params, headers=_HEADERS, follow_redirects=True)
        resp.raise_for_status()
        return parser(resp.text)
    except Exception as e:
        logger.warning("%s 搜索失败 [%s]: %s", engine, query, e)
        return []


async def search_all(queries: list[str]) -> list[dict[str, str]]:
    """多引擎搜索，自动降级。"""
    seen_urls: set[str] = set()
    all_results: list[dict[str, str]] = []
    engines = ["bing", "baidu"]
    engine_ok: dict[str, bool] = {}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for q in queries:
            for engine in engines:
                if engine_ok.get(engine) is False:
                    continue
                results = await _search_engine(client, engine, q)
                if not results and not engine_ok.get(engine):
                    # 首次失败再试一次
                    await asyncio.sleep(2)
                    results = await _search_engine(client, engine, q)
                    if not results:
                        engine_ok[engine] = False
                        logger.warning("%s 引擎已标记不可用", engine)
                        continue

                for item in results:
                    if item["url"] not in seen_urls:
                        seen_urls.add(item["url"])
                        all_results.append(item)
                        logger.info("  [%s] %s", item["engine"], item["title"][:60])
                if results:
                    break  # 当前关键词在某个引擎已有结果，跳下一个引擎
            await asyncio.sleep(1.5)

    logger.info("搜索完成，共 %d 条去重结果", len(all_results))
    return all_results


def load_url_file(path: str) -> list[dict[str, str]]:
    """从 JSON 或文本文件加载 URL 列表。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if p.suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = []
        # 兼容上次运行的 documents 格式
        for doc in data if isinstance(data, list) else data.get("documents", []):
            title = doc.get("title", doc.get("search_title", doc.get("extracted_title", "")))
            url = doc.get("url", doc.get("search_url", ""))
            if url:
                results.append({"title": title, "url": url, "engine": "url_file"})
        return results

    # 纯文本文件：每行一个 URL
    results = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and line.startswith("http"):
                results.append({"title": "", "url": line, "engine": "url_file"})
    return results


# ---------------------------------------------------------------------------
# Step 2: 全文提取
# ---------------------------------------------------------------------------

def _has_mojibake(text: str) -> bool:
    if not text:
        return False
    sample = text[:200]
    return sample.count('�') > 5


async def extract_content(url: str) -> tuple[str, str]:
    try:
        import trafilatura
        from readability import Document

        if "baidu.com/link" in url:
            return "", ""

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
            html = resp.text

        title = ""
        main_content = trafilatura.extract(html, url=url, include_tables=True, favor_precision=True)
        metadata = trafilatura.metadata.extract_metadata(html, default_url=url)
        if metadata and metadata.title:
            title = metadata.title

        if not main_content or len(main_content) < 80:
            doc = Document(html)
            main_content = re.sub(r"<[^>]+>", " ", doc.summary())
            main_content = re.sub(r"\s+", " ", main_content).strip()
            if not title:
                title = doc.title()

        content = main_content or ""
        if _has_mojibake(content):
            return "", ""

        return title, content
    except Exception as e:
        logger.warning("提取失败 %s: %s", url[:80], e)
        return "", ""


async def extract_all(search_results: list[dict[str, str]], max_urls: int = MAX_EXTRACT_URLS) -> list[dict[str, Any]]:
    candidates = [
        item for item in search_results[:max_urls]
        if "baidu.com/link" not in item["url"]
    ]
    if not candidates:
        logger.warning("无有效候选 URL（均已过滤）")
        return []

    logger.info("开始全文提取，%d 条候选", len(candidates))
    semaphore = asyncio.Semaphore(5)

    async def _one(item: dict) -> dict[str, Any] | None:
        async with semaphore:
            title, content = await extract_content(item["url"])
            if content and len(content) >= 100:
                return {
                    "title": title or item["title"],
                    "url": item["url"],
                    "engine": item["engine"],
                    "content": content,
                    "word_count": len(content),
                }
            return None

    results = await asyncio.gather(*[_one(item) for item in candidates])
    extracted = [r for r in results if r is not None]
    logger.info("全文提取完成，成功 %d / %d", len(extracted), len(candidates))
    return extracted


# ---------------------------------------------------------------------------
# Step 3: 逐篇 LLM 结构化提取
# ---------------------------------------------------------------------------

def load_prompt() -> tuple[str, str]:
    prompt_path = PROJECT_ROOT / "docs" / "prompts" / "asset_extraction_v1.yaml"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", ""), data.get("user", "")


async def call_llm(system_prompt: str, user_prompt: str) -> str:
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.05,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return re.sub(r"^```json?\s*|```\s*$", "", content.strip(), flags=re.MULTILINE).strip()


async def extract_one_article(
    doc: dict[str, Any],
    system_prompt: str,
    user_template: str,
    semaphore: asyncio.Semaphore,
    idx: int,
    total: int,
) -> dict[str, Any]:
    async with semaphore:
        user_prompt = user_template.format(
            company_name=COMPANY_NAME,
            title=doc["title"],
            content=doc["content"][:3000],
        )
        try:
            response = await call_llm(system_prompt, user_prompt)
            parsed = json.loads(response)
            logger.info("  [%d/%d] OK: %s", idx, total, doc["title"][:40])
            return {
                "source_url": doc["url"],
                "source_title": doc["title"],
                "extraction": parsed,
                "status": "ok",
            }
        except json.JSONDecodeError as e:
            logger.warning("  [%d/%d] JSON失败: %s", idx, total, doc["title"][:40])
            return {
                "source_url": doc["url"],
                "source_title": doc["title"],
                "raw_response": response,
                "status": "json_error",
                "error": str(e),
            }
        except Exception as e:
            logger.warning("  [%d/%d] 失败: %s → %s", idx, total, doc["title"][:40], e)
            return {
                "source_url": doc["url"],
                "source_title": doc["title"],
                "status": "llm_error",
                "error": str(e),
            }


async def extract_all_articles(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    system_prompt, user_template = load_prompt()
    semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
    total = len(documents)
    logger.info("开始逐篇 LLM 提取，共 %d 篇", total)

    start = time.monotonic()
    tasks = [
        extract_one_article(doc, system_prompt, user_template, semaphore, i + 1, total)
        for i, doc in enumerate(documents)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start

    ok = sum(1 for r in results if r["status"] == "ok")
    logger.info("提取完成，成功 %d / %d，耗时 %.1fs", ok, total, elapsed)
    return list(results)


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def print_results(extractions: list[dict[str, Any]]) -> None:
    success = [e for e in extractions if e["status"] == "ok"]
    failed = [e for e in extractions if e["status"] != "ok"]

    print(f"\n{'='*60}")
    print(f"  提取结果（成功 {len(success)} 篇，失败 {len(failed)} 篇）")
    print(f"{'='*60}")

    for i, item in enumerate(success, 1):
        ext = item["extraction"]
        if not ext:
            continue
        print(f"\n  {i}. {item['source_title'][:50]}")
        print(f"     日期: {ext.get('event_date', '?')}  |  类型: {ext.get('event_type', '?')}")
        print(f"     主单位: {ext.get('main_org', '?')}")
        partners = ext.get("partner_orgs", [])
        if partners:
            print(f"     协作方: {', '.join(partners)}")
        products = ext.get("products", [])
        if products:
            print(f"     产品/平台: {', '.join(products)}")
        tech = ext.get("tech_stack", [])
        if tech:
            print(f"     技术栈: {', '.join(tech)}")
        tags = ext.get("industry_tags", [])
        if tags:
            print(f"     行业: {', '.join(tags)}")
        summary = ext.get("summary", "")
        if summary:
            print(f"     摘要: {summary}")
        print(f"     来源: {item['source_url'][:80]}")

    if failed:
        print(f"\n  --- 失败 {len(failed)} 篇 ---")
        for item in failed:
            print(f"     - {item['source_title'][:50]} -> {item.get('error', item['status'])}")


def save_results(extractions: list[dict[str, Any]], search_results_count: int, extracted_count: int) -> Path:
    success = [e for e in extractions if e["status"] == "ok"]
    failed = [e for e in extractions if e["status"] != "ok"]

    output = {
        "company": COMPANY_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "search_results": search_results_count,
            "extracted_articles": extracted_count,
            "successful_extractions": len(success),
            "failed_extractions": len(failed),
        },
        "results": [
            {
                "title": item["source_title"],
                "url": item["source_url"],
                **item["extraction"],
            }
            for item in success
            if item["extraction"]
        ],
        "failures": [
            {
                "title": item["source_title"],
                "url": item["source_url"],
                "status": item["status"],
                "error": item.get("error"),
            }
            for item in failed
        ],
    }

    output_dir = PROJECT_ROOT / "test_results"
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"asset_extract_{ts}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="福建联通企业资产提取")
    parser.add_argument("--url-file", type=str, default=None,
                        help="从 JSON/文本文件加载已知 URL，跳过搜索引擎")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  福建联通 企业资产提取 — 逐篇摘要流水线")
    print(f"  模型: {OPENAI_MODEL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Step 1: 获取 URL 列表
    if args.url_file:
        print(f"[Step 1] 从文件加载 URL: {args.url_file}")
        search_results = load_url_file(args.url_file)
        print(f"  加载 {len(search_results)} 条 URL")
    else:
        print("[Step 1] 搜索引擎获取新闻链接...")
        search_results = await search_all(SEARCH_QUERIES)

    if not search_results:
        print("  未获取到任何链接。可使用 --url-file 指定已知 URL 文件。")
        return

    # Step 2: 全文提取
    print(f"\n[Step 2] 全文提取...")
    documents = await extract_all(search_results)
    if not documents:
        print("  未成功提取任何全文。")
        return

    print(f"  成功提取 {len(documents)} 篇")

    # Step 3: 逐篇 LLM 提取
    print(f"\n[Step 3] 逐篇 LLM 结构化提取...")
    extractions = await extract_all_articles(documents)

    print_results(extractions)

    output_path = save_results(extractions, len(search_results), len(documents))
    print(f"\n  结果已保存: {output_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
