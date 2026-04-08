import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_deck_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from experiment import TREATMENT_KEYS, result_deck_seed, result_deck_values
from main import app, bootstrap_demo_data
from models import PaymentDeckCard, ResultDeckCard, SessionRecord, TreatmentDeckCard


def bracelet_code(prefix: str, seed: int) -> str:
    return f"{prefix}{seed:04d}"


class DeckAssignmentTests(unittest.TestCase):
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
                "client_installation_id": f"deck-{bracelet_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def roll_first_result(self, session_id: str) -> int:
        response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 900,
                "idempotency_key": f"roll-{session_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["attempt"]["result_value"]

    def test_treatment_deck_contains_all_62_treatments_once_per_block(self) -> None:
        seen_treatments: list[str] = []
        seen_positions: set[int] = set()
        for seed in range(1, 63):
            session = self.access_session(bracelet_code("TRTA", seed))
            self.assertEqual(session["treatment_deck_index"], 1)
            self.assertNotIn(session["treatment_card_position"], seen_positions)
            seen_positions.add(session["treatment_card_position"])
            seen_treatments.append(session["treatment_key"])

        self.assertEqual(len(seen_treatments), 62)
        self.assertEqual(set(seen_treatments), set(TREATMENT_KEYS))
        self.assertEqual(len(set(seen_treatments)), 62)

        next_session = self.access_session(bracelet_code("TRTA", 63))
        self.assertEqual(next_session["treatment_deck_index"], 2)

    def test_result_deck_contains_four_of_each_value_in_four_six_card_rounds(self) -> None:
        values = result_deck_values(result_deck_seed("norm_0", 1))
        counts = {value: values.count(value) for value in range(1, 7)}

        self.assertEqual(len(values), 24)
        self.assertEqual(counts, {1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4})
        for start in range(0, 24, 6):
            self.assertEqual(set(values[start : start + 6]), {1, 2, 3, 4, 5, 6})

    def test_each_treatment_gets_all_six_values_after_six_treatment_rounds(self) -> None:
        values_by_treatment: dict[str, list[int]] = {
            treatment_key: [] for treatment_key in TREATMENT_KEYS
        }

        for seed in range(1, 62 * 6 + 1):
            session = self.access_session(bracelet_code("RSLT", seed))
            value = self.roll_first_result(session["session_id"])
            values_by_treatment[session["treatment_key"]].append(value)

        for treatment_key, values in values_by_treatment.items():
            self.assertEqual(
                len(values),
                6,
                f"{treatment_key} no recibio seis sesiones en seis rondas completas",
            )
            self.assertEqual(
                set(values),
                {1, 2, 3, 4, 5, 6},
                f"{treatment_key} no quedo equilibrado en la primera ronda de seis resultados",
            )

    def test_payment_deck_has_exactly_one_winner_per_hundred(self) -> None:
        winners = 0
        seen_positions: set[int] = set()
        for seed in range(1, 101):
            session = self.access_session(bracelet_code("PAYM", seed))
            self.assertEqual(session["payment_deck_index"], 1)
            self.assertNotIn(session["payment_card_position"], seen_positions)
            seen_positions.add(session["payment_card_position"])
            winners += int(session["selected_for_payment"])

        self.assertEqual(winners, 1)
        next_session = self.access_session(bracelet_code("PAYM", 101))
        self.assertEqual(next_session["payment_deck_index"], 2)

    def test_access_is_idempotent_for_same_bracelet(self) -> None:
        first = self.access_session(bracelet_code("IDEM", 1))
        second = self.access_session(bracelet_code("IDEM", 1))
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(first["treatment_card_position"], second["treatment_card_position"])
        self.assertEqual(first["result_card_position"], second["result_card_position"])
        self.assertEqual(first["payment_card_position"], second["payment_card_position"])

    def test_demo_ids_are_stable_and_documented(self) -> None:
        control = self.access_session("CTRL1234")
        norm_zero = self.access_session("NORM0000")
        norm_one = self.access_session("NORM0001")

        self.assertEqual(control["treatment_key"], "control")
        self.assertTrue(control["selected_for_payment"])
        self.assertEqual(self.roll_first_result(control["session_id"]), 6)

        self.assertEqual(norm_zero["treatment_key"], "norm_0")
        self.assertFalse(norm_zero["selected_for_payment"])
        self.assertEqual(self.roll_first_result(norm_zero["session_id"]), 4)

        self.assertEqual(norm_one["treatment_key"], "norm_1")
        self.assertFalse(norm_one["selected_for_payment"])
        self.assertEqual(self.roll_first_result(norm_one["session_id"]), 5)

    def test_assigned_cards_persist_without_duplicates(self) -> None:
        for seed in range(1, 21):
            self.access_session(bracelet_code("PERS", seed))

        with Session(engine) as db:
            treatment_cards = db.exec(
                select(TreatmentDeckCard).where(TreatmentDeckCard.assigned_session_id != None)  # noqa: E711
            ).all()
            result_cards = db.exec(
                select(ResultDeckCard).where(ResultDeckCard.assigned_session_id != None)  # noqa: E711
            ).all()
            payment_cards = db.exec(
                select(PaymentDeckCard).where(PaymentDeckCard.assigned_session_id != None)  # noqa: E711
            ).all()
            sessions = db.exec(select(SessionRecord)).all()

            self.assertEqual(len(treatment_cards), 20)
            self.assertEqual(len(result_cards), 20)
            self.assertEqual(len(payment_cards), 20)
            self.assertEqual(len(sessions), 20)
            self.assertEqual(
                len({card.assigned_session_id for card in treatment_cards}),
                len(treatment_cards),
            )
            self.assertEqual(
                len({card.assigned_session_id for card in result_cards}),
                len(result_cards),
            )
            self.assertEqual(
                len({card.assigned_session_id for card in payment_cards}),
                len(payment_cards),
            )


if __name__ == "__main__":
    unittest.main()
