"""
Database configuration and session management
"""
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import MetaData, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DatabaseStatus:
    ready: bool = False
    error: Optional[str] = None


database_status = DatabaseStatus()


def _get_base():
    """Lazy import Base to avoid circular imports."""
    from app.models.db_models import Base
    return Base


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
)

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _mask_url_password(url: str) -> str:
    """Replace the password in a database URL with *** for safe logging."""
    parsed = urllib.parse.urlparse(url)
    if parsed.password:
        masked = parsed._replace(
            netloc=f"{parsed.username}:***@{parsed.hostname}"
            + (f":{parsed.port}" if parsed.port else "")
        )
        return urllib.parse.urlunparse(masked)
    return url


def _find_missing_managed_columns(sync_conn, metadata, table_names: set[str]) -> dict[str, list[str]]:
    """Return missing managed columns for already-existing tables.

    This catches legacy development databases where a managed table exists,
    but its schema predates the current ORM models.
    """
    inspector = inspect(sync_conn)
    managed_tables = {table.name: table for table in metadata.sorted_tables}
    issues: dict[str, list[str]] = {}

    for table_name in table_names:
        table = managed_tables.get(table_name)
        if table is None:
            continue
        existing_columns = {
            column_info["name"] for column_info in inspector.get_columns(table_name)
        }
        missing_columns = sorted(
            column.name for column in table.columns
            if column.name not in existing_columns
        )
        if missing_columns:
            issues[table_name] = missing_columns

    return issues


def _format_schema_issues(issues: dict[str, list[str]]) -> str:
    return "; ".join(
        f"{table} missing [{', '.join(columns)}]"
        for table, columns in sorted(issues.items())
    )


def _drop_existing_tables(sync_conn, table_names: set[str]) -> None:
    if not table_names:
        return

    metadata = MetaData()
    metadata.reflect(bind=sync_conn, only=sorted(table_names))
    metadata.drop_all(bind=sync_conn)


async def init_db():
    """初始化数据库"""
    Base = _get_base()
    # Ensure all models are imported so they register with Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        table_names = set(
            await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        )

        if "alembic_version" not in table_names:
            if settings.is_production:
                raise RuntimeError(
                    "Database migrations are required in production. "
                    "Run `alembic upgrade head` before starting the app."
                )

            managed_table_names = {
                table.name for table in Base.metadata.sorted_tables
            }
            existing_managed_tables = table_names & managed_table_names

            if existing_managed_tables:
                schema_issues = await conn.run_sync(
                    lambda sync_conn: _find_missing_managed_columns(
                        sync_conn,
                        Base.metadata,
                        existing_managed_tables,
                    )
                )
                if schema_issues:
                    schema_details = _format_schema_issues(schema_issues)
                    dialect_name = await conn.run_sync(
                        lambda sync_conn: sync_conn.dialect.name
                    )
                    if dialect_name == "sqlite":
                        logger.warning(
                            "Legacy SQLite schema detected without Alembic metadata (%s). "
                            "Resetting local database schema.",
                            schema_details,
                        )
                        await conn.run_sync(
                            lambda sync_conn: _drop_existing_tables(
                                sync_conn,
                                table_names,
                            )
                        )
                    else:
                        raise RuntimeError(
                            "Database schema is out of date. "
                            f"{schema_details}. Run `alembic upgrade head`."
                        )

            await conn.run_sync(Base.metadata.create_all)
    database_status.ready = True
    database_status.error = None
    logger.info("Database initialized: %s", _mask_url_password(settings.DATABASE_URL))


def mark_db_unavailable(error: Exception) -> None:
    database_status.ready = False
    database_status.error = "database unavailable"


def get_database_status() -> DatabaseStatus:
    return database_status


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
