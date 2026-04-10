import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_config_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["AUTO_BOOTSTRAP_DEMO_DATA"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine
from main import app, build_config_payload
from models import ExperimentState


class ConfigPayloadTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(
                ExperimentState(
                    id="global",
                    current_phase="seed_high",
                    experiment_status="active",
                    phase_transition_threshold=17,
                    valid_completed_count=12,
                    treatment_version="legacy_treatment",
                    allocation_version="legacy_allocation",
                )
            )
            db.commit()

    def test_build_config_payload_recovers_from_legacy_state(self) -> None:
        with Session(engine) as db:
            payload = build_config_payload(db)

        self.assertEqual(payload["schema_version"], "sonar-2026-v9")
        self.assertEqual(payload["experiment_version"], "sonar-2026-field-v5")
        self.assertEqual(payload["current_phase"], "design_62_treatments_v1")
        self.assertEqual(payload["treatment_version"], "treatment_deck_62_v1")
        self.assertEqual(payload["allocation_version"], "balanced_assignment_v1")
        self.assertEqual(len(payload["treatments"]), 62)
        self.assertIn("control", payload["treatments"])
        self.assertIn("norm_60", payload["treatments"])
        self.assertNotIn("seed_low", payload["treatments"])
        self.assertNotIn("seed_high", payload["treatments"])

    def test_config_endpoint_returns_200_with_legacy_state(self) -> None:
        client = TestClient(app)
        response = client.get("/v1/config")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["current_phase"], "design_62_treatments_v1")
        self.assertEqual(payload["experiment_control"]["status"], "active")

    def test_access_session_bootstraps_runtime_from_empty_db(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

        client = TestClient(app)
        response = client.post(
            "/v1/session/access",
            json={
                "bracelet_id": "TEST0001",
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "lazy-bootstrap-probe",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        session_payload = response.json()["session"]
        self.assertEqual(session_payload["treatment_deck_index"], 1)
        self.assertEqual(session_payload["payment_deck_index"], 1)
        self.assertIsNotNone(session_payload["result_deck_index"])

    def test_demo_ids_work_without_eager_bootstrap(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

        client = TestClient(app)
        response = client.post(
            "/v1/session/access",
            json={
                "bracelet_id": "CTRL1234",
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "lazy-demo-probe",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        session_payload = response.json()["session"]
        self.assertEqual(session_payload["treatment_key"], "control")
        self.assertTrue(session_payload["selected_for_payment"])

    def test_ready_healthcheck_stays_green_during_lazy_startup(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

        client = TestClient(app)
        response = client.get("/health/ready")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["database_ready"])
        self.assertTrue(payload["redis_ready"])


if __name__ == "__main__":
    unittest.main()
