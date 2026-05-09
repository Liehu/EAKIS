
## 9. API 设计规范

### 9.1 总体规范

**基础 URL**：`https://api.attackscope.example.com/v1`  
**认证方式**：Bearer Token（JWT，24h 过期）  
**内容类型**：`application/json`  
**字符编码**：UTF-8  
**时间格式**：ISO 8601（`2024-01-01T00:00:00Z`）  

**错误响应格式**：
```json
{
  "error": {
    "code":    "TASK_NOT_FOUND",
    "message": "任务 ID xxx 不存在",
    "details": {},
    "request_id": "req_abc123",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

**分页格式**：
```json
{
  "data":  [],
  "pagination": {
    "page":       1,
    "page_size":  20,
    "total":      247,
    "total_pages":13
  }
}
```

### 9.2 任务管理 API

#### 创建探测任务

```
POST /v1/tasks
```

**请求体**：
```json
{
  "company_name":      "XX支付科技有限公司",
  "company_aliases":   ["XX支付", "XX Pay"],
  "industry":          "fintech",
  "authorized_scope": {
    "domains":   ["xx-payment.com", "xx-pay.cn"],
    "ip_ranges": ["203.x.x.0/24"],
    "exclude":   ["mail.xx-payment.com"]
  },
  "config": {
    "keyword_types":     ["business", "tech", "entity"],
    "asset_platforms":   ["fofa", "hunter"],
    "crawl_depth":       2,
    "pentest_enabled":   true,
    "pentest_intensity": "normal",
    "notification_webhook": "https://hook.example.com/xxx"
  }
}
```

**响应 201**：
```json
{
  "task_id":    "task_01J9XXXXX",
  "status":     "pending",
  "created_at": "2024-01-01T08:00:00Z",
  "estimated_duration_hours": 8,
  "stages": [
    {"stage": "intelligence",    "status": "pending"},
    {"stage": "keyword_gen",     "status": "pending"},
    {"stage": "asset_discovery", "status": "pending"},
    {"stage": "api_crawl",       "status": "pending"},
    {"stage": "pentest",         "status": "pending"},
    {"stage": "report_gen",      "status": "pending"}
  ]
}
```

#### 获取任务详情

```
GET /v1/tasks/{task_id}
```

**响应 200**：
```json
{
  "task_id":       "task_01J9XXXXX",
  "company_name":  "XX支付科技有限公司",
  "status":        "running",
  "current_stage": "api_crawl",
  "progress":      0.68,
  "stats": {
    "assets_found":       247,
    "assets_confirmed":   189,
    "interfaces_crawled": 1832,
    "vulns_detected":     43,
    "vulns_confirmed":    31
  },
  "stage_details": {
    "intelligence":    {"status": "completed", "duration_s": 180, "items": 1250},
    "keyword_gen":     {"status": "completed", "keywords": 113},
    "asset_discovery": {"status": "completed", "assets": 247, "confirmed": 189},
    "api_crawl":       {"status": "running",   "progress": 0.76, "interfaces": 1832},
    "pentest":         {"status": "pending"},
    "report_gen":      {"status": "pending"}
  },
  "created_at":   "2024-01-01T08:00:00Z",
  "started_at":   "2024-01-01T08:01:00Z",
  "estimated_completion": "2024-01-01T16:00:00Z"
}
```

#### 任务操作

```
POST /v1/tasks/{task_id}/pause      # 暂停
POST /v1/tasks/{task_id}/resume     # 恢复
POST /v1/tasks/{task_id}/cancel     # 取消
POST /v1/tasks/{task_id}/retry      # 重试失败阶段
```

#### 列出任务

```
GET /v1/tasks?status=running&page=1&page_size=20
```

#### 任务实时状态（WebSocket）

```
WS /v1/tasks/{task_id}/events
```

**推送事件格式**：
```json
{
  "event_type": "stage_progress | agent_log | vuln_found | task_complete | error",
  "timestamp":  "2024-01-01T08:30:00Z",
  "data": {
    "stage":    "api_crawl",
    "progress": 0.45,
    "message":  "已爬取 824/1832 个接口",
    "agent":    "APICRAWL-BROWSER"
  }
}
```

### 9.3 关键词 API

#### 获取任务关键词

```
GET /v1/tasks/{task_id}/keywords?type=business&min_weight=0.5
```

**响应 200**：
```json
{
  "data": [
    {
      "id":         "kw_xxx",
      "word":       "第三方支付",
      "type":       "business",
      "weight":     0.92,
      "confidence": 0.96,
      "source":     "新闻报道:36氪",
      "derived":    false,
      "used_in_dsl":true
    }
  ],
  "summary": {
    "business_count": 46,
    "tech_count":     29,
    "entity_count":   38,
    "total":          113
  },
  "pagination": {"page":1,"page_size":20,"total":113,"total_pages":6}
}
```

#### 手动添加关键词

```
POST /v1/tasks/{task_id}/keywords
```

```json
{
  "word":  "XX科技金融",
  "type":  "business",
  "weight": 0.85,
  "reason": "人工补充：企业子品牌"
}
```

#### 删除关键词

```
DELETE /v1/tasks/{task_id}/keywords/{keyword_id}
```

### 9.4 资产 API

#### 获取资产列表

```
GET /v1/tasks/{task_id}/assets?risk=high&confirmed=true&page=1&page_size=20
```

**查询参数**：

| 参数 | 类型 | 说明 |
|-----|------|-----|
| `risk` | string | `critical\|high\|medium\|low\|info` |
| `confirmed` | boolean | 是否已确认为靶标 |
| `asset_type` | string | `web\|api\|mobile\|infra` |
| `icp_verified` | boolean | ICP 备案是否验证 |
| `has_waf` | boolean | 是否有 WAF |
| `tech_stack` | string | 技术栈过滤（如 `spring`) |

**响应 200**：
```json
{
  "data": [{
    "id":             "asset_xxx",
    "domain":         "api.xx-payment.com",
    "ip_address":     "203.x.x.45",
    "asset_type":     "api",
    "confidence":     0.96,
    "risk_level":     "high",
    "icp_verified":   true,
    "waf_detected":   "Cloudflare",
    "tech_stack":     ["Spring Boot 2.7", "Nginx 1.24", "Redis"],
    "open_ports":     [80, 443, 8080],
    "cert_info": {
      "subject":      "api.xx-payment.com",
      "issuer":       "Let's Encrypt",
      "expires_at":   "2024-06-01"
    },
    "vuln_count": {
      "critical": 1, "high": 3, "medium": 5, "low": 2
    },
    "interface_count": 89,
    "discovered_at":  "2024-01-01T09:00:00Z"
  }],
  "pagination": {}
}
```

#### 获取资产详情

```
GET /v1/tasks/{task_id}/assets/{asset_id}
```

#### 更新资产状态

```
PATCH /v1/tasks/{task_id}/assets/{asset_id}
```

```json
{
  "confirmed":   true,
  "risk_level":  "critical",
  "notes":       "已确认为核心支付网关，高优先级"
}
```

#### 资产导出

```
GET /v1/tasks/{task_id}/assets/export?format=csv|xlsx|json
```

### 9.5 接口特征 API

#### 获取接口列表

```
GET /v1/tasks/{task_id}/interfaces?asset_id=xxx&type=operation&privilege_sensitive=true
```

**查询参数**：

| 参数 | 类型 | 说明 |
|-----|------|-----|
| `asset_id` | string | 过滤特定资产 |
| `type` | string | 接口类型过滤 |
| `privilege_sensitive` | boolean | 是否为权限敏感接口 |
| `auth_required` | boolean | 是否需要认证 |
| `min_priority` | integer | 最低测试优先级（1-10） |
| `method` | string | HTTP 方法过滤 |

**响应 200**：
```json
{
  "data": [{
    "id":                "iface_xxx",
    "asset_id":          "asset_xxx",
    "path":              "/api/v2/user/{userId}/orders",
    "method":            "GET",
    "api_type":          "query",
    "parameters": [{
      "name":            "userId",
      "location":        "path",
      "type":            "integer",
      "required":        true,
      "sensitive":       true
    }],
    "auth_required":     true,
    "privilege_sensitive":true,
    "sensitive_params":  ["userId"],
    "trigger_scenario":  "点击订单列表",
    "test_priority":     9,
    "crawl_method":      "dynamic",
    "vuln_tested":       true,
    "vuln_count":        2,
    "version":           1,
    "crawled_at":        "2024-01-01T10:00:00Z"
  }],
  "summary": {
    "total": 1832,
    "by_type": {"query":891,"operation":347,"upload":45,"search":120,"auth":89,"admin":67,"other":273},
    "privilege_sensitive": 312,
    "untested": 428
  },
  "pagination": {}
}
```

#### 获取接口详情

```
GET /v1/tasks/{task_id}/interfaces/{interface_id}
```

#### 手动标记接口

```
PATCH /v1/tasks/{task_id}/interfaces/{interface_id}
```

```json
{
  "test_priority": 10,
  "notes":         "疑似批量导出接口，高越权风险",
  "skip_test":     false
}
```

### 9.6 漏洞 API

#### 获取漏洞列表

```
GET /v1/tasks/{task_id}/vulnerabilities?severity=critical&confirmed=true
```

**查询参数**：

| 参数 | 类型 | 说明 |
|-----|------|-----|
| `severity` | string | `critical\|high\|medium\|low\|info` |
| `vuln_type` | string | 漏洞类型 |
| `confirmed` | boolean | 是否经 LLM-as-Judge 确认 |
| `false_positive_risk` | string | 误报风险等级 |
| `asset_id` | string | 特定资产的漏洞 |

**响应 200**：
```json
{
  "data": [{
    "id":              "vuln_xxx",
    "asset_id":        "asset_xxx",
    "interface_id":    "iface_xxx",
    "vuln_type":       "PRIVILEGE_ESCALATION",
    "severity":        "high",
    "cvss_score":      8.1,
    "title":           "订单查询接口存在水平越权",
    "description":     "攻击者可通过修改 userId 参数查看任意用户的订单信息",
    "affected_path":   "GET /api/v2/user/{userId}/orders",
    "test_payload":    "将 userId=1001 替换为 userId=9999",
    "evidence": {
      "request":       "GET /api/v2/user/9999/orders HTTP/1.1\nAuthorization: Bearer eyJ...(userId=1001的Token)",
      "response_code": 200,
      "response_snippet": "{\"data\":[{\"orderId\":\"2024xxxx\",\"userId\":9999,\"amount\":5000,...}]}"
    },
    "llm_confidence":  0.97,
    "false_positive_risk": "LOW",
    "remediation":     "服务端验证当前登录用户ID与请求参数userId是否一致，不一致时返回403",
    "status":          "confirmed",
    "confirmed_at":    null,
    "discovered_at":   "2024-01-01T14:00:00Z"
  }],
  "summary": {
    "total": 43,
    "by_severity": {"critical":5,"high":12,"medium":18,"low":8},
    "confirmed": 31,
    "false_positive_risk": {"HIGH":3,"MED":6,"LOW":34}
  },
  "pagination": {}
}
```

#### 获取漏洞详情

```
GET /v1/tasks/{task_id}/vulnerabilities/{vuln_id}
```

#### 更新漏洞状态

```
PATCH /v1/tasks/{task_id}/vulnerabilities/{vuln_id}
```

```json
{
  "status":         "confirmed|false_positive|fixed|wont_fix",
  "human_confirmed": true,
  "notes":          "已复现，确认为真实漏洞",
  "confirmed_by":   "security_engineer_01"
}
```

#### 漏洞统计

```
GET /v1/tasks/{task_id}/vulnerabilities/statistics
```

**响应 200**：
```json
{
  "by_severity":    {"critical":5,"high":12,"medium":18,"low":8},
  "by_type":        {"PRIVILEGE_ESC":8,"SQL_INJECTION":5,"UNAUTHORIZED":12,"XSS":6,"OTHER":12},
  "by_asset": [{
    "asset_id":     "asset_xxx",
    "domain":       "api.xx-payment.com",
    "vuln_count":   15,
    "max_severity": "critical"
  }],
  "trend":          [],
  "risk_score":     8.3,
  "confirmed_rate": 0.72
}
```

### 9.7 报告 API

#### 触发报告生成

```
POST /v1/tasks/{task_id}/reports
```

```json
{
  "format":     ["markdown", "pdf"],
  "sections":   ["summary", "assets", "interfaces", "vulns", "remediation"],
  "language":   "zh-CN",
  "template":   "standard|detailed|executive"
}
```

**响应 202**：
```json
{
  "report_job_id": "rjob_xxx",
  "status":        "generating",
  "estimated_minutes": 15
}
```

#### 获取报告状态

```
GET /v1/tasks/{task_id}/reports/{report_id}
```

**响应 200**：
```json
{
  "report_id":     "report_xxx",
  "status":        "completed",
  "quality_score": {
    "overall":      0.93,
    "accuracy":     0.96,
    "completeness": 0.91,
    "readability":  0.94,
    "actionability":0.89
  },
  "files": {
    "markdown": "https://storage.example.com/reports/xxx.md",
    "pdf":      "https://storage.example.com/reports/xxx.pdf"
  },
  "page_count":     47,
  "word_count":     8234,
  "generated_at":  "2024-01-01T16:00:00Z",
  "generation_duration_minutes": 18
}
```

#### 下载报告

```
GET /v1/tasks/{task_id}/reports/{report_id}/download?format=pdf
```

### 9.8 系统 API

#### 健康检查

```
GET /v1/health
```

```json
{
  "status":     "healthy",
  "version":    "v2.0.0",
  "timestamp":  "2024-01-01T00:00:00Z",
  "components": {
    "database":     {"status":"healthy","latency_ms":2},
    "redis":        {"status":"healthy","latency_ms":1},
    "qdrant":       {"status":"healthy","latency_ms":5},
    "kafka":        {"status":"healthy","lag":0},
    "llm_qwen":     {"status":"healthy","latency_ms":145},
    "llm_gpt4o":    {"status":"healthy","latency_ms":890},
    "playwright":   {"status":"healthy","pool_size":5}
  }
}
```

#### 系统指标

```
GET /v1/metrics
```

```json
{
  "active_tasks":          3,
  "queued_tasks":          7,
  "completed_tasks_today": 12,
  "avg_task_duration_h":   6.2,
  "llm_calls_today":       4821,
  "llm_cost_usd_today":    12.47,
  "assets_discovered_today": 1832,
  "vulns_confirmed_today":   127,
  "api_requests_per_min":    342
}
```

#### Agent 配置管理

```
GET  /v1/config/agents                    # 获取所有 Agent 配置
GET  /v1/config/agents/{agent_name}       # 获取单个 Agent 配置
PUT  /v1/config/agents/{agent_name}       # 更新 Agent 配置
POST /v1/config/agents/{agent_name}/test  # 测试 Agent 可用性
```

**更新 Agent 配置示例**：
```json
{
  "model":           "qwen2.5-7b",
  "temperature":     0.1,
  "max_tokens":      2048,
  "timeout_s":       30,
  "retry_attempts":  3,
  "enabled":         true
}
```

#### Webhook 通知

```
POST /v1/config/webhooks
```

```json
{
  "url":    "https://your-service.example.com/webhook",
  "events": ["task.complete", "vuln.critical_found", "task.failed"],
  "secret": "hmac_secret_for_verification"
}
```

**Webhook 推送格式**：
```json
{
  "event":      "vuln.critical_found",
  "task_id":    "task_xxx",
  "timestamp":  "2024-01-01T14:00:00Z",
  "data": {
    "vuln_id":  "vuln_xxx",
    "severity": "critical",
    "title":    "核心支付接口存在SQL注入",
    "asset":    "api.xx-payment.com"
  },
  "signature":  "sha256=xxxx"
}
```