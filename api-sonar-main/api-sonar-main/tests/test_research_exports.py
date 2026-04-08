import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_exports_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine
from main import app, bootstrap_demo_data


def bracelet_code(seed: int) -> str:
    return f"EXPO{seed:04d}"


def recall_bucket(count: int) -> int:
    if count <= 20:
        return 20
    if count <= 40:
        return 40
    return 60


class ResearchExportsTests(unittest.TestCase):
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
                "landing_visible_ms": 3200,
                "info_panels_opened": ["study", "dataProtection"],
                "info_panel_durations_ms": {"study": 2100, "dataProtection": 1400},
                "client_installation_id": f"exports-{bracelet_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def access_non_control_session(self, start_seed: int) -> dict:
        next_seed = start_seed
        while True:
            session = self.access_session(bracelet_code(next_seed))
            if session["treatment_key"] != "control":
                return session
            next_seed += 1

    def complete_session(self, bracelet_id: str) -> dict:
        start_seed = int(bracelet_id[4:])
        session = self.access_non_control_session(start_seed)
        session_id = session["session_id"]

        roll_response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={"attempt_index": 1, "reaction_ms": 1100, "idempotency_key": f"roll-{session_id}"},
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)
        first_value = roll_response.json()["attempt"]["result_value"]

        prepare_response = self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)

        snapshot = prepare_response.json()["session"]["report_snapshot"]
        self.client.post(
            f"/v1/session/{session_id}/display-snapshot",
            json={
                "screen_name": "report",
                "language": "es",
                "treatment_message_text": snapshot["message"],
                "rerolls_visible": [],
            },
        )

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": first_value,
                "reaction_ms": 1800,
                "idempotency_key": f"submit-{session_id}",
                "language": "es",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        completed = submit_response.json()["session"]

        followup_response = self.client.post(
            f"/v1/session/{session_id}/claim-followup",
            json={
                "crowd_prediction_value": 3,
                "social_recall_count": recall_bucket(snapshot["count_target"]),
                "language": "es",
            },
        )
        self.assertEqual(followup_response.status_code, 200, followup_response.text)
        return followup_response.json()["session"]

    def parse_csv(self, content: bytes) -> list[dict[str, str]]:
        if not content:
            return []
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        return list(reader)

    def test_exports_page_and_dashboard_are_available(self) -> None:
        completed = self.complete_session(bracelet_code(1))

        exports_response = self.client.get("/admin/exports")
        self.assertEqual(exports_response.status_code, 200)
        self.assertIn("Data Exports", exports_response.text)
        self.assertIn("Exportar dataset analitico completo", exports_response.text)
        self.assertIn("Exportar telemetria completa", exports_response.text)

        dashboard_response = self.client.get("/admin/dashboard")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("Dashboard cientifico-operativo", dashboard_response.text)
        self.assertIn(completed["experiment_phase"], dashboard_response.text)
        self.assertIn("Mazos de tratamientos", dashboard_response.text)

    def test_sessions_csv_is_analytic_and_sanitized(self) -> None:
        self.complete_session(bracelet_code(2))

        response = self.client.get("/admin/export/sessions.csv")
        self.assertEqual(response.status_code, 200, response.text)
        rows = self.parse_csv(response.content)
        self.assertEqual(len(rows), 1)
        self.assertIn("session_id", rows[0])
        self.assertIn("reported_six", rows[0])
        self.assertIn("treatment_key", rows[0])
        self.assertIn("is_control", rows[0])
        self.assertIn("displayed_count_target", rows[0])
        self.assertIn("displayed_denominator", rows[0])
        self.assertIn("treatment_deck_index", rows[0])
        self.assertIn("result_deck_index", rows[0])
        self.assertIn("result_deck_treatment_key", rows[0])
        self.assertIn("result_deck_treatment_cycle_index", rows[0])
        self.assertIn("payment_deck_index", rows[0])
        self.assertIn("payout_eligible", rows[0])
        self.assertIn("crowd_prediction_value", rows[0])
        self.assertIn("social_recall_count", rows[0])
        self.assertIn("social_recall_correct", rows[0])
        self.assertEqual(rows[0]["crowd_prediction_value"], "3")
        self.assertEqual(rows[0]["social_recall_correct"], "True")
        self.assertNotIn("requested_phone", rows[0])
        self.assertNotIn("payout_reference_shown", rows[0])

    def test_analytic_bundle_contains_manifest_and_excludes_admin_tables(self) -> None:
        self.complete_session(bracelet_code(3))

        response = self.client.get("/admin/export/bundle/analytic.zip")
        self.assertEqual(response.status_code, 200, response.text)
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = set(archive.namelist())
        self.assertIn("sessions.csv", names)
        self.assertIn("throws.csv", names)
        self.assertIn("claims.csv", names)
        self.assertIn("treatment_decks.csv", names)
        self.assertIn("result_decks.csv", names)
        self.assertIn("payment_decks.csv", names)
        self.assertIn("manifest.json", names)
        self.assertIn("README_EXPORT.md", names)
        self.assertIn("DATASETS_CODEBOOK.md", names)
        self.assertNotIn("payments_admin.csv", names)

        claims_rows = self.parse_csv(archive.read("claims.csv"))
        self.assertIn("crowd_prediction_value", claims_rows[0])
        self.assertIn("social_recall_count", claims_rows[0])
        self.assertIn("social_recall_correct", claims_rows[0])
        self.assertEqual(claims_rows[0]["crowd_prediction_value"], "3")

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        exported_datasets = {item["dataset"] for item in manifest["tables"]}
        self.assertIn("sessions", exported_datasets)
        self.assertIn("treatment_deck_cards", exported_datasets)
        self.assertIn("result_deck_cards", exported_datasets)
        self.assertIn("payment_deck_cards", exported_datasets)
        self.assertNotIn("payments_admin", exported_datasets)

    def test_deck_exports_allow_unambiguous_reconstruction(self) -> None:
        self.complete_session(bracelet_code(4))

        treatment_cards = self.parse_csv(
            self.client.get("/admin/export/treatment_deck_cards.csv").content
        )
        result_cards = self.parse_csv(
            self.client.get("/admin/export/result_deck_cards.csv").content
        )
        payment_cards = self.parse_csv(
            self.client.get("/admin/export/payment_deck_cards.csv").content
        )

        self.assertTrue(any(row["assigned_session_id"] for row in treatment_cards))
        self.assertTrue(any(row["assigned_session_id"] for row in result_cards))
        self.assertTrue(any(row["assigned_session_id"] for row in payment_cards))
        self.assertIn("deck_index", treatment_cards[0])
        self.assertIn("treatment_key", result_cards[0])
        self.assertIn("treatment_cycle_index", result_cards[0])
        self.assertIn("result_value", result_cards[0])
        self.assertIn("payout_eligible", payment_cards[0])

        claims_rows = self.parse_csv(self.client.get("/admin/export/claims.csv").content)
        self.assertEqual(claims_rows[0]["crowd_prediction_value"], "3")
        self.assertEqual(claims_rows[0]["social_recall_correct"], "True")


if __name__ == "__main__":
    unittest.main()
