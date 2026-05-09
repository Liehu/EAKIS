from __future__ import annotations

from dataclasses import dataclass, field


RATE_LIMITS: dict[str, dict[str, float]] = {
    "fofa": {
        "requests_per_minute": 10.0,
        "requests_per_day": 1000.0,
    },
    "hunter": {
        "requests_per_minute": 5.0,
        "requests_per_day": 500.0,
    },
    "shodan": {
        "requests_per_minute": 1.0,
        "requests_per_day": 100.0,
    },
    "censys": {
        "requests_per_minute": 5.0,
        "requests_per_day": 250.0,
    },
    "zoomeye": {
        "requests_per_minute": 10.0,
        "requests_per_day": 500.0,
    },
}

SUPPORTED_PLATFORMS = list(RATE_LIMITS.keys())


@dataclass
class SearchConfig:
    platforms: list[str] = field(default_factory=lambda: ["fofa", "hunter"])
    page_size: int = 100
    max_pages: int = 10
    deduplicate: bool = True


@dataclass
class AssessorConfig:
    high_confidence_threshold: float = 0.85
    medium_confidence_threshold: float = 0.65
    icp_exact_match_confidence: float = 0.98
    ip_range_match_confidence: float = 0.90
    subdomain_match_confidence: float = 0.88


@dataclass
class EnricherConfig:
    enable_port_scan: bool = True
    enable_cert_info: bool = True
    enable_waf_detect: bool = True
    enable_tech_fingerprint: bool = True
    enable_screenshot: bool = False
    scan_timeout_s: float = 10.0


@dataclass
class AssetDiscoveryConfig:
    search: SearchConfig = field(default_factory=SearchConfig)
    assessor: AssessorConfig = field(default_factory=AssessorConfig)
    enricher: EnricherConfig = field(default_factory=EnricherConfig)
    use_stubs: bool = True
    vector_store_enabled: bool = False
