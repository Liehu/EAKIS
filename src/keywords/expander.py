"""KeywordExpander: Dynamic keyword expansion for improved asset retrieval coverage.

Strategies:
  synonym     - 同义词扩充 (微服务 → Spring Cloud, Dubbo)
  abbreviation - 缩写扩充 (支付宝 → Alipay)
  subdomain   - 子域模式 (企业名 → api.企业名, m.企业名)
  tech_stack  - 技术栈关联 (Spring Boot → actuator, /health)
  relation    - 关联规则 (企业A → 合作伙伴 → 企业B的资产)

Expanded keywords inherit 50% of parent weight and are marked derived=True.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.keywords.ranker import KeywordCandidate
from src.shared.llm_client import LLMClient


EXPAND_PROMPT = """你是资产发现专家。请根据以下关键词，生成用于网络资产搜索引擎（Fofa、Hunter、Shodan）的扩展关键词。

原关键词：{word}
关键词类型：{kw_type}
企业名称：{company_name}

请从以下维度扩展：
1. 同义词/近义词（中文→英文、行业别名、品牌缩写）
2. 常见子域名模式（api、m、www、mail、oa、dev、staging、test）
3. 关联技术栈特征（如框架名 → 默认路径/端口/特征）
4. 关联企业/品牌

每个扩展关键词附带：
- strategy: 扩展策略 (synonym|abbreviation|subdomain|tech_stack|relation)
- confidence: 置信度 (0~1)

输出JSON：
{{
  "expanded": [
    {{"word": "扩展词", "strategy": "synonym", "confidence": 0.85}},
    ...
  ]
}}

