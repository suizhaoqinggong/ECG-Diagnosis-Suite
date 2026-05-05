from __future__ import annotations

import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import MetaData, inspect, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models.db_models import Base

import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
logger = logging.getLogger("alembic.env")


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _reset_legacy_sqlite_schema_if_needed(connection) -> None:
    if connection.dialect.name != "sqlite" or settings.is_production:
        return

    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    if "alembic_version" in table_names:
        version_rows = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM alembic_version"
        ).scalar_one()
        if version_rows:
            return
    else:
        version_rows = 0

    if not table_names or (table_names == {"alembic_version"} and version_rows == 0):
        return

    managed_tables = {table.name for table in target_metadata.sorted_tables}
    existing_managed_tables = sorted((table_names - {"alembic_version"}) & managed_tables)
    if not existing_managed_tables:
        return

    logger.warning(
        "Legacy SQLite schema detected without Alembic metadata. "
        "Resetting managed tables before applying migrations."
    )
    metadata = MetaData()
    metadata.reflect(bind=connection, only=existing_managed_tables)
    metadata.drop_all(bind=connection)
    if "alembic_version" in table_names:
        connection.exec_driver_sql("DROP TABLE alembic_version")


def do_run_migrations(connection) -> None:
    _reset_legacy_sqlite_schema_if_needed(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
