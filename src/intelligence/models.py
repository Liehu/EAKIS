from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceCategory(str, Enum):
    NEWS = "news"
    OFFICIAL = "official"
    LEGAL = "legal"
    SECURITY = "security"
    ASSET_ENGINE = "asset_engine"


class CollectionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


@dataclass
class DataSource:
    source_id: str
    name: str
    category: SourceCategory
    priority: int  # 1-10
    expected_yield: float  # 0.0-1.0
    rate_limit: float  # requests per second
    status: CollectionStatus = CollectionStatus.PENDING
    items_crawled: int = 0
    error_message: str | None = None


@dataclass
class RawDocument:
    content: str
    source_type: SourceCategory
    source_name: str
    source_url: str | None = None
    published_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CleanedDocument:
    content: str
    source_type: SourceCategory
    source_name: str
    source_url: str | None = None
    published_at: datetime | None = None
    quality_score: float = 0.0
    entities: list[str] = field(default_factory=list)
    checksum: str = ""


@dataclass
class DslQuery:
    platform: str
    query: str
    syntax_valid: bool = True


@dataclass
class CollectionResult:
    task_id: str
    status: CollectionStatus
    total_sources: int
    total_documents: int
    cleaned_documents: int
    avg_quality_score: float
    errors: list[str] = field(default_factory=list)
