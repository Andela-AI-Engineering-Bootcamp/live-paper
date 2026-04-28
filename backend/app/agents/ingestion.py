"""Ingestion Agent — parses a PDF and extracts structured knowledge.

Pipeline:
  1. Download PDF from URL  (or receive pre-saved tmp file / manual fields)
  2. Extract text with PyMuPDF
  3. Run LLM enrichment via OpenAI Agents SDK → PaperExtraction (Pydantic-validated)
  4. Embed full abstract via embeddings service
  5. Write embedding to S3 Vectors
  6. Write concept/method/finding nodes to Neo4J
"""

import logging
import os
import tempfile
import uuid
from typing import Optional

import httpx        # type: ignore
import fitz         # PyMuPDF  # type: ignore
from agents import Agent, Runner, trace  # type: ignore

from app.agents.base import get_langfuse, get_model
from app.models.paper import PaperExtraction
from app.services import embeddings as embed_svc
from app.services import graph, storage

logger = logging.getLogger(__name__)

INSTRUCTIONS = """You are an expert research paper analyst.
Given the text of a research paper, extract structured knowledge as a JSON object.

Be precise and factual. Only extract what is explicitly stated in the paper.
For open_questions, identify gaps, limitations, and unanswered questions the authors themselves raise.
Set confidence based on how clearly the paper states its contributions (1.0 = crystal clear, 0.5 = implicit)."""


# ── Public entry points ───────────────────────────────────────────────────────

async def run(pdf_url: str, paper_id: Optional[str] = None) -> PaperExtraction:
    """Download, parse, and enrich a PDF. Returns validated PaperExtraction."""
    lf = get_langfuse()
    trace_obj = lf.trace(name="ingestion-agent", input={"pdf_url": pdf_url}) if lf else None

    try:
        text = await _extract_text(pdf_url)
        extraction = await _enrich(text, paper_id or pdf_url)

        await _store(extraction, paper_id or extraction.title[:50])

        if trace_obj:
            trace_obj.update(output=extraction.model_dump(), status="success")

        logger.info("Ingestion complete for paper: %s", extraction.title)
        return extraction

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        logger.error("Ingestion failed for %s: %s", pdf_url, exc)
        raise


async def run_from_file(tmp_path: str, paper_id: Optional[str] = None) -> PaperExtraction:
    """Ingest from an already-saved local PDF file (uploaded via multipart form)."""
    lf = get_langfuse()
    trace_obj = lf.trace(name="ingestion-agent-file", input={"paper_id": paper_id}) if lf else None
    try:
        text = _extract_text_from_path(tmp_path)
        pid = paper_id or str(uuid.uuid4())
        extraction = await _enrich(text, pid)

        await _store(extraction, pid)

        if trace_obj:
            trace_obj.update(output=extraction.model_dump(), status="success")
        return extraction

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        raise


async def run_manual(
    paper_id: str,
    title: Optional[str],
    authors: list[dict],        # [{name, email}] — from the ingest form
    abstract: Optional[str],
) -> PaperExtraction:
    """Manual ingestion path — enrich from provided fields without a PDF.

    `authors` is a list of dicts with 'name' and optional 'email' keys,
    matching the format sent by the admin dashboard form.
    """
    lf = get_langfuse()
    trace_obj = lf.trace(name="ingestion-agent-manual", input={"paper_id": paper_id}) if lf else None

    try:
        enrichment_text = abstract or title or ""
        extraction = await _enrich(enrichment_text, paper_id)

        # Override LLM-extracted fields with the admin-supplied values
        author_names = [a.get("name", "").strip() for a in authors if a.get("name", "").strip()]
        extraction = extraction.model_copy(update={
            "title": title or extraction.title,
            "authors": author_names or extraction.authors,
            "abstract": abstract or extraction.abstract,
        })

        await _store(extraction, paper_id)

        if trace_obj:
            trace_obj.update(output=extraction.model_dump(), status="success")
        return extraction

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        raise


# ── Private helpers ───────────────────────────────────────────────────────────

async def _store(extraction: PaperExtraction, paper_id: str) -> None:
    """Embed and persist an extraction to S3 Vectors and Neo4J."""
    vector = await embed_svc.embed(
        extraction.title + " " + " ".join(extraction.key_concepts)
    )
    await storage.store_embedding(
        text=extraction.title,
        vector=vector,
        metadata={
            "paper_id": paper_id,
            "title": extraction.title,
            "authors": ", ".join(extraction.authors),
            "findings": "; ".join(extraction.findings[:3]),
        },
        paper_id=paper_id,
    )
    await graph.write_paper_node(paper_id, {
        "title": extraction.title,
        "authors": extraction.authors,
    })
    await graph.write_concept_nodes(paper_id, extraction.key_concepts)


async def _extract_text(pdf_url: str) -> str:
    """Download PDF from URL and extract plain text."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(pdf_url)
        response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        return _extract_text_from_path(tmp_path)
    finally:
        os.unlink(tmp_path)


def _extract_text_from_path(path: str) -> str:
    """Extract plain text from a local PDF file."""
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text[:12000]     # cap to avoid blowing the LLM context window


async def _enrich(text: str, paper_id: str) -> PaperExtraction:
    """Run LLM enrichment and return a validated PaperExtraction."""
    model = get_model()
    agent = Agent(
        name="IngestionAgent",
        instructions=INSTRUCTIONS,
        model=model,
        output_type=PaperExtraction,
    )
    with trace(f"Ingest {paper_id}"):
        result = await Runner.run(
            agent,
            input=f"Extract knowledge from this paper:\n\n{text}",
            max_turns=3,
        )
    return result.final_output_as(PaperExtraction)
