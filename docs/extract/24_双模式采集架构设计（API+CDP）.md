# 双模式采集架构设计（API + CDP）

**版本**：v1.0.0
**状态**：设计评审
**关联模块**：M1 情报采集模块
**前置文档**：[01_02_项目概述与系统架构设计.md](01_02_项目概述与系统架构设计.md)、[03_情报采集模块.md](03_情报采集模块.md)

---

## 目录

1. [问题分析与设计目标](#1-问题分析与设计目标)
2. [总体架构](#2-总体架构)
3. [核心组件设计](#3-核心组件设计)
4. [API 适配器层](#4-api-适配器层)
5. [CDP 增强方案](#5-cdp-增强方案)
6. [双模式调度器](#6-双模式调度器)
7. [降级与反馈机制](#7-降级与反馈机制)
8. [配置体系](#8-配置体系)
9. [数据源分类与模式映射](#9-数据源分类与模式映射)
10. [现有代码改造计划](#10-现有代码改造计划)
11. [关键接口定义](#11-关键接口定义)

---

## 1. 问题分析与设计目标

### 1.1 当前实现的问题

对现有代码（`GenericEngineScraper`、`CDPScraper`）的分析发现以下问题：

| 问题 | 当前实现 | 影响 |
|------|---------|------|
| API / CDP 互不感知 | `GenericEngineScraper` 仅支持 API，`CDPScraper` 仅支持 CDP | 无法按需切换模式 |
| API 层缺少第三方搜索 API | 搜索引擎 API 字段仅标记 `enabled`/`api_key` | 无 SerpAPI/Serper 等聚合搜索支持 |
| CDP 降级逻辑空缺 | `CDPScraper._should_fallback()` 返回 `True` 但降级体为空 | 失败后直接返回空结果 |
| 配置分散 | `engines.yaml`（API+CDP 混写）、`crawler.yaml`（CDP 专写）、`engine_specs/`（资产引擎） | 同一引擎配置跨三处维护 |
| 反爬策略与采集模式耦合 | `AntiCrawlMiddleware` 仅 CDP 调用 | API 模式无统一的限速/重试/代理管理 |

### 1.2 设计目标

1. **每个数据源独立支持 API 和 CDP 两种模式**，可按数据源、按任务自由选择
2. **API 优先策略**：搜索引擎走第三方搜索 API（SerpAPI / Serper），资产引擎走官方 API
3. **CDP 作为降级或补充**：API 不可用、需要 JS 渲染、需要深度交互时启用
4. **统一调度入口**：调用方无需关心底层模式，由调度器根据配置和运行状态自动决策
5. **闭环反馈**：采集结果写入 RAG，指导后续数据源选择和 DSL 优化

---

## 2. 总体架构

### 2.1 分层设计

```
┌──────────────────────────────────────────────────────────────┐
│                    调用层 (M1 IntelligenceModule)              │
│         start_collection() / get_collection_status()          │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              DualModeScheduler (双模式调度器)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              SourceRouter (数据源路由)                 │    │
│  │  根据 engine_name + 任务配置 → 选择 API / CDP / BOTH  │    │
│  └──────────────────┬───────────────┬───────────────────┘    │
│                     │               │                        │
│         ┌───────────▼───┐   ┌───────▼────────┐              │
│         │  API Adapter  │   │ CDP Adapter   │              │
│         │    Layer      │   │    Layer       │              │
│         └───────┬───────┘   └───────┬────────┘              │
└─────────────────┼───────────────────┼────────────────────────┘
                  │                   │
    ┌─────────────▼─────┐   ┌────────▼────────┐
    │  SerpAPIAdapter   │   │ CDPScraper      │
    │  SerperAdapter    │   │  (Playwright)   │
    │  FofaAPIAdapter   │   │  + AntiCrawl    │
    │  HunterAPIAdapter │   │  + Stealth      │
    │  DirectHttpAdapter│   │                 │
    └───────────────────┘   └─────────────────┘
                  │                   │
    ┌─────────────▼───────────────────▼─────────┐
    │         AntiCrawlMiddleware (共享)          │
    │     代理轮换 / UA 轮换 / 限速 / 重试        │
    └───────────────────────────────────────────┘
```

### 2.2 数据流

```
用户发起采集任务
      │
      ▼
IntelligenceModule.start_collection(task_id, company, config)
      │
      ▼
DataSourceAgent → 选择数据源列表 (含模式偏好)
      │
      ▼
DSLGenerator → 为每个引擎生成查询语法
      │
      ▼
DualModeScheduler.dispatch(queries_with_source)
      │
      ├─► [API 模式] ApiAdapter.scrape() → 标准化 RawDocument
      │       │ 失败
      │       ▼ 降级
      │   CDPAdapter.scrape()
      │
      ├─► [CDP 模式] CDPAdapter.scrape() → 标准化 RawDocument
      │
      └─► [BOTH 模式] 并行执行两种，合并去重
              │
              ▼
      RawDocument 列表 → CleanerAgent → RAG 写入
```

---

## 3. 核心组件设计

### 3.1 统一采集接口

所有采集模式（API / CDP）都通过统一接口输出 `RawDocument`，现有 `BaseScraper` 接口不变。

```python
# src/intelligence/services/base.py — 保持不变
class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, query: str, config: CrawlConfig) -> list[RawDocument]:
        ...
```

### 3.2 采集模式枚举

```python
# src/intelligence/models.py — 新增
from enum import Enum

class CollectMode(str, Enum):
    """采集模式。"""
    API = "api"          # 仅 API 模式
    CDP = "cdp"          # 仅 CDP 模式
    BOTH = "both"        # 两种并行，合并结果
    AUTO = "auto"        # 调度器自动决策（默认）
```

### 3.3 采集结果元数据

在 `RawDocument.metadata` 中记录采集模式信息，便于后续分析和降级决策：

```python
# metadata 示例
{
    "collect_mode": "api",           # 实际使用的采集模式
    "adapter_type": "serpapi",       # 适配器类型
    "engine_name": "google",         # 目标引擎
    "query": "site:xx.com",          # 实际发送的查询
    "latency_ms": 342,               # 响应延迟
    "total_results": 87,              # 引擎返回的总结果数
    "retrieved_count": 10,           # 本次获取的条数
    "page": 1,                       # 页码
    "is_fallback": false,            # 是否为降级采集
    "fallback_from": null,           # 降级前的模式
    "retry_count": 0,                # 重试次数
}
```

---

## 4. API 适配器层

### 4.1 适配器层次结构

将现有 `GenericEngineScraper` 重构为适配器模式，每个数据源一个适配器实例：

```
BaseScraper (ABC)
├── BaseApiAdapter (ABC)              # API 模式基类
│   ├── SerpApiAdapter               # SerpAPI 聚合搜索
│   ├── SerperApiAdapter             # Serper 搜索 API
│   ├── AssetEngineApiAdapter        # 资产引擎通用 API (FOFA/Hunter/Shodan...)
│   ├── DirectHttpAdapter            # 通用 HTTP API（现有 GenericEngineScraper 能力）
│   └── StubApiAdapter              # 测试用
└── CDPScraper                       # CDP 模式（现有，增强反检测）
```

### 4.2 BaseApiAdapter

```python
# src/intelligence/scrapers/api/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.intelligence.models import CollectMode, RawDocument
from src.intelligence.services.base import BaseScraper


@dataclass
class ApiAdapterConfig:
    """API 适配器配置。"""
    api_key: str = ""
    api_url: str = ""
    auth_type: str = "bearer"       # bearer / basic / query_param / custom
    email: str = ""                 # email+apikey 模式使用
    timeout: float = 30.0
    max_results: int = 100
    rate_limit: float = 1.0         # 每秒请求数
    retry_attempts: int = 3
    retry_backoff: float = 2.0
    query_encoding: str = "none"    # none / base64 / url
    extra_params: dict[str, Any] = None


class BaseApiAdapter(BaseScraper, ABC):
    """API 模式适配器基类。"""

    adapter_type: str = "base"

    def __init__(self, engine_name: str, config: ApiAdapterConfig) -> None:
        self.engine_name = engine_name
        self._config = config

    @abstractmethod
    async def _build_request(
        self, query: str, page: int = 1
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        """构建 HTTP 请求。返回 (url, params, headers)。"""

    @abstractmethod
    def _parse_response(self, data: dict) -> list[dict]:
        """解析 API 响应，提取结果列表。"""

    @abstractmethod
    def _format_document(self, item: dict, query: str) -> RawDocument | None:
        """将单条 API 结果转换为 RawDocument。"""

    async def scrape(
        self, query: str, config: Any = None
    ) -> list[RawDocument]:
        """执行 API 采集。"""
        import httpx

        all_docs: list[RawDocument] = []
        page = 1
        max_pages = (self._config.max_results + 9) // 10  # 每页约 10 条

        while len(all_docs) < self._config.max_results and page <= max_pages:
            url, params, headers = await self._build_request(query, page)

            try:
                async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    data = response.json()
            except Exception as e:
                raise ScrapeError(
                    engine=self.engine_name,
                    mode=CollectMode.API,
                    message=str(e),
                )

            items = self._parse_response(data)
            if not items:
                break

            for item in items:
                doc = self._format_document(item, query)
                if doc:
                    doc.metadata.update({
                        "collect_mode": "api",
                        "adapter_type": self.adapter_type,
                        "engine_name": self.engine_name,
                        "query": query,
                        "page": page,
                    })
                    all_docs.append(doc)

            page += 1

        return all_docs[:self._config.max_results]
```

### 4.3 SerpApiAdapter — 聚合搜索引擎 API

```python
# src/intelligence/scrapers/api/serpapi_adapter.py

class SerpApiAdapter(BaseApiAdapter):
    """SerpAPI 适配器 — 聚合 Google/Bing/Baidu 搜索结果。

    文档：https://serpapi.com/search-api

    支持引擎：google, bing, baidu, yahoo, yandex
    费用：Google $50/5000次, Bing $35/5000次, Baidu $15/5000次
    """

    adapter_type = "serpapi"
    BASE_URL = "https://serpapi.com/search"

    # SerpAPI engine → 本地引擎名映射
    ENGINE_MAP = {
        "google": "google",
        "bing": "bing",
        "baidu": "baidu",
    }

    async def _build_request(self, query: str, page: int = 1):
        serp_engine = self.ENGINE_MAP.get(self.engine_name, "google")
        params = {
            "engine": serp_engine,
            "q": query,
            "api_key": self._config.api_key,
            "start": (page - 1) * 10,
            "num": 10,
            "hl": "zh-cn" if self.engine_name == "baidu" else "en",
        }
        return self.BASE_URL, params, {}


    def _parse_response(self, data: dict) -> list[dict]:
        # SerpAPI 统一返回 organic_results 字段
        return data.get("organic_results", [])


    def _format_document(self, item: dict, query: str) -> RawDocument | None:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        if not title or not link:
            return None
        return RawDocument(
            content=f"标题: {title}\n链接: {link}\n摘要: {snippet}",
            source_type=SourceCategory.NEWS,
            source_name=f"SerpAPI-{self.engine_name}",
            source_url=link,
            published_at=datetime.now(timezone.utc),
            metadata={"total_results": item.get("position")},
        )
```

### 4.4 SerperApiAdapter

```python
# src/intelligence/scrapers/api/serper_adapter.py

class SerperApiAdapter(BaseApiAdapter):
    """Serper API 适配器 — Google 搜索 API。

    文档：https://serper.dev/
    费用：$50/50000次（性价比高于 SerpAPI 的 Google）
    优势：支持结构化 knowledge graph、answer box 提取
    """

    adapter_type = "serper"
    BASE_URL = "https://google.serper.dev/search"


    async def _build_request(self, query: str, page: int = 1):
        params = {
            "q": query,
            "page": page,
            "num": 10,
            "gl": "cn",     # 地理位置中国
            "hl": "zh-cn",  # 语言中文
        }
        headers = {
            "X-API-KEY": self._config.api_key,
            "Content-Type": "application/json",
        }
        # Serper 使用 JSON body 而非 query params
        return self.BASE_URL, params, headers


    def _parse_response(self, data: dict) -> list[dict]:
        results = data.get("organic", [])
        # 附加 knowledge graph（如果有）
        kg = data.get("knowledgeGraph")
        if kg:
            results.insert(0, {
                "title": kg.get("title", ""),
                "link": kg.get("website", ""),
                "snippet": kg.get("description", ""),
                "_source": "knowledge_graph",
            })
        return results
```

### 4.5 AssetEngineApiAdapter — 资产引擎通用 API

```python
# src/intelligence/scrapers/api/asset_engine_adapter.py

class AssetEngineApiAdapter(BaseApiAdapter):
    """资产引擎 API 适配器 — 复用现有 engine_specs 配置。

    支持：FOFA、Hunter、Shodan、Censys、ZoomEye
    与现有 GenericEngineScraper._real_search() 功能等价，
    但增加了统一的重试、限速、元数据记录。
    """

    adapter_type = "asset_engine"

    def __init__(self, engine_name: str, config: ApiAdapterConfig) -> None:
        super().__init__(engine_name, config)
        specs = load_engine_specs()
        self._spec = specs.get(engine_name)

    async def _build_request(self, query: str, page: int = 1):
        if not self._spec:
            raise ScrapeError(self.engine_name, CollectMode.API, "未找到引擎配置")

        encoded = encode_query(query, self._config.query_encoding)
        params = {self._spec.query_param: encoded}

        # 认证
        headers = {}
        if self._config.api_key:
            auth_type = self._config.auth_type or self._spec.auth_type
            if "email+apikey" in auth_type:
                credentials = base64.b64encode(
                    f"{self._config.email}:{self._config.api_key}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"
            elif "bearer" in auth_type:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            elif "apikey" in auth_type:
                params["apikey"] = self._config.api_key

        # 分页
        if self._spec.pagination:
            if self._spec.pagination.page_param:
                params[self._spec.pagination.page_param] = page
            if self._spec.pagination.size_param:
                params[self._spec.pagination.size_param] = self._config.max_results

        return self._spec.search_url, params, headers

    def _parse_response(self, data: dict) -> list[dict]:
        path = self._spec.response_path
        if not path:
            return [data] if isinstance(data, dict) else []
        current = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return []
        return current if isinstance(current, list) else []

    def _format_document(self, item: dict, query: str) -> RawDocument | None:
        import json
        return RawDocument(
            content=json.dumps(item, ensure_ascii=False),
            source_type=SourceCategory.ASSET_ENGINE,
            source_name=self._spec.display_name if self._spec else self.engine_name,
            source_url=self._spec.search_url if self._spec else "",
            published_at=datetime.now(timezone.utc),
        )
```

### 4.6 API 适配器工厂

```python
# src/intelligence/scrapers/api/__init__.py

from src.intelligence.models import CollectMode


class ApiAdapterFactory:
    """根据引擎名和配置创建对应的 API 适配器。"""

    # 引擎名 → 适配器类映射
    _registry: dict[str, type[BaseApiAdapter]] = {}

    @classmethod
    def register(cls, engine_name: str, adapter_class: type[BaseApiAdapter]) -> None:
        cls._registry[engine_name] = adapter_class

    @classmethod
    def create(
        cls,
        engine_name: str,
        api_config: ApiAdapterConfig,
    ) -> BaseApiAdapter:
        adapter_cls = cls._registry.get(engine_name)
        if adapter_cls:
            return adapter_cls(engine_name, api_config)

        # 默认尝试资产引擎适配器
        try:
            return AssetEngineApiAdapter(engine_name, api_config)
        except Exception:
            raise ValueError(f"未知引擎: {engine_name}，无对应 API 适配器")


# 注册默认适配器
ApiAdapterFactory.register("google", SerpApiAdapter)
ApiAdapterFactory.register("bing", SerpApiAdapter)
ApiAdapterFactory.register("baidu", SerpApiAdapter)
# 如果配置了 Serper API Key，也可用于 Google
# ApiAdapterFactory.register("google", SerperApiAdapter)
```

---

## 5. CDP 增强方案

### 5.1 现有 CDP 实现的不足

当前 `CDPScraper` 使用原生 Playwright + `chromium.launch()`，存在以下检测风险：

| 检测点 | 当前状态 | 改进方案 |
|-------|---------|---------|
| `navigator.webdriver` | 未处理 | 使用 `playwright-stealth` 或手动 patch |
| CDP 调试端口 | 暴露 | 使用 `--remote-debugging-port=0` 或管道模式 |
| Canvas 指纹 | 已注入简单噪声 | 改用确定性噪声 + 真实指纹库 |
| TLS 指纹 | Chromium 默认指纹 | 低优先级 — 搜索引擎 API 优先，CDP 仅降级场景 |
| 行为模式 | 固定延迟 | 加入人类行为模拟（鼠标/滚动/随机停顿） |

### 5.2 CDP 增强策略

```
Playwright 原生
     │
     ▼
playwright-stealth 补丁       ← 第一层：消除运行时标志
     │
     ▼
stealth 生成的 Chromium       ← 第二层：使用经过反检测处理的浏览器
     │
     ▼
行为模拟注入                  ← 第三层：鼠标轨迹、滚动、输入节奏
     │
     ▼
AntiCrawlMiddleware           ← 第四层：代理 + UA + 限速（已有）
```

### 5.3 CDPScraper 改造要点

```python
# 改造后的 CDPScraper.__init__ 增加参数

class CDPScraper(BaseScraper):

    def __init__(
        self,
        engine_name: str,
        anti_crawl: AntiCrawlProfile | None = None,
        config: CrawlerConfig | None = None,
        shared_browser: CDPScraperManager | None = None,
        # —— 新增参数 ——
        use_stealth: bool = True,            # 是否注入反检测脚本
        human_behavior: bool = True,         # 是否模拟人类行为
        max_consecutive_empty: int = 3,      # 连续空结果上限，触发降级
    ) -> None:
        ...
```

### 5.4 反检测脚本注入

```python
# src/intelligence/anti_crawl/stealth.py

STEALTH_JS = """
// 1. 移除 webdriver 标志
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// 2. 伪装 Chrome 对象
window.chrome = {
    app: { isInstalled: false, InstallState: { DISABLED: 'disabled' } },
    runtime: { OnInstalledReason: { INSTALL: 'install' }, PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' }, PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' }, PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' }, RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' } },
    csi: () => {},
    loadTimes: () => {},
};

// 3. 伪装权限查询
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// 4. 伪装插件长度
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 5. 伪装语言
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en'],
});
"""


async def inject_stealth_scripts(page: Page) -> None:
    """注入反检测脚本到页面。"""
    await page.add_init_script(STEALTH_JS)
```

### 5.5 人类行为模拟

```python
# src/intelligence/anti_crawl/human_behavior.py

import asyncio
import random


async def human_type(page: Page, selector: str, text: str) -> None:
    """模拟人类打字：随机延迟 + 偶尔退格。"""
    element = await page.query_selector(selector)
    await element.click()
    for char in text:
        await element.type(char, delay=random.randint(50, 150))
        if random.random() < 0.05:  # 5% 概率退格
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await element.type(char, delay=random.randint(50, 150))


async def human_scroll(page: Page, max_scrolls: int = 5) -> None:
    """模拟人类滚动：变速 + 随机停顿。"""
    for _ in range(max_scrolls):
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.5, 2.0))


async def human_mouse_move(page: Page) -> None:
    """模拟随机鼠标移动。"""
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.5))
```

---

## 6. 双模式调度器

### 6.1 核心调度器

```python
# src/intelligence/scrapers/dual_mode_scheduler.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.intelligence.models import CollectMode, RawDocument


class FallbackReason(str, Enum):
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    API_AUTH_ERROR = "api_auth_error"
    API_EMPTY = "api_empty_results"
    CDP_BLOCKED = "cdp_blocked"
    CDP_CAPTCHA = "cdp_captcha"
    CDP_TIMEOUT = "cdp_timeout"


@dataclass
class SourceRoute:
    """单个数据源的路由配置。"""
    engine_name: str
    mode: CollectMode = CollectMode.AUTO
    # AUTO 模式下的优先策略
    preferred: CollectMode = CollectMode.API
    # 允许降级
    allow_fallback: bool = True
    # 降级目标
    fallback_to: CollectMode | None = None


@dataclass
class ScrapeResult:
    """单次采集结果（含模式信息）。"""
    engine_name: str
    mode_used: CollectMode
    documents: list[RawDocument]
    latency_ms: float
    is_fallback: bool = False
    fallback_reason: FallbackReason | None = None
    error: str | None = None


class DualModeScheduler:
    """双模式调度器 — 根据配置和运行状态选择 API / CDP / BOTH。

    用法:
        scheduler = DualModeScheduler(api_factory, cdp_manager)
        scheduler.register_routes([
            SourceRoute("google", mode=CollectMode.AUTO, preferred=CollectMode.API),
            SourceRoute("fofa",   mode=CollectMode.API),
            SourceRoute("baidu",  mode=CollectMode.AUTO, preferred=CollectMode.CDP),
        ])
        results = await scheduler.dispatch([
            ("google", 'site:xx.com "XX支付"'),
            ("fofa",   'domain="xx-payment.com"'),
        ])
    """

    def __init__(
        self,
        api_factory: ApiAdapterFactory,
        cdp_manager: CDPScraperManager | None = None,
        anti_crawl: AntiCrawlMiddleware | None = None,
        fallback_history: FallbackHistory | None = None,
    ) -> None:
        self._api_factory = api_factory
        self._cdp_manager = cdp_manager
        self._anti_crawl = anti_crawl
        self._fallback_history = fallback_history or FallbackHistory()
        self._routes: dict[str, SourceRoute] = {}

    def register_routes(self, routes: list[SourceRoute]) -> None:
        for route in routes:
            self._routes[route.engine_name] = route

    def register_route(self, route: SourceRoute) -> None:
        self._routes[route.engine_name] = route

    async def dispatch(
        self,
        queries: list[tuple[str, str]],  # (engine_name, query)
        crawl_config: Any = None,
    ) -> list[ScrapeResult]:
        """并发调度多个查询，每个查询独立选择模式。"""
        tasks = [
            self._dispatch_one(engine, query, crawl_config)
            for engine, query in queries
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_one(
        self,
        engine_name: str,
        query: str,
        crawl_config: Any = None,
    ) -> ScrapeResult:
        route = self._routes.get(
            engine_name,
            SourceRoute(engine_name, mode=CollectMode.AUTO),
        )

        # 确定实际执行模式
        mode = self._resolve_mode(route)

        try:
            if mode == CollectMode.BOTH:
                return await self._execute_both(engine_name, query, route, crawl_config)
            elif mode == CollectMode.API:
                result = await self._execute_api(engine_name, query, crawl_config)
                # 降级判断
                if result.error and route.allow_fallback:
                    fallback = await self._try_fallback(result, route, query, crawl_config)
                    if fallback:
                        return fallback
                return result
            else:  # CDP
                result = await self._execute_cdp(engine_name, query, crawl_config)
                if result.error and route.allow_fallback:
                    fallback = await self._try_fallback(result, route, query, crawl_config)
                    if fallback:
                        return fallback
                return result
        except Exception as e:
            logger.error(f"[{engine_name}] 调度异常: {e}")
            return ScrapeResult(
                engine_name=engine_name,
                mode_used=mode,
                documents=[],
                latency_ms=0,
                error=str(e),
            )

    def _resolve_mode(self, route: SourceRoute) -> CollectMode:
        """解析实际执行模式。"""
        if route.mode != CollectMode.AUTO:
            return route.mode

        # AUTO 模式：根据历史降级记录和引擎类型决策
        recent_fallbacks = self._fallback_history.get_recent(
            route.engine_name, window_minutes=30
        )

        # 近期频繁降级到某模式 → 直接使用该模式
        if recent_fallbacks >= 3:
            stats = self._fallback_history.get_stats(route.engine_name)
            if stats.get("cdp_success_rate", 0) > stats.get("api_success_rate", 0):
                return CollectMode.CDP
            else:
                return CollectMode.API

        return route.preferred

    async def _execute_api(
        self, engine_name: str, query: str, crawl_config
    ) -> ScrapeResult:
        start = time.monotonic()
        try:
            api_config = self._build_api_config(engine_name)
            adapter = self._api_factory.create(engine_name, api_config)

            # 反爬中间件
            ctx = None
            if self._anti_crawl:
                ctx = await self._anti_crawl.before_request(engine_name)

            docs = await adapter.scrape(query, crawl_config)

            if ctx and self._anti_crawl:
                await self._anti_crawl.after_request(ctx, success=True)

            latency = (time.monotonic() - start) * 1000
            self._fallback_history.record_success(engine_name, CollectMode.API)

            return ScrapeResult(
                engine_name=engine_name,
                mode_used=CollectMode.API,
                documents=docs,
                latency_ms=latency,
            )
        except ScrapeError as e:
            if self._anti_crawl and ctx:
                await self._anti_crawl.after_request(ctx, success=False)
            self._fallback_history.record_failure(engine_name, CollectMode.API, str(e))
            return ScrapeResult(
                engine_name=engine_name,
                mode_used=CollectMode.API,
                documents=[],
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(e),
            )

    async def _execute_cdp(
        self, engine_name: str, query: str, crawl_config
    ) -> ScrapeResult:
        if not self._cdp_manager:
            return ScrapeResult(
                engine_name=engine_name,
                mode_used=CollectMode.CDP,
                documents=[],
                latency_ms=0,
                error="CDP 管理器未初始化",
            )

        start = time.monotonic()
        try:
            scraper = self._cdp_manager.get_scraper(engine_name)
            docs = await scraper.scrape(query, crawl_config)
            latency = (time.monotonic() - start) * 1000
            self._fallback_history.record_success(engine_name, CollectMode.CDP)
            return ScrapeResult(
                engine_name=engine_name,
                mode_used=CollectMode.CDP,
                documents=docs,
                latency_ms=latency,
            )
        except Exception as e:
            self._fallback_history.record_failure(engine_name, CollectMode.CDP, str(e))
            return ScrapeResult(
                engine_name=engine_name,
                mode_used=CollectMode.CDP,
                documents=[],
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(e),
            )

    async def _execute_both(
        self, engine_name: str, query: str, route: SourceRoute, crawl_config
    ) -> ScrapeResult:
        """BOTH 模式：并行执行 API 和 CDP，合并去重。"""
        start = time.monotonic()

        api_task = asyncio.create_task(
            self._execute_api(engine_name, query, crawl_config)
        )
        cdp_task = asyncio.create_task(
            self._execute_cdp(engine_name, query, crawl_config)
        )

        api_result, cdp_result = await asyncio.gather(api_task, cdp_task, return_exceptions=True)

        # 合并文档，按 URL 去重
        all_docs: list[RawDocument] = []
        seen_urls: set[str] = set()

        for result in [api_result, cdp_result]:
            if isinstance(result, ScrapeResult):
                for doc in result.documents:
                    url = doc.source_url or doc.content[:100]
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_docs.append(doc)

        latency = (time.monotonic() - start) * 1000
        return ScrapeResult(
            engine_name=engine_name,
            mode_used=CollectMode.BOTH,
            documents=all_docs,
            latency_ms=latency,
        )

    async def _try_fallback(
        self,
        failed: ScrapeResult,
        route: SourceRoute,
        query: str,
        crawl_config,
    ) -> ScrapeResult | None:
        """尝试降级到备用模式。"""
        if not route.allow_fallback:
            return None

        fallback_mode = route.fallback_to
        if not fallback_mode:
            # 自动推断降级目标
            fallback_mode = (
                CollectMode.CDP
                if failed.mode_used == CollectMode.API
                else CollectMode.API
            )

        reason = self._classify_failure(failed.error)
        logger.info(
            f"[{route.engine_name}] {failed.mode_used.value} 失败 ({reason})，"
            f"降级到 {fallback_mode.value}"
        )

        if fallback_mode == CollectMode.CDP:
            result = await self._execute_cdp(route.engine_name, query, crawl_config)
        else:
            result = await self._execute_api(route.engine_name, query, crawl_config)

        result.is_fallback = True
        result.fallback_reason = reason
        return result

    def _classify_failure(self, error: str | None) -> FallbackReason:
        if not error:
            return FallbackReason.API_TIMEOUT
        error_lower = error.lower()
        if "timeout" in error_lower:
            return FallbackReason.API_TIMEOUT
        if "rate" in error_lower or "429" in error_lower:
            return FallbackReason.API_RATE_LIMIT
        if "auth" in error_lower or "401" in error_lower or "403" in error_lower:
            return FallbackReason.API_AUTH_ERROR
        if "empty" in error_lower or "no result" in error_lower:
            return FallbackReason.API_EMPTY
        if "captcha" in error_lower or "verify" in error_lower:
            return FallbackReason.CDP_CAPTCHA
        return FallbackReason.API_TIMEOUT
```

### 6.2 降级历史记录

```python
# src/intelligence/scrapers/fallback_history.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class FallbackRecord:
    engine_name: str
    mode: CollectMode
    success: bool
    error: str | None
    timestamp: datetime


class FallbackHistory:
    """记录采集模式的历史成功/失败率，指导 AUTO 模式决策。"""

    def __init__(self, max_records: int = 1000) -> None:
        self._records: list[FallbackRecord] = []
        self._max_records = max_records
        self._stats: dict[str, dict] = defaultdict(lambda: {
            "api_attempts": 0, "api_successes": 0,
            "cdp_attempts": 0, "cdp_successes": 0,
        })

    def record_success(self, engine_name: str, mode: CollectMode) -> None:
        self._add_record(engine_name, mode, success=True)
        key = "api" if mode == CollectMode.API else "cdp"
        self._stats[engine_name][f"{key}_attempts"] += 1
        self._stats[engine_name][f"{key}_successes"] += 1

    def record_failure(self, engine_name: str, mode: CollectMode, error: str) -> None:
        self._add_record(engine_name, mode, success=False, error=error)
        key = "api" if mode == CollectMode.API else "cdp"
        self._stats[engine_name][f"{key}_attempts"] += 1

    def _add_record(
        self, engine_name: str, mode: CollectMode, success: bool, error: str | None = None
    ) -> None:
        self._records.append(FallbackRecord(
            engine_name=engine_name,
            mode=mode,
            success=success,
            error=error,
            timestamp=datetime.now(),
        ))
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

    def get_recent(self, engine_name: str, window_minutes: int = 30) -> int:
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        return sum(
            1 for r in self._records
            if r.engine_name == engine_name and not r.success and r.timestamp >= cutoff
        )

    def get_stats(self, engine_name: str) -> dict:
        s = self._stats[engine_name]
        return {
            "api_success_rate": s["api_successes"] / max(s["api_attempts"], 1),
            "cdp_success_rate": s["cdp_successes"] / max(s["cdp_attempts"], 1),
            "api_attempts": s["api_attempts"],
            "cdp_attempts": s["cdp_attempts"],
        }
```

---

## 7. 降级与反馈机制

### 7.1 降级决策矩阵

| 场景 | API 状态 | CDP 状态 | 决策 |
|------|---------|---------|------|
| 正常 | 成功 | - | 仅 API，不触发 CDP |
| API 超时 / 429 | 失败 | 可用 | 降级到 CDP |
| API 认证失败 | 失败 | 可用 | 降级到 CDP + 告警（可能 API Key 过期） |
| API 返回空结果 | 空结果 | 可用 | 降级到 CDP（可能 DSL 需要调整） |
| API + CDP 均失败 | 失败 | 失败 | 记录到 RAG + 标记该数据源暂时不可用 |
| CDP 被验证码拦截 | - | 失败 | 记录 + 延迟重试 + 加入冷却期 |
| 连续 3 次降级 | 频繁降级 | - | 切换默认模式 + 通知用户 |

### 7.2 反馈写入 RAG

降级事件写入 RAG 知识库，指导后续 DSL 优化：

```python
async def record_fallback_to_rag(
    engine_name: str,
    from_mode: CollectMode,
    to_mode: CollectMode,
    reason: FallbackReason,
    dsl_used: str,
    rag_client: BaseRAGClient,
) -> None:
    feedback = CleanedDocument(
        content=(
            f"[采集反馈] 引擎: {engine_name}, "
            f"模式降级: {from_mode.value} → {to_mode.value}, "
            f"原因: {reason.value}, "
            f"DSL: {dsl_used}, "
            f"建议: 调整 DSL 语法或更换数据源"
        ),
        source_type=SourceCategory.SECURITY,
        source_name="system_feedback",
        quality_score=0.7,
        entities=[engine_name],
        metadata={"type": "fallback_feedback"},
    )
    await rag_client.upsert([feedback], task_id="system")
```

---

## 8. 配置体系

### 8.1 统一引擎配置（重构后）

将 `engines.yaml`、`crawler.yaml`、`engine_specs/engines.yaml` 三处配置合并为统一格式：

```yaml
# config/sources.yaml — 统一数据源配置（替代 engines.yaml + crawler.yaml）

sources:
  # ===================== 普通搜索引擎 =====================

  google:
    display_name: "Google"
    category: general_search

    # 采集模式配置
    mode:
      default: auto        # auto / api / cdp / both
      preferred: api       # auto 模式下的优先选择
      allow_fallback: true
      fallback_to: cdp

    # API 模式配置
    api:
      adapter: serpapi      # serpapi / serper / direct_http
      api_key_env: SERPAPI_API_KEY   # 从环境变量读取
      timeout: 30
      max_results: 100
      rate_limit: 2.0
      # 如果 SerpAPI 不可用，可切换到 serper
      fallback_adapter: serper
      fallback_api_key_env: SERPER_API_KEY

    # CDP 模式配置
    cdp:
      enabled: true
      search_url: "https://www.google.com/search"
      query_param: q
      result_selector: ".g"
      title_selector: "h3"
      link_selector: "h3 a"
      snippet_selector: ".VwiC3b"
      load_timeout: 30
      stealth: true
      human_behavior: true

    # 搜索语法（DSL 生成器使用）
    fields:
      site: "site:{value}"
      title: 'intitle:"{value}"'
      inurl: "inurl:{value}"
      filetype: "filetype:{value}"
    operators: [" ", "OR", "-", "AND"]

  bing:
    display_name: "Bing"
    category: general_search
    mode:
      default: auto
      preferred: api
      allow_fallback: true
      fallback_to: cdp
    api:
      adapter: serpapi
      api_key_env: SERPAPI_API_KEY
      timeout: 30
      max_results: 50
      rate_limit: 1.0
    cdp:
      enabled: true
      search_url: "https://www.bing.com/search"
      query_param: q
      result_selector: ".b_algo"
      title_selector: "h2 a"
      link_selector: "h2 a"
      snippet_selector: ".b_caption p"
      load_timeout: 30
      stealth: true
      human_behavior: true
    fields:
      site: "site:{value}"
      title: 'intitle:"{value}"'
      inurl: "inurl:{value}"
      filetype: "filetype:{value}"
      body: "inbody:{value}"
    operators: ["AND", "OR", "NOT", "+", "-"]

  baidu:
    display_name: "百度"
    category: general_search
    mode:
      # 百度反爬极严，CDP 几乎必封，优先 CDP 反而可能更差
      # 建议：有 SerpAPI 走 API，否则 CDP + stealth
      default: auto
      preferred: api
      allow_fallback: true
      fallback_to: cdp
    api:
      adapter: serpapi
      api_key_env: SERPAPI_API_KEY
      timeout: 30
      max_results: 100
      rate_limit: 1.0
    cdp:
      enabled: true
      search_url: "https://www.baidu.com/s"
      query_param: wd
      result_selector: ".result"
      title_selector: "h3 a"
      link_selector: "h3 a"
      snippet_selector: ".c-abstract"
      load_timeout: 30
      stealth: true
      human_behavior: true
    fields:
      site: "site:{value}"
      title: 'intitle:"{value}"'
    operators: [" ", "AND", "OR", "-"]

  sogou:
    display_name: "搜狗"
    category: general_search
    mode:
      default: auto
      preferred: cdp      # 搜狗无第三方 API 支持，优先 CDP
      allow_fallback: false # 无 API 可降级
    api:
      adapter: none        # 无可用 API
    cdp:
      enabled: true
      search_url: "https://www.sogou.com/web"
      query_param: query
      result_selector: ".vrwrap"
      title_selector: "h3 a"
      link_selector: "h3 a"
      snippet_selector: ".ft"
      load_timeout: 30
      stealth: true
      human_behavior: true

  # ===================== 资产引擎 =====================

  fofa:
    display_name: "FOFA"
    category: intelligence
    mode:
      default: api         # 资产引擎统一走官方 API
      preferred: api
      allow_fallback: false # 资产引擎无 CDP 降级意义
    api:
      adapter: asset_engine
      api_key_env: FOFA_API_KEY
      email_env: FOFA_EMAIL
      timeout: 30
      max_results: 100
      rate_limit: 1.0
      query_encoding: base64
    fields:
      domain: 'domain="{value}"'
      host: 'host="{value}"'
      title: 'title="{value}"'
      header: 'header="{value}"'
      cert: 'cert="{value}"'
      icon_hash: 'icon_hash="{value}"'
      app: 'app="{value}"'
      port: 'port="{value}"'
      country: 'country="{value}"'
    operators: ["=", "==", "!=", "&&", "||", "()"]

  hunter:
    display_name: "奇安信Hunter"
    category: intelligence
    mode:
      default: api
      preferred: api
      allow_fallback: false
    api:
      adapter: asset_engine
      api_key_env: HUNTER_API_KEY
      timeout: 30
      max_results: 100
      rate_limit: 0.5
    fields:
      web_title: 'web.title="{value}"'
      domain: 'domain="{value}"'
      ip: 'ip="{value}"'
      cert: 'cert="{value}"'
      web_icon: 'web.icon="{value}"'
    operators: ["=", "==", "&&", "||", "()", "!"]

  shodan:
    display_name: "Shodan"
    category: intelligence
    mode:
      default: api
      preferred: api
      allow_fallback: false
    api:
      adapter: asset_engine
      api_key_env: SHODAN_API_KEY
      timeout: 30
      max_results: 100
      rate_limit: 1.0
    fields:
      hostname: 'hostname:"{value}"'
      org: 'org:"{value}"'
      net: 'net:"{value}"'
      os: 'os:"{value}"'
      port: 'port:"{value}"'
      country: 'country:"{value}"'
    operators: [" ", "+", "-"]

# ===================== 全局配置 =====================
global:
  default_mode: auto

  api:
    default_timeout: 30
    default_rate_limit: 1.0
    retry_attempts: 3
    retry_backoff: 2.0

  cdp:
    enabled: true
    max_pages: 5
    timeout: 30
    headless: true
    launch_args:
      - "--disable-blink-features=AutomationControlled"
      - "--disable-dev-shm-usage"
      - "--no-sandbox"
      - "--disable-gpu"
    stealth: true
    human_behavior: true

  anti_crawl:
    delay_range: [1.5, 4.0]
    random_wait: true
    max_fallback_attempts: 2

  # SerpAPI / Serper 全局配置
  search_api:
    serpapi_key_env: SERPAPI_API_KEY
    serper_key_env: SERPER_API_KEY
    # Google 搜索优先用 Serper（便宜），其他用 SerpAPI
    google_adapter: serper
    bing_adapter: serpapi
    baidu_adapter: serpapi
```

### 8.2 环境变量管理

API Key 统一通过环境变量管理，不写入配置文件：

```bash
# .env — API 密钥配置（不提交到版本库）

# 搜索 API
SERPAPI_API_KEY=xxx
SERPER_API_KEY=xxx

# 资产引擎 API
FOFA_API_KEY=xxx
FOFA_EMAIL=xxx@example.com
HUNTER_API_KEY=xxx
SHODAN_API_KEY=xxx
CENSYS_API_ID=xxx
CENSYS_API_SECRET=xxx
ZOOMEYE_API_KEY=xxx

# 代理配置（CDP 模式使用）
PROXY_POOL_URL=xxx   # 代理池 API 地址
```

---

## 9. 数据源分类与模式映射

### 9.1 按类型推荐模式

| 数据源类型 | 代表引擎 | 推荐 API 适配器 | 推荐 CDP | 降级策略 |
|-----------|---------|---------------|---------|---------|
| **通用搜索引擎** | Google, Bing, Baidu | SerpAPI / Serper | stealth + human_behavior | API → CDP |
| **国内搜索引擎** | 搜狗, 360搜索 | 无（CDP only） | stealth + human_behavior | 无降级 |
| **资产引擎** | FOFA, Hunter, Shodan, Censys, ZoomEye | 官方 API | 不推荐 | API 失败 → 记录 + 跳过 |
| **OSINT 平台** | ICP, 天眼查, 招投标 | CDP（需登录态） | stealth + 行为模拟 | 无降级 |
| **安全漏洞库** | CNVD, NVD | 官方 API / HTTP | 不需要 | API → HTTP |
| **新闻聚合** | 百度新闻, 36氪 | HTTP / CDP | stealth | HTTP → CDP |

### 9.2 模式决策流程图

```
引擎请求到达
    │
    ├─ 资产引擎？
    │     └─► 直接走 API（官方 API）
    │
    ├─ 有第三方搜索 API？
    │     ├─► API Key 可用？
    │     │     └─► API 调用
    │     │           ├─ 成功 → 返回
    │     │           └─ 失败 → CDP 降级
    │     └─► 无 Key → CDP 模式
    │
    └─ 仅支持 CDP？
          └─► CDP + stealth 调用
                ├─ 成功 → 返回
                └─ 验证码/封禁 → 记录 + 冷却
```

---

## 10. 现有代码改造计划

### 10.1 改造范围

| 文件 | 改动类型 | 说明 |
|-----|---------|------|
| `src/intelligence/models.py` | 新增 | `CollectMode` 枚举、`ScrapeError` 异常类 |
| `src/intelligence/scrapers/api/base.py` | 新建 | `BaseApiAdapter` 抽象基类 |
| `src/intelligence/scrapers/api/serpapi_adapter.py` | 新建 | SerpAPI 适配器 |
| `src/intelligence/scrapers/api/serper_adapter.py` | 新建 | Serper API 适配器 |
| `src/intelligence/scrapers/api/asset_engine_adapter.py` | 新建 | 资产引擎适配器（从 `GenericEngineScraper` 重构） |
| `src/intelligence/scrapers/api/__init__.py` | 新建 | `ApiAdapterFactory` 工厂 |
| `src/intelligence/scrapers/dual_mode_scheduler.py` | 新建 | `DualModeScheduler` 调度器 |
| `src/intelligence/scrapers/fallback_history.py` | 新建 | 降级历史记录 |
| `src/intelligence/anti_crawl/stealth.py` | 新建 | 反检测 JS 脚本注入 |
| `src/intelligence/anti_crawl/human_behavior.py` | 新建 | 人类行为模拟 |
| `src/intelligence/scrapers/cdp_scraper.py` | 修改 | 集成 stealth + human_behavior + 降级回调 |
| `src/intelligence/scrapers/generic_scraper.py` | 保留 | 短期内保持兼容，长期被 `AssetEngineApiAdapter` 替代 |
| `config/sources.yaml` | 新建 | 统一数据源配置（逐步替代 engines.yaml + crawler.yaml） |
| `config/engines.yaml` | 保留 | 过渡期保持兼容，最终废弃 |
| `config/crawler.yaml` | 保留 | 过渡期保持兼容，最终合并到 sources.yaml |

### 10.2 改造步骤（分 3 个迭代）

**迭代 1：API 适配器层 + 调度器框架**
1. 新增 `CollectMode`、`ScrapeError` 到 `models.py`
2. 实现 `BaseApiAdapter` + `AssetEngineApiAdapter`（从 `GenericEngineScraper` 迁移能力）
3. 实现 `SerpApiAdapter`、`SerperApiAdapter`
4. 实现 `DualModeScheduler` + `FallbackHistory`
5. 编写单元测试

**迭代 2：CDP 增强 + 集成**
1. 实现 `stealth.py` + `human_behavior.py`
2. 改造 `CDPScraper` 集成反检测脚本
3. 实现真实降级逻辑（API → CDP 和 CDP → API）
4. 降级结果写入 RAG

**迭代 3：配置统一 + 旧代码清理**
1. 创建 `config/sources.yaml` 统一配置
2. 实现配置加载兼容层（同时支持旧格式和新格式）
3. 在 `IntelligenceModule` 中切换到 `DualModeScheduler`
4. 废弃 `GenericEngineScraper`（标记 deprecated）

### 10.3 新增目录结构

```
src/intelligence/
├── scrapers/
│   ├── __init__.py                    # 导出 DualModeScheduler
│   ├── base_scraper.py                # 保留（StubScraper）
│   ├── generic_scraper.py             # 保留（过渡期兼容）
│   ├── cdp_scraper.py                 # 修改（集成 stealth）
│   ├── dual_mode_scheduler.py         # 新建
│   ├── fallback_history.py            # 新建
│   └── api/                           # 新建目录
│       ├── __init__.py                # ApiAdapterFactory
│       ├── base.py                    # BaseApiAdapter
│       ├── serpapi_adapter.py         # SerpAPI
│       ├── serper_adapter.py          # Serper
│       └── asset_engine_adapter.py    # 资产引擎
├── anti_crawl/
│   ├── __init__.py                    # 修改（新增导出）
│   ├── middleware.py                  # 保留
│   ├── proxy_pool.py                  # 保留
│   ├── ua_pool.py                     # 保留
│   ├── stealth.py                     # 新建
│   └── human_behavior.py              # 新建
config/
├── sources.yaml                       # 新建（统一配置）
├── engines.yaml                       # 保留（过渡期）
├── crawler.yaml                       # 保留（过渡期）
└── datasources.yaml                   # 保留
```

---

## 11. 关键接口定义

### 11.1 M1 IntelligenceModule 集成示例

```python
# src/intelligence/intelligence_module.py（改造后的调用示例）

class IntelligenceModule:

    def __init__(self):
        # 初始化双模式调度器
        self._scheduler = DualModeScheduler(
            api_factory=ApiAdapterFactory(),
            cdp_manager=CDPScraperManager(anti_crawl=self._profile),
            anti_crawl=self._middleware,
        )

        # 从配置加载路由
        routes = self._load_routes_from_config()
        self._scheduler.register_routes(routes)

    async def start_collection(
        self, task_id: str, company_name: str, config: CollectionConfig
    ) -> CollectionJob:
        # 1. 数据源选择
        sources = await self._select_sources(company_name, config)

        # 2. DSL 生成
        queries = await self._generate_queries(company_name, sources)

        # 3. 双模式调度采集
        results = await self._scheduler.dispatch(queries, config)

        # 4. 合并结果
        all_docs = []
        for result in results:
            if isinstance(result, ScrapeResult):
                all_docs.extend(result.documents)
                # 记录采集模式到日志
                self._log_result(result)

        # 5. 数据清洗
        cleaned = await self._cleaner.clean(all_docs)

        # 6. 写入 RAG
        await self._rag.upsert(cleaned, task_id)

        return CollectionJob(task_id=task_id, status=CollectionStatus.COMPLETED)
```

### 11.2 手动指定模式

```python
# 用户可以在任务配置中强制指定某个引擎的采集模式

task_config = {
    "sources": {
        "google": {"mode": "api"},       # 强制 Google 用 API
        "fofa":   {"mode": "api"},       # 强制 FOFA 用 API
        "baidu":  {"mode": "both"},      # 百度两种并行
        "sogou":  {"mode": "cdp"},       # 搜狗只能 CDP
    }
}
```

### 11.3 ScrapeResult 结构

```python
@dataclass
class ScrapeResult:
    """单引擎采集结果。"""
    engine_name: str
    mode_used: CollectMode
    documents: list[RawDocument]
    latency_ms: float
    is_fallback: bool = False
    fallback_reason: FallbackReason | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.documents) > 0

    @property
    def doc_count(self) -> int:
        return len(self.documents)
```
