"""
Database configuration and session management
"""
import logging
import urllib.parse
from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DatabaseStatus:
    ready: bool = False
    error: str | None = None


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


async def init_db():
    """初始化数据库"""
    Base = _get_base()
    # Ensure all models are imported so they register with Base.metadata
    import app.models.user  # noqa: F401
    import app.models.refresh_token  # noqa: F401
    import app.models.chat  # noqa: F401
    import app.models.rate_limit  # noqa: F401

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
