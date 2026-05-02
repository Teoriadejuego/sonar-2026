import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_runtime_hardening_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, bootstrap_demo_data
from models import Series, SeriesWindowEntry, SessionRecord


def bracelet_code(seed: int) -> str:
    return f"HARD{seed:04d}"


class RuntimeHardeningTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        self.client = TestClient(app)
        self.session_headers_by_id: dict[str, dict[str, str]] = {}

    def access_session(self, bracelet_id: str, installation_id: str) -> dict:
        response = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": installation_id,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        session = response.json()["session"]
        self.session_headers_by_id[session["session_id"]] = {
            "X-Sonar-Installation": installation_id,
        }
        return session

    def access_non_control_session(self, start_seed: int, installation_id: str) -> dict:
        seed = start_seed
        while True:
            session = self.access_session(bracelet_code(seed), installation_id)
            if session["treatment_key"] != "control":
                return session
            seed += 1

    def session_headers(self, session_id: str) -> dict[str, str]:
        return self.session_headers_by_id[session_id]

    def test_assigned_session_cannot_jump_directly_to_game(self) -> None:
        session = self.access_session(bracelet_code(1), "install-a")
        response = self.client.post(
            f"/v1/session/{session['session_id']}/screen",
            json={"screen": "game"},
            headers=self.session_headers(session["session_id"]),
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("Pantalla invalida", response.text)

    def test_same_bracelet_cannot_resume_from_other_installation(self) -> None:
        bracelet_id = bracelet_code(2)
        self.access_session(bracelet_id, "install-a")
        second_access = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "install-b",
            },
        )
        self.assertEqual(second_access.status_code, 409, second_access.text)
        self.assertIn("sesion activa", second_access.text)

    def test_wrong_installation_header_cannot_roll_foreign_session(self) -> None:
        session = self.access_session(bracelet_code(3), "install-a")
        response = self.client.post(
            f"/v1/session/{session['session_id']}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 700,
                "idempotency_key": f"roll-{session['session_id']}",
            },
            headers={"X-Sonar-Installation": "install-b"},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIn("otro dispositivo", response.text)

    def test_submit_report_does_not_update_legacy_actual_window(self) -> None:
        session = self.access_non_control_session(10, "install-fixed-norm")
        session_id = session["session_id"]
        headers = self.session_headers(session_id)

        to_comprehension = self.client.post(
            f"/v1/session/{session_id}/screen",
            json={"screen": "comprehension"},
            headers=headers,
        )
        self.assertEqual(to_comprehension.status_code, 200, to_comprehension.text)

        to_game = self.client.post(
            f"/v1/session/{session_id}/screen",
            json={"screen": "game"},
            headers=headers,
        )
        self.assertEqual(to_game.status_code, 200, to_game.text)

        roll_response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 800,
                "idempotency_key": f"roll-{session_id}",
            },
            headers=headers,
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)

        prepare_response = self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
            headers=headers,
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": 6,
                "reaction_ms": 1200,
                "idempotency_key": f"submit-{session_id}",
                "language": "es",
            },
            headers=headers,
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)

        with Session(engine) as db:
            record = db.get(SessionRecord, session_id)
            series = db.exec(
                select(Series).where(Series.id == record.series_id)
            ).first()
            entries = db.exec(
                select(SeriesWindowEntry).where(
                    SeriesWindowEntry.series_id == record.series_id,
                    SeriesWindowEntry.window_type == "actual",
                )
            ).all()
            self.assertIsNotNone(series)
            self.assertEqual(len(entries), 0)
            self.assertEqual(series.actual_window_version, 0)
            self.assertEqual(series.actual_count_target, 0)


if __name__ == "__main__":
    unittest.main()
