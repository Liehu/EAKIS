"""合规情报爬虫：ICP 备案 + 招投标（真实数据源组合）。

保留 LegalScraper 名字向后兼容；实际拆分为：
  - IcpScraper（icp_scraper.py）：第三方备案查询 API
  - BiddingScraper（bidding_scraper.py）：中国政府采购网 ccgp
"""

from __future__ import annotations

import logging

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument
from src.intelligence.scrapers.bidding_scraper import BiddingScraper
from src.intelligence.scrapers.icp_scraper import IcpScraper
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.legal")


class LegalScraper(BaseScraper):
    """组合爬虫：同时执行 ICP 备案查询（query 含域名时）与招投标检索。"""

    def __init__(self) -> None:
        self._icp = IcpScraper()
        self._bidding = BiddingScraper()

    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        icp_docs = await self._icp.scrape(query, config)
        bid_docs = await self._bidding.scrape(query, config)
        return icp_docs + bid_docs
