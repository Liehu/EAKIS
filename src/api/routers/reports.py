"""Report API router - M8.

Endpoints:
  GET  /v1/tasks/{task_id}/reports                  - list reports
  GET  /v1/tasks/{task_id}/reports/{report_id}      - get report detail
  POST /v1/tasks/{task_id}/reports                  - generate report
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.report import (
    GenerateReportRequest,
    ReportItem,
    ReportJobResponse,
    ReportListResponse,
)
from src.models.report import Report

router = APIRouter(tags=["reports"])


def _report_to_item(r: Report) -> ReportItem:
    """Convert ORM Report to schema ReportItem."""
    qs = r.quality_score if isinstance(r.quality_score, dict) else {}
    files = {}
    if r.markdown_path:
        files["markdown"] = r.markdown_path
    if r.pdf_path:
        files["pdf"] = r.pdf_path
    return ReportItem(
        report_id=str(r.id),
        status=r.status.value if hasattr(r.status, "value") else (r.status or "generating"),
        quality_score=qs,
        files=files,
        content=r.content,
        page_count=r.page_count,
        word_count=r.word_count,
        generated_at=str(r.generated_at) if r.generated_at else None,
        generation_duration_minutes=round(r.generation_duration_s / 60) if r.generation_duration_s else None,
    )


@router.get("/tasks/{task_id}/reports", response_model=ReportListResponse)
async def list_reports(
    task_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> ReportListResponse:
    """List reports for a task."""
    stmt = select(Report).where(Report.task_id == task_id)
    count_stmt = select(func.count(Report.id)).where(Report.task_id == task_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    reports = result.scalars().all()

    return ReportListResponse(
        data=[_report_to_item(r) for r in reports],
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get("/tasks/{task_id}/reports/{report_id}", response_model=ReportItem)
async def get_report(
    task_id: UUID,
    report_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ReportItem:
    """Get report detail."""
    report = await db.get(Report, report_id)
    if report is None or str(report.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_item(report)


@router.post("/tasks/{task_id}/reports", response_model=ReportJobResponse, status_code=201)
async def generate_report(
    task_id: UUID,
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ReportJobResponse:
    """Generate a new report for a task.

    Runs aggregation + rendering synchronously (the report is available
    immediately in the response via GET). LLM mode is optional (use_llm).
    """
    from src.reporting.worker import generate_report_task

    # Create the report row, then generate into it.
    report = Report(
        task_id=task_id,
        status="generating",
        template=body.template,
        language=body.language,
    )
    db.add(report)
    await db.flush()

    # Generate synchronously (aggregation + render + score + persist).
    await generate_report_task(db, report.id, task_id, template_name=body.template, use_llm=body.use_llm)

    await db.refresh(report)
    duration_min = round((report.generation_duration_s or 0) / 60, 2)

    return ReportJobResponse(
        report_job_id=str(report.id),
        status=report.status.value if hasattr(report.status, "value") else report.status,
        estimated_minutes=int(max(1, duration_min)) if duration_min else 0,
    )
