"""域名资产发现链路：seed 域名 → 实际资产 dict 列表。

链路（每步真实调用 CLI 工具，工具缺失时该步降级为空并记录）：
  1. subfinder + crt.sh → 子域名集合
  2. dnsx → 子域名解析 IP
  3. httpx → 存活 HTTP 资产（标题/端口/技术栈）
  4. naabu → 对解析出的 IP 做端口扫描，回填 open_ports

输出 dict 字段与 persistence.upsert_assets 兼容。
"""

from __future__ import annotations

import logging

from src.asset_discovery.models import RawAsset
from src.asset_discovery.services.base import BaseSearchClient

logger = logging.getLogger("eakis.asset_discovery.pipeline")

# 单任务防爆炸上限
_MAX_SUBDOMAINS = 500
_MAX_HTTP_TARGETS = 300
_MAX_NAABU_TARGETS = 100


def _asset_to_dict(a: RawAsset) -> dict:
    return {
        "domain": a.domain,
        "ip_address": a.ip_address,
        "port": a.port,
        "protocol": a.protocol,
        "asset_type": "web" if a.source_platform == "httpx" else "domain",
        "confidence": 0.9 if a.source_platform == "httpx" else 0.6,
        "icp_verified": False,
        "icp_entity": a.icp_entity,
        "tech_stack": a.metadata.get("tech", []),
        "open_ports": [a.port] if a.port else [],
        "cert_info": a.cert_info or None,
        "risk_level": "info",
        "confirmed": a.source_platform == "httpx",
        "notes": f"source={a.source_platform}",
        "source_platforms": [a.source_platform],
    }


def _merge(base: dict, extra: RawAsset) -> dict:
    """把后续工具的结果合入已有资产 dict（端口合并、置信度取大、来源累加）。"""
    if extra.port and extra.port not in (base.get("open_ports") or []):
        base["open_ports"] = sorted((base.get("open_ports") or []) + [extra.port])
    if extra.source_platform not in base["source_platforms"]:
        base["source_platforms"].append(extra.source_platform)
        # 多来源命中提升置信度
        base["confidence"] = min(1.0, (base.get("confidence") or 0.5) + 0.05)
    if extra.ip_address and not base.get("ip_address"):
        base["ip_address"] = extra.ip_address
    if extra.domain and not base.get("domain"):
        base["domain"] = extra.domain
    for t in extra.metadata.get("tech", []):
        if t not in (base.get("tech_stack") or []):
            base["tech_stack"] = (base.get("tech_stack") or []) + [t]
    return base


async def run_domain_pipeline(
    client: BaseSearchClient,
    seed_domains: list[str],
    enable_portscan: bool = True,
) -> tuple[list[dict], list[str]]:
    """执行完整域名发现链路，返回 (资产 dict 列表, 降级/错误信息列表)。"""
    errors: list[str] = []
    seeds = [d.strip().lower() for d in seed_domains if d and d.strip()]
    if not seeds:
        return [], ["无种子域名（企业缺少 domains/email_domains）"]

    def _warn(msg: str) -> None:
        logger.warning(msg)
        errors.append(msg)

    # ── 1. 子域名枚举（subfinder + crt.sh 证书） ──
    subdomains: set[str] = set(seeds)
    for domain in seeds:
        for platform in ("subfinder", "cert"):
            found = await client.search(platform, domain)
            if found:
                for a in found:
                    if a.domain:
                        subdomains.add(a.domain.lower().rstrip("."))
            else:
                _warn(f"{platform} 对 {domain} 无结果或工具不可用")
    subdomains = set(sorted(subdomains)[:_MAX_SUBDOMAINS])
    logger.info("子域名枚举完成：%d 个", len(subdomains))

    # ── 2. DNS 解析 ──
    resolved: dict[str, str] = {}  # subdomain → ip
    # dnsx 客户端一次只查一个域名，逐个循环
    for sub in subdomains:
        for a in await client.search("dnsx", sub):
            if a.ip_address:
                resolved.setdefault(sub, a.ip_address)
    if not resolved:
        _warn("dnsx 无解析结果或工具不可用")
    logger.info("DNS 解析完成：%d/%d", len(resolved), len(subdomains))

    # ── 3. HTTP 存活探测 ──
    assets_by_key: dict[tuple, dict] = {}
    http_targets = list(resolved.keys())[:_MAX_HTTP_TARGETS]
    for sub in http_targets:
        for a in await client.search("httpx", sub):
            key = (a.domain or sub, a.ip_address or resolved.get(sub), a.port)
            d = _asset_to_dict(a)
            if not d["domain"]:
                d["domain"] = sub
            if not d["ip_address"]:
                d["ip_address"] = resolved.get(sub)
            if key in assets_by_key:
                assets_by_key[key] = _merge(assets_by_key[key], a)
            else:
                assets_by_key[key] = d
    if not assets_by_key:
        _warn("httpx 无存活资产或工具不可用")
    logger.info("HTTP 探测完成：%d 个存活资产", len(assets_by_key))

    # ── 4. 端口扫描（对唯一 IP） ──
    if enable_portscan:
        unique_ips: set[str] = {ip for ip in resolved.values()}
        for ip in list(unique_ips)[:_MAX_NAABU_TARGETS]:
            for a in await client.search("naabu", ip):
                # 找同 IP 的现有资产合并端口；没有则新建 infra 资产
                target = next(
                    (d for d in assets_by_key.values() if d.get("ip_address") == ip), None)
                if target is not None:
                    _merge(target, a)
                else:
                    d = _asset_to_dict(a)
                    d["asset_type"] = "ip"
                    assets_by_key[(None, ip, a.port)] = d
        if not any(d.get("open_ports") for d in assets_by_key.values()):
            _warn("naabu 无端口结果或工具不可用")

    # 域名但未 http 存活的（infra 级别域名资产）也保留
    for sub, ip in resolved.items():
        key = (sub, ip, None)
        if not any(d.get("domain") == sub for d in assets_by_key.values()):
            assets_by_key[key] = {
                "domain": sub, "ip_address": ip, "port": None,
                "protocol": "https", "asset_type": "domain", "confidence": 0.5,
                "icp_verified": False, "tech_stack": [], "open_ports": [],
                "risk_level": "info", "confirmed": False, "notes": "source=dnsx",
                "source_platforms": ["dnsx"],
            }

    return list(assets_by_key.values()), errors
