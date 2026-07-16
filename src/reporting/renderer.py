"""Report renderer (S2 M6).

Renders aggregated task data into a Markdown report. Two modes:
  - template (default): deterministic Jinja2 section rendering from S4 report
    template field selection. No LLM call — fast, cheap, always works.
  - llm: uses LLMClient to generate narrative sections (摘要/风险分析/修复建议).
    Falls back to template mode on LLM failure.

Consumes S4 report templates (Template.template_type == "report"):
  content = { report_type, fields:[...], format, cover, toc, layout }
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Jinja2 available? (it's a dependency of FastAPI ecosystem)
try:
    from jinja2 import Template
    _HAS_JINJA = True
except ImportError:
    _HAS_JINJA = False

# ── Section renderers (deterministic, no LLM) ─────────────

def _r_cover(ctx: dict, company_name: str) -> str:
    s = ctx["summaries"]
    return f"""# 攻击面评估报告

**目标企业**: {company_name}
**资产总数**: {s['asset_total']} (已确认 {s['asset_confirmed']})
**漏洞总数**: {s['vuln_total']} (已确认 {s['vuln_confirmed']})
**风险评分**: {s['risk_score']} / 100

---
"""


def _r_summary(ctx: dict) -> str:
    s = ctx["summaries"]
    sev = s["vuln_by_severity"]
    company = ctx.get("company") or {}
    name = company.get("name") or ctx["task"]["company_name"]
    industry = company.get("industry") or "—"
    lines = [
        "## 一、执行摘要\n",
        f"本次评估针对 **{name}**（行业：{industry}）进行攻击面探测，",
        f"共发现资产 **{s['asset_total']}** 个、漏洞 **{s['vuln_total']}** 个、API 接口 **{s['interface_total']}** 个。\n",
        f"### 风险概览\n",
        f"- 严重 (Critical): **{sev.get('critical', 0)}**\n",
        f"- 高危 (High): **{sev.get('high', 0)}**\n",
        f"- 中危 (Medium): **{sev.get('medium', 0)}**\n",
        f"- 低危 (Low): **{sev.get('low', 0)}**\n",
        f"- 综合风险评分: **{s['risk_score']}/100**\n",
        "\n---\n",
    ]
    return "\n".join(lines)


def _r_assets(ctx: dict, fields: list[str]) -> str:
    assets = ctx.get("assets", [])
    if not assets:
        return "## 二、资产清单\n\n未发现资产。\n\n---\n"
    # table header from selected fields
    field_label = {
        "ip": "IP", "domain": "域名", "port": "端口", "tech_stack": "技术栈",
        "risk_level": "风险等级", "icp_entity": "ICP主体", "open_ports": "开放端口",
        "asset_type": "类型",
    }
    cols = [f for f in fields if f in field_label] or ["asset_type", "domain", "ip", "risk_level"]
    header = "| " + " | ".join(field_label.get(c, c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for a in assets:
        cells = []
        for c in cols:
            v = a.get(c)
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v[:5])
            cells.append(str(v) if v is not None else "—")
        rows.append("| " + " | ".join(cells) + " |")
    return f"## 二、资产清单\n\n共 {len(assets)} 个资产。\n\n{header}\n{sep}\n" + "\n".join(rows) + "\n\n---\n"


def _r_vulnerabilities(ctx: dict) -> str:
    vulns = ctx.get("vulnerabilities", [])
    if not vulns:
        return "## 三、漏洞详情\n\n未发现漏洞。\n\n---\n"
    sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
    lines = [f"## 三、漏洞详情\n\n共 {len(vulns)} 个漏洞。\n"]
    for i, v in enumerate(vulns, 1):
        sev = v.get("severity", "info")
        emoji = sev_emoji.get(sev, "⚪")
        cvss = f" (CVSS {v['cvss_score']})" if v.get("cvss_score") else ""
        lines.append(f"### {i}. {emoji} {v['title']} [{sev}{cvss}]\n")
        if v.get("vuln_type"):
            lines.append(f"- **类型**: {v['vuln_type']}\n")
        if v.get("target"):
            lines.append(f"- **目标**: {v['target']}\n")
        lines.append(f"- **已确认**: {'是' if v.get('human_confirmed') else '否'}\n")
        evidence = v.get("evidence")
        if evidence:
            ev_str = evidence if isinstance(evidence, str) else str(evidence)
            lines.append(f"- **证据**:\n```\n{ev_str[:500]}\n```\n")
        if v.get("remediation"):
            lines.append(f"- **修复建议**: {v['remediation']}\n")
        lines.append("")
    lines.append("---\n")
    return "\n".join(lines)


def _r_risk_analysis(ctx: dict) -> str:
    s = ctx["summaries"]
    risk = s["risk_score"]
    level = "高危" if risk >= 70 else "中危" if risk >= 40 else "低危"
    return f"""## 四、风险分析

