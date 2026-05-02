"""add experiment mode metadata columns

Revision ID: 20260502_10
Revises: 20260502_09
Create Date: 2026-05-02 18:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_10"
down_revision = "20260502_09"
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
    if _has_table("experiment_state") and not _has_column(
        "experiment_state",
        "experiment_mode_changed_at",
    ):
        op.add_column(
            "experiment_state",
            sa.Column("experiment_mode_changed_at", sa.DateTime(), nullable=True),
        )
    if _has_table("experiment_state") and not _has_column(
        "experiment_state",
        "experiment_mode_changed_by",
    ):
        op.add_column(
            "experiment_state",
            sa.Column("experiment_mode_changed_by", sa.String(), nullable=True),
        )
    if _has_table("experiment_state") and not _has_column(
        "experiment_state",
        "experiment_mode_reason",
    ):
        op.add_column(
            "experiment_state",
            sa.Column("experiment_mode_reason", sa.Text(), nullable=True),
        )
    if _has_table("experiment_state") and not _has_index(
        "experiment_state",
        "ix_experiment_state_experiment_mode_changed_by",
    ):
        op.create_index(
            "ix_experiment_state_experiment_mode_changed_by",
            "experiment_state",
            ["experiment_mode_changed_by"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("experiment_state") and _has_index(
        "experiment_state",
        "ix_experiment_state_experiment_mode_changed_by",
    ):
        op.drop_index(
            "ix_experiment_state_experiment_mode_changed_by",
            table_name="experiment_state",
        )
    if _has_table("experiment_state") and _has_column(
        "experiment_state",
        "experiment_mode_reason",
    ):
        op.drop_column("experiment_state", "experiment_mode_reason")
    if _has_table("experiment_state") and _has_column(
        "experiment_state",
        "experiment_mode_changed_by",
    ):
        op.drop_column("experiment_state", "experiment_mode_changed_by")
    if _has_table("experiment_state") and _has_column(
        "experiment_state",
        "experiment_mode_changed_at",
    ):
        op.drop_column("experiment_state", "experiment_mode_changed_at")
