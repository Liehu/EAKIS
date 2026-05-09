"""API integration tests: keywords endpoints (M2).

Note: Keywords endpoints use get_async_db which connects to PostgreSQL.
Since PG_UUID types are incompatible with SQLite, we can only test
validation and error-handling paths here. The CRUD logic is tested
via module pipeline tests with mocked sessions.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestKeywordsAPIValidation:
    """Tests that don't require a database connection."""

    def test_create_keyword_invalid_type(self, client: TestClient):
        """Invalid keyword type should return 422."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/v1/tasks/{fake_id}/keywords",
            json={"word": "测试", "type": "invalid_type", "weight": 0.8},
        )
        assert resp.status_code == 422

    def test_create_keyword_weight_out_of_range(self, client: TestClient):
        """Weight > 1.0 should return 422."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/v1/tasks/{fake_id}/keywords",
            json={"word": "测试", "type": "business", "weight": 1.5},
        )
        assert resp.status_code == 422

    def test_create_keyword_negative_weight(self, client: TestClient):
        """Negative weight should return 422."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/v1/tasks/{fake_id}/keywords",
            json={"word": "测试", "type": "business", "weight": -0.1},
        )
        assert resp.status_code == 422

    def test_create_keyword_missing_word(self, client: TestClient):
        """Missing required 'word' field should return 422."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/v1/tasks/{fake_id}/keywords",
            json={"type": "business", "weight": 0.5},
        )
        assert resp.status_code == 422

    def test_create_keyword_missing_type(self, client: TestClient):
        """Missing required 'type' field should return 422."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/v1/tasks/{fake_id}/keywords",
            json={"word": "测试", "weight": 0.5},
        )
        assert resp.status_code == 422

    def test_list_keywords_invalid_page(self, client: TestClient):
        """page=0 should return 422."""
        fake_id = str(uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}/keywords", params={"page": 0})
        assert resp.status_code == 422

    def test_list_keywords_invalid_page_size(self, client: TestClient):
        """page_size=200 should return 422 (max 100)."""
        fake_id = str(uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}/keywords", params={"page_size": 200})
        assert resp.status_code == 422

    def test_list_keywords_filter_invalid_type(self, client: TestClient):
        """Invalid type filter should return 422."""
        fake_id = str(uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}/keywords", params={"type": "invalid"})
        assert resp.status_code == 422

    def test_delete_keyword_invalid_uuid(self, client: TestClient):
        """Non-UUID keyword_id should return 422."""
        fake_id = str(uuid4())
        resp = client.delete(f"/v1/tasks/{fake_id}/keywords/not-a-uuid")
        assert resp.status_code == 422

    @pytest.mark.skip(reason="Hits real PostgreSQL — test validation via 422 tests instead")
    def test_create_keyword_valid_types_pass_validation(self, client: TestClient):
        """All three valid types should pass Pydantic validation."""
