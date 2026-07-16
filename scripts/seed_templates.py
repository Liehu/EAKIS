"""S4 seed: template management sample data.

Inserts sample templates for all 4 types (task/report/prompt/attack_path),
including importing Prompt seeds from config/prompts/*.yaml. Idempotent.

Usage:
    python3 scripts/seed_templates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from src.models.database import SessionLocal
from src.models.template import Template
from src.models.organization import Organization
from src.core.settings import get_settings

settings = get_settings()
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "config" / "prompts"


def _default_org(session) -> Organization:
    org = session.scalar(select(Organization).where(Organization.slug == settings.default_org_slug))
    return org


def run() -> None:
    session = SessionLocal()
    try:
        org = _default_org(session)
        if org is None:
            print("[seed] no default org — run seed_companies.py first")
            return

        # ── 任务模板 (参数预设) ──
        if session.scalar(select(Template).where(Template.template_type == "task", Template.name == "金融行业深度扫描")) is None:
            session.add(Template(
                org_id=org.id, name="金融行业深度扫描", template_type="task",
                description="金融行业企业深度扫描 (3级穿透 + 全模块)",
                content={
                    "target_depth": 3, "holding_ratio_min": 51, "include_minority": False,
                    "modules": ["M1", "M2", "M3", "M4"], "concurrency": 5,
                    "smart_c_segment": True, "smart_asset_link": True,
                },
                scope="org",
            ))
            print("[seed] task template: 金融行业深度扫描")

        if session.scalar(select(Template).where(Template.template_type == "task", Template.name == "快速资产探测")) is None:
            session.add(Template(
                org_id=org.id, name="快速资产探测", template_type="task",
                description="仅资产探测 (无漏洞扫描)",
                content={
                    "target_depth": 1, "modules": ["M3"], "concurrency": 10,
                    "smart_c_segment": False, "smart_asset_link": True,
                },
                scope="org",
            ))
            print("[seed] task template: 快速资产探测")

        # ── 报告模板 (字段勾选 + 布局) ──
        if session.scalar(select(Template).where(Template.template_type == "report", Template.name == "资产报告-标准版")) is None:
            session.add(Template(
                org_id=org.id, name="资产报告-标准版", template_type="report",
                description="资产清单报告标准模板",
                content={
                    "report_type": "asset",
                    "fields": ["ip", "domain", "port", "tech_stack", "risk_level", "icp_entity", "open_ports"],
                    "layout": "standard", "format": "md",
                    "cover": True, "toc": True,
                },
                scope="org",
            ))
            print("[seed] report template: 资产报告-标准版")

        if session.scalar(select(Template).where(Template.template_type == "report", Template.name == "企业风险报告-详细版")) is None:
            session.add(Template(
                org_id=org.id, name="企业风险报告-详细版", template_type="report",
                description="企业风险评估详细报告 (含风险趋势)",
                content={
                    "report_type": "company",
                    "fields": ["company_name", "asset_summary", "vuln_summary", "risk_score", "risk_trend", "recommendations"],
                    "layout": "detailed", "format": "html",
                },
                scope="org",
            ))
            print("[seed] report template: 企业风险报告-详细版")

        # ── Prompt 模板 (从 config/prompts/*.yaml 导入种子) ──
        if PROMPTS_DIR.exists():
            for yaml_file in sorted(PROMPTS_DIR.glob("*.yaml")):
                name_key = yaml_file.stem  # e.g. keyword_extraction_v2
                existing = session.scalar(
                    select(Template).where(Template.template_type == "prompt", Template.is_seed == 1, Template.name == name_key)
                )
                if existing is not None:
                    continue
                content_text = yaml_file.read_text(encoding="utf-8")
                # 简单提取变量 ({{ var }} 占位)
                import re
                variables = sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", content_text)))
                session.add(Template(
                    org_id=org.id, name=name_key, template_type="prompt",
                    description=f"Prompt 种子 (从 {yaml_file.name} 导入)",
                    content={
                        "agent": name_key.split("_")[0],  # keyword/vuln/asset/browser
                        "template": content_text,
                        "variables": variables,
                        "source_file": str(yaml_file.relative_to(Path(__file__).resolve().parent.parent)),
                    },
                    scope="org", is_seed=1,
                ))
                print(f"[seed] prompt template: {name_key} (vars={variables})")
        else:
            print("[seed] config/prompts not found — skip prompt seeds")

        # ── 攻击路径模板 (DAG JSON) ──
        if session.scalar(select(Template).where(Template.template_type == "attack_path", Template.name == "Web应用通用攻击路径")) is None:
            session.add(Template(
                org_id=org.id, name="Web应用通用攻击路径", template_type="attack_path",
                description="信息收集 → 漏洞发现 → 利用 → 横向移动",
                content={
                    "nodes": [
                        {"id": "n1", "type": "recon", "label": "信息收集"},
                        {"id": "n2", "type": "vuln_scan", "label": "漏洞扫描"},
                        {"id": "n3", "type": "exploit", "label": "漏洞利用"},
                        {"id": "n4", "type": "lateral", "label": "横向移动"},
                        {"id": "n5", "type": "data_exfil", "label": "数据获取"},
                    ],
                    "edges": [
                        {"source": "n1", "target": "n2", "action": "auto"},
                        {"source": "n2", "target": "n3", "action": "manual"},
                        {"source": "n3", "target": "n4", "action": "conditional"},
                        {"source": "n4", "target": "n5", "action": "auto"},
                    ],
                },
                scope="org",
            ))
            print("[seed] attack_path template: Web应用通用攻击路径")

        # ── 继承示例: 子模板继承父模板 ──
        parent = session.scalar(select(Template).where(Template.name == "资产报告-标准版"))
        if parent and session.scalar(select(Template).where(Template.name == "资产报告-精简版")) is None:
            session.add(Template(
                org_id=org.id, name="资产报告-精简版", template_type="report",
                description="继承标准版, 仅保留核心字段",
                content={"fields": ["ip", "domain", "risk_level"], "format": "md"},  # override fields
                parent_template_id=parent.id, scope="org",
            ))
            print("[seed] report template: 资产报告-精简版 (继承标准版)")

        session.commit()
        from sqlalchemy import func as _f
        total = session.scalar(select(_f.count(Template.id)))
        print(f"[seed] templates done. total templates: {total}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
