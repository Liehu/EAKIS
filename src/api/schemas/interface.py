"""Pydantic schemas for interface API endpoints (section 9.5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas ---


class CrawlStartRequest(BaseModel):
    assets: list[dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of {asset_id, url} dicts to crawl",
    )


class InterfaceUpdateRequest(BaseModel):
    test_priority: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = None
    skip_test: bool | None = None


# --- Response schemas ---


class ParameterItem(BaseModel):
    name: str
    location: str
    type: str = "string"
    required: bool = False
    example: str | None = None
    sensitive: bool = False


class InterfaceItem(BaseModel):
    interface_id: str
    asset_id: str
    path: str
    path_pattern: str = ""
    method: str
    api_type: str
    parameters: list[ParameterItem] = Field(default_factory=list)
    request_headers: dict[str, str] = Field(default_factory=dict)
    response_schema: dict = Field(default_factory=dict)
    auth_required: bool = False
    privilege_sensitive: bool = False
    sensitive_params: list[str] = Field(default_factory=list)
    trigger_scenario: str | None = None
    test_priority: int = 5
    crawl_method: str = "static"
    version: int = 1
    checksum: str = ""
    vuln_tested: bool = False
    vuln_count: int = 0
    skip_test: bool = False
    notes: str | None = None


class InterfaceSummary(BaseModel):
    total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    privilege_sensitive: int = 0
    untested: int = 0


class InterfaceListResponse(BaseModel):
    data: list[InterfaceItem] = Field(default_factory=list)
    summary: InterfaceSummary = Field(default_factory=InterfaceSummary)
    pagination: dict = Field(default_factory=dict)


class InterfaceDetailResponse(InterfaceItem):
    confidence: float = 1.0


class CrawlStartResponse(BaseModel):
    task_id: str
    status: str
    total_assets: int = 0
    total_raw: int = 0
    total_classified: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    privilege_sensitive_count: int = 0
    errors: list[str] = Field(default_factory=list)


class CrawlStatusResponse(BaseModel):
    task_id: str
    status: str
    total_interfaces: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    privilege_sensitive_count: int = 0
