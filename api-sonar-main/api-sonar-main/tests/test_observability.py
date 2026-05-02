import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_observability_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine
from main import app, bootstrap_demo_data
from runtime import reset_observability_metrics


class ObservabilityTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        reset_observability_metrics()
        self.client = TestClient(app)

    def complete_session(
        self,
        bracelet_id: str = "OBSV1001",
        *,
        roll_reaction_ms: int = 900,
        report_reaction_ms: int = 1200,
        reported_value: int | None = None,
        force_lie: bool = False,
    ) -> dict:
        access = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": f"obs-{bracelet_id}",
            },
        )
        self.assertEqual(access.status_code, 200, access.text)
        session = access.json()["session"]
        session_id = session["session_id"]

        for screen in ("comprehension", "game"):
            response = self.client.post(
                f"/v1/session/{session_id}/screen",
                json={"screen": screen},
                headers={"X-Sonar-Installation": f"obs-{bracelet_id}"},
            )
            self.assertEqual(response.status_code, 200, response.text)

        roll = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": roll_reaction_ms,
                "idempotency_key": f"roll-{session_id}",
            },
            headers={"X-Sonar-Installation": f"obs-{bracelet_id}"},
        )
        self.assertEqual(roll.status_code, 200, roll.text)
        first_value = roll.json()["attempt"]["result_value"]

        prepare = self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
            headers={"X-Sonar-Installation": f"obs-{bracelet_id}"},
        )
        self.assertEqual(prepare.status_code, 200, prepare.text)

        final_reported_value = reported_value
        if force_lie:
            final_reported_value = 6 if first_value != 6 else 5

        submit = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": (
                    final_reported_value
                    if final_reported_value is not None
                    else first_value
                ),
                "reaction_ms": report_reaction_ms,
                "idempotency_key": f"submit-{session_id}",
                "language": "es",
            },
            headers={"X-Sonar-Installation": f"obs-{bracelet_id}"},
        )
        self.assertEqual(submit.status_code, 200, submit.text)
        return submit.json()["session"]

    def test_admin_metrics_returns_live_operational_snapshot(self) -> None:
        self.complete_session()

        response = self.client.get("/admin/metrics")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()

        self.assertIn("summary", payload)
        self.assertIn("experiment_metrics", payload)
        self.assertIn("screen_abandonment", payload)
        self.assertIn("data_quality", payload)
        self.assertIn("payments", payload)
        self.assertIn("qr_metrics", payload)
        self.assertIn("referrals", payload)
        self.assertIn("endpoint_metrics", payload)
        self.assertIn("alerts", payload)
        self.assertGreaterEqual(payload["summary"]["sessions_started_total"], 1)
        self.assertGreaterEqual(payload["summary"]["sessions_completed_total"], 1)
        self.assertGreaterEqual(payload["summary"]["valid_sessions_completed_total"], 1)
        self.assertIn("fast_report_rate", payload["data_quality"])
        self.assertIn("report_distribution", payload["data_quality"])
        self.assertIn("reported_six_rate_total", payload["experiment_metrics"])
        self.assertIn("lie_rate_total", payload["experiment_metrics"])
        self.assertIn("timeseries", payload["experiment_metrics"])
        self.assertIn("sessions", payload["counters"])
        self.assertGreaterEqual(payload["counters"]["sessions"].get("started_total", 0), 1)
        self.assertGreaterEqual(payload["counters"]["sessions"].get("completed_total", 0), 1)

        endpoints = {item["endpoint"]: item for item in payload["endpoint_metrics"]}
        self.assertIn("POST /v1/session/access", endpoints)
        self.assertIn("POST /v1/session/{session_id}/roll", endpoints)
        self.assertIn("POST /v1/session/{session_id}/prepare-report", endpoints)
        self.assertIn("POST /v1/session/{session_id}/submit-report", endpoints)

        screens = {item["screen"]: item for item in payload["screen_abandonment"]}
        self.assertIn("instructions", screens)
        self.assertIn("game", screens)
        self.assertIn("report", screens)

        dashboard = self.client.get("/admin/dashboard/live")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        dashboard_payload = dashboard.json()
        self.assertIn("payments", dashboard_payload)
        self.assertIn("qr_metrics", dashboard_payload)
        self.assertIn("referrals", dashboard_payload)

    def test_admin_experiment_metrics_returns_real_time_core_kpis(self) -> None:
        self.complete_session(bracelet_id="OBSM1001")
        self.complete_session(bracelet_id="OBSM1002", force_lie=True)

        response = self.client.get("/admin/metrics/experiment")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["experiment_metrics"]

        self.assertEqual(payload["participants_total"], 2)
        self.assertEqual(payload["claims_total"], 2)
        self.assertEqual(payload["completion_rate_total"], 1.0)
        self.assertEqual(payload["reported_six_count_total"], 1)
        self.assertEqual(payload["reported_six_rate_total"], 0.5)
        self.assertEqual(payload["lies_count_total"], 1)
        self.assertEqual(payload["lie_rate_total"], 0.5)
        self.assertGreaterEqual(len(payload["timeseries"]), 1)

        timeseries = self.client.get("/admin/metrics/experiment/timeseries")
        self.assertEqual(timeseries.status_code, 200, timeseries.text)
        timeseries_payload = timeseries.json()
        self.assertEqual(timeseries_payload["bucket_minutes"], 5)
        self.assertGreaterEqual(len(timeseries_payload["timeseries"]), 1)

    def test_admin_metrics_raises_live_quality_alerts_for_suspicious_patterns(self) -> None:
        for index in range(5):
            self.complete_session(
                bracelet_id=f"OBSQ{index:04d}",
                roll_reaction_ms=120,
                report_reaction_ms=150,
                reported_value=6,
            )

        response = self.client.get("/admin/metrics")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()

        quality = payload["data_quality"]
        alert_keys = {item["key"] for item in payload["alerts"]}

        self.assertGreaterEqual(quality["window_completed_sessions"], 5)
        self.assertGreaterEqual(quality["fast_first_throw_rate"], 0.8)
        self.assertGreaterEqual(quality["fast_report_rate"], 0.8)
        self.assertEqual(quality["dominant_report_value"], "6")
        self.assertGreaterEqual(quality["dominant_report_share"], 0.8)
        self.assertIn("suspicious_speed_spike", alert_keys)
        self.assertIn("report_distribution_anomaly", alert_keys)

    def test_admin_live_renders_real_time_dashboard_shell(self) -> None:
        response = self.client.get("/admin/live")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("SONAR Live Dashboard", response.text)
        self.assertIn("/admin/dashboard/live", response.text)
        self.assertIn("Viralidad", response.text)
        self.assertIn("Pagos", response.text)
        self.assertIn("QR y zonas", response.text)
        self.assertIn("Latencia y errores", response.text)


if __name__ == "__main__":
    unittest.main()
