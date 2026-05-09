from __future__ import annotations

import logging
import re

from src.asset_discovery.models import FeatureVector, RawAsset

logger = logging.getLogger("eakis.asset_discovery.feature")

_DOMAIN_PATTERN_RE = re.compile(r"([a-zA-Z0-9-]+)\.[a-zA-Z]{2,}$")


class FeatureExtractorAgent:
    def __init__(
        self,
        target_domains: list[str] | None = None,
        target_icp_entity: str | None = None,
        target_ip_ranges: list[str] | None = None,
    ) -> None:
        self.target_domains = target_domains or []
        self.target_icp_entity = target_icp_entity
        self.target_ip_ranges = target_ip_ranges or []
        self._target_roots = {self._root_domain(d) for d in self.target_domains}

    async def extract_batch(
        self, assets: list[RawAsset]
    ) -> list[FeatureVector]:
        return [self.extract(asset) for asset in assets]

    def extract(self, asset: RawAsset) -> FeatureVector:
        return FeatureVector(
            icp_entity=self._icp_score(asset),
            domain_pattern=self._domain_score(asset),
            ip_attribution=self._ip_score(asset),
            header_features=self._header_score(asset),
            page_keywords=self._keyword_score(asset),
        )

    def _icp_score(self, asset: RawAsset) -> float:
        if not asset.icp_entity or not self.target_icp_entity:
            return 0.0
        if asset.icp_entity == self.target_icp_entity:
            return 1.0
        target_parts = set(self.target_icp_entity.lower().split())
        asset_parts = set(asset.icp_entity.lower().split())
        overlap = target_parts & asset_parts
        if not overlap:
            return 0.0
        return len(overlap) / max(len(target_parts), len(asset_parts))

    def _domain_score(self, asset: RawAsset) -> float:
        if not asset.domain:
            return 0.0
        root = self._root_domain(asset.domain)
        if root in self._target_roots:
            return 1.0
        for target_root in self._target_roots:
            if asset.domain.endswith("." + target_root):
                return 0.8
        return 0.0

    def _ip_score(self, asset: RawAsset) -> float:
        if not asset.ip_address or not self.target_ip_ranges:
            return 0.0
        import ipaddress

        try:
            addr = ipaddress.ip_address(asset.ip_address)
            for cidr in self.target_ip_ranges:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return 1.0
        except ValueError:
            pass
        return 0.0

    def _header_score(self, asset: RawAsset) -> float:
        if not asset.headers:
            return 0.0
        target_indicators = {"Server", "X-Powered-By", "Set-Cookie", "X-Application"}
        matches = sum(1 for k in asset.headers if k in target_indicators)
        return min(matches / 3.0, 1.0)

    def _keyword_score(self, asset: RawAsset) -> float:
        if not asset.body_snippet or not self.target_icp_entity:
            return 0.0
        keywords = self.target_icp_entity.lower().split()
        snippet = asset.body_snippet.lower()
        matches = sum(1 for kw in keywords if kw in snippet)
        return min(matches / max(len(keywords), 1), 1.0)

    @staticmethod
    def _root_domain(domain: str) -> str:
        domain = domain.rstrip(".")
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain
