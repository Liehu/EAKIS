
---

## 4. M2 关键词引擎模块

### 4.1 模块概述

**职责**：从清洗后的情报中提取多维度关键词，构建动态关键词库，驱动资产检索。

**输入**：M1 输出的结构化情报片段  
**输出**：分类权重关键词库（JSON），同时反馈优化 DSL 生成策略

### 4.2 数据摘要 Agent (KW-SUMMARIZER)

**功能**：将大量情报片段压缩为结构化摘要，降低关键词提取的 Token 消耗。

```python
class SummarizerConfig:
    MAX_INPUT_TOKENS  = 4096   # 每次摘要的最大输入 token 数
    TARGET_RATIO      = 0.15   # 目标压缩比（输出约为输入的 15%）
    CHUNK_SIZE        = 1000   # 情报分块大小（字符数）
    CHUNK_OVERLAP     = 100    # 分块重叠大小

# 摘要 Prompt（Map-Reduce 策略）
SUMMARIZE_MAP_PROMPT = """
你是情报分析员。请从以下文本中提取与企业攻击面相关的关键信息，
只保留：业务描述、技术词汇、子公司/合作伙伴名称、产品名称。
去除：无关新闻、广告、通用描述。

文本：{text}

输出格式（JSON）：
{
  "business_info": "核心业务描述（50字以内）",
  "tech_mentions": ["技术词1", "技术词2"],
  "entity_mentions": ["实体1", "实体2"],
  "product_mentions": ["产品1", "产品2"]
}
"""
```

### 4.3 关键词生成 Agent (KW-GENERATOR)

#### 4.3.1 三类关键词定义

| 类型 | 定义 | 示例 | 用于检索的平台 |
|-----|------|------|-------------|
| **业务关键词** | 企业主营业务、产品服务、行业标签 | 第三方支付、电子签名、核心系统 | Fofa title / 新闻检索 |
| **技术关键词** | 使用的框架、数据库、中间件、协议 | Spring Boot、Kubernetes、Redis | Fofa header / Shodan |
| **关联主体关键词** | 子公司、合作伙伴、投资方、供应商 | XY科技、ZZ银行 | ICP 备案 / 资产关联 |

#### 4.3.2 权重计算模型

```
Wk = α × TF-IDF(k) + β × DomainScore(k) + γ × RelevanceScore(k)

参数说明：
  TF-IDF(k)       — 关键词在情报文本中的词频-逆文档频率
  DomainScore(k)  — 关键词在安全/行业领域词库中的匹配得分 (0~1)
  RelevanceScore(k)— LLM 评估关键词与靶标核心业务的关联度 (0~1)
  
超参数（通过历史样本训练）：
  α = 0.35  （TF-IDF 权重）
  β = 0.40  （领域相关性权重，最高，避免通用词）
  γ = 0.25  （业务关联度权重）
```

#### 4.3.3 动态扩充策略

```python
class KeywordExpander:
    """关键词动态扩充，提升资产检索覆盖率"""
    
    EXPANSION_STRATEGIES = {
        "synonym":    "同义词扩充（如 '微服务' → 'Spring Cloud', 'Dubbo'）",
        "abbreviation": "缩写扩充（如 '支付宝' → 'Alipay'）",
        "subdomain":  "子域模式（如 '企业名' → 'api.企业名', 'm.企业名'）",
        "tech_stack": "技术栈关联（如 'Spring Boot' → 'actuator', '/health'）",
        "relation":   "关联规则（企业A → 合作伙伴 → 企业B的资产）",
    }
    
    async def expand(
        self,
        keywords: list[Keyword],
        strategy: str = "all"
    ) -> list[Keyword]:
        """
        扩充后的关键词自动继承原关键词的 50% 权重，
        并标记为 derived=True，便于过滤和溯源
        """
```

#### 4.3.4 关键词反馈优化

