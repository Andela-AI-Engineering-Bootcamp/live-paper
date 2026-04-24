"""Add abstract and status columns to papers — needed when papers move from
the in-memory `_papers` dict (which always carried both fields) to Aurora.
status doubles as the ingestion job's mirror so list views can show
"pending" / "completed" / "failed" without joining against jobs.

Revision ID: 002
Revises: 001
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column("abstract", sa.Text(), nullable=True, server_default=""),
    )
    op.add_column(
        "papers",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("papers", "status")
    op.drop_column("papers", "abstract")
