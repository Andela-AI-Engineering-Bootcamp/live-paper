"""Aurora Serverless v2 (Postgres) connection and session management.

Uses SQLAlchemy async engine with connection pooling. Falls back to a
SQLite in-memory database when AURORA_CLUSTER_ARN is not set (dev mode),
so the team can run locally without AWS credentials.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.db import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _resolve_password(raw: str) -> str:
    """Aurora's managed master-user secret stores credentials as JSON
    ({"username": ..., "password": ...}). App Runner injects the whole
    secret string verbatim, so unwrap it here when present."""
    if raw.startswith("{"):
        try:
            return json.loads(raw).get("password", raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _build_url() -> str:
    cluster_arn = os.getenv("AURORA_CLUSTER_ARN", "")

    if not cluster_arn:
        logger.warning("AURORA_CLUSTER_ARN not set — using SQLite in-memory (dev mode)")
        return "sqlite+aiosqlite:///:memory:"

    host = os.getenv("AURORA_HOST", "")
    port = os.getenv("AURORA_PORT", "5432")
    db = os.getenv("AURORA_DATABASE", "livepaper")
    user = os.getenv("AURORA_USERNAME", "livepaper")
    password = _resolve_password(os.getenv("AURORA_PASSWORD", ""))

    return f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def _get_engine():
    global _engine
    if _engine is None:
        url = _build_url()
        is_sqlite = url.startswith("sqlite")
        _engine = create_async_engine(
            url,
            echo=os.getenv("DEBUG", "").lower() == "true",
            pool_size=5 if not is_sqlite else None,
            max_overflow=10 if not is_sqlite else None,
            pool_pre_ping=True if not is_sqlite else False,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session, rolling back on error."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables — called on app startup (dev only; prod uses Alembic)."""
    if not os.getenv("AURORA_CLUSTER_ARN", ""):
        engine = _get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Dev mode: SQLite tables created")


async def get_job(job_id: str) -> dict | None:
    """Fetch a job by ID — used by the /jobs/{id} polling endpoint."""
    from sqlalchemy import select
    from app.models.db import Job

    async with get_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None
        return {
            "job_id": job.id,
            "status": job.status,
            "created_at": job.created_at,
            "result": job.result,
            "error": job.error,
        }


async def create_job(job_id: str, job_type: str = "ingestion", paper_id: str | None = None) -> None:
    """Insert a new pending job row."""
    from app.models.db import Job

    async with get_session() as session:
        session.add(Job(id=job_id, job_type=job_type, paper_id=paper_id, status="pending"))


async def update_job(
    job_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Update job status, result, and error fields."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.db import Job

    async with get_session() as session:
        result_row = await session.execute(select(Job).where(Job.id == job_id))
        job = result_row.scalar_one_or_none()
        if not job:
            return
        job.status = status
        job.result = result
        job.error = error
        if trace_id:
            job.trace_id = trace_id
        if status in ("completed", "failed"):
            job.completed_at = datetime.now(timezone.utc)
