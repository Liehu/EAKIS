# EAKIS RBAC 权限管理系统设计文档

> 本文档基于原型 `docs/前端原型.html` 中"系统设置 > 角色权限"需求，结合现有 `src/api/auth.py` 认证基础，设计完整的 RBAC 权限管理体系。

## 1. 现状分析

### 1.1 已有基础设施

| 组件 | 文件 | 状态 |
|-----|------|------|
| JWT Token 生成/验证 | `src/api/auth.py` | 已实现（HS256） |
| `get_current_user` 依赖 | `src/api/auth.py` | 已定义，**未应用到任何端点** |
| 硬编码用户（admin/analyst） | `src/api/auth.py` | 开发用，需替换 |
| 用户信息模型（UserInfo） | `src/api/auth.py` | 仅含 username + role |
| Task ORM模型 | `src/models/task.py` | `created_by` 为 VARCHAR，非FK |
| Vulnerability ORM模型 | `src/models/vulnerability.py` | `confirmed_by` 为 VARCHAR，非FK |
| 审计日志中间件 | `src/api/middleware/audit.py` | 已实现，未记录用户信息 |
| 限流中间件 | `src/api/middleware/rate_limit.py` | 按IP，非按用户/角色 |

### 1.2 缺失部分

- 无 User 数据库模型（用户存在内存字典中）
- 无 Organization / Team 数据模型
- 无 RBAC 权限矩阵
- 无权限校验装饰器/依赖
- JWT 中未包含组织/团队/角色映射信息
- 无用户管理 API 端点
- 无前端权限控制（路由守卫、按钮权限）

---

## 2. RBAC 模型设计

### 2.1 组织架构

```
Organization（组织/租户）
  │
  ├──< User（用户，归属于组织）
  │       │
  │       └──< TeamMember（团队成员，含角色）
  │               │
  │               └──< Team（团队）
  │                       │
  │                       └──< Task（任务，归属于团队）
  │                               │
  │                               ├──< Asset
  │                               ├──< Keyword
  │                               ├──< Vulnerability
  │                               ├──< IntelDocument
  │                               ├──< ApiInterface
  │                               ├──< Report
  │                               └──< AgentLog
```

### 2.2 角色定义

系统定义5个内置角色，不可自定义：

| 角色 | 标识 | 层级 | 描述 |
|-----|------|------|------|
| 超级管理员 | `super_admin` | 系统级 | 管理所有组织、全局配置、系统运维 |
| 组织管理员 | `org_admin` | 组织级 | 管理本组织内用户、团队、计费、配置 |
| 团队负责人 | `team_lead` | 团队级 | 创建/删除任务、管理团队成员、审批HIL |
| 执行工程师 | `engineer` | 团队级 | 创建任务、执行扫描/测试、查看全部数据 |
| 分析师 | `analyst` | 团队级 | 只读查看任务/资产/漏洞数据，不可触发测试 |
| 审计员 | `auditor` | 团队级 | 只读查看审计日志和报告，不可查看原始请求/响应 |

> **层级约束：**
> - `super_admin` 不受组织/团队限制，可访问所有数据
> - `org_admin` 可管理本组织内所有团队的任务
> - `team_lead` / `engineer` / `analyst` / `auditor` 只能访问所属团队的数据

---

## 3. 权限矩阵

### 3.1 操作权限定义

系统定义以下操作权限（Permission Actions）：

```python
class PermissionAction(str, Enum):
    # 任务管理
    TASK_CREATE = "task:create"           # 创建任务
    TASK_READ = "task:read"               # 查看/列出任务
    TASK_UPDATE = "task:update"           # 修改任务配置
    TASK_DELETE = "task:delete"           # 删除任务
    TASK_EXECUTE = "task:execute"         # 启动/暂停/恢复/取消任务
    TASK_BATCH = "task:batch"              # 批量操作（批量取消/恢复）

    # 任务编排（演练计划）
    ORCH_CREATE = "orch:create"            # 创建演练计划
    ORCH_READ = "orch:read"                # 查看/列出演练计划
    ORCH_UPDATE = "orch:update"            # 修改演练计划（名称、描述、添加/移除子任务）
    ORCH_DELETE = "orch:delete"            # 删除演练计划
    ORCH_EXECUTE = "orch:execute"          # 启动/暂停/恢复/取消演练
    ORCH_REPORT = "orch:report"            # 生成演练汇总报告

    # 情报采集
    INTEL_START = "intel:start"           # 启动情报采集
    INTEL_READ = "intel:read"             # 查看情报数据
    INTEL_RAG_SEARCH = "intel:rag_search" # RAG语义搜索

    # 关键词
    KEYWORD_READ = "keyword:read"         # 查看关键词
    KEYWORD_CREATE = "keyword:create"     # 添加关键词
    KEYWORD_DELETE = "keyword:delete"     # 删除关键词

    # 资产管理
    ASSET_READ = "asset:read"             # 查看资产
    ASSET_UPDATE = "asset:update"          # 更新资产（确认/标记风险）
    ASSET_EXPORT = "asset:export"         # 导出资产

    # 接口管理
    INTERFACE_READ = "interface:read"    # 查看接口
    INTERFACE_UPDATE = "interface:update" # 更新接口（优先级/备注）
    INTERFACE_RAW = "interface:raw"        # 查看原始请求/响应

    # 漏洞管理
    VULN_READ = "vuln:read"               # 查看漏洞
    VULN_UPDATE = "vuln:update"           # 更新漏洞状态（确认/误报）
    VULN_RAW = "vuln:raw"                 # 查看原始测试payload和响应

    # 渗透测试
    PENTEST_TRIGGER = "pentest:trigger"   # 触发渗透测试
    PENTEST_READ = "pentest:read"          # 查看渗透测试结果

    # 报告管理
    REPORT_GENERATE = "report:generate"    # 生成报告
    REPORT_READ = "report:read"            # 查看报告
    REPORT_DOWNLOAD = "report:download"    # 下载报告

    # 知识库管理
    KNOWLEDGE_READ = "knowledge:read"      # 查看知识库
    KNOWLEDGE_WRITE = "knowledge:write"    # 编辑知识库内容
    KNOWLEDGE_ADMIN = "knowledge:admin"    # 知识库管理（增删改模板/字典）

    # 工具管理
    TOOL_READ = "tool:read"               # 查看工具
    TOOL_EXECUTE = "tool:execute"         # 执行工具

    # 模板管理
    TEMPLATE_READ = "template:read"        # 查看模板
    TEMPLATE_WRITE = "template:write"      # 编辑模板

    # 企业管理
    COMPANY_READ = "company:read"          # 查看企业
    COMPANY_CREATE = "company:create"      # 创建企业
    COMPANY_UPDATE = "company:update"      # 更新企业
    COMPANY_DELETE = "company:delete"      # 删除企业

    # 团队管理
    TEAM_MANAGE = "team:manage"            # 管理团队成员（邀请/移除/改角色）

    # 系统管理
    SYSTEM_HEALTH = "system:health"       # 查看系统状态
    SYSTEM_CONFIG = "system:config"       # 修改系统配置（AI Provider、Webhook等）
    SYSTEM_AUDIT = "system:audit"         # 查看审计日志
    SYSTEM_ADMIN = "system:admin"         # 系统管理（用户/组织管理）
```

