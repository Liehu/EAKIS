from langgraph.graph import END, StateGraph

from src.orchestrator.checkpointer import get_checkpointer
from src.orchestrator.nodes import (
    ApiCrawlerAgent,
    ApiStaticAgent,
    AssetAssessAgent,
    AssetEnrichAgent,
    AssetSearchAgent,
    CrawlerAgent,
    DatasourceAgent,
    DslGenAgent,
    KeywordGenAgent,
    ReportGenAgent,
    SummarizerAgent,
    TestExecAgent,
    TestGenAgent,
    VulnJudgeAgent,
)
from src.orchestrator.state import GlobalState


def build_graph() -> StateGraph:
    """Build and compile the full EAKIS pipeline graph."""
    graph = StateGraph(GlobalState)

    # -- instantiate nodes ----------------------------------------------------
    agents = {
        "datasource":   DatasourceAgent(),
        "dsl_gen":      DslGenAgent(),
        "crawler":      CrawlerAgent(),
        "summarizer":   SummarizerAgent(),
        "keyword_gen":  KeywordGenAgent(),
        "asset_search":  AssetSearchAgent(),
        "asset_assess":  AssetAssessAgent(),
        "asset_enrich":  AssetEnrichAgent(),
        "api_crawler":   ApiCrawlerAgent(),
        "api_static":    ApiStaticAgent(),
        "test_gen":      TestGenAgent(),
        "test_exec":     TestExecAgent(),
        "vuln_judge":    VulnJudgeAgent(),
        "report_gen":    ReportGenAgent(),
    }

    for name, agent in agents.items():
        graph.add_node(name, agent.run)

    # -- linear pipeline edges -----------------------------------------------
    pipeline = [
        "datasource",
        "dsl_gen",
        "crawler",
        "summarizer",
        "keyword_gen",
        "asset_search",
        "asset_assess",
        "asset_enrich",
        "api_crawler",
        "test_gen",
        "test_exec",
        "vuln_judge",
        "report_gen",
    ]

    graph.set_entry_point(pipeline[0])

    for src, dst in zip(pipeline, pipeline[1:]):
        graph.add_edge(src, dst)

    graph.add_edge(pipeline[-1], END)

    # -- compile with checkpointer -------------------------------------------
    return graph.compile(checkpointer=get_checkpointer())
