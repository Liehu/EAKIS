"""S-D 企业管线 LangGraph 编排端到端测试。

stub 掉外部依赖模块（云图/情报/关键词/资产/漏洞），验证：
  - 按 config.modules 顺序执行、未启用模块不进图
  - 单模块失败不中断管线，终态按完成度判定
  - M6 真实生成报告（聚合→渲染→落库）
  - Task 进度/阶段实时更新
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.models.organization import Organization
from src.models.company import Company
from src.models.report import Report
from src.models.task import Task
from src.orchestrator.company_graph import build_company_graph, run_company_pipeline


@pytest.fixture
async def task_company(async_session):
    org_id = uuid.uuid4()
    async_session.add(Organization(id=org_id, name="t", slug=f"t-{org_id.hex[:8]}"))
    await async_session.flush()
    company = Company(org_id=org_id, name="示例科技", domains=["example.com"])
    async_session.add(company)
    await async_session.flush()
    task = Task(
        company_id=company.id, company_name="示例科技", status="pending",
        config={"modules": ["M0", "M1", "M2", "M3", "M4", "M5", "M6"]},
        authorized_scope={"domains": ["example.com"]},
    )
    async_session.add(task)
    await async_session.commit()
    return task, company


@pytest.mark.asyncio
async def test_full_pipeline_order_and_report(monkeypatch, async_session, task_company):
    task, company = task_company
    calls: list[str] = []

    from src.api.services import task_runner

    for mod, fn in [
        ("M0", "_run_m0_enrich"), ("M1", "_run_m1_intelligence"),
        ("M2", "_run_m2_keywords"), ("M3", "_run_m3_asset_discovery"),
        ("M5", "_run_m5_vuln_scan"),
    ]:
        async def _noop(db, t, c, _fn=fn):
            calls.append(_fn)
        monkeypatch.setattr(task_runner, fn, _noop)
    async def _no_icp(db, t, c):
        calls.append("icp")
    monkeypatch.setattr(task_runner, "_backfill_icp", _no_icp)

    result = await run_company_pipeline(async_session, task, company)

    # 全模块按序执行
    assert result["stages_run"] == ["M0", "M1", "M2", "M3", "M4", "M5", "M6"]
    assert calls == ["_run_m0_enrich", "_run_m1_intelligence", "icp",
                     "_run_m2_keywords", "_run_m3_asset_discovery", "_run_m5_vuln_scan"]
    assert result["errors"] == []
    assert result["report_id"] is not None

    # 终态
    await async_session.refresh(task)
    assert task.status == "completed"
    assert task.progress == 1.0
    assert task.current_stage == "done"
    assert task.completed_at is not None

    # M6 真实生成报告（空数据聚合也应产出 completed 报告）
    reports = (await async_session.execute(
        select(Report).where(Report.task_id == task.id))).scalars().all()
    assert len(reports) == 1
    assert reports[0].status in ("completed", "ready", "generated") or reports[0].content is not None


@pytest.mark.asyncio
async def test_module_failure_does_not_break_pipeline(monkeypatch, async_session, task_company):
    task, company = task_company
    task.config = {"modules": ["M1", "M2", "M6"]}
    await async_session.commit()

    from src.api.services import task_runner

    async def boom(db, t, c):
        raise RuntimeError("情报采集炸了")
    monkeypatch.setattr(task_runner, "_run_m1_intelligence", boom)
    monkeypatch.setattr(task_runner, "_backfill_icp", boom)

    result = await run_company_pipeline(async_session, task, company)
    # M1 失败但 M2/M6 继续
    assert "M2" in result["stages_run"] and "M6" in result["stages_run"]
    assert any(e["module"] == "M1" for e in result["errors"])
    await async_session.refresh(task)
    assert task.status == "completed"  # 有完成模块 → completed（错误记录在 errors）


@pytest.mark.asyncio
async def test_disabled_modules_not_in_graph(monkeypatch, async_session, task_company):
    task, company = task_company
    task.config = {"modules": ["M2"]}
    await async_session.commit()

    compiled, modules = build_company_graph(async_session, task, company)
    assert modules == ["M2"]
    node_names = set(compiled.get_graph().nodes.keys())
    assert "m2_keywords" in node_names
    assert "m5_vuln" not in node_names and "m6_report" not in node_names


@pytest.mark.asyncio
async def test_auto_report_appends_m6(monkeypatch, async_session, task_company):
    task, company = task_company
    task.config = {"modules": ["M2"], "auto_report": True}
    await async_session.commit()

    _, modules = build_company_graph(async_session, task, company)
    assert modules == ["M2", "M6"]
