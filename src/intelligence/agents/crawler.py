import asyncio
import logging

from src.intelligence.anti_crawl.middleware import AntiCrawlMiddleware, RequestContext
from src.intelligence.config import CrawlConfig
from src.intelligence.engine_specs import load_engine_specs
from src.intelligence.models import CollectionStatus, DataSource, DslQuery, RawDocument
from src.intelligence.services.base import BaseScraper
from src.intelligence.scrapers.generic_scraper import GenericEngineScraper
from src.intelligence.scrapers.legal_scraper import LegalScraper
from src.intelligence.scrapers.news_scraper import NewsScraper
from src.intelligence.scrapers.official_scraper import OfficialScraper
from src.shared.event_bus import EventBus

logger = logging.getLogger("eakis.intelligence.crawler")


def _build_scraper_map() -> dict[str, BaseScraper]:
    scrapers: dict[str, BaseScraper] = {
        "baidu_news": NewsScraper(),
        "wechat": NewsScraper(),
        "36kr": NewsScraper(),
        "official_site": OfficialScraper(),
        "github_org": OfficialScraper(),
        "tech_blog": OfficialScraper(),
        "icp_query": LegalScraper(),
        "business_info": LegalScraper(),
        "bidding": LegalScraper(),
    }

    for engine_name in load_engine_specs():
        scrapers[engine_name] = GenericEngineScraper(engine_name)

    return scrapers


class CrawlerAgent:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        scraper_overrides: dict[str, BaseScraper] | None = None,
        anti_crawl: AntiCrawlMiddleware | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.anti_crawl = anti_crawl
        self._scrapers = _build_scraper_map()
        if scraper_overrides:
            self._scrapers.update(scraper_overrides)

    async def crawl(
        self,
        sources: list[DataSource],
        dsl_queries: list[DslQuery] | None = None,
        company_name: str = "",
        config: CrawlConfig | None = None,
    ) -> list[RawDocument]:
        config = config or CrawlConfig()
        all_docs: list[RawDocument] = []
        dsl_map = {q.platform: q.query for q in (dsl_queries or [])}

        if self.anti_crawl and not self.anti_crawl._initialized:
            await self.anti_crawl.initialize()

        semaphore = asyncio.Semaphore(config.max_concurrent_sources)

        async def _crawl_source(source: DataSource) -> list[RawDocument]:
            async with semaphore:
                return await self._crawl_single(source, company_name, dsl_map, config)

        tasks = [_crawl_source(s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                source.status = CollectionStatus.PARTIAL_FAILURE
                source.error_message = str(result)
                logger.error("数据源 %s 爬取失败: %s", source.name, result)
                continue
            docs = result
            source.items_crawled = len(docs)
            source.status = CollectionStatus.COMPLETED
            all_docs.extend(docs)
            logger.info("数据源 %s 爬取完成，获取 %d 条", source.name, len(docs))
            if self.event_bus:
                await self.event_bus.publish("osint.crawl.complete", {
                    "source_name": source.name,
                    "items_count": len(docs),
                })

        return all_docs

    async def _crawl_single(
        self,
        source: DataSource,
        company_name: str,
        dsl_map: dict[str, str],
        config: CrawlConfig,
    ) -> list[RawDocument]:
        scraper = self._scrapers.get(source.source_id)
        if not scraper:
            logger.warning("未找到数据源 %s 的爬虫，跳过", source.source_id)
            return []

        query = dsl_map.get(source.source_id, company_name)

        ctx: RequestContext | None = None
        try:
            if self.anti_crawl:
                ctx = await self.anti_crawl.before_request(source.source_id)
            docs = await scraper.scrape(query, config)
            if ctx:
                await self.anti_crawl.after_request(ctx, success=True)
            return docs
        except Exception:
            if ctx:
                await self.anti_crawl.after_request(ctx, success=False)
            raise
