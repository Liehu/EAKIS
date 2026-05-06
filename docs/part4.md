
---

## 10. 数据模型设计

### 10.1 实体关系图

```
Task (探测任务)
  │
  ├──< Keyword (关键词)
  │
  ├──< Asset (靶标资产)
  │       │
  │       ├──< ApiInterface (接口特征)
  │       │         │
  │       │         └──< TestCase (测试用例)
  │       │                   │
  │       │                   └──< Vulnerability (漏洞)
  │       │
  │       └──< AssetEnrichment (资产增强信息)
  │
  ├──< IntelDocument (情报文档)
  │
  ├──< AgentLog (Agent 日志)
  │
  └──< Report (报告)
```

### 10.2 完整数据模型

#### Task 表

```sql
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name    VARCHAR(200) NOT NULL,
    company_aliases TEXT[],                          -- 企业别名
    industry        VARCHAR(50),                     -- 行业类型
    status          task_status NOT NULL DEFAULT 'pending',
    current_stage   VARCHAR(50),
    progress        FLOAT DEFAULT 0 CHECK (progress BETWEEN 0 AND 1),
    authorized_scope JSONB NOT NULL,                 -- 授权测试范围（不可为空）
    config          JSONB DEFAULT '{}',              -- 任务配置
    error_message   TEXT,                            -- 失败原因
    retry_count     INTEGER DEFAULT 0,
    created_by      VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

CREATE TYPE task_status AS ENUM (
    'pending', 'running', 'paused', 'completed', 'failed', 'cancelled'
);

-- 索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
```

#### Keyword 表

```sql
CREATE TABLE keywords (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    word        VARCHAR(200) NOT NULL,
    type        keyword_type NOT NULL,               -- business|tech|entity
    weight      FLOAT NOT NULL CHECK (weight BETWEEN 0 AND 1),
    confidence  FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source      TEXT,                                -- 情报来源
    source_idx  INTEGER,                             -- 来源句子索引
    derived     BOOLEAN DEFAULT FALSE,               -- 是否为扩充词
    parent_id   UUID REFERENCES keywords(id),        -- 来源关键词
    used_in_dsl BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE keyword_type AS ENUM ('business', 'tech', 'entity');
CREATE INDEX idx_keywords_task_id ON keywords(task_id);
CREATE INDEX idx_keywords_type ON keywords(task_id, type);
```

#### Asset 表

```sql
CREATE TABLE assets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id          UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    domain           VARCHAR(500),
    ip_address       INET,
    port             INTEGER,
    protocol         VARCHAR(10) DEFAULT 'https',
    asset_type       VARCHAR(50),                    -- web|api|mobile|infra
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    icp_verified     BOOLEAN DEFAULT FALSE,
    icp_entity       VARCHAR(500),                   -- ICP 备案主体
    tech_stack       JSONB DEFAULT '[]',             -- 技术栈列表
    response_headers JSONB DEFAULT '{}',
    page_keywords    TEXT[],
    waf_type         VARCHAR(100),                   -- WAF 类型（如有）
    cert_info        JSONB,                          -- TLS 证书信息
    screenshot_path  TEXT,                           -- 截图存储路径
    open_ports       INTEGER[],
    risk_level       risk_level DEFAULT 'info',
    confirmed        BOOLEAN DEFAULT FALSE,          -- 人工确认
    notes            TEXT,
    feature_vector_id TEXT,                          -- Qdrant 向量 ID
    discovered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 确保同一任务下不重复
    UNIQUE(task_id, domain, port),
    UNIQUE(task_id, ip_address, port)
);

CREATE TYPE risk_level AS ENUM ('critical', 'high', 'medium', 'low', 'info');
CREATE INDEX idx_assets_task_id ON assets(task_id);
CREATE INDEX idx_assets_risk ON assets(task_id, risk_level);
CREATE INDEX idx_assets_confirmed ON assets(task_id, confirmed);
```

#### ApiInterface 表

```sql
CREATE TABLE api_interfaces (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id             UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    task_id              UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    path                 TEXT NOT NULL,
    path_pattern         TEXT,                       -- 统一化路径（:id 占位符）
    method               VARCHAR(10) NOT NULL,
    api_type             VARCHAR(50),                -- query|operation|upload|search|auth|admin...
    parameters           JSONB DEFAULT '[]',
    request_headers      JSONB DEFAULT '{}',
    response_schema      JSONB DEFAULT '{}',
    auth_required        BOOLEAN DEFAULT TRUE,
    privilege_sensitive  BOOLEAN DEFAULT FALSE,
    sensitive_params     TEXT[],                     -- 权限敏感参数名列表
    trigger_scenario     TEXT,
    crawl_method         VARCHAR(20),                -- static|dynamic|cdp
    test_priority        INTEGER DEFAULT 5 CHECK (test_priority BETWEEN 1 AND 10),
    skip_test            BOOLEAN DEFAULT FALSE,
    notes                TEXT,
    feature_embedding_id TEXT,                       -- Qdrant 向量 ID
    version              INTEGER DEFAULT 1,
    checksum             VARCHAR(64),                -- 接口指纹（检测变更）
    crawled_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interfaces_asset_id ON api_interfaces(asset_id);
CREATE INDEX idx_interfaces_task_id ON api_interfaces(task_id);
CREATE INDEX idx_interfaces_type ON api_interfaces(task_id, api_type);
CREATE INDEX idx_interfaces_priority ON api_interfaces(task_id, test_priority DESC);
CREATE INDEX idx_interfaces_privilege ON api_interfaces(task_id, privilege_sensitive);
```

#### Vulnerability 表

```sql
CREATE TABLE vulnerabilities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES assets(id),
    interface_id        UUID REFERENCES api_interfaces(id),
    vuln_type           VARCHAR(50) NOT NULL,
    severity            risk_level NOT NULL,
    cvss_score          FLOAT CHECK (cvss_score BETWEEN 0 AND 10),
    title               VARCHAR(300) NOT NULL,
    description         TEXT,
    affected_path       TEXT,
    test_payload        TEXT,
    test_case_id        UUID,
    evidence            JSONB NOT NULL DEFAULT '{}', -- {request, response_code, response_snippet, screenshot}
    llm_confidence      FLOAT CHECK (llm_confidence BETWEEN 0 AND 1),
    false_positive_risk VARCHAR(10),                 -- HIGH|MED|LOW
    false_positive_reason TEXT,
    remediation         TEXT,
    status              vuln_status DEFAULT 'detected',
    human_confirmed     BOOLEAN DEFAULT FALSE,
    confirmed_by        VARCHAR(100),
    confirmed_at        TIMESTAMPTZ,
    notes               TEXT,
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE vuln_status AS ENUM (
    'detected', 'confirmed', 'false_positive', 'fixed', 'wont_fix', 'pending_review'
);

CREATE INDEX idx_vulns_task_id ON vulnerabilities(task_id);
CREATE INDEX idx_vulns_severity ON vulnerabilities(task_id, severity);
CREATE INDEX idx_vulns_status ON vulnerabilities(task_id, status);
CREATE INDEX idx_vulns_asset_id ON vulnerabilities(asset_id);
```

