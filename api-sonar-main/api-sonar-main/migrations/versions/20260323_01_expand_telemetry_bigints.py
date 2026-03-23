"""expand telemetry and screen timing columns to bigint

Revision ID: 20260323_01
Revises: 20260319_02
Create Date: 2026-03-23 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260323_01"
down_revision = "20260319_02"
branch_labels = None
depends_on = None


BIGINT_COLUMNS: dict[str, list[str]] = {
    "telemetry_events": [
        "client_ts",
        "client_clock_skew_estimate_ms",
        "duration_ms",
        "latency_ms",
    ],
    "screen_spells": [
        "entered_client_ts",
        "exited_client_ts",
        "duration_total_ms",
        "visible_ms",
        "hidden_ms",
        "blur_ms",
        "first_click_ms",
        "primary_cta_ms",
        "secondary_cta_ms",
    ],
    "consent_records": [
        "landing_visible_ms",
    ],
    "throws": [
        "reaction_ms",
    ],
    "claims": [
        "reaction_ms",
    ],
}


def _column_type_lookup(table_name: str) -> dict[str, sa.types.TypeEngine]:
    inspector = inspect(op.get_bind())
    return {
        column["name"]: column["type"]
        for column in inspector.get_columns(table_name)
    }


def _should_widen(column_type: sa.types.TypeEngine) -> bool:
    type_name = column_type.__class__.__name__.lower()
    return type_name in {"integer", "int4", "int"} or isinstance(
        column_type, sa.Integer
    ) and not isinstance(column_type, sa.BigInteger)


def upgrade() -> None:
    for table_name, column_names in BIGINT_COLUMNS.items():
        current_types = _column_type_lookup(table_name)
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                current_type = current_types.get(column_name)
                if current_type is None or not _should_widen(current_type):
                    continue
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True,
                )


def downgrade() -> None:
    for table_name, column_names in BIGINT_COLUMNS.items():
        current_types = _column_type_lookup(table_name)
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                current_type = current_types.get(column_name)
                if current_type is None or not isinstance(current_type, sa.BigInteger):
                    continue
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True,
                )
