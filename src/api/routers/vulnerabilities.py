"""Vulnerability API router - M6.

Endpoints:
  GET   /v1/tasks/{task_id}/vulnerabilities              - list vulnerabilities
  GET   /v1/tasks/{task_id}/vulnerabilities/statistics   - vuln statistics
  GET   /v1/tasks/{task_id}/vulnerabilities/{vuln_id}     - get vuln detail
  PATCH /v1/tasks/{task_id}/vulnerabilities/{vuln_id}     - update vuln
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.vulnerability import (
    UpdateVulnRequest,
    VulnListResponse,
    VulnerabilityItem,
    VulnStatistics,
)
from src.models.vulnerability import Vulnerability

router = APIRouter(tags=["vulnerabilities"])


def _vuln_to_item(v: Vulnerability) -> VulnerabilityItem:
    """Convert ORM Vulnerability to schema VulnerabilityItem."""
    evidence = v.evidence if isinstance(v.evidence, dict) else {}
    return VulnerabilityItem(
        id=str(v.id),
        asset_id=str(v.asset_id),
        interface_id=str(v.interface_id) if v.interface_id else None,
        vuln_type=v.vuln_type,
        severity=v.severity.value if hasattr(v.severity, "value") else (v.severity or "info"),
        cvss_score=v.cvss_score,
        title=v.title,
        description=v.description,
        affected_path=v.affected_path,
        test_payload=v.test_payload,
        evidence=evidence,
        llm_confidence=v.llm_confidence,
        false_positive_risk=v.false_positive_risk,
        false_positive_reason=v.false_positive_reason,
        remediation=v.remediation,
        status=v.status.value if hasattr(v.status, "value") else (v.status or "detected"),
        human_confirmed=v.human_confirmed or False,
        confirmed_by=v.confirmed_by,
        confirmed_at=str(v.confirmed_at) if v.confirmed_at else None,
        discovered_at=str(v.discovered_at) if v.discovered_at else None,
    )


async def _build_statistics(db: AsyncSession, task_id: UUID) -> VulnStatistics:
    """Build vulnerability statistics for a task."""
    # by_severity
    rows = await db.execute(
        select(Vulnerability.severity, func.count(Vulnerability.id))
        .where(Vulnerability.task_id == task_id)
        .group_by(Vulnerability.severity)
    )
    by_severity = {}
    for sev, cnt in rows:
        by_severity[sev if isinstance(sev, str) else sev.value] = cnt

    # by_type
    rows = await db.execute(
        select(Vulnerability.vuln_type, func.count(Vulnerability.id))
        .where(Vulnerability.task_id == task_id)
        .group_by(Vulnerability.vuln_type)
    )
    by_type = {vt: cnt for vt, cnt in rows}

    # totals
    total = sum(by_severity.values()) or 0
    confirmed = (await db.scalar(
        select(func.count(Vulnerability.id)).where(
            Vulnerability.task_id == task_id,
            Vulnerability.human_confirmed.is_(True),
        )
    )) or 0

    # simple risk score based on severity weights
    weights = {"critical": 10, "high": 7, "medium": 4, "low": 1, "info": 0.5}
    risk_score = sum(
        weights.get(sev if isinstance(sev, str) else sev.value, 0) * cnt
        for sev, cnt in by_severity.items()
    )

    return VulnStatistics(
        by_severity=by_severity,
        by_type=by_type,
        by_asset=[],
        trend=[],
        risk_score=min(risk_score, 100),
        confirmed_rate=round(confirmed / total, 2) if total else 0.0,
    )


@router.get("/tasks/{task_id}/vulnerabilities", response_model=VulnListResponse)
async def list_vulnerabilities(
    task_id: UUID,
    severity: str | None = Query(default=None),
    vuln_type: str | None = Query(default=None),
    confirmed: bool | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> VulnListResponse:
    """List vulnerabilities for a task."""
    stmt = select(Vulnerability).where(Vulnerability.task_id == task_id)
    count_stmt = select(func.count(Vulnerability.id)).where(Vulnerability.task_id == task_id)

    if severity:
        stmt = stmt.where(Vulnerability.severity == severity)
        count_stmt = count_stmt.where(Vulnerability.severity == severity)
    if vuln_type:
        stmt = stmt.where(Vulnerability.vuln_type == vuln_type)
        count_stmt = count_stmt.where(Vulnerability.vuln_type == vuln_type)
    if confirmed is not None:
        stmt = stmt.where(Vulnerability.human_confirmed.is_(confirmed))
        count_stmt = count_stmt.where(Vulnerability.human_confirmed.is_(confirmed))
    if asset_id:
        stmt = stmt.where(Vulnerability.asset_id == asset_id)
        count_stmt = count_stmt.where(Vulnerability.asset_id == asset_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(Vulnerability.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    vulns = result.scalars().all()

    summary = await _build_statistics(db, task_id)

    return VulnListResponse(
        data=[_vuln_to_item(v) for v in vulns],
        summary=summary,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get("/tasks/{task_id}/vulnerabilities/statistics", response_model=VulnStatistics)
async def get_vuln_statistics(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> VulnStatistics:
    """Get vulnerability statistics for a task."""
    return await _build_statistics(db, task_id)


@router.get("/tasks/{task_id}/vulnerabilities/{vuln_id}", response_model=VulnerabilityItem)
async def get_vulnerability(
    task_id: UUID,
    vuln_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> VulnerabilityItem:
    """Get vulnerability detail."""
    vuln = await db.get(Vulnerability, vuln_id)
    if vuln is None or str(vuln.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return _vuln_to_item(vuln)


@router.patch("/tasks/{task_id}/vulnerabilities/{vuln_id}", response_model=VulnerabilityItem)
async def update_vulnerability(
    task_id: UUID,
    vuln_id: str,
    body: UpdateVulnRequest,
    db: AsyncSession = Depends(get_async_db),
) -> VulnerabilityItem:
    """Update vulnerability (confirm, change status, etc.)."""
    vuln = await db.get(Vulnerability, vuln_id)
    if vuln is None or str(vuln.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vuln, field, value)

    await db.commit()
    await db.refresh(vuln)
    return _vuln_to_item(vuln)
