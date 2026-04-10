import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_legacy_runtime_access_")
LEGACY_DB_SOURCE = Path(__file__).resolve().parents[3] / "database.db"
TEST_DB_PATH = Path(TEST_DB_DIR) / "legacy.db"
shutil.copy2(LEGACY_DB_SOURCE, TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["AUTO_BOOTSTRAP_DEMO_DATA"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from main import app, schema_needs_reset
from migrate import apply_migrations


class LegacyRuntimeAccessTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def test_access_session_works_after_migrating_legacy_database_snapshot(self) -> None:
        apply_migrations()

        self.assertFalse(schema_needs_reset())

        client = TestClient(app)
        response = client.post(
            "/v1/session/access",
            json={
                "bracelet_id": "ABCD1234",
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "legacy-runtime-access",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["session"]
        self.assertEqual(payload["treatment_deck_index"], 1)
        self.assertIsNotNone(payload["result_deck_index"])
        self.assertEqual(payload["payment_deck_index"], 1)


if __name__ == "__main__":
    unittest.main()
