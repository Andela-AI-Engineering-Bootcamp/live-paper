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
                # Accept [{name, email}] — filter out empty names
                author_list = [
                    {"name": a.get("name", "").strip(), "email": a.get("email", "").strip()}
                    for a in parsed
                    if isinstance(a, dict) and a.get("name", "").strip()
                ]
            else:
                raise ValueError("authors must be a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid authors format. Expected JSON array of {{name, email}} objects: {e}",
            )

    await db.create_paper(
        paper_id=pid,
        title=title or "Processing…",
        authors=[],  # ❗ DO NOT pre-fill authors
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


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── CRUD ─────────────────────────────────────────────────────────────────────

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
