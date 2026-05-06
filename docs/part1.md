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
