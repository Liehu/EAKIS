"""Permission checking dependencies for RBAC."""

from __future__ import annotations

from enum import Enum

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo, get_current_user
from src.api.dependencies import get_async_db


class PermissionAction(str, Enum):  # noqa: UP042
    # 任务管理
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    TASK_BATCH = "task:batch"

    # 任务编排（演练计划）
    ORCH_CREATE = "orch:create"
    ORCH_READ = "orch:read"
    ORCH_UPDATE = "orch:update"
    ORCH_DELETE = "orch:delete"
    ORCH_EXECUTE = "orch:execute"
    ORCH_REPORT = "orch:report"

    # 情报采集
    INTEL_START = "intel:start"
    INTEL_READ = "intel:read"
    INTEL_RAG_SEARCH = "intel:rag_search"

    # 关键词
    KEYWORD_READ = "keyword:read"
    KEYWORD_CREATE = "keyword:create"
    KEYWORD_DELETE = "keyword:delete"

    # 资产管理
    ASSET_READ = "asset:read"
    ASSET_UPDATE = "asset:update"
    ASSET_EXPORT = "asset:export"

    # 接口管理
    INTERFACE_READ = "interface:read"
    INTERFACE_UPDATE = "interface:update"
    INTERFACE_RAW = "interface:raw"

    # 漏洞管理
    VULN_READ = "vuln:read"
    VULN_UPDATE = "vuln:update"
    VULN_RAW = "vuln:raw"

    # 渗透测试
    PENTEST_TRIGGER = "pentest:trigger"
    PENTEST_READ = "pentest:read"

    # 报告管理
    REPORT_GENERATE = "report:generate"
    REPORT_READ = "report:read"
    REPORT_DOWNLOAD = "report:download"

    # 知识库管理
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_ADMIN = "knowledge:admin"

    # 工具管理
    TOOL_READ = "tool:read"
    TOOL_EXECUTE = "tool:execute"

    # 模板管理
    TEMPLATE_READ = "template:read"
    TEMPLATE_WRITE = "template:write"

    # 企业管理
    COMPANY_READ = "company:read"
    COMPANY_CREATE = "company:create"
    COMPANY_UPDATE = "company:update"
    COMPANY_DELETE = "company:delete"

    # 团队管理
    TEAM_MANAGE = "team:manage"

    # 系统管理
    SYSTEM_HEALTH = "system:health"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_ADMIN = "system:admin"


def require_permission(action: PermissionAction):
    """FastAPI dependency: check if current user has the required permission."""

    async def checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role == "super_admin":
            return user
        if action.value not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action.value} required",
            )
        return user

    return checker


def require_role(*roles: str):
    """FastAPI dependency factory: check if current user has one of the required roles."""

    async def checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role == "super_admin":
            return user
        if user.role in roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role denied: requires one of {', '.join(roles)}",
        )

    return checker


async def require_resource_access(
    action: PermissionAction,
    resource_type: str,
    resource_id: str | None = None,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserInfo:
    """
    Resource-level permission check:
    1. Check operation permission
    2. Check resource ownership (org/team isolation)
    """
    # Step 1: Check operation permission
    if user.role != "super_admin" and action.value not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {action.value} required",
        )

    # super_admin bypasses all resource checks
    if user.role == "super_admin":
        return user

    # No resource_id means list/aggregate operation - org_admin can see all in org
    if resource_id is None:
        return user

    # Determine the table to query based on resource_type
    table_map = {
        "task": "tasks",
        "orchestration": "orchestrations",
        "vulnerability": "vulnerabilities",
        "asset": "assets",
    }
    table_name = table_map.get(resource_type)
    if not table_name:
        return user

    # org_admin can access all resources in their org
    if user.role == "org_admin":
        from sqlalchemy import text
        result = await db.execute(
            text(f"SELECT org_id FROM {table_name} WHERE id = :rid"),
            {"rid": resource_id},
        )
        row = result.fetchone()
        if row and str(row[0]) != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource not in your organization",
            )
        return user

    # Team-level roles: check resource belongs to user's team
    if user.teams:
        team_ids = set(user.teams.keys())
        from sqlalchemy import text
        result = await db.execute(
            text(f"SELECT team_id FROM {table_name} WHERE id = :rid"),
            {"rid": resource_id},
        )
        row = result.fetchone()
        if row and str(row[0]) not in team_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource not in your team",
            )

    return user
