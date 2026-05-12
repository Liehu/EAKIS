import random
import uuid
from datetime import datetime, timezone

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

STUB_NEWS = [
    "XX科技有限公司近日完成新一轮融资，估值突破百亿",
    "XX科技发布全新支付系统，基于Spring Boot微服务架构",
    "XX科技获得多项技术专利，涉及分布式系统和数据安全",
    "XX科技与多家银行达成战略合作，拓展金融科技业务",
    "XX科技参与编写行业技术标准，推动规范化发展",
]


class NewsScraper(BaseScraper):
    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        count = random.randint(3, 8)
        return [
            RawDocument(
                content=f"[新闻报道] {news} —— 关键词：{query}",
                source_type=SourceCategory.NEWS,
                source_name="百度新闻",
                source_url=f"https://news.example.com/{uuid.uuid4().hex[:8]}",
                published_at=datetime.now(timezone.utc),
            )
            for news in random.sample(STUB_NEWS, min(count, len(STUB_NEWS)))
        ]
