"""Pydantic contracts for all five agent inputs and outputs.

Every agent reads one of these models and writes one of these models.
Nothing touches the database without passing through validation here.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PaperExtraction(BaseModel):
    """Output of the Ingestion Agent — structured knowledge pulled from a PDF."""
    title: str
    authors: list[str]
    key_concepts: list[str]
    methods: list[str]
    findings: list[str]
    open_questions: list[str]  # gaps the paper itself admits
    confidence: float = Field(ge=0.0, le=1.0)


class CitedPassage(BaseModel):
    """A single passage returned by the Retrieval Agent, with attribution."""
    text: str
    paper_title: str
    authors: list[str]
    page: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    """Output of the Retrieval Agent — ranked passages + escalation decision."""
    question: str
    passages: list[CitedPassage]
    top_confidence: float = Field(ge=0.0, le=1.0)
    escalate: bool  # True when top_confidence < GAP_CONFIDENCE_THRESHOLD


class Author(BaseModel):
    """A candidate expert identified by the Expert Router Agent."""
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)


class EscalationCard(BaseModel):
    """Output of the Expert Router Agent — structured question sent to an expert."""
    question: str
    gap_description: str
    candidate_authors: list[Author]
    source_paper_ids: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExpertResponse(BaseModel):
    """Output of the Response Ingestion Agent — expert answer ready for the graph."""
    expert_name: str = Field(min_length=1)
    affiliation: Optional[str] = None
    response_text: str = Field(min_length=1)
    source_paper_id: str = Field(min_length=1)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


# ── API request/response shapes ───────────────────────────────────────────────

class IngestRequest(BaseModel):
    pdf_url: Optional[str] = None  # public URL or S3 URI
    paper_id: Optional[str] = None  # if re-ingesting existing paper


class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str


class AskRequest(BaseModel):
    question: str
    paper_ids: Optional[list[str]] = None  # scope to specific papers


class AskResponse(BaseModel):
    question: str
    passages: list[CitedPassage]
    escalated: bool
    escalation_card: Optional[EscalationCard] = None
    trace_id: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | completed | failed
    created_at: datetime
    result: Optional[dict] = None
    error: Optional[str] = None
