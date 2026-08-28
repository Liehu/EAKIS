"""招投标公告爬虫（真实数据源：中国政府采购网 search.ccgp.gov.cn）。

检索 http://search.ccgp.gov.cn/bxsearch?searchtype=1&kw=<关键词>，
解析结果列表（标题/链接/发布时间）。ccgp 有访问频率限制：
遇到「频繁访问」页按指数退避重试，仍失败则降级返回空（不产假数据）。
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timezone

import httpx

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.bidding")

_SEARCH_URL = "http://search.ccgp.gov.cn/bxsearch"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "http://search.ccgp.gov.cn/",
}
_TIMEOUT = 20.0
_MAX_RESULTS = 20
_RETRY_ATTEMPTS = 3

# 结果条目：<a href="url"...>标题</a> ... <span class="vT-srch-result-info">*2026-08-01 12:00</span>
_ITEM_RE = re.compile(
    r'<a\s+href="(http://www\.ccgp\.gov\.cn/[^"]+)"[^>]*>(.*?)</a>'
    r'.*?<span\s+class="vT-srch-result-info">([^<]*)</span>',
    re.S,
)
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_TAG_RE = re.compile(r"<[^>]+>")


def _parse_date(text: str) -> datetime | None:
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_bidding_html(html: str, keyword: str = "") -> list[RawDocument]:
    """解析 ccgp 检索结果页 HTML → RawDocument 列表（独立函数便于单测）。"""
    items = _ITEM_RE.findall(html)
    docs = []
    for url, title_html, info in items[:_MAX_RESULTS]:
        title = _TAG_RE.sub("", title_html).strip()
        if not title:
            continue
        docs.append(RawDocument(
            content=f"【招投标公告】{title}（{info.strip()}）",
            source_type=SourceCategory.LEGAL,
            source_name="中国政府采购网",
            source_url=url,
            published_at=_parse_date(info),
            metadata={"bidding": True, "summary": info.strip()},
        ))
    return docs


async def search_bidding(keyword: str, page: int = 1) -> list[RawDocument]:
    """按关键词检索政府采购公告，返回 RawDocument 列表（含真实 URL）。"""
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True,
                                         headers=_HEADERS) as client:
                resp = await client.get(_SEARCH_URL, params={
                    "searchtype": "1", "kw": keyword, "page": str(page),
                })
            if resp.status_code != 200:
                logger.warning("ccgp 返回 %s（第 %d 次）", resp.status_code, attempt)
            elif "频繁访问" in resp.text:
                logger.warning("ccgp 触发频率限制（第 %d 次）", attempt)
            else:
                docs = parse_bidding_html(resp.text, keyword)
                logger.info("ccgp 检索 %r 返回 %d 条", keyword, len(docs))
                return docs
        except Exception as exc:  # noqa: BLE001
            logger.warning("ccgp 请求异常（第 %d 次）: %s", attempt, exc)

        # 指数退避 + 抖动
        await asyncio.sleep(min(30.0, 2 ** attempt + random.random()))

    logger.warning("ccgp 检索失败（重试 %d 次）：%r", _RETRY_ATTEMPTS, keyword)
    return []


class BiddingScraper(BaseScraper):
    """招投标公告爬虫：query 为企业名/项目关键词。"""

    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        keyword = query.strip()
        if not keyword:
            return []
        return await search_bidding(keyword)
