import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_experimental_design_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, bootstrap_demo_data
from models import Claim, SessionRecord, SnapshotRecord


def bracelet_code(seed: int) -> str:
    return f"EXPD{seed:04d}"


class ExperimentalDesignTests(unittest.TestCase):
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
        self.next_bracelet_seed = 1

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

    def access_treatment(self, treatment_key: str, installation_prefix: str) -> dict:
        for offset in range(1, 160):
            session = self.access_session(
                bracelet_code(self.next_bracelet_seed),
                f"{installation_prefix}-{offset}",
            )
            self.next_bracelet_seed += 1
            if session["treatment_key"] == treatment_key:
                return session
        self.fail(f"No se encontro el tratamiento {treatment_key}")

    def session_headers(self, session_id: str) -> dict[str, str]:
        return self.session_headers_by_id[session_id]

    def move_session_to_report(self, session: dict) -> dict:
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
                "reaction_ms": 900,
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
        return prepare_response.json()["session"]

    def test_public_design_is_control_plus_norm_0_to_norm_60(self) -> None:
        response = self.client.get("/v1/config")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()

        expected_treatments = ["control"] + [f"norm_{count}" for count in range(61)]
        self.assertEqual(payload["treatments"], expected_treatments)
        self.assertEqual(payload["schema_version"], "sonar-2026-v9")
        self.assertEqual(payload["experiment_version"], "sonar-2026-field-v5")
        self.assertEqual(payload["current_phase"], "design_62_treatments_v1")
        self.assertEqual(payload["displayed_denominator"], 60)
        self.assertNotIn("seed_low", payload["treatments"])
        self.assertNotIn("seed_high", payload["treatments"])
        self.assertNotIn("seed_initial_counts", payload)

    def test_prepare_report_control_keeps_social_norm_null(self) -> None:
        prepared = self.move_session_to_report(
            self.access_treatment("control", "control-session")
        )
        snapshot = prepared["report_snapshot"]
        self.assertEqual(snapshot["treatment_key"], "control")
        self.assertIsNone(snapshot["count_target"])
        self.assertIsNone(snapshot["denominator"])
        self.assertIsNone(snapshot["target_value"])

    def test_prepare_report_uses_fixed_norm_counts(self) -> None:
        for treatment_key, expected_count in (
            ("norm_0", 0),
            ("norm_17", 17),
            ("norm_60", 60),
        ):
            prepared = self.move_session_to_report(
                self.access_treatment(treatment_key, f"fixed-{treatment_key}")
            )
            snapshot = prepared["report_snapshot"]
            self.assertEqual(snapshot["treatment_key"], treatment_key)
            self.assertEqual(snapshot["count_target"], expected_count)
            self.assertEqual(snapshot["denominator"], 60)
            self.assertEqual(snapshot["target_value"], 6)

    def test_prepare_snapshot_and_claim_persist_same_fixed_norm(self) -> None:
        session = self.access_treatment("norm_17", "snapshot-claim")
        prepared = self.move_session_to_report(session)
        session_id = session["session_id"]
        headers = self.session_headers(session_id)
        reported_value = prepared["first_result_value"]

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": reported_value,
                "reaction_ms": 1200,
                "idempotency_key": f"submit-{session_id}",
                "language": "es",
            },
            headers=headers,
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)

        with Session(engine) as db:
            record = db.get(SessionRecord, session_id)
            claim = db.exec(select(Claim).where(Claim.session_id == session_id)).first()
            snapshot = db.exec(
                select(SnapshotRecord).where(SnapshotRecord.session_id == session_id)
            ).first()

            self.assertIsNotNone(record)
            self.assertIsNotNone(claim)
            self.assertIsNotNone(snapshot)
            self.assertEqual(record.report_snapshot_treatment, "norm_17")
            self.assertEqual(record.report_snapshot_count_target, 17)
            self.assertEqual(record.report_snapshot_denominator, 60)
            self.assertEqual(record.report_snapshot_target_value, 6)
            self.assertEqual(claim.displayed_treatment_key, "norm_17")
            self.assertEqual(claim.displayed_count_target, 17)
            self.assertEqual(claim.displayed_denominator, 60)
            self.assertEqual(claim.displayed_target_value, 6)
            self.assertEqual(snapshot.treatment_key, "norm_17")
            self.assertEqual(snapshot.displayed_count_target, 17)
            self.assertEqual(snapshot.displayed_denominator, 60)


if __name__ == "__main__":
    unittest.main()