#### IntelDocument 表

```sql
CREATE TABLE intel_documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    source_type   VARCHAR(50),                       -- news|official|legal|asset_engine
    source_name   VARCHAR(200),                      -- 具体来源名称
    source_url    TEXT,
    content       TEXT NOT NULL,                     -- 清洗后正文
    quality_score FLOAT,
    published_at  TIMESTAMPTZ,
    entities      TEXT[],                            -- 预识别实体
    checksum      VARCHAR(64) UNIQUE,                -- MD5 去重
    rag_indexed   BOOLEAN DEFAULT FALSE,             -- 是否已写入 RAG
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_intel_task_id ON intel_documents(task_id);
CREATE INDEX idx_intel_quality ON intel_documents(task_id, quality_score DESC);
```

#### Report 表

```sql
CREATE TABLE reports (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id              UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status               report_status DEFAULT 'generating',
    template             VARCHAR(50) DEFAULT 'standard',
    language             VARCHAR(10) DEFAULT 'zh-CN',
    markdown_path        TEXT,                       -- 对象存储路径
    pdf_path             TEXT,
    page_count           INTEGER,
    word_count           INTEGER,
    quality_score        JSONB DEFAULT '{}',         -- {overall, accuracy, completeness, readability, actionability}
    generation_duration_s INTEGER,
    error_message        TEXT,
    generated_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE report_status AS ENUM ('generating', 'completed', 'failed');
```

#### AgentLog 表

```sql
CREATE TABLE agent_logs (
    id         BIGSERIAL PRIMARY KEY,
    task_id    UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    level      VARCHAR(10) NOT NULL,                 -- INFO|WARN|ERROR|DEBUG
    message    TEXT NOT NULL,
    context    JSONB DEFAULT '{}',                   -- 结构化上下文数据
    trace_id   VARCHAR(64),                          -- OpenTelemetry Trace ID
    span_id    VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 按时间分区（每月一个分区）
PARTITION BY RANGE (created_at);
CREATE INDEX idx_agent_logs_task ON agent_logs(task_id, created_at DESC);
CREATE INDEX idx_agent_logs_level ON agent_logs(task_id, level);
```

### 10.3 Qdrant 集合设计

```python
# 接口特征向量集合
API_INTERFACE_COLLECTION = {
    "name": "api_interface_features",
    "vectors_config": {
        "size": 384,              # all-MiniLM-L6-v2 维度
        "distance": "Cosine",
    },
    "payload_schema": {
        "task_id":    "keyword",
        "asset_id":   "keyword",
        "api_type":   "keyword",
        "method":     "keyword",
        "crawled_at": "datetime",
    }
}

# 资产特征向量集合
ASSET_FEATURE_COLLECTION = {
    "name": "target_asset_features",
    "vectors_config": {
        "size": 768,              # text-embedding-3-small 维度
        "distance": "Cosine",
    },
    "payload_schema": {
        "task_id":    "keyword",
        "asset_type": "keyword",
        "confidence": "float",
        "icp_verified": "bool",
    }
}

# RAG 知识库集合
RAG_KNOWLEDGE_COLLECTION = {
    "name": "osint_rag_knowledge",
    "vectors_config": {
        "size": 768,
        "distance": "Cosine",
    },
    "payload_schema": {
        "task_id":    "keyword",
        "source_type":"keyword",
        "quality":    "float",
        "indexed_at": "datetime",
    }
}
```

---

## 11. 核心提示词设计

### 11.1 提示词工程原则

1. **结构化输出**：所有提示词强制要求 JSON 输出，禁止自由文本
2. **角色专化**：每个 Agent 有独立的系统角色定义，避免任务混淆
3. **边界约束**：明确声明不允许的行为（越界测试/数据泄露等）
4. **置信度强制**：要求附带置信度分数，便于阈值过滤
5. **Few-Shot 示例**：每个提示词包含 2-3 个标准输入输出示例
6. **版本管理**：提示词存储于 `docs/prompts/` 目录，按版本管理

### 11.2 关键词提取提示词

**文件**：`docs/prompts/keyword_extraction_v2.yaml`

```yaml
system: |
  你是网络安全情报分析专家，专精从开源情报中提取攻击面探测关键词。
  
  任务：分析输入的企业情报文本，提取三类关键词。
  
  【分类定义】
  - business_keywords：主营业务/产品名称/服务类型/行业标签
  - tech_keywords：技术框架/数据库/中间件/协议/部署工具
  - entity_keywords：子公司/合作伙伴/投资方/供应商名称
  
  【输出规则 - 严格执行】
  1. 只输出合法 JSON，不允许任何多余文字或代码块标记
  2. 每类最多 20 个关键词，按 confidence 降序排列
  3. 每个关键词必须附 confidence(0.0~1.0) 和 source_idx（来源句子索引）
  4. 过滤通用词：公司/系统/平台/管理/服务/技术（confidence < 0.3 的不输出）
  5. 关键词长度：2~15 个汉字 或 2~30 个英文字符
  
  【Few-Shot 示例】
  输入：「XX银行近期上线基于微服务架构的新核心系统，采用Spring Boot和K8s部署，
        与国际清算组织合作开展SWIFT跨境支付项目。」
  输出：{
    "business_keywords": [
      {"word":"核心系统","confidence":0.91,"source_idx":0},
      {"word":"跨境支付","confidence":0.95,"source_idx":0}
    ],
    "tech_keywords": [
      {"word":"Spring Boot","confidence":0.99,"source_idx":0},
      {"word":"Kubernetes","confidence":0.99,"source_idx":0},
      {"word":"微服务","confidence":0.90,"source_idx":0},
      {"word":"SWIFT","confidence":0.97,"source_idx":0}
    ],
    "entity_keywords": [
      {"word":"国际清算组织","confidence":0.96,"source_idx":0}
    ]
  }

user: |
  情报来源类型: {source_type}
  靶标企业: {company_name}
  情报文本:
  {text_content}
  
  请严格按照系统提示的格式输出 JSON，不要添加任何解释文字：
```

### 11.3 资产相关性评估提示词

**文件**：`docs/prompts/asset_assessment_v2.yaml`