```
触发条件：关键词检索后，若命中率 < 20% 或结果 < 10 条
  
反馈动作：
  1. 将当前关键词集标记为 low_yield
  2. 查询 RAG 知识库中同类型企业的历史有效关键词
  3. LLM 结合历史经验生成新一批关键词
  4. 重新提交 DSL 生成，循环至多 3 次
  
写入 RAG 的反馈记录：
  {
    "company_type": "金融科技/支付",
    "failed_keywords": ["XX支付", "电子签名"],
    "failure_reason": "结果过少，语义过窄",
    "successful_keywords": ["第三方支付牌照", "cert:xx-payment.com"],
    "lesson": "金融企业建议使用牌照关键词和证书信息"
  }
```

### 4.4 领域词库设计

```
domain_dict/
├── security.txt        # 安全领域词（漏洞类型、攻击面术语）
│   ├── SQL注入, XSS, SSRF, RCE, 未授权访问 ...
│   └── WAF, IDS, JWT, OAuth, CORS ...
│
├── finance.txt         # 金融行业词
│   ├── 第三方支付, 网银, 清结算, 核心系统 ...
│   └── PCI-DSS, 国密, SWIFT, 备付金 ...
│
├── ecommerce.txt       # 电商行业词
├── government.txt      # 政务行业词
├── healthcare.txt      # 医疗行业词
│
└── tech_stack.txt      # 技术栈词（持续更新）
    ├── Java: Spring Boot, Dubbo, MyBatis, Shiro ...
    ├── Python: Django, Flask, FastAPI, Celery ...
    ├── Frontend: Vue, React, Angular, Webpack ...
    └── Database: MySQL, PostgreSQL, MongoDB, Redis ...
```

---

## 5. M3 资产发现模块

### 5.1 模块概述

**职责**：基于关键词库，通过资产搜索平台批量检索，并利用 AI 多特征融合算法精准判定资产归属。

**输入**：M2 输出的关键词库  
**输出**：精准靶标资产清单（含归属置信度、技术特征、风险预评估）

### 5.2 资产检索引擎

#### 5.2.1 多平台统一接口封装

```python
class AssetSearchEngine:
    """统一的资产搜索平台抽象层"""
    
    # 支持的搜索平台
    PLATFORMS = ["fofa", "hunter", "shodan", "censys", "zoomeye"]
    
    async def search(
        self,
        platform: str,
        dsl: str,
        page_size: int = 100,
        max_pages: int = 10,
        fields: list[str] = None
    ) -> AsyncIterator[RawAsset]:
        """
        统一搜索接口，支持分页流式返回
        
        fields 默认包含：
          fofa:   ["ip", "port", "domain", "title", "header", "body", "cert", "icon_hash", "icp"]
          hunter: ["ip", "port", "domain", "web_title", "banner", "company", "icp"]
          shodan: ["ip_str", "port", "hostnames", "org", "http.title", "http.headers"]
        """
    
    async def batch_search(
        self,
        keywords: list[Keyword],
        platforms: list[str] = ["fofa", "hunter"],
        deduplicate: bool = True
    ) -> list[RawAsset]:
        """
        批量关键词搜索：
        1. 并行调用多平台
        2. 自动限流（遵守平台 API 速率限制）
        3. 结果去重（基于 IP+端口+域名 三元组）
        """
```

#### 5.2.2 平台限流策略

```python
RATE_LIMITS = {
    "fofa": {
        "requests_per_minute": 10,
        "requests_per_day":    1000,
        "points_per_request":  1,
        "daily_point_quota":   10000,
    },
    "hunter": {
        "requests_per_minute": 5,
        "requests_per_day":    500,
    },
    "shodan": {
        "requests_per_second": 1,
        "monthly_query_limit": 100,
    },
}

# 限流器实现（令牌桶算法）
class RateLimiter:
    def __init__(self, platform: str):
        self.bucket = TokenBucket(
            capacity=RATE_LIMITS[platform]["requests_per_minute"],
            refill_rate=RATE_LIMITS[platform]["requests_per_minute"] / 60
        )
```

### 5.3 资产相关性评估 Agent (ASSET-ASSESSOR)

#### 5.3.1 五维特征提取

