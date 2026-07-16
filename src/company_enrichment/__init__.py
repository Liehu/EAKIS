"""企业主体关联信息采集模块（company_enrichment）。

对接外部商业 API（云图/天眼查/企查查/爱企查…）采集企业工商信息 + 控股子单位，
归一化后落库 Company / CompanyRelation。多 Provider 同字段差异由冲突对比处理。

架构：
- models.py:    归一化数据契约 (NormalizedCompany / NormalizedRelation / EnrichmentResult)
- base.py:      Provider 抽象基类
- providers/:   各 Provider 实现（首个：云图 yuntu）
- registry.py:  Provider 注册表（get_provider / list_providers）
- merge.py:     归一化 → Company 合并 + 冲突检测
"""

from src.company_enrichment.base import CompanyEnrichmentProvider
from src.company_enrichment.merge import FieldConflict, MergePlan, plan_company_merge, apply_merge
from src.company_enrichment.models import EnrichmentResult, NormalizedCompany, NormalizedRelation
from src.company_enrichment.registry import get_provider, list_providers

__all__ = [
    "CompanyEnrichmentProvider",
    "EnrichmentResult",
    "NormalizedCompany",
    "NormalizedRelation",
    "FieldConflict",
    "MergePlan",
    "plan_company_merge",
    "apply_merge",
    "get_provider",
    "list_providers",
]
