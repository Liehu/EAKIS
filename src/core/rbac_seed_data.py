"""RBAC seed data: roles, permissions, and role-permission mappings.

This module is used by both the seed script and test fixtures.
"""

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------
ROLES = [
    {"name": "super_admin", "display_name": "超级管理员",  # noqa: E501
     "description": "管理所有组织、全局配置、系统运维", "level": 100},
    {"name": "org_admin", "display_name": "组织管理员",  # noqa: E501
     "description": "管理本组织内用户、团队、计费、配置", "level": 50},
    {"name": "team_lead", "display_name": "团队负责人",  # noqa: E501
     "description": "创建/删除任务、管理团队成员、审批HIL", "level": 30},
    {"name": "engineer", "display_name": "执行工程师",  # noqa: E501
     "description": "创建任务、执行扫描/测试、查看全部数据", "level": 20},
    {"name": "analyst", "display_name": "分析师",  # noqa: E501
     "description": "只读查看任务/资产/漏洞数据，不可触发测试", "level": 10},
    {"name": "auditor", "display_name": "审计员",  # noqa: E501
     "description": "只读查看审计日志和报告，不可查看原始请求/响应", "level": 5},
]

# ---------------------------------------------------------------------------
# Permission definitions (action, display_name, category, description)
# ---------------------------------------------------------------------------
PERMISSIONS = [
    # 任务管理
    ("task:create", "创建任务", "task", "创建新的扫描任务"),
    ("task:read", "查看任务", "task", "查看/列出任务"),
    ("task:update", "修改任务", "task", "修改任务配置"),
    ("task:delete", "删除任务", "task", "删除任务及关联数据"),
    ("task:execute", "执行任务", "task", "启动/暂停/恢复/取消任务"),
    ("task:batch", "批量操作", "task", "批量取消/恢复任务"),

    # 任务编排
    ("orch:create", "创建演练", "orch", "创建演练计划"),
    ("orch:read", "查看演练", "orch", "查看/列出演练计划"),
    ("orch:update", "修改演练", "orch", "修改演练计划"),
    ("orch:delete", "删除演练", "orch", "删除演练计划"),
    ("orch:execute", "执行演练", "orch", "启动/暂停/恢复/取消演练"),
    ("orch:report", "演练报告", "orch", "生成演练汇总报告"),

    # 情报采集
    ("intel:start", "启动采集", "intel", "启动情报采集"),
    ("intel:read", "查看情报", "intel", "查看情报数据"),
    ("intel:rag_search", "RAG搜索", "intel", "RAG语义搜索"),

    # 关键词
    ("keyword:read", "查看关键词", "keyword", "查看关键词"),
    ("keyword:create", "添加关键词", "keyword", "添加关键词"),
    ("keyword:delete", "删除关键词", "keyword", "删除关键词"),

    # 资产管理
    ("asset:read", "查看资产", "asset", "查看资产"),
    ("asset:update", "更新资产", "asset", "更新资产状态"),
    ("asset:export", "导出资产", "asset", "导出资产"),

    # 接口管理
    ("interface:read", "查看接口", "interface", "查看接口"),
    ("interface:update", "更新接口", "interface", "更新接口信息"),
    ("interface:raw", "原始请求响应", "interface", "查看原始请求/响应"),

    # 漏洞管理
    ("vuln:read", "查看漏洞", "vuln", "查看漏洞"),
    ("vuln:update", "更新漏洞", "vuln", "更新漏洞状态"),
    ("vuln:raw", "原始测试数据", "vuln", "查看原始测试payload和响应"),

    # 渗透测试
    ("pentest:trigger", "触发渗透", "pentest", "触发渗透测试"),
    ("pentest:read", "查看渗透结果", "pentest", "查看渗透测试结果"),

    # 报告
    ("report:generate", "生成报告", "report", "生成报告"),
    ("report:read", "查看报告", "report", "查看报告"),
    ("report:download", "下载报告", "report", "下载报告"),

    # 知识库
    ("knowledge:read", "查看知识库", "knowledge", "查看知识库"),
    ("knowledge:write", "编辑知识库", "knowledge", "编辑知识库内容"),
    ("knowledge:admin", "管理知识库", "knowledge", "知识库管理"),

    # 工具
    ("tool:read", "查看工具", "tool", "查看工具"),
    ("tool:execute", "执行工具", "tool", "执行工具"),

    # 模板
    ("template:read", "查看模板", "template", "查看模板"),
    ("template:write", "编辑模板", "template", "编辑模板"),

    # 企业管理
    ("company:read", "查看企业", "company", "查看企业"),
    ("company:create", "创建企业", "company", "创建企业"),
    ("company:update", "更新企业", "company", "更新企业"),
    ("company:delete", "删除企业", "company", "删除企业"),

    # 团队
    ("team:manage", "管理团队", "team", "管理团队成员"),

    # 系统
    ("system:health", "系统状态", "system", "查看系统状态"),
    ("system:config", "系统配置", "system", "修改系统配置"),
    ("system:audit", "审计日志", "system", "查看审计日志"),
    ("system:admin", "系统管理", "system", "用户/组织管理"),
]

