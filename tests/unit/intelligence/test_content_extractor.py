"""ContentExtractor / TitleDeduplicator / FastPageExtractor 单元测试。"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.intelligence.config import ExtractionConfig
from src.intelligence.models import RawDocument, SourceCategory
from src.intelligence.services.title_dedup import (
    TitleDeduplicator,
    title_similarity,
    _normalize_title,
)
from src.intelligence.services.content_extractor import (
    CDPPageExtractor,
    ExtractedContent,
    FastPageExtractor,
)
from src.intelligence.agents.content_extractor import _extract_title_from_snippet


# ---------------------------------------------------------------------------
# 标题解析
# ---------------------------------------------------------------------------


class TestExtractTitleFromSnippet:
    def test_standard_format(self):
        content = "标题: 福建联通打造工业互联网\n链接: https://example.com/a\n摘要: 福建联通..."
        assert _extract_title_from_snippet(content) == "福建联通打造工业互联网"

    def test_colon_format(self):
        content = "标题:福建联通发布5G基站\n链接: https://example.com\n摘要: ..."
        assert _extract_title_from_snippet(content) == "福建联通发布5G基站"

    def test_multiline_title(self):
        content = "标题: 福建联通两大数据中心\n    启用仪式举行\n链接: https://example.com\n摘要: ..."
        assert _extract_title_from_snippet(content) == "福建联通两大数据中心"

    def test_plain_text_fallback(self):
        content = "这是一段没有标准格式的文本"
        assert _extract_title_from_snippet(content) == "这是一段没有标准格式的文本"

    def test_empty_content(self):
        assert _extract_title_from_snippet("") == ""


# ---------------------------------------------------------------------------
# 标题相似度
# ---------------------------------------------------------------------------


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert title_similarity("福建联通打造工业互联网平台", "福建联通打造工业互联网平台") == 1.0

    def test_similar_titles_high_similarity(self):
        a = '福建联通两大"智·云"数据中心启用 以更精的网络打造坚实底座'
        b = '福建联通两大"智·云"数据中心启用 以更精的网络打造坚实底座 '
        assert title_similarity(a, b) > 0.95

    def test_same_news_different_sources(self):
        a = '"跨岛医疗运输+安全智能巡检" 福建联通助力打造海岛低空经济'
        b = '"跨岛医疗运输+安全智能巡检" 福建联通助力打造海岛低空经济 '
        assert title_similarity(a, b) > 0.9

    def test_different_news_low_similarity(self):
        assert title_similarity("福建联通发布5G基站建设计划", "腾讯云发布AI大模型服务平台") < 0.5

    def test_empty_title(self):
        assert title_similarity("", "福建联通") == 0.0
        assert title_similarity("福建联通", "") == 0.0

    def test_normalize_strips_brackets(self):
        assert "【" not in _normalize_title("【福建联通】打造平台")

    def test_normalize_strips_punctuation(self):
        assert "：" not in _normalize_title("福建联通：打造工业互联网第一品牌")

    def test_normalize_whitespace(self):
        assert _normalize_title("福建联通  打造  平台") == _normalize_title("福建联通 打造 平台")


# ---------------------------------------------------------------------------
# TitleDeduplicator
# ---------------------------------------------------------------------------


class TestTitleDeduplicator:
    def test_identical_title_duplicate(self):
        dedup = TitleDeduplicator(threshold=0.9)
        dedup.add("福建联通打造工业互联网平台")
        assert dedup.is_duplicate("福建联通打造工业互联网平台")

    def test_similar_title_duplicate(self):
        dedup = TitleDeduplicator(threshold=0.9)
        dedup.add('“跨岛医疗运输” 福建联通助力打造海岛低空经济')
        assert dedup.is_duplicate('“跨岛医疗运输” 福建联通助力打造海岛低空经济 ')

    def test_different_title_not_duplicate(self):
        dedup = TitleDeduplicator(threshold=0.9)
        dedup.add("福建联通打造工业互联网平台")
        assert not dedup.is_duplicate("腾讯发布AI大模型")

    def test_empty_title_skipped(self):
        dedup = TitleDeduplicator(threshold=0.9)
        assert not dedup.is_duplicate("")
        dedup.add("")
        assert dedup.stats["seen_titles"] == 0

    def test_stats(self):
        dedup = TitleDeduplicator(threshold=0.9)
        dedup.add("标题A")
        dedup.add("标题B")
        assert dedup.stats["seen_titles"] == 2


# ---------------------------------------------------------------------------
# FastPageExtractor
# ---------------------------------------------------------------------------


class TestFastPageExtractor:
    @pytest.fixture
    def extractor(self):
        return FastPageExtractor(timeout=5.0)

    @pytest.fixture
    def sample_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head><title>测试文章 - 福建联通</title></head>
        <body>
            <nav>导航栏</nav>
            <article>
                <h1>福建联通打造工业互联网第一品牌</h1>
                <p>作为中国联通在福建的分支机构，福建联通扎根八闽大地，围绕大联接、大计算、大数据、大应用、大安全五大主责主业，
                全面发力数字经济主航道，打造福建"工业互联网第一品牌"，推动新型工业化发展。</p>
                <p>福建联通通过5G、边缘计算、多云联网、专用基站的融合，构建工业互联网平台，
                打造一套互联枢纽，实现工业内网、工业外网深度融合。</p>
            </article>
            <footer>版权所有</footer>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_trafilatura_extraction(self, extractor, sample_html):
        with patch.object(extractor, "_fetch_html", new_callable=AsyncMock, return_value=sample_html):
            result = await extractor.extract("https://example.com/article")
        assert result.extraction_method == "trafilatura"
        assert "工业互联网" in result.main_content
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_readability_fallback(self, extractor):
        html = "<html><head><title>Test</title></head><body><div id='content'>Some text here</div></body></html>"
        with patch.object(extractor, "_fetch_html", new_callable=AsyncMock, return_value=html):
            result = await extractor.extract("https://example.com/page")
        assert result.main_content
        assert result.extraction_method in ("trafilatura", "readability")

    @pytest.mark.asyncio
    async def test_empty_response(self, extractor):
        with patch.object(extractor, "_fetch_html", new_callable=AsyncMock, return_value=""):
            result = await extractor.extract("https://example.com/empty")
        assert result.extraction_method == "failed"

    @pytest.mark.asyncio
    async def test_http_error(self, extractor):
        with patch.object(extractor, "_fetch_html", new_callable=AsyncMock, side_effect=Exception("Connection refused")):
            result = await extractor.extract("https://example.com/error")
        assert result.extraction_method == "failed"

    def test_detect_needs_cdp_react_app(self, extractor):
        html = '<html><head><script src="react.js"></script></head><body><div id="root"></div></body></html>'
        assert extractor.detect_needs_cdp(html) is True

    def test_detect_needs_cdp_normal_page(self, extractor):
        html = '<html><head><title>Normal</title></head><body><p>A normal article.</p></body></html>'
        assert extractor.detect_needs_cdp(html) is False


# ---------------------------------------------------------------------------
# ContentExtractorAgent — 核心流程：先去重再爬取
# ---------------------------------------------------------------------------


LONG_CONTENT = (
    "福建联通作为中国联通在福建的分支机构，福建联通扎根八闽大地，"
    "围绕大联接、大计算、大数据、大应用、大安全五大主责主业，"
    "全面发力数字经济主航道，打造福建工业互联网第一品牌。"
)


class TestContentExtractorAgent:
    @pytest.fixture
    def agent(self):
        from src.intelligence.agents.content_extractor import ContentExtractorAgent
        return ContentExtractorAgent(cdp_enabled=False)

    @pytest.mark.asyncio
    async def test_passthrough_when_disabled(self, agent):
        docs = [RawDocument(content="...", source_type=SourceCategory.NEWS, source_name="Bing",
                         source_url="https://example.com/a")]
        config = ExtractionConfig(enabled=False)
        result = await agent.extract(docs, config)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_skips_search_engine_urls(self, agent):
        docs = [RawDocument(content="...", source_type=SourceCategory.NEWS, source_name="Bing",
                         source_url="https://www.baidu.com/s?wd=test")]
        result = await agent.extract(docs, ExtractionConfig())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_title_dedup_before_extraction(self, agent):
        """标题重复的文档不应被爬取（节省带宽）。"""
        docs = [
            RawDocument(
                content="标题: 福建联通打造工业互联网\n链接: https://site-a.com/news/123\n摘要: ...",
                source_type=SourceCategory.NEWS, source_name="Bing",
                source_url="https://site-a.com/news/123",
            ),
            RawDocument(
                content="标题: 福建联通打造工业互联网\n链接: https://site-b.com/news/456\n摘要: ...",
                source_type=SourceCategory.NEWS, source_name="Bing",
                source_url="https://site-b.com/news/456",
            ),
            RawDocument(
                content="标题: 腾讯云发布AI大模型\n链接: https://example.com/ai\n摘要: ...",
                source_type=SourceCategory.NEWS, source_name="Bing",
                source_url="https://example.com/ai",
            ),
        ]

        extract_call_urls = []

        async def mock_extract(url, headers=None):
            extract_call_urls.append(url)
            return ExtractedContent(
                title="title", main_content=LONG_CONTENT,
                extraction_method="trafilatura", url=url, word_count=len(LONG_CONTENT),
            )

        with patch.object(agent._fast, "extract", side_effect=mock_extract):
            result = await agent.extract(docs, ExtractionConfig(
                min_content_length=50,
                title_dedup_enabled=True,
                title_similarity_threshold=0.9,
            ))

        # 只爬取了 2 个 URL（1 个去重跳过）
        assert len(extract_call_urls) == 2
        # site-b.com/news/456 未被爬取（标题与 site-a 重复）
        assert not any("site-b.com" in u for u in extract_call_urls)
        assert any("site-a.com" in u for u in extract_call_urls)
        assert any("example.com/ai" in u for u in extract_call_urls)
        assert agent.stats["title_dup_skipped"] == 1
        assert len([d for d in result if "extraction_method" in d.metadata]) == 2

    @pytest.mark.asyncio
    async def test_different_titles_both_extracted(self, agent):
        """标题不同的文档都应被爬取。"""
        docs = [
            RawDocument(content="标题: 福建联通发布5G基站\n链接: https://a.com/1\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://a.com/1"),
            RawDocument(content="标题: 腾讯云发布AI大模型\n链接: https://b.com/2\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://b.com/2"),
        ]

        extract_call_urls = []

        async def mock_extract(url, headers=None):
            extract_call_urls.append(url)
            return ExtractedContent(main_content=LONG_CONTENT, extraction_method="trafilatura", url=url, word_count=len(LONG_CONTENT))

        with patch.object(agent._fast, "extract", side_effect=mock_extract):
            result = await agent.extract(docs, ExtractionConfig(min_content_length=50, title_dedup_enabled=True))

        assert len(extract_call_urls) == 2
        assert agent.stats["title_dup_skipped"] == 0

    @pytest.mark.asyncio
    async def test_title_dedup_can_be_disabled(self, agent):
        docs = [
            RawDocument(content="标题: 相同标题\n链接: https://a.com/1\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://a.com/1"),
            RawDocument(content="标题: 相同标题\n链接: https://b.com/2\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://b.com/2"),
        ]

        extract_call_urls = []

        async def mock_extract(url, headers=None):
            extract_call_urls.append(url)
            return ExtractedContent(main_content=LONG_CONTENT, extraction_method="trafilatura", url=url, word_count=len(LONG_CONTENT))

        with patch.object(agent._fast, "extract", side_effect=mock_extract):
            await agent.extract(docs, ExtractionConfig(
                min_content_length=50, title_dedup_enabled=False,
            ))

        assert len(extract_call_urls) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_keeps_snippet(self, agent):
        docs = [
            RawDocument(content="标题: 新闻A\n链接: https://a.com/1\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://a.com/1"),
            RawDocument(content="标题: 新闻B\n链接: https://b.com/2\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://b.com/2"),
        ]

        call_count = 0

        async def mock_extract(url, headers=None):
            nonlocal call_count
            call_count += 1
            if "a.com" in url:
                return ExtractedContent(main_content=LONG_CONTENT, extraction_method="trafilatura", url=url, word_count=len(LONG_CONTENT))
            return ExtractedContent(extraction_method="failed", url=url)

        with patch.object(agent._fast, "extract", side_effect=mock_extract):
            result = await agent.extract(docs, ExtractionConfig(min_content_length=50))

        assert call_count == 2  # 两个都尝试了爬取
        enriched = [d for d in result if "extraction_method" in d.metadata]
        snippet_kept = [d for d in result if "extraction_method" not in d.metadata and d.source_url]
        assert len(enriched) == 1
        assert len(snippet_kept) == 1  # 失败的保留原始 snippet

    @pytest.mark.asyncio
    async def test_stats_populated(self, agent):
        docs = [
            RawDocument(content="标题: 新闻A\n链接: https://a.com/1\n摘要: ...",
                       source_type=SourceCategory.NEWS, source_name="Bing", source_url="https://a.com/1"),
            RawDocument(content='{"domain":"example.com"}',
                       source_type=SourceCategory.ASSET_ENGINE, source_name="Fofa", source_url=None),
        ]

        async def mock_extract(url, headers=None):
            return ExtractedContent(main_content=LONG_CONTENT, extraction_method="trafilatura", url=url, word_count=len(LONG_CONTENT))

        with patch.object(agent._fast, "extract", side_effect=mock_extract):
            await agent.extract(docs, ExtractionConfig(min_content_length=50))

        assert agent.stats["total_candidates"] == 1
        assert agent.stats["extracted"] == 1
        assert agent.stats["passthrough"] == 1