```yaml
system: |
  你是资产归属判定专家。根据靶标基准特征，判断每个待检资产是否归属该靶标企业。
  
  【判定规则（优先级从高到低）】
  P1. ICP 备案主体与靶标精确匹配 → confidence ≥ 0.97
  P2. 域名为已知主域名的合法子域 → confidence ≥ 0.88
  P3. IP 在靶标已知网段内 + 至少1项其他特征 → confidence ≥ 0.85
  P4. 页面包含靶标特有关键词 + 域名关联 → confidence ≥ 0.75
  P5. 仅单一弱特征匹配 → confidence < 0.65（判定为非靶标）
  
  【特殊情况处理】
  - CDN 节点（Cloudflare/Akamai IP）：不能仅凭 IP 判定，需结合域名
  - 通用域名（如 github.io）：需要至少3个其他特征才能判定
  - 境外资产无 ICP：依赖 DNS/证书/页面特征综合判定

user: |
  靶标基准特征:
    企业名称: {company_name}
    ICP备案主体列表: {icp_entities}
    已知根域名: {root_domains}
    已知IP段: {ip_ranges}
    特征关键词: {signature_keywords}
  
  待判定资产:
    域名: {asset_domain}
    IP: {asset_ip}
    端口: {asset_port}
    HTTP响应头: {asset_headers}
    页面标题: {page_title}
    页面关键词: {page_keywords}
    ICP主体: {asset_icp}
    证书主体: {cert_subject}
  
  输出 JSON（只输出 JSON，不加任何说明）:
  {
    "is_target": true/false,
    "confidence": 0.0~1.0,
    "matched_rules": ["P1","P2"],
    "reason": "简短判定理由（50字以内）",
    "uncertainty_factors": "不确定性说明（如有）"
  }
```

### 11.4 接口爬取操控提示词

**文件**：`docs/prompts/browser_control_v2.yaml`

```yaml
system: |
  你是前端逆向分析专家，精通 Vue/React/Angular/jQuery 等主流框架的请求模式。
  
  任务：分析当前页面，生成操作序列以全面触发 API 接口。
  
  【操作优先级排序】
  1. 登录/注册表单（最高优先级，捕获认证接口）
  2. 搜索框/查询表单
  3. 增删改操作按钮（高越权风险）
  4. 文件上传控件
  5. 分页、Tab 切换、下拉菜单（懒加载接口）
  6. 模态框/抽屉触发按钮
  
  【约束】
  - 不触发「删除/清空/提交」等破坏性操作
  - 不提交真实个人信息（用测试账号和测试数据）
  - 已在 already_captured 中的接口前缀不重复触发
  
  【输出格式】
  {
    "actions": [
      {
        "step": 1,
        "element_type": "button|input|select|form|link",
        "selector": "精确的CSS选择器或XPath",
        "action": "click|fill|select|hover|scroll_to",
        "fill_value": "填入值（仅fill操作）",
        "wait_after_ms": 1000,
        "expected_api_pattern": "/api/xxx（可能触发的接口路径前缀）",
        "expected_api_type": "auth|query|operation|upload|search",
        "priority": 1~10,
        "note": "操作说明"
      }
    ],
    "page_analysis": {
      "framework": "Vue3|React|Angular|jQuery|unknown",
      "auth_state": "logged_in|logged_out|unknown",
      "page_type": "login|list|detail|form|dashboard"
    }
  }

user: |
  目标URL: {page_url}
  已捕获接口列表（避免重复）: {already_captured}
  页面DOM摘要（关键元素）:
  {dom_summary}
  [页面截图已附上]
```

### 11.5 漏洞测试用例生成提示词

**文件**：`docs/prompts/vuln_case_gen_v2.yaml`

```yaml
system: |
  你是渗透测试用例设计专家。根据接口特征，生成精准、有针对性的安全测试用例。
  
  【安全声明 - 严格遵守】
  只为已授权范围内的资产生成测试用例。严禁生成对第三方系统的攻击代码。
  
  【用例生成原则】
  1. 最小化原则：用例只修改必要的参数，保持其他参数为合法值
  2. 可复现性：每个用例提供完整的 curl 命令或请求体
  3. 无破坏性：不触发真实的数据删除、账号封禁等操作
  4. 差异化：同类漏洞的多个用例要覆盖不同的绕过思路
  
  【参数替换策略】
  - 越权测试：将 userId/id 替换为明显属于他人的值（如原值+1000）
  - SQL注入：在字符串参数末尾附加 Payload，不替换原值
  - 未授权：完整保留原请求，仅移除 Authorization 头

user: |
  接口信息:
    路径: {path}
    方法: {method}
    类型: {api_type}
    参数: {parameters_json}
    当前认证Token: {token_example}
    权限敏感参数: {sensitive_params}
    触发场景: {trigger}
  
  漏洞类型: {vuln_type}
  相关Payload: {payloads}
  
  生成 3~5 个测试用例（JSON数组，不加任何说明）:
  [
    {
      "case_id": "唯一短ID",
      "description": "测试说明（中文，40字以内）",
      "vuln_type": "{vuln_type}",
      "modified_request": {
        "method": "GET|POST|...",
        "path": "修改后的路径（如有路径参数替换）",
        "headers": {"Authorization": "Bearer xxx"},
        "query_params": {},
        "body": {}
      },
      "curl_command": "完整的 curl 命令",
      "expected_indicator": "触发漏洞时响应的关键特征",
      "false_positive_risk": "HIGH|MED|LOW",
      "priority": 1~10
    }
  ]
```

---

## 12. 目录结构

