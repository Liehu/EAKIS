import asyncio
import base64
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config_paths import get_engine_specs
from src.intelligence.config import CrawlConfig
from src.intelligence.engine_specs import encode_query, load_engine_specs
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.generic_scraper")


class GenericEngineScraper(BaseScraper):
    """通用引擎爬虫：根据 engine_specs.yaml 中的配置处理任意引擎。

    配置说明：
    - enabled=true  → 使用真实 API 调用
    - enabled=false → 使用 stub 模式返回模拟数据
    - api_key      → API 密钥（真实模式需要）

    query_encoding 支持 base64 / url / none。
    """
    def __init__(self, engine_name: str, config: dict | None = None) -> None:
        self.engine_name = engine_name
        self._config = config or {}
        self._spec = None
        specs = load_engine_specs()
        if engine_name in specs:
            self._spec = specs[engine_name]

    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        """根据配置选择真实 API 或 stub 模式"""
        display_name = self._spec.display_name if self._spec else self.engine_name

        # 检查是否启用真实 API
        use_real_api = self._config.get("enabled", False)
        api_key = self._config.get("api_key", "")

        if use_real_api and api_key:
            logger.info(f"[{display_name}] 使用真实 API 模式")
            return await self._real_search(query, config)
        else:
            logger.info(f"[{display_name}] 使用 stub 模式（配置 enabled={use_real_api}, has_api_key={bool(api_key)})")
            return self._stub_response(query, display_name)

    async def _real_search(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        """执行真实的 API 搜索"""
        if not self._spec or not self._spec.search_url:
            logger.warning(f"[{self.engine_name}] 缺少 search_url 配置")
            return []

        encoded_query = self._encode(query)

        # 构建请求参数
        params = {self._spec.query_param: encoded_query}

        # 添加认证
        headers = {}
        api_key = self._config.get("api_key", "")
        if api_key:
            auth_type = self._config.get("auth_type", self._spec.auth_type or "")
            if "email+apikey" in auth_type:
                email = self._config.get("email", "")
                credentials = base64.b64encode(f"{email}:{api_key}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
            elif "apikey" in auth_type:
                params["apikey"] = api_key
            elif "bearer" in auth_type:
                headers["Authorization"] = f"Bearer {api_key}"

        # 设置超时和结果数量
        timeout = self._config.get("request_timeout", 30)
        max_results = self._config.get("max_results", 100)
        if self._spec.pagination and self._spec.pagination.size_param:
            params[self._spec.pagination.size_param] = max_results

        # 执行请求
        search_url = self._spec.search_url
        logger.info(f"[{self.engine_name}] 请求: {search_url}")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(search_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.engine_name}] API 请求失败: {e.response.status_code}")
            logger.error(f"响应内容: {e.response.text[:500]}")
            return []
        except Exception as e:
            logger.error(f"[{self.engine_name}] API 调用异常: {e}")
            return []

        # 解析响应
        docs = []
        results = self._extract_results(data)

        for item in results:
            content = self._format_result(item)
            docs.append(RawDocument(
                content=content,
                source_type=SourceCategory.ASSET_ENGINE,
                source_name=self._spec.display_name,
                source_url=f"{search_url}?{self._spec.query_param}={encoded_query}",
                published_at=datetime.now(timezone.utc),
            ))

        logger.info(f"[{self.engine_name}] 真实搜索返回 {len(docs)} 条结果")
        return docs

    def _extract_results(self, data: dict) -> list:
        """从 API 响应中提取结果列表"""
        result_path = self._config.get("response_path") if self._config else None
        result_path = result_path or (self._spec.response_path if self._spec else "results")

        if not result_path:
            return [data] if isinstance(data, dict) else []

        # 按路径提取
        current = data
        for key in result_path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return []

        return current if isinstance(current, list) else []

    def _format_result(self, item: dict) -> str:
        """格式化单条结果为字符串"""
        # 简单返回 JSON 格式
        import json
        return json.dumps(item, ensure_ascii=False)

    def _stub_response(self, query: str, display_name: str) -> list[RawDocument]:
        """Stub 模式：返回模拟数据"""
        encoded = self._encode(query)

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
        encoding = self._config.get("query_encoding") or self._spec.query_encoding
        return encode_query(query, encoding)

    def _build_url(self, encoded_query: str) -> str:
        if not self._spec:
            return f"https://{self.engine_name}.example.com/search"
        search_url = self._config.get("search_url") or self._spec.search_url
        sep = "&" if "?" in search_url else "?"
        query_param = self._config.get("query_param") or self._spec.query_param
        return f"{search_url}{sep}{query_param}={encoded_query}"


def build_scraper_map() -> dict[str, BaseScraper]:
    """构建爬虫映射，支持从配置文件读取密钥"""
    from src.intelligence.config import get_engine_specs

    specs = load_engine_specs()
    scrapers: dict[str, BaseScraper] = {}

    for engine_name in specs:
        # 从配置读取引擎配置
        engine_configs = get_engine_specs()
        engine_config = engine_configs.get(engine_name, {})
        scrapers[engine_name] = GenericEngineScraper(engine_name, engine_config)

    logger.info(f"构建爬虫映射，支持 {len(scrapers)} 个引擎: {list(scrapers.keys())}")
    return scrapers
