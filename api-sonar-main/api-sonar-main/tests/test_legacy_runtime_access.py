import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
LEGACY_DB_SOURCE = Path(__file__).resolve().parents[3] / "database.db"


def run_legacy_runtime_script(test_db_path: Path, script_body: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    env["REQUIRE_REDIS"] = "false"
    env["REQUIRE_ADMIN_AUTH"] = "false"
    env["AUTO_BOOTSTRAP_DEMO_DATA"] = "true"

    body = textwrap.dedent(script_body).strip()
    script = "\n".join(
        [
            "import time",
            "from fastapi.testclient import TestClient",
            "from main import app, schema_needs_reset",
            "from migrate import apply_migrations",
            "",
            body,
            "",
        ]
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=APP_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Legacy runtime subprocess failed.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


class LegacyRuntimeAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.test_db_dir = tempfile.mkdtemp(prefix="sonar_legacy_runtime_access_")
        self.test_db_path = Path(self.test_db_dir) / "legacy.db"
        shutil.copy2(LEGACY_DB_SOURCE, self.test_db_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_db_dir, ignore_errors=True)

    def test_access_session_works_after_migrating_legacy_database_snapshot(self) -> None:
        run_legacy_runtime_script(
            self.test_db_path,
            """
apply_migrations()
assert not schema_needs_reset()
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
assert response.status_code == 200, response.text
payload = response.json()["session"]
assert payload["treatment_deck_index"] >= 1
assert payload["result_deck_index"] is not None
assert payload["payment_deck_index"] >= 1
            """,
        )

    def test_lazy_startup_recovers_legacy_database_without_pre_migrate_step(self) -> None:
        run_legacy_runtime_script(
            self.test_db_path,
            """
client = TestClient(app)
config_response = None
for _ in range(20):
    config_response = client.get("/v1/config")
    if config_response.status_code == 200:
        break
    time.sleep(0.1)

assert config_response is not None
assert config_response.status_code == 200, config_response.text
assert not schema_needs_reset()
            """,
        )


if __name__ == "__main__":
    unittest.main()
