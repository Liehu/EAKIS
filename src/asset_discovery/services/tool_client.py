"""Tool-backed search client — bridges AssetDiscoveryModule to ToolExecutor.

Instead of StubSearchClient (fake data) or a real Fofa/Shodan API client, this
implementation discovers assets via CLI tools registered in ToolExecutor:
  - "subfinder" platform → subfinder -d domain → subdomains
  - "dnsx" platform      → dnsx -d subdomains → resolved IPs
  - "httpx" platform     → httpx -u host:port → live HTTP + fingerprint
  - "cert" platform      → crt.sh → related domains
  - other platforms (fofa/shodan/...) → falls back to StubSearchClient
    (those need API keys; integrate separately)

This lets step 2(2) 域名挖掘链路 run for real when the binaries are installed,
while gracefully degrading when they're not (ToolExecutor returns unavailable).
"""

from __future__ import annotations

import asyncio
import logging

from src.asset_discovery.models import RawAsset
from src.asset_discovery.services.base import BaseSearchClient, StubSearchClient

logger = logging.getLogger("eakis.asset_discovery.tools")

# Platforms handled by CLI tools.
_TOOL_PLATFORMS = {"subfinder", "dnsx", "httpx", "cert"}


class ToolBackedSearchClient(BaseSearchClient):
    """SearchClient that delegates CLI-tool platforms to ToolExecutor.

    Non-tool platforms (fofa/shodan/...) fall back to StubSearchClient so the
    pipeline still produces data for them (until API keys are configured).
    """

    def __init__(self) -> None:
        self._stub = StubSearchClient()  # fallback for API-based platforms
        self._executor = None  # lazy

    def _get_executor(self):
        if self._executor is None:
            from src.tools.executor import get_executor
            self._executor = get_executor()
        return self._executor

    async def search(
        self,
        platform: str,
        query: str,
        page_size: int = 100,
        max_pages: int = 10,
    ) -> list[RawAsset]:
        platform_lower = platform.lower()
        if platform_lower not in _TOOL_PLATFORMS:
            # API-based platform without keys → stub fallback
            return await self._stub.search(platform, query, page_size, max_pages)

        # The query for tool platforms is a domain (e.g. "example.com").
        domain = query.strip().split()[0] if query.strip() else ""
        if not domain:
            logger.warning("Tool platform %s: empty query/domain", platform)
            return []

        if platform_lower == "subfinder":
            return await self._run_subfinder(domain, query)
        if platform_lower == "dnsx":
            return await self._run_dnsx(domain, query)
        if platform_lower == "httpx":
            return await self._run_httpx(domain, query)
        if platform_lower == "cert":
            return await self._run_cert(domain, query)
        return []

    async def _run_subfinder(self, domain: str, query: str) -> list[RawAsset]:
        """subfinder -d domain → subdomains → RawAsset (domain only, no IP yet)."""
        ex = self._get_executor()
        result = ex.run("subfinder", {"domain": [domain]})
        if result.status != "success" or not result.parsed:
            logger.info("subfinder %s: %s (degrade)", domain, result.status)
            return []
        subdomains = result.parsed if isinstance(result.parsed, list) else []
        return [
            RawAsset(domain=sub, source_platform="subfinder", source_query=query)
            for sub in subdomains[:200]  # cap
        ]

    async def _run_dnsx(self, domain: str, query: str) -> list[RawAsset]:
        """dnsx -d domain → resolved IPs."""
        ex = self._get_executor()
        result = ex.run("dnsx", {"domain": [domain]})
        if result.status != "success" or not result.parsed:
            return []
        entries = result.parsed if isinstance(result.parsed, list) else []
        assets: list[RawAsset] = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            host = e.get("host", domain)
            ips = e.get("a", []) or e.get("ips", [])
            for ip in (ips if isinstance(ips, list) else [ips]):
                assets.append(RawAsset(domain=host, ip_address=str(ip), source_platform="dnsx", source_query=query))
        return assets

    async def _run_httpx(self, target: str, query: str) -> list[RawAsset]:
        """httpx -u host → live HTTP + title + tech."""
        ex = self._get_executor()
        # httpx accepts url/domain; validate via the tool's schema
        inputs = {"domain": [target]} if "." in target and "://" not in target else {"url": [target]}
        result = ex.run("httpx", inputs)
        if result.status != "success" or not result.parsed:
            return []
        entries = result.parsed if isinstance(result.parsed, list) else []
        assets: list[RawAsset] = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            url = e.get("url", "")
            host = e.get("host", target)
            assets.append(RawAsset(
                domain=host, ip_address=e.get("a", [None])[0] if isinstance(e.get("a"), list) else e.get("a"),
                port=e.get("port"),
                title=e.get("title", ""),
                source_platform="httpx", source_query=query,
            ))
            # tech stack would be in e.get("tech") — enriched later
        return assets

    async def _run_cert(self, domain: str, query: str) -> list[RawAsset]:
        """crt.sh → related domains sharing the cert."""
        ex = self._get_executor()
        # cert tool uses curl; the registry wires the crt.sh URL via fixed_flags.
        # For now pass domain and parse the crt.sh JSON response.
        result = ex.run("cert", {"domain": domain})
        if result.status != "success" or not result.parsed:
            return []
        domains = result.parsed if isinstance(result.parsed, list) else []
        return [
            RawAsset(domain=d, source_platform="cert", source_query=query)
            for d in domains[:100]
        ]


def get_search_client() -> BaseSearchClient:
    """Factory: return ToolBackedSearchClient (CLI tools) by default.

    If asset_discovery_use_stubs is True in settings, return StubSearchClient
    (legacy behavior) instead.
    """
    from src.core.settings import get_settings
    settings = get_settings()
    if settings.asset_discovery_use_stubs:
        return StubSearchClient()
    return ToolBackedSearchClient()
