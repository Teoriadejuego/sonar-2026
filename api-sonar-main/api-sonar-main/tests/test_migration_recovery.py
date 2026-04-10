import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy import text


TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_migration_recovery_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from migrate import (
    alembic_config,
    apply_migrations,
    current_database_revision,
    head_revision,
    seed_demo,
)
from sqlmodel import SQLModel


class MigrationRecoveryTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        apply_migrations()

    def test_unknown_alembic_revision_is_repaired_when_schema_matches(self) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num = :version_num"),
                {"version_num": "missing_revision_2026"},
            )

        apply_migrations()

        self.assertEqual(
            current_database_revision(),
            head_revision(alembic_config()),
        )

    def test_unknown_alembic_revision_is_not_silently_repaired_when_schema_is_incomplete(self) -> None:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE result_decks"))
            connection.execute(
                text("UPDATE alembic_version SET version_num = :version_num"),
                {"version_num": "missing_revision_2026"},
            )

        with self.assertRaises(RuntimeError) as context:
            apply_migrations()

        self.assertIn("automatic repair was refused", str(context.exception))

    def test_head_revision_backfills_missing_experiment_state_columns(self) -> None:
        SQLModel.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.execute(
                text(
                    """
                    CREATE TABLE experiment_state (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        current_phase VARCHAR,
                        phase_transition_threshold INTEGER,
                        valid_completed_count INTEGER,
                        phase_2_activated_at DATETIME,
                        treatment_version VARCHAR NOT NULL,
                        allocation_version VARCHAR NOT NULL,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO experiment_state (
                        id,
                        current_phase,
                        phase_transition_threshold,
                        valid_completed_count,
                        phase_2_activated_at,
                        treatment_version,
                        allocation_version,
                        created_at,
                        updated_at
                    ) VALUES (
                        'global',
                        'seed_high',
                        17,
                        0,
                        NULL,
                        'legacy_treatment',
                        'legacy_allocation',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('20260408_02')")
            )

        apply_migrations()

        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(experiment_state)"))
            }
            status = connection.execute(
                text("SELECT experiment_status FROM experiment_state WHERE id = 'global'")
            ).scalar_one()

        self.assertIn("experiment_status", columns)
        self.assertIn("paused_at", columns)
        self.assertIn("resumed_at", columns)
        self.assertIn("pause_reason", columns)
        self.assertEqual(status, "active")
        self.assertEqual(current_database_revision(), head_revision(alembic_config()))

    def test_head_revision_backfills_missing_runtime_columns(self) -> None:
        SQLModel.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.execute(
                text(
                    """
                    CREATE TABLE sessions (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        user_id VARCHAR,
                        root_id VARCHAR,
                        series_id VARCHAR,
                        experiment_version VARCHAR,
                        experiment_phase VARCHAR,
                        phase_version VARCHAR,
                        phase_activation_status VARCHAR,
                        ui_version VARCHAR,
                        consent_version VARCHAR,
                        treatment_version VARCHAR,
                        treatment_text_version VARCHAR,
                        allocation_version VARCHAR,
                        deck_version VARCHAR,
                        payment_version VARCHAR,
                        telemetry_version VARCHAR,
                        lexicon_version VARCHAR,
                        treatment_key VARCHAR,
                        treatment_type VARCHAR,
                        treatment_family VARCHAR,
                        norm_target_value INTEGER,
                        displayed_count_target INTEGER,
                        displayed_denominator INTEGER,
                        treatment_deck_id VARCHAR,
                        treatment_card_position INTEGER,
                        result_deck_id VARCHAR,
                        result_card_position INTEGER,
                        payment_deck_id VARCHAR,
                        payment_card_position INTEGER,
                        language_at_access VARCHAR,
                        language_at_claim VARCHAR,
                        language_changed_during_session BOOLEAN,
                        deployment_context VARCHAR,
                        site_code VARCHAR,
                        campaign_code VARCHAR,
                        environment_label VARCHAR,
                        referral_code VARCHAR,
                        invited_by_session_id VARCHAR,
                        invited_by_referral_code VARCHAR,
                        referral_source VARCHAR,
                        qr_entry_code VARCHAR,
                        referral_landing_path VARCHAR,
                        operational_note_id VARCHAR,
                        operational_note_text TEXT,
                        position_index INTEGER,
                        state VARCHAR,
                        screen_cursor VARCHAR,
                        consent_accepted BOOLEAN,
                        consent_age_confirmed BOOLEAN,
                        consent_info_accepted BOOLEAN,
                        consent_data_accepted BOOLEAN,
                        consent_accepted_at DATETIME,
                        max_attempts INTEGER,
                        selected_for_payment BOOLEAN,
                        payout_amount INTEGER,
                        reported_value INTEGER,
                        is_honest BOOLEAN,
                        first_result_value INTEGER,
                        max_seen_value INTEGER,
                        last_seen_value INTEGER,
                        report_snapshot_treatment VARCHAR,
                        report_snapshot_count_target INTEGER,
                        report_snapshot_denominator INTEGER,
                        report_snapshot_target_value INTEGER,
                        report_snapshot_version INTEGER,
                        report_snapshot_message VARCHAR,
                        report_snapshot_message_version VARCHAR,
                        displayed_message_version VARCHAR,
                        is_valid_completed BOOLEAN,
                        valid_completed_at DATETIME,
                        claim_submitted_at DATETIME,
                        first_roll_at DATETIME,
                        report_prepared_at DATETIME,
                        completed_at DATETIME,
                        created_at DATETIME,
                        last_seen_at DATETIME,
                        resume_count INTEGER,
                        refresh_count INTEGER,
                        blur_count INTEGER,
                        network_error_count INTEGER,
                        reroll_count INTEGER,
                        client_installation_id VARCHAR,
                        device_hash VARCHAR,
                        ip_hash VARCHAR,
                        user_agent_hash VARCHAR,
                        quality_flags_json TEXT,
                        antifraud_flags_json TEXT
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE consent_records (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        session_id VARCHAR,
                        bracelet_id VARCHAR,
                        consent_version VARCHAR,
                        language_at_access VARCHAR,
                        age_confirmed BOOLEAN,
                        participation_accepted BOOLEAN,
                        data_accepted BOOLEAN,
                        accepted_at DATETIME,
                        landing_visible_ms BIGINT,
                        info_panels_opened_json TEXT,
                        info_panel_durations_json TEXT,
                        info_panel_open_count INTEGER,
                        created_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE snapshot_records (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        session_id VARCHAR,
                        language_used VARCHAR,
                        treatment_key VARCHAR,
                        treatment_family VARCHAR,
                        norm_target_value INTEGER,
                        is_control BOOLEAN,
                        displayed_count_target INTEGER,
                        displayed_denominator INTEGER,
                        displayed_message_text TEXT,
                        displayed_message_version VARCHAR,
                        control_message_text TEXT,
                        first_result_value INTEGER,
                        last_seen_value INTEGER,
                        rerolls_visible_json TEXT,
                        final_state_shown VARCHAR,
                        final_message_text TEXT,
                        final_amount_eur INTEGER,
                        payout_reference_shown VARCHAR,
                        payout_phone_shown VARCHAR,
                        updated_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE telemetry_events (
                        id INTEGER NOT NULL PRIMARY KEY,
                        session_id VARCHAR,
                        event_type VARCHAR,
                        event_name VARCHAR,
                        screen_name VARCHAR,
                        client_ts BIGINT,
                        duration_ms BIGINT,
                        value INTEGER,
                        network_status VARCHAR,
                        visibility_state VARCHAR,
                        operational_note_id VARCHAR,
                        operational_note_text TEXT,
                        payload_json TEXT,
                        server_ts DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('20260410_03')")
            )

        apply_migrations()

        with engine.begin() as connection:
            sessions_columns = {
                row[1] for row in connection.execute(text("PRAGMA table_info(sessions)"))
            }
            consent_columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(consent_records)"))
            }
            snapshot_columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(snapshot_records)"))
            }
            telemetry_columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(telemetry_events)"))
            }

        for required in [
            "referral_medium",
            "referral_campaign",
            "referral_link_id",
            "referral_arrived_at",
            "retry_count",
            "click_count_total",
            "screen_changes_count",
            "language_change_count",
            "telemetry_event_count",
            "max_event_sequence_number",
        ]:
            self.assertIn(required, sessions_columns)
        for required in [
            "checkbox_order_json",
            "checkbox_timestamps_json",
            "continue_blocked_count",
        ]:
            self.assertIn(required, consent_columns)
        self.assertIn("all_values_seen_json", snapshot_columns)
        for required in [
            "event_sequence_number",
            "timezone_offset_minutes",
            "client_clock_skew_estimate_ms",
            "app_language",
            "browser_language",
            "spell_id",
            "interaction_target",
            "interaction_role",
            "cta_kind",
            "endpoint_name",
            "request_method",
            "status_code",
            "latency_ms",
            "attempt_number",
            "is_retry",
            "error_name",
        ]:
            self.assertIn(required, telemetry_columns)
        self.assertEqual(current_database_revision(), head_revision(alembic_config()))

    def test_seed_demo_failure_does_not_abort_migrate_process(self) -> None:
        with mock.patch("migrate.bootstrap_demo_data", side_effect=RuntimeError("boom")):
            seed_demo()


if __name__ == "__main__":
    unittest.main()