### 3.2 角色-权限矩阵

| 权限 | super_admin | org_admin | team_lead | engineer | analyst | auditor |
|------|:-----------:|:---------:|:---------:|:--------:|:-------:|:-------:|
| **任务管理** |
| task:create | Y | Y | Y | Y | - | - |
| task:read | Y | Y* | Y | Y | Y | - |
| task:update | Y | Y | Y | Y | - | - |
| task:delete | Y | Y | Y | - | - | - |
| task:execute | Y | Y | Y | Y | - | - |
| task:batch | Y | Y | Y | Y | - | - |
| **任务编排（演练）** |
| orch:create | Y | Y | Y | - | - | - |
| orch:read | Y | Y* | Y | Y | Y | - |
| orch:update | Y | Y | Y | - | - | - |
| orch:delete | Y | Y | Y | - | - | - |
| orch:execute | Y | Y | Y | Y | - | - |
| orch:report | Y | Y | Y | Y | Y | Y |
| **情报采集** |
| intel:start | Y | Y | Y | Y | - | - |
| intel:read | Y | Y* | Y | Y | Y | - |
| intel:rag_search | Y | Y* | Y | Y | Y | - |
| **关键词** |
| keyword:read | Y | Y* | Y | Y | Y | - |
| keyword:create | Y | Y | Y | Y | - | - |
| keyword:delete | Y | Y | Y | Y | - | - |
| **资产管理** |
| asset:read | Y | Y* | Y | Y | Y | - |
| asset:update | Y | Y | Y | Y | - | - |
| asset:export | Y | Y | Y | Y | Y | - |
| **接口管理** |
| interface:read | Y | Y* | Y | Y | Y | Y** |
| interface:update | Y | Y | Y | Y | - | - |
| interface:raw | Y | Y | Y | Y | - | - |
| **漏洞管理** |
| vuln:read | Y | Y* | Y | Y | Y | Y** |
| vuln:update | Y | Y | Y | Y | - | - |
| vuln:raw | Y | Y | Y | Y | - | - |
| **渗透测试** |
| pentest:trigger | Y | Y | Y | Y | - | - |
| pentest:read | Y | Y* | Y | Y | Y | Y** |
| **报告** |
| report:generate | Y | Y | Y | Y | - | Y |
| report:read | Y | Y* | Y | Y | Y | Y |
| report:download | Y | Y | Y | Y | Y | Y |
| **知识库** |
| knowledge:read | Y | Y | Y | Y | Y | Y |
| knowledge:write | Y | Y | Y | Y | - | - |
| knowledge:admin | Y | Y | - | - | - | - |
| **工具** |
| tool:read | Y | Y | Y | Y | Y | Y |
| tool:execute | Y | Y | Y | Y | - | - |
| **模板** |
| template:read | Y | Y | Y | Y | Y | Y |
| template:write | Y | Y | Y | Y | - | - |
| **企业管理** |
| company:read | Y | Y | Y | Y | Y | - |
| company:create | Y | Y | Y | Y | - | - |
| company:update | Y | Y | Y | Y | - | - |
| company:delete | Y | Y | Y | - | - | - |
| **团队** |
| team:manage | Y | Y | Y | - | - | - |
| **系统** |
| system:health | Y | Y | Y | Y | Y | Y |
| system:config | Y | Y | - | - | - | - |
| system:audit | Y | Y | Y | - | - | Y |
| system:admin | Y | - | - | - | - | - |

