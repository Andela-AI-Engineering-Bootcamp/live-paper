"""Papers endpoint — upload and ingest PDFs into the knowledge base."""

import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.agents import ingestion
from app.models.paper import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])

_jobs: dict[str, dict] = {}  # In-memory job store for MVP; replace with Aurora


@router.post("/ingest", response_model=IngestResponse)
async def ingest_paper(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """Trigger ingestion of a PDF from a URL. Returns a job_id for polling."""
    if not request.pdf_url:
        raise HTTPException(status_code=400, detail="pdf_url is required")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "result": None, "error": None}

    background_tasks.add_task(_run_ingestion, job_id, request.pdf_url)
    return IngestResponse(job_id=job_id, status="pending", message="Ingestion queued")


async def _run_ingestion(job_id: str, pdf_url: str) -> None:
    _jobs[job_id]["status"] = "running"
    try:
        extraction = await ingestion.run(pdf_url)
        _jobs[job_id] = {"status": "completed", "result": extraction.model_dump(), "error": None}
    except Exception as exc:
        logger.error("Ingestion job %s failed: %s", job_id, exc)
        _jobs[job_id] = {"status": "failed", "result": None, "error": str(exc)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **_jobs[job_id]}
