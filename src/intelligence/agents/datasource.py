import logging
from enum import Enum

import yaml

from src.core.config_paths import DATASOURCES_YAML
from src.intelligence.engine_specs import load_engine_specs
from src.intelligence.models import DataSource, SourceCategory
from src.intelligence.services.base import BaseRAGClient

logger = logging.getLogger("eakis.intelligence.datasource")

# YAML category -> SourceCategory 映射
_CATEGORY_MAP = {
    "NEWS": SourceCategory.NEWS,
    "OFFICIAL": SourceCategory.OFFICIAL,
    "LEGAL": SourceCategory.LEGAL,
    "SECURITY": SourceCategory.SECURITY,
    "ASSET_ENGINE": SourceCategory.ASSET_ENGINE,
}


def _load_datasource_catalog() -> dict[SourceCategory, list[DataSource]]:
    """从 datasources.yaml 加载静态数据源目录。"""
    if not DATASOURCES_YAML.exists():
        logger.warning("数据源配置文件不存在: %s，使用默认空目录", DATASOURCES_YAML)
        return {}

    try:
        with open(DATASOURCES_YAML, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        catalog: dict[SourceCategory, list[DataSource]] = {}
        for item in data.get("dataSources", []):
            try:
                category_str = item.get("category")
                category = _CATEGORY_MAP.get(category_str)
                if not category:
                    logger.warning("未知的数据源类别: %s", category_str)
                    continue

                ds = DataSource(
                    source_id=item["sourceId"],
                    name=item["name"],
                    category=category,
                    priority=item.get("priority", 5),
                    expected_yield=item.get("expectedYield", 0.5),
                    rate_limit=item.get("rateLimit", 1.0),
                )

                catalog.setdefault(category, []).append(ds)
            except Exception as e:
                logger.warning("解析数据源配置失败: %s, 错误: %s", item, e)

        logger.info("从 %s 加载了 %d 个类别共 %d 个数据源",
                    DATASOURCES_YAML, len(catalog), sum(len(v) for v in catalog.values()))
        return catalog

    except Exception as e:
        logger.error("加载数据源配置失败: %s", e)
        return {}


# 全局缓存的数据源目录
_DATASOURCE_CATALOG: dict[SourceCategory, list[DataSource]] | None = None


def get_datasource_catalog() -> dict[SourceCategory, list[DataSource]]:
    """获取数据源目录（带缓存）。"""
    global _DATASOURCE_CATALOG
    if _DATASOURCE_CATALOG is None:
        _DATASOURCE_CATALOG = _load_datasource_catalog()
    return _DATASOURCE_CATALOG


def reload_datasource_catalog() -> dict[SourceCategory, list[DataSource]]:
    """重新加载数据源目录。"""
    global _DATASOURCE_CATALOG
    _DATASOURCE_CATALOG = _load_datasource_catalog()
    return _DATASOURCE_CATALOG


def _build_asset_engine_sources() -> list[DataSource]:
    """从 engines.yaml 构建资产引擎数据源。"""
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


class DataSourceAgent:
    """数据源选择 Agent - 从配置文件加载可用的数据源。"""

    def __init__(self, rag_client: BaseRAGClient) -> None:
        self.rag_client = rag_client
        self._catalog = get_datasource_catalog()

    async def select_sources(
        self,
        company_name: str,
        industry: str | None = None,
        enabled_categories: list[SourceCategory] | None = None,
    ) -> list[DataSource]:
        """根据公司和行业选择合适的数据源。"""
        categories = enabled_categories or [
            SourceCategory.NEWS,
            SourceCategory.OFFICIAL,
            SourceCategory.LEGAL,
            SourceCategory.ASSET_ENGINE,
        ]

        rag_hints = await self._query_rag_history(company_name, industry)

        sources: list[DataSource] = []
        for cat in categories:
            if cat == SourceCategory.ASSET_ENGINE:
                cat_sources = _build_asset_engine_sources()
            else:
                cat_sources = self._catalog.get(cat, [])
            for src in cat_sources:
                # 深拷贝避免修改原始数据
                src = DataSource(**src.__dict__)
                effective = rag_hints.get(src.source_id)
                if effective is not None:
                    src.expected_yield = effective
                sources.append(src)

        sources.sort(key=lambda s: s.priority, reverse=True)
        logger.info("为 %s 选择了 %d 个数据源", company_name, len(sources))
        return sources

    async def _query_rag_history(self, company_name: str, industry: str | None) -> dict[str, float]:
        """查询 RAG 历史记录中的数据源效果。"""
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
