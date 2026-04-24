"""
Business regression tests for chat API endpoints.

Covers session CRUD, message listing, message creation (batch + idempotency),
and delete-all.  Uses TestClient with dependency overrides to mock the auth
layer and patches AsyncSessionLocal for database interactions.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.core.auth_dependencies import get_current_user
from app.core.rate_limit import rate_limiter


def _make_mock_session():
    """Create an AsyncMock session that works with `async with Session() as s:`."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _mock_user(id=1, email="test@example.com", display_name="Tester"):
    """Create a mock User ORM object."""
    user = MagicMock()
    user.id = id
    user.email = email
    user.display_name = display_name
    user.is_active = True
    return user


TEST_USER = _mock_user()
VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def auth_client():
    """TestClient with get_current_user overridden to return TEST_USER."""
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


def _mock_session_orm(session_id=VALID_UUID, title="Test", user_id=1):
    """Create a mock ChatSession ORM object."""
    from app.models.chat import ChatSession
    s = MagicMock(spec=ChatSession)
    s.id = session_id
    s.title = title
    s.user_id = user_id
    s.updated_at = datetime.now(timezone.utc)
    return s


def _mock_message_orm(
    msg_id=VALID_UUID,
    session_id=VALID_UUID,
    role="user",
    type="prompt",
    title=None,
    content="hello",
    status="completed",
):
    """Create a mock ChatMessage ORM object."""
    from app.models.chat import ChatMessage
    m = MagicMock(spec=ChatMessage)
    m.id = msg_id
    m.session_id = session_id
    m.role = role
    m.type = type
    m.title = title
    m.content = content
    m.status = status
    m.attachments = None
    m.result = None
    m.created_at = datetime.now(timezone.utc)
    return m


# ===========================================================================
# Session List
# ===========================================================================


