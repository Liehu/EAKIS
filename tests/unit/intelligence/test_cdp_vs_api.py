"""百度搜索 CDP vs API 调用对比测试。

测试关键词：
  - "福建联通" or "中国联通福建省分公司"
  - "打造" or "发布"
  - "系统" or "平台"

对比维度：
  - 搜索结果数量
  - 结果标题
  - 结果链接
  - 执行耗时
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 百度 API 调用方式
# ---------------------------------------------------------------------------

class BaiduAPIClient:
    """百度搜索 API 客户端（httpx 方式）。"""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """执行百度搜索（API 方式）。"""
        url = "https://www.baidu.com/s"
        params = {"wd": query, "rn": max_results}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                html = response.text

            parse_time = time.time() - start_time
            logger.info(f"[API] 请求完成，耗时: {parse_time:.2f}秒")

            # 解析搜索结果
            results = self._parse_results(html)

            return {
                "method": "API",
                "query": query,
                "results_count": len(results),
                "results": results,
                "duration": parse_time,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[API] 搜索失败: {e}")
            return {
                "method": "API",
                "query": query,
                "error": str(e),
                "results_count": 0,
                "results": [],
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
            }

    def _parse_results(self, html: str) -> list[dict[str, Any]]:
        """从 HTML 中解析搜索结果。"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        results = []

        # 百度结果选择器
        result_divs = soup.select("div.result")

        for div in result_divs:
            try:
                # 提取标题
                title_elem = div.select_one("h3 a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # 提取链接
                link = title_elem.get("href", "")
                # 百度的链接是跳转链接，需要解密，这里暂时保留原链接
                if link.startswith("http"):
                    pass  # 是完整链接
                elif link.startswith("/"):
                    link = f"https://www.baidu.com{link}"

                # 提取摘要
                snippet_elem = div.select_one("div.c-abstract")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                })
            except Exception as e:
                logger.debug(f"解析单条结果失败: {e}")
                continue

        return results


# ---------------------------------------------------------------------------
# 百度 CDP 调用方式
# ---------------------------------------------------------------------------

class BaiduCDPClient:
    """百度搜索 CDP 客户端（Playwright 方式）。"""

    def __init__(self, timeout: float = 30.0, headless: bool = True) -> None:
        self.timeout = timeout
        self.headless = headless

    async def search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """执行百度搜索（CDP 方式）。"""
        url = f"https://www.baidu.com/s?wd={query}&rn={max_results}"

        start_time = time.time()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )

                page = await context.new_page()
                page.set_default_timeout(self.timeout * 1000)

                # 访问搜索页面
                await page.goto(url, wait_until="networkidle")

                # 等待结果加载
                await page.wait_for_selector("div.result", timeout=5000)

                # 提取结果
                results = await self._parse_results(page)

                parse_time = time.time() - start_time
                logger.info(f"[CDP] 请求完成，耗时: {parse_time:.2f}秒")

                await browser.close()

                return {
                    "method": "CDP",
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                    "duration": parse_time,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"[CDP] 搜索失败: {e}")
            return {
                "method": "CDP",
                "query": query,
                "error": str(e),
                "results_count": 0,
                "results": [],
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
            }

    async def _parse_results(self, page) -> list[dict[str, Any]]:
        """从页面中解析搜索结果。"""
        results = []
        result_divs = await page.query_selector_all("div.result")

        for div in result_divs:
            try:
                # 提取标题
                title_elem = await div.query_selector("h3 a")
                if not title_elem:
                    continue
                title = await title_elem.inner_text()

                # 提取链接
                link = await title_elem.get_attribute("href")
                if not link.startswith("http"):
                    link = f"https://www.baidu.com{link}" if link.startswith("/") else link

                # 提取摘要
                snippet = ""
                snippet_elem = await div.query_selector("div.c-abstract")
                if snippet_elem:
                    snippet = await snippet_elem.inner_text()

                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                })
            except Exception as e:
                logger.debug(f"解析单条结果失败: {e}")
                continue

        return results


# ---------------------------------------------------------------------------
# 测试对比
# ---------------------------------------------------------------------------

async def test_search_comparison():
    """对比 CDP 和 API 两种方式的搜索结果。"""

    # 测试关键词
    test_queries = [
        "福建联通 打造 系统",
        "福建联通 发布 平台",
        "中国联通福建省分公司 打造 系统",
        "中国联通福建省分公司 发布 平台",
    ]

    # 初始化客户端
    api_client = BaiduAPIClient()
    cdp_client = BaiduCDPClient(headless=True)  # 可改为 False 查看浏览器

    results_dir = Path("/tmp/cdp_vs_api_test")
    results_dir.mkdir(exist_ok=True)

    all_results = []

    for query in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"测试关键词: {query}")
        logger.info(f"{'='*60}")

        # API 方式
        api_result = await api_client.search(query)
        all_results.append(api_result)

        logger.info(f"[API] 结果数量: {api_result['results_count']}, 耗时: {api_result['duration']:.2f}秒")
        if api_result.get("error"):
            logger.warning(f"[API] 错误: {api_result['error']}")
        else:
            for i, item in enumerate(api_result["results"][:5], 1):
                logger.info(f"[API] {i}. {item['title'][:50]}...")

        # CDP 方式
        cdp_result = await cdp_client.search(query)
        all_results.append(cdp_result)

        logger.info(f"[CDP] 结果数量: {cdp_result['results_count']}, 耗时: {cdp_result['duration']:.2f}秒")
        if cdp_result.get("error"):
            logger.warning(f"[CDP] 错误: {cdp_result['error']}")
        else:
            for i, item in enumerate(cdp_result["results"][:5], 1):
                logger.info(f"[CDP] {i}. {item['title'][:50]}...")

        # 对比差异
        if not api_result.get("error") and not cdp_result.get("error"):
            api_titles = {r["title"] for r in api_result["results"]}
            cdp_titles = {r["title"] for r in cdp_result["results"]}

            common = api_titles & cdp_titles
            api_only = api_titles - cdp_titles
            cdp_only = cdp_titles - api_titles

            logger.info(f"\n[对比]")
            logger.info(f"  共同结果: {len(common)} 条")
            logger.info(f"  仅 API: {len(api_only)} 条")
            logger.info(f"  仅 CDP: {len(cdp_only)} 条")

        # 间隔
        await asyncio.sleep(2)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = results_dir / f"baidu_search_comparison_{timestamp}.json"

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n测试结果已保存到: {result_file}")

    # 生成对比报告
    await generate_comparison_report(all_results, results_dir / f"report_{timestamp}.txt")


