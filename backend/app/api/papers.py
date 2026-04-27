"""Papers endpoint — ingest and manage research papers.

Backed by Aurora via app.services.database helpers; no in-memory state, so
running multiple uvicorn workers (or being scheduled across App Runner
instances later) does not split the read-after-write view a client sees.
"""

import logging
import os
import json
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.agents import ingestion
from app.models.paper import IngestResponse
from app.services import database as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_paper(
    background_tasks: BackgroundTasks,
    pdf_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    paper_id: Optional[str] = Form(None),
) -> IngestResponse:
    has_url    = bool(pdf_url)
    has_file   = pdf_file is not None and pdf_file.filename
    has_manual = bool(title and abstract)

    if not has_url and not has_file and not has_manual:
        raise HTTPException(
            status_code=422,
            detail="Provide pdf_url, upload a pdf_file, or supply title + abstract.",
        )

    pid    = paper_id or str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    # Parse authors from JSON string array [{"name": "...", "email": "..."}]
    # Falls back gracefully if authors is None or malformed.
    author_list: list[dict] = []
    if authors:
        try:
            parsed = json.loads(authors)
            if isinstance(parsed, list):
                author_list = [
                    {"name": a.get("name", "").strip(), "email": a.get("email", "").strip()}
                    if isinstance(a, dict)
                    else {"name": str(a).strip(), "email": ""}
                    for a in parsed
                    if (a.get("name", "") if isinstance(a, dict) else str(a)).strip()
                ]
            else:
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            # Accept plain comma-separated string: "Smith, J.; Doe, A."
            author_list = [
                {"name": n.strip(), "email": ""}
                for n in authors.replace(";", ",").split(",")
                if n.strip()
            ]

    await db.create_paper(
        paper_id=pid,
        title=title or "Processing…",
        authors=author_list,
        abstract=abstract or "",
        status="pending",
        pdf_url=pdf_url,
    )
    await db.create_job(job_id=job_id, job_type="ingestion", paper_id=pid)

    tmp_path = None
    if has_file and not has_url:
        content = await pdf_file.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

    background_tasks.add_task(
        _run_ingestion,
        job_id=job_id,
        paper_id=pid,
        pdf_url=pdf_url,
        tmp_path=tmp_path,
        title=title,
        authors=author_list,
        abstract=abstract,
    )

    return IngestResponse(job_id=job_id, status="pending", message="Ingestion queued")


async def _run_ingestion(
    job_id: str,
    paper_id: str,
    pdf_url: Optional[str],
    tmp_path: Optional[str],
    title: Optional[str],
    authors: list[dict],
    abstract: Optional[str],
) -> None:
    """Background task: run ingestion agent and update job + paper records."""
    import asyncio
    await db.update_job(job_id, status="running")
    try:
        if tmp_path:
            extraction = await ingestion.run_from_file(tmp_path, paper_id=paper_id)
        elif pdf_url:
            extraction = await ingestion.run(pdf_url, paper_id=paper_id)
        else:
            extraction = await ingestion.run_manual(
                paper_id=paper_id,
                title=title or "",
                authors=[a.get("name", "") for a in authors],
                abstract=abstract or "",
            )
        await db.update_paper(
            paper_id,
            title=extraction.title,
            authors=[a for a in (a.get("name", "") for a in authors) if a] or extraction.authors,
            key_concepts=extraction.key_concepts,
            methods=extraction.methods,
            findings=extraction.findings,
            open_questions=extraction.open_questions,
            extraction_confidence=extraction.confidence,
            status="completed",
        )
        await db.update_job(job_id, status="completed", result={"title": extraction.title})
    except Exception as exc:
        logger.error("Ingestion failed for paper %s: %s", paper_id, exc)
        await db.update_paper(paper_id, status="failed")
        await db.update_job(job_id, status="failed", error=str(exc))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_papers() -> list[dict]:
    return await db.list_papers()


@router.get("/{paper_id}")
async def get_paper(paper_id: str) -> dict:
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.put("/{paper_id}")
async def update_paper(paper_id: str, updates: dict) -> dict:
    paper = await db.update_paper(paper_id, **updates)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(paper_id: str) -> None:
    deleted = await db.delete_paper(paper_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found")