"""KW-SUMMARIZER: Compresses intelligence documents into structured summaries.

Uses a Map-Reduce strategy:
  1. Split large intel collections into chunks
  2. Summarize each chunk (map phase)
  3. Merge summaries into a final structured output (reduce phase)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.shared.llm_client import LLMClient


@dataclass
class SummarizerConfig:
    max_input_tokens: int = 4096
    target_ratio: float = 0.15
    chunk_size: int = 1000
    chunk_overlap: int = 100


@dataclass
class StructuredSummary:
    business_info: str = ""
    tech_mentions: list[str] = field(default_factory=list)
    entity_mentions: list[str] = field(default_factory=list)
    product_mentions: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_text(self) -> str:
        parts = []
        if self.business_info:
            parts.append(f"业务: {self.business_info}")
        if self.tech_mentions:
            parts.append(f"技术: {', '.join(self.tech_mentions)}")
        if self.entity_mentions:
            parts.append(f"实体: {', '.join(self.entity_mentions)}")
        if self.product_mentions:
            parts.append(f"产品: {', '.join(self.product_mentions)}")
        return " | ".join(parts)


MAP_PROMPT = """你是情报分析员。请从以下文本中提取与企业攻击面相关的关键信息，
只保留：业务描述、技术词汇、子公司/合作伙伴名称、产品名称。
去除：无关新闻、广告、通用描述。

文本：
{text}

输出格式（JSON）：
{{
  "business_info": "核心业务描述（50字以内）",
  "tech_mentions": ["技术词1", "技术词2"],
  "entity_mentions": ["实体1", "实体2"],
  "product_mentions": ["产品1", "产品2"]
}}
"""

REDUCE_PROMPT = """你是情报分析员。以下是多段情报的结构化摘要，请合并为一份统一的摘要。
去除重复项，保留最关键的信息。

摘要列表：
{summaries}

输出格式（JSON）：
{{
  "business_info": "核心业务描述（50字以内）",
  "tech_mentions": ["技术词1", "技术词2"],
  "entity_mentions": ["实体1", "实体2"],
  "product_mentions": ["产品1", "产品2"]
}}
"""


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _parse_summary_json(raw: str) -> StructuredSummary:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting JSON block from markdown-style response
        import re
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return StructuredSummary(raw_text=raw)
        else:
            return StructuredSummary(raw_text=raw)
    return StructuredSummary(
        business_info=data.get("business_info", ""),
        tech_mentions=data.get("tech_mentions", []),
        entity_mentions=data.get("entity_mentions", []),
        product_mentions=data.get("product_mentions", []),
    )


class SummarizerAgent:
    """Map-Reduce summarization of intelligence documents."""

    def __init__(
        self,
        llm: LLMClient,
        config: SummarizerConfig | None = None,
    ) -> None:
        self._llm = llm
        self._config = config or SummarizerConfig()

    async def summarize(self, documents: list[str]) -> StructuredSummary:
        """Summarize a collection of intelligence documents."""
        combined = "\n\n".join(documents)
        if not combined.strip():
            return StructuredSummary()

        chunks = _chunk_text(combined, self._config.chunk_size, self._config.chunk_overlap)

        # Map phase: summarize each chunk
        chunk_summaries: list[StructuredSummary] = []
        for chunk in chunks:
            prompt = MAP_PROMPT.format(text=chunk)
            try:
                result = await self._llm.generate(prompt)
                chunk_summaries.append(_parse_summary_json(result))
            except Exception:
                continue

        if not chunk_summaries:
            return StructuredSummary()

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        # Reduce phase: merge summaries
        summaries_text = "\n".join(s.to_text() for s in chunk_summaries)
        prompt = REDUCE_PROMPT.format(summaries=summaries_text)
        try:
            result = await self._llm.generate(prompt)
            return _parse_summary_json(result)
        except Exception:
            # Fallback: merge manually without LLM
            return self._manual_merge(chunk_summaries)

    @staticmethod
    def _manual_merge(summaries: list[StructuredSummary]) -> StructuredSummary:
        tech: list[str] = []
        entities: list[str] = []
        products: list[str] = []
        business_parts: list[str] = []

        seen_tech: set[str] = set()
        seen_entity: set[str] = set()
        seen_product: set[str] = set()

        for s in summaries:
            if s.business_info:
                business_parts.append(s.business_info)
            for t in s.tech_mentions:
                if t.lower() not in seen_tech:
                    seen_tech.add(t.lower())
                    tech.append(t)
            for e in s.entity_mentions:
                if e.lower() not in seen_entity:
                    seen_entity.add(e.lower())
                    entities.append(e)
            for p in s.product_mentions:
                if p.lower() not in seen_product:
                    seen_product.add(p.lower())
                    products.append(p)

        return StructuredSummary(
            business_info="；".join(business_parts[:3]) if business_parts else "",
            tech_mentions=tech,
            entity_mentions=entities,
            product_mentions=products,
        )
