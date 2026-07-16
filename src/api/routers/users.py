"""User management API endpoints (admin)."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo, hash_password
from src.api.dependencies import get_async_db
from src.api.deps.permissions import PermissionAction, require_permission
from src.api.schemas.user import Pagination, UserCreateRequest, UserListResponse, UserResponse, UserUpdateRequest
from src.models.role import Role
from src.models.team import Team, TeamMember
from src.models.user import User

router = APIRouter(tags=["admin-users"])


@router.get("/admin/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    org_id: UUID | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> UserListResponse:
    """List users with pagination, optionally filtered by org."""
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if org_id:
        stmt = stmt.where(User.org_id == org_id)
        count_stmt = count_stmt.where(User.org_id == org_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return UserListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Create a new user."""
    # Use the creating user's org if no org specified (via team assignment)
    org_id = UUID(user.org_id)

    # Check for duplicate email in org
    existing = await db.execute(
        select(User).where(User.org_id == org_id, User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists in this organization")

    # Validate role
    role_stmt = select(Role).where(Role.name == body.role_name)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {body.role_name}")

    new_user = User(
        org_id=org_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        phone=body.phone,
    )
    db.add(new_user)
    await db.flush()

    # Assign to teams if specified
    if body.team_ids:
        for team_id in body.team_ids:
            team = await db.get(Team, team_id)
            if team and str(team.org_id) == user.org_id:
                member = TeamMember(team_id=team_id, user_id=new_user.id, role_id=role.id)
                db.add(member)

    await db.commit()
    await db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Get user detail."""
    db_user = await db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(db_user)


@router.patch("/admin/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Update user information."""
    db_user = await db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Soft delete user (set is_active=False)."""
    db_user = await db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db_user.is_active = False
    await db.commit()
