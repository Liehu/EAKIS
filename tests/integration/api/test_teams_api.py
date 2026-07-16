"""Integration tests for team management admin API."""

from __future__ import annotations


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListTeams:
    def test_list_teams_as_admin(self, admin_token):
        token, client, ctx = admin_token
        resp = client.get("/v1/admin/teams", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert len(body["data"]) >= 1

    def test_list_teams_unauthenticated(self, rbac_client):
        client, ctx = rbac_client
        resp = client.get("/v1/admin/teams")
        assert resp.status_code == 401

    def test_list_teams_as_analyst_denied(self, analyst_token):
        token, client, ctx = analyst_token
        resp = client.get("/v1/admin/teams", headers=_auth_headers(token))
        assert resp.status_code == 403


class TestCreateTeam:
    def test_create_team_as_admin(self, admin_token):
        token, client, ctx = admin_token
        resp = client.post(
            "/v1/admin/teams",
            headers=_auth_headers(token),
            json={"name": "New Team", "description": "A new team"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Team"
        assert body["member_count"] == 0

    def test_create_team_duplicate_name(self, admin_token):
        token, client, ctx = admin_token
        resp = client.post(
            "/v1/admin/teams",
            headers=_auth_headers(token),
            json={"name": "Test Team"},  # Already exists from seed
        )
        assert resp.status_code == 409


class TestGetTeam:
    def test_get_team_with_members(self, admin_token):
        token, client, ctx = admin_token
        resp = client.get(f"/v1/admin/teams/{ctx['team_id']}", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "members" in body
        assert len(body["members"]) >= 2  # at least admin + engineer

    def test_get_team_not_found(self, admin_token):
        token, client, ctx = admin_token
        from uuid import uuid4
        resp = client.get(f"/v1/admin/teams/{uuid4()}", headers=_auth_headers(token))
        assert resp.status_code == 404


class TestTeamMemberManagement:
    def test_add_member_to_team(self, admin_token):
        token, client, ctx = admin_token
        # Create a new user first
        create_resp = client.post(
            "/v1/admin/users",
            headers=_auth_headers(token),
            json={
                "email": "newmember@test.local",
                "password": "member123",
                "display_name": "New Member",
                "role_name": "analyst",
            },
        )
        user_id = create_resp.json()["id"]

        # Add to team
        resp = client.post(
            f"/v1/admin/teams/{ctx['team_id']}/members",
            headers=_auth_headers(token),
            json={"user_id": user_id, "role_name": "engineer"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role_name"] == "engineer"

    def test_remove_member_from_team(self, admin_token):
        token, client, ctx = admin_token
        resp = client.delete(
            f"/v1/admin/teams/{ctx['team_id']}/members/{ctx['analyst_id']}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 204

    def test_update_member_role(self, admin_token):
        token, client, ctx = admin_token
        resp = client.patch(
            f"/v1/admin/teams/{ctx['team_id']}/members/{ctx['engineer_id']}",
            headers=_auth_headers(token),
            json={"role_name": "team_lead"},
        )
        assert resp.status_code == 200
        assert resp.json()["role_name"] == "team_lead"


class TestDeleteTeam:
    def test_delete_team_as_admin(self, admin_token):
        token, client, ctx = admin_token
        # Create a team first
        create_resp = client.post(
            "/v1/admin/teams",
            headers=_auth_headers(token),
            json={"name": "To Delete Team"},
        )
        team_id = create_resp.json()["id"]

        resp = client.delete(f"/v1/admin/teams/{team_id}", headers=_auth_headers(token))
        assert resp.status_code == 204
