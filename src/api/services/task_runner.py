"""任务执行编排服务。

按任务模板的 config.modules 顺序执行各模块：
  M0 采集企业主体 → M1 情报采集 → M2 关键词生成 → M3 资产发现 → M4 接口爬取

每个模块调用对应的独立服务函数（复用 company_enrichment / intelligence / keywords），
实时更新 Task 的 status / current_stage / progress。

本次实现 M0/M1/M2/M3 四个模块：
  M3 走真实工具链（subfinder→dnsx→httpx→naabu），M4 仍预留。
PD 工具二进制需在 PATH 上（go install 到 $(go env GOPATH)/bin，见 docs/PLAN_真实能力落地_v1.md）。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import Company
from src.models.intel_document import IntelDocument
from src.models.keyword import Keyword
from src.models.task import Task
from src.shared.logger import get_logger

logger = get_logger("task_runner")


def _to_dt(val) -> datetime | None:
    """将字符串/None 转为 datetime（SQLite DateTime 列不接受字符串）。"""
    if val is None or isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return None


async def _run_m0_enrich(db: AsyncSession, task: Task, company: Company | None) -> None:
    """M0：采集企业主体（云图）。"""
    if company is None:
        logger.warning("M0 跳过：任务 %s 无关联企业", task.id)
        return
    cfg = task.config or {}
    # 延迟导入避免循环依赖（companies router 依赖 task 模型）
    from src.api.routers.companies import _do_enrich
    await _do_enrich(
        db, company,
        provider=cfg.get("enrich_provider", "yuntu"),
        depth=cfg.get("enrich_depth", cfg.get("target_depth", 3)),
        holding_min=cfg.get("holding_min", 50.0),
        strategy="auto_fill",
    )
    logger.info("M0 完成：企业 %s 采集", company.name)


async def _run_m1_intelligence(db: AsyncSession, task: Task, company: Company | None) -> None:
    """M1：情报采集（IntelligenceModule → IntelDocument 持久化）。"""
    from src.intelligence.module import IntelligenceModule
    from src.intelligence.models import SourceCategory

    cfg = task.config or {}
    company_name = company.name if company else task.company_name
    industry = company.industry if company else task.industry
    domains = company.domains if company else None
    aliases = (company.aliases if company else task.company_aliases) or []

    # enabled_categories
    enabled_cats_str = cfg.get("intel_categories", ["news", "official", "legal"])
    cat_map = {c.value: c for c in SourceCategory}
    enabled_categories = [cat_map[c] for c in enabled_cats_str if c in cat_map] or None

    module = IntelligenceModule()
    task_id_str = str(task.id)
    await module.run(
        task_id=task_id_str,
        company_name=company_name,
        industry=industry,
        domains=domains,
        keywords=list(aliases),
        enabled_categories=enabled_categories,
    )

    # 持久化 CleanedDocument → IntelDocument
    # 注意：get_documents() 返回 list[dict]，不是 CleanedDocument 对象
    docs = module.get_documents()
    saved = 0
    for doc in docs:
        checksum = doc.get("checksum") if isinstance(doc, dict) else getattr(doc, "checksum", "")
        if not checksum:
            continue
        existing = (await db.execute(
            select(IntelDocument).where(IntelDocument.checksum == checksum).limit(1)
        )).scalar_one_or_none()
        if existing is None:
            db.add(IntelDocument(
                task_id=task.id,
                source_type=doc.get("source_type") if isinstance(doc, dict) else doc.source_type.value,
                source_name=doc.get("source_name") if isinstance(doc, dict) else doc.source_name,
                source_url=doc.get("source_url") if isinstance(doc, dict) else doc.source_url,
                content=doc.get("content") if isinstance(doc, dict) else doc.content,
                quality_score=doc.get("quality_score", 0.0) if isinstance(doc, dict) else doc.quality_score,
                published_at=_to_dt(doc.get("published_at") if isinstance(doc, dict) else doc.published_at),
                entities=doc.get("entities", []) if isinstance(doc, dict) else doc.entities,
                checksum=checksum,
            ))
            saved += 1
    await db.commit()
    logger.info("M1 完成：情报采集 %d 条文档（新存 %d）", len(docs), saved)


async def _run_m2_keywords(db: AsyncSession, task: Task, company: Company | None) -> None:
    """M2：关键词生成（KeywordModule pipeline → Keyword 持久化 + company_id 关联）。"""
    from src.keywords.module import KeywordModule

    company_name = company.name if company else task.company_name
    industry = company.industry if company else task.industry
    module = KeywordModule(industry=industry)
    result = await module.run_pipeline(
        session=db, task_id=task.id, company_name=company_name, industry=industry,
    )

    # populate company_id：给本任务新生成的关键词填上企业归属
    if company is not None:
        keywords = (await db.execute(
            select(Keyword).where(Keyword.task_id == task.id, Keyword.company_id.is_(None))
        )).scalars().all()
        for kw in keywords:
            kw.company_id = company.id
        await db.commit()
    logger.info("M2 完成：关键词生成 %s", result)


async def _run_m3_asset_discovery(db: AsyncSession, task: Task, company: Company | None) -> None:
    """M3：资产发现（云图企业域名 → 真实资产落库）。

    链路：subfinder/crt.sh 子域名 → dnsx 解析 → httpx 存活 → naabu 端口，
    结果经 persistence.upsert_assets 幂等写入 Asset 表。
    """
    from src.asset_discovery.services.domain_pipeline import run_domain_pipeline
    from src.asset_discovery.services.persistence import upsert_assets
    from src.asset_discovery.services.tool_client import ToolBackedSearchClient

    cfg = task.config or {}
    seed_domains = []
    if company is not None:
        seed_domains = list(company.domains or [])
        # email_domains 形如 mail.example.com 的裸域也并入
        seed_domains += [d for d in (company.email_domains or []) if d not in seed_domains]
    if not seed_domains:
        logger.warning("M3 跳过：企业 %s 无种子域名", task.company_name)
        return

    client = ToolBackedSearchClient()
    assets, errors = await run_domain_pipeline(
        client, seed_domains,
        enable_portscan=cfg.get("asset_portscan", True),
    )
    for e in errors:
        logger.warning("M3 资产发现降级：%s", e)

    stats = await upsert_assets(db, task, assets, company=company)
    logger.info(
        "M3 完成：种子域名 %d 个 → 资产 %d 条（新增 %d / 更新 %d）",
        len(seed_domains), len(assets), stats["inserted"], stats["updated"],
    )


async def _backfill_icp(db: AsyncSession, task: Task, company: Company | None) -> int:
    """ICP 备案回填：查询企业域名备案 → 回填 Company.icp_* 与关联 Asset.icp_*。

    返回成功查询的域名数。查询失败不阻塞任务（记录日志）。
    """
    import hashlib

    from src.intelligence.scrapers.icp_scraper import query_icp
    from src.models.asset import Asset

    if company is None or not company.domains:
        return 0

    # 主域名优先，最多查 5 个
    domains = list(dict.fromkeys(company.domains))[:5]
    success = 0
    for domain in domains:
        info = await query_icp(domain)
        if info is None:
            continue
        success += 1

        # 1) 回填 Company（首个有效结果）
        if not company.icp_entity and (info.get("icp_entity") or info.get("icp_number")):
            company.icp_number = info.get("icp_number")
            company.icp_entity = info.get("icp_entity")

        # 2) 回填匹配后缀的 Asset
        assets = (await db.execute(
            select(Asset).where(Asset.task_id == task.id)
        )).scalars().all()
        for a in assets:
            if a.domain and (a.domain == domain or a.domain.endswith(f".{domain}")):
                a.icp_entity = info.get("icp_entity") or a.icp_entity
                if info.get("icp_number"):
                    a.icp_verified = True

        # 3) 备案结果也存为 IntelDocument（checksum 去重）
        content = (
            f"ICP备案查询：{info['domain']} 备案号 {info.get('icp_number') or '未知'}，"
            f"备案主体 {info.get('icp_entity') or '未知'}（来源 {info['provider']}）"
        )
        checksum = hashlib.sha256(content.encode()).hexdigest()
        existing = (await db.execute(
            select(IntelDocument).where(IntelDocument.checksum == checksum).limit(1)
        )).scalar_one_or_none()
        if existing is None:
            db.add(IntelDocument(
                task_id=task.id, source_type="legal", source_name="ICP备案查询",
                source_url=info["provider"], content=content,
                quality_score=0.9, entities=[info.get("icp_entity")] if info.get("icp_entity") else [],
                checksum=checksum,
            ))
        await db.commit()
    if success:
        logger.info("ICP 回填完成：%d/%d 个域名（企业 %s）", success, len(domains), company.name)
    return success


async def _run_m5_vuln_scan(db: AsyncSession, task: Task, company: Company | None) -> dict:
    """M5：漏洞扫描（nuclei 扫 authorized_scope 内已发现资产 → Vulnerability 落库）。

    仅扫描任务授权范围内、协议为 http/https 的存活资产；发现以 detected
    （candidate）状态入库并携带原始 evidence，待 vuln_judge/人工确认。
    """
    from src.models.asset import Asset
    from src.models.vulnerability import Vulnerability
    from src.pentest.scanner import NucleiScanner, findings_to_vulnerability_rows

    assets = (await db.execute(
        select(Asset).where(Asset.task_id == task.id)
    )).scalars().all()

    # 只扫 http/https 存活资产（M3 中 httpx 确认的 web 资产）
    scan_targets: list[str] = []
    asset_id_map: dict[str, object] = {}
    for a in assets:
        if not (a.domain or a.ip_address):
            continue
        if a.protocol not in ("http", "https"):
            continue
        scheme = a.protocol if a.protocol in ("http", "https") else "https"
        host = a.domain or a.ip_address
        url = f"{scheme}://{host}" + (f":{a.port}" if a.port and a.port not in (80, 443) else "")
        scan_targets.append(url)
        asset_id_map[url] = a.id
        if a.domain:
            asset_id_map.setdefault(a.domain, a.id)

    if not scan_targets:
        logger.info("M5 跳过：任务 %s 无可扫描的 http 资产", task.id)
        return {"scanned": 0, "inserted": 0}

    cfg = task.config or {}
    scanner = NucleiScanner(
        severity_filter=cfg.get("vuln_severity_filter"),  # 如 "medium,high,critical"
        max_targets=cfg.get("vuln_max_targets", 50),
    )
    report = await scanner.scan_targets(scan_targets, task.authorized_scope)

    rows = findings_to_vulnerability_rows(report.findings, asset_id_map)
    # 去重：同资产同模板不重复入库
    existing = (await db.execute(
        select(Vulnerability.asset_id, Vulnerability.title).where(Vulnerability.task_id == task.id)
    )).all()
    seen = {(str(a), t) for a, t in existing}
    inserted = 0
    for row in rows:
        key = (str(row["asset_id"]), row["title"])
        if key in seen:
            continue
        seen.add(key)
        db.add(Vulnerability(task_id=task.id, **row))
        inserted += 1
    await db.commit()
    logger.info(
        "M5 完成：扫描 %d 目标 / %d 发现 / 新增漏洞 %d（status=%s, errors=%d）",
        report.targets_scanned, len(report.findings), inserted,
        report.status, len(report.errors),
    )
    for e in report.errors[:5]:
        logger.warning("M5 扫描问题：%s", e)
    return {"scanned": report.targets_scanned, "inserted": inserted, "status": report.status}


async def run_task_pipeline(db: AsyncSession, task: Task) -> dict:
    """执行任务管线：LangGraph 企业管线图（M0-M6 + 持久化 checkpoint）。

    S-D 起编排收敛到 src/orchestrator/company_graph.py 的 LangGraph 图，
    本函数只负责取关联企业并调用图入口；返回 {stages_run, errors, completed, report_id}。
    """
    company = None
    if task.company_id:
        company = await db.get(Company, task.company_id)

    from src.orchestrator.company_graph import run_company_pipeline
    return await run_company_pipeline(db, task, company)
