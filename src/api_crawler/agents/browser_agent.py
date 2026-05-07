from __future__ import annotations

import logging
from urllib.parse import urlparse

from src.api_crawler.models import CrawlMethod, RawInterface
from src.api_crawler.services.base import BaseBrowserClient
from src.api_crawler.services.stub_browser import StubBrowserClient

logger = logging.getLogger("eakis.api_crawler.browser")


class BrowserAgent:
    def __init__(self, client: BaseBrowserClient | None = None) -> None:
        self.client = client or StubBrowserClient()

    async def crawl(
        self,
        urls: list[str],
        already_captured: list[str],
    ) -> list[RawInterface]:
        results: list[RawInterface] = []
        seen: set[str] = set(already_captured)

        for url in urls:
            try:
                captured = await self.client.navigate_and_interact(url, already_captured)
                for req in captured:
                    path = self._url_to_path(req.url)
                    key = f"{req.method}:{path}"
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            RawInterface(
                                path=path,
                                method=req.method,
                                request_headers=req.headers,
                                crawl_method=CrawlMethod.DYNAMIC,
                                source_url=url,
                                trigger_scenario=f"Dynamic interaction on {url}",
                            )
                        )
            except Exception as e:
                logger.warning("Browser crawl failed for %s: %s", url, e)

        return results

    @staticmethod
    def _url_to_path(url: str) -> str:
        parsed = urlparse(url)
        return parsed.path or "/"
