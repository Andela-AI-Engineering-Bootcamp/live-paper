"""Alembic migration environment — async SQLAlchemy + Aurora Serverless v2."""

import asyncio
import json
import os
from logging.config import fileConfig
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_password(raw: str) -> str:
    """Mirror app.services.database._resolve_password — Aurora's managed
    master-user secret stores credentials as JSON, and App Runner injects
    the whole secret string verbatim into AURORA_PASSWORD."""
    if raw.startswith("{"):
        try:
            return json.loads(raw).get("password", raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _url() -> str:
    user = quote_plus(os.getenv("AURORA_USERNAME", "livepaper"))
    password = quote_plus(_resolve_password(os.getenv("AURORA_PASSWORD", "")))
    host = os.getenv("AURORA_HOST", "localhost")
    port = os.getenv("AURORA_PORT", "5432")
    db = os.getenv("AURORA_DATABASE", "livepaper")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_url())
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
