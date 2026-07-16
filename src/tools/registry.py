"""Tool registry — register the first batch of external security tools.

Each tool = (binary) + (params with validated input types) + (fixed flags) +
(output parser). Registers into the ToolExecutor singleton.

Tools map to the user's 5-step pipeline:
  subfinder / dnsx / httpx      → step 2(2) 域名挖掘
  naabu / nmap                  → step 2(3) IP 端口扫描
  nuclei                        → step 5 漏洞扫描 (registered, disabled by default)
  cert (crt.sh)                 → step 2(1) 证书挖掘

NOTE: All tools default to JSON output (-json / -j) so parsers are deterministic.
Inputs pass through VALIDATORS (domain/ip/cidr/url) — hostile values are rejected
before subprocess. See security.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.executor import ToolExecutor, ToolResult
from src.tools.security import ToolDefinition, ToolParam

logger = logging.getLogger(__name__)


# ── Output parsers ───────────────────────────────────────
# ProjectDiscovery tools emit newline-delimited JSON when -json is set.

def _parse_ndjson(stdout: str, _result: ToolResult) -> list[dict]:
    """Parse newline-delimited JSON (subfinder/dnsx/httpx/naabu/nuclei -json)."""
    out: list[dict] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _parse_subfinder(stdout: str, _result: ToolResult) -> list[str]:
    """subfinder -json emits {"host": "..."} per line → list of subdomains."""
    return [obj.get("host", "") for obj in _parse_ndjson(stdout, _result) if obj.get("host")]


def _parse_dnsx(stdout: str, _result: ToolResult) -> list[dict]:
    """dnsx -json → [{host, a:[ips], resolver, ...}]."""
    return _parse_ndjson(stdout, _result)


def _parse_httpx(stdout: str, _result: ToolResult) -> list[dict]:
    """httpx -json → [{url, host, status_code, title, webserver, tech, ...}]."""
    return _parse_ndjson(stdout, _result)


def _parse_naabu(stdout: str, _result: ToolResult) -> list[dict]:
    """naabu -json → [{ip, port}]."""
    return _parse_ndjson(stdout, _result)


def _parse_nmap(stdout: str, _result: ToolResult) -> dict:
    """nmap -oX - emits XML; here we do a lightweight line-based fallback
    (full XML parsing would need a dep). Returns {raw: stdout} for now — agents
    that need structured nmap output can plug a real parser.
    """
    return {"raw": stdout[:5000]}


def _parse_nuclei(stdout: str, _result: ToolResult) -> list[dict]:
    """nuclei -jsonl → [{template-id, matched, info:{severity,name}, ...}]."""
    return _parse_ndjson(stdout, _result)


def _parse_crtsh(stdout: str, _result: ToolResult) -> list[str]:
    """crt.sh returns JSON array [{name_value: "domain\\nwww.domain"}, ...]."""
    try:
        data = json.loads(stdout)
        names: set[str] = set()
        for entry in data:
            for n in str(entry.get("name_value", "")).split("\n"):
                n = n.strip().lstrip("*.")
                if n:
                    names.add(n)
        return sorted(names)
    except json.JSONDecodeError:
        return []


# Map tool name → parser (used by router/agent when invoking).
PARSERS: dict[str, Any] = {
    "subfinder": _parse_subfinder,
    "dnsx": _parse_dnsx,
    "httpx": _parse_httpx,
    "naabu": _parse_naabu,
    "nmap": _parse_nmap,
    "nuclei": _parse_nuclei,
    "cert": _parse_crtsh,
}


def register_all(executor: ToolExecutor) -> None:
    """Register the first batch of tools into the executor."""

    # subfinder — 子域名枚举
    executor.register(ToolDefinition(
        name="subfinder", binary="subfinder", category="recon",
        description="ProjectDiscovery 子域名枚举 (被动源聚合)",
        params=[ToolParam(name="domain", input_type="domain", flag="-d", required=True, multiple=True)],
        fixed_flags=["-silent", "-json"],
        allowed_flags={"-all", "-recursive"},
        default_timeout=300,
    ))

    # dnsx — DNS 解析 / 反查
    executor.register(ToolDefinition(
        name="dnsx", binary="dnsx", category="dns",
        description="ProjectDiscovery DNS 解析与反查",
        params=[
            ToolParam(name="domain", input_type="domain", flag="-d", multiple=True),
            ToolParam(name="ip", input_type="ip", flag="-d", multiple=True),
        ],
        fixed_flags=["-silent", "-json", "-a", "-resp"],
        allowed_flags={"-reverse", "-cname"},
        default_timeout=180,
    ))

    # httpx — HTTP 存活探测 + 指纹
    executor.register(ToolDefinition(
        name="httpx", binary="httpx", category="recon",
        description="ProjectDiscovery HTTP 存活探测 / 指纹 / 标题",
        params=[
            ToolParam(name="url", input_type="url", flag="-u", multiple=True),
            ToolParam(name="domain", input_type="domain", flag="-u", multiple=True),
        ],
        fixed_flags=["-silent", "-json", "-title", "-tech-detect", "-status-code"],
        allowed_flags={"-follow-redirects", "-screenshot"},
        default_timeout=300,
    ))

    # naabu — 端口扫描 (SYN/CONNECT)
    executor.register(ToolDefinition(
        name="naabu", binary="naabu", category="portscan",
        description="ProjectDiscovery 端口扫描",
        params=[
            ToolParam(name="host", input_type="domain", flag="-host", multiple=True),
            ToolParam(name="ip", input_type="ip", flag="-host", multiple=True),
            ToolParam(name="cidr", input_type="cidr", flag="-cidr", multiple=True),
        ],
        fixed_flags=["-silent", "-json"],
        allowed_flags={"-top-ports", "-scan", "-rate"},
        default_timeout=600,
    ))

    # nmap — 深度端口/服务/版本识别
    executor.register(ToolDefinition(
        name="nmap", binary="nmap", category="portscan",
        description="Nmap 深度端口与服务版本识别",
        params=[
            ToolParam(name="host", input_type="domain", flag="", multiple=True),
            ToolParam(name="ip", input_type="ip", flag="", multiple=True),
            ToolParam(name="cidr", input_type="cidr", flag="", multiple=True),
        ],
        fixed_flags=["-sV", "-oX", "-"],
        allowed_flags={"-sS", "-O", "-A"},
        default_timeout=900,
    ))

    # nuclei — 漏洞扫描 (默认禁用, S5 启用)
    executor.register(ToolDefinition(
        name="nuclei", binary="nuclei", category="vulnscan",
        description="ProjectDiscovery 漏洞扫描 (PoC 模板)",
        params=[
            ToolParam(name="url", input_type="url", flag="-u", multiple=True),
            ToolParam(name="target", input_type="domain", flag="-u", multiple=True),
        ],
        fixed_flags=["-silent", "-jsonl"],
        allowed_flags={"-severity high,critical", "-etags"},
        default_timeout=1800,
        enabled=False,  # 第 5 步暂不做, 注册但不启用
    ))

    # cert — 证书透明度查询 (crt.sh HTTP API, 非二进制; 用 curl 代理)
    # NOTE: crt.sh 是 HTTP API, 这里用 curl 作为执行体; 输入仍是 domain 白名单.
    executor.register(ToolDefinition(
        name="cert", binary="curl", category="cert",
        description="证书透明度查询 (crt.sh) — 同证书关联域名",
        params=[ToolParam(name="domain", input_type="domain", flag="", required=True)],
        fixed_flags=["-s", "--max-time", "30"],
        # crt.sh URL 由 router 层拼装 (domain 已白名单校验), 这里 flag 留空
        default_timeout=60,
    ))
