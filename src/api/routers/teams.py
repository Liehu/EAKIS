"""Team management API endpoints (admin)."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo
from src.api.dependencies import get_async_db
from src.api.deps.permissions import PermissionAction, require_permission
from src.api.schemas.team import (
    Pagination,
    TeamCreateRequest,
    TeamDetailResponse,
    TeamListResponse,
    TeamMemberAddRequest,
    TeamMemberResponse,
    TeamMemberUpdateRequest,
    TeamResponse,
    TeamUpdateRequest,
)
from src.models.role import Role
from src.models.team import Team, TeamMember
from src.models.user import User

router = APIRouter(tags=["admin-teams"])


def _team_with_member_count(stmt):
    """Add member count subquery to a team select."""
    member_count_sq = (
        select(func.count(TeamMember.user_id))
        .where(TeamMember.team_id == Team.id)
        .correlate(Team)
        .scalar_subquery()
        .label("member_count")
    )
    return stmt.add_columns(member_count_sq)


@router.get("/admin/teams", response_model=TeamListResponse)
async def list_teams(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    org_id: UUID | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamListResponse:
    """List teams with pagination."""
    # org_admin can see all org teams; team_lead sees own teams
    if user.role not in ("super_admin", "org_admin") and org_id is None:
        org_id = UUID(user.org_id)

    stmt = select(Team)
    count_stmt = select(func.count(Team.id))

    if org_id:
        stmt = stmt.where(Team.org_id == org_id)
        count_stmt = count_stmt.where(Team.org_id == org_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(Team.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    teams = result.scalars().all()

    items = []
    for team in teams:
        mc = (await db.execute(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
        )).scalar() or 0
        items.append(TeamResponse(
            id=team.id,
            org_id=team.org_id,
            name=team.name,
            description=team.description,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=mc,
        ))

    return TeamListResponse(
        data=items,
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.post("/admin/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamResponse:
    """Create a new team."""
    org_id = UUID(user.org_id)

    # Check uniqueness
    existing = await db.execute(
        select(Team).where(Team.org_id == org_id, Team.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(  # noqa: E501
            status_code=status.HTTP_409_CONFLICT,
            detail="Team name already exists in this organization",
        )

    team = Team(org_id=org_id, name=body.name, description=body.description)
    db.add(team)
    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id, org_id=team.org_id, name=team.name,
        description=team.description, created_at=team.created_at,
        updated_at=team.updated_at, member_count=0,
    )


@router.get("/admin/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamDetailResponse:
    """Get team detail with members."""
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Get members
    stmt = (
        select(TeamMember, Role.name.label("role_name"), User.display_name, User.email)
        .join(Role, TeamMember.role_id == Role.id)
        .join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == team_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    members = [
        TeamMemberResponse(
            user_id=str(tm.user_id),
            team_id=str(tm.team_id),
            role_name=role_name,
            display_name=display_name,
            email=email,
            joined_at=tm.joined_at,
            invited_by=str(tm.invited_by) if tm.invited_by else None,
        )
        for tm, role_name, display_name, email in rows
    ]

    mc = len(members)
    return TeamDetailResponse(
        id=team.id, org_id=team.org_id, name=team.name,
        description=team.description, created_at=team.created_at,
        updated_at=team.updated_at, member_count=mc, members=members,
    )


@router.patch("/admin/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    body: TeamUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamResponse:
    """Update team info."""
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)

    mc = (await db.execute(
        select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
    )).scalar() or 0

    return TeamResponse(
        id=team.id, org_id=team.org_id, name=team.name,
        description=team.description, created_at=team.created_at,
        updated_at=team.updated_at, member_count=mc,
    )


@router.delete("/admin/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete a team."""
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    await db.delete(team)
    await db.commit()


# --- Team member management ---

@router.post("/admin/teams/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: UUID,
    body: TeamMemberAddRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamMemberResponse:
    """Add a member to a team."""
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    target_user = await db.get(User, body.user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if already a member
    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == body.user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this team")

    role = await db.execute(select(Role).where(Role.name == body.role_name))
    role_obj = role.scalar_one_or_none()
    if role_obj is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {body.role_name}")

    member = TeamMember(
        team_id=team_id,
        user_id=body.user_id,
        role_id=role_obj.id,
        invited_by=UUID(user.id),
    )
    db.add(member)
    await db.commit()

    return TeamMemberResponse(
        user_id=str(body.user_id),
        team_id=str(team_id),
        role_name=body.role_name,
        display_name=target_user.display_name,
        email=target_user.email,
        joined_at=member.joined_at,
        invited_by=user.id,
    )


@router.patch("/admin/teams/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member(
    team_id: UUID,
    user_id: UUID,
    body: TeamMemberUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> TeamMemberResponse:
    """Update a team member's role."""
    member = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    tm = member.scalar_one_or_none()
    if tm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    role = await db.execute(select(Role).where(Role.name == body.role_name))
    role_obj = role.scalar_one_or_none()
    if role_obj is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {body.role_name}")

    tm.role_id = role_obj.id
    await db.commit()

    target_user = await db.get(User, user_id)
    return TeamMemberResponse(
        user_id=str(user_id),
        team_id=str(team_id),
        role_name=body.role_name,
        display_name=target_user.display_name if target_user else "",
        email=target_user.email if target_user else "",
        joined_at=tm.joined_at,
        invited_by=str(tm.invited_by) if tm.invited_by else None,
    )


@router.delete("/admin/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.TEAM_MANAGE)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Remove a member from a team."""
    member = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    tm = member.scalar_one_or_none()
    if tm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    await db.delete(tm)
    await db.commit()