最多返回15个扩展词。
"""

# Static expansion rules for common patterns (no LLM needed)
_STATIC_SYNONYMS: dict[str, list[str]] = {
    "微服务": ["Spring Cloud", "Dubbo", "Kubernetes", "Service Mesh"],
    "支付": ["payment", "pay", "交易", "settlement"],
    "电商": ["ecommerce", "商城", "shop", "mall"],
    "银行": ["bank", "网银", "online banking"],
    "保险": ["insurance", "ins", "保单"],
    "云计算": ["cloud", "云服务", "云平台"],
    "大数据": ["big data", "data platform", "数据中台"],
    "人工智能": ["AI", "machine learning", "ML", "深度学习"],
    "区块链": ["blockchain", "chain", "智能合约"],
}

_STATIC_TECH_STACK: dict[str, list[str]] = {
    "spring boot": ["actuator", "/health", "/env", "/info", "Spring Boot Admin"],
    "nginx": ["/nginx_status", "X-Powered-By"],
    "tomcat": ["/manager/html", "/host-manager"],
    "php": ["phpinfo", "phpmyadmin", "/wp-admin"],
    "wordpress": ["/wp-admin", "/wp-login.php", "/wp-json"],
    "drupal": ["/user/login", "/admin"],
    "redis": ["redis-cli", "6379"],
    "mysql": ["3306", "phpmyadmin"],
    "mongodb": ["27017", "mongo-express"],
    "elasticsearch": ["9200", "/_cat/indices"],
    "kubernetes": ["/api/v1", "k8s", "dashboard"],
    "docker": ["2375", "/containers/json"],
    "jenkins": ["/script", "/console", "/login"],
    "gitlab": ["/api/v4", "/users/sign_in"],
    "nacos": ["/nacos/v1", "8848"],
    "swagger": ["/swagger-ui.html", "/v2/api-docs", "/v3/api-docs"],
}

_STATIC_SUBDOMAINS = [
    "api", "m", "www", "mail", "oa", "dev", "staging", "test",
    "admin", "portal", "app", "cdn", "static", "img", "upload",
    "gateway", "auth", "sso", "crm", "erp", "hr",
]


@dataclass
class ExpansionResult:
    original: KeywordCandidate
    expanded: list[KeywordCandidate]


class KeywordExpander:
    """Expands keywords using LLM + static rules for better asset coverage."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    async def expand(
        self,
        keywords: list[KeywordCandidate],
        company_name: str = "",
        strategy: str = "all",
    ) -> list[ExpansionResult]:
        results: list[ExpansionResult] = []
        for kw in keywords:
            expanded = await self._expand_one(kw, company_name, strategy)
            results.append(ExpansionResult(original=kw, expanded=expanded))
        return results

    async def _expand_one(
        self,
        kw: KeywordCandidate,
        company_name: str,
        strategy: str,
    ) -> list[KeywordCandidate]:
        expanded: list[KeywordCandidate] = []

        # Static expansion first (fast, no LLM needed)
        if strategy in ("all", "synonym", "abbreviation"):
            expanded.extend(self._static_synonym_expand(kw))

        if strategy in ("all", "tech_stack"):
            expanded.extend(self._static_tech_expand(kw))

        if strategy in ("all", "subdomain"):
            expanded.extend(self._static_subdomain_expand(kw, company_name))

        # LLM-based expansion for deeper coverage
        if self._llm and strategy != "subdomain":
            expanded.extend(await self._llm_expand(kw, company_name))

        # Deduplicate
        seen: set[str] = set()
        unique: list[KeywordCandidate] = []
        for e in expanded:
            if e.word.lower() not in seen:
                seen.add(e.word.lower())
                unique.append(e)

        return unique

    def _static_synonym_expand(self, kw: KeywordCandidate) -> list[KeywordCandidate]:
        results: list[KeywordCandidate] = []
        word_lower = kw.word.lower()
        for key, synonyms in _STATIC_SYNONYMS.items():
            if key in word_lower or word_lower in key:
                for s in synonyms:
                    results.append(KeywordCandidate(
                        word=s,
                        keyword_type=kw.keyword_type,
                        weight=0.0,
                        domain_score=0.3,
                        relevance_score=kw.relevance_score * 0.5,
                        derived=True,
                        parent_word=kw.word,
                    ))
        return results

    def _static_tech_expand(self, kw: KeywordCandidate) -> list[KeywordCandidate]:
        results: list[KeywordCandidate] = []
        word_lower = kw.word.lower()
        for key, features in _STATIC_TECH_STACK.items():
            if key in word_lower or word_lower in key:
                for f in features:
                    results.append(KeywordCandidate(
                        word=f,
                        keyword_type="tech",
                        weight=0.0,
                        domain_score=0.6,
                        relevance_score=kw.relevance_score * 0.5,
                        derived=True,
                        parent_word=kw.word,
                    ))
        return results

    def _static_subdomain_expand(
        self,
        kw: KeywordCandidate,
        company_name: str,
    ) -> list[KeywordCandidate]:
        if kw.keyword_type not in ("business", "entity") or not company_name:
            return []
        results: list[KeywordCandidate] = []
        for prefix in _STATIC_SUBDOMAINS[:6]:  # Top 6 most common
            results.append(KeywordCandidate(
                word=f"{prefix}.{company_name}",
                keyword_type=kw.keyword_type,
                weight=0.0,
                domain_score=0.2,
                relevance_score=kw.relevance_score * 0.4,
                derived=True,
                parent_word=kw.word,
            ))
        return results

    async def _llm_expand(
        self,
        kw: KeywordCandidate,
        company_name: str,
    ) -> list[KeywordCandidate]:
        if not self._llm:
            return []

        import json
        import re

        prompt = EXPAND_PROMPT.format(
            word=kw.word,
            kw_type=kw.keyword_type,
            company_name=company_name,
        )

        try:
            raw = await self._llm.generate(prompt)
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                return []
            data = json.loads(match.group())
        except Exception:
            return []

        results: list[KeywordCandidate] = []
        for item in data.get("expanded", []):
            word = item.get("word", "").strip()
            if not word:
                continue
            conf = float(item.get("confidence", 0.5))
            results.append(KeywordCandidate(
                word=word,
                keyword_type=kw.keyword_type,
                weight=0.0,
                domain_score=0.3,
                relevance_score=min(1.0, conf * kw.relevance_score),
                derived=True,
                parent_word=kw.word,
            ))
        return results
