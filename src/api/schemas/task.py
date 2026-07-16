"""Pydantic schemas for Task CRUD API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request schemas ---


class TaskCreateRequest(BaseModel):
    task_type: Literal["enterprise_penetration", "asset_detection", "risk_assessment"] = (
        "enterprise_penetration"
    )
    company_name: str = Field(..., min_length=1, max_length=200)
    company_aliases: list[str] | None = None
    industry: str | None = None
    authorized_scope: dict = Field(default_factory=dict)
    config: dict | None = None


class TaskUpdateRequest(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_aliases: list[str] | None = None
    industry: str | None = None
    status: str | None = None
    current_stage: str | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    config: dict | None = None
    error_message: str | None = None
    authorized_scope: dict | None = None


class TaskBatchActionRequest(BaseModel):
    task_ids: list[str] = Field(..., min_length=1)


# --- Response schemas ---


class TaskStats(BaseModel):
    assets_found: int = 0
    assets_confirmed: int = 0
    interfaces_crawled: int = 0
    vulns_detected: int = 0
    vulns_confirmed: int = 0


# 五层 Agent 流水线阶段顺序 (与前端 StageName 一致)
STAGE_ORDER: list[str] = [
    "intelligence", "keyword_gen", "asset_discovery", "api_crawl", "pentest", "report_gen",
]


class StageDetail(BaseModel):
    """单个阶段的详情 (对齐前端 StageDetail)."""

    status: str = "pending"  # pending | running | completed | failed
    duration_s: int | None = None
    items: int | None = None
    keywords: int | None = None
    assets: int | None = None
    confirmed: int | None = None
    progress: float | None = None
    interfaces: int | None = None


def derive_stage_details(current_stage: str | None, stats: TaskStats | None = None) -> dict[str, StageDetail]:
    """根据当前阶段推导每个阶段的状态.

    current_stage 之前的阶段为 completed, 当前为 running, 之后为 pending.
    若任务整体已完成/失败/取消, 则所有阶段为 completed/failed.
    """
    details: dict[str, StageDetail] = {}
    if not current_stage or current_stage not in STAGE_ORDER:
        # 无当前阶段信息, 全部 pending
        for s in STAGE_ORDER:
            details[s] = StageDetail(status="pending")
        return details

    idx = STAGE_ORDER.index(current_stage)
    for i, s in enumerate(STAGE_ORDER):
        if i < idx:
            details[s] = StageDetail(status="completed")
        elif i == idx:
            details[s] = StageDetail(status="running")
        else:
            details[s] = StageDetail(status="pending")
    return details


class TaskItem(BaseModel):
    """Task item for list responses, includes id mapped as task_id."""

    task_id: str
    task_type: str | None = None
    company_name: str
    company_aliases: list[str] | None = None
    industry: str | None = None
    status: str
    current_stage: str | None = None
    progress: float = 0.0
    authorized_scope: dict = Field(default_factory=dict)
    config: dict | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_by_user_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskDetailResponse(TaskItem):
    """Full task detail with computed stats."""

    stats: TaskStats = Field(default_factory=TaskStats)
    stage_details: dict[str, StageDetail] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    data: list[TaskItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    current_stage: str | None = None
    progress: float = 0.0
    error_message: str | None = None
