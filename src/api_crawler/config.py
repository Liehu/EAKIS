from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StaticAnalysisConfig:
    max_js_files: int = 50
    max_html_pages: int = 100
    enable_sourcemap: bool = True


@dataclass
class BrowserConfig:
    headless: bool = True
    timeout_s: float = 30.0
    max_interactions: int = 20


@dataclass
class CDPConfig:
    max_buffer_mb: int = 50
    capture_ws: bool = True
    capture_sse: bool = True


@dataclass
class CrawlerConfig:
    static: StaticAnalysisConfig = field(default_factory=StaticAnalysisConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    cdp: CDPConfig = field(default_factory=CDPConfig)
    use_stubs: bool = True
