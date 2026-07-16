"""Task CRUD API router.

Endpoints:
  POST   /v1/tasks                       - Create task
  GET    /v1/tasks                       - List tasks (paginated)
  GET    /v1/tasks/{task_id}             - Get task detail
  PUT    /v1/tasks/{task_id}             - Update task
  DELETE /v1/tasks/{task_id}             - Delete task
  GET    /v1/tasks/{task_id}/status      - Get task status
  POST   /v1/tasks/{task_id}/pause       - Pause task
  POST   /v1/tasks/{task_id}/resume      - Resume task
  POST   /v1/tasks/{task_id}/cancel      - Cancel task
  POST   /v1/tasks/{task_id}/retry       - Retry failed task
  POST   /v1/tasks/batch/cancel          - Batch cancel tasks
  POST   /v1/tasks/batch/resume         - Batch resume tasks
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.dependencies import get_async_db
from src.api.schemas.task import (
    STAGE_ORDER,
    StageDetail,
    TaskBatchActionRequest,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskItem,
    TaskListResponse,
    TaskStatusResponse,
    TaskUpdateRequest,
    derive_stage_details,
)
from src.models.asset import Asset
from src.models.task import Task
from src.models.vulnerability import Vulnerability

router = APIRouter(tags=["tasks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_to_item(task: Task) -> TaskItem:
    """Convert ORM Task to TaskItem response schema."""
    config = task.config or {}
    metadata_ = task.metadata_ or {}
    task_type = config.get("task_type") or metadata_.get("task_type")

    return TaskItem(
        task_id=str(task.id),
        task_type=task_type,
        company_name=task.company_name,
        company_aliases=task.company_aliases or [],
        industry=task.industry,
        status=task.status if isinstance(task.status, str) else task.status.value,
        current_stage=task.current_stage,
        progress=task.progress,
        authorized_scope=task.authorized_scope or {},
        config=config,
        error_message=task.error_message,
        retry_count=task.retry_count,
        created_by_user_id=task.created_by,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


async def _build_detail_response(db: AsyncSession, task: Task) -> TaskDetailResponse:
    """统一组装 TaskDetailResponse (含 stats + stage_details)."""
    item = _task_to_item(task)
    stats = await _count_task_stats(db, task.id)
    # 整体已完成/失败/取消时, 阶段状态随之调整
    current_stage = task.current_stage
    if task.status in ("completed", "success"):
        details = {s: StageDetail(status="completed") for s in STAGE_ORDER}
    elif task.status in ("failed", "error") and current_stage:
        details = derive_stage_details(current_stage, stats)
        if current_stage in details:
            details[current_stage] = StageDetail(status="failed")
    else:
        details = derive_stage_details(current_stage, stats)
    return TaskDetailResponse(
        **item.model_dump(),
        stats=stats,
        stage_details=details,
    )


async def _count_task_stats(db: AsyncSession, task_id: UUID) -> dict:
    """Count related assets and vulnerabilities for a task."""
    from src.models.keyword import Keyword

    assets_total = await db.scalar(
        select(func.count()).where(Asset.task_id == task_id)
    ) or 0

    assets_confirmed = await db.scalar(
        select(func.count()).where(Asset.task_id == task_id, Asset.confirmed.is_(True))
    ) or 0

    keywords_total = await db.scalar(
        select(func.count()).where(Keyword.task_id == task_id)
    ) or 0

    vulns_total = await db.scalar(
        select(func.count()).where(Vulnerability.task_id == task_id)
    ) or 0

    vulns_confirmed = await db.scalar(
        select(func.count()).where(
            Vulnerability.task_id == task_id,
            Vulnerability.human_confirmed.is_(True),
        )
    ) or 0

    return {
        "assets_found": assets_total,
        "assets_confirmed": assets_confirmed,
        "interfaces_crawled": keywords_total,  # approx, no Interface model yet
        "vulns_detected": vulns_total,
        "vulns_confirmed": vulns_confirmed,
    }


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks", response_model=TaskDetailResponse, status_code=201)
async def create_task(
    body: TaskCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
) -> TaskDetailResponse:
    """Create a new detection task."""
    config = body.config or {}
    config["task_type"] = body.task_type

    task = Task(
        company_name=body.company_name,
        company_aliases=body.company_aliases,
        industry=body.industry,
        authorized_scope=body.authorized_scope,
        config=config,
        org_id=UUID(user.org_id) if user.org_id else None,
        created_by_user_id=UUID(user.id) if user.id else None,
        status="pending",
        progress=0.0,
    )
    db.add(task)
    await db.flush()
    await db.commit()
    await db.refresh(task)

    item = _task_to_item(task)
    return await _build_detail_response(db, task)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskListResponse:
    """List tasks with optional status filter and pagination."""
    stmt = select(Task).order_by(Task.created_at.desc())

    if status:
        stmt = stmt.where(Task.status == status)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.scalar(count_stmt)) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return TaskListResponse(
        data=[_task_to_item(t) for t in tasks],
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskDetailResponse:
    """Get task detail by ID."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    item = _task_to_item(task)
    return await _build_detail_response(db, task)


