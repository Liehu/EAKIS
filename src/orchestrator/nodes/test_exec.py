"""PENTEST-EXECUTOR node — nuclei 漏洞扫描（真实工具集成）。

对 state 中的已发现资产执行 nuclei 扫描（授权边界校验前置），
结果（带原始 evidence 的 finding）写入 state["vuln_findings"]，
由下游 vuln_judge 节点做误报分诊与状态判定。
"""
from typing import Any

from src.orchestrator.nodes.base import AgentBase
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator")


class TestExecAgent(AgentBase):
    """Executes vulnerability scanning (nuclei) against discovered assets."""

    def __init__(self, llm_client: Any = None) -> None:
        super().__init__(name="pentest-executor", llm_client=llm_client)

    async def run(self, state: GlobalState) -> GlobalState:
        task_id = state.get("task_id", "unknown")
        state["current_stage"] = "pentest-executor"

        # 目标来源：state["asset_urls"]（asset_search/enrich 节点产出）或显式传入
        targets = state.get("asset_urls") or []
        authorized_scope = state.get("authorized_scope")

        if not targets:
            logger.warning(
                "pentest-executor: 无扫描目标（state.asset_urls 为空），跳过 task=%s",
                task_id, extra={"task_id": task_id},
            )
            state["vuln_findings"] = []
            return state

        from src.pentest.scanner import NucleiScanner

        scanner = NucleiScanner()
        report = await scanner.scan_targets(targets, authorized_scope)

        if report.status == "unavailable":
            # 工具缺失：不产假数据，记入 state 供前端/报告展示能力缺口
            logger.error(
                "pentest-executor: nuclei 不可用 (%s)", report.errors,
                extra={"task_id": task_id},
            )
            state["pipeline_errors"] = (state.get("pipeline_errors") or []) + [
                f"vuln_scan: {e}" for e in report.errors
            ]
        state["vuln_findings"] = [
            {
                "template_id": f.template_id,
                "title": f.title,
                "severity": f.severity,
                "matched_url": f.matched_url,
                "cvss_score": f.cvss_score,
                "evidence": f.evidence,
            }
            for f in report.findings
        ]
        state["scan_summary"] = {
            "targets_scanned": report.targets_scanned,
            "findings": len(report.findings),
            "status": report.status,
            "errors": report.errors[:10],
        }
        logger.info(
            "pentest-executor: %d 目标 / %d 发现（task=%s）",
            report.targets_scanned, len(report.findings), task_id,
            extra={"task_id": task_id},
        )
        return state
