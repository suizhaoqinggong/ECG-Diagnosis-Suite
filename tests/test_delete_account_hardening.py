"""
Security tests for delete-account password confirmation.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.core.auth_dependencies import get_current_user
from app.core.rate_limit import rate_limiter


def _make_mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _mock_user(id=1, email="test@example.com", display_name="Tester", hashed_password="hashed_pw"):
    user = MagicMock()
    user.id = id
    user.email = email
    user.display_name = display_name
    user.hashed_password = hashed_password
    user.is_active = True
    return user


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def auth_client():
    user = _mock_user()

    async def _override():
        return user

    app.dependency_overrides[get_current_user] = _override
    client = TestClient(app, raise_server_exceptions=False)
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


class TestDeleteAccountPasswordConfirmation:
    def test_delete_requires_password_field(self, auth_client):
        client, user = auth_client
        response = client.post("/api/auth/delete-account", json={})
        assert response.status_code == 422

    @patch("app.api.auth._validate_origin")
    def test_delete_with_wrong_password_fails(self, mock_origin, auth_client):
        client, user = auth_client
        mock_session = _make_mock_session()

        with (
            patch("app.api.auth.verify_password", return_value=False),
            patch("app.api.auth.AsyncSessionLocal", return_value=mock_session),
        ):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "wrong"},
            )

        assert response.status_code == 401

    @patch("app.api.auth._validate_origin")
    def test_delete_with_correct_password_succeeds(self, mock_origin, auth_client):
        client, user = auth_client
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        with (
            patch("app.api.auth.verify_password", return_value=True),
            patch("app.api.auth.AsyncSessionLocal", return_value=mock_session),
        ):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "correct"},
            )

        assert response.status_code == 200
        assert response.json()["message"] == "Account deleted"

    @patch("app.api.auth._validate_origin")
    def test_delete_clears_refresh_cookie(self, mock_origin, auth_client):
        client, user = auth_client
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        with (
            patch("app.api.auth.verify_password", return_value=True),
            patch("app.api.auth.AsyncSessionLocal", return_value=mock_session),
        ):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "correct"},
            )

        assert response.status_code == 200
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert any('"rt"' in h or "rt=" in h for h in set_cookie_headers)
