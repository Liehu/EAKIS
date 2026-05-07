from src.orchestrator.state import GlobalState

_STAGE_MAP: dict[str, str] = {
    "datasource": "dsl_gen",
    "dsl_gen": "crawler",
    "crawler": "summarizer",
    "summarizer": "keyword_gen",
    "keyword_gen": "asset_search",
    "asset_search": "asset_assess",
    "asset_assess": "asset_enrich",
    "asset_enrich": "api_crawler",
    "api_crawler": "test_gen",
    "test_gen": "test_exec",
    "test_exec": "vuln_judge",
    "vuln_judge": "report_gen",
    "report_gen": "__end__",
}


def route_by_stage(state: GlobalState) -> str:
    """Return the next pipeline stage based on *current_stage*."""
    current = state.get("current_stage", "")
    return _STAGE_MAP.get(current, "__end__")


def route_on_error(state: GlobalState) -> str:
    """Placeholder error router -- currently just advances the pipeline."""
    # Future: if state.get("errors"), route to "error_handler".
    return route_by_stage(state)


def route_by_asset_count(state: GlobalState) -> str:
    """If no assets were found, loop back to keyword_gen for expanded search."""
    assets = state.get("assets")
    if not assets:
        return "keyword_gen"
    return "asset_enrich"
