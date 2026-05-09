from __future__ import annotations

from abc import ABC, abstractmethod

from src.asset_discovery.models import RawAsset


class BaseSearchClient(ABC):
    @abstractmethod
    async def search(
        self,
        platform: str,
        query: str,
        page_size: int = 100,
        max_pages: int = 10,
    ) -> list[RawAsset]:
        ...


class BaseVectorStore(ABC):
    @abstractmethod
    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        ...

    @abstractmethod
    async def search_similar(
        self, collection: str, vector: list[float], limit: int = 10, threshold: float = 0.85
    ) -> list[dict]:
        ...


class StubSearchClient(BaseSearchClient):
    async def search(
        self,
        platform: str,
        query: str,
        page_size: int = 100,
        max_pages: int = 10,
    ) -> list[RawAsset]:
        import uuid

        return [
            RawAsset(
                domain=f"api-{uuid.uuid4().hex[:4]}.example.com",
                ip_address=f"203.0.{hash(query) % 255}.{(hash(platform) % 200) + 10}",
                port=443,
                source_platform=platform,
                source_query=query,
                title=f"{query} - Official Portal",
                headers={"Server": "nginx/1.24.0", "X-Powered-By": "Express"},
                body_snippet=f"Welcome to the {query} management system",
                icp_entity=f"{query}科技有限公司" if hash(query) % 2 == 0 else None,
            ),
            RawAsset(
                domain=f"mobile-{uuid.uuid4().hex[:4]}.example.com",
                ip_address=f"203.0.{(hash(query) + 1) % 255}.{(hash(platform) % 200) + 10}",
                port=8080,
                source_platform=platform,
                source_query=query,
                title=f"{query} - Mobile API Gateway",
                headers={"Server": "Apache/2.4.57", "X-Frame-Options": "DENY"},
                body_snippet="API gateway for mobile applications",
                icp_entity=None,
            ),
        ]


class StubVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self._store: dict[str, list[tuple[str, list[float], dict]]] = {}

    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        self._store.setdefault(collection, []).append((point_id, vector, payload))

    async def search_similar(
        self, collection: str, vector: list[float], limit: int = 10, threshold: float = 0.85
    ) -> list[dict]:
        return []
