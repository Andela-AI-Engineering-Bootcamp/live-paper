"""Initial schema — papers, jobs, experts, expert_responses, chat_messages, escalation_events.

Revision ID: 001
Revises:
Create Date: 2025-04-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authors", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("pdf_url", sa.String(2000)),
        sa.Column("key_concepts", ARRAY(sa.String), server_default="{}"),
        sa.Column("methods", ARRAY(sa.String), server_default="{}"),
        sa.Column("findings", ARRAY(sa.String), server_default="{}"),
        sa.Column("open_questions", ARRAY(sa.String), server_default="{}"),
        sa.Column("extraction_confidence", sa.Float, server_default="0"),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("paper_id", sa.String(64), sa.ForeignKey("papers.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("job_type", sa.String(30), nullable=False, server_default="ingestion"),
        sa.Column("result", JSONB),
        sa.Column("error", sa.Text),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_paper_id", "jobs", ["paper_id"])

    op.create_table(
        "experts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200)),
        sa.Column("affiliation", sa.String(300)),
        sa.Column("is_registered", sa.Boolean, server_default="false"),
        sa.Column("relevance_score", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "expert_responses",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("paper_id", sa.String(64), sa.ForeignKey("papers.id")),
        sa.Column("expert_id", sa.String(64), sa.ForeignKey("experts.id")),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("paper_ids", ARRAY(sa.String), server_default="{}"),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "escalation_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id")),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("gap_description", sa.Text),
        sa.Column("top_confidence", sa.Float),
        sa.Column("candidate_expert_ids", ARRAY(sa.String), server_default="{}"),
        sa.Column("source_paper_ids", ARRAY(sa.String), server_default="{}"),
        sa.Column("resolved", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("escalation_events")
    op.drop_table("chat_messages")
    op.drop_table("expert_responses")
    op.drop_table("experts")
    op.drop_table("jobs")
    op.drop_table("papers")
