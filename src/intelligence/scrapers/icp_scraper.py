"""ICP 备案查询爬虫（真实数据源）。

通过可配置的第三方备案查询 API 查询域名备案信息：
  - API 模板从环境变量/设置读取：ICP_API_URL（占位符 {domain}），可选 ICP_API_KEY（Bearer）
  - 未配置时使用内置免费提供方列表（vvhan / ooomn 风格 JSON API）
  - 解析常见 JSON 字段形状（icp/icpCode/number + unitName/mainUnit/company）

查询失败时返回 None / 空列表并记录日志——绝不产假数据。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper

logger = logging.getLogger("eakis.intelligence.icp")

# 内置免费提供方（{domain} 占位）；均可能失效，按序尝试
_DEFAULT_PROVIDERS = [
    "https://api.vvhan.com/api/icp?domain={domain}",
    "https://api.ooomn.com/api/icp?domain={domain}",
]

_TIMEOUT = 15.0

# 常见 JSON 响应中的备案号/主体字段名
_ICP_NUMBER_KEYS = ("icp", "icpCode", "icp_number", "number", "license", "beian")
_ENTITY_KEYS = ("unitName", "mainUnit", "company", "unit", "owner", "serviceName", "name")


def _providers() -> list[str]:
    custom = os.environ.get("ICP_API_URL", "")
    return ([custom] if custom else []) + _DEFAULT_PROVIDERS


def _find_field(data: Any, keys: tuple[str, ...]) -> str | None:
    """在（可能嵌套的）JSON 里按候选键名找第一个非空字符串值。"""
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in data.values():
            found = _find_field(v, keys)
            if found:
                return found
    elif isinstance(data, list):
        for v in data:
            found = _find_field(v, keys)
            if found:
                return found
    return None


async def query_icp(domain: str) -> dict | None:
    """查询单个域名的 ICP 备案。返回 {icp_number, icp_entity, provider, raw} 或 None。"""
    domain = domain.strip().lower().lstrip("*.").split("/")[0]
    if "." not in domain:
        return None

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    api_key = os.environ.get("ICP_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        for template in _providers():
            url = template.format(domain=domain)
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200 or not resp.content.strip():
                    logger.info("ICP 提供方 %s 无有效响应 (%s)", url, resp.status_code)
                    continue
                try:
                    data = resp.json()
                except ValueError:
                    logger.info("ICP 提供方 %s 返回非 JSON", url)
                    continue
                number = _find_field(data, _ICP_NUMBER_KEYS)
                entity = _find_field(data, _ENTITY_KEYS)
                if number or entity:
                    logger.info("ICP 查询成功 %s → %s / %s", domain, number, entity)
                    return {
                        "domain": domain,
                        "icp_number": number,
                        "icp_entity": entity,
                        "provider": url.split("?")[0],
                        "raw": data if isinstance(data, dict) else {"data": data},
                    }
            except Exception as exc:  # noqa: BLE001
                logger.warning("ICP 提供方 %s 请求异常: %s", url, exc)

    logger.warning("ICP 查询失败：所有提供方均无结果 (%s)", domain)
    return None


class IcpScraper(BaseScraper):
    """ICP 备案查询爬虫：query 为域名（含点号）时真实查询。"""

    async def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
        target = query.strip()
        if "." not in target or " " in target:
            # query 是企业名而非域名——备案查询需要域名，交给 task 层用 company.domains 查
            logger.info("ICP 查询需要域名，跳过非域名 query: %r", query[:50])
            return []

        info = await query_icp(target)
        if info is None:
            return []
        content = (
            f"ICP备案查询：{info['domain']} 备案号 {info.get('icp_number') or '未知'}，"
            f"备案主体 {info.get('icp_entity') or '未知'}（来源 {info['provider']}）"
        )
        return [RawDocument(
            content=content,
            source_type=SourceCategory.LEGAL,
            source_name="ICP备案查询",
            source_url=info["provider"],
            published_at=datetime.now(timezone.utc),
            metadata={"icp": info},
        )]
