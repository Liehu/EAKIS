"""Unit tests for asset discovery agents."""
from __future__ import annotations

import pytest

from src.asset_discovery.agents.asset_assessor import AssetAssessorAgent
from src.asset_discovery.agents.asset_enricher import AssetEnricherAgent
from src.asset_discovery.agents.feature_extractor import FeatureExtractorAgent
from src.asset_discovery.agents.search_engine import AssetSearchAgent, TokenBucket
from src.asset_discovery.config import AssessorConfig, SearchConfig
from src.asset_discovery.models import (
    AssetType,
    AssessedAsset,
    FeatureVector,
    RawAsset,
)
from src.asset_discovery.services.base import StubSearchClient


# --- TokenBucket ---


class TestTokenBucket:
    def test_initial_capacity(self):
        bucket = TokenBucket(capacity=5, refill_rate=5.0 / 60)
        assert bucket._tokens == 5

    @pytest.mark.asyncio
    async def test_acquire_decrements(self):
        bucket = TokenBucket(capacity=3, refill_rate=100.0)
        await bucket.acquire()
        assert bucket._tokens < 3


# --- AssetSearchAgent ---


class TestAssetSearchAgent:
    @pytest.fixture
    def search_agent(self):
        client = StubSearchClient()
        config = SearchConfig(platforms=["fofa", "hunter"])
        return AssetSearchAgent(client, config)

    @pytest.mark.asyncio
    async def test_search_returns_assets(self, search_agent):
        queries = [
            {"platform": "fofa", "query": 'domain="example.com"'},
            {"platform": "hunter", "query": 'web.title="example"'},
        ]
        results = await search_agent.search(queries)
        assert len(results) > 0
        for asset in results:
            assert isinstance(asset, RawAsset)
            assert asset.source_platform in ("fofa", "hunter")

    @pytest.mark.asyncio
    async def test_search_deduplicates(self, search_agent):
        queries = [
            {"platform": "fofa", "query": "test"},
            {"platform": "fofa", "query": "test"},
        ]
        results = await search_agent.search(queries)
        keys = [a.dedup_key for a in results]
        assert len(keys) == len(set(keys))

    @pytest.mark.asyncio
    async def test_search_empty_queries(self, search_agent):
        results = await search_agent.search([])
        assert results == []

    @pytest.mark.asyncio
    async def test_search_skips_wrong_platform(self, search_agent):
        queries = [{"platform": "shodan", "query": "test"}]
        results = await search_agent.search(queries, platforms=["fofa"])
        assert len(results) == 0


# --- FeatureExtractorAgent ---