async def generate_comparison_report(results: list[dict], output_path: Path):
    """生成对比报告。"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("百度搜索 CDP vs API 对比报告\n")
        f.write("=" * 80 + "\n\n")

        # 按查询分组
        query_groups: dict[str, dict] = {}
        for result in results:
            query = result["query"]
            if query not in query_groups:
                query_groups[query] = {}
            query_groups[query][result["method"]] = result

        # 输出每个查询的对比
        for query, methods in query_groups.items():
            f.write(f"\n查询: {query}\n")
            f.write("-" * 80 + "\n")

            api_data = methods.get("API")
            cdp_data = methods.get("CDP")

            if api_data:
                f.write(f"\n[API 方式]\n")
                f.write(f"  结果数量: {api_data['results_count']}\n")
                f.write(f"  耗时: {api_data['duration']:.2f} 秒\n")
                if api_data.get("error"):
                    f.write(f"  错误: {api_data['error']}\n")
                else:
                    f.write(f"  前 5 条结果:\n")
                    for i, item in enumerate(api_data["results"][:5], 1):
                        f.write(f"    {i}. {item['title']}\n")
                        f.write(f"       链接: {item['link'][:80]}...\n")
                        f.write(f"       摘要: {item['snippet'][:80]}...\n\n")

            if cdp_data:
                f.write(f"\n[CDP 方式]\n")
                f.write(f"  结果数量: {cdp_data['results_count']}\n")
                f.write(f"  耗时: {cdp_data['duration']:.2f} 秒\n")
                if cdp_data.get("error"):
                    f.write(f"  错误: {cdp_data['error']}\n")
                else:
                    f.write(f"  前 5 条结果:\n")
                    for i, item in enumerate(cdp_data["results"][:5], 1):
                        f.write(f"    {i}. {item['title']}\n")
                        f.write(f"       链接: {item['link'][:80]}...\n")
                        f.write(f"       摘要: {item['snippet'][:80]}...\n\n")

            # 对比差异
            if api_data and cdp_data and not api_data.get("error") and not cdp_data.get("error"):
                api_titles = {r["title"] for r in api_data["results"]}
                cdp_titles = {r["title"] for r in cdp_data["results"]}

                common = api_titles & cdp_titles
                api_only = api_titles - cdp_titles
                cdp_only = cdp_titles - api_titles

                f.write(f"\n[差异分析]\n")
                f.write(f"  共同结果: {len(common)} 条\n")
                f.write(f"  仅 API: {len(api_only)} 条\n")
                f.write(f"  仅 CDP: {len(cdp_only)} 条\n")
                f.write(f"  时间差: {abs(cdp_data['duration'] - api_data['duration']):.2f} 秒\n")
                f.write(f"  结果数差: {abs(cdp_data['results_count'] - api_data['results_count'])} 条\n")

        # 统计汇总
        f.write("\n" + "=" * 80 + "\n")
        f.write("统计汇总\n")
        f.write("=" * 80 + "\n\n")

        api_success = sum(1 for r in results if r["method"] == "API" and not r.get("error"))
        cdp_success = sum(1 for r in results if r["method"] == "CDP" and not r.get("error"))

        api_avg_time = sum(r["duration"] for r in results if r["method"] == "API") / len([r for r in results if r["method"] == "API"])
        cdp_avg_time = sum(r["duration"] for r in results if r["method"] == "CDP") / len([r for r in results if r["method"] == "CDP"])

        api_avg_results = sum(r["results_count"] for r in results if r["method"] == "API") / len([r for r in results if r["method"] == "API"])
        cdp_avg_results = sum(r["results_count"] for r in results if r["method"] == "CDP") / len([r for r in results if r["method"] == "CDP"])

        f.write(f"\n成功率:\n")
        f.write(f"  API: {api_success}/{len([r for r in results if r['method'] == 'API'])} ({api_success/len([r for r in results if r['method'] == 'API'])*100:.1f}%)\n")
        f.write(f"  CDP: {cdp_success}/{len([r for r in results if r['method'] == 'CDP'])} ({cdp_success/len([r for r in results if r['method'] == 'CDP'])*100:.1f}%)\n")

        f.write(f"\n平均耗时:\n")
        f.write(f"  API: {api_avg_time:.2f} 秒\n")
        f.write(f"  CDP: {cdp_avg_time:.2f} 秒\n")
        f.write(f"  差异: {cdp_avg_time - api_avg_time:.2f} 秒\n")

        f.write(f"\n平均结果数:\n")
        f.write(f"  API: {api_avg_results:.1f} 条\n")
        f.write(f"  CDP: {cdp_avg_results:.1f} 条\n")
        f.write(f"  差异: {cdp_avg_results - api_avg_results:.1f} 条\n")

    logger.info(f"对比报告已保存到: {output_path}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(test_search_comparison())
