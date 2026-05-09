# AI 赋能攻击面探测系统 — 增量设计补充文档

**版本**：v2.1.0-supplement  
**基于**：EAKIS-1.md (v2.0.0)  
**状态**：草稿 / 内部评审  
**说明**：本文档为 v2.0.0 的增量补充，包含四个方向的新增内容：数据层架构变更、Human-in-the-Loop 详细设计、多租户权限体系、以及前端 UI/UX 规范。对原有方案有结构性影响的部分均以 `⚠️ 架构变更` 标注，便于针对性重构。

---

## 目录（增量部分）

17. [数据层架构补充](#17-数据层架构补充)
18. [Human-in-the-Loop 详细设计](#18-human-in-the-loop-详细设计)
19. [多租户与权限体系](#19-多租户与权限体系)
20. [成本模型与 API 消耗估算](#20-成本模型与-api-消耗估算)
21. [UI/UX 设计规范](#21-uiux-设计规范)
22. [攻击图谱模块（M7）](#22-攻击图谱模块m7)
23. [前端开发计划调整](#23-前端开发计划调整)

---

## 17. 数据层架构补充

### ⚠️ 架构变更：引入图数据支持

**变更原因**：v2.0.0 使用纯 PostgreSQL 关系模型，无法高效表达和查询"资产→接口→漏洞→攻击路径"的有向图结构。攻击路径分析（M7）要求对多跳关系进行遍历，关系数据库在此场景下性能和表达力均不足。

**变更方案**：在现有基础设施基础上，**新增 Apache AGE 扩展**（PostgreSQL 图扩展），复用现有 PostgreSQL 实例，无需引入独立图数据库服务，降低运维复杂度。

> **重构范围提示**：`第10章 数据模型设计` 需新增图模型 Schema；`第2章 2.3 核心技术栈` 需补充 Apache AGE 条目；`第15章 部署` 需更新 PostgreSQL 镜像为含 AGE 扩展的版本。

### 17.1 图数据模型设计

```sql
-- 启用 Apache AGE 扩展
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- 创建攻击图谱 Graph
SELECT create_graph('attack_graph');
```

**节点类型（Vertex）**：

```cypher
-- 资产节点
(:Asset {
  asset_id: "uuid",
  domain: "api.xx-payment.com",
  asset_type: "api",
  risk_level: "high",
  confirmed: true
})

-- 接口节点
(:Interface {
  interface_id: "uuid",
  path: "/api/v2/user/{userId}/orders",
  method: "GET",
  privilege_sensitive: true,
  test_priority: 9
})

-- 漏洞节点
(:Vulnerability {
  vuln_id: "uuid",
  vuln_type: "PRIVILEGE_ESCALATION",
  severity: "high",
  cvss_score: 8.1
})

-- 权限节点（Token/Session 等）
(:AuthToken {
  token_id: "uuid",
  token_type: "JWT",
  scope: "user",
  leaked: true
})

-- 云资产节点
(:CloudAsset {
  asset_id: "uuid",
  provider: "aliyun",
  resource_type: "OSS",
  ak_exposed: true
})
```

**边类型（Edge）**：

```cypher
-- 资产包含接口
(:Asset)-[:HAS_INTERFACE {crawl_method: "dynamic"}]->(:Interface)

-- 接口存在漏洞
(:Interface)-[:HAS_VULNERABILITY {confidence: 0.97}]->(:Vulnerability)

-- 漏洞导致权限泄露
(:Vulnerability)-[:LEADS_TO {step: 1}]->(:AuthToken)

-- 权限可访问资产
(:AuthToken)-[:CAN_ACCESS {privilege: "admin"}]->(:Asset)

-- 资产关联云资产
(:Asset)-[:EXPOSES_CLOUD_RESOURCE]->(:CloudAsset)

-- 攻击路径边（由 M7 生成）
(:Asset)-[:ATTACK_PATH {
  path_id: "uuid",
  step_order: 1,
  technique: "IDOR",
  confidence: 0.89
}]->(:Asset)
```

### 17.2 图查询示例

```python
# 查询从公网入口到云资产的完整攻击路径
ATTACK_PATH_QUERY = """
SELECT * FROM cypher('attack_graph', $$
  MATCH path = (entry:Asset {asset_type: "web"})-[*1..6]->(target:CloudAsset {ak_exposed: true})
  WHERE ALL(r IN relationships(path) WHERE r.confidence > 0.7)
  RETURN path, length(path) AS hop_count
  ORDER BY hop_count ASC
  LIMIT 10
$$) AS (path agtype, hop_count agtype);
"""

# 查询某资产的所有高危接口及关联漏洞
ASSET_VULN_GRAPH_QUERY = """
SELECT * FROM cypher('attack_graph', $$
  MATCH (a:Asset {asset_id: $asset_id})-[:HAS_INTERFACE]->(i:Interface)-[:HAS_VULNERABILITY]->(v:Vulnerability)
  WHERE v.severity IN ['critical', 'high']
  RETURN a.domain, i.path, i.method, v.vuln_type, v.cvss_score
  ORDER BY v.cvss_score DESC
$$) AS (domain agtype, path agtype, method agtype, vuln_type agtype, cvss_score agtype);
"""
```

### 17.3 图数据同步策略

图数据与 PostgreSQL 关系表双写，以关系表为主数据源，图数据库为查询加速层：

```python
class GraphSyncService:
    """
    触发时机：
    - Asset 确认 (confirmed=True)     → 写入/更新 Asset 节点
    - Interface 爬取完成              → 写入 Interface 节点 + HAS_INTERFACE 边
    - Vulnerability 经 LLM-Judge 确认 → 写入 Vulnerability 节点 + HAS_VULNERABILITY 边
    - M7 攻击路径生成完成             → 写入 ATTACK_PATH 边
    
    一致性保障：
    - 使用 Kafka 事件驱动异步写入，不阻塞主流程
    - 图写入失败不影响关系表主流程，记录重试队列
    - 每日全量对账（Reconciliation Job）
    """
    
    async def sync_vulnerability_confirmed(self, vuln: Vulnerability):
        # 写入漏洞节点
        await self.upsert_vertex('Vulnerability', vuln.id, {
            'vuln_id':   vuln.id,
            'vuln_type': vuln.vuln_type,
            'severity':  vuln.severity,
            'cvss_score': vuln.cvss_score
        })
        # 建立接口→漏洞边
        await self.create_edge(
            'HAS_VULNERABILITY',
            from_label='Interface', from_id=vuln.interface_id,
            to_label='Vulnerability', to_id=vuln.id,
            props={'confidence': vuln.llm_confidence}
        )
```

### 17.4 技术栈变更汇总

| 项目 | v2.0.0 | v2.1.0 |
|-----|--------|--------|
| 图数据 | 无 | Apache AGE（PostgreSQL 扩展） |
| PostgreSQL 镜像 | `postgres:16` | `apache/age:PG16` |
| 新增 Python 依赖 | - | `apache-age>=1.5.0` |

---

## 18. Human-in-the-Loop 详细设计

> **补充说明**：v2.0.0 中 Human-in-the-Loop 仅在架构图中出现，缺乏具体的节点定义、超时策略和 UI 交互设计，本章补全该部分。

### 18.1 必须人工干预的决策节点

系统中存在五类必须暂停等待人工确认的节点，不允许 AI 自动通过：

| 节点编号 | 所在模块 | 触发条件 | 风险说明 |
|---------|---------|---------|---------|
| HIL-01 | M3 资产发现 | 发现 ICP 备案主体与授权范围不完全匹配的资产 | 防止误测未授权资产 |
| HIL-02 | M3 资产发现 | 资产置信度在 0.60~0.75 区间（灰度区） | 低于阈值自动拒绝，高于自动确认，中间必须人工判断 |
| HIL-03 | M5 渗透测试 | 即将发起 `aggressive` 强度测试前 | 强度测试可能影响目标服务稳定性 |
| HIL-04 | M5 渗透测试 | LLM-as-Judge 判定为 critical 漏洞且置信度 > 0.90 | 高置信度高危漏洞，需人工二次核实再写入报告 |
| HIL-05 | M7 攻击路径 | 生成的攻击路径涉及云资产 AK/SK 泄露 | 敏感信息，需人工审核后才可纳入报告 |

### 18.2 HIL 状态机设计

```python
class HILStatus(str, Enum):
    PENDING  = "pending"   # 等待人工响应
    APPROVED = "approved"  # 人工批准，继续执行
    REJECTED = "rejected"  # 人工拒绝，跳过该步骤
    TIMEOUT  = "timeout"   # 超时，执行默认策略
    ESCALATED = "escalated" # 升级到更高权限用户

class HILCheckpoint:
    checkpoint_id: str
    task_id:       str
    node_code:     str          # HIL-01 ~ HIL-05
    context:       dict         # 供人工判断的上下文信息
    status:        HILStatus
    created_at:    datetime
    timeout_at:    datetime     # 超时时间
    resolved_at:   datetime | None
    resolved_by:   str | None
    resolution_note: str | None
    default_action: str         # 超时后的默认行为: "approve" | "reject" | "skip"
```

### 18.3 超时策略

```python
HIL_TIMEOUT_CONFIG = {
    "HIL-01": {
        "timeout_minutes":  30,
        "default_action":   "reject",   # 超时默认拒绝，保守策略
        "notify_channels":  ["webhook", "websocket"],
        "escalation_after": 20,         # 20分钟无响应升级通知
    },
    "HIL-02": {
        "timeout_minutes":  60,
        "default_action":   "reject",
        "notify_channels":  ["webhook", "websocket"],
        "escalation_after": 40,
    },
    "HIL-03": {
        "timeout_minutes":  120,        # 强度测试等待时间更长
        "default_action":   "reject",   # 超时绝不自动开始强度测试
        "notify_channels":  ["webhook", "websocket", "email"],
        "escalation_after": 60,
    },
    "HIL-04": {
        "timeout_minutes":  240,
        "default_action":   "approve",  # 漏洞确认超时默认收录，不漏报
        "notify_channels":  ["webhook", "websocket"],
        "escalation_after": 120,
    },
    "HIL-05": {
        "timeout_minutes":  60,
        "default_action":   "reject",   # AK/SK 相关超时默认不写报告
        "notify_channels":  ["webhook", "websocket", "email"],
        "escalation_after": 30,
    },
}
```

### 18.4 HIL API 补充

在原有 API 设计基础上新增以下端点：

```
GET  /v1/tasks/{task_id}/hil-checkpoints          # 获取任务所有待审节点
GET  /v1/hil-checkpoints?status=pending           # 获取当前用户所有待审节点（跨任务）
POST /v1/hil-checkpoints/{checkpoint_id}/resolve  # 人工决策
```

**决策请求体**：
```json
{
  "action":  "approved | rejected",
  "note":    "该资产 ICP 备案主体为集团子公司，确认纳入测试范围",
  "context_update": {
    "confirmed": true,
    "notes": "人工核实：集团子公司，已获授权"
  }
}
```

**WebSocket 推送**（HIL 触发时主动推送给前端）：
```json
{
  "event_type": "hil_checkpoint_created",
  "checkpoint_id": "hil_xxx",
  "node_code":     "HIL-01",
  "timeout_at":    "2024-01-01T10:30:00Z",
  "context": {
    "asset_domain":    "sub.unmatched-company.com",
    "icp_entity":      "未知备案主体有限公司",
    "confidence_score": 0.71,
    "reason":          "ICP 备案主体与授权范围不完全匹配"
  }
}
```

---

## 19. 多租户与权限体系

> **补充说明**：v2.0.0 中权限仅有"用户只能访问自己的任务"一句描述，缺乏完整的团队协作和角色设计，本章补全该部分。

### 19.1 租户与角色模型

```
Organization（组织/租户）
  │
  ├──< Team（团队）
  │       │
  │       ├──< TeamMember（成员，含角色）
  │       │
  │       └──< Task（任务，归属于 Team）
  │
  └──< User（用户，可属于多个 Team）
```

**角色定义**：

| 角色 | 英文标识 | 权限描述 |
|-----|---------|---------|
| 组织管理员 | `org_admin` | 管理成员、团队、计费、全局配置 |
| 团队负责人 | `team_lead` | 创建/删除任务、管理团队成员、审批 HIL |
| 执行工程师 | `engineer` | 创建任务、执行测试、查看全部数据、审批 HIL |
| 分析师 | `analyst` | 只读查看任务数据、资产、漏洞，不可触发测试 |
| 审计员 | `auditor` | 只读查看审计日志和报告，不可查看原始请求/响应 |

### 19.2 数据模型补充

```sql
-- 组织表
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,   -- URL 标识
    plan        VARCHAR(50) DEFAULT 'standard', -- standard|enterprise
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 用户表（补充 org 字段）
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    email           VARCHAR(300) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    display_name    VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 团队表
CREATE TABLE teams (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name    VARCHAR(200) NOT NULL,
    UNIQUE(org_id, name)
);

-- 团队成员与角色
CREATE TABLE team_members (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role    VARCHAR(50) NOT NULL,   -- team_lead|engineer|analyst|auditor
    PRIMARY KEY (team_id, user_id)
);

-- Task 表新增 team_id 字段（⚠️ 原 Task 表需增加此字段）
ALTER TABLE tasks ADD COLUMN team_id UUID REFERENCES teams(id);
ALTER TABLE tasks ADD COLUMN created_by_user_id UUID REFERENCES users(id);
```

> ⚠️ **重构提示**：`第10章 Task 表` 中的 `created_by VARCHAR(100)` 字段需替换为 `created_by_user_id UUID REFERENCES users(id)`，并新增 `team_id` 外键约束。所有涉及任务查询的 API 均需加入 `team_id` 过滤。

### 19.3 权限校验中间件

```python
class PermissionChecker:
    """
    API 层权限校验规则：
    
    资源访问：
    - 所有资源（Task/Asset/Vuln 等）通过 task_id → team_id 链路校验所属
    - 用户必须是该 task 所属 team 的成员，否则返回 403
    
    操作权限：
    - CREATE_TASK:      engineer, team_lead
    - DELETE_TASK:      team_lead
    - VIEW_RAW_TRAFFIC: engineer, team_lead（原始请求/响应体）
    - RESOLVE_HIL:      engineer, team_lead
    - MANAGE_MEMBERS:   team_lead, org_admin
    - VIEW_AUDIT_LOG:   auditor, org_admin, team_lead
    - TRIGGER_PENTEST:  engineer, team_lead（需额外 HIL-03 确认）
    """
    
    async def check(self, user: User, action: str, resource_id: str) -> bool:
        team_id = await self.resolve_team(resource_id)
        member  = await self.get_member(user.id, team_id)
        if not member:
            raise PermissionDenied("用户不属于该任务所在团队")
        return ROLE_PERMISSIONS[member.role].get(action, False)
```

### 19.4 API 鉴权补充

原 JWT 设计基础上补充 Payload 字段：

```json
{
  "sub":    "user_uuid",
  "org_id": "org_uuid",
  "teams":  ["team_uuid_1", "team_uuid_2"],
  "role_map": {
    "team_uuid_1": "engineer",
    "team_uuid_2": "analyst"
  },
  "exp": 1234567890
}
```

---

## 20. 成本模型与 API 消耗估算

> **补充说明**：v2.0.0 未涉及 LLM 调用成本估算，该部分对产品定价和商业可行性有直接影响。

### 20.1 单次完整任务 Token 消耗估算

基准假设：中型企业，约 200 个资产，1500 个接口，30 个漏洞（其中 5 个 critical）。

| 模块 | 使用模型 | 调用次数 | 平均 Token/次 | 小计 Token |
|-----|---------|---------|------------|-----------|
| M2 关键词提取 | Qwen-7B（本地） | ~15 次 | ~3,000 | 45,000 |
| M2 DSL 生成 | Qwen-7B（本地） | ~10 次 | ~2,000 | 20,000 |
| M3 资产评估 | Qwen-7B（本地） | ~200 次 | ~1,500 | 300,000 |
| M4 接口识别 | Qwen-7B（本地） | ~500 次 | ~2,000 | 1,000,000 |
| M5 测试用例生成 | GPT-4o（云端） | ~300 次 | ~3,000 | **900,000** |
| M5 LLM-as-Judge | GPT-4o（云端） | ~150 次 | ~4,000 | **600,000** |
| M6 报告生成 | GPT-4o（云端） | ~10 次 | ~8,000 | **80,000** |
| M6 报告质量评分 | Qwen-7B（本地） | ~5 次 | ~2,000 | 10,000 |

**GPT-4o 云端消耗合计**：约 1,580,000 tokens/任务

**按 GPT-4o 定价（input $2.5/1M, output $10/1M，混合估算约 $5/1M）**：

| 场景 | GPT-4o 成本 | 备注 |
|-----|------------|-----|
| 单次任务（中型企业） | **约 $7.9** | 基准场景 |
| 单次任务（大型企业，接口×3） | **约 $20** | 接口增至 4500 个 |
| 月均 50 个任务 | **约 $395~$1,000** | 视企业规模 |

### 20.2 成本控制建议

```python
COST_CONTROL_CONFIG = {
    # 缓存：相同接口特征命中缓存，不重复调用 LLM
    "llm_response_cache_ttl_hours": 24,
    "cache_similarity_threshold":   0.95,   # 向量相似度高于此值直接复用
    
    # 批处理：合并同类小请求
    "vuln_judge_batch_size":        10,     # 每批 10 个漏洞一起 Judge
    
    # 降级：非关键任务 GPT-4o → Qwen
    "fallback_to_local_if_cost_exceed_usd": 15,   # 单任务超过 $15 触发降级
    
    # 预算上限
    "max_cost_per_task_usd":        30,
    "daily_budget_usd":             200,
}
```

### 20.3 产品定价参考

| 定价层级 | 月均任务量 | 建议定价/月 | 毛利率参考 |
|---------|----------|-----------|---------|
| 基础版 | ≤10 个任务 | ¥5,000 | ~60% |
| 专业版 | ≤50 个任务 | ¥18,000 | ~65% |
| 企业版 | 不限 | 按需定制 | - |

---

## 21. UI/UX 设计规范

> **说明**：v2.0.0 未涉及 UI 设计。本章从零定义前端交互架构，与后续第23章前端开发计划配套。

### 21.1 整体设计理念

系统定位是**"攻击面情报作战平台"**，而非传统管理后台。核心设计原则：

**工作流驱动，非模块驱动**：用户的操作路径是"创建任务 → 查看情报流 → 审视资产图谱 → 定位攻击路径 → 核实漏洞 → 生成报告"，界面围绕这条工作流设计，而不是围绕 M1-M6 模块。

**信息分层展示**：避免信息爆炸，采用四层渐进式信息密度：
- L1：风险概览（数字、颜色、趋势）
- L2：资产/漏洞列表（结构化表格+图谱）
- L3：单资产/漏洞详情（接口树、原始流量）
- L4：原始 Payload 和 Evidence（加密存储，按需解密展示）

**AI 推理透明化**：每一个 AI 判断（资产确认、漏洞评级、攻击路径）都附有可展开的推理链，用户始终清楚"AI 为什么这么判断"。

### 21.2 视觉规范

#### 色彩规范

```css
:root {
  /* 背景层 */
  --bg-base:       #0B1020;   /* 最底层背景 */
  --bg-surface:    #111827;   /* 主面板背景 */
  --bg-elevated:   #1E293B;   /* 卡片/浮层背景 */
  --bg-overlay:    #263042;   /* 边框/分割线 */

  /* 主强调色 */
  --accent-primary: #5B8CFF;  /* 主交互色（按钮、链接、选中） */
  --accent-cyan:    #00E5A8;  /* 数据流/实时事件高亮 */
  --accent-purple:  #A78BFA;  /* AI 推理链高亮 */

  /* 风险等级色 */
  --risk-critical: #FF4D4F;
  --risk-high:     #F97316;
  --risk-medium:   #FAAD14;
  --risk-low:      #52C41A;
  --risk-info:     #38BDF8;

  /* 文字 */
  --text-primary:   #F1F5F9;
  --text-secondary: #94A3B8;
  --text-muted:     #475569;

  /* HIL 待审状态 */
  --hil-pending:   #F59E0B;   /* 琥珀色，醒目但不刺眼 */
}
```

#### 字体规范

```css
/* 主字体：界面文字 */
font-family: 'Inter', -apple-system, sans-serif;

/* 代码/数据字体：路径、IP、Payload、DSL */
font-family: 'JetBrains Mono', 'Fira Code', monospace;
```

#### 圆角与间距

```css
--radius-card:   12px;
--radius-dialog: 16px;
--radius-btn:    8px;
--radius-badge:  4px;

--spacing-base: 8px;   /* 基础单位，所有间距为 8 的倍数 */
```

#### 动效规范

| 场景 | 动效类型 | 时长 |
|-----|---------|-----|
| 页面切换 | Fade + SlideUp | 200ms |
| 卡片 Hover | Scale(1.01) + Shadow | 150ms |
| 图谱节点展开 | 平滑力导向 | 300ms |
| 实时事件流 | FadeIn from bottom | 200ms |
| HIL 弹窗出现 | Scale from center | 250ms |
| 数据刷新 | 数字滚动动画 | 500ms |

### 21.3 前端技术栈

| 模块 | 选型 | 说明 |
|-----|------|-----|
| 框架 | React 18 + TypeScript | 与 v2.0.0 一致 |
| 路由 | React Router v6 | - |
| 样式 | TailwindCSS | 替代 Ant Design Pro 默认样式，UI 从零定制 |
| 组件库 | shadcn/ui | 基于 Radix UI，深色主题友好，可高度定制 |
| 图谱 | React Flow + Cytoscape.js | React Flow 用于 Agent 编排图，Cytoscape 用于资产关系图 |
| 图表 | Apache ECharts | 与 v2.0.0 一致 |
| 动效 | Framer Motion | - |
| 状态管理 | Zustand | 轻量，替代 Redux |
| 数据请求 | TanStack Query | 缓存 + 实时更新 |
| 代码编辑器 | Monaco Editor | DSL 规则编辑、Payload 编写 |
| 终端模拟 | xterm.js | Agent 日志实时流 |
| 实时通信 | 原生 WebSocket（封装 hook） | 与后端 WS API 对接 |
| 虚拟列表 | TanStack Virtual | 接口列表（1000+ 条）性能保障 |

> ⚠️ **重构提示**：v2.0.0 技术栈中的 `React 18 + TypeScript + Ant Design Pro` 需调整为上表方案。Ant Design Pro 的 ProTable、ProForm 等组件不再使用，改为 shadcn/ui + 自定义组件。迁移成本：由于 UI 从零开发，不存在存量代码迁移问题。

### 21.4 信息架构（IA）

```
EAKIS 平台
│
├── 全局作战中心（首页 /dashboard）
│   ├── 攻击面态势概览（数字大盘）
│   ├── 资产关系图谱（全局视图）
│   ├── 实时事件流
│   └── HIL 待审队列（醒目展示）
│
├── 任务中心 /tasks
│   ├── 任务列表
│   ├── 新建任务
│   └── 任务详情 /tasks/:id
│       ├── 概览（进度 + 阶段状态）
│       ├── 情报流（M1 输出）
│       ├── 资产图谱（M3 输出）
│       ├── 接口分析（M4 输出）
│       ├── 漏洞列表（M5 输出）
│       ├── 攻击路径（M7 输出）
│       ├── Agent 编排视图（实时状态）
│       └── 报告（M6 输出）
│
├── 知识库 /knowledge
│   ├── RAG 情报片段
│   ├── DSL 规则库
│   └── Payload 库
│
├── 团队管理 /team
│   ├── 成员管理
│   ├── 角色配置
│   └── HIL 审批记录
│
└── 系统配置 /settings
    ├── Agent 配置
    ├── LLM 路由配置
    ├── Webhook 配置
    └── 成本监控
```

### 21.5 六大核心界面

#### 21.5.1 全局作战中心（首页）

```
┌──────────────────────────────────────────────────────────────────┐
│  EAKIS  [搜索/命令面板 ⌘K]              [HIL 待审 3] [用户]        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐            │
│  │ 活跃任务 │ 资产总数 │ 接口总数 │ 高危漏洞 │ 待审节点 │            │
│  │   3     │  2,847  │ 18,392  │   47    │   3 ⚠   │            │
│  └─────────┴─────────┴─────────┴─────────┴─────────┘            │
│                                                                  │
│  ┌─────────────────────────┬──────────────────────────────────┐  │
│  │  资产关系图谱（全局）      │  实时事件流                       │  │
│  │                         │                                  │  │
│  │  [Cytoscape.js 图谱]    │ ● [+] 发现新资产 admin.xx.com    │  │
│  │  节点：资产/漏洞/云资产   │ ▲ [!] HIL-01 待审：资产确认      │  │
│  │  边：接口/漏洞/攻击路径   │ ● [+] 接口爬取完成：1832个       │  │
│  │  点击节点→跳转详情        │ ▲ [!] 发现 critical 漏洞        │  │
│  │                         │ ● [+] DSL 优化完成               │  │
│  └─────────────────────────┴──────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  HIL 待审队列（需要人工干预）                               │    │
│  │  [HIL-01] api.xx.com 资产确认 — 超时剩余 22min  [审批]    │    │
│  │  [HIL-03] 强度测试授权确认 — 超时剩余 95min   [审批]       │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

#### 21.5.2 任务详情 — 资产图谱视图

资产图谱是任务详情页的核心视图，取代传统资产列表页：

- **图谱渲染**：Cytoscape.js，支持力导向布局 + 层次布局切换
- **节点着色**：按 `risk_level` 着色，critical=红，high=橙，medium=黄
- **节点大小**：按接口数量映射（接口越多节点越大）
- **边含义**：实线=直接关系，虚线=推断关系，红色边=攻击路径
- **交互**：点击节点展开右侧详情面板；框选多节点批量操作；双击进入接口分析视图
- **过滤器**：按资产类型、风险等级、ICP状态、技术栈过滤节点

#### 21.5.3 任务详情 — 接口分析视图

三栏布局，对标 Burp Suite 但 AI 化：

```
┌────────────┬──────────────────────────┬────────────────────────┐
│ 接口树      │ 请求/响应详情             │ AI 分析面板             │
│            │                          │                        │
│ ▼ 资产 A   │ GET /api/v2/user/        │ 风险评级：HIGH          │
│   ▼ /api   │ {userId}/orders          │ 置信度：97%             │
│     /v2    │                          │                        │
│     /user  │ Request:                 │ 风险点：                │
│       /{id}│ Authorization: Bearer    │ • userId 参数可被遍历   │
│         /o │ ...                      │ • 缺少当前用户校验      │
│            │                          │                        │
│ ▼ 资产 B   │ Response:                │ 推理链 ▼               │
│   ...      │ 200 OK                   │ 1. 检测到 path param   │
│            │ {"data": [...]}          │ 2. 参数类型为 integer  │
│ [过滤器]   │                          │ 3. 命中越权规则库      │
│ ■ 高优先级 │ [历史版本 v1 v2 v3]      │ 4. LLM Judge: 确认     │
│ ■ 权限敏感 │                          │                        │
│            │                          │ [触发测试] [标记误报]   │
└────────────┴──────────────────────────┴────────────────────────┘
```

#### 21.5.4 任务详情 — 攻击路径视图

展示 M7 生成的攻击路径图：

```
┌──────────────────────────────────────────────────────────────┐
│  攻击路径图谱                    [导出路径] [生成报告章节]        │
│                                                              │
│  www.xx-payment.com                                          │
│       │ IDOR → 登录接口                                       │
│       ▼                                                      │
│  api.xx-payment.com/auth/login  ──► JWT 令牌泄露              │
│       │ 持有 JWT                                              │
│       ▼                                                      │
│  admin.xx-payment.com  ──► 管理后台未鉴权访问                   │
│       │ 读取配置                                               │
│       ▼                                                      │
│  OSS AK/SK 暴露  ──────────────► ⚠ 云资产失陷风险              │
│                                                              │
│  路径置信度：89%   跳数：4   影响评级：CRITICAL                  │
│  [展开每步证据]  [标记为误报]  [创建修复工单]                     │
└──────────────────────────────────────────────────────────────┘
```

#### 21.5.5 Agent 编排视图

实时展示 Agent DAG 执行状态（React Flow）：

- 节点状态：待执行（灰）、执行中（蓝色脉冲动画）、完成（绿）、失败（红）、等待HIL（琥珀）
- 边上显示：Token 消耗、执行耗时
- 点击节点：展开该 Agent 的输入/输出和日志流（xterm.js）
- HIL 节点：暂停状态下显示审批弹窗入口

#### 21.5.6 HIL 审批弹窗

所有 HIL 审批操作通过统一弹窗完成，设计要点：

- 顶部显示：节点类型、剩余超时时间（倒计时）、超时默认行为
- 中部显示：完整上下文（资产信息、AI 推理链、相关证据）
- 底部：`批准继续` / `拒绝跳过` 两个主按钮 + 备注输入框
- 弹窗不可轻易关闭（需明确操作），背景遮罩更深

### 21.6 命令面板（Command Palette）

按 `⌘K` / `Ctrl+K` 唤起，支持以下命令：

```
新建任务 <企业名>
查看任务 <task_id 前缀>
搜索资产 <域名/IP>
搜索漏洞 <类型/严重程度>
审批 HIL <checkpoint_id>
查看攻击路径 <task_id>
导出报告 <task_id>
```

---

## 22. 攻击图谱模块（M7）

> **说明**：v2.0.0 共 6 个功能模块（M1-M6），本章新增 M7，为第二阶段（第13-24月）工作范围。

### 22.1 模块概述

**职责**：基于 M3 资产数据、M4 接口数据和 M5 漏洞数据，自动推理生成"攻击路径图"，量化攻击者从公网入口到核心资产的可行路径。

**输入**：已确认资产 + 已确认漏洞 + 接口权限关系  
**输出**：有向攻击路径图（存入图数据库）+ 攻击路径报告章节

**价值**：将系统从"漏洞扫描器"升级为"攻击面分析平台"，帮助企业理解"攻击者实际能做什么"而不只是"有哪些漏洞"。

### 22.2 攻击路径推理 Agent

```python
class AttackPathAgent:
    """
    推理策略：
    
    1. 入口识别
       - 公网暴露的 Web/API 资产
       - 无需认证的接口（auth_required=False）
       
    2. 路径延伸规则
       - 认证绕过漏洞 → 获得 Token → 访问更多接口
       - 越权漏洞 → 访问其他用户数据 → 横向移动
       - SSRF → 访问内网资产
       - 文件上传 → 代码执行 → 访问内网
       - 信息泄露（AK/SK）→ 云资产失陷
       
    3. 路径评分
       - 跳数（越少越危险）
       - 每步置信度（取最小值）
       - 最终影响资产价值（云资产 > 数据库 > 普通 API）
       
    4. HIL-05 触发条件
       - 路径终点为云资产且涉及 AK/SK
    """
    
    async def generate_paths(self, task_id: str) -> list[AttackPath]:
        # 从图数据库查询起点
        entries = await self.graph.query(ENTRY_POINT_QUERY, task_id=task_id)
        paths = []
        for entry in entries:
            # LLM 辅助路径推理
            candidate_paths = await self.llm_reason_paths(entry, task_id)
            for path in candidate_paths:
                scored = await self.score_path(path)
                paths.append(scored)
        return sorted(paths, key=lambda p: p.risk_score, reverse=True)
```

### 22.3 M7 数据模型补充

```sql
-- 攻击路径表（关系表，图数据以 Apache AGE 为主）
CREATE TABLE attack_paths (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    path_name       VARCHAR(300),                    -- 如"公网 → JWT 泄露 → 管理后台 → OSS"
    hop_count       INTEGER NOT NULL,
    risk_score      FLOAT CHECK (risk_score BETWEEN 0 AND 10),
    confidence      FLOAT CHECK (confidence BETWEEN 0 AND 1),
    entry_asset_id  UUID REFERENCES assets(id),
    target_asset_id UUID REFERENCES assets(id),
    steps           JSONB NOT NULL DEFAULT '[]',     -- 攻击步骤数组
    involves_cloud  BOOLEAN DEFAULT FALSE,
    hil_required    BOOLEAN DEFAULT FALSE,
    hil_approved    BOOLEAN,
    status          VARCHAR(50) DEFAULT 'draft',     -- draft|confirmed|false_positive
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attack_paths_task_id ON attack_paths(task_id);
CREATE INDEX idx_attack_paths_risk ON attack_paths(task_id, risk_score DESC);
```

### 22.4 Agent 编排流程更新

> ⚠️ **重构提示**：`第2章 2.2 Agent 编排流程图` 需在节点 10（报告输出 Agent）之前插入节点 M7 Attack Path Agent，形成 M5→M7→M6 的依赖关系。

```
（原流程）M5 自动渗透测试 Agent → M6 报告生成 Agent

（更新后）M5 自动渗透测试 Agent → M7 攻击路径分析 Agent → M6 报告生成 Agent
                                       │
                                   HIL-05（涉及云资产时）
```

---

## 23. 前端开发计划调整

> ⚠️ **重构提示**：v2.0.0 将前端开发排在第 19-21 个月，导致前 18 个月无可演示界面。本章将前端开发提前，采用"最小可用界面优先"策略。

### 23.1 调整原则

- **第 7-8 月**：交付最小可用前端（MVP），可演示任务创建、Agent 状态监控、基础资产列表
- **第 19-21 月**：完成完整 UI，包括图谱、攻击路径、HIL 审批、AI 推理链可视化

### 23.2 MVP 前端任务（第 7-9 月，替换原第 19-20 月部分任务）

| 月份 | 任务描述 | 工作量（人天） | 优先级 |
|-----|---------|------------|-------|
| 7 | 前端基础框架搭建（React + Tailwind + shadcn/ui + Zustand） | 5 | P0 |
| 7 | 设计系统搭建（色彩/字体/组件规范，含深色主题） | 4 | P0 |
| 7-8 | 任务创建与管理面板（创建/暂停/恢复/取消） | 8 | P0 |
| 8 | Agent 状态实时监控（WebSocket + 简版 DAG 视图） | 6 | P0 |
| 8 | HIL 审批弹窗（HIL-01 ~ HIL-05 通用弹窗） | 5 | P0 |
| 8-9 | 资产列表（基础表格，含风险着色） | 5 | P1 |
| 9 | 漏洞列表（含 LLM 置信度展示） | 5 | P1 |
| 9 | WebSocket 实时事件流（首页事件面板） | 4 | P1 |

### 23.3 完整前端任务（第 19-22 月，原计划延续 + 新增）

| 月份 | 任务描述 | 工作量（人天） |
|-----|---------|------------|
| 19 | 全局作战中心（首页大盘 + 全局图谱） | 10 |
| 19-20 | 资产图谱中心（Cytoscape.js，支持过滤/点击详情） | 12 |
| 20 | 接口分析三栏视图（接口树 + 请求详情 + AI 分析面板） | 10 |
| 20-21 | AI 推理链可视化（每个 AI 判断可展开决策树） | 8 |
| 21 | Agent 编排视图完整版（React Flow + xterm.js 日志） | 8 |
| 21 | 攻击路径图视图（M7 输出可视化） | 8 |
| 21-22 | 命令面板（⌘K，全局搜索 + 快捷操作） | 5 |
| 22 | 多视角切换（红队视图 / 管理层视图 / 分析师视图） | 6 |
| 22 | 成本监控看板（LLM 消耗、日预算进度） | 4 |

---

*增量文档版本：v2.1.0-supplement | 基于：EAKIS-1.md v2.0.0 | 保密级别：内部使用*
