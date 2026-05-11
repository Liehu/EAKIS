#!/usr/bin/env python3
"""LangGraph 编排层端到端测试脚本.

运行方式:
    python scripts/test_orchestrator.py
    python scripts/test_orchestrator.py --phase intelligence  # 只测试情报采集阶段
    python scripts/test_orchestrator.py --verbose              # 详细输出
"""
import asyncio
import sys
from uuid import uuid4
from argparse import ArgumentParser

# Add project root to path
sys.path.insert(0, "/coding/EAKIS")

from src.orchestrator.graph import build_graph
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator-test")

# 阶段定义
PHASES = {
    "intelligence": ["datasource", "dsl_gen", "crawler", "summarizer", "keyword_gen"],
    "assets": ["asset_search", "asset_assess", "asset_enrich"],
    "interfaces": ["api_crawler", "api_static"],
    "pentest": ["test_gen", "test_exec", "vuln_judge"],
    "report": ["report_gen"],
}

ALL_NODES = []
for phase_nodes in PHASES.values():
    ALL_NODES.extend(phase_nodes)


class OrchestratorTester:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.graph = None
        self.task_id = None
        self.results = {}

    async def setup(self):
        """初始化测试环境"""
        logger.info("构建 LangGraph 编排图...")
        self.graph = build_graph()
        self.task_id = str(uuid4())
        logger.info(f"测试任务 ID: {self.task_id}")

    def create_initial_state(self, company_name: str = "编排层测试公司") -> GlobalState:
        """创建初始状态"""
        return {
            "task_id": self.task_id,
            "company_name": company_name,
            "industry": "fintech",
            "domains": ["example.com"],
            "keywords": ["支付网关", "API接口", "数据安全"],
            "current_stage": "",
            "errors": [],
            "metadata": {},
        }

    async def run_phase(self, phase: str, state: GlobalState) -> GlobalState:
        """运行指定阶段"""
        nodes = PHASES.get(phase, ALL_NODES)
        logger.info(f"执行阶段: {phase} (节点: {', '.join(nodes)})")

        config = {"configurable": {"thread_id": self.task_id}}
        final_state = state
        executed_nodes = []

        async for event in self.graph.astream(state, config):
            for node_name, node_output in event.items():
                if node_name in executed_nodes:
                    continue

                executed_nodes.append(node_name)
                logger.info(f"  ✓ 节点 {node_name} 完成")

                if self.verbose and node_output:
                    self._log_node_details(node_name, node_output)

                if "errors" in node_output and node_output["errors"]:
                    logger.warning(f"  ⚠ 节点 {node_name} 有错误: {node_output['errors']}")

                final_state = node_output

                # 检查是否到达目标阶段末尾
                if node_name == nodes[-1]:
                    break

        self.results[phase] = {
            "executed_nodes": executed_nodes,
            "errors": final_state.get("errors", []),
        }

        return final_state

    def _log_node_details(self, node_name: str, output: dict):
        """输出节点详细信息"""
        details = []
        if "metadata" in output and output["metadata"]:
            meta = output["metadata"]
            if "sources" in meta:
                details.append(f"    数据源: {len(meta['sources'])} 个")
            if "dsl_queries" in meta:
                details.append(f"    DSL查询: {len(meta['dsl_queries'])} 条")
        if "intel_documents" in output:
            details.append(f"    文档数: {len(output['intel_documents'])}")
        if "summary" in output:
            details.append(f"    摘要长度: {len(output['summary'])}")
        if "keywords" in output:
            details.append(f"    关键词: {len(output['keywords'])} 个")
        if "assets" in output:
            details.append(f"    资产: {len(output['assets'])} 个")
        if "interfaces" in output:
            details.append(f"    接口: {len(output['interfaces'])} 个")

        if details:
            for detail in details:
                logger.info(detail)

    async def run_full_pipeline(self):
        """运行完整流程"""
        state = self.create_initial_state()

        logger.info("=" * 60)
        logger.info("开始 LangGraph 编排层完整流程测试")
        logger.info("=" * 60)

        config = {"configurable": {"thread_id": self.task_id}}
        executed = []

        async for event in self.graph.astream(state, config):
            for node_name, node_output in event.items():
                if node_name in executed:
                    continue

                executed.append(node_name)
                logger.info(f"[{len(executed)}/{len(ALL_NODES)}] {node_name}")

                if self.verbose:
                    self._log_node_details(node_name, node_output)

                if "errors" in node_output and node_output["errors"]:
                    logger.warning(f"  错误: {node_output['errors']}")

        self.results["full"] = {
            "executed_nodes": executed,
            "errors": node_output.get("errors", []),
        }

        return node_output

    def print_summary(self, final_state: GlobalState):
        """打印测试总结"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("测试总结")
        logger.info("=" * 60)

        executed = self.results.get("full", {}).get("executed_nodes", [])
        errors = self.results.get("full", {}).get("errors", [])

        logger.info(f"执行节点数: {len(executed)}/{len(ALL_NODES)}")
        logger.info(f"错误数量: {len(errors)}")

        if errors:
            logger.warning("错误列表:")
            for err in errors:
                logger.warning(f"  - {err}")

        logger.info("")
        logger.info("关键指标:")
        metadata = final_state.get("metadata", {})
        logger.info(f"  数据源: {len(metadata.get('sources', []))} 个")
        logger.info(f"  DSL查询: {len(metadata.get('dsl_queries', []))} 条")
        logger.info(f"  文档数: {len(final_state.get('intel_documents', []))} 条")
        logger.info(f"  关键词: {len(final_state.get('keywords', []))} 个")
        logger.info(f"  资产: {len(final_state.get('assets', []))} 个")
        logger.info(f"  接口: {len(final_state.get('interfaces', []))} 个")
        logger.info(f"  漏洞: {len(final_state.get('vulnerabilities', []))} 个")

        logger.info("")
        if len(executed) == len(ALL_NODES) and not errors:
            logger.info("✓ 所有测试通过")
        else:
            logger.warning("⚠ 测试存在问题，请检查输出")


async def main():
    parser = ArgumentParser(description="LangGraph 编排层测试")
    parser.add_argument("--phase", choices=list(PHASES.keys()) + ["all"],
                       default="all", help="要测试的阶段")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="详细输出")
    parser.add_argument("--company", default="编排层测试公司",
                       help="目标公司名称")

    args = parser.parse_args()

    tester = OrchestratorTester(verbose=args.verbose)
    await tester.setup()

    if args.phase == "all":
        final_state = await tester.run_full_pipeline()
    else:
        state = tester.create_initial_state(args.company)
        final_state = await tester.run_phase(args.phase, state)

    tester.print_summary(final_state)


if __name__ == "__main__":
    asyncio.run(main())