综合风险评分 **{risk}/100**，整体风险等级：**{level}**。

- 资产风险分布: {s.get('asset_by_risk', {})}
- 漏洞严重度分布: {s.get('vuln_by_severity', {})}

---

"""


def _r_remediation(ctx: dict) -> str:
    vulns = ctx.get("vulnerabilities", [])
    if not vulns:
        return "## 五、修复建议\n\n无漏洞需修复。\n\n---\n"
    lines = ["## 五、修复建议\n", "按优先级建议如下：\n"]
    priority = {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5}
    sorted_v = sorted(vulns, key=lambda v: priority.get(v.get("severity", "info"), 9))
    for i, v in enumerate(sorted_v, 1):
        rem = v.get("remediation") or "请联系厂商获取补丁或临时缓解措施"
        lines.append(f"{i}. **[{v.get('severity', '?').upper()}] {v['title']}**: {rem}\n")
    lines.append("\n---\n")
    return "\n".join(lines)


# ── Public render API ─────────────────────────────────────

def render_report(
    ctx: dict,
    *,
    report_template: dict | None = None,
    use_llm: bool = False,
    llm_client: Any = None,
) -> str:
    """Render the report context into a Markdown string.

    Args:
        ctx: aggregated task data (from aggregator.aggregate_task_data).
        report_template: S4 report template content
            {report_type, fields, format, cover, toc, layout}. None = default.
        use_llm: if True and llm_client provided, generate narrative via LLM.
        llm_client: LLMClient instance (optional).
    """
    tmpl = report_template or {}
    fields = tmpl.get("fields", ["ip", "domain", "risk_level"])
    company_name = (ctx.get("company") or {}).get("name") or ctx["task"]["company_name"]

    sections: list[str] = []

    if tmpl.get("cover", True):
        sections.append(_r_cover(ctx, company_name))
    sections.append(_r_summary(ctx))
    sections.append(_r_assets(ctx, fields))
    sections.append(_r_vulnerabilities(ctx))
    sections.append(_r_risk_analysis(ctx))
    sections.append(_r_remediation(ctx))

    # Optional LLM-generated executive summary (appended, replaces nothing)
    if use_llm and llm_client is not None:
        try:
            llm_summary = _llm_executive_summary(ctx, llm_client, company_name)
            if llm_summary:
                # insert after cover
                sections.insert(1, f"## LLM 摘要\n\n{llm_summary}\n\n---\n")
        except Exception as exc:
            logger.warning("LLM summary generation failed, skipping: %s", exc)

    return "\n".join(sections)


def _llm_executive_summary(ctx: dict, llm_client: Any, company_name: str) -> str:
    """Use LLM to generate a narrative executive summary. Returns empty on failure."""
    s = ctx["summaries"]
    prompt = (
        f"你是网络安全报告撰写专家。请根据以下评估数据为{company_name}撰写一段简洁的中文执行摘要(150字以内)：\n"
        f"资产数: {s['asset_total']}, 漏洞数: {s['vuln_total']}, "
        f"严重漏洞: {s['vuln_by_severity'].get('critical',0)}, "
        f"风险评分: {s['risk_score']}/100\n"
        f"直接输出摘要正文,不要标题。"
    )
    import asyncio
    return asyncio.get_event_loop().run_until_complete(llm_client.generate(prompt, temperature=0.5, max_tokens=300))
