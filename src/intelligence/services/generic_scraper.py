import uuid
from datetime import datetime, timezone

from src.intelligence.config import CrawlConfig
from src.intelligence.engine_specs import encode_query, load_engine_specs
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper


class GenericEngineScraper(BaseScraper):
    """通用引擎爬虫：根据 engine_specs.yaml 中的配置处理任意引擎。
    Stub 模式下返回模拟数据；真实模式下按 search_url + auth 拼接请求。
    query_encoding 支持 base64 / url / none。
    """

    def __init__(self, engine_name: str) -> None:
        self.engine_name = engine_name
        self._spec = None
        specs = load_engine_specs()
        if engine_name in specs:
            self._spec = specs[engine_name]

    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        display_name = self._spec.display_name if self._spec else self.engine_name
        encoded = self._encode(query)

        # Stub 模式：返回模拟数据（encoded query 写入 source_url 供调试）
        return [
            RawDocument(
                content=f"[{display_name}] 资产发现：{query}关联域名 example-{uuid.uuid4().hex[:4]}.com，"
                        f"开放端口80/443/8080，技术栈Nginx/Spring Boot",
                source_type=SourceCategory.ASSET_ENGINE,
                source_name=display_name,
                source_url=self._build_url(encoded),
                published_at=datetime.now(timezone.utc),
            ),
            RawDocument(
                content=f"[{display_name}] SSL证书信息：{query}关联域名使用Let's Encrypt证书，"
                        f"有效期至2025年底",
                source_type=SourceCategory.ASSET_ENGINE,
                source_name=display_name,
                source_url=self._build_url(encoded),
                published_at=datetime.now(timezone.utc),
            ),
        ]

    def _encode(self, query: str) -> str:
        if not self._spec:
            return query
        return encode_query(query, self._spec.query_encoding)

    def _build_url(self, encoded_query: str) -> str:
        if not self._spec:
            return f"https://{self.engine_name}.example.com/search"
        sep = "&" if "?" in self._spec.search_url else "?"
        return f"{self._spec.search_url}{sep}{self._spec.query_param}={encoded_query}"
