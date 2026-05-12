import uuid
from datetime import datetime, timezone

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper


class OfficialScraper(BaseScraper):
    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        return [
            RawDocument(
                content=f"{query}官方网站产品介绍：提供企业级解决方案，技术栈包括Java、微服务、Kubernetes",
                source_type=SourceCategory.OFFICIAL,
                source_name="企业官网",
                source_url=f"https://www.{query.lower().replace(' ', '')}.example.com",
                published_at=datetime.now(timezone.utc),
            ),
            RawDocument(
                content=f"{query}技术博客：深入解析微服务架构设计与DevOps实践",
                source_type=SourceCategory.OFFICIAL,
                source_name="技术博客",
                source_url=f"https://blog.{query.lower().replace(' ', '')}.example.com",
                published_at=datetime.now(timezone.utc),
            ),
        ]
