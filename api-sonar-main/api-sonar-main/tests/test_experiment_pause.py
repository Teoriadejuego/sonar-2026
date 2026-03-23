import csv
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_pause_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, bootstrap_demo_data
from models import ExperimentState, InterestSignup, SessionRecord


def bracelet_code(seed: int) -> str:
    return f"PAUS{seed:04d}"


class ExperimentPauseTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        self.client = TestClient(app)

    def access_session(self, bracelet_id: str) -> dict:
        response = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": f"pause-{bracelet_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def complete_winner_session(self, bracelet_id: str) -> None:
        session = self.access_session(bracelet_id)
        with Session(engine) as db:
            record = db.get(SessionRecord, session["session_id"])
            record.selected_for_payment = True
            db.add(record)
            db.commit()

        roll_response = self.client.post(
            f"/v1/session/{session['session_id']}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 900,
                "idempotency_key": f"roll-{session['session_id']}",
            },
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)
        first_value = roll_response.json()["attempt"]["result_value"]

        prepare_response = self.client.post(
            f"/v1/session/{session['session_id']}/prepare-report",
            json={"idempotency_key": f"prepare-{session['session_id']}"},
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)

        submit_response = self.client.post(
            f"/v1/session/{session['session_id']}/submit-report",
            json={
                "reported_value": first_value,
                "reaction_ms": 1200,
                "idempotency_key": f"submit-{session['session_id']}",
                "language": "es",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)

    def parse_csv(self, content: bytes) -> list[dict[str, str]]:
        if not content:
            return []
        return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))

    def test_pause_blocks_new_access_and_resume_reenables_it(self) -> None:
        pause_response = self.client.post(
            "/admin/experiment/pause",
            json={"reason": "fraud review"},
        )
        self.assertEqual(pause_response.status_code, 200, pause_response.text)
        self.assertEqual(pause_response.json()["experiment_status"], "paused")

        blocked = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(1),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "pause-blocked",
            },
        )
        self.assertEqual(blocked.status_code, 423, blocked.text)

        resume_response = self.client.post(
            "/admin/experiment/resume",
            json={"reason": "fixed"},
        )
        self.assertEqual(resume_response.status_code, 200, resume_response.text)
        self.assertEqual(resume_response.json()["experiment_status"], "active")

        allowed = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(1),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "pause-unblocked",
            },
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_interest_signup_is_stored_and_exported(self) -> None:
        self.client.post("/admin/experiment/pause", json={"reason": "mail list"})
        response = self.client.post(
            "/v1/interest-signup",
            json={"email": "user@example.com", "language": "en"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        with Session(engine) as db:
            stored = db.exec(select(InterestSignup)).all()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0].email_normalized, "user@example.com")
            self.assertEqual(stored[0].language_used, "en")

        export_response = self.client.get("/admin/export/interest_signups.csv")
        self.assertEqual(export_response.status_code, 200, export_response.text)
        rows = self.parse_csv(export_response.content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["email_normalized"], "user@example.com")

    def test_admin_experiment_and_dashboard_report_prize_totals(self) -> None:
        self.complete_winner_session(bracelet_code(2))

        experiment_response = self.client.get("/admin/experiment")
        self.assertEqual(experiment_response.status_code, 200, experiment_response.text)
        payload = experiment_response.json()
        self.assertEqual(payload["prizes"]["winner_count"], 1)
        self.assertGreaterEqual(payload["prizes"]["total_prize_amount_eur"], 10)

        dashboard_response = self.client.get("/admin/dashboard")
        self.assertEqual(dashboard_response.status_code, 200, dashboard_response.text)
        self.assertIn("Parar experimento", dashboard_response.text)
        self.assertIn("Personas premiadas", dashboard_response.text)
        self.assertIn("Importe total de premios", dashboard_response.text)

    def test_pause_state_is_persisted(self) -> None:
        self.client.post("/admin/experiment/pause", json={"reason": "manual"})
        with Session(engine) as db:
            state = db.get(ExperimentState, "global")
            self.assertEqual(state.experiment_status, "paused")
            self.assertIsNotNone(state.paused_at)
            self.assertEqual(state.pause_reason, "manual")


if __name__ == "__main__":
    unittest.main()