class TestFeatureExtractorAgent:
    def test_icp_exact_match(self):
        agent = FeatureExtractorAgent(
            target_domains=["example.com"],
            target_icp_entity="Example科技有限公司",
        )
        asset = RawAsset(icp_entity="Example科技有限公司", domain="api.example.com")
        fv = agent.extract(asset)
        assert fv.icp_entity == 1.0

    def test_icp_partial_match(self):
        agent = FeatureExtractorAgent(target_icp_entity="Example Tech Co")
        asset = RawAsset(icp_entity="Example Corp")
        fv = agent.extract(asset)
        assert 0 < fv.icp_entity < 1.0

    def test_domain_exact_root_match(self):
        agent = FeatureExtractorAgent(target_domains=["example.com"])
        asset = RawAsset(domain="example.com")
        fv = agent.extract(asset)
        assert fv.domain_pattern == 1.0

    def test_domain_subdomain_match(self):
        agent = FeatureExtractorAgent(target_domains=["example.com"])
        asset = RawAsset(domain="deep.api.example.com")
        fv = agent.extract(asset)
        # root of "deep.api.example.com" = "example.com" → exact match
        assert fv.domain_pattern == 1.0

    def test_domain_no_match(self):
        agent = FeatureExtractorAgent(target_domains=["example.com"])
        asset = RawAsset(domain="other.com")
        fv = agent.extract(asset)
        assert fv.domain_pattern == 0.0

    def test_ip_in_range(self):
        agent = FeatureExtractorAgent(target_ip_ranges=["192.168.1.0/24"])
        asset = RawAsset(ip_address="192.168.1.100")
        fv = agent.extract(asset)
        assert fv.ip_attribution == 1.0

    def test_ip_not_in_range(self):
        agent = FeatureExtractorAgent(target_ip_ranges=["192.168.1.0/24"])
        asset = RawAsset(ip_address="10.0.0.1")
        fv = agent.extract(asset)
        assert fv.ip_attribution == 0.0

    def test_header_score(self):
        agent = FeatureExtractorAgent()
        asset = RawAsset(headers={"Server": "nginx", "X-Powered-By": "Express"})
        fv = agent.extract(asset)
        assert fv.header_features > 0

    @pytest.mark.asyncio
    async def test_extract_batch(self):
        agent = FeatureExtractorAgent(target_domains=["example.com"])
        assets = [
            RawAsset(domain="example.com"),
            RawAsset(domain="other.com"),
        ]
        results = await agent.extract_batch(assets)
        assert len(results) == 2
        assert results[0].domain_pattern == 1.0
        assert results[1].domain_pattern == 0.0

    def test_empty_inputs(self):
        agent = FeatureExtractorAgent()
        asset = RawAsset()
        fv = agent.extract(asset)
        assert fv.icp_entity == 0.0
        assert fv.domain_pattern == 0.0

    def test_feature_vector_to_list(self):
        fv = FeatureVector(icp_entity=0.5, domain_pattern=0.3, ip_attribution=0.2)
        lst = fv.to_list()
        assert len(lst) == 5
        assert lst[0] == 0.5

    def test_feature_vector_weighted_score(self):
        fv = FeatureVector(icp_entity=1.0, domain_pattern=1.0, ip_attribution=1.0)
        score = fv.weighted_score()
        assert score > 0


# --- AssetAssessorAgent ---


class TestAssetAssessorAgent:
    @pytest.fixture
    def assessor(self):
        config = AssessorConfig()
        return AssetAssessorAgent(
            config=config,
            target_domains=["example.com"],
            target_icp_entity="Example科技有限公司",
            target_ip_ranges=["203.0.113.0/24"],
        )

    def test_icp_exact_match_rule(self, assessor):
        raw = RawAsset(
            domain="example.com",
            icp_entity="Example科技有限公司",
            ip_address="1.2.3.4",
        )
        fv = FeatureVector(icp_entity=1.0, domain_pattern=1.0)
        result = assessor.assess(raw, fv)
        assert result.confidence == 0.98
        assert "icp_exact_match" in result.matched_rules
        assert result.icp_verified is True

    def test_ip_range_match_rule(self, assessor):
        raw = RawAsset(
            domain="sub.example.com",
            ip_address="203.0.113.50",
            headers={"Server": "nginx"},
        )
        fv = FeatureVector(ip_attribution=1.0, domain_pattern=0.8)
        result = assessor.assess(raw, fv)
        assert "ip_range_match" in result.matched_rules
        assert result.confidence == 0.90

    def test_subdomain_match_rule(self, assessor):
        raw = RawAsset(domain="api.example.com")
        fv = FeatureVector(domain_pattern=0.8)
        result = assessor.assess(raw, fv)
        assert "subdomain_match" in result.matched_rules
        assert result.confidence == 0.88

    def test_cosine_similarity_fallback(self, assessor):
        raw = RawAsset(domain="random.com", headers={"Server": "nginx"})
        fv = FeatureVector(header_features=0.33)
        result = assessor.assess(raw, fv)
        assert result.confidence >= 0.0
        assert result.asset_type in list(AssetType)

    def test_filter_confirmed(self, assessor):
        assets = [
            AssessedAsset(
                raw=RawAsset(domain="a.com"),
                confidence=0.90,
                feature_vector=FeatureVector(),
            ),
            AssessedAsset(
                raw=RawAsset(domain="b.com"),
                confidence=0.50,
                feature_vector=FeatureVector(),
            ),
            AssessedAsset(
                raw=RawAsset(domain="c.com"),
                confidence=0.70,
                feature_vector=FeatureVector(),
            ),
        ]
        confirmed = assessor.filter_confirmed(assets)
        ids = {a.raw.domain for a in confirmed}
        assert "a.com" in ids
        assert "c.com" in ids
        assert "b.com" not in ids

    def test_classify_type_api(self, assessor):
        raw = RawAsset(domain="api.example.com", port=8080)
        assert assessor._classify_type(raw) == AssetType.API

    def test_classify_type_infra(self, assessor):
        raw = RawAsset(domain="db.example.com", port=3306)
        assert assessor._classify_type(raw) == AssetType.INFRA

    def test_classify_type_web(self, assessor):
        raw = RawAsset(domain="www.example.com", port=443)
        assert assessor._classify_type(raw) == AssetType.WEB

    def test_assess_batch(self, assessor):
        raws = [RawAsset(domain="a.com"), RawAsset(domain="b.com")]
        fvs = [FeatureVector(), FeatureVector()]
        results = assessor.assess_batch(raws, fvs)
        assert len(results) == 2