```python
class AssetFeatureExtractor:
    """
    提取资产的五个维度特征，用于相似度计算
    """
    
    FEATURE_WEIGHTS = {
        "icp_entity":     0.35,   # ICP 备案主体（最高权重）
        "domain_pattern": 0.25,   # 域名模式匹配
        "ip_attribution": 0.20,   # IP 归属地/ASN
        "header_features":0.12,   # HTTP 响应头特征
        "page_keywords":  0.08,   # 页面内容关键词
    }
    
    async def extract(self, asset: RawAsset) -> FeatureVector:
        """
        特征提取流水线：
        1. ICP 主体: 查询 ICP 备案API，获取主体名称，向量化编码
        2. 域名模式: 提取根域名/子域名模式，生成 n-gram 特征
        3. IP 归属: 调用 IP 情报库，获取 ASN/ORG/地理信息
        4. Header 特征: 提取 Server/X-Powered-By/框架标识
        5. 页面关键词: TF-IDF 提取页面核心词，与靶标关键词对比
        
        返回归一化的 5 维加权特征向量
        """
    
    async def extract_with_screenshot(
        self, asset: RawAsset
    ) -> FeatureVector:
        """
        增强版：截图 + OCR 提取 favicon hash 和页面文字
        用于无 ICP 备案的境外资产判断
        """
```

#### 5.3.2 相似度计算模型

```
加权余弦相似度：

Sim(V_target, V_asset) = 
  Σ(wi × V_target,i × V_asset,i) /
  √(Σ(wi × V_target,i²)) × √(Σ(wi × V_asset,i²))

判定阈值（θ）：
  θ ≥ 0.85 → 高置信度靶标资产（直接纳入）
  θ ∈ [0.65, 0.85) → 中置信度（人工确认队列）
  θ < 0.65 → 低置信度（剔除）

特殊规则（优先级高于阈值）：
  - ICP 主体精确匹配 → 直接判定为靶标（置信度 0.98）
  - IP 在靶标已知 IP 段内 + 至少1个其他特征匹配 → 置信度 0.90
  - 域名为已知主域名的子域 → 置信度 0.88
```

#### 5.3.3 Vector DB 持久化设计

```python
# Qdrant 集合设计
ASSET_COLLECTION = {
    "name":        "target_asset_features",
    "vector_size": 768,           # text-embedding-3-small 维度
    "distance":    "Cosine",
    
    # 分片策略（提升查询性能）
    "shard_number": 2,
    "replication_factor": 1,
    
    # Payload 索引（支持过滤查询）
    "payload_indexes": [
        {"field": "task_id",    "type": "keyword"},
        {"field": "confidence", "type": "float"},
        {"field": "asset_type", "type": "keyword"},
    ]
}

# 资产特征向量存储
async def upsert_asset_vector(asset: Asset, vector: list[float]):
    await qdrant.upsert(
        collection_name="target_asset_features",
        points=[PointStruct(
            id=str(asset.id),
            vector=vector,
            payload={
                "task_id":    asset.task_id,
                "domain":     asset.domain,
                "ip":         asset.ip_address,
                "asset_type": asset.asset_type,
                "confidence": asset.confidence_score,
                "icp_verified": asset.icp_verified,
            }
        )]
    )
```

### 5.4 资产增强信息采集

```python
class AssetEnricher:
    """
    对判定为靶标的资产进行深度信息采集
    """
    
    async def enrich(self, asset: Asset) -> EnrichedAsset:
        # 并行执行多项信息采集
        results = await asyncio.gather(
            self._get_ports_services(asset),      # 端口/服务扫描
            self._get_cert_info(asset),           # TLS 证书信息
            self._get_waf_detection(asset),       # WAF 识别
            self._get_tech_fingerprint(asset),    # 技术栈指纹
            self._get_web_title(asset),           # 页面标题
            self._capture_screenshot(asset),      # 截图存储
            return_exceptions=True
        )
        return self._merge_enrichment(asset, results)
    
    async def _get_tech_fingerprint(self, asset: Asset) -> TechStack:
        """
        技术指纹识别（基于 Wappalyzer 规则库）：
        - 响应头特征 (Server, X-Powered-By, Set-Cookie 等)
        - HTML 内容特征 (meta generator, script src, link href)
        - JavaScript 全局变量
        - CSS 类名特征
        - 图标哈希
        """
    
    async def _get_waf_detection(self, asset: Asset) -> WAFInfo:
        """
        WAF/安全设备识别：
        发送探测请求（含常见 WAF 触发特征），
        根据响应特征（状态码/Body/Header）判断 WAF 类型
        （Cloudflare/阿里云盾/腾讯云防火墙/ModSecurity 等）
        """
```

