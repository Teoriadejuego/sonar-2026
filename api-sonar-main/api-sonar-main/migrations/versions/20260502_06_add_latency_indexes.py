"""add latency-oriented indexes for hot session paths

Revision ID: 20260502_06
Revises: 20260410_05
Create Date: 2026-05-02 03:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_06"
down_revision = "20260410_05"
branch_labels = None
depends_on = None


def create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        return
    op.create_index(index_name, table_name, columns, unique=False)


def drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        return
    op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    create_index_if_missing(
        "ix_sessions_device_hash_created_at",
        "sessions",
        ["device_hash", "created_at"],
    )
    create_index_if_missing(
        "ix_treatment_decks_status_deck_index",
        "treatment_decks",
        ["status", "deck_index"],
    )
    create_index_if_missing(
        "ix_treatment_deck_cards_deck_assigned_position",
        "treatment_deck_cards",
        ["deck_id", "assigned_session_id", "card_position"],
    )
    create_index_if_missing(
        "ix_result_decks_status_treatment_deck_index",
        "result_decks",
        ["status", "treatment_key", "deck_index"],
    )
    create_index_if_missing(
        "ix_result_deck_cards_deck_assigned_position",
        "result_deck_cards",
        ["deck_id", "assigned_session_id", "card_position"],
    )
    create_index_if_missing(
        "ix_payment_decks_status_deck_index",
        "payment_decks",
        ["status", "deck_index"],
    )
    create_index_if_missing(
        "ix_payment_deck_cards_deck_assigned_position",
        "payment_deck_cards",
        ["deck_id", "assigned_session_id", "card_position"],
    )


def downgrade() -> None:
    drop_index_if_exists(
        "ix_payment_deck_cards_deck_assigned_position",
        "payment_deck_cards",
    )
    drop_index_if_exists(
        "ix_payment_decks_status_deck_index",
        "payment_decks",
    )
    drop_index_if_exists(
        "ix_result_deck_cards_deck_assigned_position",
        "result_deck_cards",
    )
    drop_index_if_exists(
        "ix_result_decks_status_treatment_deck_index",
        "result_decks",
    )
    drop_index_if_exists(
        "ix_treatment_deck_cards_deck_assigned_position",
        "treatment_deck_cards",
    )
    drop_index_if_exists(
        "ix_treatment_decks_status_deck_index",
        "treatment_decks",
    )
    drop_index_if_exists(
        "ix_sessions_device_hash_created_at",
        "sessions",
    )
