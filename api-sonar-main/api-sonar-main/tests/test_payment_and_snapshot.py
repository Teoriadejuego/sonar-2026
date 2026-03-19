import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_payment_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, bootstrap_demo_data
from models import Payment, PayoutRequest, SessionRecord, SnapshotRecord


class PaymentAndSnapshotTests(unittest.TestCase):
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
                "language": "en",
                "client_installation_id": f"payment-{bracelet_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def make_winner(self, session_id: str) -> None:
        with Session(engine) as db:
            record = db.get(SessionRecord, session_id)
            record.selected_for_payment = True
            db.add(record)
            db.commit()

    def access_non_control_session(self, start_bracelet: int) -> dict:
        next_bracelet = start_bracelet
        while True:
            session = self.access_session(str(next_bracelet))
            if session["treatment_key"] != "control":
                return session
            next_bracelet += 1

    def test_display_snapshot_persists_exact_visible_copy(self) -> None:
        session = self.access_non_control_session(10000010)
        session_id = session["session_id"]
        self.make_winner(session_id)

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
        prepared_snapshot = prepare_response.json()["session"]["report_snapshot"]
        expected_message = (
            f"{prepared_snapshot['count_target']} out of "
            f"{prepared_snapshot['denominator']} previous participants "
            f"reported a {prepared_snapshot['target_value']}."
        )

        self.client.post(
            f"/v1/session/{session_id}/display-snapshot",
            json={
                "screen_name": "report",
                "language": "en",
                "treatment_message_text": expected_message,
                "rerolls_visible": [],
            },
        )

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": first_value,
                "reaction_ms": 1700,
                "idempotency_key": f"submit-{session_id}",
                "language": "en",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        completed = submit_response.json()["session"]

        self.client.post(
            f"/v1/session/{session_id}/display-snapshot",
            json={
                "screen_name": "exit",
                "language": "en",
                "final_message_text": "Your response has been recorded and you were selected for payment.",
                "final_amount_eur": int(completed["payment"]["amount_eur"]),
                "payout_reference_shown": completed["payment"]["reference_code"],
            },
        )

        with Session(engine) as db:
            snapshot = db.exec(
                select(SnapshotRecord).where(SnapshotRecord.session_id == session_id)
            ).first()
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.language_used, "en")
            self.assertEqual(snapshot.displayed_message_text, expected_message)
            self.assertEqual(
                snapshot.final_message_text,
                "Your response has been recorded and you were selected for payment.",
            )
            self.assertEqual(
                snapshot.payout_reference_shown,
                completed["payment"]["reference_code"],
            )

    def test_payment_lookup_and_submit_prevent_reuse(self) -> None:
        session = self.access_session("10000011")
        session_id = session["session_id"]
        self.make_winner(session_id)

        roll_response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={"attempt_index": 1, "reaction_ms": 900, "idempotency_key": f"roll-{session_id}"},
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)
        first_value = roll_response.json()["attempt"]["result_value"]

        self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
        )
        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": first_value,
                "reaction_ms": 1200,
                "idempotency_key": f"submit-{session_id}",
                "language": "en",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        reference_code = submit_response.json()["session"]["payment"]["reference_code"]

        lookup_response = self.client.post(
            "/v1/payment/lookup",
            json={"code": reference_code},
        )
        self.assertEqual(lookup_response.status_code, 200, lookup_response.text)
        self.assertTrue(lookup_response.json()["valid"])

        first_submit = self.client.post(
            "/v1/payment/submit",
            json={
                "code": reference_code,
                "phone": "0034693494561",
                "language": "en",
                "donation_requested": False,
                "message_text": "",
            },
        )
        self.assertEqual(first_submit.status_code, 200, first_submit.text)
        self.assertEqual(first_submit.json()["status"], "queued")

        second_submit = self.client.post(
            "/v1/payment/submit",
            json={
                "code": reference_code,
                "phone": "0034693494561",
                "language": "en",
                "donation_requested": False,
                "message_text": "",
            },
        )
        self.assertEqual(second_submit.status_code, 409, second_submit.text)

        with Session(engine) as db:
            payment = db.exec(
                select(Payment).where(Payment.payout_reference == reference_code)
            ).first()
            payout_request = db.exec(
                select(PayoutRequest).where(PayoutRequest.payment_id == payment.id)
            ).first()
            self.assertEqual(payment.status, "queued")
            self.assertIsNotNone(payout_request)
            self.assertEqual(payout_request.requested_phone, "34693494561")


if __name__ == "__main__":
    unittest.main()
