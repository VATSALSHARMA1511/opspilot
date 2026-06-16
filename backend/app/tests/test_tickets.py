"""
Tests for /api/v1/tickets/*.

Verified against tickets.py and ticket_service.py:

  Routes (no trailing slash on collection endpoints):
    POST   /api/v1/tickets                  -> 201
    GET    /api/v1/tickets                  -> 200  PaginatedResponse
    GET    /api/v1/tickets/{id}             -> 200
    PUT    /api/v1/tickets/{id}             -> 200
    PATCH  /api/v1/tickets/{id}/status      -> 200
    PATCH  /api/v1/tickets/{id}/assign      -> 200
    DELETE /api/v1/tickets/{id}             -> 204  (admin only)
    POST   /api/v1/tickets/{id}/comments    -> 201
    GET    /api/v1/tickets/{id}/comments    -> 200

  State machine from VALID_TRANSITIONS in ticket_service.py:
    OPEN        -> {ASSIGNED, IN_PROGRESS}
    ASSIGNED    -> {IN_PROGRESS, OPEN}
    IN_PROGRESS -> {RESOLVED}
    RESOLVED    -> {CLOSED, IN_PROGRESS}
    CLOSED      -> set()  [terminal - raises 400]

  Permissions from ticket_service.py:
    update_ticket:    creator OR admin; any other role -> 403
    soft_delete:      admin only -> 403 for everyone else
    internal comment: agent or admin only; viewer -> 403
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TICKET_PAYLOAD = {
    "title": "Printer not working",
    "description": "Office printer is offline",
    "priority": "medium",
    "category": "hardware",
}


def register_and_headers(client, email, role="agent"):
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "StrongPass123!",
        "full_name": "Test User",
        "role": role,
        "department": "IT",
        "is_active": True,
    })
    assert resp.status_code == 200, f"Register failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_ticket(client, headers, overrides=None):
    payload = {**TICKET_PAYLOAD, **(overrides or {})}
    resp = client.post("/api/v1/tickets", json=payload, headers=headers)
    assert resp.status_code == 201, f"Ticket creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class TestCreateTicket:
    def test_create_success(self, client, auth_headers):
        resp = client.post("/api/v1/tickets", json=TICKET_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == TICKET_PAYLOAD["title"]
        assert data["status"] == "open"

    def test_create_unauthenticated_returns_401(self, client):
        resp = client.post("/api/v1/tickets", json=TICKET_PAYLOAD)
        assert resp.status_code == 401

    def test_create_missing_title_returns_422(self, client, auth_headers):
        payload = {k: v for k, v in TICKET_PAYLOAD.items() if k != "title"}
        resp = client.post("/api/v1/tickets", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_invalid_priority_returns_422(self, client, auth_headers):
        resp = client.post(
            "/api/v1/tickets",
            json={**TICKET_PAYLOAD, "priority": "not_a_priority"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

class TestListTickets:
    def test_list_returns_paginated_response(self, client, auth_headers):
        create_ticket(client, auth_headers)
        resp = client.get("/api/v1/tickets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_unauthenticated_returns_401(self, client):
        resp = client.get("/api/v1/tickets")
        assert resp.status_code == 401

    def test_list_filter_by_status(self, client, auth_headers):
        create_ticket(client, auth_headers)
        resp = client.get("/api/v1/tickets?status=open", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "open"

    def test_list_pagination(self, client, auth_headers):
        for i in range(3):
            create_ticket(client, auth_headers, {"title": f"Ticket {i}"})
        resp = client.get("/api/v1/tickets?page=1&page_size=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1


# ---------------------------------------------------------------------------
# GET SINGLE
# ---------------------------------------------------------------------------

class TestGetTicket:
    def test_get_ticket_success(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == ticket["id"]

    def test_get_nonexistent_ticket_returns_404(self, client, auth_headers):
        resp = client.get("/api/v1/tickets/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_unauthenticated_returns_401(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.get(f"/api/v1/tickets/{ticket['id']}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# UPDATE (PUT)
# ---------------------------------------------------------------------------

class TestUpdateTicket:
    def test_creator_can_update(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.put(
            f"/api/v1/tickets/{ticket['id']}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_admin_can_update_any_ticket(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        admin_h = register_and_headers(client, "admin_upd@example.com", role="admin")
        resp = client.put(
            f"/api/v1/tickets/{ticket['id']}",
            json={"title": "Admin Updated"},
            headers=admin_h,
        )
        assert resp.status_code == 200

    def test_non_creator_non_admin_returns_403(self, client, auth_headers):
        """ticket_service.update_ticket: creator OR admin only."""
        ticket = create_ticket(client, auth_headers)
        other_h = register_and_headers(client, "other@example.com", role="agent")
        resp = client.put(
            f"/api/v1/tickets/{ticket['id']}",
            json={"title": "Sneaky Edit"},
            headers=other_h,
        )
        assert resp.status_code == 403

    def test_update_nonexistent_ticket_returns_404(self, client, auth_headers):
        resp = client.put("/api/v1/tickets/999999", json={"title": "Ghost"}, headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# STATUS TRANSITIONS  (PATCH /{id}/status)
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    def test_open_to_in_progress(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(
            f"/api/v1/tickets/{ticket['id']}/status",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_in_progress_to_resolved(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "in_progress"}, headers=auth_headers)
        resp = client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "resolved"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_resolved_to_closed(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "in_progress"}, headers=auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "resolved"}, headers=auth_headers)
        resp = client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "closed"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_closed_is_terminal_returns_400(self, client, auth_headers):
        """CLOSED -> set() in VALID_TRANSITIONS. Raises 400 'Terminal state'."""
        ticket = create_ticket(client, auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "in_progress"}, headers=auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "resolved"}, headers=auth_headers)
        client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "closed"}, headers=auth_headers)
        resp = client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={"status": "open"}, headers=auth_headers)
        assert resp.status_code == 400
        

    def test_invalid_transition_open_to_closed_returns_400(self, client, auth_headers):
        """OPEN -> CLOSED is not in VALID_TRANSITIONS[OPEN]."""
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(
            f"/api/v1/tickets/{ticket['id']}/status",
            json={"status": "closed"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_invalid_status_value_returns_400(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(
            f"/api/v1/tickets/{ticket['id']}/status",
            json={"status": "flying"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_missing_status_field_returns_422(self, client, auth_headers):
        """tickets.py raises 422 explicitly when status key is absent."""
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(f"/api/v1/tickets/{ticket['id']}/status", json={}, headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# ASSIGN  (PATCH /{id}/assign)
# ---------------------------------------------------------------------------

class TestAssignTicket:
    def test_assign_sets_assignee_and_status(self, client, auth_headers):
        """
        Get assignee's id by having them create a ticket and reading created_by_id
        — avoids needing a /users/me endpoint.
        """
        assignee_h = register_and_headers(client, "assignee@example.com", role="agent")
        temp = create_ticket(client, assignee_h, {"title": "temp"})
        assignee_id = temp["created_by"]["id"]

        ticket = create_ticket(client, auth_headers)
        resp = client.patch(
            f"/api/v1/tickets/{ticket['id']}/assign",
            json={"assignee_id": assignee_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assigned_to"]["id"] == assignee_id
        assert data["status"] == "assigned"

    def test_assign_nonexistent_user_returns_404(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(
            f"/api/v1/tickets/{ticket['id']}/assign",
            json={"assignee_id": 999999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_assign_missing_assignee_id_returns_422(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.patch(f"/api/v1/tickets/{ticket['id']}/assign", json={}, headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE  (soft delete — admin only)
# ---------------------------------------------------------------------------

class TestDeleteTicket:
    def test_admin_can_soft_delete(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        admin_h = register_and_headers(client, "admin_d1@example.com", role="admin")
        resp = client.delete(f"/api/v1/tickets/{ticket['id']}", headers=admin_h)
        assert resp.status_code == 204

    def test_deleted_ticket_not_in_list(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        admin_h = register_and_headers(client, "admin_d2@example.com", role="admin")
        client.delete(f"/api/v1/tickets/{ticket['id']}", headers=admin_h)
        ids = [t["id"] for t in client.get("/api/v1/tickets", headers=auth_headers).json()["items"]]
        assert ticket["id"] not in ids

    def test_deleted_ticket_get_returns_404(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        admin_h = register_and_headers(client, "admin_d3@example.com", role="admin")
        client.delete(f"/api/v1/tickets/{ticket['id']}", headers=admin_h)
        resp = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers)
        assert resp.status_code == 404

    def test_non_admin_delete_returns_403(self, client, auth_headers):
        """ticket_service.soft_delete_ticket: role != ADMIN -> 403."""
        ticket = create_ticket(client, auth_headers)
        resp = client.delete(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_ticket_returns_404(self, client):
        admin_h = register_and_headers(client, "admin_d4@example.com", role="admin")
        resp = client.delete("/api/v1/tickets/999999", headers=admin_h)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# COMMENTS
# ---------------------------------------------------------------------------

class TestComments:
    def test_add_public_comment(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.post(
            f"/api/v1/tickets/{ticket['id']}/comments",
            json={"body": "Public comment", "is_internal": False},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_internal"] is False

    def test_viewer_cannot_post_internal_comment_returns_403(self, client):
        """ticket_service.add_comment: is_internal=True + role VIEWER -> 403."""
        viewer_h = register_and_headers(client, "viewer1@example.com", role="viewer")
        ticket = create_ticket(client, viewer_h)
        resp = client.post(
            f"/api/v1/tickets/{ticket['id']}/comments",
            json={"body": "Secret", "is_internal": True},
            headers=viewer_h,
        )
        assert resp.status_code == 403

    def test_agent_can_post_internal_comment(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.post(
            f"/api/v1/tickets/{ticket['id']}/comments",
            json={"body": "Internal note", "is_internal": True},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_internal"] is True

    def test_viewer_cannot_see_internal_comments(self, client, auth_headers):
        """ticket_service.get_comments: VIEWER role filters out is_internal=True."""
        ticket = create_ticket(client, auth_headers)
        client.post(
            f"/api/v1/tickets/{ticket['id']}/comments",
            json={"body": "Internal only", "is_internal": True},
            headers=auth_headers,
        )
        viewer_h = register_and_headers(client, "viewer2@example.com", role="viewer")
        resp = client.get(f"/api/v1/tickets/{ticket['id']}/comments", headers=viewer_h)
        assert resp.status_code == 200
        assert all(not c["is_internal"] for c in resp.json())

    def test_agent_sees_internal_comments(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        client.post(
            f"/api/v1/tickets/{ticket['id']}/comments",
            json={"body": "Internal note", "is_internal": True},
            headers=auth_headers,
        )
        resp = client.get(f"/api/v1/tickets/{ticket['id']}/comments", headers=auth_headers)
        assert resp.status_code == 200
        assert any(c["is_internal"] for c in resp.json())

    def test_comment_on_nonexistent_ticket_returns_404(self, client, auth_headers):
        resp = client.post(
            "/api/v1/tickets/999999/comments",
            json={"body": "ghost", "is_internal": False},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_comments_unauthenticated_returns_401(self, client, auth_headers):
        ticket = create_ticket(client, auth_headers)
        resp = client.get(f"/api/v1/tickets/{ticket['id']}/comments")
        assert resp.status_code == 401