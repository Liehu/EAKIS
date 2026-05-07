"""Unit tests for the keyword engine module.

Covers: KeywordRanker, SummarizerAgent, KeywordGeneratorAgent,
KeywordExpander, FeedbackOptimizer, and KeywordModule.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from src.keywords.ranker import (
    DomainDictionary,
    KeywordCandidate,
    KeywordRanker,
    TfIdfCalculator,
)
from src.keywords.summarizer import SummarizerAgent, SummarizerConfig, StructuredSummary, _parse_summary_json
from src.keywords.generator import KeywordGeneratorAgent
from src.keywords.expander import KeywordExpander
from src.keywords.feedback import FeedbackOptimizer


# ============================================================
# UT-KW-001: Keyword weight calculation
# ============================================================

class TestKeywordRanker:
    """Verify TF-IDF + domain dictionary weight calculation."""

    def test_domain_word_beats_generic_word(self):
        """Domain-strong word should outrank generic word even with lower TF-IDF."""
        ranker = KeywordRanker(domain="finance")

        score_fintech = ranker.compute_weight(
            word="第三方支付",
            tf_idf=0.45,
            domain_score=0.92,
            relevance_score=0.88,
        )

        score_generic = ranker.compute_weight(
            word="管理系统",
            tf_idf=0.60,
            domain_score=0.15,
            relevance_score=0.30,
        )

        assert score_fintech > score_generic
        assert 0.7 < score_fintech < 1.0
        assert score_generic < 0.4

    def test_weight_clamps_to_range(self):
        ranker = KeywordRanker()
        w = ranker.compute_weight("test", tf_idf=5.0, domain_score=2.0, relevance_score=3.0)
        assert 0.0 <= w <= 1.0

    def test_rank_sorts_by_weight_descending(self):
        ranker = KeywordRanker()
        candidates = [
            KeywordCandidate(word="low", keyword_type="business", relevance_score=0.1),
            KeywordCandidate(word="high", keyword_type="business", relevance_score=0.9),
            KeywordCandidate(word="mid", keyword_type="business", relevance_score=0.5),
        ]
        ranked = ranker.rank(candidates)
        weights = [k.weight for k in ranked]
        assert weights == sorted(weights, reverse=True)

    def test_alpha_beta_gamma_sum(self):
        """Hyperparameters should sum to 1.0."""
        ranker = KeywordRanker()
        assert abs(ranker.alpha + ranker.beta + ranker.gamma - 1.0) < 1e-9

    def test_beta_is_highest(self):
        """Domain weight (beta) should be the highest hyperparameter."""
        ranker = KeywordRanker()
        assert ranker.beta > ranker.alpha
        assert ranker.beta > ranker.gamma


class TestDomainDictionary:
    def test_finance_domain_match(self):
        dd = DomainDictionary(domains=["finance"])
        assert dd.score("第三方支付") > 0.0

    def test_tech_stack_match(self):
        dd = DomainDictionary(domains=["tech_stack"])
        assert dd.score("Spring Boot") > 0.0

    def test_unknown_word_low_score(self):
        dd = DomainDictionary(domains=["finance"])
        assert dd.score("xyzzy12345") < 0.1

    def test_empty_word_zero(self):
        dd = DomainDictionary(domains=["finance"])
        assert dd.score("") == 0.0

    def test_all_domains_loaded(self):
        dd = DomainDictionary()
        # Should have entries for all domain files
        assert len(dd._words) > 0


class TestTfIdfCalculator:
    def test_tf_idf_basic(self):
        calc = TfIdfCalculator()
        calc.add_document("hello world foo bar")
        calc.add_document("hello baz qux")
        score = calc.tf_idf("hello", "hello world")
        assert score > 0.0

    def test_rare_word_higher_idf(self):
        calc = TfIdfCalculator()
        for _ in range(10):
            calc.add_document("common word")
        calc.add_document("rare unique word")
        score_common = calc.tf_idf("common", "common")
        score_rare = calc.tf_idf("rare", "rare")
        assert score_rare > score_common


# ============================================================
# Summarizer tests
# ============================================================

class TestSummarizerAgent:
    def test_parse_summary_json_valid(self):
        raw = json.dumps({
            "business_info": "支付公司",
            "tech_mentions": ["Spring Boot"],
            "entity_mentions": ["子公司A"],
            "product_mentions": ["支付平台"],
        })
        s = _parse_summary_json(raw)
        assert s.business_info == "支付公司"
        assert "Spring Boot" in s.tech_mentions

    def test_parse_summary_json_invalid(self):
        s = _parse_summary_json("not json at all")
        assert s.raw_text == "not json at all"

    def test_parse_summary_json_markdown_wrapped(self):
        raw = "```json\n" + json.dumps({
            "business_info": "test",
            "tech_mentions": [],
            "entity_mentions": [],
            "product_mentions": [],
        }) + "\n```"
        s = _parse_summary_json(raw)
        assert s.business_info == "test"

    @pytest.mark.asyncio
    async def test_summarize_with_mock_llm(self):
        llm = AsyncMock()
        llm.generate.return_value = json.dumps({
            "business_info": "金融科技公司",
            "tech_mentions": ["Kubernetes"],
            "entity_mentions": [],
            "product_mentions": ["支付网关"],
        })
        agent = SummarizerAgent(llm, SummarizerConfig(chunk_size=500, chunk_overlap=50))
        result = await agent.summarize(["企业A是一家金融科技公司，使用K8s部署。"])
        assert result.business_info == "金融科技公司"
        assert "Kubernetes" in result.tech_mentions

    @pytest.mark.asyncio
    async def test_summarize_empty_input(self):
        llm = AsyncMock()
        agent = SummarizerAgent(llm)
        result = await agent.summarize([])
        assert result.business_info == ""

    @pytest.mark.asyncio
    async def test_manual_merge_fallback(self):
        summaries = [
            StructuredSummary(business_info="支付", tech_mentions=["Java"], entity_mentions=["A公司"], product_mentions=[]),
            StructuredSummary(business_info="贷款", tech_mentions=["Python"], entity_mentions=["B公司"], product_mentions=["APP"]),
        ]
        result = SummarizerAgent._manual_merge(summaries)
        assert "Java" in result.tech_mentions
        assert "Python" in result.tech_mentions
        assert "A公司" in result.entity_mentions
        assert "B公司" in result.entity_mentions


# ============================================================
# Generator tests
# ============================================================

class TestKeywordGeneratorAgent:
    @pytest.mark.asyncio
    async def test_generate_with_llm(self):
        llm = AsyncMock()
        llm.generate.return_value = json.dumps({
            "business": [{"word": "第三方支付", "relevance": 0.95}],
            "tech": [{"word": "Spring Boot", "relevance": 0.80}],
            "entity": [{"word": "XY科技", "relevance": 0.75}],
        })
        ranker = KeywordRanker(domain="fintech")
        gen = KeywordGeneratorAgent(llm, ranker)
        summary = StructuredSummary(
            business_info="支付公司",
            tech_mentions=["Spring Boot"],
            entity_mentions=["XY科技"],
        )
        result = await gen.generate("XX支付公司", "fintech", summary)
        assert result.total == 3
        assert result.business[0].word == "第三方支付"
        assert result.tech[0].word == "Spring Boot"

    @pytest.mark.asyncio
    async def test_fallback_generate(self):
        llm = AsyncMock()
        llm.generate.side_effect = Exception("LLM unavailable")
        ranker = KeywordRanker()
        gen = KeywordGeneratorAgent(llm, ranker)
        summary = StructuredSummary(
            business_info="支付公司",
            tech_mentions=["Redis"],
            entity_mentions=["子公司"],
            product_mentions=["支付APP"],
        )
        result = await gen.generate("XX支付公司", "fintech", summary)
        assert result.total >= 3  # business_info + product + tech + entity


# ============================================================
# Expander tests
# ============================================================

class TestKeywordExpander:
    @pytest.mark.asyncio
    async def test_static_synonym_expand(self):
        expander = KeywordExpander(llm=None)
        kw = KeywordCandidate(word="微服务", keyword_type="tech", relevance_score=0.8)
        results = await expander.expand([kw])
        assert len(results) == 1
        assert len(results[0].expanded) > 0
        words = [e.word for e in results[0].expanded]
        assert any("Spring Cloud" in w for w in words)

    @pytest.mark.asyncio
    async def test_static_tech_expand(self):
        expander = KeywordExpander(llm=None)
        kw = KeywordCandidate(word="Spring Boot", keyword_type="tech", relevance_score=0.8)
        results = await expander.expand([kw])
        expanded_words = [e.word for e in results[0].expanded]
        assert any("actuator" in w for w in expanded_words)

    @pytest.mark.asyncio
    async def test_static_subdomain_expand(self):
        expander = KeywordExpander(llm=None)
        kw = KeywordCandidate(word="XX支付", keyword_type="business", relevance_score=0.8)
        results = await expander.expand([kw], company_name="xx-pay.com")
        expanded_words = [e.word for e in results[0].expanded]
        assert any("api." in w for w in expanded_words)

    @pytest.mark.asyncio
    async def test_expanded_are_derived(self):
        expander = KeywordExpander(llm=None)
        kw = KeywordCandidate(word="微服务", keyword_type="tech", relevance_score=0.8)
        results = await expander.expand([kw])
        for e in results[0].expanded:
            assert e.derived is True
            assert e.parent_word == "微服务"

    @pytest.mark.asyncio
    async def test_deduplication_within_single_expand(self):
        expander = KeywordExpander(llm=None)
        # Per-keyword expansion deduplicates internally
        kw = KeywordCandidate(word="微服务", keyword_type="tech", relevance_score=0.8)
        results = await expander.expand([kw])
        words = [e.word.lower() for e in results[0].expanded]
        assert len(words) == len(set(words))


# ============================================================
# Feedback tests
# ============================================================

class TestFeedbackOptimizer:
    def test_should_trigger_low_hit_rate(self):
        fb = FeedbackOptimizer(hit_rate_threshold=0.20, min_results=10)
        assert fb.should_trigger(total_keywords=10, hit_count=1, result_count=15) is True

    def test_should_trigger_few_results(self):
        fb = FeedbackOptimizer(hit_rate_threshold=0.20, min_results=10)
        assert fb.should_trigger(total_keywords=10, hit_count=5, result_count=5) is True

    def test_should_not_trigger(self):
        fb = FeedbackOptimizer(hit_rate_threshold=0.20, min_results=10)
        assert fb.should_trigger(total_keywords=10, hit_count=5, result_count=50) is False

    @pytest.mark.asyncio
    async def test_rule_based_optimize(self):
        fb = FeedbackOptimizer(llm=None)
        keywords = [
            KeywordCandidate(word="XX支付", keyword_type="business", relevance_score=0.8),
        ]
        result = await fb.optimize(
            keywords=keywords,
            company_name="XX支付",
            industry="fintech",
            hit_count=1,
            result_count=3,
        )
        assert result.improved is True
        assert len(result.new_keywords) > 0

    @pytest.mark.asyncio
    async def test_max_cycles_respected(self):
        fb = FeedbackOptimizer(llm=None, max_cycles=3)
        keywords = [KeywordCandidate(word="test", keyword_type="business", relevance_score=0.5)]
        result = await fb.optimize(
            keywords=keywords,
            company_name="test",
            industry=None,
            hit_count=0,
            result_count=0,
            cycle=3,  # Already at max
        )
        assert result.improved is False

    @pytest.mark.asyncio
    async def test_llm_optimize(self):
        llm = AsyncMock()
        llm.generate.return_value = json.dumps({
            "failure_analysis": "关键词过于具体",
            "new_keywords": [
                {"word": "支付牌照", "type": "business", "relevance": 0.85, "reason": "扩大范围"},
            ],
        })
        fb = FeedbackOptimizer(llm=llm)
        keywords = [KeywordCandidate(word="XX支付", keyword_type="business", relevance_score=0.8)]
        result = await fb.optimize(
            keywords=keywords,
            company_name="XX支付",
            industry="fintech",
            hit_count=1,
            result_count=5,
        )
        assert result.improved is True
        assert result.new_keywords[0].word == "支付牌照"

    def test_record_feedback(self):
        fb = FeedbackOptimizer()
        from src.keywords.feedback import FeedbackRecord
        fb.record_feedback(FeedbackRecord(
            company_type="fintech",
            failed_keywords=["XX支付"],
            failure_reason="语义过窄",
            successful_keywords=["支付牌照"],
            lesson="金融企业用牌照关键词",
        ))
        assert len(fb._feedback_history) == 1
        hist = fb._get_historical_keywords("fintech")
        assert len(hist) == 1

    def test_feedback_history_capped(self):
        fb = FeedbackOptimizer()
        from src.keywords.feedback import FeedbackRecord
        for i in range(110):
            fb.record_feedback(FeedbackRecord(
                company_type="fintech",
                failed_keywords=[],
                failure_reason="",
                successful_keywords=[],
                lesson="",
            ))
        assert len(fb._feedback_history) <= 100