```
attackscope-ai/
├── README.md
├── CHANGELOG.md
├── docker-compose.yml           # 本地开发环境
├── docker-compose.prod.yml      # 生产环境
├── docker-compose.test.yml      # 测试环境
├── Makefile
├── pyproject.toml               # Poetry 项目配置
├── alembic.ini
├── .env.example
├── .pre-commit-config.yaml      # 代码质量钩子
│
├── docs/
│   ├── architecture.md
│   ├── api-spec.yaml            # OpenAPI 3.0 完整规范
│   ├── deployment.md
│   ├── prompts/                 # 提示词版本管理
│   │   ├── keyword_extraction_v1.yaml
│   │   ├── keyword_extraction_v2.yaml
│   │   ├── asset_assessment_v1.yaml
│   │   ├── asset_assessment_v2.yaml
│   │   ├── browser_control_v1.yaml
│   │   ├── browser_control_v2.yaml
│   │   ├── vuln_case_gen_v1.yaml
│   │   ├── vuln_case_gen_v2.yaml
│   │   ├── llm_judge_vuln_v1.yaml
│   │   └── report_gen_v1.yaml
│   └── runbooks/                # 运维手册
│       ├── incident_response.md
│       ├── scaling.md
│       └── backup_restore.md
│
├── src/
│   ├── orchestrator/            # Agent 编排层（LangGraph）
│   │   ├── __init__.py
│   │   ├── graph.py             # 主工作流图定义
│   │   ├── state.py             # GlobalState TypedDict 定义
│   │   ├── router.py            # 条件路由（阈值判断/错误处理）
│   │   ├── checkpointer.py      # 状态持久化（PostgreSQL）
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── base.py          # Agent 基类（日志/监控/重试）
│   │       ├── datasource.py    # OSINT-DATASOURCE Agent
│   │       ├── dsl_gen.py       # OSINT-DSL Agent
│   │       ├── crawler.py       # OSINT-CRAWLER Agent
│   │       ├── cleaner.py       # OSINT-CLEANER Agent
│   │       ├── summarizer.py    # KW-SUMMARIZER Agent
│   │       ├── keyword_gen.py   # KW-GENERATOR Agent
│   │       ├── asset_search.py  # ASSET-SEARCH Agent
│   │       ├── asset_assess.py  # ASSET-ASSESSOR Agent
│   │       ├── asset_enrich.py  # ASSET-ENRICHER Agent
│   │       ├── api_crawler.py   # APICRAWL-BROWSER Agent
│   │       ├── api_static.py    # APICRAWL-STATIC Agent
│   │       ├── test_gen.py      # PENTEST-CASEGEN Agent
│   │       ├── test_exec.py     # PENTEST-EXECUTOR Agent
│   │       ├── vuln_judge.py    # PENTEST-JUDGE Agent
│   │       └── report_gen.py    # REPORT-GEN Agent
│   │
│   ├── intelligence/            # M1 情报采集
│   │   ├── __init__.py
│   │   ├── module.py            # 模块入口
│   │   ├── scrapers/
│   │   │   ├── base.py          # 爬虫基类（重试/限速）
│   │   │   ├── news.py          # 新闻/招投标爬虫
│   │   │   ├── official.py      # 企业官网爬虫
│   │   │   └── icp.py           # ICP 备案查询
│   │   ├── engines/
│   │   │   ├── fofa.py
│   │   │   ├── hunter.py
│   │   │   ├── shodan.py
│   │   │   └── censys.py
│   │   └── anti_crawl/
│   │       ├── proxy_pool.py    # 代理池管理（Redis 存储）
│   │       ├── ua_pool.py       # UA 池
│   │       └── fingerprint.py   # 浏览器指纹伪装
│   │
│   ├── keywords/                # M2 关键词引擎
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── extractor.py         # LLM 三类关键词提取
│   │   ├── ranker.py            # 权重计算（TF-IDF + 领域词库）
│   │   ├── expander.py          # 同义词/关联规则扩充
│   │   ├── dsl_builder.py       # DSL 语法生成（Fofa/Hunter/Shodan）
│   │   └── domain_dicts/
│   │       ├── security.txt
│   │       ├── finance.txt
│   │       ├── ecommerce.txt
│   │       ├── government.txt
│   │       ├── healthcare.txt
│   │       └── tech_stack.txt
│   │
│   ├── asset_discovery/         # M3 资产发现
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── search_engine.py     # 统一资产搜索引擎
│   │   ├── rate_limiter.py      # 平台限流管理
│   │   ├── feature_extractor.py # 五维特征提取
│   │   ├── assessor.py          # 相似度计算与判定
│   │   ├── enricher.py          # 资产深度信息采集
│   │   ├── icp_verifier.py      # ICP 备案验证
│   │   ├── waf_detector.py      # WAF 识别
│   │   ├── tech_fingerprint.py  # 技术栈指纹（Wappalyzer规则）
│   │   └── vector_store.py      # Qdrant 向量存储封装
│   │
│   ├── api_crawler/             # M4 接口爬取
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── browser_controller.py# Playwright 浏览器管理
│   │   ├── cdp_interceptor.py   # CDP 流量捕获
│   │   ├── js_analyzer.py       # JS Bundle 逆向（含 Sourcemap）
│   │   ├── dom_analyzer.py      # DOM 结构分析
│   │   ├── interface_classifier.py # Few-Shot 接口分类（LLM）
│   │   ├── normalizer.py        # 接口标准化（统一格式）
│   │   ├── version_tracker.py   # 接口版本变更追踪
│   │   └── swagger_discoverer.py# OpenAPI/Swagger 文档自动发现
│   │
│   ├── pentest/                 # M5 渗透测试
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── rule_engine.py       # 接口类型→漏洞类型映射规则
│   │   ├── case_generator.py    # LLM 测试用例动态生成
│   │   ├── executor.py          # 测试用例执行引擎
│   │   ├── llm_judge.py         # LLM-as-Judge 漏洞验证
│   │   ├── boundary_guard.py    # 授权边界校验（强制）
│   │   ├── payload_library.py   # Payload 库管理
│   │   └── plugins/             # 漏洞检测插件
│   │       ├── base.py          # 插件基类
│   │       ├── unauthorized.py  # 未授权访问
│   │       ├── privilege_esc.py # 越权操作（水平+垂直）
│   │       ├── sqli.py          # SQL 注入（报错/盲注/联合）
│   │       ├── xss.py           # XSS（反射/存储/DOM）
│   │       ├── ssrf.py          # SSRF
│   │       ├── file_upload.py   # 恶意文件上传
│   │       └── idor.py          # IDOR（直接对象引用）
│   │
│   ├── report/                  # M6 报告生成
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── data_aggregator.py   # 数据汇聚（任务全量数据整合）
│   │   ├── generator.py         # LLM 报告内容生成
│   │   ├── quality_scorer.py    # 报告质量评分
│   │   ├── exporter.py          # Markdown/PDF 导出
│   │   └── templates/
│   │       ├── standard.md.j2   # 标准模板（Jinja2）
│   │       ├── detailed.md.j2   # 详细模板
│   │       └── executive.md.j2  # 管理层摘要模板
│   │
│   ├── models/                  # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── database.py          # 引擎/会话/Base
│   │   ├── task.py
│   │   ├── keyword.py
│   │   ├── asset.py
│   │   ├── interface.py
│   │   ├── vulnerability.py
│   │   ├── intel_document.py
│   │   ├── agent_log.py
│   │   └── report.py
│   │
│   ├── api/                     # FastAPI REST API 层
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口（含中间件配置）
│   │   ├── dependencies.py      # 依赖注入（DB 会话/认证/限流）
│   │   ├── middleware/
│   │   │   ├── auth.py          # JWT 鉴权中间件
│   │   │   ├── rate_limit.py    # API 限流（Redis 令牌桶）
│   │   │   └── audit.py         # 审计日志中间件
│   │   ├── routers/
│   │   │   ├── tasks.py         # /v1/tasks
│   │   │   ├── keywords.py      # /v1/tasks/{id}/keywords
│   │   │   ├── assets.py        # /v1/tasks/{id}/assets
│   │   │   ├── interfaces.py    # /v1/tasks/{id}/interfaces
│   │   │   ├── vulnerabilities.py # /v1/tasks/{id}/vulnerabilities
│   │   │   ├── reports.py       # /v1/tasks/{id}/reports
│   │   │   ├── system.py        # /v1/health, /v1/metrics
│   │   │   └── websocket.py     # WS /v1/tasks/{id}/events
│   │   └── schemas/             # Pydantic 请求/响应模型
│   │       ├── task.py
│   │       ├── keyword.py
│   │       ├── asset.py
│   │       ├── interface.py
│   │       ├── vulnerability.py
│   │       └── report.py
│   │
│   └── shared/                  # 公共基础设施
│       ├── llm_client.py        # LLM 统一调用（重试/缓存/计费统计）
│       ├── cache.py             # Redis 缓存装饰器
│       ├── logger.py            # 结构化日志（OpenTelemetry）
│       ├── metrics.py           # Prometheus 指标注册
│       ├── circuit_breaker.py   # 熔断器（基于失败率）
│       ├── event_bus.py         # Kafka 生产者/消费者封装
│       ├── storage.py           # MinIO 对象存储封装
│       └── exceptions.py        # 自定义异常层级
│
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── TaskList.tsx     # 任务列表
│   │   │   ├── TaskDetail.tsx   # 任务详情（含实时日志）
│   │   │   ├── AssetMap.tsx     # 资产可视化地图
│   │   │   ├── InterfaceList.tsx
│   │   │   ├── VulnList.tsx
│   │   │   └── ReportView.tsx
│   │   ├── components/
│   │   │   ├── PipelineStatus.tsx  # 五层流程状态组件
│   │   │   ├── AgentLogStream.tsx  # 实时日志流（WebSocket）
│   │   │   ├── VulnChart.tsx       # 漏洞分布图（ECharts）
│   │   │   └── AssetTable.tsx
│   │   ├── hooks/
│   │   │   ├── useTaskEvents.ts    # WebSocket 事件订阅
│   │   │   └── useTaskPolling.ts   # 任务状态轮询
│   │   └── services/
│   │       └── api.ts              # Axios API 客户端
│   └── package.json
│
├── migrations/                  # Alembic 数据库迁移
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_vector_id_fields.py
│
├── tests/
│   ├── conftest.py              # pytest 全局 fixtures
│   ├── unit/
│   │   ├── test_keyword_extractor.py
│   │   ├── test_asset_assessor.py
│   │   ├── test_interface_classifier.py
│   │   ├── test_payload_library.py
│   │   └── test_boundary_guard.py
│   ├── integration/
│   │   ├── test_intelligence_module.py
│   │   ├── test_keyword_module.py
│   │   ├── test_asset_discovery.py
│   │   ├── test_api_crawler.py
│   │   └── test_full_pipeline.py
│   ├── e2e/
│   │   ├── test_dvwa_scenario.py   # DVWA 靶场端到端测试
│   │   └── test_webgoat_scenario.py
│   └── fixtures/
│       ├── sample_intel.json
│       ├── sample_assets.json
│       ├── sample_interfaces.json
│       └── mock_responses/
│
└── scripts/
    ├── seed_domain_dicts.py     # 领域词库初始化
    ├── benchmark.py             # 性能基准测试
    ├── health_check.py          # 系统健康检查
    ├── migrate_prompts.py       # 提示词版本迁移
    └── export_test_dataset.py   # 导出测试数据集
```

