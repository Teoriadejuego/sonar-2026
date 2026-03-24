"""add balanced treatment, result, and payment decks

Revision ID: 20260324_01
Revises: 20260323_01
Create Date: 2026-03-24 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_01"
down_revision = "20260323_01"
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


def _create_treatment_decks() -> None:
    if not _has_table("treatment_decks"):
        op.create_table(
            "treatment_decks",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("deck_index", sa.Integer(), nullable=False),
            sa.Column("deck_seed", sa.String(), nullable=False),
            sa.Column("legacy_root_id", sa.String(), nullable=True),
            sa.Column("card_count", sa.Integer(), nullable=False, server_default="62"),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["legacy_root_id"], ["series_roots.id"]),
            sa.UniqueConstraint("deck_index", name="uq_treatment_decks_deck_index"),
        )
    if not _has_index("treatment_decks", "ix_treatment_decks_deck_index"):
        op.create_index("ix_treatment_decks_deck_index", "treatment_decks", ["deck_index"])
    if not _has_index("treatment_decks", "ix_treatment_decks_legacy_root_id"):
        op.create_index("ix_treatment_decks_legacy_root_id", "treatment_decks", ["legacy_root_id"])
    if not _has_index("treatment_decks", "ix_treatment_decks_status"):
        op.create_index("ix_treatment_decks_status", "treatment_decks", ["status"])

    if not _has_table("treatment_deck_cards"):
        op.create_table(
            "treatment_deck_cards",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("deck_id", sa.String(), nullable=False),
            sa.Column("legacy_series_id", sa.String(), nullable=True),
            sa.Column("card_position", sa.Integer(), nullable=False),
            sa.Column("treatment_key", sa.String(), nullable=False),
            sa.Column("assigned_session_id", sa.String(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["deck_id"], ["treatment_decks.id"]),
            sa.ForeignKeyConstraint(["legacy_series_id"], ["series.id"]),
            sa.ForeignKeyConstraint(["assigned_session_id"], ["sessions.id"]),
            sa.UniqueConstraint("deck_id", "card_position", name="uq_treatment_deck_position"),
            sa.UniqueConstraint("assigned_session_id", name="uq_treatment_deck_assigned_session_id"),
        )
    for index_name, columns in {
        "ix_treatment_deck_cards_deck_id": ["deck_id"],
        "ix_treatment_deck_cards_legacy_series_id": ["legacy_series_id"],
        "ix_treatment_deck_cards_card_position": ["card_position"],
        "ix_treatment_deck_cards_treatment_key": ["treatment_key"],
        "ix_treatment_deck_cards_assigned_session_id": ["assigned_session_id"],
    }.items():
        if not _has_index("treatment_deck_cards", index_name):
            op.create_index(index_name, "treatment_deck_cards", columns)


def _create_result_decks() -> None:
    if not _has_table("result_decks"):
        op.create_table(
            "result_decks",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("deck_index", sa.Integer(), nullable=False),
            sa.Column("deck_seed", sa.String(), nullable=False),
            sa.Column("card_count", sa.Integer(), nullable=False, server_default="24"),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("deck_index", name="uq_result_decks_deck_index"),
        )
    if not _has_index("result_decks", "ix_result_decks_deck_index"):
        op.create_index("ix_result_decks_deck_index", "result_decks", ["deck_index"])
    if not _has_index("result_decks", "ix_result_decks_status"):
        op.create_index("ix_result_decks_status", "result_decks", ["status"])

    if not _has_table("result_deck_cards"):
        op.create_table(
            "result_deck_cards",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("deck_id", sa.String(), nullable=False),
            sa.Column("card_position", sa.Integer(), nullable=False),
            sa.Column("result_value", sa.Integer(), nullable=False),
            sa.Column("assigned_session_id", sa.String(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["deck_id"], ["result_decks.id"]),
            sa.ForeignKeyConstraint(["assigned_session_id"], ["sessions.id"]),
            sa.UniqueConstraint("deck_id", "card_position", name="uq_result_deck_position"),
            sa.UniqueConstraint("assigned_session_id", name="uq_result_deck_assigned_session_id"),
        )
    for index_name, columns in {
        "ix_result_deck_cards_deck_id": ["deck_id"],
        "ix_result_deck_cards_card_position": ["card_position"],
        "ix_result_deck_cards_result_value": ["result_value"],
        "ix_result_deck_cards_assigned_session_id": ["assigned_session_id"],
    }.items():
        if not _has_index("result_deck_cards", index_name):
            op.create_index(index_name, "result_deck_cards", columns)


def _create_payment_decks() -> None:
    if not _has_table("payment_decks"):
        op.create_table(
            "payment_decks",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("deck_index", sa.Integer(), nullable=False),
            sa.Column("deck_seed", sa.String(), nullable=False),
            sa.Column("card_count", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("deck_index", name="uq_payment_decks_deck_index"),
        )
    if not _has_index("payment_decks", "ix_payment_decks_deck_index"):
        op.create_index("ix_payment_decks_deck_index", "payment_decks", ["deck_index"])
    if not _has_index("payment_decks", "ix_payment_decks_status"):
        op.create_index("ix_payment_decks_status", "payment_decks", ["status"])

    if not _has_table("payment_deck_cards"):
        op.create_table(
            "payment_deck_cards",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("deck_id", sa.String(), nullable=False),
            sa.Column("card_position", sa.Integer(), nullable=False),
            sa.Column("payout_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("assigned_session_id", sa.String(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["deck_id"], ["payment_decks.id"]),
            sa.ForeignKeyConstraint(["assigned_session_id"], ["sessions.id"]),
            sa.UniqueConstraint("deck_id", "card_position", name="uq_payment_deck_position"),
            sa.UniqueConstraint("assigned_session_id", name="uq_payment_deck_assigned_session_id"),
        )
    for index_name, columns in {
        "ix_payment_deck_cards_deck_id": ["deck_id"],
        "ix_payment_deck_cards_card_position": ["card_position"],
        "ix_payment_deck_cards_payout_eligible": ["payout_eligible"],
        "ix_payment_deck_cards_assigned_session_id": ["assigned_session_id"],
    }.items():
        if not _has_index("payment_deck_cards", index_name):
            op.create_index(index_name, "payment_deck_cards", columns)


def upgrade() -> None:
    _create_treatment_decks()
    _create_result_decks()
    _create_payment_decks()

    session_columns = {
        "treatment_type": sa.Column("treatment_type", sa.String(), nullable=True),
        "displayed_count_target": sa.Column("displayed_count_target", sa.Integer(), nullable=True),
        "displayed_denominator": sa.Column("displayed_denominator", sa.Integer(), nullable=True),
        "treatment_deck_id": sa.Column("treatment_deck_id", sa.String(), nullable=True),
        "treatment_card_position": sa.Column("treatment_card_position", sa.Integer(), nullable=True),
        "result_deck_id": sa.Column("result_deck_id", sa.String(), nullable=True),
        "result_card_position": sa.Column("result_card_position", sa.Integer(), nullable=True),
        "payment_deck_id": sa.Column("payment_deck_id", sa.String(), nullable=True),
        "payment_card_position": sa.Column("payment_card_position", sa.Integer(), nullable=True),
    }
    for column_name, column in session_columns.items():
        if not _has_column("sessions", column_name):
            op.add_column("sessions", column)

    for index_name, columns in {
        "ix_sessions_treatment_type": ["treatment_type"],
        "ix_sessions_treatment_deck_id": ["treatment_deck_id"],
        "ix_sessions_treatment_card_position": ["treatment_card_position"],
        "ix_sessions_result_deck_id": ["result_deck_id"],
        "ix_sessions_result_card_position": ["result_card_position"],
        "ix_sessions_payment_deck_id": ["payment_deck_id"],
        "ix_sessions_payment_card_position": ["payment_card_position"],
    }.items():
        if not _has_index("sessions", index_name):
            op.create_index(index_name, "sessions", columns)

    if not _has_column("snapshot_records", "is_control"):
        op.add_column("snapshot_records", sa.Column("is_control", sa.Boolean(), nullable=True))
    if not _has_index("snapshot_records", "ix_snapshot_records_is_control"):
        op.create_index("ix_snapshot_records_is_control", "snapshot_records", ["is_control"])


def downgrade() -> None:
    if _has_index("snapshot_records", "ix_snapshot_records_is_control"):
        op.drop_index("ix_snapshot_records_is_control", table_name="snapshot_records")
    if _has_column("snapshot_records", "is_control"):
        op.drop_column("snapshot_records", "is_control")

    for index_name in [
        "ix_sessions_payment_card_position",
        "ix_sessions_payment_deck_id",
        "ix_sessions_result_card_position",
        "ix_sessions_result_deck_id",
        "ix_sessions_treatment_card_position",
        "ix_sessions_treatment_deck_id",
        "ix_sessions_treatment_type",
    ]:
        if _has_index("sessions", index_name):
            op.drop_index(index_name, table_name="sessions")

    for column_name in [
        "payment_card_position",
        "payment_deck_id",
        "result_card_position",
        "result_deck_id",
        "treatment_card_position",
        "treatment_deck_id",
        "displayed_denominator",
        "displayed_count_target",
        "treatment_type",
    ]:
        if _has_column("sessions", column_name):
            op.drop_column("sessions", column_name)

    for table_name, index_names in [
        ("payment_deck_cards", [
            "ix_payment_deck_cards_assigned_session_id",
            "ix_payment_deck_cards_payout_eligible",
            "ix_payment_deck_cards_card_position",
            "ix_payment_deck_cards_deck_id",
        ]),
        ("payment_decks", [
            "ix_payment_decks_status",
            "ix_payment_decks_deck_index",
        ]),
        ("result_deck_cards", [
            "ix_result_deck_cards_assigned_session_id",
            "ix_result_deck_cards_result_value",
            "ix_result_deck_cards_card_position",
            "ix_result_deck_cards_deck_id",
        ]),
        ("result_decks", [
            "ix_result_decks_status",
            "ix_result_decks_deck_index",
        ]),
        ("treatment_deck_cards", [
            "ix_treatment_deck_cards_assigned_session_id",
            "ix_treatment_deck_cards_treatment_key",
            "ix_treatment_deck_cards_card_position",
            "ix_treatment_deck_cards_legacy_series_id",
            "ix_treatment_deck_cards_deck_id",
        ]),
        ("treatment_decks", [
            "ix_treatment_decks_status",
            "ix_treatment_decks_legacy_root_id",
            "ix_treatment_decks_deck_index",
        ]),
    ]:
        for index_name in index_names:
            if _has_index(table_name, index_name):
                op.drop_index(index_name, table_name=table_name)

    for table_name in [
        "payment_deck_cards",
        "payment_decks",
        "result_deck_cards",
        "result_decks",
        "treatment_deck_cards",
        "treatment_decks",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)
