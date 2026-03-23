import csv
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_operational_notes_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine
from main import app, bootstrap_demo_data


def bracelet_code(seed: int) -> str:
    return f"OPER{seed:04d}"


class OperationalNotesAndQrTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        self.client = TestClient(app)

    def parse_csv(self, content: bytes) -> list[dict[str, str]]:
        if not content:
            return []
        return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))

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
                "client_installation_id": f"ops-{bracelet_id}",
                "referral_source": "qr",
                "referral_medium": "offline_poster",
                "referral_campaign": "carteles_sonar",
                "referral_link_id": "poster-entrada-a",
                "qr_entry_code": "poster-entrada-a",
                "referral_path": "/?qr=poster-entrada-a&src=qr",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def complete_session(self, bracelet_id: str) -> dict:
        session = self.access_session(bracelet_id)
        session_id = session["session_id"]

        roll_response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={"attempt_index": 1, "reaction_ms": 900, "idempotency_key": f"roll-{session_id}"},
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)
        first_value = roll_response.json()["attempt"]["result_value"]

        prepare_response = self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": first_value,
                "reaction_ms": 1200,
                "idempotency_key": f"submit-{session_id}",
                "language": "es",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        return submit_response.json()["session"]

    def test_operational_note_is_attached_to_new_records_and_exports(self) -> None:
        activate = self.client.post(
            "/admin/operational-notes/activate",
            json={"note_text": "Cambio de localizacion al Hall B a las 18:40"},
        )
        self.assertEqual(activate.status_code, 200, activate.text)

        session = self.complete_session(bracelet_code(21))
        self.assertEqual(session["qr_entry_code"], "poster-entrada-a")
        self.assertEqual(
            session["operational_note"]["note_text"],
            "Cambio de localizacion al Hall B a las 18:40",
        )

        telemetry_response = self.client.post(
            "/v1/telemetry/batch",
            json={
                "session_id": session["session_id"],
                "events": [
                    {
                        "event_type": "network",
                        "event_name": "api_success",
                        "screen_name": "exit",
                        "client_ts": 1234,
                        "event_sequence_number": 1,
                        "endpoint_name": "/v1/session/access",
                        "request_method": "POST",
                        "status_code": 200,
                        "latency_ms": 120,
                    }
                ],
            },
        )
        self.assertEqual(telemetry_response.status_code, 200, telemetry_response.text)

        session_rows = self.parse_csv(self.client.get("/admin/export/sessions.csv").content)
        self.assertEqual(session_rows[0]["qr_entry_code"], "poster-entrada-a")
        self.assertEqual(
            session_rows[0]["operational_note_text"],
            "Cambio de localizacion al Hall B a las 18:40",
        )

        claim_rows = self.parse_csv(self.client.get("/admin/export/claims.csv").content)
        self.assertEqual(
            claim_rows[0]["operational_note_text"],
            "Cambio de localizacion al Hall B a las 18:40",
        )

        telemetry_rows = self.parse_csv(self.client.get("/admin/export/telemetry.csv").content)
        self.assertTrue(
            any(
                row["operational_note_text"] == "Cambio de localizacion al Hall B a las 18:40"
                for row in telemetry_rows
            )
        )

        notes_rows = self.parse_csv(self.client.get("/admin/export/operational_notes.csv").content)
        self.assertEqual(len(notes_rows), 1)
        self.assertEqual(notes_rows[0]["status"], "active")

    def test_operational_note_can_be_cleared(self) -> None:
        self.client.post(
            "/admin/operational-notes/activate",
            json={"note_text": "Incidencia breve"},
        )
        clear = self.client.post("/admin/operational-notes/clear")
        self.assertEqual(clear.status_code, 200, clear.text)
        self.assertEqual(clear.json()["active_operational_note"]["status"], "inactive")


if __name__ == "__main__":
    unittest.main()
