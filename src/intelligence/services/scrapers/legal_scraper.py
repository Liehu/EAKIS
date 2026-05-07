import uuid
from datetime import datetime, timezone

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper


class LegalScraper(BaseScraper):
    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        return [
            RawDocument(
                content=f"ICP备案查询：{query}备案号京ICP备2024XXXXX号，备案主体为{query}科技有限公司",
                source_type=SourceCategory.LEGAL,
                source_name="ICP备案查询",
                source_url=f"https://icp.example.com/query/{uuid.uuid4().hex[:8]}",
                published_at=datetime.now(timezone.utc),
            ),
            RawDocument(
                content=f"招投标公告：{query}发布云安全平台采购项目招标，预算500万元",
                source_type=SourceCategory.LEGAL,
                source_name="招投标公告",
                source_url=f"https://bid.example.com/{uuid.uuid4().hex[:8]}",
                published_at=datetime.now(timezone.utc),
            ),
        ]