> **说明：**
> - `Y*` — `org_admin` 可访问本组织内所有团队的数据（不受team_id限制）
> - `Y**` — `auditor` 可查看脱敏数据（接口路径脱敏、漏洞标题保留但payload和响应脱敏）
> - `Y` — 有权限
> - `-` — 无权限（返回403）

---

## 4. 数据模型设计

### 4.1 新增数据库表

```sql
-- =========================================
-- 组织表
-- =========================================
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,     -- URL标识符
    plan        VARCHAR(50) NOT NULL DEFAULT 'standard',  -- standard|enterprise
    max_teams   INT NOT NULL DEFAULT 5,             -- plan限制最大团队数
    max_members INT NOT NULL DEFAULT 20,            -- plan限制最大成员数
    settings    JSONB NOT NULL DEFAULT '{}',       -- 组织级配置
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);

-- =========================================
-- 用户表
-- =========================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    email           VARCHAR(300) NOT NULL,
    hashed_password TEXT NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    phone           VARCHAR(50),
    avatar_url      VARCHAR(500),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, email)   -- 同组织内email唯一
);

CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- =========================================
-- 角色定义表（预填充，不可通过API修改）
-- =========================================
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) UNIQUE NOT NULL,       -- super_admin|org_admin|team_lead|engineer|analyst|auditor
    display_name VARCHAR(100) NOT NULL,              -- 显示名称
    description TEXT,
    level       INT NOT NULL,                       -- 层级数字，用于判断权限覆盖
    is_system   BOOLEAN NOT NULL DEFAULT TRUE       -- 系统内置角色不可删除
);

-- 预填充数据
INSERT INTO roles (name, display_name, level, is_system) VALUES
    ('super_admin', '超级管理员', 100, TRUE),
    ('org_admin', '组织管理员', 50, TRUE),
    ('team_lead', '团队负责人', 30, TRUE),
    ('engineer', '执行工程师', 20, TRUE),
    ('analyst', '分析师', 10, TRUE),
    ('auditor', '审计员', 5, TRUE);

-- =========================================
-- 团队表
-- =========================================
CREATE TABLE teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, name)
);

CREATE INDEX idx_teams_org_id ON teams(org_id);

-- =========================================
-- 团队成员表（用户-团队-角色）
-- =========================================
CREATE TABLE team_members (
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    invited_by  UUID REFERENCES users(id),
    PRIMARY KEY (team_id, user_id)
);

CREATE INDEX idx_team_members_user_id ON team_members(user_id);
CREATE INDEX idx_team_members_role_id ON team_members(role_id);

-- =========================================
-- 权限定义表（预填充，不可通过API修改）
-- =========================================
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action      VARCHAR(100) UNIQUE NOT NULL,      -- task:create, asset:read 等
    display_name VARCHAR(200) NOT NULL,
    category    VARCHAR(50) NOT NULL,               -- task|intel|asset|vuln|system 等
    description TEXT
);

-- 预填充数据（见3.1节 PermissionAction 枚举值）
-- INSERT INTO permissions ...

-- =========================================
-- 角色-权限关联表（预填充）
-- =========================================
CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- =========================================
-- 操作审计日志表
-- =========================================
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    username    VARCHAR(300),                       -- 冗余存储，防止用户删除后无法追溯
    org_id      UUID,
    team_id     UUID,
    action      VARCHAR(100) NOT NULL,             -- 执行的操作
    resource_type VARCHAR(50) NOT NULL,            -- 操作的资源类型
    resource_id VARCHAR(100),                      -- 操作的资源ID
    ip_address  INET,
    user_agent  TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    status_code  INT,
    duration_ms INT,
    detail      JSONB,                              -- 额外详情
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 按月分区
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

### 4.2 现有表修改

```sql
-- Task 表新增字段
ALTER TABLE tasks ADD COLUMN org_id UUID REFERENCES organizations(id);
ALTER TABLE tasks ADD COLUMN team_id UUID REFERENCES teams(id);
ALTER TABLE tasks ADD COLUMN created_by_user_id UUID REFERENCES users(id);

-- 创建索引
CREATE INDEX idx_tasks_org_id ON tasks(org_id);
CREATE INDEX idx_tasks_team_id ON tasks(team_id);
CREATE INDEX idx_tasks_created_by ON tasks(created_by_user_id);

