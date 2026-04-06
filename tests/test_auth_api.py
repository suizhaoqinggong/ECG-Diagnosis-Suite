"""
Business regression tests for auth API endpoints.

Covers register, login, refresh, logout, change-password, delete-account, and me.
These are integration tests using TestClient with dependency overrides to
mock the database layer.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.core.rate_limit import rate_limiter


def _make_mock_session():
    """Create an AsyncMock session that works with `async with Session() as s:`."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


def _mock_user(id=1, email="test@example.com", display_name="Tester", hashed_password="hash"):
    """Create a mock User ORM object."""
    user = MagicMock()
    user.id = id
    user.email = email
    user.display_name = display_name
    user.hashed_password = hashed_password
    return user


def _mock_refresh_token(user_id=1, family_id="abc123"):
    """Create a mock RefreshToken ORM object."""
    from datetime import datetime, timedelta, timezone
    token = MagicMock()
    token.user_id = user_id
    token.family_id = family_id
    token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token.revoked_at = None
    token.replaced_by_id = None
    token.id = 1
    token.user = _mock_user(id=user_id)
    return token


# ===========================================================================
# Register
# ===========================================================================


class TestRegister:
    @patch("app.api.auth.verify_password")
    @patch("app.api.auth.get_password_hash", return_value="hashed_pw")
    @patch("app.api.auth._validate_origin")
    def test_register_success(self, mock_origin, mock_hash, mock_verify, client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        # After commit, user should have an id
        def set_user_id(user):
            user.id = 1
        mock_session.refresh.side_effect = set_user_id

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            with patch("app.api.auth._set_refresh_cookie"):
                response = client.post(
                    "/api/auth/register",
                    json={"email": "new@example.com", "password": "password123"},
                )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"

    @patch("app.api.auth._validate_origin")
    def test_register_duplicate_email(self, mock_origin, client):
        mock_session = _make_mock_session()
        existing_user = _mock_user()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
        )

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            response = client.post(
                "/api/auth/register",
                json={"email": "test@example.com", "password": "password123"},
            )
        assert response.status_code == 400

    def test_register_short_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "1234567"},
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422


# ===========================================================================
# Login
# ===========================================================================


class TestLogin:
    @patch("app.api.auth.verify_password", return_value=True)
    @patch("app.api.auth._validate_origin")
    def test_login_success(self, mock_origin, mock_verify, client):
        mock_user = _mock_user()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            with patch("app.api.auth._set_refresh_cookie"):
                response = client.post(
                    "/api/auth/login",
                    json={"email": "test@example.com", "password": "password123"},
                )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    @patch("app.api.auth.verify_password", return_value=False)
    @patch("app.api.auth._validate_origin")
    def test_login_wrong_password(self, mock_origin, mock_verify, client):
        mock_user = _mock_user()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user))
        )

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
            )
        assert response.status_code == 401

    @patch("app.api.auth._validate_origin")
    def test_login_nonexistent_user(self, mock_origin, client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            response = client.post(
                "/api/auth/login",
                json={"email": "noone@example.com", "password": "password123"},
            )
        assert response.status_code == 401


# ===========================================================================
# Refresh
# ===========================================================================


class TestRefresh:
    @patch("app.api.auth._validate_origin")
    def test_refresh_no_cookie(self, mock_origin, client):
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401
        assert "No refresh token" in response.json()["detail"]

    @patch("app.api.auth._validate_origin")
    def test_refresh_expired_token(self, mock_origin, client):
        from datetime import datetime, timedelta, timezone
        mock_token = _mock_refresh_token()
        mock_token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_token))
        )

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            with patch("app.api.auth._set_refresh_cookie"):
                response = client.post("/api/auth/refresh", cookies={"rt": "some-token"})
        assert response.status_code == 401

    @patch("app.api.auth.create_access_token", return_value=("new-access-token", None))
    @patch("app.api.auth._validate_origin")
    def test_refresh_success_rotates_token(self, mock_origin, mock_access, client):
        mock_token = _mock_refresh_token()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_token)),
                MagicMock(rowcount=1),
            ]
        )
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            with patch("app.api.auth._set_refresh_cookie"):
                response = client.post("/api/auth/refresh", cookies={"rt": "valid-token"})
        assert response.status_code == 200
        assert response.json()["access_token"] == "new-access-token"

    @patch("app.api.auth._validate_origin")
    def test_refresh_rejects_token_when_rotation_already_claimed(self, mock_origin, client):
        mock_token = _mock_refresh_token()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_token)),
                MagicMock(rowcount=0),
            ]
        )
        mock_session.rollback = AsyncMock()

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            response = client.post("/api/auth/refresh", cookies={"rt": "valid-token"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired refresh token"
        mock_session.rollback.assert_awaited()


# ===========================================================================
# Logout
# ===========================================================================


class TestLogout:
    @patch("app.api.auth._validate_origin")
    def test_logout_clears_cookie(self, mock_origin, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        # Check that rt cookie is cleared
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert any('"rt"' in h or 'rt=' in h for h in set_cookie_headers)

    @patch("app.api.auth._validate_origin")
    def test_logout_with_valid_cookie_revokes_token(self, mock_origin, client):
        mock_token = _mock_refresh_token()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_token))
        )
        mock_session.commit = AsyncMock()

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            response = client.post("/api/auth/logout", cookies={"rt": "valid-token"})
        assert response.status_code == 200
        mock_session.commit.assert_awaited()


# ===========================================================================
# Me
# ===========================================================================


class TestMe:
    def test_me_without_auth_returns_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401


# ===========================================================================
# Change Password
# ===========================================================================


class TestChangePassword:
    def test_change_password_requires_auth(self, client):
        response = client.post(
            "/api/auth/change-password",
            json={"old_password": "old", "new_password": "newpassword"},
        )
        assert response.status_code == 401
