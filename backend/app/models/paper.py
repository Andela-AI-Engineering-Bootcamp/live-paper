"""Pydantic models for the papers domain.

These are the data-transfer objects used across agents and API endpoints.
They are separate from the SQLAlchemy ORM models in app/models/db.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Author ────────────────────────────────────────────────────────────────────

class Author(BaseModel):
    """Author of a paper — used in EscalationCard and PaperExtraction."""
    name: str
    email: Optional[str] = None          # required for email dispatch
    affiliation: Optional[str] = None
    relevance_score: float = 0.0


# ── Paper extraction (output of ingestion agent) ──────────────────────────────

class PaperExtraction(BaseModel):
    """Structured knowledge extracted from a paper by the ingestion agent."""
    title: str
    authors: list[str] = Field(default_factory=list)   # plain name strings
    abstract: str = ""
    key_concepts: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    confidence: float = 0.8


# ── Retrieval ─────────────────────────────────────────────────────────────────

class CitedPassage(BaseModel):
    """A single retrieved passage with provenance."""
    text: str
    paper_title: str
    authors: list[str] = Field(default_factory=list)   # plain name strings
    confidence: float = 0.0


class RetrievalResult(BaseModel):
    """Full output of the retrieval agent."""
    question: str
    passages: list[CitedPassage] = Field(default_factory=list)
    top_confidence: float = 0.0
    escalate: bool = False


# ── Expert response (submitted via the expert-response page) ──────────────────

class ExpertResponse(BaseModel):
    """An expert's reply to an escalated question."""
    expert_name: str
    affiliation: Optional[str] = None
    source_paper_id: str
    response_text: str


# ── Escalation ────────────────────────────────────────────────────────────────

class EscalationCard(BaseModel):
    """Structured escalation card produced by the expert router."""
    question: str
    gap_description: str
    candidate_authors: list[Author] = Field(default_factory=list)
    source_paper_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Ingest API ────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    """Returned immediately when an ingestion job is queued."""
    job_id: str
    status: str
    message: str
