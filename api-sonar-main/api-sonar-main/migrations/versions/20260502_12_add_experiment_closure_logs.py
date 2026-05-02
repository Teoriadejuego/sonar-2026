"""add experiment closure logs

Revision ID: 20260502_12
Revises: 20260502_11
Create Date: 2026-05-02 23:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_12"
down_revision = "20260502_11"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in _inspector().get_indexes(table_name)
    )


def upgrade() -> None:
    if not _has_table("experiment_closure_logs"):
        op.create_table(
            "experiment_closure_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("experiment_mode", sa.String(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("actor", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("session_count_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("session_state_counts_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("series_count_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("series_count_closed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("series_state_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if _has_table("experiment_closure_logs") and not _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_experiment_mode",
    ):
        op.create_index(
            "ix_experiment_closure_logs_experiment_mode",
            "experiment_closure_logs",
            ["experiment_mode"],
            unique=False,
        )
    if _has_table("experiment_closure_logs") and not _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_timestamp",
    ):
        op.create_index(
            "ix_experiment_closure_logs_timestamp",
            "experiment_closure_logs",
            ["timestamp"],
            unique=False,
        )
    if _has_table("experiment_closure_logs") and not _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_actor",
    ):
        op.create_index(
            "ix_experiment_closure_logs_actor",
            "experiment_closure_logs",
            ["actor"],
            unique=False,
        )
    if _has_table("experiment_closure_logs") and not _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_mode_timestamp",
    ):
        op.create_index(
            "ix_experiment_closure_logs_mode_timestamp",
            "experiment_closure_logs",
            ["experiment_mode", "timestamp"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("experiment_closure_logs") and _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_mode_timestamp",
    ):
        op.drop_index(
            "ix_experiment_closure_logs_mode_timestamp",
            table_name="experiment_closure_logs",
        )
    if _has_table("experiment_closure_logs") and _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_actor",
    ):
        op.drop_index(
            "ix_experiment_closure_logs_actor",
            table_name="experiment_closure_logs",
        )
    if _has_table("experiment_closure_logs") and _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_timestamp",
    ):
        op.drop_index(
            "ix_experiment_closure_logs_timestamp",
            table_name="experiment_closure_logs",
        )
    if _has_table("experiment_closure_logs") and _has_index(
        "experiment_closure_logs",
        "ix_experiment_closure_logs_experiment_mode",
    ):
        op.drop_index(
            "ix_experiment_closure_logs_experiment_mode",
            table_name="experiment_closure_logs",
        )
    if _has_table("experiment_closure_logs"):
        op.drop_table("experiment_closure_logs")
