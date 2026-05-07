from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CrawlMethod(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    CDP = "cdp"
    INFERRED = "inferred"


class ProtocolType(str, Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    SSE = "sse"
    GRPC_WEB = "grpc_web"


class InterfaceType(str, Enum):
    AUTH = "auth"
    QUERY = "query"
    OPERATION = "operation"
    UPLOAD = "upload"
    SEARCH = "search"
    WEBHOOK = "webhook"
    CONFIG = "config"
    ADMIN = "admin"


class CrawlStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    CRAWLING = "crawling"
    CLASSIFYING = "classifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ParameterInfo:
    name: str
    location: str  # path | query | body | header
    type: str = "string"
    required: bool = False
    example: str | None = None
    sensitive: bool = False


@dataclass
class CapturedRequest:
    url: str
    method: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    source: str = "static"
    timestamp: str | None = None


@dataclass
class WSFrame:
    direction: str  # sent | received
    payload: str
    timestamp: str | None = None
    opcode: int = 1


@dataclass
class SSEEvent:
    url: str
    event_type: str | None = None
    data: str = ""
    event_id: str | None = None
    timestamp: str | None = None


@dataclass
class CDPTrafficItem:
    url: str
    method: str = "GET"
    protocol: ProtocolType = ProtocolType.HTTP
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    request_id: str | None = None
    resource_type: str | None = None
    status_code: int | None = None
    ws_frames: list[WSFrame] = field(default_factory=list)
    sse_events: list[SSEEvent] = field(default_factory=list)
    timestamp: str | None = None


@dataclass
class RawInterface:
    path: str
    method: str
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_headers: dict[str, str] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    auth_required: bool = False
    trigger_scenario: str | None = None
    crawl_method: CrawlMethod = CrawlMethod.STATIC
    source_url: str | None = None


@dataclass
class ClassifiedInterface:
    interface_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ""
    path: str = ""
    path_pattern: str = ""
    method: str = "GET"
    api_type: InterfaceType = InterfaceType.QUERY
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_headers: dict[str, str] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    auth_required: bool = False
    privilege_sensitive: bool = False
    sensitive_params: list[str] = field(default_factory=list)
    trigger_scenario: str | None = None
    test_priority: int = 5
    crawl_method: CrawlMethod = CrawlMethod.STATIC
    version: int = 1
    checksum: str = ""
    confidence: float = 1.0
    skip_test: bool = False
    notes: str | None = None


@dataclass
class CrawlResult:
    task_id: str
    status: CrawlStatus
    total_assets: int = 0
    total_raw: int = 0
    total_classified: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_method: dict[str, int] = field(default_factory=dict)
    privilege_sensitive_count: int = 0
    errors: list[str] = field(default_factory=list)
