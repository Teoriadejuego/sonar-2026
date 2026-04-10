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


if __name__ == "__main__":
    unittest.main()
