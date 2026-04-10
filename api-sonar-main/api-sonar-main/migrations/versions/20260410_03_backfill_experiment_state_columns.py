"""backfill missing experiment_state control columns

Revision ID: 20260410_03
Revises: 20260408_02
Create Date: 2026-04-10 22:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_03"
down_revision = "20260408_02"
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
        column["name"] == column_name for column in _inspector().get_columns(table_name)
    )


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("experiment_state"):
        return

    if not _has_column("experiment_state", "experiment_status"):
        op.add_column(
            "experiment_state",
            sa.Column("experiment_status", sa.String(), nullable=True),
        )
    if not _has_column("experiment_state", "paused_at"):
        op.add_column(
            "experiment_state",
            sa.Column("paused_at", sa.DateTime(), nullable=True),
        )
    if not _has_column("experiment_state", "resumed_at"):
        op.add_column(
            "experiment_state",
            sa.Column("resumed_at", sa.DateTime(), nullable=True),
        )
    if not _has_column("experiment_state", "pause_reason"):
        op.add_column(
            "experiment_state",
            sa.Column("pause_reason", sa.Text(), nullable=True),
        )

    op.execute(
        """
        UPDATE experiment_state
        SET experiment_status = COALESCE(experiment_status, 'active')
        """
    )

    if not _has_index("experiment_state", "ix_experiment_state_experiment_status"):
        op.create_index(
            "ix_experiment_state_experiment_status",
            "experiment_state",
            ["experiment_status"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("experiment_state", "ix_experiment_state_experiment_status"):
        op.drop_index(
            "ix_experiment_state_experiment_status",
            table_name="experiment_state",
        )
    for column_name in ["pause_reason", "resumed_at", "paused_at", "experiment_status"]:
        if _has_column("experiment_state", column_name):
            op.drop_column("experiment_state", column_name)
