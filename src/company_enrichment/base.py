"""Provider 抽象基类。

每个商业 API（云图/天眼查/企查查/爱企查…）实现一个 Provider，返回统一的
`EnrichmentResult`。新增 Provider 时实现该基类并在 registry 注册即可。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.company_enrichment.models import EnrichmentResult


class CompanyEnrichmentProvider(ABC):
    """企业主体关联信息采集 Provider。"""

    name: str = ""  # "yuntu" / "tianyancha" / ...

    @abstractmethod
    async def enrich(
        self,
        company_name: str,
        *,
        depth: int = 3,
        holding_min: float = 50.0,
    ) -> EnrichmentResult:
        """采集企业主体信息 + 控股子单位。

        Parameters
        ----------
        company_name:
            企业全称（或简称，由 Provider 内部做模糊匹配）。
        depth:
            穿透深度（子公司层级），默认 3 层。
        holding_min:
            持股比例下限（%），低于此值的关系不采集，默认 50%。
        """
        ...

    async def close(self) -> None:
        """释放底层资源（httpx client 等）。默认无操作。"""
        return None
