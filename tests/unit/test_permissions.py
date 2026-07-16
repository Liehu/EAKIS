"""Unit tests for permission checking dependencies."""

from __future__ import annotations

import pytest

from src.api.auth import UserInfo
from src.api.deps.permissions import PermissionAction, require_permission, require_role


def _make_user(**overrides) -> UserInfo:
    defaults = {
        "id": "user-1",
        "email": "test@test.local",
        "display_name": "Test",
        "org_id": "org-1",
        "org_slug": "test",
        "role": "engineer",
        "permissions": ["task:read", "task:create", "asset:read"],
        "teams": {"team-1": {"role": "engineer"}},
    }
    defaults.update(overrides)
    return UserInfo(**defaults)


class TestRequirePermission:
    @pytest.mark.asyncio
    async def test_granted_when_user_has_permission(self):
        checker = require_permission(PermissionAction.TASK_READ)
        user = _make_user()
        result = await checker(user)
        assert result.email == "test@test.local"

    @pytest.mark.asyncio
    async def test_denied_when_user_lacks_permission(self):
        from fastapi import HTTPException
        checker = require_permission(PermissionAction.SYSTEM_ADMIN)
        user = _make_user()
        with pytest.raises(HTTPException) as exc:
            await checker(user)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_super_admin_bypasses_all(self):
        checker = require_permission(PermissionAction.SYSTEM_ADMIN)
        user = _make_user(role="super_admin", permissions=[])
        result = await checker(user)
        assert result.role == "super_admin"


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_granted_when_role_matches(self):
        checker = require_role("engineer", "team_lead")
        user = _make_user(role="engineer")
        result = await checker(user)
        assert result.role == "engineer"

    @pytest.mark.asyncio
    async def test_denied_when_role_not_in_list(self):
        from fastapi import HTTPException
        checker = require_role("team_lead", "org_admin")
        user = _make_user(role="engineer")
        with pytest.raises(HTTPException) as exc:
            await checker(user)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_super_admin_bypasses_role_check(self):
        checker = require_role("org_admin")
        user = _make_user(role="super_admin")
        result = await checker(user)
        assert result.role == "super_admin"
