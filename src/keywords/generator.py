"""KW-GENERATOR: Extracts multi-dimensional keywords from structured summaries.

Generates three keyword types:
  - business: core business, products/services, industry tags
  - tech: frameworks, databases, middleware, protocols
  - entity: subsidiaries, partners, investors, suppliers
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.keywords.ranker import KeywordCandidate, KeywordRanker
from src.keywords.summarizer import StructuredSummary
from src.shared.llm_client import LLMClient


GENERATE_PROMPT = """你是企业攻击面分析专家。根据以下情报摘要，提取用于资产发现的关键词。

企业名称：{company_name}
行业：{industry}
情报摘要：
{summary_text}

请提取三类关键词：
1. **业务关键词** (business)：企业主营业务、产品服务名称、行业标签
2. **技术关键词** (tech)：使用的框架、数据库、中间件、协议、开发工具
3. **关联主体关键词** (entity)：子公司、合作伙伴、投资方、供应商、关联公司名称

每个关键词附带：
- relevance (0~1)：与靶标核心业务的关联程度

输出JSON格式：
{{
  "business": [
    {{"word": "关键词", "relevance": 0.95}},
    ...
  ],
  "tech": [
    {{"word": "关键词", "relevance": 0.80}},
    ...
  ],
  "entity": [
    {{"word": "关键词", "relevance": 0.75}},
    ...
  ]
}}
"""


@dataclass
class GeneratedKeywords:
    business: list[KeywordCandidate]
    tech: list[KeywordCandidate]
    entity: list[KeywordCandidate]

    @property
    def all(self) -> list[KeywordCandidate]:
        return self.business + self.tech + self.entity

    @property
    def total(self) -> int:
        return len(self.business) + len(self.tech) + len(self.entity)


def _parse_generated(raw: str) -> dict[str, list[dict]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return {}
        else:
            return {}
    return data if isinstance(data, dict) else {}


class KeywordGeneratorAgent:
    """Extracts keywords from intelligence summaries using LLM."""

    def __init__(
        self,
        llm: LLMClient,
        ranker: KeywordRanker,
    ) -> None:
        self._llm = llm
        self._ranker = ranker

    async def generate(
        self,
        company_name: str,
        industry: str | None,
        summary: StructuredSummary,
    ) -> GeneratedKeywords:
        summary_text = summary.to_text()
        if not summary_text.strip():
            return self._fallback_generate(summary)

        prompt = GENERATE_PROMPT.format(
            company_name=company_name,
            industry=industry or "未知",
            summary_text=summary_text,
        )

        try:
            raw = await self._llm.generate(prompt)
            parsed = _parse_generated(raw)
        except Exception:
            parsed = {}

        if not parsed:
            return self._fallback_generate(summary)

        business = self._to_candidates(parsed.get("business", []), "business")
        tech = self._to_candidates(parsed.get("tech", []), "tech")
        entity = self._to_candidates(parsed.get("entity", []), "entity")

        return GeneratedKeywords(business=business, tech=tech, entity=entity)

    def _to_candidates(
        self,
        items: list[dict],
        keyword_type: str,
    ) -> list[KeywordCandidate]:
        candidates: list[KeywordCandidate] = []
        for item in items:
            word = item.get("word", "").strip()
            if not word:
                continue
            relevance = float(item.get("relevance", 0.5))
            domain_score = self._ranker._domain_dict.score(word)
            candidates.append(
                KeywordCandidate(
                    word=word,
                    keyword_type=keyword_type,
                    tf_idf=0.0,
                    domain_score=domain_score,
                    relevance_score=min(1.0, max(0.0, relevance)),
                )
            )
        return candidates

    def _fallback_generate(self, summary: StructuredSummary) -> GeneratedKeywords:
        """When LLM is unavailable, extract keywords directly from summary fields."""
        business: list[KeywordCandidate] = []
        tech: list[KeywordCandidate] = []
        entity: list[KeywordCandidate] = []

        if summary.business_info:
            ds = self._ranker._domain_dict.score(summary.business_info)
            business.append(KeywordCandidate(
                word=summary.business_info,
                keyword_type="business",
                domain_score=ds,
                relevance_score=0.7,
            ))

        for w in summary.tech_mentions:
            ds = self._ranker._domain_dict.score(w)
            tech.append(KeywordCandidate(
                word=w,
                keyword_type="tech",
                domain_score=ds,
                relevance_score=0.6,
            ))

        for w in summary.entity_mentions:
            ds = self._ranker._domain_dict.score(w)
            entity.append(KeywordCandidate(
                word=w,
                keyword_type="entity",
                domain_score=ds,
                relevance_score=0.6,
            ))

        for w in summary.product_mentions:
            ds = self._ranker._domain_dict.score(w)
            business.append(KeywordCandidate(
                word=w,
                keyword_type="business",
                domain_score=ds,
                relevance_score=0.7,
            ))

        return GeneratedKeywords(business=business, tech=tech, entity=entity)
