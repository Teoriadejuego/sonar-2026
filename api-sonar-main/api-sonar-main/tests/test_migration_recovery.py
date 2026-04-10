import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
