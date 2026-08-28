"""新闻采集爬虫（真实数据源优先，stub 仅在显式配置时兜底）。

真实路径（按序尝试，任一成功即返回）：
  1. Bing 新闻 RSS（https://www.bing.com/news/search?q=...&format=RSS，免 key）
  2. CDP 浏览器爬虫（Playwright，走 crawler.yaml 的 baidu 引擎配置，对抗反爬）

全部失败时：settings.intelligence_use_stubs=True 则返回旧 stub 数据（开发模式），
否则返回空列表并记录降级——线上不产假数据。
"""

from __future__ import annotations

import logging
import random
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from src.core.settings import get_settings
from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.news")

_RSS_URL = "https://www.bing.com/news/search?q={query}&format=RSS"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml",
}
_TIMEOUT = 20.0
_MAX_ITEMS = 15

# 旧 stub 数据（仅 intelligence_use_stubs=True 时使用）
STUB_NEWS = [
    "XX科技有限公司近日完成新一轮融资，估值突破百亿",
    "XX科技发布全新支付系统，基于Spring Boot微服务架构",
    "XX科技获得多项技术专利，涉及分布式系统和数据安全",
    "XX科技与多家银行达成战略合作，拓展金融科技业务",
    "XX科技参与编写行业技术标准，推动规范化发展",
]


def _parse_rss(xml_text: str, query: str) -> list[RawDocument]:
    """解析 RSS 2.0（Bing News 格式）。解析失败返回空。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    docs: list[RawDocument] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not (title or desc):
            continue
        published = None
        if pub:
            try:
                published = parsedate_to_datetime(pub)
            except (TypeError, ValueError):
                published = None
        docs.append(RawDocument(
            content=f"【新闻】{title}\n{desc}".strip(),
            source_type=SourceCategory.NEWS,
            source_name="Bing News",
            source_url=link or _RSS_URL.format(query=query),
            published_at=published or datetime.now(timezone.utc),
        ))
        if len(docs) >= _MAX_ITEMS:
            break
    return docs


class NewsScraper(BaseScraper):
    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        query = query.strip()
        if not query:
            return []

        # 1) Bing News RSS（免 key、纯 HTTP）
        docs = await self._rss(query)
        if docs:
            return docs

        # 2) CDP 浏览器路径（Playwright）
        docs = await self._cdp(query, config)
        if docs:
            return docs

        # 3) 降级：仅开发 stub 模式返回假数据
        if get_settings().intelligence_use_stubs:
            logger.info("新闻采集全部失败，使用 stub 数据（query=%r）", query[:50])
            return self._stub(query)
        logger.warning("新闻采集失败且未启用 stub，返回空（query=%r）", query[:50])
        return []

    async def _rss(self, query: str) -> list[RawDocument]:
        url = _RSS_URL.format(query=urllib.parse.quote_plus(query))
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True,
                                         headers=_HEADERS) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                logger.info("Bing News RSS 返回 %s", resp.status_code)
                return []
            return _parse_rss(resp.text, query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bing News RSS 请求异常: %s", exc)
            return []

    async def _cdp(self, query: str, config: CrawlConfig | None) -> list[RawDocument]:
        try:
            from src.intelligence.scrapers.cdp_scraper import CDPScraper
            # bing 对无头浏览器较友好；baidu 常出安全验证页
            scraper = CDPScraper(engine_name="bing")
            docs = await scraper.scrape(query, config)
            if docs:
                logger.info("CDP 新闻采集 %d 条（query=%r）", len(docs), query[:50])
            return docs
        except Exception as exc:  # noqa: BLE001
            logger.warning("CDP 新闻采集异常: %s", exc)
            return []

    def _stub(self, query: str) -> list[RawDocument]:
        return [
            RawDocument(
                content=f"[新闻报道(stub)] {news} —— 关键词：{query}",
                source_type=SourceCategory.NEWS,
                source_name="百度新闻(stub)",
                source_url=f"https://news.example.com/{uuid.uuid4().hex[:8]}",
                published_at=datetime.now(timezone.utc),
            )
            for news in random.sample(STUB_NEWS, min(3, len(STUB_NEWS)))
        ]
