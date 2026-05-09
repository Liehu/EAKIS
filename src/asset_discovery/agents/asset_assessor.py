from __future__ import annotations

import logging
import math

from src.asset_discovery.config import AssessorConfig
from src.asset_discovery.models import (
    AssetType,
    AssessedAsset,
    FeatureVector,
    RawAsset,
)

logger = logging.getLogger("eakis.asset_discovery.assessor")


class AssetAssessorAgent:
    def __init__(
        self,
        config: AssessorConfig | None = None,
        target_domains: list[str] | None = None,
        target_icp_entity: str | None = None,
        target_ip_ranges: list[str] | None = None,
    ) -> None:
        self.config = config or AssessorConfig()
        self.target_domains = target_domains or []
        self.target_icp_entity = target_icp_entity
        self.target_ip_ranges = target_ip_ranges or []
        self._target_roots = {self._root_domain(d) for d in self.target_domains}

    def assess_batch(
        self,
        assets: list[RawAsset],
        features: list[FeatureVector],
    ) -> list[AssessedAsset]:
        results: list[AssessedAsset] = []
        for asset, fv in zip(assets, features):
            results.append(self.assess(asset, fv))
        return results

    def assess(self, raw: RawAsset, fv: FeatureVector) -> AssessedAsset:
        confidence = 0.0
        matched_rules: list[str] = []

        # Special rules (highest priority)
        if raw.icp_entity and self.target_icp_entity:
            if raw.icp_entity == self.target_icp_entity:
                confidence = self.config.icp_exact_match_confidence
                matched_rules.append("icp_exact_match")

        if confidence < 0.85 and self._ip_in_range(raw):
            if fv.domain_pattern > 0 or fv.header_features > 0:
                confidence = self.config.ip_range_match_confidence
                matched_rules.append("ip_range_match")

        if confidence < 0.85 and raw.domain:
            if self._is_subdomain(raw.domain):
                confidence = self.config.subdomain_match_confidence
                matched_rules.append("subdomain_match")

        # Weighted cosine similarity fallback
        if not matched_rules:
            confidence = self._weighted_cosine(fv)
            if confidence >= self.config.high_confidence_threshold:
                matched_rules.append("high_confidence_similarity")
            elif confidence >= self.config.medium_confidence_threshold:
                matched_rules.append("medium_confidence_similarity")

        icp_verified = (
            raw.icp_entity is not None
            and raw.icp_entity == self.target_icp_entity
        )

        return AssessedAsset(
            raw=raw,
            confidence=round(confidence, 4),
            feature_vector=fv,
            matched_rules=matched_rules,
            asset_type=self._classify_type(raw),
            icp_verified=icp_verified,
        )

    def filter_confirmed(self, assessed: list[AssessedAsset]) -> list[AssessedAsset]:
        confirmed = []
        for a in assessed:
            if a.confidence >= self.config.high_confidence_threshold:
                confirmed.append(a)
            elif a.confidence >= self.config.medium_confidence_threshold:
                a.matched_rules.append("needs_manual_confirmation")
                confirmed.append(a)
        return confirmed

    def _weighted_cosine(self, fv: FeatureVector) -> float:
        target = FeatureVector(
            icp_entity=1.0, domain_pattern=1.0, ip_attribution=1.0,
            header_features=0.5, page_keywords=0.5,
        )
        dims = list(FeatureVector.WEIGHTS.keys())
        dot = sum(fv.WEIGHTS[d] * getattr(fv, d) * getattr(target, d) for d in dims)
        mag_a = math.sqrt(sum(fv.WEIGHTS[d] * getattr(fv, d) ** 2 for d in dims))
        mag_b = math.sqrt(sum(fv.WEIGHTS[d] * getattr(target, d) ** 2 for d in dims))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _ip_in_range(self, raw: RawAsset) -> bool:
        if not raw.ip_address or not self.target_ip_ranges:
            return False
        import ipaddress

        try:
            addr = ipaddress.ip_address(raw.ip_address)
            return any(
                addr in ipaddress.ip_network(cidr, strict=False)
                for cidr in self.target_ip_ranges
            )
        except ValueError:
            return False

    def _is_subdomain(self, domain: str) -> bool:
        for root in self._target_roots:
            if domain.endswith("." + root):
                return True
        return False

    @staticmethod
    def _classify_type(raw: RawAsset) -> AssetType:
        domain = (raw.domain or "").lower()
        title = (raw.title or "").lower()
        port = raw.port

        if "api" in domain or "api" in title or port in (8080, 3000, 8000):
            return AssetType.API
        if port in (25, 53, 22, 3306, 5432, 6379, 27017):
            return AssetType.INFRA
        if "mobile" in domain or "m." in domain or "app" in domain:
            return AssetType.MOBILE
        return AssetType.WEB

    @staticmethod
    def _root_domain(domain: str) -> str:
        parts = domain.rstrip(".").split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else domain
