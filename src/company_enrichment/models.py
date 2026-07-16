"""Normalized data contracts for company enrichment (企业主体信息采集).

所有商业 API Provider（云图/天眼查/企查查/爱企查…）统一返回这里的归一化结构，
字段对齐 `src/models/company.py` 的 Company 模型 + 前端企业字段。

不同 Provider 采集到的相同字段若有差异，由 `merge.py` 生成冲突列表交由用户对比确认，
不自动覆盖（见 A.1 企业关系穿透决策）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NormalizedCompany:
    """归一化的企业主体信息（对齐 Company 模型字段）。

    Provider 不提供的字段留 None，由 merge 策略决定是否填充。
    """

    name: str
    # ── 工商字段 (只读) ──
    credit_code: str | None = None  # 统一社会信用代码
    legal_person: str | None = None  # 法定代表人
    industry: str | None = None  # 所属行业
    registered_capital: str | None = None  # 注册资本
    established_at: datetime | None = None  # 成立时间
    business_status: str | None = None  # 存续状态（存续/注销/吊销…）
    website: str | None = None  # 官网
    # ── 业务字段 ──
    email_domains: list[str] | None = None  # 邮箱域名（生成邮箱字典）
    work_id_rule: str | None = None  # 员工工号规则（生成账号字典）
    aliases: list[str] | None = None  # 简称/曾用名
    # ── 元信息 ──
    provider: str = ""  # 来源标记 (yuntu/tianyancha/...)
    raw: dict[str, Any] = field(default_factory=dict)  # 原始响应（审计/调试）


@dataclass
class NormalizedRelation:
    """归一化的母子公司关系。"""

    parent_name: str  # 母公司名称（用于回查匹配）
    child: NormalizedCompany  # 子公司
    relation_type: str = "holding"  # holding(控股) / minority_stake(参股) / branch(分支机构)
    holding_ratio: float | None = None  # 持股比例 0-100
    provider: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichmentResult:
    """单个企业一次采集的结果。"""

    root: NormalizedCompany  # 主体本身（可能补全了工商字段）
    relations: list[NormalizedRelation]  # 分子公司列表
    provider: str
    fetched_at: datetime
    # 采集时云图等服务的临时 id（如云图 seed id），落库后用于清理
    external_root_id: str | None = None