---

## 13. 测试样例

### 13.1 单元测试样例

#### 测试用例 UT-KW-001：关键词权重计算

```python
# tests/unit/test_keyword_extractor.py

def test_keyword_weight_calculation():
    """验证 TF-IDF + 领域词库的权重计算"""
    
    from src.keywords.ranker import KeywordRanker
    
    ranker = KeywordRanker(domain="finance")
    
    # 领域强相关词（DomainScore 高）
    score_fintech = ranker.compute_weight(
        word="第三方支付",
        tf_idf=0.45,
        domain_score=0.92,
        relevance_score=0.88
    )
    
    # 通用词（DomainScore 低）
    score_generic = ranker.compute_weight(
        word="管理系统",
        tf_idf=0.60,  # TF-IDF 更高
        domain_score=0.15,
        relevance_score=0.30
    )
    
    # 验证：领域词权重应高于通用词，即便 TF-IDF 更低
    assert score_fintech > score_generic
    assert 0.7 < score_fintech < 1.0
    assert score_generic < 0.4
```

#### 测试用例 UT-ASSESS-001：资产归属判定（正例）

```python
def test_asset_assessment_positive():
    """ICP 精确匹配应直接判定为高置信度靶标"""
    
    target_profile = TargetProfile(
        company_name="XX支付科技有限公司",
        icp_entities=["XX支付科技有限公司", "XY科技有限公司"],
        root_domains=["xx-payment.com"],
        ip_ranges=["203.0.113.0/24"],
    )
    
    asset = RawAsset(
        domain="api.xx-payment.com",
        ip_address="203.0.113.45",
        icp_entity="XX支付科技有限公司",  # 精确匹配
        headers={"Server": "nginx", "X-Powered-By": "Spring Boot"},
    )
    
    result = assessor.assess(target_profile, asset)
    
    assert result.is_target == True
    assert result.confidence >= 0.95
    assert "P1" in result.matched_rules  # ICP 精确匹配规则
```

#### 测试用例 UT-ASSESS-002：资产归属判定（负例）

```python
def test_asset_assessment_cdn_node():
    """CDN 节点不应仅凭 IP 归属判定为靶标"""
    
    asset = RawAsset(
        domain="cdn-12345.cloudflare.com",   # Cloudflare 域名
        ip_address="104.16.0.1",             # Cloudflare IP
        icp_entity=None,
    )
    
    result = assessor.assess(target_profile, asset)
    
    assert result.is_target == False
    assert result.confidence < 0.30
```

#### 测试用例 UT-BOUNDARY-001：越界测试阻断

```python
@pytest.mark.asyncio
async def test_boundary_guard_blocks_unauthorized():
    """未在授权白名单内的资产，任何测试必须被阻断"""
    
    task = Task(authorized_scope={
        "domains": ["xx-payment.com"],
        "ip_ranges": ["203.0.113.0/24"]
    })
    
    # 不在白名单的资产
    unauthorized_asset_id = "asset_unrelated_com"
    
    with pytest.raises(UnauthorizedTestError):
        await boundary_guard.check(unauthorized_asset_id)
    
    # 验证审计日志被写入
    audit_entries = await audit_log.get_recent(1)
    assert audit_entries[0]["event"] == "boundary_violation_attempt"
```