@router.put("/tasks/{task_id}", response_model=TaskDetailResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskDetailResponse:
    """Update a task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(task)

    item = _task_to_item(task)
    return await _build_detail_response(db, task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> None:
    """Delete a task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


# ---------------------------------------------------------------------------
# Status endpoints
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskStatusResponse:
    """Get task status summary."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=str(task.id),
        status=task.status if isinstance(task.status, str) else task.status.value,
        current_stage=task.current_stage,
        progress=task.progress,
        error_message=task.error_message,
    )


@router.post("/tasks/{task_id}/pause", response_model=TaskStatusResponse)
async def pause_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskStatusResponse:
    """Pause a running task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "running":
        raise HTTPException(status_code=400, detail="Only running tasks can be paused")

    task.status = "paused"
    await db.flush()
    await db.commit()
    await db.refresh(task)

    return TaskStatusResponse(
        task_id=str(task.id),
        status="paused",
        current_stage=task.current_stage,
        progress=task.progress,
        error_message=task.error_message,
    )


@router.post("/tasks/{task_id}/resume", response_model=TaskStatusResponse)
async def resume_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskStatusResponse:
    """Resume a paused task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused tasks can be resumed")

    task.status = "running"
    task.started_at = task.started_at or datetime.now(UTC)
    await db.flush()
    await db.commit()
    await db.refresh(task)

    return TaskStatusResponse(
        task_id=str(task.id),
        status="running",
        current_stage=task.current_stage,
        progress=task.progress,
        error_message=task.error_message,
    )


@router.post("/tasks/{task_id}/cancel", response_model=TaskStatusResponse)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskStatusResponse:
    """Cancel a task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a task that is already {task.status}",
        )

    task.status = "cancelled"
    await db.flush()
    await db.commit()
    await db.refresh(task)

    return TaskStatusResponse(
        task_id=str(task.id),
        status="cancelled",
        current_stage=task.current_stage,
        progress=task.progress,
        error_message=task.error_message,
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskDetailResponse)
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> TaskDetailResponse:
    """Retry a failed task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    task.status = "pending"
    task.error_message = None
    task.retry_count = (task.retry_count or 0) + 1
    await db.flush()
    await db.commit()
    await db.refresh(task)

    item = _task_to_item(task)
    return await _build_detail_response(db, task)


# ---------------------------------------------------------------------------
# Batch endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks/batch/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def batch_cancel_tasks(
    body: TaskBatchActionRequest,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> None:
    """Batch cancel multiple tasks."""
    task_ids = [UUID(tid) for tid in body.task_ids]
    await db.execute(
        update(Task)
        .where(
            Task.id.in_(task_ids),
            Task.status.notin_(["completed", "cancelled"]),
        )
        .values(status="cancelled")
    )
    await db.commit()


@router.post("/tasks/batch/resume", status_code=status.HTTP_204_NO_CONTENT)
async def batch_resume_tasks(
    body: TaskBatchActionRequest,
    db: AsyncSession = Depends(get_async_db),
    _user=Depends(get_current_user),
) -> None:
    """Batch resume multiple paused tasks."""
    task_ids = [UUID(tid) for tid in body.task_ids]
    await db.execute(
        update(Task)
        .where(Task.id.in_(task_ids), Task.status == "paused")
        .values(status="running")
    )
    await db.commit()
