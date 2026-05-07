from __future__ import annotations

import re
from urllib.parse import urlparse

from src.api_crawler.models import CrawlMethod, ParameterInfo, RawInterface

_API_PATH_RE = re.compile(r"^/api(/v\d+)?/[a-zA-Z0-9][\w/.{}-]*$")
_ROUTE_PATH_RE = re.compile(r"^/[a-zA-Z0-9][\w/-]*(?:/[a-zA-Z0-9][\w/-]*)+$")
_STATIC_EXT_RE = re.compile(
    r"\.(png|jpg|jpeg|gif|svg|css|ico|woff|woff2|ttf|map|js)$", re.IGNORECASE
)


class StaticAnalyzer:
    PATTERNS: dict[str, re.Pattern[str]] = {
        "fetch_call": re.compile(r"""fetch\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "axios_get": re.compile(r"""axios\.get\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "axios_post": re.compile(r"""axios\.post\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "axios_put": re.compile(r"""axios\.put\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "axios_delete": re.compile(r"""axios\.delete\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "axios_patch": re.compile(r"""axios\.patch\s*\(\s*['"`]([^'"`\s]+)['"`]"""),
        "request_call": re.compile(
            r"""request\s*(?:\.\s*(?:get|post|put|delete|patch))?\s*\(\s*['"`]([^'"`\s]+)['"`]"""
        ),
        "vue_router": re.compile(r"""path\s*:\s*['"`]([^'"`{}]+)['"`]"""),
        "base_url": re.compile(r"""baseURL\s*:\s*['"`]([^'"`\s]+)['"`]"""),
    }

    FETCH_METHOD_MAP: dict[str, str] = {
        "fetch_call": "GET",
        "request_call": "GET",
        "vue_router": "GET",
        "base_url": "GET",
    }

    def analyze_js(self, js_content: str, base_url: str) -> list[RawInterface]:
        seen: set[str] = set()
        results: list[RawInterface] = []

        axios_patterns = [
            ("axios_get", "GET"),
            ("axios_post", "POST"),
            ("axios_put", "PUT"),
            ("axios_delete", "DELETE"),
            ("axios_patch", "PATCH"),
        ]
        for pat_name, method in axios_patterns:
            for m in self.PATTERNS[pat_name].finditer(js_content):
                path = m.group(1)
                if not self._is_api_path(path):
                    continue
                key = f"{method}:{path}"
                if key not in seen:
                    seen.add(key)
                    results.append(
                        RawInterface(
                            path=path,
                            method=method,
                            crawl_method=CrawlMethod.STATIC,
                            source_url=base_url,
                        )
                    )

        generic_patterns = ["fetch_call", "request_call", "vue_router"]
        for pat_name in generic_patterns:
            for m in self.PATTERNS[pat_name].finditer(js_content):
                path = m.group(1)
                if not self._is_api_path(path):
                    continue
                method = self.FETCH_METHOD_MAP.get(pat_name, "GET")
                key = f"{method}:{path}"
                if key not in seen:
                    seen.add(key)
                    results.append(
                        RawInterface(
                            path=path,
                            method=method,
                            crawl_method=CrawlMethod.STATIC,
                            source_url=base_url,
                        )
                    )

        return results

    def analyze_html(self, html_content: str, base_url: str) -> list[RawInterface]:
        seen: set[str] = set()
        results: list[RawInterface] = []

        form_re = re.compile(
            r'<form[^>]*action\s*=\s*["\']([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )
        method_re = re.compile(
            r'method\s*=\s*["\'](\w+)["\']', re.IGNORECASE
        )
        input_re = re.compile(
            r'<input[^>]*name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE
        )

        for form_match in form_re.finditer(html_content):
            path = form_match.group(1)
            form_tag = form_match.group(0)
            method_m = method_re.search(form_tag)
            method = (method_m.group(1) if method_m else "GET").upper()
            if not self._is_api_path(path):
                continue
            key = f"{method}:{path}"
            if key not in seen:
                seen.add(key)
                params = [
                    ParameterInfo(name=n, location="body")
                    for n in input_re.findall(form_tag)
                ]
                results.append(
                    RawInterface(
                        path=path,
                        method=method,
                        parameters=params,
                        crawl_method=CrawlMethod.STATIC,
                        source_url=base_url,
                    )
                )

        script_blocks = re.findall(
            r"<script[^>]*>(.*?)</script>", html_content, re.DOTALL | re.IGNORECASE
        )
        for script in script_blocks:
            js_results = self.analyze_js(script, base_url)
            for r in js_results:
                key = f"{r.method}:{r.path}"
                if key not in seen:
                    seen.add(key)
                    results.append(r)

        return results

    def detect_documentation_urls(
        self, html_content: str, base_url: str
    ) -> list[str]:
        standard_paths = [
            "/api-docs",
            "/swagger.json",
            "/openapi.json",
            "/v1/docs",
            "/v2/docs",
            "/docs",
            "/graphql",
            "/__graphql",
        ]
        candidates = []
        for p in standard_paths:
            if p in html_content:
                candidates.append(f"{base_url.rstrip('/')}{p}")
        if not candidates:
            candidates = [f"{base_url.rstrip('/')}{p}" for p in standard_paths[:4]]
        return candidates

    def _is_api_path(self, path: str) -> bool:
        if not path.startswith("/"):
            return False
        if _STATIC_EXT_RE.search(path):
            return False
        if _API_PATH_RE.match(path):
            return True
        return bool(_ROUTE_PATH_RE.match(path))
