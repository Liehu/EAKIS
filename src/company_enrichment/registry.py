"""Provider 注册表。

新增商业 API（天眼查/企查查/爱企查…）时：
1. 实现 `CompanyEnrichmentProvider` 子类（放在 providers/ 下）。
2. 在 `_build_providers()` 注册。
3. 前端 Provider 选择下拉自动获得新选项（通过 list_providers 端点）。
"""

from __future__ import annotations

from functools import lru_cache

from src.company_enrichment.base import CompanyEnrichmentProvider
from src.company_enrichment.providers.yuntu import YunTuProvider
from src.shared.exceptions import CompanyEnrichmentError


@lru_cache
def _build_providers() -> dict[str, CompanyEnrichmentProvider]:
    """构建 provider 名 → 实例的映射。

    后续接入天眼查/企查查/爱企查时在此追加。未配置凭证的 provider 仍注册
    （走各自的 stub 模式），前端可展示但不发真实请求。
    """
    providers: dict[str, CompanyEnrichmentProvider] = {
        "yuntu": YunTuProvider(),
        # 预留（实现后取消注释）：
        # "tianyancha": TianYanChaProvider(),
        # "qichacha": QiChaChaProvider(),
        # "aiqicha": AiQiChaProvider(),
    }
    return providers


def get_provider(name: str = "yuntu") -> CompanyEnrichmentProvider:
    """按名称取 provider 实例。不存在时抛 CompanyEnrichmentError。"""
    providers = _build_providers()
    if name not in providers:
        available = ", ".join(providers) or "(无)"
        raise CompanyEnrichmentError(f"未知的采集 provider: {name}（可用: {available}）")
    return providers[name]


def list_providers() -> list[str]:
    """列出所有已注册的 provider 名称（供前端下拉）。"""
    return list(_build_providers().keys())
