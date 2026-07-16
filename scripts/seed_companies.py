"""S1 seed: backfill Company entities from existing tasks and link assets.

This bridges the legacy Task.company_name (string) world to the new Company
entity model (ROADMAP A.1). Idempotent: safe to re-run.

What it does:
  1. Ensures a default Organization exists (slug from settings).
  2. For each distinct task.company_name with no company_id, creates a Company
     and links the task (and its assets) to it via company_id.
  3. Creates one sample parent→child CompanyRelation (holding) for the first
     company, to demonstrate A.1 graph traversal.
  4. Computes a RiskHistory snapshot for each company (A.7).

Usage:
    python3 scripts/seed_companies.py
"""

from __future__ import annotations

import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.core.risk import calc_asset_risk, calc_company_risk, severity_counts
from src.core.settings import get_settings
from src.models import (
    Asset, Company, CompanyRelation, Organization, RiskHistory, Task, Vulnerability,
)
from src.models.database import SessionLocal

settings = get_settings()


def _default_org(session: Session) -> Organization:
    org = session.scalar(select(Organization).where(Organization.slug == settings.default_org_slug))
    if org is None:
        org = Organization(
            name="默认组织",
            slug=settings.default_org_slug,
            plan="enterprise",
            max_teams=50,
            max_members=200,
        )
        session.add(org)
        session.flush()
    return org


def run() -> None:
    session = SessionLocal()
    try:
        org = _default_org(session)
        print(f"[seed] org: {org.slug} ({org.id})")

        # Group tasks by company_name.
        tasks = session.scalars(select(Task)).all()
        by_name: dict[str, list[Task]] = defaultdict(list)
        for t in tasks:
            by_name[t.company_name].append(t)

        if not by_name:
            print("[seed] no tasks found — nothing to backfill. Run seed_mock_data.py first.")
            return

        created_or_reused = 0
        for name, name_tasks in by_name.items():
            # Skip tasks already linked to a company.
            unlinked = [t for t in name_tasks if t.company_id is None]
            if not unlinked:
                continue
            # Reuse an existing Company with this name in this org, else create.
            company = session.scalar(
                select(Company).where(Company.org_id == org.id, Company.name == name)
            )
            if company is None:
                first = unlinked[0]
                company = Company(
                    org_id=org.id,
                    name=name,
                    aliases=first.company_aliases,
                    industry=first.industry,
                    domains=list(first.authorized_scope.get("domains", []) or []),
                    ip_ranges=list(first.authorized_scope.get("ip_ranges", []) or []),
                    data_source="legacy_backfill",
                )
                session.add(company)
                session.flush()
                created_or_reused += 1
                print(f"[seed] created company: {company.name} ({company.id})")
            else:
                print(f"[seed] reused company: {company.name} ({company.id})")

            # Link tasks + their assets.
            for t in unlinked:
                t.company_id = company.id
                session.scalars(select(Asset).where(Asset.task_id == t.id)).unique().all()
                assets = session.scalars(select(Asset).where(Asset.task_id == t.id)).all()
                for a in assets:
                    a.company_id = company.id
                print(f"   ↳ task {t.id} + {len(assets)} assets linked")

        # Sample relation: if ≥2 companies, mark the 2nd as a subsidiary of the 1st (holding 100%).
        companies = session.scalars(
            select(Company).where(Company.org_id == org.id).order_by(Company.created_at)
        ).all()
        if len(companies) >= 2:
            parent, child = companies[0], companies[1]
            existing = session.scalar(
                select(CompanyRelation).where(
                    CompanyRelation.parent_company_id == parent.id,
                    CompanyRelation.child_company_id == child.id,
                    CompanyRelation.relation_type == "holding",
                )
            )
            if existing is None:
                session.add(CompanyRelation(
                    parent_company_id=parent.id, child_company_id=child.id,
                    relation_type="holding", holding_ratio=100.0, data_source="seed_sample",
                ))
                print(f"[seed] sample relation: {parent.name} →holding(100%)→ {child.name}")

        # Risk snapshots (A.7) — one per company (requires at least one linked task).
        for c in companies:
            company_task = session.scalars(select(Task).where(Task.company_id == c.id)).first()
            if company_task is None:
                print(f"[seed] skip risk snapshot for {c.name}: no linked task")
                continue
            asset_ids = [a.id for a in session.scalars(select(Asset).where(Asset.company_id == c.id)).all()]
            asset_risks: list[float] = []
            all_vulns: list[Vulnerability] = []
            for aid in asset_ids:
                vulns = session.scalars(select(Vulnerability).where(Vulnerability.asset_id == aid)).all()
                all_vulns.extend(vulns)
                asset_risks.append(calc_asset_risk(vulns))
            risk_score = calc_company_risk(asset_risks)
            session.add(RiskHistory(
                company_id=c.id,
                task_id=company_task.id,
                risk_score=risk_score,
                asset_count=len(asset_ids),
                vuln_count=len(all_vulns),
                by_severity=severity_counts(all_vulns),
                snapshot_at=datetime.now(timezone.utc),
            ))
            print(f"[seed] risk snapshot: {c.name} score={risk_score:.1f} assets={len(asset_ids)} vulns={len(all_vulns)}")

        session.commit()
        print(f"[seed] done. companies created/reused: {created_or_reused}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
