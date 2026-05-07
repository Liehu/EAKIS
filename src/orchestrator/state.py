from typing import Any, TypedDict


class GlobalState(TypedDict, total=False):
    task_id: str
    company_name: str
    industry: str
    domains: list[str]
    keywords: list[str]
    summary: str
    intel_documents: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    interfaces: list[dict[str, Any]]
    vulnerabilities: list[dict[str, Any]]
    reports: list[dict[str, Any]]
    current_stage: str
    errors: list[str]
    metadata: dict[str, Any]
