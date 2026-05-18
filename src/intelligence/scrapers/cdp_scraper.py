"""CDP 爬虫：基于 Playwright + Chrome DevTools Protocol 的浏览器自动化爬虫。

使用场景：
  1. 普通搜索引擎（百度/Bing/Google）反爬对抗
  2. 需要 JavaScript 渲染的动态页面
  3. Cookie/登录态维护的页面
  4. 复杂的反爬检测场景

设计要点：
  - 集成反爬中间件（UA/指纹伪装）
  - 支持并发页面控制
  - 自动降级到 httpx 模式
  - CDP 流量捕获（可选）
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.core.config_loader import config_loader
from src.core.config_paths import CRAWLER_YAML
from src.intelligence.anti_crawl.ua_pool import AntiCrawlProfile, BrowserProfile
from src.intelligence.config import CrawlConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.base import BaseScraper
from src.intelligence.agents.dsl_generator import UnifiedDSLGenerator

logger = logging.getLogger("eakis.intelligence.cdp_scraper")
logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# 配置模型
# ---------------------------------------------------------------------------


@dataclass
class EngineSelector:
    """搜索引擎结果选择器配置。"""
    search_url: str
    query_param: str
    result_selector: str
    title_selector: str
    link_selector: str
    snippet_selector: str


@dataclass
class CrawlerConfig:
    """CDP 爬虫配置。"""
    enabled: bool
    max_pages: int
    timeout: float
    headless: bool
    launch_args: list[str]
    cdp_engines: dict[str, EngineSelector]
    anti_crawl: dict
    fallback: dict


def load_crawler_config() -> CrawlerConfig:
    """从统一配置加载 CDP 爬虫配置。"""
    global_config = config_loader.load_global_config()

    # 从 config/crawler.yaml 加载特定配置（如果存在）
    if CRAWLER_YAML.exists():
        import yaml
        with open(CRAWLER_YAML, "r", encoding="utf-8") as f:
            crawler_data = yaml.safe_load(f)
        cdp_data = crawler_data.get("cdp_mode", {})
        anti_crawl = crawler_data.get("anti_crawl", {})
        fallback = crawler_data.get("fallback", {})
    else:
        cdp_data = {}
        anti_crawl = global_config.anti_crawl or {}
        fallback = {"on_failure": True, "failure_types": ["timeout", "navigation_error"]}

    return CrawlerConfig(
        enabled=cdp_data.get("enabled", False),
        max_pages=cdp_data.get("max_pages", getattr(global_config.cdp or {}, "get", lambda x, y: y)("max_pages", 5)),
        timeout=cdp_data.get("timeout", getattr(global_config.cdp or {}, "get", lambda x, y: y)("timeout", 30)),
        headless=cdp_data.get("headless", getattr(global_config.cdp or {}, "get", lambda x, y: y)("headless", True)),
        launch_args=cdp_data.get("launch_args", getattr(global_config.cdp or {}, "get", lambda x, y: y)("launch_args", ["--no-sandbox"])),
        cdp_engines=crawler_data.get("cdp_engines", {}),
        anti_crawl=anti_crawl,
        fallback=fallback,
    )


# ---------------------------------------------------------------------------
# CDP 爬虫
# ---------------------------------------------------------------------------


class CDPScraper(BaseScraper):
    """基于 Playwright + CDP 的浏览器爬虫。

    用法:
        scraper = CDPScraper(engine_name="baidu", anti_crawl=middleware)
        docs = await scraper.scrape(query="XX支付 后台", config=config)
    """

    def __init__(
        self,
        engine_name: str,
        anti_crawl: AntiCrawlProfile | None = None,
        config: CrawlerConfig | None = None,
        shared_browser: CDPScraperManager | None = None,
    ) -> None:
        self.engine_name = engine_name
        self.anti_crawl = anti_crawl
        self._config = config or load_crawler_config()
        self._shared_browser = shared_browser
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        # 初始化 DSL 生成器
        self._dsl_generator = UnifiedDSLGenerator()

        # 从 CDP 配置加载选择器
        crawler_config = load_crawler_config()
        self._engine_config = crawler_config.cdp_engines.get(engine_name, {})

    async def scrape(
        self, query: str, config: CrawlConfig | None = None
    ) -> list[RawDocument]:
        """执行 CDP 爬取。"""
        if not self._engine_config:
            logger.warning(f"[{self.engine_name}] 未找到 CDP 配置")
            return []

        # 应用反爬延迟
        await self._apply_anti_crawl_delay()

        # 总是使用独立浏览器实例，避免并发问题
        logger.debug(f"[{self.engine_name}] 使用独立浏览器实例")
        try:
            async with async_playwright() as p:
                await self._launch_browser(p)
                if not self._context:
                    return []

                page = await self._context.new_page()
                await self._setup_page(page)

                # 执行搜索
                logger.info(f"[{self.engine_name}] 原始查询: {query}")
                docs = await self._search(page, query)

                await page.close()

            return docs

        except Exception as e:
            logger.error(f"[{self.engine_name}] CDP 爬取失败: {e}")

            # 检查是否需要降级
            if self._should_fallback(str(e)):
                logger.info(f"[{self.engine_name}] 触发降级策略")
                # 这里可以调用 httpx 爬虫降级
                # 暂时返回空结果
                return []

            return []

        finally:
            # 独立模式下清理
            await self._cleanup()

    async def _launch_browser(self, playwright) -> None:
        """启动浏览器。"""
        launch_args = self._config.launch_args.copy()

        # 如果不是无头模式，添加开发工具标志
        if not self._config.headless:
            launch_args.append("--auto-open-devtools-for-tabs")

        self._browser = await playwright.chromium.launch(
            headless=self._config.headless,
            args=launch_args,
        )

        # 应用反爬伪装
        profile = self.anti_crawl.random_profile() if self.anti_crawl else None

        user_agent = profile.user_agent if profile else None
        viewport = None
        if profile:
            viewport = {
                "width": profile.viewport_width,
                "height": profile.viewport_height,
            }

        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale=profile.accept_language.split(",")[0] if profile else "zh-CN",
            timezone_id="Asia/Shanghai",
            # 添加额外的反爬措施
            permissions=["geolocation"],
            geolocation={"latitude": 39.9, "longitude": 116.4},  # 北京
            extra_http_headers={
                "Accept-Language": profile.accept_language if profile else "zh-CN,zh;q=0.9",
                "Accept-Encoding": profile.accept_encoding if profile else "gzip, deflate, br",
            },
        )

    async def _setup_page(self, page: Page) -> None:
        """设置页面，注入反爬脚本。"""
        # 注入 Canvas 噪声（如果配置了 canvas_seed）
        if self.anti_crawl:
            profile = self.anti_crawl.random_profile()
            await page.add_init_script(
                f"""
                // Canvas 指纹噪声注入
                (function() {{
                    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    const seed = {profile.canvas_seed};
                    let counter = 0;
                    HTMLCanvasElement.prototype.toDataURL = function() {{
                        counter++;
                        const result = originalToDataURL.apply(this, arguments);
                        // 每第10次调用返回轻微不同的结果
                        if (counter % 10 === 0) {{
                            const lastChar = result.charCodeAt(result.length - 1);
                            return result.slice(0, -1) + String.fromCharCode(lastChar + (seed % 2));
                        }}
                        return result;
                    }};
                }})();
                """
            )

        # 设置超时
        page.set_default_timeout(self._config.timeout * 1000)

        # 监听页面错误
        page.on("pageerror", lambda error: logger.debug(f"页面错误: {error}"))

    async def _search(self, page: Page, query: str) -> list[RawDocument]:
        """执行搜索并提取结果。"""
        # 构建搜索 URL
        search_url = self._build_search_url(query)
        logger.info(f"[{self.engine_name}] 访问: {search_url}")

        # 访问搜索页面
        timeout = self._engine_config.get("load_timeout", self._config.timeout) * 1000
        await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout)

        # 等待结果加载
        wait_selector = self._engine_config.get("wait_for_selector", self._engine_config["result_selector"])
        await page.wait_for_selector(wait_selector, timeout=5000)

        # 提取结果
        results = await page.query_selector_all(self._engine_config["result_selector"])
        logger.info(f"[{self.engine_name}] 找到 {len(results)} 条结果")

        docs = []
        for result in results:
            try:
                doc = await self._parse_result(page, result, query)
                if doc:
                    docs.append(doc)
            except Exception as e:
                logger.debug(f"解析结果失败: {e}")
                continue

        return docs

    async def _parse_result(
        self,
        page: Page,
        result,
        query: str,
    ) -> RawDocument | None:
        """解析单条搜索结果。"""
        try:
            # 提取标题
            title_el = await result.query_selector(self._engine_config["title_selector"])
            title = await title_el.inner_text() if title_el else ""

            # 提取链接
            link_el = await result.query_selector(self._engine_config["link_selector"])
            link = await link_el.get_attribute("href") if link_el else ""

            # 提取摘要（如果存在选择器）
            snippet = ""
            if self._engine_config["snippet_selector"]:
                snippet_el = await result.query_selector(self._engine_config["snippet_selector"])
                snippet = await snippet_el.inner_text() if snippet_el else ""

            if not title or not link:
                return None

            return RawDocument(
                content=f"标题: {title}\n链接: {link}\n摘要: {snippet}",
                source_type=SourceCategory.NEWS,
                source_name=self.engine_name.title(),
                source_url=link,
                published_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.debug(f"解析单条结果失败: {e}")
            return None

    _DSL_PREFIXES = ("site:", "intitle:", "inurl:", "filetype:", "inbody:", "cache:",
                     "related:", "ext:", "allinurl:", "allintitle:", "allintext:")

    def _is_dsl_query(self, query: str) -> bool:
        """判断查询是否已经是 DSL 格式（含搜索引擎操作符）。"""
        return any(query.startswith(p) or f" {p}" in query for p in self._DSL_PREFIXES)

    def _build_search_url(self, query: str) -> str:
        """构建搜索 URL。如果查询已包含 DSL 操作符则直接使用，否则尝试生成。"""
        from urllib.parse import urlencode

        # 如果查询已包含 DSL 操作符（由上游 DSL 生成器生成），直接使用
        if self._is_dsl_query(query):
            params = {self._engine_config["query_param"]: query}
            logger.info(f"[{self.engine_name}] 直接使用 DSL: {query}")
            return f"{self._engine_config['search_url']}?{urlencode(params)}"

        # 否则尝试通过 DSL 生成器转换
        try:
            from src.intelligence.agents.dsl_generator import SearchContext
            context = SearchContext(
                keywords=[query],
                domains=[],
            )
            dsl_results = self._dsl_generator._generate_via_template(
                context=context,
                engines=[self.engine_name]
            )
            if dsl_results:
                dsl_query = dsl_results[0].query
                params = {self._engine_config["query_param"]: dsl_query}
                logger.info(f"[{self.engine_name}] 使用 DSL 语法: {dsl_query}")
                return f"{self._engine_config['search_url']}?{urlencode(params)}"
        except Exception as e:
            logger.warning(f"[{self.engine_name}] DSL 生成异常: {e}，使用原始查询")

        params = {self._engine_config["query_param"]: query}
        return f"{self._engine_config['search_url']}?{urlencode(params)}"

    async def _apply_anti_crawl_delay(self) -> None:
        """应用反爬请求延迟。"""
        delay_range = self._config.anti_crawl.get("delay_range", [1.5, 4.0])
        if self._config.anti_crawl.get("random_wait", True):
            delay = random.uniform(*delay_range)
        else:
            delay = delay_range[0]

        logger.debug(f"[{self.engine_name}] 反爬延迟: {delay:.2f}秒")
        await asyncio.sleep(delay)

    def _should_fallback(self, error: str) -> bool:
        """检查是否需要降级。"""
        if not self._config.fallback.get("on_failure", False):
            return False

        failure_types = self._config.fallback.get("failure_types", [])
        error_lower = error.lower()

        for fail_type in failure_types:
            if fail_type.lower() in error_lower:
                return True

        return False

    async def _cleanup(self) -> None:
        """清理资源。"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None


