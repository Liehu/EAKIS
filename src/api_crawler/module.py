from __future__ import annotations

import logging
from typing import Any

from src.api_crawler.agents.browser_agent import BrowserAgent
from src.api_crawler.agents.cdp_interceptor import CDPAgent
from src.api_crawler.agents.interface_classifier import InterfaceClassifier
from src.api_crawler.agents.static_analyzer import StaticAnalyzer
from src.api_crawler.agents.version_tracker import VersionTracker
from src.api_crawler.config import CrawlerConfig
from src.api_crawler.models import (
    ClassifiedInterface,
    CrawlResult,
    CrawlStatus,
    RawInterface,
)

logger = logging.getLogger("eakis.api_crawler")


class ApiCrawlerModule:
    def __init__(self, config: CrawlerConfig | None = None) -> None:
        self.config = config or CrawlerConfig()
        self.static_analyzer = StaticAnalyzer()
        self.browser_agent = BrowserAgent()
        self.cdp_agent = CDPAgent()
        self.classifier = InterfaceClassifier()
        self.version_tracker = VersionTracker()

        self._interfaces: list[ClassifiedInterface] = []
        self._status: CrawlStatus = CrawlStatus.PENDING
        self._task_id: str = ""

    async def run(
        self,
        task_id: str,
        assets: list[dict[str, Any]],
    ) -> CrawlResult:
        self._task_id = task_id
        self._status = CrawlStatus.ANALYZING
        errors: list[str] = []
        all_raw: list[RawInterface] = []

        try:
            for asset in assets:
                asset_id = asset.get("asset_id", "")
                url = asset.get("url", "")
                if not url:
                    continue

                # Layer 1: Static analysis
                static_results = self._static_crawl(url)
                all_raw.extend(static_results)
                logger.info(
                    "[%s] Static analysis: %d interfaces from %s",
                    task_id, len(static_results), url,
                )

                # Layer 2: Browser interaction (stub)
                captured_paths = [r.path for r in all_raw]
                dynamic_results = await self.browser_agent.crawl([url], captured_paths)
                all_raw.extend(dynamic_results)
                logger.info(
                    "[%s] Dynamic crawl: %d interfaces from %s",
                    task_id, len(dynamic_results), url,
                )

                # Layer 3: CDP capture (stub)
                captured_paths += [r.path for r in dynamic_results]
                cdp_results = await self.cdp_agent.capture([url], captured_paths)
                all_raw.extend(cdp_results)
                logger.info(
                    "[%s] CDP capture: %d interfaces from %s",
                    task_id, len(cdp_results), url,
                )

            # Classify + normalize
            self._status = CrawlStatus.CLASSIFYING
            classified: list[ClassifiedInterface] = []
            for raw in all_raw:
                asset_id = self._find_asset_for_raw(raw, assets)
                classified.append(self.classifier.classify(raw, asset_id))

            # Version tracking
            self._interfaces = self.version_tracker.track_batch(
                classified, existing_checksums={}
            )
            self._status = CrawlStatus.COMPLETED

        except Exception as e:
            self._status = CrawlStatus.FAILED
            errors.append(str(e))
            logger.exception("[%s] API crawl failed", task_id)

        by_type: dict[str, int] = {}
        by_method: dict[str, int] = {}
        priv_count = 0
        for iface in self._interfaces:
            by_type[iface.api_type.value] = by_type.get(iface.api_type.value, 0) + 1
            by_method[iface.method] = by_method.get(iface.method, 0) + 1
            if iface.privilege_sensitive:
                priv_count += 1

        return CrawlResult(
            task_id=task_id,
            status=self._status,
            total_assets=len(assets),
            total_raw=len(all_raw),
            total_classified=len(self._interfaces),
            by_type=by_type,
            by_method=by_method,
            privilege_sensitive_count=priv_count,
            errors=errors,
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "task_id": self._task_id,
            "status": self._status.value,
            "total_interfaces": len(self._interfaces),
            "by_type": {
                t: len([i for i in self._interfaces if i.api_type.value == t])
                for t in set(i.api_type.value for i in self._interfaces)
            },
            "privilege_sensitive_count": len(
                [i for i in self._interfaces if i.privilege_sensitive]
            ),
        }

    def get_interfaces(
        self,
        asset_id: str | None = None,
        api_type: str | None = None,
        method: str | None = None,
        privilege_sensitive: bool | None = None,
        min_priority: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        filtered = self._interfaces
        if asset_id:
            filtered = [i for i in filtered if i.asset_id == asset_id]
        if api_type:
            filtered = [i for i in filtered if i.api_type.value == api_type]
        if method:
            filtered = [i for i in filtered if i.method == method.upper()]
        if privilege_sensitive is not None:
            filtered = [i for i in filtered if i.privilege_sensitive == privilege_sensitive]
        if min_priority is not None:
            filtered = [i for i in filtered if i.test_priority >= min_priority]

        start = (page - 1) * page_size
        return [self._iface_to_dict(i) for i in filtered[start : start + page_size]]

    def get_interface(self, interface_id: str) -> dict[str, Any] | None:
        for i in self._interfaces:
            if i.interface_id == interface_id:
                return self._iface_to_dict(i)
        return None

    def update_interface(
        self,
        interface_id: str,
        test_priority: int | None = None,
        notes: str | None = None,
        skip_test: bool | None = None,
    ) -> dict[str, Any] | None:
        for i in self._interfaces:
            if i.interface_id == interface_id:
                if test_priority is not None:
                    i.test_priority = min(max(test_priority, 1), 10)
                if notes is not None:
                    i.notes = notes
                if skip_test is not None:
                    i.skip_test = skip_test
                return self._iface_to_dict(i)
        return None

    def _static_crawl(self, url: str) -> list[RawInterface]:
        stub_js = """
        fetch('/api/v1/users');
        fetch('/api/v1/orders');
        axios.post('/api/v1/cart', {});
        axios.get('/api/v1/products');
        """
        return self.static_analyzer.analyze_js(stub_js, base_url=url)

    @staticmethod
    def _find_asset_for_raw(
        raw: RawInterface, assets: list[dict[str, Any]]
    ) -> str:
        source = raw.source_url or ""
        for asset in assets:
            if asset.get("url", "") in source:
                return asset.get("asset_id", "")
        return assets[0].get("asset_id", "") if assets else ""

    @staticmethod
    def _iface_to_dict(iface: ClassifiedInterface) -> dict[str, Any]:
        return {
            "interface_id": iface.interface_id,
            "asset_id": iface.asset_id,
            "path": iface.path,
            "path_pattern": iface.path_pattern,
            "method": iface.method,
            "api_type": iface.api_type.value,
            "parameters": [
                {
                    "name": p.name,
                    "location": p.location,
                    "type": p.type,
                    "required": p.required,
                    "example": p.example,
                    "sensitive": p.sensitive,
                }
                for p in iface.parameters
            ],
            "request_headers": iface.request_headers,
            "response_schema": iface.response_schema,
            "auth_required": iface.auth_required,
            "privilege_sensitive": iface.privilege_sensitive,
            "sensitive_params": iface.sensitive_params,
            "trigger_scenario": iface.trigger_scenario,
            "test_priority": iface.test_priority,
            "crawl_method": iface.crawl_method.value,
            "version": iface.version,
            "checksum": iface.checksum,
            "confidence": iface.confidence,
            "skip_test": iface.skip_test,
            "notes": iface.notes,
        }