---

## 6. M4 智能接口爬取模块

### 6.1 模块概述

**职责**：对目标资产进行深度接口采集，覆盖静态声明接口、动态交互接口和隐藏接口。

**输入**：M3 输出的精准靶标资产清单  
**输出**：标准化接口特征库（含路径/方法/参数/认证/类型/触发场景）

### 6.2 接口爬取分层策略

```
Layer 1 - 静态分析（无需浏览器）：
  ├─ JS Bundle 逆向解析（webpack 产物、路由表提取）
  ├─ HTML 页面 form action / fetch / XHR 调用
  ├─ Swagger/OpenAPI 文档自动发现（/api-docs, /swagger.json）
  └─ GraphQL 内省查询（/__graphql, /graphql）

Layer 2 - 动态交互（Playwright + LLM）：
  ├─ 模拟用户交互（点击/输入/滚动）
  ├─ 登录后接口捕获
  ├─ 按钮/表单提交触发接口
  └─ 路由跳转触发的懒加载接口

Layer 3 - 精细流量捕获（CDP）：
  ├─ WebSocket 消息捕获
  ├─ SSE (Server-Sent Events) 流
  ├─ gRPC-Web 请求
  └─ Service Worker 拦截的请求

Layer 4 - 相似接口推断（Few-Shot + KNN）：
  └─ 基于已捕获接口特征，推断未触发的同类接口
```

### 6.3 CDP 流量捕获器

```python
class CDPInterceptor:
    """
    基于 Chrome DevTools Protocol 的精细流量捕获
    """
    
    async def setup(self, page: Page):
        """初始化 CDP 会话，注入所有必要的监听器"""
        cdp = await page.context.new_cdp_session(page)
        
        # 启用网络追踪
        await cdp.send("Network.enable", {
            "maxResourceBufferSize": 10 * 1024 * 1024,  # 10MB 缓冲
            "maxTotalBufferSize":    50 * 1024 * 1024,  # 50MB 总缓冲
        })
        
        # 监听所有请求（含二进制）
        cdp.on("Network.requestWillBeSent",     self._on_request)
        cdp.on("Network.responseReceived",      self._on_response)
        cdp.on("Network.webSocketCreated",      self._on_ws_created)
        cdp.on("Network.webSocketFrameSent",    self._on_ws_frame_sent)
        cdp.on("Network.webSocketFrameReceived",self._on_ws_frame_received)
        
        # 注入 JS 钩子，在页面加载前捕获 fetch/XHR
        await cdp.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": self._get_intercept_script()
        })
        
        self.cdp = cdp
    
    def _get_intercept_script(self) -> str:
        """
        注入到页面的 JS 钩子脚本：
        - 拦截 fetch 调用，记录 URL/method/headers/body
        - 拦截 XMLHttpRequest，记录同样信息
        - 拦截 WebSocket 构造函数，记录连接 URL
        - 拦截 EventSource 构造函数，记录 SSE URL
        """
        return """
        (function() {
          const _fetch = window.fetch;
          window.fetch = function(url, opts={}) {
            window.__captured_requests = window.__captured_requests || [];
            window.__captured_requests.push({
              type: 'fetch',
              url: url.toString(),
              method: (opts.method || 'GET').toUpperCase(),
              headers: opts.headers || {},
              body: opts.body || null,
              timestamp: Date.now()
            });
            return _fetch.apply(this, arguments);
          };
          
          const _XHROpen = XMLHttpRequest.prototype.open;
          XMLHttpRequest.prototype.open = function(method, url) {
            this.__xhr_info = { method, url };
            return _XHROpen.apply(this, arguments);
          };
          
          const _XHRSend = XMLHttpRequest.prototype.send;
          XMLHttpRequest.prototype.send = function(body) {
            if (this.__xhr_info) {
              window.__captured_requests = window.__captured_requests || [];
              window.__captured_requests.push({
                type: 'xhr',
                method: this.__xhr_info.method,
                url: this.__xhr_info.url,
                body: body || null,
                timestamp: Date.now()
              });
            }
            return _XHRSend.apply(this, arguments);
          };
        })();
        """
    
    async def get_response_body(
        self, request_id: str
    ) -> dict:
        """获取响应体（含 Base64 编码的二进制响应）"""
        try:
            result = await self.cdp.send(
                "Network.getResponseBody",
                {"requestId": request_id}
            )
            return {
                "body":          result["body"],
                "base64_encoded":result.get("base64Encoded", False)
            }
        except Exception:
            return {"body": "", "base64_encoded": False}
```

