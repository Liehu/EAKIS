from dataclasses import dataclass, field


@dataclass
class AntiCrawlConfig:
    request_delay_min: float = 1.5
    request_delay_max: float = 4.0
    retry_max_attempts: int = 3
    retry_backoff: float = 2.0
    proxy_rotation: bool = True
    proxy_pool_size: int = 50
    ua_rotation: bool = True
    ua_pool_size: int = 200
    fingerprint_randomize: bool = True


@dataclass
class CrawlConfig:
    max_concurrent_sources: int = 5
    max_concurrent_pages: int = 10
    anti_crawl: AntiCrawlConfig = field(default_factory=AntiCrawlConfig)


@dataclass
class CleanConfig:
    min_text_length: int = 50
    max_stopword_ratio: float = 0.6
    staleness_days: int = 730
    dedup_jaccard_threshold: float = 0.85
    min_quality_score: float = 0.6


@dataclass
class ExtractionConfig:
    """全文内容提取配置。"""
    enabled: bool = True
    fast_mode_timeout: float = 15.0
    cdp_mode_timeout: float = 30.0
    cdp_wait_for_content: float = 2.0
    max_content_length: int = 5_000_000
    max_concurrent_extractions: int = 5
    min_content_length: int = 100
    auto_cdp_fallback: bool = True
    title_dedup_enabled: bool = True
    title_similarity_threshold: float = 0.9
    cdp_required_domains: list[str] = field(default_factory=lambda: [
        "mp.weixin.qq.com", "weibo.com", "x.com", "twitter.com",
    ])
    skip_url_patterns: list[str] = field(default_factory=lambda: [
        r"baidu\.com/s\?", r"bing\.com/search", r"google\.com/search",
        r"sogou\.com/web", r"so\.com/s",
        r"\.(pdf|zip|rar|exe|jpg|png|gif|svg|mp4)$",
    ])


@dataclass
class IntelligenceConfig:
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    extract: ExtractionConfig = field(default_factory=ExtractionConfig)
    clean: CleanConfig = field(default_factory=CleanConfig)
    use_stubs: bool = True
