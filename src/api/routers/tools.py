"""Tools API router (S5 工具管理).

Endpoints:
  GET    /v1/tools                              — list registered tools (registry)
  GET    /v1/tools/{tool_name}                  — tool metadata
  POST   /v1/tools/{tool_name}/run              — execute a tool (anti-RCE validated)
  GET    /v1/tools/{tool_name}/status           — recent execution status
  GET    /v1/tool-executions                    — execution history
  GET    /v1/tool-executions/{execution_id}     — execution detail

Security: all execution goes through ToolExecutor → ToolDefinition.build_argv()
(validated argv list, never shell=True). Hostile inputs are rejected before
subprocess. See src/tools/security.py.
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.tool import (
    Pagination, RunToolRequest, ToolExecutionListResponse,
    ToolExecutionResponse, ToolInfo, ToolParamInfo,
)
from src.models.tool_execution import ToolExecution
from src.tools.executor import get_executor
from src.tools.registry import PARSERS

router = APIRouter(tags=["tools"])


def _def_to_info(d) -> ToolInfo:
    return ToolInfo(
        name=d.name, binary=d.binary, description=d.description, category=d.category,
        params=[ToolParamInfo(name=p.name, input_type=p.input_type, flag=p.flag,
                               required=p.required, multiple=p.multiple) for p in d.params],
        allowed_flags=sorted(d.allowed_flags),
        default_timeout=d.default_timeout, enabled=d.enabled,
    )


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """List all registered tools (metadata only, no execution)."""
    return [_def_to_info(t) for t in get_executor().list_tools()]


@router.get("/tools/{tool_name}", response_model=ToolInfo)
async def get_tool(tool_name: str) -> ToolInfo:
    t = get_executor().get(tool_name)
    if t is None:
        raise HTTPException(status_code=404, detail="工具不存在")
    return _def_to_info(t)


@router.post("/tools/{tool_name}/run", response_model=ToolExecutionResponse, status_code=status.HTTP_201_CREATED)
async def run_tool(
    tool_name: str,
    body: RunToolRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ToolExecutionResponse:
    """Execute a registered tool. Inputs are validated against the tool's schema
    (domain/ip/url whitelists) before subprocess — hostile values are rejected."""
    executor = get_executor()
    tool = executor.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail="工具不存在")
    if not tool.enabled:
        raise HTTPException(status_code=400, detail="工具未启用")

    # Execute (anti-RCE: validated argv list, shell=False).
    flags = set(body.flags) if body.flags else None
    parser = PARSERS.get(tool_name)
    result = executor.run(tool_name, body.inputs, flags=flags, timeout=body.timeout, parser=parser)

    # Persist execution record.
    execution = ToolExecution(
        tool_name=tool_name, category=tool.category, task_id=body.task_id,
        inputs=body.inputs, flags=list(flags) if flags else None,
        status=result.status, exit_code=result.exit_code,
        stdout=result.stdout, stderr=result.stderr, parsed=result.parsed,
        duration_s=result.duration_s, error=result.error,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return ToolExecutionResponse.model_validate(execution)


@router.get("/tools/{tool_name}/status")
async def tool_status(tool_name: str, db: AsyncSession = Depends(get_async_db)) -> dict:
    """Most recent execution status for a tool."""
    row = (await db.execute(
        select(ToolExecution).where(ToolExecution.tool_name == tool_name).order_by(ToolExecution.created_at.desc()).limit(1)
    )).scalars().first()
    if row is None:
        return {"tool_name": tool_name, "last_status": None, "last_run": None}
    return {"tool_name": tool_name, "last_status": row.status, "last_run": row.created_at.isoformat() if row.created_at else None}


@router.get("/tool-executions", response_model=ToolExecutionListResponse)
async def list_executions(
    tool_name: str | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> ToolExecutionListResponse:
    stmt = select(ToolExecution)
    count_stmt = select(func.count(ToolExecution.id))
    if tool_name:
        stmt, count_stmt = (stmt.where(ToolExecution.tool_name == tool_name),
                            count_stmt.where(ToolExecution.tool_name == tool_name))
    if task_id:
        stmt, count_stmt = (stmt.where(ToolExecution.task_id == task_id),
                            count_stmt.where(ToolExecution.task_id == task_id))
    if status_:
        stmt, count_stmt = (stmt.where(ToolExecution.status == status_),
                            count_stmt.where(ToolExecution.status == status_))
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(ToolExecution.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return ToolExecutionListResponse(
        data=[ToolExecutionResponse.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total,
                              total_pages=max(1, math.ceil(total / page_size))),
    )


@router.get("/tool-executions/{execution_id}", response_model=ToolExecutionResponse)
async def get_execution(execution_id: UUID, db: AsyncSession = Depends(get_async_db)) -> ToolExecutionResponse:
    row = await db.get(ToolExecution, execution_id)
    if row is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return ToolExecutionResponse.model_validate(row)
