from typing import Any, TypedDict


class GlobalState(TypedDict, total=False):
    task_id: str
    company_name: str
    industry: str
    domains: list[str]
    ip_ranges: list[str]
    keywords: list[str]
    dsl_queries: list[dict[str, Any]]
    summary: str
    intel_documents: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    asset_search_result: dict[str, Any]
    asset_search_error: str
    asset_assess_result: dict[str, Any]
    asset_enrich_result: dict[str, Any]
    interfaces: list[dict[str, Any]]
    vulnerabilities: list[dict[str, Any]]
    reports: list[dict[str, Any]]
    current_stage: str
    errors: list[str]
    metadata: dict[str, Any]
