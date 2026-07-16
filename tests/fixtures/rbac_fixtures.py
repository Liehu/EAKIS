"""RBAC test fixtures: file-based SQLite DB with seeded roles, permissions, users."""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.auth import hash_password
from src.api.dependencies import get_async_db
from src.api.main import app
from src.core.rbac_seed_data import PERMISSIONS, ROLE_PERMISSIONS, ROLES
from src.models import Base
from src.models.organization import Organization
from src.models.role import Permission, Role, RolePermission
from src.models.team import Team, TeamMember
from src.models.user import User

DB_URL_TEMPLATE = "sqlite+aiosqlite:///{path}"


async def _seed_rbac_data(async_session: AsyncSession) -> dict:
    """Seed RBAC data using an async session."""
    role_map: dict[str, str] = {}
    for rd in ROLES:
        r = Role(**rd)
        async_session.add(r)
        await async_session.flush()
        role_map[rd["name"]] = r.id

    perm_map: dict[str, str] = {}
    for action, display_name, category, description in PERMISSIONS:
        p = Permission(action=action, display_name=display_name, category=category, description=description)
        async_session.add(p)
        await async_session.flush()
        perm_map[action] = p.id

    for role_name, actions in ROLE_PERMISSIONS.items():
        for action in actions:
            async_session.add(RolePermission(role_id=role_map[role_name], permission_id=perm_map[action]))

    org = Organization(name="Test Org", slug="test-org", plan="enterprise", max_teams=50, max_members=200)
    async_session.add(org)
    await async_session.flush()

    admin = User(  # noqa: E501
        org_id=org.id, email="admin@test.local",
        hashed_password=hash_password("admin123"), display_name="Admin User",
    )
    engineer = User(  # noqa: E501
        org_id=org.id, email="engineer@test.local",
        hashed_password=hash_password("eng12345"), display_name="Engineer User",
    )
    analyst = User(  # noqa: E501
        org_id=org.id, email="analyst@test.local",
        hashed_password=hash_password("ana12345"), display_name="Analyst User",
    )
    async_session.add_all([admin, engineer, analyst])
    await async_session.flush()

    team = Team(org_id=org.id, name="Test Team", description="Test team")
    async_session.add(team)
    await async_session.flush()

    async_session.add(TeamMember(team_id=team.id, user_id=admin.id, role_id=role_map["super_admin"]))
    async_session.add(TeamMember(team_id=team.id, user_id=engineer.id, role_id=role_map["engineer"]))
    async_session.add(TeamMember(team_id=team.id, user_id=analyst.id, role_id=role_map["analyst"]))

    await async_session.commit()
    return {
        "org_id": str(org.id),
        "admin_id": str(admin.id),
        "engineer_id": str(engineer.id),
        "analyst_id": str(analyst.id),
        "team_id": str(team.id),
        "role_map": {k: str(v) for k, v in role_map.items()},
    }


async def _setup_db(db_path: str) -> dict:
    """Create tables and seed data in a self-contained async context."""
    url = DB_URL_TEMPLATE.format(path=db_path)
    engine = create_async_engine(url, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        ctx = await _seed_rbac_data(session)
    await engine.dispose()  # flush WAL, close all connections cleanly
    return ctx


@pytest.fixture(scope="function")
def rbac_client():
    """TestClient with RBAC data and async DB dependency override."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Step 1: Create tables + seed data in an isolated loop, then dispose engine
    ctx = asyncio.run(_setup_db(db_path))

    # Step 2: Create a fresh engine for TestClient (its own loop, fresh connections)
    url = DB_URL_TEMPLATE.format(path=db_path)
    async_engine = create_async_engine(url, connect_args={"check_same_thread": False})
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_async_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db

    client = TestClient(app)
    yield client, ctx

    app.dependency_overrides.clear()
    asyncio.run(async_engine.dispose())
    os.close(db_fd)
    os.unlink(db_path)


def _make_token_for_user(client_obj, email: str, password: str) -> tuple:
    """Login and return (token, client, context)."""
    client, ctx = client_obj
    resp = client.post("/v1/auth/token", data={"username": email, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    return token, client, ctx


@pytest.fixture(scope="function")
def admin_token(rbac_client):
    return _make_token_for_user(rbac_client, "admin@test.local", "admin123")


@pytest.fixture(scope="function")
def engineer_token(rbac_client):
    return _make_token_for_user(rbac_client, "engineer@test.local", "eng12345")


@pytest.fixture(scope="function")
def analyst_token(rbac_client):
    return _make_token_for_user(rbac_client, "analyst@test.local", "ana12345")
