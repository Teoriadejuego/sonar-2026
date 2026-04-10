"""backfill missing runtime columns for legacy databases

Revision ID: 20260410_04
Revises: 20260410_03
Create Date: 2026-04-10 23:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_04"
down_revision = "20260410_03"
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


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_table(table_name):
        return
    if _has_column(table_name, column.name):
        return
    op.add_column(table_name, column)


def _create_index_if_missing(
    table_name: str,
    index_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if not _has_table(table_name):
        return
    if _has_index(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    session_columns = [
        sa.Column("referral_medium", sa.String(), nullable=True),
        sa.Column("referral_campaign", sa.String(), nullable=True),
        sa.Column("referral_link_id", sa.String(), nullable=True),
        sa.Column("referral_arrived_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("screen_changes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telemetry_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_event_sequence_number", sa.Integer(), nullable=False, server_default="0"),
    ]
    for column in session_columns:
        _add_column_if_missing("sessions", column)
    if _has_table("sessions"):
        op.execute(
            """
            UPDATE sessions
            SET retry_count = COALESCE(retry_count, 0),
                click_count_total = COALESCE(click_count_total, 0),
                screen_changes_count = COALESCE(screen_changes_count, 0),
                language_change_count = COALESCE(language_change_count, 0),
                telemetry_event_count = COALESCE(telemetry_event_count, 0),
                max_event_sequence_number = COALESCE(max_event_sequence_number, 0)
            """
        )
    for index_name, columns in {
        "ix_sessions_referral_medium": ["referral_medium"],
        "ix_sessions_referral_campaign": ["referral_campaign"],
        "ix_sessions_referral_link_id": ["referral_link_id"],
    }.items():
        _create_index_if_missing("sessions", index_name, columns)

    consent_columns = [
        sa.Column("checkbox_order_json", sa.Text(), nullable=True),
        sa.Column("checkbox_timestamps_json", sa.Text(), nullable=True),
        sa.Column("continue_blocked_count", sa.Integer(), nullable=False, server_default="0"),
    ]
    for column in consent_columns:
        _add_column_if_missing("consent_records", column)
    if _has_table("consent_records"):
        op.execute(
            """
            UPDATE consent_records
            SET continue_blocked_count = COALESCE(continue_blocked_count, 0)
            """
        )

    _add_column_if_missing(
        "snapshot_records",
        sa.Column("all_values_seen_json", sa.Text(), nullable=True),
    )

    telemetry_columns = [
        sa.Column("event_sequence_number", sa.Integer(), nullable=True),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("client_clock_skew_estimate_ms", sa.BigInteger(), nullable=True),
        sa.Column("app_language", sa.String(), nullable=True),
        sa.Column("browser_language", sa.String(), nullable=True),
        sa.Column("spell_id", sa.String(), nullable=True),
        sa.Column("interaction_target", sa.String(), nullable=True),
        sa.Column("interaction_role", sa.String(), nullable=True),
        sa.Column("cta_kind", sa.String(), nullable=True),
        sa.Column("endpoint_name", sa.String(), nullable=True),
        sa.Column("request_method", sa.String(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.BigInteger(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("is_retry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_name", sa.String(), nullable=True),
    ]
    for column in telemetry_columns:
        _add_column_if_missing("telemetry_events", column)
    if _has_table("telemetry_events"):
        op.execute(
            """
            UPDATE telemetry_events
            SET is_retry = COALESCE(is_retry, 0)
            """
        )
    for index_name, columns in {
        "ix_telemetry_events_event_sequence_number": ["event_sequence_number"],
        "ix_telemetry_events_app_language": ["app_language"],
        "ix_telemetry_events_browser_language": ["browser_language"],
        "ix_telemetry_events_spell_id": ["spell_id"],
        "ix_telemetry_events_interaction_target": ["interaction_target"],
        "ix_telemetry_events_interaction_role": ["interaction_role"],
        "ix_telemetry_events_cta_kind": ["cta_kind"],
        "ix_telemetry_events_endpoint_name": ["endpoint_name"],
        "ix_telemetry_events_request_method": ["request_method"],
        "ix_telemetry_events_is_retry": ["is_retry"],
    }.items():
        _create_index_if_missing("telemetry_events", index_name, columns)


def downgrade() -> None:
    for table_name, index_names in [
        (
            "telemetry_events",
            [
                "ix_telemetry_events_is_retry",
                "ix_telemetry_events_request_method",
                "ix_telemetry_events_endpoint_name",
                "ix_telemetry_events_cta_kind",
                "ix_telemetry_events_interaction_role",
                "ix_telemetry_events_interaction_target",
                "ix_telemetry_events_spell_id",
                "ix_telemetry_events_browser_language",
                "ix_telemetry_events_app_language",
                "ix_telemetry_events_event_sequence_number",
            ],
        ),
        (
            "sessions",
            [
                "ix_sessions_referral_link_id",
                "ix_sessions_referral_campaign",
                "ix_sessions_referral_medium",
            ],
        ),
    ]:
        for index_name in index_names:
            if _has_index(table_name, index_name):
                op.drop_index(index_name, table_name=table_name)

    for table_name, columns in [
        (
            "telemetry_events",
            [
                "error_name",
                "is_retry",
                "attempt_number",
                "latency_ms",
                "status_code",
                "request_method",
                "endpoint_name",
                "cta_kind",
                "interaction_role",
                "interaction_target",
                "spell_id",
                "browser_language",
                "app_language",
                "client_clock_skew_estimate_ms",
                "timezone_offset_minutes",
                "event_sequence_number",
            ],
        ),
        ("snapshot_records", ["all_values_seen_json"]),
        (
            "consent_records",
            ["continue_blocked_count", "checkbox_timestamps_json", "checkbox_order_json"],
        ),
        (
            "sessions",
            [
                "max_event_sequence_number",
                "telemetry_event_count",
                "language_change_count",
                "screen_changes_count",
                "click_count_total",
                "retry_count",
                "referral_arrived_at",
                "referral_link_id",
                "referral_campaign",
                "referral_medium",
            ],
        ),
    ]:
        for column_name in columns:
            if _has_column(table_name, column_name):
                op.drop_column(table_name, column_name)
