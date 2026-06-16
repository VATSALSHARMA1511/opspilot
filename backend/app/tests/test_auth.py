"""
Tests for /api/v1/auth/*.

Verified against the actual auth.py you shared:
  - POST /register returns {access_token, refresh_token, token_type} directly
    (no user object), default status 200.
  - Duplicate email on /register returns 409, not 400.
  - POST /login returns the same token shape, 401 on bad credentials.
  - POST /refresh returns ONLY {access_token, token_type} -- no refresh_token.
  - POST /logout returns 204 and deletes the Redis-stored refresh token hash,
    but does NOT blacklist the access token itself (it's a stateless JWT).
    So a previously-issued access token keeps working until it expires --
    logout only prevents that token from being *refreshed* again.

STILL UNVERIFIED (ask Vatsal to share these to tighten further):
  - app/schemas/user.py -> exact required fields/types for UserCreate.
    test_user_payload below guesses role="agent", department="IT",
    is_active=True; fix these if your enum values differ.
  - app/models/enums.py -> actual UserRole values.
  - app/core/security.py -> does decode_token() raise a caught exception
    (-> clean 401) or an unhandled jose.JWTError (-> 500) on a garbage
    token string? test_refresh_with_invalid_token_rejected assumes 401.
"""


class TestRegister:
    def test_register_success_returns_tokens(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "StrongPass123!",
                "full_name": "New User",
                "role": "agent",
                "department": "IT",
                "is_active": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_returns_409(self, client, test_user_payload):
        client.post("/api/v1/auth/register", json=test_user_payload)
        response = client.post("/api/v1/auth/register", json=test_user_payload)
        assert response.status_code == 409


class TestLogin:
    def test_login_success_returns_tokens(self, client, test_user_payload):
        client.post("/api/v1/auth/register", json=test_user_payload)
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_payload["email"],
                "password": test_user_payload["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_rejected(self, client, test_user_payload):
        client.post("/api/v1/auth/register", json=test_user_payload)
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_payload["email"],
                "password": "TotallyWrongPassword!",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_rejected(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_login_inactive_user_rejected(self, client, test_user_payload):
        inactive_payload = {**test_user_payload, "is_active": False}
        client.post("/api/v1/auth/register", json=inactive_payload)
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_payload["email"],
                "password": inactive_payload["password"],
            },
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_returns_new_access_token_only(self, client, test_user_payload):
        register_resp = client.post("/api/v1/auth/register", json=test_user_payload)
        refresh_token = register_resp.json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # /refresh intentionally does not rotate/return a new refresh_token
        assert "refresh_token" not in data

    def test_refresh_with_garbage_token_rejected(self, client):
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        # NOTE: this assumes decode_token() raises/handles invalid tokens such
        # that FastAPI surfaces a 401. If decode_token lets a jose.JWTError
        # bubble up uncaught, this will actually come back as a 500 -- worth
        # confirming against core/security.py.
        assert response.status_code == 401

    def test_refresh_after_logout_rejected(self, client, test_user_payload):
        register_resp = client.post("/api/v1/auth/register", json=test_user_payload)
        tokens = register_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        client.post("/api/v1/auth/logout", headers=headers)

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client, auth_headers):
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 204

    def test_access_token_still_works_after_logout(self, client, auth_headers):
        """
        Logout only revokes the refresh token in Redis -- the access token
        is a stateless JWT with no blocklist check in get_current_user, so
        it keeps working until it naturally expires. This documents that
        behavior rather than assuming the opposite.
        """
        client.post("/api/v1/auth/logout", headers=auth_headers)
        response = client.get("/api/v1/tickets", headers=auth_headers)
        assert response.status_code == 200
