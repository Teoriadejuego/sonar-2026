"""add followup claim fields for final-screen questions

Revision ID: 20260408_01
Revises: 20260324_01
Create Date: 2026-04-08 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_01"
down_revision = "20260324_01"
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
    new_columns = {
        "crowd_prediction_value": sa.Column(
            "crowd_prediction_value", sa.Integer(), nullable=True
        ),
        "crowd_prediction_submitted_at": sa.Column(
            "crowd_prediction_submitted_at", sa.DateTime(), nullable=True
        ),
        "social_recall_count": sa.Column(
            "social_recall_count", sa.Integer(), nullable=True
        ),
        "social_recall_correct": sa.Column(
            "social_recall_correct", sa.Boolean(), nullable=True
        ),
        "social_recall_submitted_at": sa.Column(
            "social_recall_submitted_at", sa.DateTime(), nullable=True
        ),
    }
    for column_name, column in new_columns.items():
        if not _has_column("claims", column_name):
            op.add_column("claims", column)

    if not _has_index("claims", "ix_claims_crowd_prediction_value"):
        op.create_index(
            "ix_claims_crowd_prediction_value",
            "claims",
            ["crowd_prediction_value"],
        )
    if not _has_index("claims", "ix_claims_social_recall_correct"):
        op.create_index(
            "ix_claims_social_recall_correct",
            "claims",
            ["social_recall_correct"],
        )


def downgrade() -> None:
    if _has_index("claims", "ix_claims_social_recall_correct"):
        op.drop_index("ix_claims_social_recall_correct", table_name="claims")
    if _has_index("claims", "ix_claims_crowd_prediction_value"):
        op.drop_index("ix_claims_crowd_prediction_value", table_name="claims")

    for column_name in [
        "social_recall_submitted_at",
        "social_recall_correct",
        "social_recall_count",
        "crowd_prediction_submitted_at",
        "crowd_prediction_value",
    ]:
        if _has_column("claims", column_name):
            op.drop_column("claims", column_name)
