"""Integration tests for user management admin API."""

from __future__ import annotations


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListUsers:
    def test_list_users_as_admin(self, admin_token):
        token, client, ctx = admin_token
        resp = client.get("/v1/admin/users", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert len(body["data"]) >= 3  # admin, engineer, analyst

    def test_list_users_unauthenticated(self, rbac_client):
        client, ctx = rbac_client
        resp = client.get("/v1/admin/users")
        assert resp.status_code == 401

    def test_list_users_as_engineer_denied(self, engineer_token):
        token, client, ctx = engineer_token
        resp = client.get("/v1/admin/users", headers=_auth_headers(token))
        assert resp.status_code == 403


class TestCreateUser:
    def test_create_user_as_admin(self, admin_token):
        token, client, ctx = admin_token
        resp = client.post(
            "/v1/admin/users",
            headers=_auth_headers(token),
            json={
                "email": "newuser@test.local",
                "password": "newpass123",
                "display_name": "New User",
                "role_name": "analyst",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newuser@test.local"
        assert body["display_name"] == "New User"

    def test_create_user_duplicate_email(self, admin_token):
        token, client, ctx = admin_token
        resp = client.post(
            "/v1/admin/users",
            headers=_auth_headers(token),
            json={
                "email": "admin@test.local",
                "password": "anypass123",
                "display_name": "Dup User",
                "role_name": "analyst",
            },
        )
        assert resp.status_code == 409

    def test_create_user_short_password(self, admin_token):
        token, client, ctx = admin_token
        resp = client.post(
            "/v1/admin/users",
            headers=_auth_headers(token),
            json={
                "email": "short@test.local",
                "password": "123",
                "display_name": "Short Pass",
                "role_name": "analyst",
            },
        )
        assert resp.status_code == 422


class TestGetUser:
    def test_get_user_detail(self, admin_token):
        token, client, ctx = admin_token
        resp = client.get(f"/v1/admin/users/{ctx['admin_id']}", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "admin@test.local"

    def test_get_user_not_found(self, admin_token):
        token, client, ctx = admin_token
        from uuid import uuid4
        resp = client.get(f"/v1/admin/users/{uuid4()}", headers=_auth_headers(token))
        assert resp.status_code == 404


class TestUpdateUser:
    def test_update_user(self, admin_token):
        token, client, ctx = admin_token
        resp = client.patch(
            f"/v1/admin/users/{ctx['engineer_id']}",
            headers=_auth_headers(token),
            json={"display_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"


class TestDeleteUser:
    def test_soft_delete_user(self, admin_token):
        token, client, ctx = admin_token
        # Create user first
        create_resp = client.post(
            "/v1/admin/users",
            headers=_auth_headers(token),
            json={
                "email": "todelete@test.local",
                "password": "delete123",
                "display_name": "To Delete",
                "role_name": "analyst",
            },
        )
        user_id = create_resp.json()["id"]

        # Soft delete
        resp = client.delete(f"/v1/admin/users/{user_id}", headers=_auth_headers(token))
        assert resp.status_code == 204

        # User should still exist but be inactive
        get_resp = client.get(f"/v1/admin/users/{user_id}", headers=_auth_headers(token))
        assert get_resp.json()["is_active"] is False
