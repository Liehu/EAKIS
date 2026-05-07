from __future__ import annotations

import logging
from urllib.parse import urlparse

from src.api_crawler.models import (
    CDPTrafficItem,
    CrawlMethod,
    ProtocolType,
    RawInterface,
)
from src.api_crawler.services.base import BaseCDPClient
from src.api_crawler.services.stub_browser import StubCDPClient

logger = logging.getLogger("eakis.api_crawler.cdp")


class CDPAgent:
    def __init__(self, client: BaseCDPClient | None = None) -> None:
        self.client = client or _default_client()

    async def capture(
        self,
        urls: list[str],
        already_captured: list[str],
    ) -> list[RawInterface]:
        results: list[RawInterface] = []
        seen: set[str] = set(already_captured)

        traffic_items = await self.client.capture_batch(urls)

        for item in traffic_items:
            path = self._url_to_path(item.url)
            key = f"{item.method}:{path}"

            if key in seen:
                continue
            seen.add(key)

            raw = _traffic_to_raw(item)
            if raw is not None:
                results.append(raw)

        return results

    async def capture_detailed(
        self,
        urls: list[str],
        already_captured: list[str],
    ) -> list[CDPTrafficItem]:
        traffic_items = await self.client.capture_batch(urls)
        seen: set[str] = set(already_captured)
        deduped: list[CDPTrafficItem] = []
        for item in traffic_items:
            path = self._url_to_path(item.url)
            key = f"{item.method}:{path}"
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    @staticmethod
    def _url_to_path(url: str) -> str:
        parsed = urlparse(url)
        return parsed.path or "/"


def _traffic_to_raw(item: CDPTrafficItem) -> RawInterface | None:
    protocol = item.protocol
    if protocol == ProtocolType.WEBSOCKET:
        return RawInterface(
            path=_extract_path(item.url),
            method="GET",
            request_headers=item.headers,
            crawl_method=CrawlMethod.CDP,
            source_url=item.url,
            trigger_scenario=f"CDP WebSocket capture ({len(item.ws_frames)} frames)",
        )
    if protocol == ProtocolType.SSE:
        return RawInterface(
            path=_extract_path(item.url),
            method="GET",
            request_headers=item.headers,
            crawl_method=CrawlMethod.CDP,
            source_url=item.url,
            trigger_scenario=f"CDP SSE capture ({len(item.sse_events)} events)",
        )
    if protocol == ProtocolType.GRPC_WEB:
        return RawInterface(
            path=_extract_path(item.url),
            method=item.method,
            request_headers=item.headers,
            crawl_method=CrawlMethod.CDP,
            source_url=item.url,
            trigger_scenario="CDP gRPC-Web capture",
        )
    return RawInterface(
        path=_extract_path(item.url),
        method=item.method,
        request_headers=item.headers,
        crawl_method=CrawlMethod.CDP,
        source_url=item.url,
        trigger_scenario="CDP HTTP capture",
    )


def _extract_path(url: str) -> str:
    return urlparse(url).path or "/"


def _default_client() -> BaseCDPClient:
    try:
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        return PlaywrightCDPClient()
    except Exception:
        logger.info("Playwright not available, using stub CDP client")
        return StubCDPClient()