-- ⚠️ 迁移注意：保留 created_by VARCHAR(100) 向后兼容，新代码使用 created_by_user_id
-- 后续版本可移除 created_by
```

### 4.3 ORM 模型文件规划

```
src/models/
├── organization.py    # Organization
├── user.py            # User
├── role.py            # Role, Permission, RolePermission
├── team.py            # Team, TeamMember
├── audit_log.py       # AuditLog
├── task.py            # Task (修改：增加 org_id, team_id, created_by_user_id)
└── vulnerability.py   # Vulnerability (修改：confirmed_by → FK)
```

---

## 5. 认证流程设计

### 5.1 JWT Token 结构

```json
{
  "sub": "user_uuid",
  "username": "zhangwei",
  "display_name": "张伟",
  "org_id": "org_uuid",
  "org_slug": "yunchuang",
  "teams": {
    "team_uuid_1": {
      "role": "engineer",
      "team_name": "安全研究组"
    },
    "team_uuid_2": {
      "role": "analyst",
      "team_name": "数据分析组"
    }
  },
  "permissions": [
    "task:create", "task:read", "task:update", "task:execute",
    "asset:read", "asset:update", ...
  ],
  "exp": 1735689600,
  "iat": 1735686000
}
```

**设计说明：**
- `teams` 为对象（非数组），包含每个团队的角色信息，避免二次查询
- `permissions` 为扁平数组，包含该用户所有团队角色的权限并集，便于前端快速判断
- Token 有效期默认60分钟，可通过环境变量配置
- 需要 Refresh Token 机制（见5.3节）

### 5.2 登录流程

```
┌─────────┐     POST /v1/auth/token      ┌─────────┐
│  前端    │ ──────────────────────────→ │  后端    │
│         │   { username, password }     │         │
│         │                               │ 1.验证  │
│         │                               │ 2.查询  │
│         │                               │ 3.构建  │
│         │                               │ 4.签发  │
│         │ ←──────────────────────────  │         │
│         │   { access_token,             │         │
│         │     refresh_token }           │         │
└─────────┘                               └─────────┘
```

### 5.3 Refresh Token 机制

```
┌─────────┐    POST /v1/auth/refresh    ┌─────────┐
│  前端    │ ──────────────────────────→ │  后端    │
│         │   { refresh_token }          │         │
│         │                               │ 1.验证  │
│         │                               │ 2.检查  │
│         │                               │ 3.轮换  │
│         │                               │ 4.签发  │
│         │ ←──────────────────────────  │         │
│         │   { access_token,             │         │
│         │     refresh_token(新) }       │         │
└─────────┘                               └─────────┘
```

**实现要点：**
- Refresh Token 存储在数据库 `user_refresh_tokens` 表中
- 每次使用后旧Token失效，签发新Token（Rotation）
- 支持主动吊销（logout时删除所有refresh token）
- Refresh Token 有效期7天

```sql
CREATE TABLE user_refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(128) NOT NULL,    -- SHA256(token)
    device_info TEXT,                     -- 设备/浏览器信息
    ip_address  INET,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ              -- 非NULL表示已吊销
);

CREATE INDEX idx_refresh_tokens_user ON user_refresh_tokens(user_id);
```

### 5.4 密码安全

- 使用 `bcrypt` 或 `passlib[bcrypt]` 进行密码哈希
- 最小密码长度：8字符
- 登录失败锁定：连续5次失败，锁定15分钟（per email）

---

## 6. 后端权限校验实现

### 6.1 权限校验依赖

```python
# src/api/deps/permissions.py

from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user, UserInfo
from src.models.database import get_async_db


class PermissionAction(str, Enum):
    """操作权限枚举 — 见3.1节完整定义"""
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    # ...其余权限项省略，见3.1节


async def require_permission(
    action: PermissionAction,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserInfo:
    """
    FastAPI 依赖注入：校验当前用户是否具有指定操作权限。
    无权限返回 403 Forbidden。
    """
    if user.role == "super_admin":
        return user

    # 从JWT中的permissions数组检查（避免每次查DB）
    # 权限已在登录时计算并写入token
    if action.value not in getattr(user, '_permissions', []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足：需要 {action.value}",
        )
    return user


def require_role(*roles: str):
    """
    角色校验依赖（简单场景）。
    用法: Depends(require_role("team_lead", "org_admin"))
    """
    async def checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role == "super_admin" or user.role in roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"角色限制：需要 {', '.join(roles)} 之一",
        )
    return checker


async def require_resource_access(
    action: PermissionAction,
    resource_type: str,   # "task"
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    resource_id: Optional[str] = None,  # 从路径参数获取
) -> UserInfo:
    """
    资源级别权限校验：
    1. 先检查操作权限
    2. 再检查用户是否有权访问该资源（通过 task_id → team_id 链路）
    """
    await require_permission(action, user, db)

    if user.role == "super_admin":
        return user

    # org_admin 可访问本组织所有数据
    if user.role == "org_admin" and resource_id:
        # 查询资源的org_id是否与用户org_id匹配
        pass

    # team级别角色：检查资源是否属于用户所在团队
    if resource_id and user.role not in ("super_admin", "org_admin"):
        # SELECT team_id FROM tasks WHERE id = :resource_id
        # 检查 user.teams 中是否包含该 team_id
        pass

    return user
```

### 6.2 路由端点应用权限

```python
# 示例：任务管理路由
from src.api.deps.permissions import require_permission, PermissionAction

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/")
async def create_task(
    request: CreateTaskRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TASK_CREATE)),
    db: AsyncSession = Depends(get_async_db),
):
    """创建任务 — 需 task:create 权限"""
    ...

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    user: UserInfo = Depends(require_permission(PermissionAction.TASK_READ)),
    db: AsyncSession = Depends(get_async_db),
):
    """查看任务 — 需 task:read 权限 + 资源归属校验"""
    ...
