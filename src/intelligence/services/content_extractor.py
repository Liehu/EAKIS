"""内容提取服务 — trafilatura 智能正文提取。

两种提取后端：
  - FastPageExtractor: httpx HTTP + trafilatura 正文解析（静态页面首选）
  - CDPPageExtractor: Playwright 渲染 + trafilatura 正文解析（JS 重页面降级）

提取策略类似 Firefox Reader Mode / Notion Web Clipper：
  去除导航栏、侧边栏、广告、页脚等噪音，只保留主要文章内容。
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger("eakis.intelligence.content_extractor")

_SPA_MARKERS = [
    'ng-app', 'ng-version', 'data-reactroot', 'data-react-helmet',
    'id="root"', 'id="app"', '__NEXT_DATA__', 'window.__NUXT__',
    'vue-app', 'data-v-', 'data-page-component',
]


@dataclass
class ExtractedContent:
    """页面内容提取结果。"""
    title: str = ""
    author: str = ""
    publish_date: datetime | None = None
    main_content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    extraction_method: str = ""
    url: str = ""
    word_count: int = 0  # 中文字符 + 英文词数


class BaseExtractor(ABC):

    @abstractmethod
    async def extract(self, url: str, headers: dict[str, str] | None = None) -> ExtractedContent:
        ...


def _count_words(text: str) -> int:
    """统计文本字数（中文按字符计，英文按空格分词计）。"""
    import re
    cn_chars = len(re.findall(r"[一-鿿㐀-䶿]", text))
    en_words = len(re.findall(r"[a-zA-Z]+", text))
    return cn_chars + en_words


class FastPageExtractor(BaseExtractor):
    """快速提取：httpx 请求 + trafilatura 解析。

    适用于绝大多数静态 HTML 页面。trafilatura 输出为空时自动降级到 readability-lxml。
    """

    def __init__(
        self,
        timeout: float = 15.0,
        max_content_length: int = 5_000_000,
    ) -> None:
        self.timeout = timeout
        self.max_content_length = max_content_length

    async def extract(self, url: str, headers: dict[str, str] | None = None) -> ExtractedContent:
        try:
            html = await self._fetch_html(url, headers)
            if not html:
                return ExtractedContent(extraction_method="failed", url=url)

            result = self._parse_with_trafilatura(html, url)
            if not result.main_content or len(result.main_content) < 50:
                logger.debug("trafilatura 提取内容过少，降级到 readability-lxml: %s", url)
                result = self._parse_with_readability(html, url)

            return result
        except Exception as e:
            logger.warning("快速提取失败 %s: %s", url, e)
            return ExtractedContent(extraction_method="failed", url=url)

    async def _fetch_html(self, url: str, headers: dict[str, str] | None = None) -> str:
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if headers:
            default_headers.update(headers)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10),
        ) as client:
            resp = await client.get(url, headers=default_headers)
            resp.raise_for_status()

            content_length = int(resp.headers.get("content-length", 0))
            if content_length > self.max_content_length:
                logger.warning("页面内容过大 (%d bytes)，跳过: %s", content_length, url)
                return ""

            return resp.text

    def _parse_with_trafilatura(self, html: str, url: str) -> ExtractedContent:
        import trafilatura

        main_content = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            include_formatting=False,
        )

        metadata = trafilatura.metadata.extract_metadata(html, default_url=url)

        publish_date = None
        if metadata and metadata.date:
            try:
                from dateutil import parser as date_parser
                publish_date = date_parser.parse(metadata.date)
            except Exception:
                pass

        return ExtractedContent(
            title=metadata.title if metadata else "",
            author=metadata.author if metadata else "",
            publish_date=publish_date,
            main_content=main_content or "",
            metadata={
                "hostname": metadata.sitename if metadata else "",
                "description": metadata.description if metadata else "",
            },
            extraction_method="trafilatura",
            url=url,
            word_count=_count_words(main_content) if main_content else 0,
        )

    def _parse_with_readability(self, html: str, url: str) -> ExtractedContent:
        from readability import Document

        doc = Document(html)
        summary_html = doc.summary()
        main_content = re.sub(r"<[^>]+>", " ", summary_html)
        main_content = re.sub(r"\s+", " ", main_content).strip()

        return ExtractedContent(
            title=doc.title(),
            main_content=main_content,
            extraction_method="readability",
            url=url,
            word_count=_count_words(main_content) if main_content else 0,
        )

    def detect_needs_cdp(self, html: str) -> bool:
        """启发式检测：判断页面是否需要 JS 渲染。"""
        for marker in _SPA_MARKERS:
            if marker in html:
                return True

        head_match = re.search(r"<head[^>]*>(.*?)</head>", html, re.DOTALL | re.IGNORECASE)
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)

        if head_match and body_match:
            head_len = len(head_match.group(1))
            body_text = re.sub(r"<[^>]+>", "", body_match.group(1)).strip()
            body_len = len(body_text)
            if head_len > 5000 and body_len < 200:
                return True

        return False


class CDPPageExtractor(BaseExtractor):
    """CDP 提取：Playwright 渲染 + trafilatura 解析。

    用于 JS 重度渲染的页面（微信公众号、SPA 应用等）。
    支持复用已有的 CDPScraperManager 资源池。
    """

    def __init__(
        self,
        timeout: float = 30.0,
        wait_for_content: float = 2.0,
        headless: bool = True,
    ) -> None:
        self.timeout = timeout
        self.wait_for_content = wait_for_content
        self.headless = headless
        self._fast = FastPageExtractor(timeout=timeout)

    async def extract(self, url: str, headers: dict[str, str] | None = None) -> ExtractedContent:
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )

                context_kwargs: dict[str, Any] = {
                    "locale": "zh-CN",
                    "timezone_id": "Asia/Shanghai",
                }
                if headers and "User-Agent" in headers:
                    context_kwargs["user_agent"] = headers["User-Agent"]

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    await page.wait_for_timeout(int(self.wait_for_content * 1000))

                    html = await page.content()
                    result = self._fast._parse_with_trafilatura(html, url)

                    if not result.main_content or len(result.main_content) < 50:
                        result = self._fast._parse_with_readability(html, url)

                    result.extraction_method = "cdp_trafilatura" if result.main_content else "cdp_failed"
                    return result
                finally:
                    await page.close()
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.warning("CDP 提取失败 %s: %s", url, e)
            return ExtractedContent(extraction_method="cdp_failed", url=url)
