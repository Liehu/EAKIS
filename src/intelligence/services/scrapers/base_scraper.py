from src.intelligence.services.base import BaseScraper


class StubScraper(BaseScraper):
    async def scrape(self, query: str, config=None) -> list:
        return []