### 6.4 LLM 浏览器操控 Agent

```python
class BrowserControlAgent:
    """
    LLM 驱动的浏览器操控，智能识别和触发交互元素
    """
    
    INTERACTION_PROMPT = """
你是前端交互分析专家。给定当前页面截图和 DOM 信息，
识别所有可能触发 API 请求的交互元素，并生成操作序列。

优先级（从高到低）：
1. 登录/注册表单（触发认证接口）
2. 数据查询/搜索框（触发查询接口）
3. 新增/编辑/删除按钮（触发操作接口）
4. 文件上传控件（触发上传接口）
5. 下拉菜单/Tab 切换（触发懒加载接口）
6. 分页控件（触发列表接口）

对每个交互元素输出：
{
  "element_type": "button|input|select|form",
  "selector": "CSS选择器",
  "action": "click|fill|select",
  "fill_value": "输入值（如有）",
  "expected_api_type": "auth|query|operation|upload|search",
  "priority": 1-10,
  "description": "操作说明"
}
"""
    
    async def generate_interaction_plan(
        self,
        page: Page,
        already_captured: list[str]   # 已捕获接口列表，避免重复
    ) -> list[InteractionAction]:
        
        screenshot = await page.screenshot(full_page=False)
        dom_summary = await self._extract_dom_summary(page)
        
        response = await llm.ainvoke([
            SystemMessage(content=self.INTERACTION_PROMPT),
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64encode(screenshot).decode()}"}},
                {"type": "text", "text": f"DOM摘要：{dom_summary}\n已捕获接口：{already_captured}"}
            ])
        ])
        
        return self._parse_actions(response.content)
    
    async def execute_with_capture(
        self,
        page: Page,
        action: InteractionAction,
        cdp: CDPInterceptor
    ) -> list[CapturedRequest]:
        """执行交互操作，返回触发的 API 请求"""
        
        # 执行前清空缓存
        await page.evaluate("window.__captured_requests = []")
        captured = []
        
        # 执行操作
        if action.action == "click":
            await page.click(action.selector, timeout=5000)
        elif action.action == "fill":
            await page.fill(action.selector, action.fill_value)
        elif action.action == "select":
            await page.select_option(action.selector, action.fill_value)
        
        # 等待网络请求
        await page.wait_for_load_state("networkidle", timeout=5000)
        
        # 获取 JS 钩子捕获的请求
        js_captured = await page.evaluate(
            "window.__captured_requests || []"
        )
        
        return [CapturedRequest(**r) for r in js_captured]
```

### 6.5 JS Bundle 解析器

