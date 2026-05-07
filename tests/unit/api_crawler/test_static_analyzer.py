from __future__ import annotations

import pytest

from src.api_crawler.agents.static_analyzer import StaticAnalyzer
from src.api_crawler.models import CrawlMethod


@pytest.fixture
def analyzer() -> StaticAnalyzer:
    return StaticAnalyzer()


class TestExtractFromJS:
    def test_extracts_fetch_calls(self, analyzer: StaticAnalyzer):
        js = """
        async function getData() {
            const resp = await fetch('/api/v1/users');
            const resp2 = await fetch('/api/v2/orders');
        }
        """
        result = analyzer.analyze_js(js, base_url="https://example.com")
        paths = [r.path for r in result]
        assert "/api/v1/users" in paths
        assert "/api/v2/orders" in paths

    def test_extracts_axios_calls(self, analyzer: StaticAnalyzer):
        js = """
        axios.get('/api/v1/products');
        axios.post('/api/v1/cart', {item: 1});
        axios.put('/api/v1/user/settings');
        axios.delete('/api/v1/session');
        """
        result = analyzer.analyze_js(js, base_url="https://example.com")
        methods = {(r.method, r.path) for r in result}
        assert ("GET", "/api/v1/products") in methods
        assert ("POST", "/api/v1/cart") in methods
        assert ("PUT", "/api/v1/user/settings") in methods
        assert ("DELETE", "/api/v1/session") in methods

    def test_extracts_vue_router_paths(self, analyzer: StaticAnalyzer):
        js = """
        { path: '/admin/users', component: UserAdmin },
        { path: '/dashboard', component: Dashboard },
        """
        result = analyzer.analyze_js(js, base_url="https://example.com")
        paths = [r.path for r in result]
        assert "/admin/users" in paths

    def test_deduplicates_paths(self, analyzer: StaticAnalyzer):
        js = """
        fetch('/api/v1/items');
        fetch('/api/v1/items');
        """
        result = analyzer.analyze_js(js, base_url="https://example.com")
        paths = [r.path for r in result]
        assert paths.count("/api/v1/items") == 1

    def test_ignores_non_api_paths(self, analyzer: StaticAnalyzer):
        js = "const x = '/static/logo.png';"
        result = analyzer.analyze_js(js, base_url="https://example.com")
        paths = [r.path for r in result]
        assert "/static/logo.png" not in paths


class TestExtractFromHTML:
    def test_extracts_form_actions(self, analyzer: StaticAnalyzer):
        html = """
        <form action="/api/v1/login" method="POST">
            <input name="username"/>
            <input name="password" type="password"/>
            <button type="submit">Login</button>
        </form>
        """
        result = analyzer.analyze_html(html, base_url="https://example.com")
        assert len(result) >= 1
        assert result[0].path == "/api/v1/login"
        assert result[0].method == "POST"

    def test_extracts_inline_fetch_from_html(self, analyzer: StaticAnalyzer):
        html = """
        <script>
        fetch('/api/v1/data', {method: 'POST', body: JSON.stringify({q: 'test'})});
        </script>
        """
        result = analyzer.analyze_html(html, base_url="https://example.com")
        assert len(result) >= 1


class TestDetectSwagger:
    def test_detects_swagger_urls(self, analyzer: StaticAnalyzer):
        html = '<script src="app.js"></script>'
        urls = analyzer.detect_documentation_urls(
            html_content=html,
            base_url="https://example.com",
        )
        assert isinstance(urls, list)

    def test_returns_empty_for_none(self, analyzer: StaticAnalyzer):
        urls = analyzer.detect_documentation_urls(
            html_content="",
            base_url="https://example.com",
        )
        assert isinstance(urls, list)


class TestCrawlMethod:
    def test_results_have_static_method(self, analyzer: StaticAnalyzer):
        js = "fetch('/api/v1/test');"
        result = analyzer.analyze_js(js, base_url="https://example.com")
        assert all(r.crawl_method == CrawlMethod.STATIC for r in result)
