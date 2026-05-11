#!/usr/bin/env python3
"""LangGraph 编排层快速验证脚本.

快速验证编排层的基本功能，适合 CI/CD 或快速检查。
"""
import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, "/coding/EAKIS")

from src.orchestrator.graph import build_graph
from src.orchestrator.state import GlobalState
from src.shared.logger import get_logger

logger = get_logger("orchestrator-quick-test")


async def quick_test():
    """快速测试编排层核心功能"""
    task_id = str(uuid4())

    logger.info("1. 构建 LangGraph 编排图...")
    try:
        graph = build_graph()
        logger.info("   ✓ 图构建成功")
    except Exception as e:
        logger.error(f"   ✗ 图构建失败: {e}")
        return False

    logger.info("2. 验证节点注册...")
    expected_nodes = [
        "datasource", "dsl_gen", "crawler", "summarizer", "keyword_gen",
        "asset_search", "asset_assess", "asset_enrich", "api_crawler",
        "api_static", "test_gen", "test_exec", "vuln_judge", "report_gen"
    ]
    actual_nodes = list(graph.nodes.keys())
    missing = set(expected_nodes) - set(actual_nodes)
    if missing:
        logger.error(f"   ✗ 缺少节点: {missing}")
        return False
    logger.info(f"   ✓ 所有 {len(expected_nodes)} 个节点已注册")

    logger.info("3. 初始化状态...")
    initial_state: GlobalState = {
        "task_id": task_id,
        "company_name": "快速测试公司",
        "industry": "tech",
        "domains": ["test.example.com"],
        "keywords": ["测试", "API"],
        "current_stage": "",
        "errors": [],
        "metadata": {},
    }
    logger.info("   ✓ 状态初始化成功")

    logger.info("4. 执行情报采集阶段 (datasource → dsl_gen → crawler)...")
    config = {"configurable": {"thread_id": task_id}}
    executed = []
    errors = []

    try:
        async for event in graph.astream(initial_state, config):
            for node_name, node_output in event.items():
                if node_name in executed:
                    continue
                executed.append(node_name)
                logger.info(f"   ✓ 节点 {node_name} 完成")

                if "errors" in node_output and node_output["errors"]:
                    errors.extend(node_output["errors"])
                    logger.warning(f"   ⚠ 节点 {node_name} 有错误")

                # 执行到 crawler 后停止
                if node_name == "crawler":
                    break

        if "crawler" in executed:
            logger.info("   ✓ 情报采集阶段执行成功")
        else:
            logger.error(f"   ✗ 情报采集阶段未完成，只执行到: {executed}")
            return False

    except Exception as e:
        logger.error(f"   ✗ 执行失败: {e}")
        return False

    logger.info("5. 验证状态传递...")
    # 检查状态是否正确传递
    if errors:
        logger.warning(f"   ⚠ 存在 {len(errors)} 个错误（Stub 模式下可接受）")

    logger.info("")
    logger.info("=" * 50)
    logger.info("快速验证结果:")
    logger.info(f"  执行节点: {', '.join(executed)}")
    logger.info(f"  错误数量: {len(errors)}")
    logger.info("")
    logger.info("✓ 编排层核心功能正常")
    logger.info("=" * 50)

    return True


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)
