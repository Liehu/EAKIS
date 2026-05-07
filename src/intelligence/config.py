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
class IntelligenceConfig:
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    clean: CleanConfig = field(default_factory=CleanConfig)
    use_stubs: bool = True
