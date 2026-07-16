"""JWT 认证模块 — token 创建/验证 + 用户依赖."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

from src.core.settings import get_settings

router = APIRouter(tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# 开发模式硬编码用户，生产环境应替换为数据库查询
# super_admin 绕过 require_permission; org_id 用于 companies router 的 UUID(user.org_id)
# NOTE: login 优先查 DB (seed_rbac 创建的真实账号); 仅当 DB 查不到时 fallback 到 _DEV_USERS.
_DEV_USERS: dict[str, dict[str, str]] = {
    "admin": {"username": "admin", "password": "eakis2024", "role": "super_admin"},
    "analyst": {"username": "analyst", "password": "eakis2024", "role": "analyst"},
}

# 开发模式默认组织 ID (与 seed_rbac 创建的默认组织一致; 真实环境从 DB 查)
_DEV_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

# 角色优先级: super_admin > org_admin > team_lead > engineer/analyst > auditor
_ROLE_PRIORITY = ["super_admin", "org_admin", "team_lead", "engineer", "analyst", "auditor"]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserInfo(BaseModel):
    username: str
    role: str = "analyst"
    org_id: str = ""
    id: str | None = None
    permissions: list[str] = []


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ─── Refresh token 工具函数 ────────────────────────────────────────────────

def _generate_refresh_token() -> tuple[str, str]:
    """生成 refresh token，返回 (明文 token, 用于存储的 hash)."""
    raw = secrets.token_urlsafe(48)
    return raw, pwd_context.hash(raw)


def create_refresh_token_for_user(user_id: str) -> str:
    """为用户签发并持久化一个 refresh token，返回明文 token (仅此一次可见)."""
    from uuid import UUID

    from src.models.database import SessionLocal
    from src.models.user import UserRefreshToken

    settings = get_settings()
    raw, token_hash = _generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    with SessionLocal() as session:
        session.add(UserRefreshToken(
            user_id=UUID(user_id),
            token_hash=token_hash,
            expires_at=expires_at,
        ))
        session.commit()
    return raw


def _resolve_real_user_id(payload: dict) -> str | None:
    """从 token payload 解析真实的 user_id (优先 uid 字段)."""
    uid = payload.get("uid")
    if uid:
        return str(uid)
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInfo:
    payload = decode_access_token(token)
    # 仅接受 access token
    if payload.get("type") not in (None, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    role = payload.get("role", "analyst")
    # 开发模式: super_admin 拥有全部权限, org_id 指向默认组织
    permissions = ["*"] if role == "super_admin" else []
    org_id = payload.get("org_id", _DEV_DEFAULT_ORG_ID)
    uid = payload.get("uid")
    # 开发模式: 若 token 里的 org_id 不是真实组织, 从 DB 解析默认组织 slug 对应的真实 ID
    # (seed_rbac 创建的真实组织 ID 是随机的, 与硬编码 _DEV_DEFAULT_ORG_ID 不一致)
    if role == "super_admin":
        try:
            from src.core.settings import get_settings
            from src.models.database import SessionLocal
            from src.models.organization import Organization
            from sqlalchemy import select
            settings = get_settings()
            with SessionLocal() as session:
                org = session.scalar(select(Organization).where(Organization.slug == settings.default_org_slug))
                if org is not None:
                    org_id = str(org.id)
        except Exception:
            pass  # 保持默认 org_id
    return UserInfo(
        username=username, role=role,
        org_id=org_id,
        id=uid,
        permissions=permissions,
    )


def _authenticate_db_user(email_or_username: str, password: str) -> dict | None:
    """查 DB 验证用户 (seed_rbac 创建的真实账号). 返回 {sub, role, org_id, uid} 或 None.

    username 可以是 email 或 display_name; 角色取 TeamMember 中最高权限 (super_admin 最优).
    """
    try:
        from src.models.database import SessionLocal
        from src.models.user import User
        from src.models.team import TeamMember
        from src.models.role import Role
        from sqlalchemy import or_, select

        with SessionLocal() as session:
            user = session.scalar(
                select(User).where(
                    or_(User.email == email_or_username, User.display_name == email_or_username)
                )
            )
            if user is None or not user.is_active:
                return None
            if not verify_password(password, user.hashed_password):
                return None
            # 取该用户在 TeamMember 中的角色 (最高权限). 无 team 记录则默认 analyst.
            rows = session.execute(
                select(Role.name).join(TeamMember, TeamMember.role_id == Role.id).where(TeamMember.user_id == user.id)
            ).scalars().all()
            role = "analyst"
            for r in rows:
                if r in _ROLE_PRIORITY and _ROLE_PRIORITY.index(r) < _ROLE_PRIORITY.index(role):
                    role = r
            # 登录成功, 更新 last_login_at
            user.last_login_at = datetime.now(timezone.utc)
            session.commit()
            return {
                "sub": user.email,
                "role": role,
                "org_id": str(user.org_id),
                "uid": str(user.id),
            }
    except Exception:
        return None


def _build_me_payload(user_id: str | None, role: str, org_id: str, username: str) -> dict:
    """组装前端 /v1/auth/me 期望的完整用户信息 dict.

    DB 用户返回完整字段 (含 permissions/teams); dev 硬编码用户返回精简信息.
    """
    # 默认 (dev 硬编码用户) 返回值
    base = {
        "id": user_id or "",
        "org_id": org_id,
        "email": username,
        "display_name": username,
        "phone": None,
        "avatar_url": None,
        "is_active": True,
        "last_login_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "permissions": ["*"] if role == "super_admin" else [],
        "teams": {},
    }
    if not user_id:
        return base

    try:
        from src.models.database import SessionLocal
        from src.models.user import User
        from src.models.team import Team, TeamMember
        from src.models.role import Role, Permission
        from sqlalchemy import select

        with SessionLocal() as session:
            user = session.get(User, user_id)
            if user is None:
                return base

            # 收集该用户所有 team 成员记录 -> 最高角色 + 各 team 角色
            members = session.execute(
                select(TeamMember).where(TeamMember.user_id == user.id)
            ).scalars().all()

            # roles 去重并按优先级取最高
            role_names: list[str] = []
            teams: dict[str, dict[str, str]] = {}
            for m in members:
                r = session.get(Role, m.role_id)
                if r is None:
                    continue
                role_names.append(r.name)
                team = session.get(Team, m.team_id)
                if team is not None:
                    teams[str(team.id)] = {"name": team.name, "role": r.name}

            top_role = role
            for rn in role_names:
                if rn in _ROLE_PRIORITY and _ROLE_PRIORITY.index(rn) < _ROLE_PRIORITY.index(top_role):
                    top_role = rn

            # 收集权限 action (通过所有 team member 的 role -> permissions)
            perm_actions = session.execute(
                select(Permission.action)
                .join(Role.permissions)
                .join(TeamMember, TeamMember.role_id == Role.id)
                .where(TeamMember.user_id == user.id)
            ).scalars().all()
            permissions = sorted(set(perm_actions)) or (["*"] if top_role == "super_admin" else [])

            return {
                "id": str(user.id),
                "org_id": str(user.org_id),
                "email": user.email,
                "display_name": user.display_name,
                "phone": user.phone,
                "avatar_url": user.avatar_url,
                "is_active": bool(user.is_active),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "role": top_role,
                "permissions": permissions,
                "teams": teams,
            }
    except Exception:
        return base


# ─── 请求/响应模型 ─────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class InitAdminRequest(BaseModel):
    email: str
    password: str
    display_name: str


class SystemStatusResponse(BaseModel):
    initialized: bool


class MessageResponse(BaseModel):
    success: bool = True


# ─── 路由 ──────────────────────────────────────────────────────────────────

def _issue_token_pair(db_user: dict) -> TokenResponse:
    """根据 DB 验证结果签发 access + refresh token 对."""
    access = create_access_token(data={
        "sub": db_user["sub"], "role": db_user["role"],
        "org_id": db_user["org_id"], "uid": db_user["uid"],
    })
    refresh = create_refresh_token_for_user(db_user["uid"])
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    # 1. DB 优先验证 (真实账号: admin@eakis.local 等)
    db_user = _authenticate_db_user(form_data.username, form_data.password)
    if db_user is not None:
        return _issue_token_pair(db_user)

    # 2. Fallback: dev 硬编码用户 (admin / analyst)
    user = _DEV_USERS.get(form_data.username)
    if user is None or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={
        "sub": user["username"], "role": user["role"], "org_id": _DEV_DEFAULT_ORG_ID,
    })
    # dev 用户无 DB 记录, 无法持久化 refresh token, 返回一个无状态 refresh token 占位
    settings = get_settings()
    refresh_payload = {
        "sub": user["username"], "role": user["role"],
        "org_id": _DEV_DEFAULT_ORG_ID, "type": "refresh",
    }
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    refresh_payload.update({"exp": refresh_expire})
    refresh = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return TokenResponse(access_token=token, refresh_token=refresh)


@router.get("/auth/me")
async def get_me(current: UserInfo = Depends(get_current_user)) -> dict:
    """返回当前登录用户的完整信息 (前端 LoginStore.user)."""
    return _build_me_payload(current.id, current.role, current.org_id, current.username)


@router.get("/auth/system-status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """检测系统是否已初始化 (是否存在至少一个组织 + 一个用户)."""
    try:
        from src.models.database import SessionLocal
        from src.models.organization import Organization
        from src.models.user import User
        from sqlalchemy import func, select

        with SessionLocal() as session:
            org_count = session.scalar(select(func.count()).select_from(Organization))
            user_count = session.scalar(select(func.count()).select_from(User))
            initialized = bool(org_count and user_count)
        return SystemStatusResponse(initialized=initialized)
    except Exception:
        # 表不存在等异常, 视为未初始化
        return SystemStatusResponse(initialized=False)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_access_token(body: RefreshRequest) -> TokenResponse:
    """用 refresh token 换取新的 access + refresh token 对."""
    settings = get_settings()
    from src.models.database import SessionLocal
    from src.models.user import UserRefreshToken, User
    from src.models.team import TeamMember
    from src.models.role import Role
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    # 1. 先尝试匹配 DB 中持久化的 refresh token (DB 用户)
    try:
        with SessionLocal() as session:
            tokens = session.execute(
                select(UserRefreshToken).where(UserRefreshToken.revoked_at.is_(None))
            ).scalars().all()
            matched = None
            for t in tokens:
                if t.expires_at and t.expires_at < now:
                    continue
                if pwd_context.verify(body.refresh_token, t.token_hash):
                    matched = t
                    break

            if matched is not None:
                # 旋转: 吊销旧 token, 签发新对
                matched.revoked_at = now
                user = session.get(User, matched.user_id)
                if user is None or not user.is_active:
                    session.commit()
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
                rows = session.execute(
                    select(Role.name).join(TeamMember, TeamMember.role_id == Role.id).where(TeamMember.user_id == user.id)
                ).scalars().all()
                role = "analyst"
                for r in rows:
                    if r in _ROLE_PRIORITY and _ROLE_PRIORITY.index(r) < _ROLE_PRIORITY.index(role):
                        role = r
                db_user = {
                    "sub": user.email, "role": role,
                    "org_id": str(user.org_id), "uid": str(user.id),
                }
                session.commit()
                return _issue_token_pair(db_user)
    except HTTPException:
        raise
    except Exception:
        pass  # 继续尝试无状态 dev refresh token

    # 2. Fallback: 无状态 dev refresh token (JWT)
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    username = payload.get("sub")
    role = payload.get("role", "analyst")
    org_id = payload.get("org_id", _DEV_DEFAULT_ORG_ID)
    access = create_access_token(data={"sub": username, "role": role, "org_id": org_id})
    refresh_expire = now + timedelta(days=settings.jwt_refresh_expire_days)
    refresh_payload = {"sub": username, "role": role, "org_id": org_id, "type": "refresh", "exp": refresh_expire}
    refresh = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(current: UserInfo = Depends(get_current_user)) -> MessageResponse:
    """登出: 吊销该用户所有未过期的 refresh token (access token 短期自然过期)."""
    if current.id:
        try:
            from src.models.database import SessionLocal
            from src.models.user import UserRefreshToken
            from sqlalchemy import select

            now = datetime.now(timezone.utc)
            with SessionLocal() as session:
                tokens = session.execute(
                    select(UserRefreshToken).where(
                        UserRefreshToken.user_id == current.id,
                        UserRefreshToken.revoked_at.is_(None),
                    )
                ).scalars().all()
                for t in tokens:
                    t.revoked_at = now
                session.commit()
        except Exception:
            pass  # 登出不应因 DB 问题失败
    return MessageResponse(success=True)


@router.patch("/auth/me/password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current: UserInfo = Depends(get_current_user),
) -> MessageResponse:
    """修改当前用户密码."""
    if not current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dev users cannot change password")

    from src.models.database import SessionLocal
    from src.models.user import User
    from sqlalchemy import select

    with SessionLocal() as session:
        user = session.get(User, current.id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(body.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password incorrect")
        user.hashed_password = hash_password(body.new_password)
        session.commit()
    return MessageResponse(success=True)


@router.post("/auth/init-admin", response_model=TokenResponse)
async def init_admin(body: InitAdminRequest) -> TokenResponse:
    """首次部署初始化: 创建默认组织 + 管理员, 并返回登录 token 对.

    若系统已初始化 (存在用户), 拒绝重复初始化.
    """
    from src.models.database import SessionLocal
    from src.models.organization import Organization
    from src.models.user import User
    from src.models.team import Team, TeamMember
    from src.models.role import Role
    from sqlalchemy import func, select

    with SessionLocal() as session:
        # 已初始化则拒绝
        user_count = session.scalar(select(func.count()).select_from(User))
        if user_count:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System already initialized")

        # 确保默认组织存在
        settings = get_settings()
        org = session.scalar(select(Organization).where(Organization.slug == settings.default_org_slug))
        if org is None:
            org = Organization(name="默认组织", slug=settings.default_org_slug)
            session.add(org)
            session.flush()

        # 创建管理员
        if session.scalar(select(User).where(User.org_id == org.id, User.email == body.email)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        admin = User(
            org_id=org.id,
            email=body.email,
            hashed_password=hash_password(body.password),
            display_name=body.display_name,
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(admin)
        session.flush()

        # 放入默认团队并赋予 super_admin 角色
        super_admin_role = session.scalar(select(Role).where(Role.name == "super_admin"))
        if super_admin_role is not None:
            team = session.scalar(select(Team).where(Team.org_id == org.id))
            if team is None:
                team = Team(org_id=org.id, name="默认团队", description="默认团队，包含系统管理员")
                session.add(team)
                session.flush()
            session.add(TeamMember(team_id=team.id, user_id=admin.id, role_id=super_admin_role.id))

        session.commit()
        return _issue_token_pair({
            "sub": admin.email, "role": "super_admin",
            "org_id": str(org.id), "uid": str(admin.id),
        })
