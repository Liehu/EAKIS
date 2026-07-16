"""Report data aggregator (S2 M6).

Collects all task-scoped data (company / assets / vulnerabilities / interfaces /
intel) into a single dict context for the renderer. Powers report generation.
"""

from __future__ import annotations

import math
from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.asset import Asset
from src.models.company import Company
from src.models.intel_document import IntelDocument
from src.models.interface import ApiInterface
from src.models.task import Task
from src.models.vulnerability import Vulnerability
from src.core.risk import calc_asset_risk, calc_company_risk, severity_counts


async def aggregate_task_data(db: AsyncSession, task_id: UUID) -> dict:
    """Aggregate all data for a task into a report context dict.

    Returns:
        {
          task, company, assets, vulnerabilities, interfaces, intel,
          asset_summary, vuln_summary, risk_score, ...
        }
    """
    task = await db.get(Task, task_id)
    if task is None:
        raise ValueError(f"Task {task_id} not found")

    # Company (linked via task.company_id; fall back to None)
    company = await db.get(Company, task.company_id) if task.company_id else None

    # Assets
    assets = (await db.execute(
        select(Asset).where(Asset.task_id == task_id).order_by(Asset.discovered_at.desc())
    )).scalars().all()

    # Vulnerabilities (via assets)
    asset_ids = [a.id for a in assets]
    vulns: list[Vulnerability] = []
    if asset_ids:
        vulns = list((await db.execute(
            select(Vulnerability).where(Vulnerability.asset_id.in_(asset_ids)).order_by(Vulnerability.discovered_at.desc())
        )).scalars().all())

    # Interfaces
    interfaces = (await db.execute(
        select(ApiInterface).where(ApiInterface.task_id == task_id).order_by(ApiInterface.crawled_at.desc())
    )).scalars().all() if hasattr(ApiInterface, 'task_id') else []

    # Intel documents
    intel = (await db.execute(
        select(IntelDocument).where(IntelDocument.task_id == task_id).order_by(IntelDocument.created_at.desc()).limit(50)
    )).scalars().all() if hasattr(IntelDocument, 'task_id') else []

    # ── Summaries ──
    asset_by_type: Counter = Counter(a.asset_type or "other" for a in assets)
    asset_by_risk: Counter = Counter((a.risk_level or "info") for a in assets)
    confirmed_assets = sum(1 for a in assets if a.confirmed)

    sev_counts = severity_counts(vulns)
    confirmed_vulns = sum(1 for v in vulns if getattr(v, "human_confirmed", False) or getattr(v, "confirmed", False))

    # Risk (A.7 formula)
    asset_risks: list[float] = []
    for aid in asset_ids:
        asset_vulns = [v for v in vulns if v.asset_id == aid]
        asset_risks.append(calc_asset_risk(asset_vulns))
    risk_score = calc_company_risk(asset_risks)

    return {
        "task": {
            "id": str(task.id),
            "company_name": task.company_name,
            "industry": task.industry,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "current_stage": getattr(task, "current_stage", None),
            "created_at": task.created_at.isoformat() if task.created_at else None,
        },
        "company": {
            "name": company.name if company else task.company_name,
            "credit_code": company.credit_code if company else None,
            "industry": company.industry if company else task.industry,
            "legal_person": company.legal_person if company else None,
            "website": company.website if company else None,
            "domains": company.domains if company else [],
        } if company else None,
        "assets": [
            {
                "id": str(a.id),
                "asset_type": a.asset_type,
                "domain": a.domain,
                "ip_address": a.ip_address,
                "port": a.port,
                "risk_level": a.risk_level,
                "confirmed": a.confirmed,
                "tech_stack": a.tech_stack or [],
                "open_ports": a.open_ports or [],
                "icp_entity": a.icp_entity,
                "waf_type": a.waf_type,
                "value_score": a.value_score,
            }
            for a in assets
        ],
        "vulnerabilities": [
            {
                "id": str(v.id),
                "title": getattr(v, "title", None) or getattr(v, "name", None) or "未命名漏洞",
                "severity": v.severity,
                "vuln_type": getattr(v, "vuln_type", None),
                "cvss_score": getattr(v, "cvss_score", None),
                "target": getattr(v, "target", None),
                "status": getattr(v, "status", None),
                "human_confirmed": getattr(v, "human_confirmed", False),
                "evidence": getattr(v, "evidence", None),
                "remediation": getattr(v, "remediation", None),
            }
            for v in vulns
        ],
        "interfaces": [
            {
                "id": str(i.id),
                "path": getattr(i, "path", None),
                "method": getattr(i, "method", None),
                "interface_type": getattr(i, "interface_type", None),
                "privilege_sensitive": getattr(i, "privilege_sensitive", False),
            }
            for i in interfaces
        ],
        "intel": [
            {"id": str(d.id), "title": getattr(d, "title", None), "source": getattr(d, "source", None)}
            for d in intel
        ],
        "summaries": {
            "asset_total": len(assets),
            "asset_confirmed": confirmed_assets,
            "asset_by_type": dict(asset_by_type),
            "asset_by_risk": dict(asset_by_risk),
            "vuln_total": len(vulns),
            "vuln_confirmed": confirmed_vulns,
            "vuln_by_severity": sev_counts,
            "interface_total": len(interfaces),
            "intel_total": len(intel),
            "risk_score": round(risk_score, 1),
        },
    }


def estimate_quality(ctx: dict) -> dict:
    """Heuristic quality score (0-1) based on data completeness.

    No extra LLM call — derives from data coverage. A real LLM-Judge can be
    plugged in later (A.7/S2 risk note).
    """
    s = ctx.get("summaries", {})
    asset_total = s.get("asset_total", 0)
    vuln_total = s.get("vuln_total", 0)
    confirmed_vulns = s.get("vuln_confirmed", 0)

    # completeness: data coverage (assets + vulns present)
    completeness = min(1.0, (asset_total / 10) * 0.5 + (vuln_total / 5) * 0.5)
    # accuracy: ratio of confirmed vulns
    accuracy = (confirmed_vulns / vuln_total) if vuln_total > 0 else (1.0 if vuln_total == 0 else 0.0)
    # readability: fixed (template-based rendering is readable)
    readability = 0.9
    # actionability: remediation present ratio
    vulns = ctx.get("vulnerabilities", [])
    with_remediation = sum(1 for v in vulns if v.get("remediation"))
    actionability = (with_remediation / vuln_total) if vuln_total > 0 else 1.0

    overall = round((completeness * 0.3 + accuracy * 0.3 + readability * 0.2 + actionability * 0.2), 2)
    return {
        "overall": overall,
        "accuracy": round(accuracy, 2),
        "completeness": round(completeness, 2),
        "readability": readability,
        "actionability": round(actionability, 2),
    }
