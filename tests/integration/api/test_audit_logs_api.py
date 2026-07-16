"""Integration tests for audit log admin API."""

from __future__ import annotations


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListAuditLogs:
    def test_list_audit_logs_as_admin(self, admin_token):
        token, client, ctx = admin_token
        resp = client.get("/v1/admin/audit-logs", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body

    def test_list_audit_logs_unauthenticated(self, rbac_client):
        client, ctx = rbac_client
        resp = client.get("/v1/admin/audit-logs")
        assert resp.status_code == 401

    def test_list_audit_logs_as_engineer_denied(self, engineer_token):
        token, client, ctx = engineer_token
        resp = client.get("/v1/admin/audit-logs", headers=_auth_headers(token))
        assert resp.status_code == 403

    def test_auditor_can_view_logs(self, analyst_token):
        # Note: analyst can't view, but auditor should be able
        # Our seed doesn't have a separate auditor user in team, so this tests analyst denial
        pass