### 13.2 集成测试样例

#### 测试用例 IT-INTEL-001：情报采集完整流程

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligence_full_pipeline(mock_news_server, mock_icp_server):
    """验证情报采集完整链路：采集→清洗→RAG写入"""
    
    task = await create_test_task("测试企业A")
    
    # 启动情报采集
    job = await intel_module.start_collection(
        task_id=task.id,
        company_name="测试企业A",
        config=CollectionConfig(
            sources=["news", "official"],
            max_items_per_source=50,
        )
    )
    
    # 等待完成（最多60秒）
    await wait_for_job_complete(job.id, timeout=60)
    
    # 验证输出
    docs = await intel_module.get_cleaned_intel(task.id)
    
    assert len(docs) > 0
    assert all(doc.quality_score >= 0.6 for doc in docs)
    assert all(doc.rag_indexed for doc in docs)  # 增量写入验证
    
    # 验证 RAG 可检索
    rag_results = await intel_module.search_rag("测试企业A 技术栈")
    assert len(rag_results) > 0
```

#### 测试用例 IT-CRAWL-001：动态接口捕获

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dynamic_interface_capture(dvwa_server):
    """对 DVWA 靶场验证动态接口捕获能力"""
    
    target_url = f"http://localhost:{dvwa_server.port}"
    
    # 初始化爬取模块
    crawler = ApiCrawlerModule()
    
    # 爬取接口
    interfaces = await crawler.crawl(
        asset=Asset(domain="localhost", port=dvwa_server.port, protocol="http"),
        credentials={"username": "admin", "password": "password"},
    )
    
    # 验证关键接口被捕获
    paths = [iface.path for iface in interfaces]
    
    assert any("/login.php" in p for p in paths)        # 认证接口
    assert any("/vulnerabilities/sqli/" in p for p in paths)  # SQL 注入接口
    assert any("/vulnerabilities/upload/" in p for p in paths) # 文件上传接口
    
    # 验证接口信息完整性
    for iface in interfaces:
        assert iface.method in ["GET", "POST", "PUT", "DELETE", "PATCH"]
        assert iface.api_type is not None
        assert iface.crawl_method in ["static", "dynamic", "cdp"]
    
    # 验证漏爬率
    expected_interfaces = dvwa_server.known_interface_count  # 靶场已知接口数
    actual_count = len(interfaces)
    crawl_coverage = actual_count / expected_interfaces
    
    assert crawl_coverage >= 0.90, f"接口覆盖率 {crawl_coverage:.1%} 低于目标 90%"
```

### 13.3 端到端测试样例

#### 测试用例 E2E-001：DVWA 完整探测流程

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_pipeline_dvwa(dvwa_server, webgoat_server):
    """
    对两个靶场执行完整探测流程，验证所有阶段的指标
    预计执行时间：15-30 分钟
    """
    
    task_id = await create_and_run_task({
        "company_name": "DVWA 测试靶场",
        "authorized_scope": {
            "domains": ["localhost"],
            "ip_ranges": ["127.0.0.0/8"]
        },
        "config": {
            "asset_platforms": [],  # 不调用真实 API
            "manual_assets": [f"http://localhost:{dvwa_server.port}"],
            "pentest_enabled": True,
        }
    })
    
    # 等待任务完成（最多40分钟）
    result = await wait_for_task(task_id, timeout=2400)
    
    assert result.status == "completed"
    
    # 阶段指标验证
    stats = result.stats
    
    # 接口爬取指标
    assert stats.interface_crawl_coverage >= 0.90, "接口覆盖率不达标"
    assert stats.parameter_completeness >= 0.90,   "参数完整度不达标"
    
    # 漏洞检测指标
    known_vulns = dvwa_server.get_known_vulnerabilities()
    detected_vuln_types = {v.vuln_type for v in result.vulnerabilities if v.llm_confidence > 0.8}
    
    detection_rate = len(known_vulns & detected_vuln_types) / len(known_vulns)
    assert detection_rate >= 0.95, f"漏洞检测率 {detection_rate:.1%} 低于目标 95%"
    
    false_positives = [v for v in result.vulnerabilities
                       if v.vuln_type not in known_vulns and v.llm_confidence > 0.8]
    fp_rate = len(false_positives) / max(len(result.vulnerabilities), 1)
    assert fp_rate <= 0.15, f"误报率 {fp_rate:.1%} 高于目标 15%"
    
    # 报告生成指标
    report = result.report
    assert report is not None
    assert report.quality_score["overall"] >= 0.90
    assert report.generation_duration_s <= 1800  # 30 分钟
