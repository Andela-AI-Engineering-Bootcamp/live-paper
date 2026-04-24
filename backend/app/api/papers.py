"""Papers endpoint — ingest and manage research papers."""

import uuid
import logging
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form

from app.agents import ingestion
from app.models.paper import IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])

# In-memory stores for MVP — both wired to Aurora in production
_jobs: dict[str, dict] = {}
_papers: dict[str, dict] = {}


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_paper(
    background_tasks: BackgroundTasks,
    # Path 1 — PDF URL
    pdf_url: Optional[str] = Form(None),
    # Path 2 — file upload
    pdf_file: Optional[UploadFile] = File(None),
    # Path 3 — manual fields
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),   # comma-separated string
    abstract: Optional[str] = Form(None),
    # Optional — reuse an existing paper_id (prevents duplicates)
    paper_id: Optional[str] = Form(None),
) -> IngestResponse:
    """Single ingest entry point supporting three input paths:

    1. pdf_url  — agent downloads the PDF and extracts everything automatically
    2. pdf_file — uploaded file saved to temp storage, then same pipeline as (1)
    3. title + abstract — manual entry, no PDF required

    Priority: pdf_url > pdf_file > manual. Returns a job_id for polling.
    Rejects with 422 when none of the three paths can be satisfied.
    """
    has_url = bool(pdf_url)
    has_file = pdf_file is not None and pdf_file.filename
    has_manual = bool(title and abstract)

    if not has_url and not has_file and not has_manual:
        raise HTTPException(
            status_code=422,
            detail="Provide pdf_url, upload a pdf_file, or supply title + abstract.",
        )

    pid = paper_id or str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    # Auto-create pending paper and job rows immediately
    _papers[pid] = {
        "id": pid,
        "title": title or "Processing…",
        "authors": [a.strip() for a in authors.split(",")] if authors else [],
        "abstract": abstract or "",
        "status": "pending",
    }
    _jobs[job_id] = {"status": "pending", "paper_id": pid, "result": None, "error": None}

    # Save uploaded file to temp path so the background task can read it
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
        authors=[a.strip() for a in authors.split(",")] if authors else [],
        abstract=abstract,
    )

    return IngestResponse(job_id=job_id, status="pending", message="Ingestion queued")


async def _run_ingestion(
    job_id: str,
    paper_id: str,
    pdf_url: Optional[str],
    tmp_path: Optional[str],
    title: Optional[str],
    authors: list[str],
    abstract: Optional[str],
) -> None:
    _jobs[job_id]["status"] = "running"
    try:
        if pdf_url:
            extraction = await ingestion.run(pdf_url, paper_id=paper_id)
        elif tmp_path:
            extraction = await ingestion.run_from_file(tmp_path, paper_id=paper_id)
        else:
            extraction = await ingestion.run_manual(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
            )

        result = extraction.model_dump()
        _jobs[job_id] = {"status": "completed", "paper_id": paper_id, "result": result, "error": None}
        _papers[paper_id].update({
            "title": extraction.title,
            "authors": extraction.authors,
            "status": "completed",
            "key_concepts": extraction.key_concepts,
            "findings": extraction.findings,
        })
    except Exception as exc:
        logger.error("Ingestion job %s failed: %s", job_id, exc)
        _jobs[job_id] = {"status": "failed", "paper_id": paper_id, "result": None, "error": str(exc)}
        _papers[paper_id]["status"] = "failed"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **_jobs[job_id]}


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_papers() -> list[dict]:
    return list(_papers.values())


@router.get("/{paper_id}")
async def get_paper(paper_id: str) -> dict:
    if paper_id not in _papers:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _papers[paper_id]


@router.put("/{paper_id}")
async def update_paper(paper_id: str, updates: dict) -> dict:
    if paper_id not in _papers:
        raise HTTPException(status_code=404, detail="Paper not found")
    _papers[paper_id].update(updates)
    return _papers[paper_id]


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(paper_id: str) -> None:
    if paper_id not in _papers:
        raise HTTPException(status_code=404, detail="Paper not found")
    del _papers[paper_id]
