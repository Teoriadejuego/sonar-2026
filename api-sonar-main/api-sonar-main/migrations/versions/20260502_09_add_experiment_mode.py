"""add experiment mode to global experiment state

Revision ID: 20260502_09
Revises: 20260502_08
Create Date: 2026-05-02 18:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_09"
down_revision = "20260502_08"
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
        "experiment_mode",
    ):
        op.add_column(
            "experiment_state",
            sa.Column(
                "experiment_mode",
                sa.String(),
                nullable=False,
                server_default="live",
            ),
        )
        op.execute(
            sa.text(
                "UPDATE experiment_state "
                "SET experiment_mode = 'live' "
                "WHERE experiment_mode IS NULL OR experiment_mode = ''"
            )
        )
    if _has_table("experiment_state") and not _has_index(
        "experiment_state",
        "ix_experiment_state_experiment_mode",
    ):
        op.create_index(
            "ix_experiment_state_experiment_mode",
            "experiment_state",
            ["experiment_mode"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("experiment_state") and _has_index(
        "experiment_state",
        "ix_experiment_state_experiment_mode",
    ):
        op.drop_index(
            "ix_experiment_state_experiment_mode",
            table_name="experiment_state",
        )
    if _has_table("experiment_state") and _has_column(
        "experiment_state",
        "experiment_mode",
    ):
        op.drop_column("experiment_state", "experiment_mode")
