from __future__ import annotations

import logging
from dataclasses import dataclass, field

import yaml

from src.core.config_paths import ENGINES_YAML

logger = logging.getLogger("eakis.intelligence.engine_specs")

SPECS_FILE = ENGINES_YAML


@dataclass
class EnginePagination:
    param: str = "page"
    size_param: str | None = None
    default_size: int = 100


@dataclass
class EngineSpec:
    name: str
    display_name: str
    search_url: str
    auth_type: str
    fields: dict[str, str]
    query_param: str = "query"
    query_encoding: str = "none"
    operators: list[str] = field(default_factory=list)
    pagination: EnginePagination = field(default_factory=EnginePagination)
    response_path: str = "results"
    rate_limit: float = 1.0


def load_engine_specs() -> dict[str, EngineSpec]:
    if not SPECS_FILE.exists():
        logger.warning("引擎规格文件不存在: %s", SPECS_FILE)
        return {}

    with open(SPECS_FILE, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    engines: dict[str, EngineSpec] = {}
    for name, cfg in raw.get("engines", {}).items():
        pag_cfg = cfg.get("pagination", {})
        engines[name] = EngineSpec(
            name=name,
            display_name=cfg.get("display_name", name),
            search_url=cfg.get("search_url", ""),
            auth_type=cfg.get("auth_type", "apikey"),
            fields=cfg.get("fields", {}),
            query_param=cfg.get("query_param", "query"),
            query_encoding=cfg.get("query_encoding", "none"),
            operators=cfg.get("operators", []),
            pagination=EnginePagination(
                param=pag_cfg.get("param", "page"),
                size_param=pag_cfg.get("size_param"),
                default_size=pag_cfg.get("default_size", 100),
            ),
            response_path=cfg.get("response_path", "results"),
            rate_limit=cfg.get("rate_limit", 1.0),
        )

    logger.info("加载了 %d 个引擎规格: %s", len(engines), list(engines.keys()))
    return engines


def build_field_docs(spec: EngineSpec) -> str:
    lines = [f"## {spec.display_name} ({spec.name})"]
    lines.append(f"搜索URL: {spec.search_url}")
    lines.append(f"认证方式: {spec.auth_type}")
    lines.append("可用字段:")
    for field_name, template in spec.fields.items():
        lines.append(f"  - {field_name}: 例 {template}")
    if spec.operators:
        lines.append(f"操作符: {', '.join(spec.operators)}")
    return "\n".join(lines)


def build_all_field_docs(platforms: list[str] | None = None) -> str:
    specs = load_engine_specs()
    target = platforms or list(specs.keys())
    sections = []
    for name in target:
        if name in specs:
            sections.append(build_field_docs(specs[name]))
    return "\n\n".join(sections)


def encode_query(query: str, encoding: str) -> str:
    if encoding == "base64":
        import base64
        return base64.b64encode(query.encode("utf-8")).decode("ascii")
    if encoding == "url":
        from urllib.parse import quote
        return quote(query, safe="")
    return query
