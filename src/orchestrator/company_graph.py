"""企业级全流程 LangGraph 编排图（S-D）。

将 M0-M6 各模块串联为一张图，替代 task_runner 中手工 for 循环：
  M0 云图采集企业主体 → M1 情报采集(+ICP回填) → M2 关键词 → M3 资产发现
  → M4 接口爬取(预留) → M5 漏洞扫描(nuclei) → M6 报告生成

设计要点（借鉴 CyberStrikeAI checkpoint / muteki 事件流）：
  - 按任务 config.modules 动态构建节点链，未启用的模块不进图
  - AsyncSqliteSaver 持久化 checkpoint（thread_id=task.id），失败任务可从断点续跑
  - 每个节点负责更新 Task.status/current_stage/progress，异常写入 state.errors
    不中断整体管线（单模块失败其余模块继续，最终按完成度判定任务状态）
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.shared.logger import get_logger

logger = get_logger("orchestrator.company_graph")

# 模块 → (节点名, 阶段名)
MODULE_STAGES: dict[str, tuple[str, str]] = {
    "M0": ("m0_enrich", "company_enrich"),
    "M1": ("m1_intel", "intelligence"),
    "M2": ("m2_keywords", "keyword_gen"),
    "M3": ("m3_assets", "asset_discovery"),
    "M4": ("m4_api", "api_crawl"),
    "M5": ("m5_vuln", "vuln_scan"),
    "M6": ("m6_report", "report_gen"),
}


class CompanyState(TypedDict, total=False):
    task_id: str
    modules: list[str]
    completed: list[str]
    errors: list[dict]
    report_id: str | None


def build_company_graph(
    db: Any,
    task: Any,
    company: Any,
    checkpoint_saver: Any = None,
) -> Any:
    """构建企业管线图。节点闭包持有 db/task/company，复用 task_runner 的模块实现。"""
    from src.api.services import task_runner

    modules = [m for m in (task.config or {}).get("modules", ["M0", "M1", "M2"]) if m in MODULE_STAGES]
    # M6 兜底：modules 未显式包含 M6 但 auto_report 开启时追加
    if (task.config or {}).get("auto_report") and "M6" not in modules:
        modules.append("M6")

    graph = StateGraph(CompanyState)

    def _make_node(mod: str):
        node_name, stage = MODULE_STAGES[mod]

        async def _node(state: CompanyState) -> CompanyState:
            task.current_stage = stage
            await db.commit()
            try:
                if mod == "M0":
                    await task_runner._run_m0_enrich(db, task, company)
                elif mod == "M1":
                    await task_runner._run_m1_intelligence(db, task, company)
                    try:
                        await task_runner._backfill_icp(db, task, company)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("ICP 回填失败（不阻塞）: %s", exc)
                elif mod == "M2":
                    await task_runner._run_m2_keywords(db, task, company)
                elif mod == "M3":
                    await task_runner._run_m3_asset_discovery(db, task, company)
                elif mod == "M4":
                    logger.info("M4 接口爬取（预留，静态分析实现待接入图）")
                elif mod == "M5":
                    await task_runner._run_m5_vuln_scan(db, task, company)
                elif mod == "M6":
                    report_id = await _generate_report(db, task)
                    state["report_id"] = report_id
                completed = state.get("completed") or []
                if mod not in completed:  # 断点续跑可能重放节点，防重复
                    completed = completed + [mod]
                state["completed"] = completed
            except Exception as exc:  # noqa: BLE001
                logger.error("模块 %s 执行失败: %s", mod, exc)
                state["errors"] = (state.get("errors") or []) + [{"module": mod, "error": str(exc)}]
            # 进度按已完成（去重）节点数推进，钳制到 [0,1]（DB CHECK 约束）
            task.progress = min(1.0, round(
                len(set(state.get("completed") or [])) / max(1, len(modules)), 2))
            try:
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                logger.error("进度落库失败（回滚后继续）: %s", exc)
                await db.rollback()
            return state

        return node_name, _node

    # 动态接线：线性链 START → m0 → m1 → ... → END
    prev = "__start__"
    for mod in modules:
        node_name, fn = _make_node(mod)
        graph.add_node(node_name, fn)
        if prev == "__start__":
            graph.set_entry_point(node_name)
        else:
            graph.add_edge(prev, node_name)
        prev = node_name
    if prev == "__start__":
        graph.set_entry_point(END)  # 空模块集：直接结束
    else:
        graph.add_edge(prev, END)

    compiled = graph.compile(checkpointer=checkpoint_saver)
    return compiled, modules


async def _generate_report(db: Any, task: Any) -> str | None:
    """M6：创建 Report 行并同步生成（聚合→渲染→评分→落库）。"""
    from src.models.report import Report
    from src.reporting.worker import generate_report_task

    report = Report(
        task_id=task.id, status="generating",
        template=(task.config or {}).get("report_template", "standard"),
        language="zh-CN",
    )
    db.add(report)
    await db.flush()
    await generate_report_task(db, report.id, task.id)
    await db.commit()
    logger.info("M6 完成：报告 %s", report.id)
    return str(report.id)


async def run_company_pipeline(db: Any, task: Any, company: Any = None) -> dict:
    """企业管线入口：构建图 → 执行 → 更新 Task 终态。

    返回 {stages_run, errors, completed, report_id}。
    """
    task.status = "running"
    task.started_at = datetime.now(UTC)
    task.progress = 0.0
    await db.commit()

    # 持久化 checkpoint：开发 sqlite 文件（生产可换 PostgresSaver）
    from langgraph.checkpoint.memory import MemorySaver

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        async with AsyncSqliteSaver.from_conn_string(".langgraph_checkpoints.db") as saver:
            compiled, modules = build_company_graph(db, task, company, saver)
            state: CompanyState = await compiled.ainvoke(
                {"task_id": str(task.id), "modules": modules},
                config={"configurable": {"thread_id": f"task-{task.id}"}},
            )
    except Exception as exc:  # noqa: BLE001
        # SqliteSaver 不可用（或图执行基础设施异常）时回退内存 checkpoint 重跑
        if "SqliteSaver" in str(exc) or "checkpointer" in str(exc):
            logger.warning("SqliteSaver 不可用，回退内存 checkpoint: %s", exc)
        else:
            logger.warning("持久化 checkpoint 执行异常，回退内存重跑: %s", exc)
        saver = MemorySaver()
        compiled, modules = build_company_graph(db, task, company, saver)
        state = await compiled.ainvoke(
            {"task_id": str(task.id), "modules": modules},
            config={"configurable": {"thread_id": f"task-{task.id}"}},
        )

    completed = state.get("completed") or []
    errors = state.get("errors") or []
    task.completed_at = datetime.now(UTC)
    task.progress = 1.0
    task.current_stage = "done"
    task.status = "failed" if errors and not completed else "completed"
    await db.commit()

    return {
        "stages_run": completed,
        "errors": errors,
        "completed": task.status,
        "report_id": state.get("report_id"),
    }