# ---------------------------------------------------------------------------
# Role-permission mapping (role_name -> list of permission actions)
# Based on the matrix in docs/RBAC权限管理设计文档.md section 3.2
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": [
        # super_admin has ALL permissions
        p[0] for p in PERMISSIONS
    ],
    "org_admin": [
        "task:create", "task:read", "task:update", "task:delete", "task:execute", "task:batch",
        "orch:create", "orch:read", "orch:update", "orch:delete", "orch:execute", "orch:report",
        "intel:start", "intel:read", "intel:rag_search",
        "keyword:read", "keyword:create", "keyword:delete",
        "asset:read", "asset:update", "asset:export",
        "interface:read", "interface:update", "interface:raw",
        "vuln:read", "vuln:update", "vuln:raw",
        "pentest:trigger", "pentest:read",
        "report:generate", "report:read", "report:download",
        "knowledge:read", "knowledge:write", "knowledge:admin",
        "tool:read", "tool:execute",
        "template:read", "template:write",
        "company:read", "company:create", "company:update", "company:delete",
        "team:manage",
        "system:health", "system:config", "system:audit",
    ],
    "team_lead": [
        "task:create", "task:read", "task:update", "task:delete", "task:execute", "task:batch",
        "orch:create", "orch:read", "orch:update", "orch:delete", "orch:execute", "orch:report",
        "intel:start", "intel:read", "intel:rag_search",
        "keyword:read", "keyword:create", "keyword:delete",
        "asset:read", "asset:update", "asset:export",
        "interface:read", "interface:update", "interface:raw",
        "vuln:read", "vuln:update", "vuln:raw",
        "pentest:trigger", "pentest:read",
        "report:generate", "report:read", "report:download",
        "knowledge:read", "knowledge:write",
        "tool:read", "tool:execute",
        "template:read", "template:write",
        "company:read", "company:create", "company:update", "company:delete",
        "team:manage",
        "system:health", "system:audit",
    ],
    "engineer": [
        "task:create", "task:read", "task:update", "task:execute", "task:batch",
        "orch:read", "orch:execute", "orch:report",
        "intel:start", "intel:read", "intel:rag_search",
        "keyword:read", "keyword:create", "keyword:delete",
        "asset:read", "asset:update", "asset:export",
        "interface:read", "interface:update", "interface:raw",
        "vuln:read", "vuln:update", "vuln:raw",
        "pentest:trigger", "pentest:read",
        "report:generate", "report:read", "report:download",
        "knowledge:read", "knowledge:write",
        "tool:read", "tool:execute",
        "template:read", "template:write",
        "company:read", "company:create", "company:update",
        "system:health",
    ],
    "analyst": [
        "task:read",
        "orch:read", "orch:report",
        "intel:read", "intel:rag_search",
        "keyword:read",
        "asset:read", "asset:export",
        "interface:read",
        "vuln:read",
        "pentest:read",
        "report:read", "report:download",
        "knowledge:read",
        "tool:read",
        "template:read",
        "company:read",
        "system:health",
    ],
    "auditor": [
        "interface:read",
        "vuln:read",
        "pentest:read",
        "report:generate", "report:read", "report:download",
        "knowledge:read",
        "tool:read",
        "template:read",
        "system:health", "system:audit",
    ],
}
