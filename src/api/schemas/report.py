"""Pydantic schemas for report API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas ---


class GenerateReportRequest(BaseModel):
    format: list[str] = Field(default=["markdown"])
    sections: list[str] = Field(default=["summary", "assets", "interfaces", "vulns", "remediation"])
    language: str = "zh-CN"
    template: str = "standard"
    use_llm: bool = Field(default=False, description="是否用 LLM 生成执行摘要 (可选)")


# --- Response schemas ---


class QualityScoreItem(BaseModel):
    overall: float = 0.0
    accuracy: float = 0.0
    completeness: float = 0.0
    readability: float = 0.0
    actionability: float = 0.0


class ReportItem(BaseModel):
    report_id: str
    status: str = "generating"
    quality_score: dict = Field(default_factory=lambda: {
        "overall": 0, "accuracy": 0, "completeness": 0, "readability": 0, "actionability": 0,
    })
    files: dict[str, str] = Field(default_factory=dict)
    content: str | None = None
    page_count: int | None = None
    word_count: int | None = None
    generated_at: str | None = None
    generation_duration_minutes: float | None = None


class ReportListResponse(BaseModel):
    data: list[ReportItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class ReportJobResponse(BaseModel):
    report_job_id: str
    status: str
    estimated_minutes: int = 0
