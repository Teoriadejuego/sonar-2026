"""operational notes and qr tracking

Revision ID: 20260319_02
Revises: 20260319_01
Create Date: 2026-03-19 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_02"
down_revision = "20260319_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_notes",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("cleared_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_operational_notes_status", "operational_notes", ["status"], unique=False
    )
    op.create_index(
        "ix_operational_notes_effective_from",
        "operational_notes",
        ["effective_from"],
        unique=False,
    )

    for table_name in ["sessions", "claims", "payments", "payout_requests", "interest_signups", "telemetry_events"]:
        op.add_column(
            table_name,
            sa.Column("operational_note_id", sa.String(), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("operational_note_text", sa.Text(), nullable=True),
        )
        op.create_index(
            f"ix_{table_name}_operational_note_id",
            table_name,
            ["operational_note_id"],
            unique=False,
        )

    op.add_column("sessions", sa.Column("qr_entry_code", sa.String(), nullable=True))
    op.create_index("ix_sessions_qr_entry_code", "sessions", ["qr_entry_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessions_qr_entry_code", table_name="sessions")
    op.drop_column("sessions", "qr_entry_code")

    for table_name in ["telemetry_events", "interest_signups", "payout_requests", "payments", "claims", "sessions"]:
        op.drop_index(f"ix_{table_name}_operational_note_id", table_name=table_name)
        op.drop_column(table_name, "operational_note_text")
        op.drop_column(table_name, "operational_note_id")

    op.drop_index("ix_operational_notes_effective_from", table_name="operational_notes")
    op.drop_index("ix_operational_notes_status", table_name="operational_notes")
    op.drop_table("operational_notes")
