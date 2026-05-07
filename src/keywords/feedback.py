"""FeedbackOptimizer: Regenerates low-yield keywords based on retrieval results.

Trigger: hit_rate < 20% or result count < 10 after asset retrieval.
Actions:
  1. Mark current keywords as low_yield
  2. Query RAG for historical effective keywords of similar companies
  3. LLM generates new keywords combining historical experience
  4. Re-submit for DSL generation, max 3 cycles
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from src.keywords.ranker import KeywordCandidate
from src.shared.llm_client import LLMClient


FEEDBACK_PROMPT = """你是企业攻击面分析专家。以下关键词在资产检索中命中率过低，需要优化。

企业名称：{company_name}
行业：{industry}
低效关键词：{failed_keywords}
历史成功案例：{historical_keywords}

请分析失败原因并生成新的关键词：
1. 扩大搜索范围（如使用行业通用词、产品类别词）
2. 添加证书/域名相关的搜索模式
3. 参考历史成功案例中的关键词模式

输出JSON：
{{
  "failure_analysis": "失败原因分析",
  "new_keywords": [
    {{"word": "新关键词", "type": "business|tech|entity", "relevance": 0.8, "reason": "生成原因"}}
  ]
}}
"""


@dataclass
class FeedbackRecord:
    company_type: str
    failed_keywords: list[str]
    failure_reason: str
    successful_keywords: list[str]
    lesson: str


@dataclass
class FeedbackResult:
    new_keywords: list[KeywordCandidate] = field(default_factory=list)
    analysis: str = ""
    cycle: int = 0
    improved: bool = False


class FeedbackOptimizer:
    """Monitors keyword retrieval effectiveness and triggers regeneration."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        max_cycles: int = 3,
        hit_rate_threshold: float = 0.20,
        min_results: int = 10,
    ) -> None:
        self._llm = llm
        self._max_cycles = max_cycles
        self._hit_rate_threshold = hit_rate_threshold
        self._min_results = min_results
        self._feedback_history: list[FeedbackRecord] = []

    def should_trigger(
        self,
        total_keywords: int,
        hit_count: int,
        result_count: int,
    ) -> bool:
        hit_rate = hit_count / max(total_keywords, 1)
        return hit_rate < self._hit_rate_threshold or result_count < self._min_results

    async def optimize(
        self,
        keywords: list[KeywordCandidate],
        company_name: str,
        industry: str | None,
        hit_count: int,
        result_count: int,
        cycle: int = 0,
    ) -> FeedbackResult:
        if cycle >= self._max_cycles:
            return FeedbackResult(cycle=cycle, improved=False)

        failed_words = [kw.word for kw in keywords if not kw.derived]
        historical = self._get_historical_keywords(industry)

        if self._llm:
            new_keywords = await self._llm_optimize(
                company_name, industry, failed_words, historical
            )
        else:
            new_keywords = self._rule_based_optimize(failed_words, industry)

        analysis = f"命中率 {hit_count}/{len(keywords)}, 结果数 {result_count}, 第 {cycle + 1} 轮优化"

        return FeedbackResult(
            new_keywords=new_keywords,
            analysis=analysis,
            cycle=cycle + 1,
            improved=len(new_keywords) > 0,
        )

    async def _llm_optimize(
        self,
        company_name: str,
        industry: str | None,
        failed_keywords: list[str],
        historical_keywords: list[str],
    ) -> list[KeywordCandidate]:
        prompt = FEEDBACK_PROMPT.format(
            company_name=company_name,
            industry=industry or "未知",
            failed_keywords=json.dumps(failed_keywords, ensure_ascii=False),
            historical_keywords=json.dumps(historical_keywords, ensure_ascii=False) if historical_keywords else "无",
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
        for item in data.get("new_keywords", []):
            word = item.get("word", "").strip()
            if not word:
                continue
            results.append(KeywordCandidate(
                word=word,
                keyword_type=item.get("type", "business"),
                relevance_score=min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            ))
        return results

    def _rule_based_optimize(
        self,
        failed_keywords: list[str],
        industry: str | None,
    ) -> list[KeywordCandidate]:
        # Simple heuristic: broaden with industry-level terms
        industry_terms: dict[str, list[str]] = {
            "fintech": ["支付牌照", "金融科技", "互联网金融", "数字支付", "fintech"],
            "finance": ["金融", "银行", "证券", "基金", "保险", "banking"],
            "ecommerce": ["电商", "购物", "商城", "shop", "mall"],
            "government": ["政务", "政府", "公共服务", "gov"],
            "healthcare": ["医疗", "健康", "医院", "health", "medical"],
        }

        results: list[KeywordCandidate] = []
        if industry and industry in industry_terms:
            for term in industry_terms[industry]:
                if term.lower() not in {f.lower() for f in failed_keywords}:
                    results.append(KeywordCandidate(
                        word=term,
                        keyword_type="business",
                        relevance_score=0.6,
                    ))
        return results

    def _get_historical_keywords(self, industry: str | None) -> list[str]:
        if not industry:
            return []
        return [
            rec.successful_keywords
            for rec in self._feedback_history
            if rec.company_type == industry
        ]

    def record_feedback(self, record: FeedbackRecord) -> None:
        self._feedback_history.append(record)
        if len(self._feedback_history) > 100:
            self._feedback_history = self._feedback_history[-50:]
