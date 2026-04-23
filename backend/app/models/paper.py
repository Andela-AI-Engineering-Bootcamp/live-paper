"""Pydantic contracts for all five agent inputs and outputs.

Every agent reads one of these models and writes one of these models.
Nothing touches the database without passing through validation here.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


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
    # Path 1 — PDF URL (ingestion agent downloads + extracts everything)
    pdf_url: Optional[str] = None

    # Path 2 — Manual fields (no PDF needed; pdf_url takes priority if both provided)
    paper_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    abstract: Optional[str] = None

    @model_validator(mode="after")
    def require_pdf_url_or_manual_fields(self) -> "IngestRequest":
        has_pdf = bool(self.pdf_url)
        has_manual = bool(self.title and self.abstract)
        if not has_pdf and not has_manual:
            raise ValueError("Provide either pdf_url or (title + abstract)")
        return self


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
