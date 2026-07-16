"""归一化结果 → Company/CompanyRelation 的合并与冲突检测。

合并策略（strategy）:
- ``auto_fill``（默认）：只填充数据库中为空的字段，已有值不覆盖。
- ``overwrite``：用采集到的新数据覆盖数据库现有值（关系仍按唯一约束去重插入）。

无论哪种策略，当 incoming 字段非空且与数据库现有值不同时，都记入 conflicts 列表，
供前端提示用户对比确认（符合用户要求：不同 API 同字段不同值时提示确认）。
auto_fill 下冲突字段不落库；overwrite 下冲突字段已落库但仍记录冲突供审计。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.company_enrichment.models import EnrichmentResult, NormalizedCompany
from src.models.company import Company

# 参与对比/合并的 Company 标量字段（工商 + 业务），排除 id/org_id/时间戳/数组特殊处理。
_SCALAR_FIELDS: tuple[str, ...] = (
    "credit_code",
    "legal_person",
    "industry",
    "registered_capital",
    "established_at",
    "business_status",
    "website",
    "work_id_rule",
)
# 数组字段：合并时取并集去重。
_ARRAY_FIELDS: tuple[str, ...] = (
    "email_domains",
    "aliases",
)


@dataclass
class FieldConflict:
    """一个字段的旧值（DB）与新值（采集）对比。"""

    field: str
    old_value: Any
    new_value: Any
    old_source: str | None = None  # 该字段上次的数据来源 (data_source)
    new_source: str | None = None  # 本次采集的 provider


@dataclass
class MergePlan:
    """合并计划：记录将应用到 Company 的变更 + 检测到的冲突。"""

    applied_fields: dict[str, Any] = field(default_factory=dict)  # field -> 即将/已写入的值
    conflicts: list[FieldConflict] = field(default_factory=list)


def _values_equal(a: Any, b: Any) -> bool:
    """宽松相等：None/空串/空列表 视为相等；时间戳比对 isoformat。"""
    if a in (None, "", []) and b in (None, "", []):
        return True
    if hasattr(a, "isoformat") and hasattr(b, "isoformat"):
        return a.isoformat() == b.isoformat()
    return a == b


def plan_company_merge(
    existing: Company,
    incoming: NormalizedCompany,
    *,
    strategy: str = "auto_fill",
) -> MergePlan:
    """生成 existing Company 与 incoming 归一化数据的合并计划。

    返回 applied_fields（应写入的字段值）和 conflicts（非空且不同的字段）。
    调用方据此落库。
    """
    plan = MergePlan()
    overwrite = strategy == "overwrite"

    for fname in _SCALAR_FIELDS:
        new_val = getattr(incoming, fname, None)
        if new_val in (None, "", []):
            continue
        old_val = getattr(existing, fname, None)
        if _values_equal(old_val, new_val):
            continue  # 一致，无需变更
        # 存在差异 → 记录冲突
        plan.conflicts.append(
            FieldConflict(
                field=fname,
                old_value=old_val,
                new_value=new_val,
                old_source=existing.data_source,
                new_source=incoming.provider,
            )
        )
        # auto_fill：仅当旧值为空时才填入；overwrite：总是采用新值
        if overwrite or old_val in (None, "", []):
            plan.applied_fields[fname] = new_val

    # 数组字段：取并集去重（不视为冲突，仅扩展）
    for fname in _ARRAY_FIELDS:
        new_list = getattr(incoming, fname, None) or []
        if not new_list:
            continue
        old_list = list(getattr(existing, fname, None) or [])
        merged = old_list + [x for x in new_list if x not in old_list]
        if len(merged) != len(old_list):
            plan.applied_fields[fname] = merged

    return plan


def apply_merge(existing: Company, applied_fields: dict[str, Any], provider: str) -> None:
    """将 applied_fields 写入 Company ORM 对象（原地修改，不 commit）。"""
    from datetime import UTC, datetime

    for fname, value in applied_fields.items():
        setattr(existing, fname, value)
    existing.data_source = provider
    existing.last_collected_at = datetime.now(UTC)


def summarize_result(result: EnrichmentResult) -> dict[str, Any]:
    """生成给前端的采集摘要（不含原始 raw）。"""
    return {
        "provider": result.provider,
        "fetched_at": result.fetched_at.isoformat() if result.fetched_at else None,
        "root_name": result.root.name,
        "relation_count": len(result.relations),
    }
