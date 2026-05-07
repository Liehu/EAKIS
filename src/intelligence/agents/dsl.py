import json
import logging

from src.intelligence.engine_specs import build_all_field_docs, load_engine_specs
from src.intelligence.models import DslQuery
from src.intelligence.services.base import BaseLLMClient

logger = logging.getLogger("eakis.intelligence.dsl")


class DSLAgent:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self.llm_client = llm_client

    async def generate(
        self,
        keywords: list[str],
        domains: list[str] | None = None,
        platforms: list[str] | None = None,
    ) -> list[DslQuery]:
        specs = load_engine_specs()
        target_platforms = platforms or list(specs.keys())
        available = [p for p in target_platforms if p in specs]
        if not available:
            logger.warning("未找到任何匹配的引擎规格: %s", target_platforms)
            return []

        try:
            queries = await self._generate_via_llm(keywords, domains, available)
            if queries:
                return queries
        except Exception:
            logger.warning("LLM DSL生成失败，降级为模板生成")

        return self._generate_via_template(keywords, domains, available)

    async def _generate_via_llm(
        self, keywords: list[str], domains: list[str] | None, platforms: list[str]
    ) -> list[DslQuery]:
        kw_str = ", ".join(keywords[:10])
        domain_str = ", ".join(domains) if domains else "未知"
        field_docs = build_all_field_docs(platforms)

        prompt = (
            f"你是一个搜索语法生成专家。请根据以下关键词、域名和各平台字段说明，为每个平台生成最优的搜索语法（DSL）。\n\n"
            f"关键词：{kw_str}\n"
            f"域名：{domain_str}\n\n"
            f"{field_docs}\n\n"
            f"请仅返回JSON格式：{{\"平台名\": \"DSL查询语句\"}}\n"
            f"不要添加任何解释，只返回JSON。"
        )

        response = await self.llm_client.generate(prompt)
        parsed = json.loads(response)
        queries: list[DslQuery] = []
        for platform, dsl in parsed.items():
            if platform in platforms and isinstance(dsl, str):
                queries.append(DslQuery(
                    platform=platform,
                    query=dsl,
                    syntax_valid=self._validate_dsl(platform, dsl),
                ))
        return queries

    def _generate_via_template(
        self, keywords: list[str], domains: list[str] | None, platforms: list[str]
    ) -> list[DslQuery]:
        specs = load_engine_specs()
        queries: list[DslQuery] = []
        primary_kw = keywords[0] if keywords else "目标"
        primary_domain = domains[0] if domains else None

        for platform in platforms:
            spec = specs.get(platform)
            if not spec:
                continue

            dsl = None
            if primary_domain:
                for field_name, template in spec.fields.items():
                    if "domain" in field_name or "hostname" in field_name or "names" in field_name:
                        dsl = template.replace("{value}", primary_domain)
                        break

            if not dsl:
                for field_name, template in spec.fields.items():
                    if "title" in field_name or "org" in field_name:
                        dsl = template.replace("{value}", primary_kw)
                        break

            if dsl:
                queries.append(DslQuery(platform=platform, query=dsl, syntax_valid=True))

        return queries

    def _validate_dsl(self, platform: str, dsl: str) -> bool:
        if not dsl or len(dsl) < 3:
            return False
        specs = load_engine_specs()
        spec = specs.get(platform)
        if not spec:
            return True

        has_field = any(field_key in dsl for field_key in spec.fields)
        if spec.operators:
            has_op = any(op in dsl for op in spec.operators if op not in ("(", ")"))
            return has_field or has_op
        return has_field
