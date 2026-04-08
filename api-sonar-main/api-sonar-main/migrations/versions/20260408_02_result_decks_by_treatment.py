"""scope result decks by treatment and cycle

Revision ID: 20260408_02
Revises: 20260408_01
Create Date: 2026-04-08 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_02"
down_revision = "20260408_01"
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
    if not _has_column("result_decks", "treatment_key"):
        op.add_column(
            "result_decks",
            sa.Column("treatment_key", sa.String(), nullable=True),
        )
    if not _has_column("result_decks", "treatment_cycle_index"):
        op.add_column(
            "result_decks",
            sa.Column("treatment_cycle_index", sa.Integer(), nullable=True),
        )

    op.execute(
        """
        UPDATE result_decks
        SET treatment_key = COALESCE(treatment_key, '__legacy_global__')
        """
    )
    op.execute(
        """
        UPDATE result_decks
        SET treatment_cycle_index = COALESCE(
            treatment_cycle_index,
            CASE
                WHEN deck_index > 0 THEN deck_index
                ELSE ABS(deck_index) + 1000000
            END
        )
        """
    )

    if not _has_index("result_decks", "ix_result_decks_treatment_key"):
        op.create_index(
            "ix_result_decks_treatment_key",
            "result_decks",
            ["treatment_key"],
        )
    if not _has_index("result_decks", "ix_result_decks_treatment_cycle_index"):
        op.create_index(
            "ix_result_decks_treatment_cycle_index",
            "result_decks",
            ["treatment_cycle_index"],
        )
    if not _has_index("result_decks", "ux_result_decks_treatment_cycle"):
        op.create_index(
            "ux_result_decks_treatment_cycle",
            "result_decks",
            ["treatment_key", "treatment_cycle_index"],
            unique=True,
        )


def downgrade() -> None:
    if _has_index("result_decks", "ux_result_decks_treatment_cycle"):
        op.drop_index("ux_result_decks_treatment_cycle", table_name="result_decks")
    if _has_index("result_decks", "ix_result_decks_treatment_cycle_index"):
        op.drop_index("ix_result_decks_treatment_cycle_index", table_name="result_decks")
    if _has_index("result_decks", "ix_result_decks_treatment_key"):
        op.drop_index("ix_result_decks_treatment_key", table_name="result_decks")
    if _has_column("result_decks", "treatment_cycle_index"):
        op.drop_column("result_decks", "treatment_cycle_index")
    if _has_column("result_decks", "treatment_key"):
        op.drop_column("result_decks", "treatment_key")
