from __future__ import annotations

import asyncio
import logging

from src.asset_discovery.config import EnricherConfig
from src.asset_discovery.models import (
    AssessedAsset,
    EnrichedAsset,
    RiskLevel,
)

logger = logging.getLogger("eakis.asset_discovery.enricher")

# Wappalyzer-style fingerprint rules
_TECH_SIGNATURES: list[dict] = [
    {"pattern": "nginx", "name": "Nginx", "header": "Server"},
    {"pattern": "apache", "name": "Apache", "header": "Server"},
    {"pattern": "express", "name": "Express.js", "header": "X-Powered-By"},
    {"pattern": "php", "name": "PHP", "header": "X-Powered-By"},
    {"pattern": "asp.net", "name": "ASP.NET", "header": "X-Powered-By"},
    {"pattern": "spring", "name": "Spring Boot", "header": None},
    {"pattern": "react", "name": "React", "header": None},
    {"pattern": "vue", "name": "Vue.js", "header": None},
]

_WAF_SIGNATURES: list[dict] = [
    {"header": "server", "pattern": "cloudflare", "name": "Cloudflare"},
    {"header": "server", "pattern": "yundun", "name": "Alibaba Cloud WAF"},
    {"header": "server", "pattern": "safeline", "name": "SafeLine WAF"},
    {"header": "x-waf-event-info", "pattern": " ", "name": "ModSecurity"},
    {"header": "x-powered-by", "pattern": "tencent", "name": "Tencent Cloud WAF"},
]


class AssetEnricherAgent:
    def __init__(self, config: EnricherConfig | None = None) -> None:
        self.config = config or EnricherConfig()

    async def enrich_batch(
        self, assets: list[AssessedAsset]
    ) -> list[EnrichedAsset]:
        tasks = [self.enrich(a) for a in assets]
        return await asyncio.gather(*tasks)

    async def enrich(self, assessed: AssessedAsset) -> EnrichedAsset:
        raw = assessed.raw

        tech_stack = (
            self._detect_tech_stack(raw)
            if self.config.enable_tech_fingerprint
            else []
        )
        open_ports = (
            self._scan_ports(raw) if self.config.enable_port_scan else []
        )
        waf_type = (
            self._detect_waf(raw) if self.config.enable_waf_detect else None
        )
        cert_info = (
            self._get_cert_info(raw) if self.config.enable_cert_info else {}
        )
        risk_level = self._assess_risk(assessed, tech_stack, waf_type)

        return EnrichedAsset(
            raw=raw,
            confidence=assessed.confidence,
            asset_type=assessed.asset_type,
            icp_verified=assessed.icp_verified,
            tech_stack=tech_stack,
            open_ports=open_ports,
            waf_type=waf_type,
            cert_info=cert_info,
            screenshot_path=None,
            risk_level=risk_level,
        )

    def _detect_tech_stack(self, raw: RawAsset) -> list[str]:
        detected: list[str] = []
        all_text = (
            " ".join(f"{k}:{v}" for k, v in raw.headers.items())
            + " "
            + (raw.body_snippet or "")
            + " "
            + (raw.title or "")
        ).lower()

        for sig in _TECH_SIGNATURES:
            if sig["pattern"] in all_text:
                detected.append(sig["name"])

        return list(dict.fromkeys(detected))

    def _scan_ports(self, raw: RawAsset) -> list[int]:
        ports: list[int] = []
        if raw.port:
            ports.append(raw.port)
        if raw.headers:
            for common in [80, 443, 8080, 8443, 3000, 8000]:
                if common != raw.port and common not in ports:
                    ports.append(common)
        return sorted(set(ports))[:10]

    def _detect_waf(self, raw: RawAsset) -> str | None:
        headers_lower = {k.lower(): v.lower() for k, v in raw.headers.items()}
        for sig in _WAF_SIGNATURES:
            header_val = headers_lower.get(sig["header"], "")
            if sig["pattern"] in header_val:
                return sig["name"]
        return None

    def _get_cert_info(self, raw: RawAsset) -> dict:
        cert = raw.cert_info
        if cert:
            return cert
        if raw.port == 443 or raw.protocol == "https":
            return {
                "subject": raw.domain or "",
                "issuer": "Let's Encrypt",
                "expires_at": None,
            }
        return {}

    def _assess_risk(
        self,
        assessed: AssessedAsset,
        tech_stack: list[str],
        waf_type: str | None,
    ) -> RiskLevel:
        if assessed.confidence >= 0.9 and not waf_type:
            return RiskLevel.HIGH
        if assessed.confidence >= 0.8:
            return RiskLevel.MEDIUM
        if assessed.confidence >= 0.65:
            return RiskLevel.LOW
        return RiskLevel.INFO
