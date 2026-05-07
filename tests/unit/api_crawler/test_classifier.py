from __future__ import annotations

import pytest

from src.api_crawler.agents.interface_classifier import InterfaceClassifier
from src.api_crawler.models import (
    CrawlMethod,
    InterfaceType,
    ParameterInfo,
    RawInterface,
)


@pytest.fixture
def classifier() -> InterfaceClassifier:
    return InterfaceClassifier()


def _raw(path: str, method: str = "GET", **kwargs) -> RawInterface:
    return RawInterface(
        path=path, method=method, crawl_method=CrawlMethod.STATIC, **kwargs
    )


class TestClassifyType:
    def test_auth_paths(self, classifier: InterfaceClassifier):
        for path, expected in [
            ("/api/v1/auth/login", InterfaceType.AUTH),
            ("/api/v1/logout", InterfaceType.AUTH),
            ("/api/v1/token/refresh", InterfaceType.AUTH),
            ("/api/v1/register", InterfaceType.AUTH),
        ]:
            result = classifier.classify(_raw(path), asset_id="a1")
            assert result.api_type == expected, f"{path} should be {expected}"

    def test_operation_paths(self, classifier: InterfaceClassifier):
        for path, method, expected in [
            ("/api/v1/users", "POST", InterfaceType.OPERATION),
            ("/api/v1/orders/create", "POST", InterfaceType.OPERATION),
            ("/api/v1/users/123", "DELETE", InterfaceType.OPERATION),
            ("/api/v1/users/123/profile", "PUT", InterfaceType.OPERATION),
        ]:
            result = classifier.classify(_raw(path, method), asset_id="a1")
            assert result.api_type == expected, f"{method} {path} should be {expected}"

    def test_query_paths(self, classifier: InterfaceClassifier):
        for path in ["/api/v1/users", "/api/v1/orders/list", "/api/v1/products/detail"]:
            result = classifier.classify(_raw(path, "GET"), asset_id="a1")
            assert result.api_type == InterfaceType.QUERY, f"GET {path} should be QUERY"

    def test_upload_paths(self, classifier: InterfaceClassifier):
        for path in ["/api/v1/files/upload", "/api/v1/export/csv"]:
            result = classifier.classify(_raw(path, "POST"), asset_id="a1")
            assert result.api_type == InterfaceType.UPLOAD, f"{path} should be UPLOAD"

    def test_search_paths(self, classifier: InterfaceClassifier):
        result = classifier.classify(
            _raw("/api/v1/search/products", "GET"), asset_id="a1"
        )
        assert result.api_type == InterfaceType.SEARCH

    def test_admin_paths(self, classifier: InterfaceClassifier):
        result = classifier.classify(
            _raw("/api/v1/admin/users", "GET"), asset_id="a1"
        )
        assert result.api_type == InterfaceType.ADMIN


class TestPrivilegeSensitivity:
    def test_detects_userid_param(self, classifier: InterfaceClassifier):
        raw = _raw(
            "/api/v2/user/{userId}/orders",
            "GET",
            parameters=[
                ParameterInfo(
                    name="userId", location="path", type="integer", required=True
                ),
            ],
        )
        result = classifier.classify(raw, asset_id="a1")
        assert result.privilege_sensitive is True
        assert "userId" in result.sensitive_params

    def test_detects_multiple_sensitive_params(self, classifier: InterfaceClassifier):
        raw = _raw(
            "/api/v1/admin/tenant/{tenantId}/role/{roleId}",
            "GET",
            parameters=[
                ParameterInfo(name="tenantId", location="path"),
                ParameterInfo(name="roleId", location="path"),
            ],
        )
        result = classifier.classify(raw, asset_id="a1")
        assert result.privilege_sensitive is True
        assert len(result.sensitive_params) == 2

    def test_non_sensitive_params(self, classifier: InterfaceClassifier):
        raw = _raw(
            "/api/v1/products",
            "GET",
            parameters=[
                ParameterInfo(name="page", location="query"),
                ParameterInfo(name="size", location="query"),
            ],
        )
        result = classifier.classify(raw, asset_id="a1")
        assert result.privilege_sensitive is False
        assert result.sensitive_params == []


class TestPathNormalization:
    def test_replaces_numeric_ids(self, classifier: InterfaceClassifier):
        raw = _raw("/api/v1/users/123/orders", "GET")
        result = classifier.classify(raw, asset_id="a1")
        assert result.path_pattern == "/api/v1/users/{id}/orders"

    def test_replaces_uuid_segments(self, classifier: InterfaceClassifier):
        raw = _raw(
            "/api/v1/items/550e8400-e29b-41d4-a716-446655440000", "GET"
        )
        result = classifier.classify(raw, asset_id="a1")
        assert "{id}" in result.path_pattern

    def test_preserves_non_id_paths(self, classifier: InterfaceClassifier):
        raw = _raw("/api/v1/users/list", "GET")
        result = classifier.classify(raw, asset_id="a1")
        assert result.path_pattern == "/api/v1/users/list"


class TestPriorityScoring:
    def test_admin_gets_high_priority(self, classifier: InterfaceClassifier):
        raw = _raw("/api/v1/admin/config", "PUT")
        result = classifier.classify(raw, asset_id="a1")
        assert result.test_priority >= 8

    def test_privilege_sensitive_gets_high_priority(
        self, classifier: InterfaceClassifier
    ):
        raw = _raw(
            "/api/v2/user/{userId}/orders",
            "GET",
            parameters=[ParameterInfo(name="userId", location="path", sensitive=True)],
        )
        result = classifier.classify(raw, asset_id="a1")
        assert result.test_priority >= 8

    def test_simple_query_gets_medium_priority(self, classifier: InterfaceClassifier):
        raw = _raw("/api/v1/products", "GET")
        result = classifier.classify(raw, asset_id="a1")
        assert 3 <= result.test_priority <= 6
