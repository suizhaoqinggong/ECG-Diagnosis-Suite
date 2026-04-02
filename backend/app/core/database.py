"""
Database configuration and session management
"""
import logging
from dataclasses import dataclass

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
    echo=settings.DEBUG,
    future=True,
)

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """初始化数据库"""
    Base = _get_base()
    # Ensure all models are imported so they register with Base.metadata
    import app.models.user  # noqa: F401
    import app.models.refresh_token  # noqa: F401
    import app.models.chat  # noqa: F401

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
    database_status.ready = True
    database_status.error = None
    logger.info("Database initialized: %s", settings.DATABASE_URL)


def mark_db_unavailable(error: Exception) -> None:
    database_status.ready = False
    database_status.error = str(error)


def get_database_status() -> DatabaseStatus:
    return database_status


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