class TestListSessions:
    def test_returns_empty_list(self, auth_client):
        mock_session = _make_mock_session()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get("/api/chat/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_sessions(self, auth_client):
        mock_session = _make_mock_session()
        s1 = _mock_session_orm(session_id="11111111-1111-4111-b111-111111111111", title="First")
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [s1]
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get("/api/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "First"


# ===========================================================================
# Session Create
# ===========================================================================


class TestCreateSession:
    def test_create_success(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        orm_session = _mock_session_orm()
        mock_session.refresh = AsyncMock(return_value=None)

        # refresh sets the real updated_at on the mock object
        def _refresh(obj):
            obj.updated_at = datetime.now(timezone.utc)
        mock_session.refresh.side_effect = _refresh

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                "/api/chat/sessions",
                json={"id": VALID_UUID, "title": "New Session"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == VALID_UUID
        assert data["title"] == "New Session"

    def test_rejects_invalid_uuid(self, auth_client):
        response = auth_client.post(
            "/api/chat/sessions",
            json={"id": "not-a-uuid", "title": "Bad"},
        )
        assert response.status_code == 422

    def test_rejects_missing_title(self, auth_client):
        response = auth_client.post(
            "/api/chat/sessions",
            json={"id": VALID_UUID},
        )
        assert response.status_code == 422

    def test_duplicate_session_returns_409(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(
            side_effect=IntegrityError("insert", {"id": VALID_UUID}, Exception("dup"))
        )
        mock_session.rollback = AsyncMock()

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                "/api/chat/sessions",
                json={"id": VALID_UUID, "title": "New Session"},
            )

        assert response.status_code == 409
        assert response.json()["detail"] == "Session already exists"
        mock_session.rollback.assert_awaited_once()


# ===========================================================================
# Session Get
# ===========================================================================


class TestGetSession:
    def test_get_existing_session(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=orm))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(f"/api/chat/sessions/{VALID_UUID}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test"

    def test_get_nonexistent_session_returns_404(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(f"/api/chat/sessions/{VALID_UUID}")
        assert response.status_code == 404


# ===========================================================================
# Session Update
# ===========================================================================


class TestUpdateSession:
    def test_update_title(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=orm))
        )
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.patch(
                f"/api/chat/sessions/{VALID_UUID}",
                json={"title": "Updated Title"},
            )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_nonexistent_returns_404(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.patch(
                f"/api/chat/sessions/{VALID_UUID}",
                json={"title": "Updated"},
            )
        assert response.status_code == 404


# ===========================================================================
# Session Delete
# ===========================================================================


class TestDeleteSession:
    def test_delete_existing_session(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=orm))
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.delete(f"/api/chat/sessions/{VALID_UUID}")
        assert response.status_code == 204

    def test_delete_nonexistent_returns_404(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.delete(f"/api/chat/sessions/{VALID_UUID}")
        assert response.status_code == 404


# ===========================================================================
# Delete All Sessions
# ===========================================================================


class TestDeleteAllSessions:
    def test_delete_all(self, auth_client):
        mock_session = _make_mock_session()
        s1 = _mock_session_orm(session_id="11111111-1111-4111-b111-111111111111")
        s2 = _mock_session_orm(session_id="22222222-2222-4222-b222-222222222222")
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [s1, s2]
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock))
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.delete("/api/chat/sessions")
        assert response.status_code == 204
        assert mock_session.delete.await_count == 2


# ===========================================================================
# List Messages
# ===========================================================================


class TestListMessages:
    def test_returns_empty_for_session(self, auth_client):
        mock_session = _make_mock_session()
        # First execute: session ownership check
        # Second execute: message listing
        orm = _mock_session_orm()
        scalars_empty = MagicMock()
        scalars_empty.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(scalars=MagicMock(return_value=scalars_empty)),
            ]
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(f"/api/chat/sessions/{VALID_UUID}/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_404_for_nonexistent_session(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(f"/api/chat/sessions/{VALID_UUID}/messages")
        assert response.status_code == 404

    def test_returns_messages(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        msg = _mock_message_orm(content="Hello world", title="Clinical note")
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [msg]

        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(scalars=MagicMock(return_value=scalars_mock)),
            ]
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(f"/api/chat/sessions/{VALID_UUID}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Clinical note"
        assert data[0]["content"] == "Hello world"

    def test_invalid_cursor_returns_400(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_mock_session_orm()))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.get(
                f"/api/chat/sessions/{VALID_UUID}/messages?cursor=not-a-timestamp,{VALID_UUID}"
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid cursor"


# ===========================================================================
# Create Messages (batch + idempotency)
# ===========================================================================


class TestCreateMessages:
    def _make_message_payload(self, msg_id=VALID_UUID):
        return {
            "id": msg_id,
            "role": "user",
            "type": "prompt",
            "title": "Submitted ECG for review",
            "content": "test",
            "status": "completed",
        }

    def test_create_success(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        # execute 1: session check, execute 2: existing IDs check (empty)
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(all=MagicMock(return_value=[])),
            ]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        # refresh must populate created_at (normally set by DB default)
        def _set_created_at(obj):
            obj.created_at = datetime.now(timezone.utc)
        mock_session.refresh = AsyncMock(side_effect=_set_created_at)

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                f"/api/chat/sessions/{VALID_UUID}/messages",
                json={"messages": [self._make_message_payload()]},
            )
        assert response.status_code == 201
        created_message = mock_session.add.call_args_list[0].args[0]
        assert created_message.title == "Submitted ECG for review"

    def test_idempotent_when_all_ids_exist(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        msg = _mock_message_orm()
        # execute 1: session check
        # execute 2: existing IDs check (all exist)
        # execute 3: fetch existing messages
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [msg]
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(all=MagicMock(return_value=[(VALID_UUID, VALID_UUID)])),
                MagicMock(scalars=MagicMock(return_value=scalars_mock)),
            ]
        )
        mock_session.commit = AsyncMock()

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                f"/api/chat/sessions/{VALID_UUID}/messages",
                json={"messages": [self._make_message_payload()]},
            )
        assert response.status_code == 201

    def test_partial_duplicate_returns_409(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()
        other_id = "33333333-3333-4333-b333-333333333333"
        # execute 1: session check
        # execute 2: existing IDs check (partial)
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(all=MagicMock(return_value=[(VALID_UUID, VALID_UUID)])),
            ]
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                f"/api/chat/sessions/{VALID_UUID}/messages",
                json={
                    "messages": [
                        self._make_message_payload(),
                        self._make_message_payload(msg_id=other_id),
                    ]
                },
            )
        assert response.status_code == 409
        assert "duplicate" in response.json()["detail"].lower()

    def test_rejects_message_ids_owned_by_another_session(self, auth_client):
        mock_session = _make_mock_session()
        orm = _mock_session_orm()

        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=orm)),
                MagicMock(all=MagicMock(return_value=[(VALID_UUID, "another-session-id")])),
            ]
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                f"/api/chat/sessions/{VALID_UUID}/messages",
                json={"messages": [self._make_message_payload()]},
            )

        assert response.status_code == 409
        assert response.json()["detail"] == "Message IDs already belong to another session"

    def test_returns_404_for_nonexistent_session(self, auth_client):
        mock_session = _make_mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("app.api.chat.AsyncSessionLocal", return_value=mock_session):
            response = auth_client.post(
                f"/api/chat/sessions/{VALID_UUID}/messages",
                json={"messages": [self._make_message_payload()]},
            )
        assert response.status_code == 404


# ===========================================================================
# Auth requirement
# ===========================================================================


class TestChatAuthRequired:
    def test_sessions_require_auth(self):
        """All chat endpoints should return 401 without a valid token."""
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/chat/sessions")
        assert response.status_code == 401
