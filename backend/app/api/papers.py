"""Papers endpoint — ingest PDFs or manual paper entries into the knowledge base."""

import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.agents import ingestion
from app.models.paper import IngestRequest, IngestResponse, PaperExtraction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])

_jobs: dict[str, dict] = {}  # In-memory job store for MVP; replace with Aurora


@router.post("/ingest", response_model=IngestResponse)
async def ingest_paper(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """Ingest a paper from a PDF URL or manual fields.

    Path 1 — pdf_url provided: agent downloads + extracts everything automatically.
    Path 2 — title + abstract provided: uses supplied fields, no PDF download needed.
    Both paths write embeddings to S3 Vectors and concept nodes to Neo4J.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "result": None, "error": None}
    background_tasks.add_task(_run_ingestion, job_id, request)
    return IngestResponse(job_id=job_id, status="pending", message="Ingestion queued")


async def _run_ingestion(job_id: str, request: IngestRequest) -> None:
    _jobs[job_id]["status"] = "running"
    try:
        if request.pdf_url:
            extraction = await ingestion.run(request.pdf_url, paper_id=request.paper_id)
        else:
            # Manual path — build a PaperExtraction from provided fields
            extraction = await ingestion.run_manual(
                paper_id=request.paper_id or str(uuid.uuid4()),
                title=request.title,
                authors=request.authors or [],
                abstract=request.abstract,
            )
        _jobs[job_id] = {"status": "completed", "result": extraction.model_dump(), "error": None}
    except Exception as exc:
        logger.error("Ingestion job %s failed: %s", job_id, exc)
        _jobs[job_id] = {"status": "failed", "result": None, "error": str(exc)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **_jobs[job_id]}
