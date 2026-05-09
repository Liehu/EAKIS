<<<<<<< HEAD

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
=======

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
>>>>>>> 62da9d74 (feat(core): implement asset discovery, RAG intelligence, and inference modules)
```