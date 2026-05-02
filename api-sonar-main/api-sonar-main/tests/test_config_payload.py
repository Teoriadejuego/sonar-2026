import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_config_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["AUTO_BOOTSTRAP_DEMO_DATA"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, build_config_payload
from models import ExperimentState
from settings import settings


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
                    current_phase="legacy_old_phase",
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
        self.assertEqual(payload["experiment_control"]["mode"], "live")
        self.assertEqual(len(payload["treatments"]), 62)
        self.assertIn("control", payload["treatments"])
        self.assertIn("norm_0", payload["treatments"])
        self.assertIn("norm_17", payload["treatments"])
        self.assertIn("norm_60", payload["treatments"])
        self.assertNotIn("seed_low", payload["treatments"])
        self.assertNotIn("seed_high", payload["treatments"])
        self.assertNotIn("seed_initial_counts", payload)
        self.assertEqual(payload["displayed_denominator"], 60)
        self.assertEqual(payload["social_norm_design"], "fixed_by_treatment")
        self.assertIsNone(payload["treatment_display_counts"]["control"])
        self.assertEqual(payload["treatment_display_counts"]["norm_0"], 0)
        self.assertEqual(payload["treatment_display_counts"]["norm_17"], 17)
        self.assertEqual(payload["treatment_display_counts"]["norm_60"], 60)
        self.assertEqual(payload["treatment_display_denominators"]["norm_0"], 60)
        self.assertEqual(payload["treatment_display_denominators"]["norm_60"], 60)

    def test_config_endpoint_returns_200_with_legacy_state(self) -> None:
        client = TestClient(app)
        response = client.get("/v1/config")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["current_phase"], "design_62_treatments_v1")
        self.assertEqual(payload["experiment_control"]["status"], "active")
        self.assertEqual(payload["experiment_control"]["mode"], "live")

    def test_config_endpoint_normalizes_unknown_phase_state(self) -> None:
        with Session(engine) as db:
            state = db.exec(select(ExperimentState).where(ExperimentState.id == "global")).one()
            state.current_phase = "broken_live_phase"
            db.add(state)
            db.commit()

        client = TestClient(app)
        response = client.get("/v1/config")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["current_phase"], "design_62_treatments_v1")

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

    def test_sqlite_engine_uses_configured_pool_size(self) -> None:
        pool = engine.pool
        self.assertTrue(hasattr(pool, "size"))
        self.assertEqual(pool.size(), settings.db_pool_size)

    def test_access_uses_flow_payload_and_admin_session_uses_analytics_payload(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/v1/session/access",
            json={
                "bracelet_id": "TESA0001",
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "landing_visible_ms": 1500,
                "consent_checkbox_order": ["age", "participation", "data"],
                "consent_checkbox_timestamps_ms": {
                    "age": 120,
                    "participation": 240,
                    "data": 360,
                },
                "consent_continue_blocked_count": 1,
                "client_installation_id": "flow-vs-analytics",
                "client_context": {
                    "user_agent_raw": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                    "platform": "iPhone",
                    "language_browser": "es-ES",
                    "language_app_selected": "es",
                    "screen_width": 390,
                    "screen_height": 844,
                    "viewport_width": 390,
                    "viewport_height": 760,
                },
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        session_payload = response.json()["session"]
        self.assertEqual(session_payload["payload_mode"], "flow")
        self.assertEqual(
            session_payload["session_metrics"],
            {"max_event_sequence_number": 0},
        )
        self.assertNotIn("phase_activation_status", session_payload)
        self.assertNotIn("quality_flags", session_payload)
        self.assertNotIn("antifraud_flags", session_payload)
        self.assertNotIn("client_context", session_payload)
        self.assertNotIn("consent_record", session_payload)
        self.assertNotIn("snapshot_record", session_payload)
        self.assertNotIn("screen_metrics", session_payload)
        self.assertNotIn("visible_count_target", session_payload["series"])
        self.assertNotIn("actual_count_target", session_payload["series"])
        self.assertNotIn("visible_window_version", session_payload["series"])
        self.assertNotIn("actual_window_version", session_payload["series"])

        admin_response = client.get("/admin/session/TESA0001")
        self.assertEqual(admin_response.status_code, 200, admin_response.text)
        analytics_payload = admin_response.json()
        self.assertEqual(analytics_payload["payload_mode"], "analytics")
        self.assertIn("phase_activation_status", analytics_payload)
        self.assertIn("quality_flags", analytics_payload)
        self.assertIn("antifraud_flags", analytics_payload)
        self.assertIn("client_context", analytics_payload)
        self.assertIn("consent_record", analytics_payload)
        self.assertIn("snapshot_record", analytics_payload)
        self.assertIn("visible_count_target", analytics_payload["series"])
        self.assertIn("actual_count_target", analytics_payload["series"])
        self.assertIn("visible_window_version", analytics_payload["series"])
        self.assertIn("actual_window_version", analytics_payload["series"])

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

    def test_ready_healthcheck_requires_startup_completion(self) -> None:
        client = TestClient(app)
        with mock.patch(
            "main.startup_dependency_status",
            return_value={
                "database_ready": True,
                "redis_ready": True,
                "schema_ready": True,
            },
        ), mock.patch(
            "main.current_startup_state",
            return_value={
                "initialized": False,
                "initializing": True,
                "error": None,
                "last_readiness": {
                    "database_ready": True,
                    "redis_ready": True,
                    "schema_ready": True,
                },
            },
        ):
            response = client.get("/health/ready")

        self.assertEqual(response.status_code, 503, response.text)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["schema_ready"])
        self.assertFalse(payload["startup_initialized"])
        self.assertTrue(payload["startup_initializing"])

    def test_ready_healthcheck_turns_green_when_startup_completed(self) -> None:
        client = TestClient(app)
        with mock.patch(
            "main.startup_dependency_status",
            return_value={
                "database_ready": True,
                "redis_ready": True,
                "schema_ready": True,
            },
        ), mock.patch(
            "main.current_startup_state",
            return_value={
                "initialized": True,
                "initializing": False,
                "error": None,
                "last_readiness": {
                    "database_ready": True,
                    "redis_ready": True,
                    "schema_ready": True,
                },
            },
        ):
            response = client.get("/health/ready")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["database_ready"])
        self.assertTrue(payload["redis_ready"])
        self.assertTrue(payload["schema_ready"])
        self.assertIn("instance_name", payload)
        self.assertIn("config_fingerprint", payload)

    def test_full_healthcheck_reports_instance_identity(self) -> None:
        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("instance_name", payload)
        self.assertIn("config_fingerprint", payload)

    def test_live_healthcheck_reports_config_fingerprint(self) -> None:
        client = TestClient(app)
        response = client.get("/health/live")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("instance_name", payload)
        self.assertIn("config_fingerprint", payload)


if __name__ == "__main__":
    unittest.main()
