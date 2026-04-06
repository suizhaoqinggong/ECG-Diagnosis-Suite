import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.core.auth_dependencies import get_current_user
from app.core.rate_limit import rate_limiter


def _make_mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _mock_user(id=1, email="test@example.com", display_name="Tester", hashed_password="hash"):
    user = MagicMock()
    user.id = id
    user.email = email
    user.display_name = display_name
    user.hashed_password = hashed_password
    user.is_active = True
    return user


VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_client():
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def _mock_chat_session(session_id=VALID_UUID, title="Test", user_id=1):
    session = MagicMock()
    session.id = session_id
    session.title = title
    session.user_id = user_id
    session.updated_at = datetime.now(timezone.utc)
    return session


class TestAuthRateLimits:
    @patch("app.api.auth.verify_password", return_value=True)
    @patch("app.api.auth._validate_origin")
    def test_login_rate_limited_by_email(self, mock_origin, mock_verify, client):
        mock_user = _mock_user()
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        with patch("app.api.auth.AsyncSessionLocal", return_value=mock_session):
            with patch("app.api.auth._set_refresh_cookie"):
                for _ in range(5):
                    response = client.post(
                        "/api/auth/login",
                        json={"email": "test@example.com", "password": "password123"},
                    )
                    assert response.status_code == 200

                response = client.post(
                    "/api/auth/login",
                    json={"email": "test@example.com", "password": "password123"},
                )

        assert response.status_code == 429
        assert "Too many login attempts" in response.json()["detail"]


class TestChatRateLimits:
    def test_create_session_rate_limited_per_user(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "updated_at", datetime.now(timezone.utc))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            for idx in range(30):
                response = auth_client.post(
                    "/api/chat/sessions",
                    json={
                        "id": f"550e8400-e29b-41d4-a716-{idx:012d}",
                        "title": f"Session {idx}",
                    },
                )
                assert response.status_code == 201

            response = auth_client.post(
                "/api/chat/sessions",
                json={
                    "id": "550e8400-e29b-41d4-a716-999999999999",
                    "title": "Blocked",
                },
            )

        assert response.status_code == 429
        assert "Too many chat write requests" in response.json()["detail"]