```python
class JSBundleAnalyzer:
    """
    解析前端 JS Bundle，提取路由表和 API 调用
    支持：Webpack、Vite、Rollup 产物
    """
    
    # 正则模式库
    PATTERNS = {
        # API 路径提取
        "api_path_v1":  r'["\'](/api/v\d+/[a-zA-Z0-9/_-]+)["\']',
        "api_path_v2":  r'["\'](/[a-zA-Z0-9-]+/[a-zA-Z0-9/_-]+(?:\{[^}]+\})?)["\']',
        "fetch_call":   r'fetch\(["\']([^"\']+)["\']',
        "axios_call":   r'axios\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        "request_call": r'request(?:\.(?:get|post|put|delete))?\(["\']([^"\']+)["\']',
        
        # Vue Router 路由表
        "vue_router":   r'path:\s*["\']([^"\']+)["\'].*?component',
        
        # React Router
        "react_router": r'<Route[^>]+path=["\']([^"\']+)["\']',
        
        # Next.js API 路由
        "nextjs_api":   r'pages/api/([a-zA-Z0-9/_-]+)',
        
        # Axios baseURL
        "base_url":     r'baseURL:\s*["\']([^"\']+)["\']',
        
        # 环境变量中的 API 地址
        "env_api":      r'VUE_APP_API|REACT_APP_API|NEXT_PUBLIC_API',
    }
    
    async def analyze(
        self,
        js_urls: list[str],
        base_url: str
    ) -> list[StaticInterface]:
        """
        分析步骤：
        1. 下载所有 JS 文件（并行）
        2. 尝试解析 Sourcemap（获取原始源码）
        3. 正则提取所有 API 路径
        4. LLM 分析路径语义，推断接口类型
        5. 去重合并，输出标准化接口列表
        """
    
    async def extract_with_sourcemap(
        self, js_url: str
    ) -> str:
        """
        尝试获取并解析 sourcemap：
        1. 检查 js 文件末尾的 //# sourceMappingURL
        2. 下载 .map 文件
        3. 使用 source-map 库还原原始源码
        4. 返回可读性更高的源码（路径命名更语义化）
        """
```

### 6.6 接口分类与标准化

```python
class InterfaceClassifier:
    """
    Few-Shot 接口类型分类（LLM 辅助）
    """
    
    INTERFACE_TYPES = {
        "auth":        "认证类（登录/注销/刷新Token/注册）",
        "query":       "查询类（列表/详情/统计/导出）",
        "operation":   "操作类（增删改，含越权测试重点）",
        "upload":      "文件处理类（上传/下载/预览）",
        "search":      "搜索类（含搜索框，SQL注入/XSS重点）",
        "webhook":     "回调/通知类",
        "config":      "配置类（系统设置/参数管理）",
        "admin":       "管理员接口（高权限，重点关注）",
    }
    
    CLASSIFICATION_PROMPT = """
根据以下接口信息，判断其类型（只能选择一种）。
重点关注参数名称中是否包含权限相关词汇（userId, roleId, tenantId, orgId）。

接口信息：
  路径: {path}
  方法: {method}
  参数: {params}
  触发场景: {trigger}

可选类型: auth | query | operation | upload | search | webhook | config | admin

输出JSON: {
  "type": "类型",
  "confidence": 0.0~1.0,
  "privilege_sensitive": true/false,  // 是否含权限敏感参数
  "sensitive_params": ["userId", "roleId"],  // 敏感参数列表
  "test_priority": 1~10  // 渗透测试优先级
}
"""

class InterfaceNormalizer:
    """将原始捕获的请求标准化为统一接口格式"""
    
    STANDARD_FORMAT = {
        "interface_id":    "uuid",
        "asset_id":        "关联资产ID",
        "path":            "/api/v2/user/{userId}/orders",
        "path_pattern":    "/api/v2/user/:id/orders",  # 参数占位符统一化
        "method":          "GET|POST|PUT|DELETE|PATCH",
        "api_type":        "query|operation|...",
        "parameters": [{
            "name":        "userId",
            "location":    "path|query|body|header",
            "type":        "string|integer|boolean|array|object",
            "required":    True,
            "example":     "10086",
            "sensitive":   True,  // 是否为权限敏感参数
        }],
        "request_headers": {
            "Content-Type":  "application/json",
            "Authorization": "Bearer {token}",
        },
        "response_schema": {
            "status_200": {"code": 0, "data": {}, "msg": "success"},
        },
        "auth_required":   True,
        "trigger_scenario":"点击订单列表页面",
        "privilege_sensitive": True,
        "test_priority":   9,
        "crawl_method":    "dynamic|static|cdp",
        "version":         1,
        "crawled_at":      "2024-01-01T00:00:00Z",
    }
```
