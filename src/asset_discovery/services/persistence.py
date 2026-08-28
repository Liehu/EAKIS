"""EnrichedAsset → Asset 幂等落库。

按 (task_id, domain, port) / (task_id, ip, port) 唯一约束 upsert：
已存在的资产生效 last_seen_at、miss_count=0，并合入新证据（端口/技术栈/置信度取大）；
新资产插入。多来源命中同一 key 时提升 confidence_score（来源融合）。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.asset import Asset
from src.models.company import Company
from src.models.task import Task

logger = logging.getLogger("eakis.asset_discovery.persistence")


def _merge_confidence(old: float | None, new: float | None) -> float | None:
    """多来源命中：来源数加权提升置信度（多来源同 key 至少 +0.05，封顶 1.0）。"""
    if old is None:
        return new
    if new is None:
        return old
    return min(1.0, max(old, new) + 0.05)


async def upsert_assets(
    db: AsyncSession,
    task: Task,
    asset_dicts: list[dict],
    company: Company | None = None,
) -> dict:
    """将 module.get_assets() 的 dict 形式资产幂等写库。返回 {inserted, updated}。"""
    inserted = updated = skipped = 0
    now = datetime.now(UTC)

    for d in asset_dicts:
        domain = (d.get("domain") or None) or None
        ip = d.get("ip_address") or None
        port = d.get("port")

        if not domain and not ip:
            skipped += 1
            continue

        conds = []
        if domain and port:
            conds.append(and_(Asset.domain == domain, Asset.port == port))
        if ip and port:
            conds.append(and_(Asset.ip_address == ip, Asset.port == port))
        if domain and not ip:
            conds.append(Asset.domain == domain)
        if not conds:
            skipped += 1
            continue

        existing = (await db.execute(
            select(Asset).where(Asset.task_id == task.id, or_(*conds)).limit(1)
        )).scalar_one_or_none()

        open_ports = d.get("open_ports") or ([port] if port else [])
        tech = d.get("tech_stack") or []

        if existing is not None:
            existing.last_seen_at = now
            existing.miss_count = 0
            existing.confidence_score = _merge_confidence(
                existing.confidence_score, d.get("confidence"))
            if domain:
                existing.domain = domain
            if ip:
                existing.ip_address = ip
            if port:
                existing.port = port
            merged_ports = sorted(set((existing.open_ports or []) + open_ports))
            existing.open_ports = merged_ports
            merged_tech = sorted(set((existing.tech_stack or []) + tech))
            existing.tech_stack = merged_tech or existing.tech_stack
            if d.get("icp_entity"):
                existing.icp_entity = d["icp_entity"]
                existing.icp_verified = True
            if d.get("cert_info"):
                existing.cert_info = d["cert_info"]
            updated += 1
        else:
            db.add(Asset(
                task_id=task.id,
                company_id=company.id if company else task.company_id,
                domain=domain,
                ip_address=ip,
                port=port,
                protocol=d.get("protocol") or "https",
                asset_type=d.get("asset_type") or "domain",
                confidence_score=d.get("confidence"),
                icp_verified=bool(d.get("icp_verified")),
                icp_entity=d.get("icp_entity"),
                tech_stack=tech,
                cert_info=d.get("cert_info"),
                open_ports=open_ports,
                risk_level=d.get("risk_level") or "info",
                confirmed=bool(d.get("confirmed")),
                notes=d.get("notes"),
                status="confirmed" if d.get("confirmed") else "discovered",
                last_seen_at=now,
            ))
            inserted += 1

    await db.commit()
    logger.info(
        "资产落库完成 task=%s: 新增 %d / 更新 %d / 跳过 %d",
        task.id, inserted, updated, skipped,
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
