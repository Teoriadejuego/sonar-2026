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


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in _inspector().get_columns(table_name)
    )


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in _inspector().get_indexes(table_name)
    )


def upgrade() -> None:
    if not _has_table("operational_notes"):
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
    if not _has_index("operational_notes", "ix_operational_notes_status"):
        op.create_index(
            "ix_operational_notes_status", "operational_notes", ["status"], unique=False
        )
    if not _has_index("operational_notes", "ix_operational_notes_effective_from"):
        op.create_index(
            "ix_operational_notes_effective_from",
            "operational_notes",
            ["effective_from"],
            unique=False,
        )

    for table_name in ["sessions", "claims", "payments", "payout_requests", "interest_signups", "telemetry_events"]:
        if not _has_column(table_name, "operational_note_id"):
            op.add_column(
                table_name,
                sa.Column("operational_note_id", sa.String(), nullable=True),
            )
        if not _has_column(table_name, "operational_note_text"):
            op.add_column(
                table_name,
                sa.Column("operational_note_text", sa.Text(), nullable=True),
            )
        index_name = f"ix_{table_name}_operational_note_id"
        if _has_table(table_name) and not _has_index(table_name, index_name):
            op.create_index(
                index_name,
                table_name,
                ["operational_note_id"],
                unique=False,
            )

    if not _has_column("sessions", "qr_entry_code"):
        op.add_column("sessions", sa.Column("qr_entry_code", sa.String(), nullable=True))
    if _has_table("sessions") and not _has_index("sessions", "ix_sessions_qr_entry_code"):
        op.create_index("ix_sessions_qr_entry_code", "sessions", ["qr_entry_code"], unique=False)


def downgrade() -> None:
    if _has_index("sessions", "ix_sessions_qr_entry_code"):
        op.drop_index("ix_sessions_qr_entry_code", table_name="sessions")
    if _has_column("sessions", "qr_entry_code"):
        op.drop_column("sessions", "qr_entry_code")

    for table_name in ["telemetry_events", "interest_signups", "payout_requests", "payments", "claims", "sessions"]:
        index_name = f"ix_{table_name}_operational_note_id"
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        if _has_column(table_name, "operational_note_text"):
            op.drop_column(table_name, "operational_note_text")
        if _has_column(table_name, "operational_note_id"):
            op.drop_column(table_name, "operational_note_id")

    if _has_index("operational_notes", "ix_operational_notes_effective_from"):
        op.drop_index("ix_operational_notes_effective_from", table_name="operational_notes")
    if _has_index("operational_notes", "ix_operational_notes_status"):
        op.drop_index("ix_operational_notes_status", table_name="operational_notes")
    if _has_table("operational_notes"):
        op.drop_table("operational_notes")
