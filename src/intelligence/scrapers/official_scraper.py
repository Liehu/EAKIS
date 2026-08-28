"""官网内容爬虫（真实抓取）。

query 为 URL 或裸域名时真实抓取首页（httpx 直抓，失败降级 CDP 浏览器渲染），
提取 <title> 与正文文本片段作为 OFFICIAL 情报；query 为企业名等非站点串时
返回空（官网 URL 由 task 层从 Company.website 传入 dsl）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.official")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
_TIMEOUT = 20.0
_MAX_TEXT = 4000  # 正文截断长度

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_STRIP_RE = re.compile(r"<[^>]+>")


def _normalize_target(query: str) -> str | None:
    q = query.strip()
    if not q or " " in q or "." not in q:
        return None
    if q.startswith(("http://", "https://")):
        return q
    if re.fullmatch(r"[\w.-]+\.[a-zA-Z]{2,}(/.*)?", q):
        return f"https://{q}"
    return None


def _extract(html: str) -> tuple[str, str]:
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = _STRIP_RE.sub("", title_m.group(1)).strip() if title_m else ""
    text = _TAG_RE.sub(" ", html)
    text = _STRIP_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return title, text[:_MAX_TEXT]


class OfficialScraper(BaseScraper):
    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        target = _normalize_target(query)
        if target is None:
            logger.info("官网抓取需要 URL/域名，跳过 query: %r", query[:50])
            return []

        html = await self._fetch_httpx(target)
        if html is None:
            html = await self._fetch_cdp(target, config)
        if not html:
            logger.warning("官网抓取失败：%s", target)
            return []

        title, text = _extract(html)
        if not text:
            return []
        host = re.sub(r"^https?://", "", target).split("/")[0]
        content = f"【官网】{host} — {title}\n{text}" if title else f"【官网】{host}\n{text}"
        return [RawDocument(
            content=content,
            source_type=SourceCategory.OFFICIAL,
            source_name=host,
            source_url=target,
            published_at=datetime.now(timezone.utc),
        )]

    async def _fetch_httpx(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True,
                                         headers=_HEADERS,
                                         verify=False) as client:
                resp = await client.get(url)
            if resp.status_code == 200 and "<html" in resp.text.lower():
                return resp.text
            logger.info("官网 httpx 抓取 %s → %s", url, resp.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.info("官网 httpx 抓取异常 %s: %s", url, exc)
        return None

    async def _fetch_cdp(self, url: str, config: CrawlConfig | None) -> str | None:
        """JS 渲染兜底：CDP 打开页面取 HTML。"""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, args=["--no-sandbox"])
                try:
                    page = await browser.new_page(user_agent=_HEADERS["User-Agent"])
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    return await page.content()
                finally:
                    await browser.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("官网 CDP 抓取异常 %s: %s", url, exc)
            return None