# ---------------------------------------------------------------------------
# CDP 爬虫管理器
# ---------------------------------------------------------------------------


class CDPScraperManager:
    """CDP 爬虫管理器，管理并发页面和资源池。"""

    def __init__(
        self,
        anti_crawl: AntiCrawlProfile | None = None,
        config: CrawlerConfig | None = None,
    ) -> None:
        self.anti_crawl = anti_crawl
        self._config = config or load_crawler_config()
        self._semaphore = asyncio.Semaphore(self._config.max_pages)
        self._scrapers: dict[str, CDPScraper] = {}
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._cleanup_called = False

    async def _launch_browser(self, playwright) -> None:
        """启动共享浏览器实例。"""
        launch_args = self._config.launch_args.copy()

        # 如果不是无头模式，添加开发工具标志
        if not self._config.headless:
            launch_args.append("--auto-open-devtools-for-tabs")

        self._browser = await playwright.chromium.launch(
            headless=self._config.headless,
            args=launch_args,
        )

        # 应用反爬伪装
        profile = self.anti_crawl.random_profile() if self.anti_crawl else None

        user_agent = profile.user_agent if profile else None
        viewport = None
        if profile:
            viewport = {
                "width": profile.viewport_width,
                "height": profile.viewport_height,
            }

        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale=profile.accept_language.split(",")[0] if profile else "zh-CN",
            timezone_id="Asia/Shanghai",
            # 添加额外的反爬措施
            permissions=["geolocation"],
            geolocation={"latitude": 39.9, "longitude": 116.4},  # 北京
            extra_http_headers={
                "Accept-Language": profile.accept_language if profile else "zh-CN,zh;q=0.9",
                "Accept-Encoding": profile.accept_encoding if profile else "gzip, deflate, br",
            },
        )

    def get_scraper(self, engine_name: str) -> CDPScraper:
        """获取或创建引擎爬虫。"""
        if engine_name not in self._scrapers:
            self._scrapers[engine_name] = CDPScraper(
                engine_name=engine_name,
                anti_crawl=self.anti_crawl,
                config=self._config,
            )
        return self._scrapers[engine_name]

    async def scrape_concurrent(
        self,
        queries: list[tuple[str, str]],  # (engine_name, query)
        config: CrawlConfig | None = None,
    ) -> list[RawDocument]:
        """并发执行多个查询。"""
        all_docs: list[RawDocument] = []

        async def _scrape_one(engine_name: str, query: str) -> list[RawDocument]:
            async with self._semaphore:
                scraper = self.get_scraper(engine_name)
                return await scraper.scrape(query, config)

        tasks = [_scrape_one(name, q) for name, q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_docs.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"查询失败: {result}")

        return all_docs

    async def cleanup(self) -> None:
        """清理所有爬虫资源。"""
        if self._cleanup_called:
            return

        self._cleanup_called = True

        try:
            # 关闭浏览器和上下文（如果存在）
            if self._context:
                try:
                    await self._context.close()
                except Exception as e:
                    logger.debug(f"关闭浏览器上下文时出错: {e}")
                finally:
                    self._context = None
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.debug(f"关闭浏览器时出错: {e}")
                finally:
                    self._browser = None
        except Exception as e:
            logger.error(f"清理浏览器资源时出错: {e}")

        # 清理爬虫列表
        self._scrapers.clear()
