from __future__ import annotations

import logging
from typing import Any

from src.asset_discovery.agents.asset_assessor import AssetAssessorAgent
from src.asset_discovery.agents.asset_enricher import AssetEnricherAgent
from src.asset_discovery.agents.feature_extractor import FeatureExtractorAgent
from src.asset_discovery.agents.search_engine import AssetSearchAgent
from src.asset_discovery.config import AssetDiscoveryConfig
from src.asset_discovery.models import (
    DiscoveryResult,
    DiscoveryStatus,
    EnrichedAsset,
    RiskLevel,
)
from src.asset_discovery.services.base import (
    BaseSearchClient,
    BaseVectorStore,
    StubSearchClient,
    StubVectorStore,
)

logger = logging.getLogger("eakis.asset_discovery")


class AssetDiscoveryModule:
    def __init__(
        self,
        config: AssetDiscoveryConfig | None = None,
        search_client: BaseSearchClient | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.config = config or AssetDiscoveryConfig()
        self.search_client = search_client or StubSearchClient()
        self.vector_store = vector_store or StubVectorStore()

        self.search_agent = AssetSearchAgent(self.search_client, self.config.search)
        self.extractor_agent = FeatureExtractorAgent()
        self.assessor_agent = AssetAssessorAgent(self.config.assessor)
        self.enricher_agent = AssetEnricherAgent(self.config.enricher)

        self._assets: list[EnrichedAsset] = []
        self._status: DiscoveryStatus = DiscoveryStatus.PENDING
        self._task_id: str = ""

    async def run(
        self,
        task_id: str,
        dsl_queries: list[dict[str, str]],
        company_name: str | None = None,  # noqa: ARG002
        target_domains: list[str] | None = None,
        target_icp_entity: str | None = None,
        target_ip_ranges: list[str] | None = None,
    ) -> DiscoveryResult:
        self._task_id = task_id
        self._status = DiscoveryStatus.SEARCHING
        errors: list[str] = []

        # Re-initialize agents with target context
        self.extractor_agent = FeatureExtractorAgent(
            target_domains=target_domains,
            target_icp_entity=target_icp_entity,
            target_ip_ranges=target_ip_ranges,
        )
        self.assessor_agent = AssetAssessorAgent(
            config=self.config.assessor,
            target_domains=target_domains,
            target_icp_entity=target_icp_entity,
            target_ip_ranges=target_ip_ranges,
        )

        try:
            # Stage 1: Search
            raw_assets = await self.search_agent.search(dsl_queries)
            logger.info("[%s] Asset search: %d candidates", task_id, len(raw_assets))

            # Stage 2: Feature extraction
            self._status = DiscoveryStatus.ASSESSING
            features = await self.extractor_agent.extract_batch(raw_assets)

            # Stage 3: Assessment + confidence scoring
            assessed = self.assessor_agent.assess_batch(raw_assets, features)
            confirmed = self.assessor_agent.filter_confirmed(assessed)
            logger.info(
                "[%s] Assessment: %d/%d confirmed",
                task_id, len(confirmed), len(assessed),
            )

            # Stage 4: Enrichment
            self._status = DiscoveryStatus.ENRICHING
            self._assets = await self.enricher_agent.enrich_batch(confirmed)

            # Stage 5: Vector store persistence
            if self.config.vector_store_enabled:
                await self._persist_vectors(task_id)

            self._status = DiscoveryStatus.COMPLETED

        except Exception as e:
            self._status = DiscoveryStatus.FAILED
            errors.append(str(e))
            logger.exception("[%s] Asset discovery failed", task_id)

        by_type: dict[str, int] = {}
        for a in self._assets:
            by_type[a.asset_type.value] = by_type.get(a.asset_type.value, 0) + 1

        confirmed_count = sum(1 for a in self._assets if a.confidence >= 0.85)
        avg_conf = (
            sum(a.confidence for a in self._assets) / len(self._assets)
            if self._assets else 0.0
        )

        return DiscoveryResult(
            task_id=task_id,
            status=self._status,
            total_searched=len(raw_assets) if self._status != DiscoveryStatus.FAILED else 0,
            total_candidates=len(raw_assets) if self._status != DiscoveryStatus.FAILED else 0,
            total_confirmed=confirmed_count,
            total_enriched=len(self._assets),
            by_asset_type=by_type,
            avg_confidence=round(avg_conf, 4),
            errors=errors,
        )

    def get_status(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for a in self._assets:
            by_type[a.asset_type.value] = by_type.get(a.asset_type.value, 0) + 1

        return {
            "task_id": self._task_id,
            "status": self._status.value,
            "total_assets": len(self._assets),
            "total_confirmed": sum(1 for a in self._assets if a.confidence >= 0.85),
            "by_asset_type": by_type,
            "avg_confidence": (
                round(sum(a.confidence for a in self._assets) / len(self._assets), 4)
                if self._assets else 0.0
            ),
        }

    def get_assets(
        self,
        risk: str | None = None,
        confirmed: bool | None = None,
        asset_type: str | None = None,
        icp_verified: bool | None = None,
        has_waf: bool | None = None,
        tech_stack: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        filtered = self._assets
        if risk:
            filtered = [a for a in filtered if a.risk_level.value == risk]
        if confirmed is not None:
            filtered = [a for a in filtered if a.confirmed == confirmed]
        if asset_type:
            filtered = [a for a in filtered if a.asset_type.value == asset_type]
        if icp_verified is not None:
            filtered = [a for a in filtered if a.icp_verified == icp_verified]
        if has_waf is not None:
            filtered = [a for a in filtered if bool(a.waf_type) == has_waf]
        if tech_stack:
            filtered = [
                a for a in filtered
                if any(tech_stack.lower() in t.lower() for t in a.tech_stack)
            ]

        total = len(filtered)
        start = (page - 1) * page_size
        items = [self._asset_to_dict(a) for a in filtered[start : start + page_size]]
        return items, total

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        for a in self._assets:
            if a.asset_id == asset_id:
                return self._asset_to_dict(a)
        return None

    def update_asset(
        self,
        asset_id: str,
        confirmed: bool | None = None,
        risk_level: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        for a in self._assets:
            if a.asset_id == asset_id:
                if confirmed is not None:
                    a.confirmed = confirmed
                if risk_level is not None:
                    a.risk_level = RiskLevel(risk_level)
                if notes is not None:
                    a.notes = notes
                return self._asset_to_dict(a)
        return None

    async def _persist_vectors(self, task_id: str) -> None:
        for asset in self._assets:
            await self.vector_store.upsert(
                collection="target_asset_features",
                point_id=asset.asset_id,
                vector=[0.0] * 768,  # Placeholder for real embedding
                payload={
                    "task_id": task_id,
                    "domain": asset.domain,
                    "ip": asset.ip_address,
                    "asset_type": asset.asset_type.value,
                    "confidence": asset.confidence,
                    "icp_verified": asset.icp_verified,
                },
            )

    @staticmethod
    def _asset_to_dict(asset: EnrichedAsset) -> dict[str, Any]:
        return {
            "id": asset.asset_id,
            "domain": asset.domain,
            "ip_address": asset.ip_address,
            "port": asset.port,
            "protocol": asset.raw.protocol,
            "asset_type": asset.asset_type.value,
            "confidence": asset.confidence,
            "risk_level": asset.risk_level.value,
            "icp_verified": asset.icp_verified,
            "icp_entity": asset.raw.icp_entity,
            "waf_detected": asset.waf_type,
            "tech_stack": asset.tech_stack,
            "open_ports": asset.open_ports,
            "cert_info": asset.cert_info,
            "screenshot_path": asset.screenshot_path,
            "confirmed": asset.confirmed,
            "notes": asset.notes,
            "discovered_at": asset.raw.metadata.get("discovered_at"),
        }
