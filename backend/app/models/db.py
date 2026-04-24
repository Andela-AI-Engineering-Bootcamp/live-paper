"""SQLAlchemy ORM models for Aurora Serverless v2 (Postgres).

Three storage tiers:
  - Aurora (here)      — relational: papers, jobs, experts, chat history
  - Neo4J              — graph: concept/paper/expert relationships
  - S3 Vectors         — vector: embeddings for semantic search
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
    types,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class StringList(types.TypeDecorator):
    """ARRAY(String) on Postgres, JSON list on SQLite — keeps production
    schema unchanged while still letting tests run against SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())


class JSONDict(types.TypeDecorator):
    """JSONB on Postgres, JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(64), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    authors = Column(StringList, nullable=False, default=list)
    abstract = Column(Text, default="")
    pdf_url = Column(String(2000))
    status = Column(String(20), nullable=False, default="pending")  # pending|running|completed|failed
    key_concepts = Column(StringList, default=list)
    methods = Column(StringList, default=list)
    findings = Column(StringList, default=list)
    open_questions = Column(StringList, default=list)
    extraction_confidence = Column(Float, default=0.0)
    vector_id = Column(String(64))  # pointer into S3 Vectors
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    jobs = relationship("Job", back_populates="paper", cascade="all, delete-orphan")
    expert_responses = relationship("ExpertResponseRecord", back_populates="paper")


class Job(Base):
    """Tracks async ingestion and escalation jobs."""
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, default=_uuid)
    paper_id = Column(String(64), ForeignKey("papers.id"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|running|completed|failed
    job_type = Column(String(30), nullable=False, default="ingestion")  # ingestion|escalation
    result = Column(JSONDict)
    error = Column(Text)
    trace_id = Column(String(64))  # LangFuse trace ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    paper = relationship("Paper", back_populates="jobs")


class Expert(Base):
    __tablename__ = "experts"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    email = Column(String(200))
    affiliation = Column(String(300))
    is_registered = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    responses = relationship("ExpertResponseRecord", back_populates="expert")


class ExpertResponseRecord(Base):
    __tablename__ = "expert_responses"

    id = Column(String(64), primary_key=True, default=_uuid)
    paper_id = Column(String(64), ForeignKey("papers.id"))
    expert_id = Column(String(64), ForeignKey("experts.id"))
    question = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    vector_id = Column(String(64))  # embedding stored in S3 Vectors
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    paper = relationship("Paper", back_populates="expert_responses")
    expert = relationship("Expert", back_populates="responses")


class ChatMessage(Base):
    """Conversation history for multi-turn question sessions."""
    __tablename__ = "chat_messages"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(10), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    paper_ids = Column(StringList, default=list)  # papers in scope
    trace_id = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EscalationEvent(Base):
    """Audit trail for every gap-detected escalation."""
    __tablename__ = "escalation_events"

    id = Column(String(64), primary_key=True, default=_uuid)
    job_id = Column(String(64), ForeignKey("jobs.id"))
    question = Column(Text, nullable=False)
    gap_description = Column(Text)
    top_confidence = Column(Float)
    candidate_expert_ids = Column(StringList, default=list)
    source_paper_ids = Column(StringList, default=list)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
