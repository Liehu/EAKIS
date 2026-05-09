# AI 赋能攻击面探测系统 — 技术设计文档

**版本**：v2.0.0  
**状态**：草稿 / 内部评审  
**项目周期**：24 个月（分两阶段）  
**保密级别**：内部使用

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构设计](#2-系统架构设计)
3. [M1 情报采集模块](#3-m1-情报采集模块)
4. [M2 关键词引擎模块](#4-m2-关键词引擎模块)
5. [M3 资产发现模块](#5-m3-资产发现模块)
6. [M4 智能接口爬取模块](#6-m4-智能接口爬取模块)
7. [M5 自动渗透测试模块](#7-m5-自动渗透测试模块)
8. [M6 报告生成模块](#8-m6-报告生成模块)
9. [API 设计规范](#9-api-设计规范)
10. [数据模型设计](#10-数据模型设计)
11. [核心提示词设计](#11-核心提示词设计)
12. [目录结构](#12-目录结构)
13. [测试样例](#13-测试样例)
14. [功能开发进度表](#14-功能开发进度表)
15. [部署与运维](#15-部署与运维)
16. [安全合规](#16-安全合规)

---

## 1. 项目概述

### 1.1 背景与问题

当前攻击面探测领域存在四类核心痛点：

| 问题类型 | 现状描述 | 量化影响 |
|---------|---------|---------|
| 靶标关键词维度单一 | 仅含企业名称，未利用 OSINT 多源情报 | 关联资产遗漏率 > 60% |
| 资产归属人工核验 | 依赖人工判断 title / IP 等特征 | 筛选成本占探测周期 40% |
| 接口爬取覆盖不全 | 固定爬虫规则，无法适配动态交互场景 | 接口漏爬率 > 35% |
| 漏洞测试缺乏靶向性 | 未结合接口特征设计测试用例 | 无效测试占比 > 40% |

### 1.2 核心目标

构建融合**开源情报分析、大模型浏览器操控、自动化测试引擎**的智能攻击面探测系统，打通：

```
关键词生成 → 资产关联 → 接口爬取 → 漏洞测试 → 报告输出
```

全链路实现智能化，将探测周期从传统 5-10 天压缩至 **2-3 天**，整体效率提升 **≥ 80%**。

### 1.3 预期指标

| 指标 | 传统方法 | 目标值 |
|-----|---------|-------|
| 关联资产搜索覆盖率 | 基准 | 提升 70% |
| 靶标资产误判率 | ~40% | ≤ 15% |
| 动态交互接口识别率 | ~65% | ≥ 90% |
| 接口漏爬率 | > 35% | ≤ 10% |
| 核心漏洞检测覆盖率 | ~60% | ≥ 95% |
| 无效测试占比 | ~40% | ≤ 15% |
| 报告生成时间 | 4 小时/份 | ≤ 30 分钟/份 |
| 全流程探测周期 | 5-10 天 | 2-3 天 |

---

## 2. 系统架构设计

### 2.1 总体架构

系统采用**微服务 + 事件驱动**架构，共分七层：

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端交互层 (React)                         │
│              任务管理 │ 实时监控 │ 报告预览 │ 配置中心              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                      API 网关层 (FastAPI)                         │
│            鉴权 │ 限流 │ 路由 │ OpenAPI 文档 │ 审计日志             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                   Agent 编排层 (LangGraph)                        │
│        Stateful Graph │ 条件路由 │ 人工干预节点 │ 状态持久化          │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬───────────────────┘
   │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼
 M1情   M2关   M3资   M4接   M5渗   M6报   边界
 报采   键词   产发   口爬   透测   告生   守卫
 集     引擎   现     取     试     成     层
└─────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        基础设施层                                  │
│  PostgreSQL │ Qdrant │ Redis │ Kafka │ MinIO │ Prometheus        │
└─────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        LLM 推理层                                  │
│     Qwen-7B (本地 INT8) │ GPT-4o (云端备用) │ 推理缓存             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent 编排流程

系统包含 10 个 Agent 节点，形成两条并行主路径和多个反馈回路：

```
                     ┌────────────────────┐
                     │  任务输入 / 配置中心  │
                     └─────────┬──────────┘
                               │
                     ┌─────────▼──────────┐
                     │ 1. 数据源定义 Agent  │◄──────── RAG 知识库反馈
                     └─────────┬──────────┘
                               │
              ┌────────────────▼──────────────────┐
              │        2. 搜索语法生成 Agent (DSL)   │◄─ 关键词优化反馈
              └──────────┬────────────────────────┘
                         │
         ┌───────────────┼──────────────────┐
         │               │                  │
         ▼               ▼                  ▼
   [通用搜索引擎]    [空间资产引擎]      [OSINT 爬虫]
   新闻/招投标      Fofa/Hunter         官网/ICP
         │               │                  │
         └───────────────┼──────────────────┘
                         │
                ┌────────▼────────┐
                │ 3. 数据爬取 Agent│
                └────────┬────────┘
                         │
                ┌────────▼────────┐
                │ 4. 数据清洗 Agent│──► 增量写入 RAG
                └────┬───────┬───┘
                     │       │
                     ▼       ▼
            ┌────────┐  ┌────────────────────┐
            │5.摘要  │  │ 7. 资产相关性        │
            │  Agent │  │    评估 Agent        │
            └───┬────┘  └────────┬───────────┘
                │                │
                ▼                ▼
        ┌───────────────┐  ┌─────────────────┐
        │6. 关键词生成   │  │8. 智能接口爬取   │
        │   Agent       │  │   Agent          │
        └───┬──────┬────┘  └────────┬────────┘
            │      │                │
            │      └───► DSL 反馈   │
            │                       ▼
            │             ┌─────────────────┐
            │             │ 9. 自动渗透测试  │
            │             │    Agent (Phase2)│
            │             └────────┬────────┘
            │                      │
            └──────────────────────┤
                                   ▼
                         ┌─────────────────┐
                         │ 10. 报告输出     │──► RAG 知识库更新
                         │    Agent         │
                         └─────────────────┘
```

### 2.3 核心技术栈

| 层次 | 组件 | 版本 | 用途 |
|-----|------|------|-----|
| Agent 编排 | LangGraph | 0.2.x | 有状态 Agent 图、条件路由、Human-in-the-Loop |
| LLM 推理 | Qwen2.5-7B-Instruct | latest | 本地推理（INT8 量化，<4GB VRAM） |
| LLM 备用 | GPT-4o via Azure | latest | 云端高精度任务 |
| 浏览器操控 | Playwright | 1.44 | 动态页面交互 |
| CDP 捕获 | Chrome DevTools Protocol | - | 精细流量拦截 |
| 向量存储 | Qdrant | 1.9 | 接口特征 / 情报 RAG 嵌入 |
| RAG 框架 | LlamaIndex | 0.10 | 知识库构建与检索 |
| 关系数据库 | PostgreSQL | 16 | 任务/资产/漏洞持久化 |
| 消息队列 | Apache Kafka | 3.7 | Agent 解耦、事件驱动 |
| 任务调度 | Celery + Redis | 5.3 | 异步任务队列 |
| Web 框架 | FastAPI | 0.111 | REST API + WebSocket |
| 漏洞扫描 | Nuclei + SQLMap | latest | 自动化漏洞检测 |
| 前端 | React 18 + TypeScript | - | 操作界面 |
| 监控 | Prometheus + Grafana | - | 可观测性 |
| 日志 | OpenTelemetry + ELK | - | 分布式追踪 |
| 容器 | Docker + Kubernetes | - | 部署编排 |

### 2.4 关键设计决策

#### 2.4.1 为何选择 LangGraph 而非传统 LangChain Agents

| 维度 | LangChain Agents | LangGraph |
|-----|-----------------|-----------|
| 状态管理 | 无持久化状态 | TypedDict 全局状态，支持断点恢复 |
| 流程控制 | 线性或简单分支 | 有向图，支持循环、条件边、并行 |
| 调试能力 | 难以追踪中间状态 | 内置 LangSmith 追踪，可逐步回放 |
| 人工干预 | 不原生支持 | interrupt_before/interrupt_after 节点 |
| 适配本项目 | ❌ 反馈闭环难实现 | ✅ 完美支持多反馈回路 |

#### 2.4.2 CDP 层 vs 纯 Playwright 拦截

```
纯 Playwright 方案：
  覆盖范围: XHR / Fetch
  遗漏场景: WebSocket 推送、SSE 流、gRPC-Web、Service Worker 拦截请求

CDP 方案（本项目）：
  覆盖范围: 所有 HTTP 流量 + WebSocket + 二进制协议
  关键能力: Network.getResponseBody、Page.addScriptToEvaluateOnNewDocument
  额外收益: 获取完整请求/响应体，包含 Base64 编码的二进制响应
```

#### 2.4.3 模型选型策略

```python
# 不同任务的模型路由策略
MODEL_ROUTING = {
    "keyword_extraction":    "qwen2.5-7b",    # 低延迟，本地推理
    "asset_assessment":      "qwen2.5-7b",    # 结构化判断，本地推理
    "interface_recognition": "qwen2.5-7b",    # Few-Shot 分类，本地推理
    "vuln_case_generation":  "gpt-4o",        # 需要高推理能力
    "llm_judge_vuln":        "gpt-4o",        # 漏洞验证准确性要求高
    "report_generation":     "gpt-4o",        # 长文本生成质量要求高
    "report_quality_score":  "qwen2.5-7b",    # 评分任务，本地推理
}
```

---

## 3. M1 情报采集模块

### 3.1 模块概述

**职责**：从多源开放数据中自动采集靶标企业相关情报，为后续关键词生成提供原始数据。

**输入**：靶标企业名称、行业类型、任务配置（时间窗口、地域范围）  
**输出**：原始情报数据集（含来源标注、采集时间、可信度评分）

### 3.2 子模块设计

#### 3.2.1 数据源定义 Agent (OSINT-DATASOURCE)

**功能**：根据靶标信息和 RAG 历史经验，智能选择最优数据源组合。

```python
class DataSourceAgent:
    """
    决策逻辑：
    1. 查询 RAG 知识库获取同行业历史有效数据源
    2. 根据靶标规模（大/中/小企业）调整采集策略
    3. 输出优先级排序的数据源列表
    """
    
    # 数据源分类
    SOURCE_CATEGORIES = {
        "news":        ["百度新闻", "微信公众号", "36氪", "虎嗅", "钛媒体"],
        "official":    ["企业官网", "GitHub 组织页", "技术博客"],
        "legal":       ["ICP 备案查询", "工商信息（天眼查/企查查）", "招投标公告"],
        "security":    ["漏洞库（CNVD/NVD）", "安全公告", "CVE 数据库"],
        "asset_engine":["Fofa", "Hunter", "Shodan", "Censys", "ZoomEye"],
    }
    
    def select_sources(self, company_profile: dict) -> list[DataSource]:
        """
        Returns:
            按优先级排序的数据源列表，每个包含：
            - source_id: 数据源标识
            - priority: 1-10 优先级
            - expected_yield: 预期有效情报比例
            - rate_limit: 请求频率限制
        """
```

#### 3.2.2 搜索语法生成 Agent (OSINT-DSL)

**功能**：基于 LLM + 预定义规则，为不同平台生成最优搜索语法（DSL）。

**Fofa DSL 生成示例**：

```python
# 输入关键词: ["XX支付", "Spring Boot", "微服务", "XY科技"]
# 生成的 Fofa DSL:
dsl_examples = {
    "domain_search": 'domain="xx-payment.com" || domain="xy-tech.com"',
    "title_search":  'title="XX支付" && country="CN"',
    "header_search": 'header="X-Powered-By: Spring Boot" && title="XX"',
    "cert_search":   'cert="xx-payment" && port="443"',
    "icon_search":   'icon_hash="-123456789"',  # favicon hash
}

# Hunter DSL:
hunter_dsl = 'domain.suffix="xx-payment.com" && web.title="支付"'

# Shodan DSL:
shodan_dsl = 'org:"XX Payment Technology" http.title:"支付"'
```

**DSL 反馈优化机制**：

```
当资产检索结果满足以下条件时，触发 DSL 重新生成：
  - 返回资产数 < 10（关键词可能过于严格）
  - 靶标资产命中率 < 20%（关键词可能过于宽泛）
  - 误判率 > 30%（需要添加过滤条件）

反馈信息写入 RAG 知识库：
  {
    "company_type": "金融科技",
    "effective_dsl_patterns": ["cert_search", "icon_search"],
    "ineffective_dsl_patterns": ["title_search"],
    "optimization_notes": "金融类企业建议优先使用证书和 favicon hash 检索"
  }
```

#### 3.2.3 数据爬取 Agent (OSINT-CRAWLER)

**功能**：执行实际的多源并行数据采集，内置反爬对抗策略。

**爬取策略设计**：

```python
class CrawlerConfig:
    # 并发控制
    MAX_CONCURRENT_SOURCES = 5      # 最大并发数据源数
    MAX_CONCURRENT_PAGES   = 10     # 每个数据源最大并发页面数
    
    # 反爬对抗
    REQUEST_DELAY_MIN   = 1.5       # 最小请求间隔（秒）
    REQUEST_DELAY_MAX   = 4.0       # 最大请求间隔（秒，随机）
    RETRY_MAX_ATTEMPTS  = 3         # 最大重试次数
    RETRY_BACKOFF       = 2.0       # 重试退避系数
    
    # 代理配置
    PROXY_ROTATION      = True      # 开启 IP 轮换
    PROXY_POOL_SIZE     = 50        # 代理池大小
    PROXY_HEALTH_CHECK  = True      # 代理健康检查
    
    # User-Agent 池
    UA_ROTATION         = True
    UA_POOL_SIZE        = 200       # UA 池大小
    
    # 浏览器指纹
    FINGERPRINT_RANDOMIZE = True    # 随机化 Canvas/WebGL 指纹
    VIEWPORT_RANDOMIZE    = True    # 随机化视口尺寸
```

**数据采集 Kafka 事件**：

```python
# 爬取完成后发布事件
CRAWL_COMPLETE_EVENT = {
    "topic":   "osint.crawl.complete",
    "payload": {
        "task_id":       "uuid",
        "source_type":   "news|official|legal|asset_engine",
        "source_name":   "百度新闻",
        "items_count":   127,
        "raw_data_path": "s3://attackscope/tasks/{task_id}/raw/{timestamp}.json",
        "crawl_duration": 45.2,    # 秒
        "success_rate":   0.94,
    }
}
```

#### 3.2.4 数据清洗 Agent (OSINT-CLEANER)

**功能**：对原始情报进行去重、降噪、质量评分，输出结构化情报片段。

**清洗流水线**：

```
原始文本
  ├─► 语言检测 (langdetect)
  ├─► HTML/Markdown 标签去除
  ├─► 重复内容检测 (MinHash LSH, Jaccard ≥ 0.85 视为重复)
  ├─► 质量评分
  │     ├─ 文本长度 (< 50 字符 → 丢弃)
  │     ├─ 信息密度 (停用词占比 > 60% → 低质量)
  │     └─ 时效性 (发布时间 > 2 年 → 降权)
  ├─► 实体预识别 (spaCy NER: 组织/地点/技术词)
  └─► 结构化输出
        {
          "content":     "清洗后正文",
          "source":      "来源标注",
          "published_at": "发布时间",
          "quality_score": 0.85,  // 0.0~1.0
          "entities":    ["XX支付", "Spring Boot"],  // 预识别实体
          "checksum":    "md5/sha256"  // 去重用
        }
```

**增量 RAG 写入**（改进点）：

```python
# 每批清洗完成后，立即写入 RAG 知识库片段
# 不再等待报告生成阶段才更新
async def on_batch_clean_complete(batch: list[CleanedDoc]):
    embeddings = await embed_model.aembed_documents(
        [doc.content for doc in batch]
    )
    await rag_store.aadd_texts(
        texts=[doc.content for doc in batch],
        embeddings=embeddings,
        metadatas=[{"source": doc.source, "task_id": doc.task_id} for doc in batch]
    )
```

### 3.3 模块内部 API

```python
# 模块内部 Python 接口（非 HTTP API）

class IntelligenceModule:
    
    async def start_collection(
        self,
        task_id: str,
        company_name: str,
        config: CollectionConfig
    ) -> CollectionJob:
        """启动情报采集任务，返回 Job 对象用于状态跟踪"""
    
    async def get_collection_status(
        self,
        job_id: str
    ) -> CollectionStatus:
        """获取采集进度，包含各数据源的采集状态"""
    
    async def get_cleaned_intel(
        self,
        task_id: str,
        min_quality: float = 0.6,
        limit: int = 500
    ) -> list[CleanedDocument]:
        """获取清洗后的情报列表"""
    
    async def search_rag(
        self,
        query: str,
        top_k: int = 10,
        filter: dict = None
    ) -> list[RagResult]:
        """检索 RAG 知识库"""
```

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
