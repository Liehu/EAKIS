"""Unit tests for S-B real scrapers: news RSS / ICP / bidding (ccgp) / official."""
from __future__ import annotations

import pytest

from src.intelligence.models import SourceCategory
from src.intelligence.scrapers.bidding_scraper import BiddingScraper, parse_bidding_html
from src.intelligence.scrapers.icp_scraper import IcpScraper, _find_field
from src.intelligence.scrapers.news_scraper import NewsScraper, _parse_rss
from src.intelligence.scrapers.official_scraper import OfficialScraper, _extract, _normalize_target

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Bing News</title>
<item><title>Example Corp 发布新产品</title><link>https://example.com/news/1</link>
<description>Example Corp 今日发布新一代安全产品</description>
<pubDate>Mon, 17 Aug 2026 08:00:00 GMT</pubDate></item>
<item><title>Example Corp 获得融资</title><link>https://example.com/news/2</link>
<description>融资 10 亿元</description><pubDate>invalid-date</pubDate></item>
</channel></rss>"""

CCGP_SAMPLE = """
<ul class="vT-srch-result-list">
<li><a href="http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202608/t1.htm" target="_blank">
某单位云安全平台采购项目公开招标公告</a>
<span class="vT-srch-result-info">* 2026-08-15 14:30 &nbsp;某某中心</span></li>
<li><a href="http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202608/t2.htm">
网络安全服务项目中标公告</a>
<span class="vT-srch-result-info">* 2026-08-10 09:00</span></li>
</ul>
"""

HTML_SAMPLE = """<html><head><title>Example 官网</title></head>
<body><script>var x=1;</script><h1>企业级安全解决方案</h1><p>提供攻击面管理服务。</p></body></html>"""


# --- news ---

def test_parse_rss_extracts_real_urls():
    docs = _parse_rss(RSS_SAMPLE, "Example Corp")
    assert len(docs) == 2
    assert docs[0].source_url == "https://example.com/news/1"
    assert docs[0].source_type == SourceCategory.NEWS
    assert "Example Corp" in docs[0].content
    assert docs[0].published_at is not None  # 合法 pubDate 解析成功
    assert docs[1].published_at is not None  # 非法日期回退为 now 而非报错


def test_parse_rss_garbage_returns_empty():
    assert _parse_rss("<not-xml", "q") == []


@pytest.mark.asyncio
async def test_news_scraper_prefers_rss(monkeypatch):
    scraper = NewsScraper()
    async def fake_rss(q):
        return _parse_rss(RSS_SAMPLE, q)
    monkeypatch.setattr(scraper, "_rss", fake_rss)
    docs = await scraper.scrape("Example Corp")
    assert len(docs) == 2
    assert all(d.source_url.startswith("https://example.com") for d in docs)


@pytest.mark.asyncio
async def test_news_scraper_degrades_to_empty_without_stub(monkeypatch):
    from src.core.settings import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "intelligence_use_stubs", False)
    scraper = NewsScraper()
    async def none(q, c=None):
        return []
    monkeypatch.setattr(scraper, "_rss", none)
    monkeypatch.setattr(scraper, "_cdp", none)
    assert await scraper.scrape("Example Corp") == []


# --- icp ---

def test_find_field_nested():
    data = {"info": {"unitName": "北京百度网讯科技有限公司", "icp": "京ICP证030173号"}}
    assert _find_field(data, ("icp",)) == "京ICP证030173号"
    assert _find_field(data, ("unitName",)) == "北京百度网讯科技有限公司"
    assert _find_field([{"company": "X"}], ("company",)) == "X"


@pytest.mark.asyncio
async def test_icp_scraper_wraps_query_result(monkeypatch):
    from src.intelligence.scrapers import icp_scraper
    async def fake_query(domain):
        return {"domain": domain, "icp_number": "京ICP备12345678号-1",
                "icp_entity": "示例科技有限公司", "provider": "https://api.example.com/icp",
                "raw": {}}
    monkeypatch.setattr(icp_scraper, "query_icp", fake_query)
    docs = await IcpScraper().scrape("www.example.com")
    assert len(docs) == 1
    assert "京ICP备12345678号-1" in docs[0].content
    assert docs[0].metadata["icp"]["icp_entity"] == "示例科技有限公司"


@pytest.mark.asyncio
async def test_icp_scraper_skips_non_domain():
    assert await IcpScraper().scrape("北京示例科技有限公司") == []


# --- bidding ---

def test_parse_bidding_html():
    docs = parse_bidding_html(CCGP_SAMPLE)
    assert len(docs) == 2
    assert docs[0].source_url.endswith("t1.htm")
    assert "云安全平台" in docs[0].content
    assert docs[0].published_at is not None
    assert docs[0].published_at.year == 2026
    assert docs[0].source_name == "中国政府采购网"


@pytest.mark.asyncio
async def test_bidding_scraper_degrades(monkeypatch):
    from src.intelligence.scrapers import bidding_scraper
    async def fail(keyword, page=1):
        return []
    monkeypatch.setattr(bidding_scraper, "search_bidding", fail)
    assert await BiddingScraper().scrape("云安全") == []


# --- official ---

def test_normalize_target():
    assert _normalize_target("https://www.example.com") == "https://www.example.com"
    assert _normalize_target("example.com") == "https://example.com"
    assert _normalize_target("北京示例科技有限公司") is None
    assert _normalize_target("") is None


def test_extract_strips_script_and_tags():
    title, text = _extract(HTML_SAMPLE)
    assert title == "Example 官网"
    assert "var x" not in text
    assert "攻击面管理" in text


@pytest.mark.asyncio
async def test_official_scraper_real_fetch(monkeypatch):
    scraper = OfficialScraper()
    async def fake_httpx(url):
        return HTML_SAMPLE
    monkeypatch.setattr(scraper, "_fetch_httpx", fake_httpx)
    docs = await scraper.scrape("www.example.com")
    assert len(docs) == 1
    assert docs[0].source_url == "https://www.example.com"
    assert "攻击面管理" in docs[0].content
    assert docs[0].source_name == "www.example.com"