```

---

## 14. 功能开发进度表

### 14.1 总体里程碑

| 里程碑 | 时间节点 | 核心交付物 | 验收指标 |
|-------|---------|----------|---------|
| M1.0 | 第 4 个月末 | 情报采集 + 关键词引擎 v1.0 | 关键词≥3类，准确率≥85% |
| M1.5 | 第 8 个月末 | 接口爬取 v1.0（基础版） | 漏爬率≤12%，参数完整度≥85% |
| M1.9 | 第 12 个月末 | 第一阶段完整系统 | 动态接口识别≥90%，完整技术文档 |
| M2.3 | 第 16 个月末 | 自动渗透 v1.0 + 测试引擎 | 漏洞覆盖率≥92%，误报≤18% |
| M2.7 | 第 20 个月末 | 报告生成 v1.0 + 前端 v1.0 | 报告≤30分钟，质量分≥0.90 |
| M2.9 | 第 24 个月末 | 全流程 v2.0 + 真实项目验证 | 效率提升≥60%，5个真实项目 |

### 14.2 第一阶段详细任务（第 1-12 个月）

| 月份 | 模块 | 任务描述 | 负责人 | 工作量（人天） | 前置依赖 | 状态 |
|-----|------|---------|-------|------------|---------|-----|
| 1-2 | 基础设施 | PostgreSQL + Alembic 初始 Schema 设计 | 架构组 | 5 | - | 待启动 |
| 1-2 | 基础设施 | Docker Compose 开发环境（含 Kafka/Redis/Qdrant） | DevOps | 4 | - | 待启动 |
| 1-2 | 基础设施 | FastAPI 应用骨架 + JWT 认证 + OpenAPI 文档 | 开发组A | 5 | - | 待启动 |
| 1-2 | 基础设施 | LangGraph 编排框架搭建 + 全局状态定义 | 架构组 | 6 | - | 待启动 |
| 1-2 | 基础设施 | Kafka 事件总线 + Agent 解耦架构 | 架构组 | 4 | - | 待启动 |
| 1-2 | 基础设施 | Prometheus + Grafana 监控基础看板 | DevOps | 3 | - | 待启动 |
| 1-2 | 基础设施 | 结构化日志（OpenTelemetry 集成） | DevOps | 3 | - | 待启动 |
| 2-3 | M1 | Scrapy 多线程爬虫框架 + 新闻/招投标爬虫 | 开发组A | 8 | 基础设施 | 待启动 |
| 2-3 | M1 | ICP 备案查询接口集成 + 企业信息爬取 | 开发组A | 5 | - | 待启动 |
| 2-3 | M1 | IP 代理池管理服务（Redis 存储 + 健康检查） | 开发组A | 4 | Redis | 待启动 |
| 2-3 | M1 | UA 池 + 浏览器指纹伪装模块 | 开发组A | 3 | - | 待启动 |
| 2-4 | M1 | CDP 流量捕获层（WebSocket/SSE/gRPC-Web） | 开发组A | 10 | Playwright | 待启动 |
| 3-4 | M1 | Fofa API 封装（分页/限流/重试/字段映射） | 开发组B | 4 | - | 待启动 |
| 3-4 | M1 | Hunter API 封装 | 开发组B | 3 | - | 待启动 |
| 3-4 | M1 | 数据清洗流水线（去重/降噪/质量评分） | 算法组 | 6 | M1爬虫 | 待启动 |
| 3-4 | M2 | Qwen-7B 本地部署 + FastAPI 推理服务 | 算法组 | 6 | GPU服务器 | 待启动 |
| 3-4 | M2 | 关键词提取 Prompt 设计 + v1 版本测试 | 算法组 | 5 | LLM服务 | 待启动 |
| 4 | M2 | TF-IDF + 领域词库权重排序模型 | 算法组 | 4 | - | 待启动 |
| 4 | M2 | 关键词同义词/关联规则扩充模块 | 算法组 | 4 | - | 待启动 |
| 4 | M2 | DSL 生成模块（Fofa/Hunter/Shodan 语法） | 开发组B | 5 | M2关键词 | 待启动 |
| 4 | M2 | 增量式 RAG 知识库（LlamaIndex + Qdrant） | 算法组 | 6 | Qdrant | 待启动 |
| 4 | 测试 | 单元测试覆盖率达 75%（M1+M2） | 测试组 | 5 | M1+M2 | 待启动 |
| 5-6 | M3 | 资产五维特征提取器 | 开发组B | 7 | - | 待启动 |
| 5-6 | M3 | 余弦相似度资产判定 + 阈值调优 | 算法组 | 6 | 特征提取器 | 待启动 |
| 5-6 | M3 | Qdrant 资产特征向量存储集成 | 开发组B | 4 | Qdrant | 待启动 |
| 5-6 | M3 | WAF 识别模块 + 技术栈指纹（Wappalyzer） | 开发组B | 5 | - | 待启动 |
| 5-6 | M3 | 资产增强信息采集（端口/证书/截图） | 开发组B | 5 | - | 待启动 |
| 6-7 | M4 | Playwright 浏览器控制基础框架 + 连接池 | 开发组A | 6 | - | 待启动 |
| 6-7 | M4 | LLM 登录页识别 + 操作序列生成（Prompt v1） | 算法组 | 7 | LLM+Playwright | 待启动 |
| 7-8 | M4 | JS Bundle 逆向解析（Webpack/Vite + Sourcemap） | 开发组A | 8 | - | 待启动 |
| 7-8 | M4 | OpenAPI/Swagger 文档自动发现 | 开发组A | 4 | - | 待启动 |
| 7-8 | M4 | GraphQL 内省查询支持 | 开发组A | 4 | - | 待启动 |
| 8-9 | M4 | Few-Shot 接口分类模型（LLM Prompt + 后处理） | 算法组 | 6 | LLM | 待启动 |
| 8-9 | M4 | 接口标准化（统一路径模式 + 参数格式化） | 开发组A | 4 | - | 待启动 |
| 9-10 | M4 | 接口版本变更追踪（Checksum Diff） | 开发组A | 4 | - | 待启动 |
| 9-10 | M4 | Vue/React/JSP 特化爬取优化 | 开发组A | 6 | M4基础 | 待启动 |
| 10-11 | 编排层 | BoundaryGuard 授权边界校验模块 | 架构组 | 5 | - | 待启动 |
| 10-11 | 编排层 | 熔断器 + 任务应急回滚机制 | 架构组 | 5 | - | 待启动 |
| 10-11 | 编排层 | 全流程串联测试 + 反馈回路验证 | 架构组 | 8 | 所有M1-M4 | 待启动 |
| 11-12 | 测试 | 靶场集成测试（DVWA + WebGoat） | 测试组 | 8 | M4完成 | 待启动 |
| 11-12 | 测试 | 性能基准测试 + 瓶颈优化 | 算法组 | 5 | - | 待启动 |
| 12 | 文档 | 第一阶段技术文档 + API 文档 + 部署指南 | 全团队 | 6 | - | 待启动 |

### 14.3 第二阶段详细任务（第 13-24 个月）

| 月份 | 模块 | 任务描述 | 负责人 | 工作量（人天） | 前置依赖 | 状态 |
|-----|------|---------|-------|------------|---------|-----|
| 13-14 | M5 | 接口类型→漏洞映射规则库构建 | 安全组 | 8 | - | 规划中 |
| 13-14 | M5 | Payload 库初始化（SQLi/XSS/SSRF/越权） | 安全组 | 6 | - | 规划中 |
| 13-14 | M5 | LLM 测试用例生成 Prompt v1 + 测试 | 算法组 | 7 | LLM+规则库 | 规划中 |
| 14-15 | M5 | 测试执行引擎（限速/超时/并发控制） | 开发组A | 8 | - | 规划中 |
| 14-15 | M5 | SQLi 插件（报错/盲注/联合查询） | 安全组 | 8 | 执行引擎 | 规划中 |
| 14-15 | M5 | 越权检测插件（水平+垂直越权） | 安全组 | 7 | 执行引擎 | 规划中 |
| 15-16 | M5 | 未授权访问 + IDOR + XSS 插件 | 安全组 | 8 | 执行引擎 | 规划中 |
| 15-16 | M5 | SSRF + 文件上传插件 | 安全组 | 6 | 执行引擎 | 规划中 |
| 15-16 | M5 | GraphQL/gRPC 接口测试支持 | 安全组 | 6 | - | 规划中 |
| 16-17 | M5 | LLM-as-Judge 漏洞验证（GPT-4o） | 算法组 | 8 | GPT-4o API | 规划中 |
| 16-17 | M5 | 误报样本库构建 + LLM Judge 优化 | 算法组 | 5 | LLM Judge v1 | 规划中 |
| 17-18 | M6 | 报告数据聚合器（全量数据整合） | 开发组B | 5 | - | 规划中 |
| 17-18 | M6 | 报告 LLM 生成 Prompt 设计（各章节） | 算法组 | 7 | - | 规划中 |
| 18-19 | M6 | Markdown/PDF 双格式报告模板 | 开发组B | 5 | - | 规划中 |
| 18-19 | M6 | LLM-as-Judge 报告质量评分 | 算法组 | 5 | 报告生成 | 规划中 |
| 19-20 | 前端 | React 18 + TypeScript 基础框架 | 前端组 | 6 | - | 规划中 |
| 19-20 | 前端 | 任务管理面板（创建/监控/暂停/恢复） | 前端组 | 8 | - | 规划中 |
| 20-21 | 前端 | Agent 状态实时监控（WebSocket） | 前端组 | 6 | WS API | 规划中 |
| 20-21 | 前端 | 资产/漏洞可视化看板（ECharts） | 前端组 | 8 | - | 规划中 |
| 21-22 | 集成 | 全流程 v2.0 串联 + 端到端测试 | 全团队 | 10 | 所有模块 | 规划中 |
| 22-23 | 实战 | 5 个真实项目落地测试 + 数据收集 | 安全组 | 20 | v2.0 | 规划中 |
| 23-24 | 优化 | 基于真实项目反馈的系统优化 | 全团队 | 15 | 实战测试 | 规划中 |
| 23-24 | 运维 | K8s 部署配置 + Docker 镜像发布 | DevOps | 8 | - | 规划中 |
| 24 | 文档 | 完整 API 文档 + 部署指南 + 培训材料 | 全团队 | 8 | - | 规划中 |

---

## 15. 部署与运维

### 15.1 本地开发环境

```bash
# 克隆项目
git clone https://github.com/example/attackscope-ai.git
cd attackscope-ai

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入 API Keys

