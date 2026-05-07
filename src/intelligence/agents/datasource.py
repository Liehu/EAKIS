import logging

from src.intelligence.engine_specs import load_engine_specs
from src.intelligence.models import DataSource, SourceCategory
from src.intelligence.services.base import BaseRAGClient

logger = logging.getLogger("eakis.intelligence.datasource")


def _build_asset_engine_sources() -> list[DataSource]:
    sources: list[DataSource] = []
    priority = 9
    for name, spec in load_engine_specs().items():
        sources.append(DataSource(
            source_id=name,
            name=spec.display_name,
            category=SourceCategory.ASSET_ENGINE,
            priority=priority,
            expected_yield=round(0.5 + 0.1 * priority / 9, 2),
            rate_limit=spec.rate_limit,
        ))
        priority = max(priority - 1, 5)
    return sources


STATIC_CATALOG = {
    SourceCategory.NEWS: [
        DataSource(source_id="baidu_news", name="百度新闻", category=SourceCategory.NEWS, priority=7, expected_yield=0.7, rate_limit=2.0),
        DataSource(source_id="wechat", name="微信公众号", category=SourceCategory.NEWS, priority=6, expected_yield=0.6, rate_limit=1.0),
        DataSource(source_id="36kr", name="36氪", category=SourceCategory.NEWS, priority=5, expected_yield=0.5, rate_limit=3.0),
    ],
    SourceCategory.OFFICIAL: [
        DataSource(source_id="official_site", name="企业官网", category=SourceCategory.OFFICIAL, priority=8, expected_yield=0.8, rate_limit=5.0),
        DataSource(source_id="github_org", name="GitHub 组织页", category=SourceCategory.OFFICIAL, priority=6, expected_yield=0.4, rate_limit=10.0),
        DataSource(source_id="tech_blog", name="技术博客", category=SourceCategory.OFFICIAL, priority=5, expected_yield=0.5, rate_limit=5.0),
    ],
    SourceCategory.LEGAL: [
        DataSource(source_id="icp_query", name="ICP备案查询", category=SourceCategory.LEGAL, priority=9, expected_yield=0.9, rate_limit=1.0),
        DataSource(source_id="business_info", name="工商信息", category=SourceCategory.LEGAL, priority=7, expected_yield=0.7, rate_limit=1.0),
        DataSource(source_id="bidding", name="招投标公告", category=SourceCategory.LEGAL, priority=4, expected_yield=0.3, rate_limit=2.0),
    ],
    SourceCategory.SECURITY: [
        DataSource(source_id="cnvd", name="CNVD漏洞库", category=SourceCategory.SECURITY, priority=6, expected_yield=0.5, rate_limit=5.0),
        DataSource(source_id="nvd", name="NVD数据库", category=SourceCategory.SECURITY, priority=5, expected_yield=0.4, rate_limit=10.0),
    ],
}


class DataSourceAgent:
    def __init__(self, rag_client: BaseRAGClient) -> None:
        self.rag_client = rag_client

    async def select_sources(
        self,
        company_name: str,
        industry: str | None = None,
        enabled_categories: list[SourceCategory] | None = None,
    ) -> list[DataSource]:
        categories = enabled_categories or [SourceCategory.NEWS, SourceCategory.OFFICIAL, SourceCategory.LEGAL, SourceCategory.ASSET_ENGINE]

        rag_hints = await self._query_rag_history(company_name, industry)

        sources: list[DataSource] = []
        for cat in categories:
            if cat == SourceCategory.ASSET_ENGINE:
                cat_sources = _build_asset_engine_sources()
            else:
                cat_sources = STATIC_CATALOG.get(cat, [])
            for src in cat_sources:
                effective = rag_hints.get(src.source_id)
                if effective is not None:
                    src.expected_yield = effective
                sources.append(src)

        sources.sort(key=lambda s: s.priority, reverse=True)
        logger.info("为 %s 选择了 %d 个数据源", company_name, len(sources))
        return sources

    async def _query_rag_history(self, company_name: str, industry: str | None) -> dict[str, float]:
        try:
            results = await self.rag_client.search(f"{company_name} {industry or ''} 有效数据源", top_k=5)
            hints: dict[str, float] = {}
            for r in results:
                meta = r.get("metadata", {})
                if "source_id" in meta and "yield" in meta:
                    hints[meta["source_id"]] = meta["yield"]
            return hints
        except Exception:
            logger.debug("RAG历史查询失败，使用默认优先级")
            return {}
