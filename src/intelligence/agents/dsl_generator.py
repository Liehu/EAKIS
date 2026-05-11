"""
统一 DSL 生成器 - 支持资产搜索引擎和普通搜索引擎

引擎分类：
- Asset Engine: Fofa, Shodan, ZoomEye, Hunter, Quake, Censys
- General Search: 百度, Bing, Google
- Special: Ceye (DNS/HTTP 回显平台)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.intelligence.engine_specs import (
    EngineSpec,
    build_all_field_docs,
    load_engine_specs,
)
from src.intelligence.models import DslQuery
from src.intelligence.services.base import BaseLLMClient

logger = logging.getLogger("eakis.intelligence.dsl_generator")


class EngineType(str, Enum):
    """引擎类型分类"""

    ASSET = "asset"  # 资产搜索引擎
    GENERAL = "general"  # 普通搜索引擎
    SPECIAL = "special"  # 特殊平台


@dataclass
class SearchContext:
    """搜索上下文"""

    keywords: list[str]
    domains: list[str] | None = None
    ip_ranges: list[str] | None = None
    ports: list[int] | None = None
    company_name: str | None = None
    filters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "keywords": self.keywords,
            "domains": self.domains,
            "ip_ranges": self.ip_ranges,
            "ports": self.ports,
            "company_name": self.company_name,
            "filters": self.filters or {},
        }


@dataclass
class DSLTemplate:
    """DSL 模板"""

    name: str
    template: str
    engine_type: EngineType
    priority: int = 5
    description: str = ""


class UnifiedDSLGenerator:
    """
    统一 DSL 生成器

    支持的搜索引擎：
    1. 资产引擎：FOFA, Shodan, ZoomEye, Hunter, Quake, Censys
    2. 普通搜索：百度, Bing, Google
    3. 特殊平台：Ceye
    """

    # 引擎类型映射
    ENGINE_TYPE_MAP: dict[str, EngineType] = {
        # 资产引擎
        "fofa": EngineType.ASSET,
        "shodan": EngineType.ASSET,
        "zoomeye": EngineType.ASSET,
        "hunter": EngineType.ASSET,
        "quake": EngineType.ASSET,
        "censys": EngineType.ASSET,
        # 普通搜索
        "baidu": EngineType.GENERAL,
        "bing": EngineType.GENERAL,
        "google": EngineType.GENERAL,
        # 特殊
        "ceye": EngineType.SPECIAL,
    }

    # 操作符映射（不同引擎的逻辑操作符）
    OPERATOR_MAP: dict[EngineType, dict[str, str]] = {
        EngineType.ASSET: {
            "AND": "&&",
            "OR": "||",
            "NOT": "!=",
        },
        EngineType.GENERAL: {
            "AND": " ",
            "OR": " OR ",
            "NOT": " -",
        },
    }

    # 预定义 DSL 模板
    ASSET_TEMPLATES: list[DSLTemplate] = [
        DSLTemplate(
            name="domain_search",
            template='domain="{domain}"',
            engine_type=EngineType.ASSET,
            priority=8,
            description="域名搜索",
        ),
        DSLTemplate(
            name="title_search",
            template='title="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=7,
            description="标题搜索",
        ),
        DSLTemplate(
            name="header_search",
            template='header="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=6,
            description="响应头搜索",
        ),
        DSLTemplate(
            name="body_search",
            template='body="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=5,
            description="正文搜索",
        ),
        DSLTemplate(
            name="cert_search",
            template='cert="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=7,
            description="证书搜索",
        ),
        DSLTemplate(
            name="icon_search",
            template='icon_hash="{hash}"',
            engine_type=EngineType.ASSET,
            priority=9,
            description="图标哈希搜索",
        ),
        DSLTemplate(
            name="org_search",
            template='org="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=6,
            description="组织搜索",
        ),
        DSLTemplate(
            name="app_search",
            template='app="{keyword}"',
            engine_type=EngineType.ASSET,
            priority=5,
            description="应用指纹搜索",
        ),
    ]

    GENERAL_TEMPLATES: list[DSLTemplate] = [
        DSLTemplate(
            name="site_search",
            template="site:{domain}",
            engine_type=EngineType.GENERAL,
            priority=9,
            description="站点搜索",
        ),
        DSLTemplate(
            name="intitle_search",
            template='intitle:"{keyword}"',
            engine_type=EngineType.GENERAL,
            priority=8,
            description="标题搜索",
        ),
        DSLTemplate(
            name="inurl_search",
            template='inurl:"{keyword}"',
            engine_type=EngineType.GENERAL,
            priority=7,
            description="URL搜索",
        ),
        DSLTemplate(
            name="filetype_search",
            template='filetype:{ext}',
            engine_type=EngineType.GENERAL,
            priority=5,
            description="文件类型搜索",
        ),
        DSLTemplate(
            name="exact_search",
            template='"{keyword}"',
            engine_type=EngineType.GENERAL,
            priority=6,
            description="精确短语搜索",
        ),
    ]

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.specs = load_engine_specs()
        logger.info(
            "DSL生成器初始化完成，支持 %d 个引擎: %s",
            len(self.specs),
            list(self.specs.keys()),
        )

    def get_engine_type(self, engine: str) -> EngineType:
        """获取引擎类型"""
        return self.ENGINE_TYPE_MAP.get(engine.lower(), EngineType.SPECIAL)

    def is_asset_engine(self, engine: str) -> bool:
        """判断是否为资产引擎"""
        return self.get_engine_type(engine) == EngineType.ASSET

    def is_general_engine(self, engine: str) -> bool:
        """判断是否为普通搜索引擎"""
        return self.get_engine_type(engine) == EngineType.GENERAL

    async def generate(
        self,
        context: SearchContext,
        engines: list[str] | None = None,
        use_llm: bool = True,
    ) -> list[DslQuery]:
        """
        生成 DSL 查询

        Args:
            context: 搜索上下文（关键词、域名、过滤器等）
            engines: 目标引擎列表，None 表示全部
            use_llm: 是否使用 LLM 生成（默认 True）

        Returns:
            DSL 查询列表
        """
        target_engines = engines or list(self.specs.keys())
        available = [e for e in target_engines if e in self.specs]

        if not available:
            logger.warning("未找到任何匹配的引擎: %s", target_engines)
            return []

        # 优先尝试 LLM 生成
        if use_llm and self.llm_client:
            try:
                queries = await self._generate_via_llm(context, available)
                if queries:
                    logger.info("LLM DSL生成成功，生成 %d 条查询", len(queries))
                    return queries
            except Exception as e:
                logger.warning("LLM DSL生成失败: %s，降级为模板生成", e)

        # 降级到模板生成
        return self._generate_via_template(context, available)

    async def _generate_via_llm(
        self, context: SearchContext, engines: list[str]
    ) -> list[DslQuery]:
        """使用 LLM 生成 DSL"""

        # 按引擎类型分组
        asset_engines = [e for e in engines if self.is_asset_engine(e)]
        general_engines = [e for e in engines if self.is_general_engine(e)]

        # 构建提示词
        prompt_parts = [
            "你是一个搜索语法生成专家。请根据以下信息，为每个平台生成最优的搜索语法（DSL）。",
            "",
            f"关键词：{', '.join(context.keywords[:10])}",
        ]

        if context.domains:
            prompt_parts.append(f"域名：{', '.join(context.domains)}")
        if context.ip_ranges:
            prompt_parts.append(f"IP段：{', '.join(context.ip_ranges)}")
        if context.ports:
            prompt_parts.append(f"端口：{', '.join(map(str, context.ports))}")
        if context.company_name:
            prompt_parts.append(f"企业名称：{context.company_name}")
        if context.filters:
            prompt_parts.append(f"过滤器：{json.dumps(context.filters, ensure_ascii=False)}")

        prompt_parts.append("")

        # 添加引擎规格文档
        if asset_engines:
            prompt_parts.append("## 资产搜索引擎")
            prompt_parts.append(build_all_field_docs(asset_engines))
            prompt_parts.append("")
            prompt_parts.append(
                "资产引擎语法规则："
                "- 字段查询格式：field=\"value\" 或 field==\"value\"（精确匹配）"
                "- 逻辑操作：&&（AND）、||（OR）、!=（NOT）"
                "- 示例：title=\"后台\" && country=\"CN\" && port=\"443\""
            )

        if general_engines:
            prompt_parts.append("## 普通搜索引擎")
            prompt_parts.append(build_all_field_docs(general_engines))
            prompt_parts.append("")
            prompt_parts.append(
                "普通搜索引擎语法规则："
                "- site: 域名限定，如 site:example.com"
                "- intitle: 标题包含，如 intitle:\"后台管理\""
                "- inurl: URL包含，如 inurl:admin"
                "- filetype: 文件类型，如 filetype:pdf"
                "- 逻辑操作：空格=AND、OR、-（NOT）"
                "- 示例：site:example.com intitle:\"后台\" filetype:pdf"
            )

        prompt_parts.append("")
        prompt_parts.append(
            "请仅返回JSON格式：{\"平台名\": \"DSL查询语句\"}，不要添加任何解释。"
        )

        prompt = "\n".join(prompt_parts)
        response = await self.llm_client.generate(prompt)

        # 解析响应
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            logger.error("LLM返回的JSON格式无效: %s", response[:200])
            return []

        queries: list[DslQuery] = []
        for platform, dsl in parsed.items():
            if platform in engines and isinstance(dsl, str):
                queries.append(
                    DslQuery(
                        platform=platform,
                        query=dsl,
                        syntax_valid=self._validate_dsl(platform, dsl),
                    )
                )

        return queries

    def _generate_via_template(
        self, context: SearchContext, engines: list[str]
    ) -> list[DslQuery]:
        """使用预定义模板生成 DSL"""
        queries: list[DslQuery] = []
        primary_kw = context.keywords[0] if context.keywords else "目标"
        primary_domain = context.domains[0] if context.domains else None
        primary_ip = context.ip_ranges[0] if context.ip_ranges else None

        for engine in engines:
            spec = self.specs.get(engine)
            if not spec:
                continue

            engine_type = self.get_engine_type(engine)
            dsl = self._build_dsl_from_template(
                engine, spec, engine_type, context, primary_kw, primary_domain, primary_ip
            )

            if dsl:
                queries.append(
                    DslQuery(platform=engine, query=dsl, syntax_valid=True)
                )

        return queries

    def _build_dsl_from_template(
        self,
        engine: str,
        spec: EngineSpec,
        engine_type: EngineType,
        context: SearchContext,
        primary_kw: str,
        primary_domain: str | None,
        primary_ip: str | None,
    ) -> str | None:
        """从模板构建 DSL"""
        parts: list[str] = []

        # 获取操作符
        ops = self.OPERATOR_MAP.get(engine_type, {})
        and_op = ops.get("AND", " ")

        # 1. 域名/站点搜索（优先级最高）
        if primary_domain:
            if engine_type == EngineType.ASSET:
                # 资产引擎：查找 domain 字段
                domain_field = self._find_field(spec, ["domain", "hostname", "host"])
                if domain_field:
                    parts.append(domain_field.replace("{value}", primary_domain))
            else:
                # 普通搜索：site: 操作符
                parts.append(f"site:{primary_domain}")

        # 2. IP 段搜索
        if primary_ip:
            if engine_type == EngineType.ASSET:
                ip_field = self._find_field(spec, ["ip", "ip_cidr", "cidr", "net"])
                if ip_field:
                    parts.append(ip_field.replace("{value}", primary_ip))

        # 3. 端口搜索
        if context.ports:
            if engine_type == EngineType.ASSET:
                port_field = self._find_field(spec, ["port"])
                if port_field:
                    port_strs = [
                        port_field.replace("{value}", str(p)) for p in context.ports
                    ]
                    parts.append(f"({' || '.join(port_strs)})")

        # 4. 关键词搜索
        if primary_kw:
            if engine_type == EngineType.ASSET:
                # 资产引擎：尝试多个字段
                title_field = self._find_field(spec, ["title", "web_title"])
                body_field = self._find_field(spec, ["body", "web_body", "http_body"])
                org_field = self._find_field(spec, ["org", "owner"])

                # 优先使用组织字段
                if context.company_name and org_field:
                    parts.append(org_field.replace("{value}", context.company_name))
                elif title_field:
                    parts.append(title_field.replace("{value}", primary_kw))
                elif body_field:
                    parts.append(body_field.replace("{value}", primary_kw))

            else:
                # 普通搜索：intitle 精确匹配
                parts.append(f'intitle:"{primary_kw}"')

        # 5. 过滤器
        if context.filters:
            for key, value in context.filters.items():
                field = self._find_field(spec, [key])
                if field:
                    if engine_type == EngineType.ASSET:
                        parts.append(field.replace("{value}", str(value)))
                    else:
                        parts.append(f"{key}:\"{value}\"")

        # 组合
        if not parts:
            # 降级：使用通用字段
            fallback_field = self._find_field(spec, ["title", "app", "q"])
            if fallback_field:
                return fallback_field.replace("{value}", primary_kw)

        return and_op.join(parts) if parts else None

    def _find_field(self, spec: EngineSpec, candidates: list[str]) -> str | None:
        """在引擎规格中查找字段"""
        for candidate in candidates:
            if candidate in spec.fields:
                return spec.fields[candidate]
        return None

    def _validate_dsl(self, platform: str, dsl: str) -> bool:
        """验证 DSL 语法"""
        if not dsl or len(dsl) < 3:
            return False

        spec = self.specs.get(platform)
        if not spec:
            return True

        # 检查是否包含已知字段或操作符
        has_field = any(field_key in dsl for field_key in spec.fields)
        if spec.operators:
            has_op = any(op in dsl for op in spec.operators if op not in ("(", ")"))
            return has_field or has_op

        # 普通搜索引擎的特殊验证
        if self.is_general_engine(platform):
            general_keywords = ["site:", "intitle:", "inurl:", "filetype:", "cache:", "related:"]
            return any(kw in dsl for kw in general_keywords)

        return has_field

    def get_supported_engines(self, engine_type: EngineType | None = None) -> list[str]:
        """获取支持的引擎列表"""
        if engine_type is None:
            return list(self.specs.keys())
        return [
            engine
            for engine in self.specs.keys()
            if self.get_engine_type(engine) == engine_type
        ]

    def translate_dsl(self, dsl: str, from_engine: str, to_engine: str) -> str | None:
        """
        跨引擎 DSL 转换

        Args:
            dsl: 源 DSL 查询
            from_engine: 源引擎
            to_engine: 目标引擎

        Returns:
            转换后的 DSL，转换失败返回 None
        """
        from_type = self.get_engine_type(from_engine)
        to_type = self.get_engine_type(to_engine)
        to_spec = self.specs.get(to_engine)

        if not to_spec:
            return None

        # 同类型引擎直接返回
        if from_type == to_type:
            return dsl

        # 资产引擎 → 普通搜索
        if from_type == EngineType.ASSET and to_type == EngineType.GENERAL:
            return self._asset_to_general(dsl, to_spec)

        # 普通搜索 → 资产引擎
        if from_type == EngineType.GENERAL and to_type == EngineType.ASSET:
            return self._general_to_asset(dsl, to_spec)

        return None

    def _asset_to_general(self, dsl: str, to_spec: EngineSpec) -> str:
        """资产引擎 DSL 转普通搜索 DSL"""
        result = dsl
        mappings = {
            'domain="': "site:",
            'title="': 'intitle:"',
            'body="': 'inbody:"',
            'header="': "inheader:",
            " && ": " ",
            " || ": " OR ",
        }
        for old, new in mappings.items():
            result = result.replace(old, new)
        # 去掉闭合引号后的引号，转换为普通搜索格式
        result = result.replace('")', '"')
        return result

    def _general_to_asset(self, dsl: str, to_spec: EngineSpec) -> str:
        """普通搜索 DSL 转资产引擎 DSL"""
        result = dsl
        mappings = {
            "site:": 'domain="',
            "intitle:": 'title="',
            "inurl:": 'url="',
            "inbody:": 'body="',
            '"': '"',
            " ": " && ",
            " OR ": " || ",
        }
        for old, new in mappings.items():
            result = result.replace(old, new)
        return result


# 向后兼容的 DSLAgent 类（保持原有接口）
class DSLAgent(UnifiedDSLGenerator):
    """向后兼容的 DSL Agent"""

    async def generate(
        self,
        keywords: list[str],
        domains: list[str] | None = None,
        platforms: list[str] | None = None,
    ) -> list[DslQuery]:
        """兼容原有接口"""
        context = SearchContext(
            keywords=keywords,
            domains=domains,
        )
        return await super().generate(context=context, engines=platforms)