# 启动基础设施
make dev-up
# 等价于: docker-compose up -d postgres redis qdrant kafka

# 安装 Python 依赖
poetry install

# 执行数据库迁移
make migrate
# 等价于: alembic upgrade head

# 初始化领域词库
python scripts/seed_domain_dicts.py

# 启动 API 服务（热重载）
make dev-api
# 等价于: uvicorn src.api.main:app --reload --port 8000

# 启动前端开发服务
cd frontend && npm install && npm run dev
```

### 15.2 环境变量配置

```bash
# .env.example

# === LLM 配置 ===
QWEN_MODEL_PATH=/models/Qwen2.5-7B-Instruct-GPTQ-Int8
QWEN_SERVER_PORT=8001
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# === 数据库 ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/attackscope
REDIS_URL=redis://localhost:6379/0

# === 向量数据库 ===
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                    # 生产环境必填

# === 消息队列 ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# === 对象存储 ===
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=attackscope

# === 资产搜索平台 API ===
FOFA_EMAIL=your@email.com
FOFA_API_KEY=xxx
HUNTER_API_KEY=xxx
SHODAN_API_KEY=xxx

# === 安全配置 ===
JWT_SECRET_KEY=your-256-bit-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
AUDIT_LOG_IMMUTABLE=true       # 审计日志不可删除

# === 功能开关 ===
PENTEST_ENABLED=true
PENTEST_INTENSITY=normal       # light|normal|aggressive
LLM_JUDGE_ENABLED=true
RAG_INCREMENTAL_UPDATE=true
```

### 15.3 生产环境部署要点

```yaml
# 关键服务资源需求（Kubernetes）

resources:
  api_gateway:
    replicas: 2
    cpu: "500m"
    memory: "512Mi"
  
  orchestrator:
    replicas: 2
    cpu: "1000m"
    memory: "2Gi"
  
  llm_inference:
    replicas: 1
    cpu: "4000m"
    memory: "16Gi"
    gpu: 1                     # NVIDIA GPU（INT8量化需约4GB显存）
  
  browser_pool:
    replicas: 3
    cpu: "2000m"
    memory: "4Gi"
    # 每个副本维护 5 个 Playwright 浏览器实例
  
  postgresql:
    storage: "100Gi"
    backup: "daily"
  
  qdrant:
    storage: "50Gi"
    replicas: 1
  
  kafka:
    partitions: 10
    retention_hours: 72
```

### 15.4 熔断器配置

```python
CIRCUIT_BREAKER_CONFIG = {
    "llm_inference": {
        "failure_threshold":  5,     # 连续失败 5 次触发熔断
        "recovery_timeout":   60,    # 60 秒后尝试恢复
        "half_open_requests": 3,     # 半开状态允许 3 个请求
    },
    "fofa_api": {
        "failure_threshold":  3,
        "recovery_timeout":   120,
        "half_open_requests": 1,
    },
    "playwright": {
        "failure_threshold":  2,     # 浏览器崩溃快速熔断
        "recovery_timeout":   30,
        "half_open_requests": 1,
    },
}
```

---

## 16. 安全合规

### 16.1 授权边界管理

所有渗透测试任务必须包含明确的 `authorized_scope`，该字段：
- 不可为空（API 层强制校验）
- 一经创建不可修改（变更需创建新任务）
- 所有测试请求经 `BoundaryGuard` 二次验证
- 越界尝试写入不可删除的审计日志

### 16.2 数据安全

```
敏感数据处理规则：

1. 传输加密：所有 API 通信强制 HTTPS (TLS 1.3)
2. 存储加密：
   - 漏洞证据（含 Token/密码）：AES-256-GCM 加密存储
   - 数据库密码字段：bcrypt 哈希
3. 日志脱敏：
   - Agent 日志中的 IP/域名自动打码（仅保留最后一段）
   - Token/密码在日志中替换为 [REDACTED]
4. 数据隔离：
   - 不同任务的数据严格隔离（task_id 强制过滤）
   - API 层验证当前用户只能访问自己的任务
```

### 16.3 漏洞信息处理规范

- 漏洞证据（请求/响应体）存储于加密对象存储，链接有效期 24 小时
- 报告 PDF 包含水印（任务 ID + 生成时间），防止泄露溯源
- 超过 90 天的任务数据自动归档（可配置保留策略）
- 高危漏洞发现后，自动触发 Webhook 通知（支持钉钉/飞书/Slack）

---

*文档版本：v2.0.0 | 最后更新：2024-01-01 | 保密级别：内部使用*
