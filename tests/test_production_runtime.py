import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import Settings
from app.core.database import init_db
from app.services import diagnosis_service


class _AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_production_uses_database_rate_limit_backend_by_default():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-real-secret",
    )
    assert settings.effective_rate_limit_backend == "database"


def test_get_model_service_requires_checkpoint_in_production():
    with patch.object(diagnosis_service.settings, "ENVIRONMENT", "production"):
        with patch(
            "app.core.config.Settings.get_model_checkpoint_path",
            return_value=None,
        ):
            with patch.object(diagnosis_service, "_model_service", None):
                with pytest.raises(RuntimeError) as exc_info:
                    diagnosis_service.get_model_service()

    assert "Model checkpoint not found" in str(exc_info.value)


def test_init_db_requires_migrations_in_production():
    mock_conn = SimpleNamespace(run_sync=AsyncMock(return_value=[]))
    mock_engine = SimpleNamespace(begin=lambda: _AsyncContextManager(mock_conn))

    with patch("app.core.database.settings.ENVIRONMENT", "production"):
        with patch("app.core.database.engine", mock_engine):
            with pytest.raises(RuntimeError) as exc_info:
                asyncio.run(init_db())

    assert "alembic upgrade head" in str(exc_info.value)


def test_init_db_recreates_legacy_sqlite_schema_without_alembic(tmp_path):
    db_path = tmp_path / "legacy.sqlite"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    try:
        with sync_engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE users (
                    id INTEGER NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    created_at DATETIME,
                    PRIMARY KEY (id),
                    UNIQUE (username),
                    UNIQUE (email)
                )
                """
            )

        async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        try:
            with patch("app.core.database.engine", async_engine):
                asyncio.run(init_db())
        finally:
            asyncio.run(async_engine.dispose())

        columns = {
            column["name"]
            for column in sa_inspect(sync_engine).get_columns("users")
        }
        assert "display_name" in columns
        assert "is_active" in columns
        assert "updated_at" in columns
        assert "username" not in columns
    finally:
        sync_engine.dispose()
