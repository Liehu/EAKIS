"""Seed script for RBAC data: roles, permissions, role-permission mappings, default org and admin user.

Usage:
    python scripts/seed_rbac.py [--password DEFAULT_PASSWORD]

Requires the database to be accessible (same config as .env).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.auth import hash_password
from src.core.rbac_seed_data import PERMISSIONS, ROLE_PERMISSIONS, ROLES
from src.core.settings import get_settings
from src.models import Organization, Permission, Role, RolePermission, Team, TeamMember, User
from src.models.database import Base, SessionLocal, engine


def seed_roles(session) -> dict[str, str]:
    """Insert system roles, return name->id mapping."""
    name_to_id = {}
    for role_def in ROLES:
        existing = session.execute(
            __import__("sqlalchemy").select(Role).where(Role.name == role_def["name"])
        ).scalar_one_or_none()
        if existing:
            name_to_id[role_def["name"]] = str(existing.id)
            print(f"  Role '{role_def['name']}' already exists, skipping.")
        else:
            role = Role(**role_def)
            session.add(role)
            session.flush()
            name_to_id[role_def["name"]] = str(role.id)
            print(f"  Created role '{role_def['name']}' ({role.id})")
    return name_to_id


def seed_permissions(session) -> dict[str, str]:
    """Insert permissions, return action->id mapping."""
    from sqlalchemy import select
    action_to_id = {}
    for action, display_name, category, description in PERMISSIONS:
        existing = session.execute(
            select(Permission).where(Permission.action == action)
        ).scalar_one_or_none()
        if existing:
            action_to_id[action] = str(existing.id)
        else:
            perm = Permission(action=action, display_name=display_name, category=category, description=description)
            session.add(perm)
            session.flush()
            action_to_id[action] = str(perm.id)
            print(f"  Created permission '{action}'")
    return action_to_id


def seed_role_permissions(session, role_map: dict[str, str], perm_map: dict[str, str]) -> int:
    """Insert role-permission mappings. Return count of new mappings."""
    from uuid import UUID

    from sqlalchemy import select
    count = 0
    for role_name, actions in ROLE_PERMISSIONS.items():
        role_id = UUID(role_map[role_name])
        for action in actions:
            perm_id = UUID(perm_map[action])
            existing = session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == perm_id,
                )
            ).scalar_one_or_none()
            if not existing:
                session.add(RolePermission(role_id=role_id, permission_id=perm_id))
                count += 1
    session.flush()
    print(f"  Created {count} role-permission mappings")
    return count


def seed_default_org(session) -> Organization:
    """Create default organization if not exists."""
    from sqlalchemy import select
    settings = get_settings()
    existing = session.execute(
        select(Organization).where(Organization.slug == settings.default_org_slug)
    ).scalar_one_or_none()
    if existing:
        print(f"  Organization '{existing.name}' already exists, skipping.")
        return existing
    org = Organization(  # noqa: E501
        name="默认组织", slug=settings.default_org_slug,
        plan="enterprise", max_teams=50, max_members=200,
    )
    session.add(org)
    session.flush()
    print(f"  Created organization '{org.name}' ({org.id})")
    return org


def seed_default_admin(session, org: Organization, password: str) -> User:
    """Create default admin user if not exists."""
    from sqlalchemy import select
    email = "admin@eakis.local"
    existing = session.execute(
        select(User).where(User.org_id == org.id, User.email == email)
    ).scalar_one_or_none()
    if existing:
        print(f"  Admin user '{email}' already exists, skipping.")
        return existing
    admin = User(
        org_id=org.id,
        email=email,
        hashed_password=hash_password(password),
        display_name="系统管理员",
    )
    session.add(admin)
    session.flush()
    print(f"  Created admin user '{email}' ({admin.id})")
    return admin


def seed_default_team(session, org: Organization, admin: User, role_map: dict[str, str]) -> Team:
    """Create default team and add admin as super_admin."""
    from uuid import UUID

    from sqlalchemy import select
    team_name = "默认团队"
    existing = session.execute(
        select(Team).where(Team.org_id == org.id, Team.name == team_name)
    ).scalar_one_or_none()
    if existing:
        print(f"  Team '{team_name}' already exists, skipping.")
        return existing
    team = Team(org_id=org.id, name=team_name, description="默认团队，包含系统管理员")
    session.add(team)
    session.flush()
    print(f"  Created team '{team_name}' ({team.id})")

    # Add admin as super_admin
    super_admin_role_id = UUID(role_map["super_admin"])
    member = TeamMember(team_id=team.id, user_id=admin.id, role_id=super_admin_role_id)
    session.add(member)
    session.flush()
    print(f"  Added admin to team '{team_name}' as super_admin")
    return team


def main():
    parser = argparse.ArgumentParser(description="Seed RBAC data")
    parser.add_argument("--password", default="eakis2024", help="Default admin password")
    args = parser.parse_args()

    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        print("\nSeeding roles...")
        role_map = seed_roles(session)

        print("\nSeeding permissions...")
        perm_map = seed_permissions(session)

        print("\nSeeding role-permission mappings...")
        seed_role_permissions(session, role_map, perm_map)

        print("\nSeeding default organization...")
        org = seed_default_org(session)

        print("\nSeeding default admin user...")
        admin = seed_default_admin(session, org, args.password)

        print("\nSeeding default team...")
        seed_default_team(session, org, admin, role_map)

        session.commit()
        print("\nSeed completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"\nSeed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