```

### 6.3 API 端点权限分配表

| 端点 | 方法 | 所需权限 |
|-----|------|---------|
| `/v1/auth/token` | POST | 无需认证 |
| `/v1/auth/refresh` | POST | 无需认证 |
| `/v1/health` | GET | 无需认证 |
| `/v1/tasks` | POST | task:create |
| `/v1/tasks` | GET | task:read |
| `/v1/tasks/{id}` | GET | task:read |
| `/v1/tasks/{id}` | PATCH | task:update |
| `/v1/tasks/{id}` | DELETE | task:delete |
| `/v1/tasks/{id}/pause` | POST | task:execute |
| `/v1/tasks/{id}/resume` | POST | task:execute |
| `/v1/tasks/{id}/cancel` | POST | task:execute |
| `/v1/tasks/{id}/retry` | POST | task:execute |
| `/v1/tasks/batch/cancel` | POST | task:batch |
| `/v1/tasks/batch/resume` | POST | task:batch |
| `/v1/orchestrations` | POST | orch:create |
| `/v1/orchestrations` | GET | orch:read |
| `/v1/orchestrations/{id}` | GET | orch:read |
| `/v1/orchestrations/{id}` | PATCH | orch:update |
| `/v1/orchestrations/{id}` | DELETE | orch:delete |
| `/v1/orchestrations/{id}/tasks` | POST | orch:update |
| `/v1/orchestrations/{id}/tasks` | GET | orch:read |
| `/v1/orchestrations/{id}/tasks/{tid}` | DELETE | orch:update |
| `/v1/orchestrations/{id}/start` | POST | orch:execute |
| `/v1/orchestrations/{id}/pause` | POST | orch:execute |
| `/v1/orchestrations/{id}/resume` | POST | orch:execute |
| `/v1/orchestrations/{id}/cancel` | POST | orch:execute |
| `/v1/orchestrations/{id}/summary` | GET | orch:read |
| `/v1/orchestrations/{id}/report` | POST | orch:report |
| `/v1/tasks/{id}/intelligence` | POST | intel:start |
| `/v1/tasks/{id}/intelligence` | GET | intel:read |
| `/v1/tasks/{id}/intelligence/documents` | GET | intel:read |
| `/v1/tasks/{id}/intelligence/dsl` | GET | intel:read |
| `/v1/tasks/{id}/intelligence/sources` | GET | intel:read |
| `/v1/intelligence/rag/search` | POST | intel:rag_search |
| `/v1/tasks/{id}/keywords` | GET | keyword:read |
| `/v1/tasks/{id}/keywords` | POST | keyword:create |
| `/v1/tasks/{id}/keywords/{kid}` | DELETE | keyword:delete |
| `/v1/tasks/{id}/assets/discover` | POST | task:execute |
| `/v1/tasks/{id}/assets` | GET | asset:read |
| `/v1/tasks/{id}/assets/{aid}` | GET | asset:read |
| `/v1/tasks/{id}/assets/{aid}` | PATCH | asset:update |
| `/v1/tasks/{id}/assets/export` | GET | asset:export |
| `/v1/tasks/{id}/interfaces/crawl` | POST | task:execute |
| `/v1/tasks/{id}/interfaces` | GET | interface:read |
| `/v1/tasks/{id}/interfaces/{iid}` | GET | interface:read |
| `/v1/tasks/{id}/interfaces/{iid}` | PATCH | interface:update |
| `/v1/tasks/{id}/vulnerabilities` | GET | vuln:read |
| `/v1/tasks/{id}/vulnerabilities/{vid}` | GET | vuln:read |
| `/v1/tasks/{id}/vulnerabilities/{vid}` | PATCH | vuln:update |
| `/v1/tasks/{id}/pentest/start` | POST | pentest:trigger |
| `/v1/tasks/{id}/pentest/status` | GET | pentest:read |
| `/v1/tasks/{id}/reports` | POST | report:generate |
| `/v1/tasks/{id}/reports` | GET | report:read |
| `/v1/tasks/{id}/reports/{rid}` | GET | report:read |
| `/v1/tasks/{id}/reports/{rid}/download` | GET | report:download |
| `/v1/companies` | GET | company:read |
| `/v1/companies` | POST | company:create |
| `/v1/companies/{id}` | GET | company:read |
| `/v1/companies/{id}` | PATCH | company:update |
| `/v1/companies/{id}` | DELETE | company:delete |
| `/v1/knowledge/*` | GET | knowledge:read |
| `/v1/knowledge/*` | POST/PUT/DELETE | knowledge:write 或 knowledge:admin |
| `/v1/tools` | GET | tool:read |
| `/v1/tools/{id}/run` | POST | tool:execute |
| `/v1/templates/*` | GET | template:read |
| `/v1/templates/*` | POST/PUT/DELETE | template:write |
| `/v1/config/providers` | GET | system:config |
| `/v1/config/providers` | POST/PUT/DELETE | system:config |
| `/v1/config/webhooks` | GET/POST/PUT/DELETE | system:config |
| `/v1/config/agents` | GET | system:config |
| `/v1/config/agents` | PUT | system:config |
| `/v1/metrics` | GET | system:health |
| `/v1/admin/users` | GET/POST | system:admin |
| `/v1/admin/users/{id}` | PATCH/DELETE | system:admin |
| `/v1/admin/teams` | GET/POST | team:manage 或 system:admin |
| `/v1/admin/teams/{id}` | PATCH/DELETE | team:manage 或 system:admin |
| `/v1/admin/audit-logs` | GET | system:audit |

---

## 7. 用户管理 API 设计

### 7.1 用户管理端点（super_admin/org_admin）

```
# 用户 CRUD
GET    /v1/admin/users              → 用户列表（支持 org_id 过滤）
POST   /v1/admin/users              → 创建用户
GET    /v1/admin/users/{user_id}     → 用户详情
PATCH  /v1/admin/users/{user_id}     → 更新用户信息（display_name, is_active等）
DELETE /v1/admin/users/{user_id}     → 禁用用户（软删除）

# 用户自身信息
GET    /v1/auth/me                  → 当前用户信息+权限列表
PATCH  /v1/auth/me/password          → 修改自身密码

# Token 管理
POST   /v1/auth/refresh             → 刷新access_token
POST   /v1/auth/logout              → 吊销所有refresh_token
```

### 7.2 团队管理端点（team_lead/org_admin）

```
GET    /v1/admin/teams              → 团队列表
POST   /v1/admin/teams              → 创建团队
GET    /v1/admin/teams/{team_id}     → 团队详情（含成员列表）
PATCH  /v1/admin/teams/{team_id}     → 更新团队信息
DELETE /v1/admin/teams/{team_id}     → 删除团队

# 团队成员管理
POST   /v1/admin/teams/{team_id}/members     → 邀请成员
PATCH  /v1/admin/teams/{team_id}/members/{user_id}  → 修改成员角色
DELETE /v1/admin/teams/{team_id}/members/{user_id}  → 移除成员
```

### 7.3 审计日志端点

```
GET    /v1/admin/audit-logs         → 审计日志列表（支持时间范围、用户、操作过滤）
GET    /v1/admin/audit-logs/{id}     → 审计日志详情
```

---

## 8. 前端权限控制设计

### 8.1 路由守卫

```typescript
// router.tsx — 基于权限的路由配置

interface RouteConfig {
  path: string;
  component: React.ComponentType;
  permission?: string;       // 所需权限（如 "task:create"）
  roles?: string[];           // 允许的角色列表
}

const routes: RouteConfig[] = [
  { path: "/", component: Dashboard, permission: "task:read" },
  { path: "/tasks", component: TaskManagement, permission: "task:read" },
  { path: "/companies", component: Companies, permission: "company:read" },
  { path: "/assets", component: Assets, permission: "asset:read" },
  { path: "/vulnerabilities", component: Vulnerabilities, permission: "vuln:read" },
  { path: "/pentest", component: Pentest, permission: "pentest:read" },
  { path: "/reports", component: Reports, permission: "report:read" },
  { path: "/knowledge/*", component: KnowledgePages, permission: "knowledge:read" },
  { path: "/settings", component: Settings, permission: "system:config", roles: ["team_lead", "org_admin", "super_admin"] },
  { path: "/admin/users", component: UserManagement, permission: "system:admin" },
];
```

### 8.2 权限判断 Hook

```typescript
// hooks/usePermission.ts

import { useAuthStore } from '../store/authStore';

export function usePermission() {
  const { permissions, role, teams } = useAuthStore();

  const hasPermission = (action: string): boolean => {
    if (role === 'super_admin') return true;
    return permissions.includes(action);
  };

  const hasRole = (...roles: string[]): boolean => {
    if (role === 'super_admin') return true;
    return roles.includes(role);
  };

  const hasTeamRole = (teamId: string, requiredRole: string): boolean => {
    if (role === 'super_admin') return true;
    return teams[teamId]?.role === requiredRole || role === 'org_admin';
  };

  return { hasPermission, hasRole, hasTeamRole };
}
```

### 8.3 UI元素级权限控制

```tsx
// 示例：按钮权限控制
function TaskActions() {
  const { hasPermission } = usePermission();

  return (
    <Space>
      {hasPermission('task:create') && (
        <Button type="primary" onClick={handleCreate}>新建任务</Button>
      )}
      {hasPermission('task:execute') && (
        <Button onClick={handleStart}>启动</Button>
      )}
      {hasPermission('pentest:trigger') && (
        <Button danger onClick={handlePentest}>触发渗透</Button>
      )}
    </Space>
  );
}

// 示例：菜单权限控制
// Sidebar 中根据权限过滤可见菜单
const menuItems = allMenuItems.filter(item =>
  !item.permission || hasPermission(item.permission)
);
```

### 8.4 前端菜单权限映射

| 菜单项 | 所需权限 |
|-------|---------|
| 总览 | task:read |
| 任务管理 > 扫描任务 | task:read |
| 任务管理 > 任务编排 | orch:read |
| 任务管理 > 导入记录 | task:create |
| 任务管理 > 导出记录 | asset:export |
| 企业管理 | company:read |
| 资产管理 | asset:read |
| 漏洞管理 | vuln:read |
| 知识库管理（全部子菜单） | knowledge:read |
| 工具管理 | tool:read |
| 模板管理（全部子菜单） | template:read |
| 报告管理 | report:read |
| 系统设置 | system:config |
| 系统状态 | system:health |

---

## 9. 审计日志增强

### 9.1 现有审计中间件改造

当前 `src/api/middleware/audit.py` 记录请求日志但不含用户信息。改造要点：

```python
# 改造后的审计日志记录（在每个路由处理函数中）：
async def log_audit(
    db: AsyncSession,
    user: UserInfo,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    request: Request = None,
    response_status: int = 200,
):
    log = AuditLog(
        user_id=user.id,
        username=user.username,
        org_id=user.org_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=str(request.url.path) if request else None,
        status_code=response_status,
    )
    db.add(log)
```

### 9.2 需要审计的关键操作

| 操作 | action | resource_type | 描述 |
|-----|--------|--------------|------|
| 创建任务 | task:create | task | 创建新的扫描任务 |
| 删除任务 | task:delete | task | 删除任务及关联数据 |
| 创建演练 | orch:create | orchestration | 创建演练计划 |
| 启动演练 | orch:execute | orchestration | 启动/暂停/恢复/取消演练 |
| 生成演练报告 | orch:report | orchestration | 生成演练汇总报告 |
| 触发渗透 | pentest:trigger | task | 启动渗透测试 |
| HIL审批 | hil:resolve | task | 人工审批决策 |
| 确认漏洞 | vuln:confirm | vulnerability | 人工确认漏洞真实性 |
| 生成报告 | report:generate | report | 生成渗透测试报告 |
| 用户登录 | auth:login | user | 用户登录成功 |
| 用户登出 | auth:logout | user | 用户主动登出 |
| 修改角色 | role:update | team_member | 变更团队成员角色 |
| 邀请成员 | member:invite | team | 邀请新团队成员 |
| 移除成员 | member:remove | team | 移除团队成员 |
| 修改配置 | config:update | system | 修改系统配置 |

---

## 10. 安全注意事项

### 10.1 JWT 安全

- 生产环境必须更换 `JWT_SECRET_KEY`（当前默认值 `eakis-dev-secret-change-in-production`）
- Token 过期时间建议：access_token 60分钟，refresh_token 7天
- Token 不包含敏感信息（如密码、API Key）
- 前端存储在 `localStorage` 中（可考虑 `httpOnly cookie` 增强安全）

### 10.2 数据隔离

- **行级安全（RLS）**：PostgreSQL 可通过 Row Level Security 实现数据库级别的数据隔离
  ```sql
  ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

  CREATE POLICY tasks_team_isolation ON tasks
    USING (team_id IN (
      SELECT team_id FROM team_members WHERE user_id = current_setting('app.current_user_id')::UUID
    ));
  ```
- **应用层过滤**：所有查询API必须在WHERE条件中包含 `team_id` 过滤
- **org_admin 特殊处理**：可查询 `WHERE org_id = :user_org_id`（不限team_id）

### 10.3 防御措施

- 所有API端点添加认证依赖（移除当前无认证状态）
- CORS 配置收紧（生产环境不可用 `*`）
- 限流中间件增加按用户/角色维度
- 敏感操作（删除任务、触发渗透）添加二次确认
- 密码哈希使用 bcrypt（cost factor >= 12）

---

## 11. 迁移计划

### 11.1 数据库迁移步骤

1. **创建新表**：organizations, users, roles, permissions, role_permissions, teams, team_members, user_refresh_tokens, audit_logs
2. **填充种子数据**：6个角色 + 所有权限定义 + 角色-权限映射
3. **修改现有表**：tasks 增加 org_id, team_id, created_by_user_id
4. **创建默认组织和用户**：迁移脚本自动创建默认组织和admin用户
5. **数据迁移**：现有tasks的 created_by VARCHAR映射到user记录

### 11.2 后端代码迁移步骤

1. 新建ORM模型文件
2. 改造 `auth.py`：从硬编码用户改为数据库查询
3. 新建 `deps/permissions.py`：权限校验依赖
4. 所有路由添加认证和权限依赖
5. 新建用户/团队管理路由
6. 改造审计中间件

### 11.3 前端迁移步骤

1. 新建登录页和authStore
2. 改造API Client（JWT注入、401处理）
3. 新建 `usePermission` Hook
4. 添加路由守卫
5. 系统设置页增加用户/角色/权限管理Tab
6. 菜单权限过滤

---

## 12. 文件结构

### 12.1 后端新增文件

```
src/
├── api/
│   ├── auth.py                  # (修改) 认证改造
│   ├── deps/
│   │   ├── __init__.py
│   │   └── permissions.py       # (新建) 权限校验依赖
│   └── routers/
│       ├── users.py              # (新建) 用户管理API
│       ├── teams.py             # (新建) 团队管理API
│       └── orchestrations.py    # (新建) 任务编排/演练计划API
├── models/
│   ├── organization.py           # (新建)
│   ├── user.py                  # (新建)
│   ├── role.py                  # (新建) Role, Permission, RolePermission
│   ├── team.py                  # (新建) Team, TeamMember
│   ├── orchestration.py         # (新建) Orchestration, OrchestrationTask
│   ├── audit_log.py             # (新建)
│   ├── task.py                  # (修改) 增加org_id, team_id, created_by_user_id
│   └── vulnerability.py         # (修改) confirmed_by → FK
├── api/schemas/
│   ├── user.py                  # (新建) 用户请求/响应模型
│   ├── team.py                  # (新建) 团队请求/响应模型
│   └── orchestration.py         # (新建) 演练计划请求/响应模型
└── core/
    └── settings.py              # (修改) 增加RBAC相关配置
```

### 12.2 前端新增文件

```
web/src/
├── api/
│   ├── auth.ts                  # (新建) 登录/刷新/用户信息API
│   └── orchestrations.ts        # (新建) 演练计划/任务编排API
├── hooks/
│   └── usePermission.ts         # (新建) 权限判断Hook
├── store/
│   └── authStore.ts             # (新建) 认证状态管理
├── pages/
│   ├── Login/                   # (新建) 登录页
│   └── UserManagement/          # (新建) 用户管理页
├── components/
│   ├── AuthGuard/               # (新建) 路由守卫组件
│   └── PermissionGate/          # (新建) 元素级权限控制组件
└── router.tsx                   # (修改) 添加路由守卫
```

---

## 13. 后端开发进度

> 范围：仅后端 RBAC（Phase 0-8），不含前端改动

| Phase | 模块 | 状态 | 新增/修改文件 | 说明 |
|:-----:|------|:----:|---------------|------|
| 0 | 依赖 + 配置 | 已完成 | `pyproject.toml`, `src/core/settings.py` | 添加 `bcrypt` 依赖；Settings 新增 `refresh_token_expire_days`、`bcrypt_rounds`、`default_org_slug` |
| 1 | ORM 模型 | 已完成 | `src/models/organization.py` (新), `src/models/user.py` (新), `src/models/role.py` (新), `src/models/team.py` (新), `src/models/audit_log.py` (新), `src/models/task.py` (改), `src/models/__init__.py` (改) | 5 个新模型文件；Task 新增 `org_id`、`team_id`、`created_by_user_id` FK；修复 `AmbiguousForeignKeysError`（`TeamMember` 双 FK 到 `users`） |
| 2 | Pydantic Schemas | 已完成 | `src/api/schemas/user.py` (新), `src/api/schemas/team.py` (新), `src/api/schemas/audit_log.py` (新) | 用户/团队/审计日志的请求和响应模型 |
| 3 | 认证改造 | 已完成 | `src/api/auth.py` (改) | 移除硬编码用户；bcrypt 密码哈希；JWT 增加 RBAC claims（org_id, teams, permissions）；refresh token 轮换；新增 `/auth/me`、`/auth/logout`、`/auth/me/password` 端点；修复 async 环境下 lazy loading（`MissingGreenlet`）问题 |
| 4 | 权限校验 | 已完成 | `src/api/deps/__init__.py` (新), `src/api/deps/permissions.py` (新) | `PermissionAction` 枚举（45+ 操作）；`require_permission()`、`require_role()`、`require_resource_access()` 依赖工厂 |
| 5 | 管理路由 | 已完成 | `src/api/routers/users.py` (新), `src/api/routers/teams.py` (新), `src/api/routers/audit_logs.py` (新), `src/api/main.py` (改) | 用户 CRUD、团队 CRUD + 成员管理、审计日志查询；注册 3 个新路由到 app |
| 6 | 审计日志服务 | 已完成 | `src/api/services/__init__.py` (新), `src/api/services/audit_service.py` (新) | `write_audit_log()` 集中化审计日志写入函数 |
| 7 | 种子数据脚本 | 已完成 | `src/core/rbac_seed_data.py` (新), `scripts/seed_rbac.py` (新) | 6 个角色 + 45 个权限 + 角色-权限映射矩阵；幂等种子脚本（`--password` 可配） |
| 8 | 测试 | 已完成 | `tests/fixtures/rbac_fixtures.py` (新), `tests/unit/test_auth_utils.py` (新), `tests/unit/test_permissions.py` (新), `tests/integration/api/test_auth_api.py` (新), `tests/integration/api/test_users_api.py` (新), `tests/integration/api/test_teams_api.py` (新), `tests/integration/api/test_audit_logs_api.py` (新), `tests/conftest.py` (改) | 14 个单元测试全部通过；36 个集成测试全部通过；共 50 个 RBAC 测试用例 |

### 测试覆盖

| 测试类别 | 测试数 | 通过 | 文件 |
|---------|:------:|:----:|------|
| 单元：密码哈希 | 4 | 4 | `tests/unit/test_auth_utils.py` |
| 单元：JWT | 4 | 4 | `tests/unit/test_auth_utils.py` |
| 单元：权限校验 | 6 | 6 | `tests/unit/test_permissions.py` |
| 集成：登录 | 3 | 3 | `tests/integration/api/test_auth_api.py` |
| 集成：/auth/me | 3 | 3 | `tests/integration/api/test_auth_api.py` |
| 集成：refresh token | 2 | 2 | `tests/integration/api/test_auth_api.py` |
| 集成：logout | 1 | 1 | `tests/integration/api/test_auth_api.py` |
| 集成：修改密码 | 2 | 2 | `tests/integration/api/test_auth_api.py` |
| 集成：用户管理 | 6 | 6 | `tests/integration/api/test_users_api.py` |
| 集成：团队管理 | 8 | 8 | `tests/integration/api/test_teams_api.py` |
| 集成：审计日志 | 4 | 4 | `tests/integration/api/test_audit_logs_api.py` |
| **合计** | **50** | **50** | |

### 代码质量

| 检查项 | 结果 | 说明 |
|-------|:----:|------|
| ruff lint | 通过 | 0 error，0 warning |
| mypy | 部分 | `Column[T]` vs `T` 类型问题与项目已有代码模式一致（SQLAlchemy 在 mypy 中的已知限制） |
| 全量测试回归 | 无回归 | 334 unit passed，原有 integration passed（排除 2 个已有的 broken test 模块） |

### 待后续迭代

- [ ] 前端：登录页 + authStore + usePermission Hook + 路由守卫
- [ ] 前端：系统设置页增加用户/团队/权限管理 Tab
- [ ] 后端：现有路由端点逐一添加权限依赖（`require_permission`）
- [ ] 后端：Vulnerability.confirmed_by 改为 FK
- [ ] 后端：登录失败锁定机制（连续 5 次失败锁定 15 分钟）
- [ ] 后端：PostgreSQL RLS（行级安全）策略
- [ ] 后端：CORS 收紧为非 `*` 配置