# --- AssetEnricherAgent ---


class TestAssetEnricherAgent:
    @pytest.mark.asyncio
    async def test_enrich_basic(self):
        agent = AssetEnricherAgent()
        assessed = AssessedAsset(
            raw=RawAsset(
                domain="example.com",
                ip_address="1.2.3.4",
                port=443,
                protocol="https",
                headers={"Server": "nginx/1.24.0"},
            ),
            confidence=0.9,
            feature_vector=FeatureVector(),
        )
        enriched = await agent.enrich(assessed)
        assert enriched.tech_stack == ["Nginx"]
        assert 443 in enriched.open_ports
        assert enriched.cert_info.get("issuer") == "Let's Encrypt"
        assert enriched.waf_type is None

    @pytest.mark.asyncio
    async def test_enrich_detects_waf(self):
        agent = AssetEnricherAgent()
        assessed = AssessedAsset(
            raw=RawAsset(
                domain="example.com",
                headers={"Server": "cloudflare"},
            ),
            confidence=0.8,
            feature_vector=FeatureVector(),
        )
        enriched = await agent.enrich(assessed)
        assert enriched.waf_type == "Cloudflare"

    @pytest.mark.asyncio
    async def test_enrich_batch(self):
        agent = AssetEnricherAgent()
        assets = [
            AssessedAsset(
                raw=RawAsset(domain=f"a{i}.com"), confidence=0.8,
                feature_vector=FeatureVector(),
            )
            for i in range(3)
        ]
        results = await agent.enrich_batch(assets)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_enrich_no_cert_for_http(self):
        agent = AssetEnricherAgent()
        assessed = AssessedAsset(
            raw=RawAsset(domain="example.com", port=80, protocol="http"),
            confidence=0.5,
            feature_vector=FeatureVector(),
        )
        enriched = await agent.enrich(assessed)
        assert enriched.cert_info == {}

    @pytest.mark.asyncio
    async def test_risk_level_high_no_waf(self):
        agent = AssetEnricherAgent()
        assessed = AssessedAsset(
            raw=RawAsset(domain="example.com", headers={}),
            confidence=0.95,
            feature_vector=FeatureVector(),
        )
        enriched = await agent.enrich(assessed)
        assert enriched.risk_level.value == "high"

    @pytest.mark.asyncio
    async def test_risk_level_info(self):
        agent = AssetEnricherAgent()
        assessed = AssessedAsset(
            raw=RawAsset(domain="example.com"),
            confidence=0.3,
            feature_vector=FeatureVector(),
        )
        enriched = await agent.enrich(assessed)
        assert enriched.risk_level.value == "info"
