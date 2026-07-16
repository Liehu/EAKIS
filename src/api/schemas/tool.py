"""Pydantic schemas for tools API (S5)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


# ── Tool registry (static metadata) ──────────────────────
class ToolParamInfo(BaseModel):
    name: str
    input_type: str
    flag: str
    required: bool = False
    multiple: bool = False


class ToolInfo(BaseModel):
    name: str
    binary: str
    description: str
    category: str
    params: list[ToolParamInfo] = []
    allowed_flags: list[str] = []
    default_timeout: int = 300
    enabled: bool = True


# ── Run tool ─────────────────────────────────────────────
class RunToolRequest(BaseModel):
    inputs: dict = Field(..., description="工具输入 {domain/ip/url: value | [values]}")
    flags: list[str] | None = None
    timeout: int | None = Field(default=None, ge=10, le=3600)
    task_id: UUID | None = None


class ToolExecutionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tool_name: str
    category: str | None = None
    task_id: UUID | None = None
    inputs: dict
    flags: dict | None = None
    status: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    parsed: list | dict | None = None
    duration_s: float | None = None
    error: str | None = None
    started_at: datetime
    created_at: datetime


class ToolExecutionListResponse(BaseModel):
    data: list[ToolExecutionResponse]
    pagination: Pagination
