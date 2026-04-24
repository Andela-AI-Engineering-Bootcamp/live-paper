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
        # Multi-worker uvicorn (--workers 2 in the Dockerfile) gives every
        # process its own ":memory:" database, so a job created by worker A
        # is invisible to worker B's polling request. Default to a shared
        # file path on disk for any environment that opts in via SQLITE_PATH;
        # tests leave it unset so they keep the fast in-memory path.
        sqlite_path = os.getenv("SQLITE_PATH", ":memory:")
        logger.warning(
            "AURORA_CLUSTER_ARN not set — using SQLite at %s (dev mode)", sqlite_path
        )
        if sqlite_path == ":memory:":
            return "sqlite+aiosqlite:///:memory:"
        # Three slashes + leading absolute path == four slashes total, which
        # is SQLAlchemy's syntax for an absolute filesystem path.
        return f"sqlite+aiosqlite:///{sqlite_path}"

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
        kwargs: dict = {"echo": os.getenv("DEBUG", "").lower() == "true"}
        # SQLite/aiosqlite uses StaticPool which rejects pool_size/max_overflow
        # outright (even =None). Only set them for the Aurora/Postgres path.
        if not url.startswith("sqlite"):
            kwargs["pool_size"] = 5
            kwargs["max_overflow"] = 10
            kwargs["pool_pre_ping"] = True
        _engine = create_async_engine(url, **kwargs)
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
            "paper_id": job.paper_id,
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


# ── Papers ────────────────────────────────────────────────────────────────────
# Plain-dict returns rather than ORM objects so callers can hand them straight
# to FastAPI without lazy-load surprises after the session closes.

_PAPER_FIELDS = (
    "id", "title", "authors", "abstract", "pdf_url", "status",
    "key_concepts", "methods", "findings", "open_questions",
    "extraction_confidence", "vector_id",
)


def _paper_to_dict(p) -> dict:
    return {f: getattr(p, f) for f in _PAPER_FIELDS}


async def create_paper(
    paper_id: str,
    title: str,
    authors: list[str],
    abstract: str = "",
    status: str = "pending",
    pdf_url: str | None = None,
) -> None:
    """Insert a row in papers; safe to call multiple times — silently no-ops if
    the row already exists (so re-ingesting an existing paper_id reuses it)."""
    from sqlalchemy import select
    from app.models.db import Paper

    async with get_session() as session:
        existing = await session.execute(select(Paper.id).where(Paper.id == paper_id))
        if existing.scalar_one_or_none():
            return
        session.add(Paper(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            status=status,
            pdf_url=pdf_url,
        ))


async def update_paper(paper_id: str, **fields) -> dict | None:
    """Patch a paper row. Unknown keys are ignored so callers can pass dicts
    that contain extra fields without crashing."""
    from sqlalchemy import select
    from app.models.db import Paper

    async with get_session() as session:
        result = await session.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        if not paper:
            return None
        for key, value in fields.items():
            if key in _PAPER_FIELDS and key != "id":
                setattr(paper, key, value)
        await session.flush()
        return _paper_to_dict(paper)


async def get_paper(paper_id: str) -> dict | None:
    from sqlalchemy import select
    from app.models.db import Paper

    async with get_session() as session:
        result = await session.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        return _paper_to_dict(paper) if paper else None


async def list_papers() -> list[dict]:
    from sqlalchemy import select
    from app.models.db import Paper

    async with get_session() as session:
        result = await session.execute(select(Paper).order_by(Paper.created_at.desc()))
        return [_paper_to_dict(p) for p in result.scalars().all()]


async def delete_paper(paper_id: str) -> bool:
    """Returns True if a row was deleted, False if no such paper existed."""
    from sqlalchemy import select
    from app.models.db import Paper

    async with get_session() as session:
        result = await session.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        if not paper:
            return False
        await session.delete(paper)
        return True


# ── Experts ───────────────────────────────────────────────────────────────────

async def upsert_expert(
    email: str,
    name: str | None = None,
    affiliation: str | None = None,
    is_registered: bool = False,
) -> str:
    """Find an expert by email or insert one. Returns the expert id. Email is
    treated as the natural identifier even though the schema PK is a uuid;
    that lets the inviter pass just an email and the form submitter look the
    same person up later without a coordination step."""
    import uuid
    from sqlalchemy import select
    from app.models.db import Expert

    if not email:
        raise ValueError("email is required to upsert an expert")

    async with get_session() as session:
        result = await session.execute(select(Expert).where(Expert.email == email))
        expert = result.scalar_one_or_none()
        if expert:
            if name and not expert.name:
                expert.name = name
            if affiliation and not expert.affiliation:
                expert.affiliation = affiliation
            if is_registered:
                expert.is_registered = True
            return expert.id

        new_id = str(uuid.uuid4())
        session.add(Expert(
            id=new_id,
            name=name or email.split("@")[0],
            email=email,
            affiliation=affiliation,
            is_registered=is_registered,
        ))
        return new_id


async def get_expert(expert_id: str) -> dict | None:
    """Return an expert with the papers they've responded to attached as full
    paper objects (matches the frontend Expert.papers shape)."""
    from sqlalchemy import select
    from app.models.db import Expert, ExpertResponseRecord, Paper

    async with get_session() as session:
        result = await session.execute(select(Expert).where(Expert.id == expert_id))
        expert = result.scalar_one_or_none()
        if not expert:
            return None
        papers_result = await session.execute(
            select(Paper)
            .join(ExpertResponseRecord, ExpertResponseRecord.paper_id == Paper.id)
            .where(ExpertResponseRecord.expert_id == expert_id)
            .distinct()
        )
        return _expert_to_dict(expert, [_paper_to_dict(p) for p in papers_result.scalars().all()])


async def list_experts() -> list[dict]:
    from sqlalchemy import select
    from app.models.db import Expert, ExpertResponseRecord, Paper

    async with get_session() as session:
        experts = (await session.execute(select(Expert).order_by(Expert.created_at.desc()))).scalars().all()
        if not experts:
            return []
        # One round-trip for the join; group in Python so the N+1 doesn't bite.
        rows = (await session.execute(
            select(ExpertResponseRecord.expert_id, Paper)
            .join(Paper, Paper.id == ExpertResponseRecord.paper_id)
        )).all()
        papers_by_expert: dict[str, list[dict]] = {}
        for expert_id, paper in rows:
            papers_by_expert.setdefault(expert_id, []).append(_paper_to_dict(paper))
        return [_expert_to_dict(e, papers_by_expert.get(e.id, [])) for e in experts]


def _expert_to_dict(expert, papers: list[dict]) -> dict:
    return {
        "id": expert.id,
        "name": expert.name,
        "email": expert.email,
        "affiliation": expert.affiliation,
        "bio": "",  # not in schema yet — frontend tolerates empty string
        "is_registered": expert.is_registered,
        "papers": papers,
    }


# ── Expert responses ──────────────────────────────────────────────────────────

async def create_expert_response(
    paper_id: str,
    expert_id: str,
    question: str,
    response_text: str,
    vector_id: str | None = None,
) -> str:
    """Insert an expert response row. Returns the new response id. `question`
    is required by the schema; for paper-level reviews (no specific question)
    callers should pass a placeholder like 'General expert review'."""
    import uuid
    from app.models.db import ExpertResponseRecord

    response_id = str(uuid.uuid4())
    async with get_session() as session:
        session.add(ExpertResponseRecord(
            id=response_id,
            paper_id=paper_id,
            expert_id=expert_id,
            question=question,
            response_text=response_text,
            vector_id=vector_id,
        ))
    return response_id
