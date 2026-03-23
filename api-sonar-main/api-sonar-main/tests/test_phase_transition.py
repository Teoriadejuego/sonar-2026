import os
import shutil
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_phase_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from database import engine
from experiment import (
    PHASE_1_MAIN,
    PHASE_2_ROBUSTNESS,
    PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD,
    WINDOW_SIZE,
    allocation_version_for_phase,
    phase_treatments,
    seed_window_values,
    treatment_config,
    treatment_version_for_phase,
)
from main import app, bootstrap_demo_data, get_or_create_experiment_state
from models import AuditEvent, ExperimentState, Series, SeriesRoot, SessionRecord


def bracelet_code(seed: int) -> str:
    return f"PHAS{seed:04d}"


class PhaseTransitionTests(unittest.TestCase):
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
                "client_installation_id": f"test-{bracelet_id}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def roll_prepare_submit(self, session_id: str, reported_value: int | None = None) -> dict:
        roll_response = self.client.post(
            f"/v1/session/{session_id}/roll",
            json={"attempt_index": 1, "reaction_ms": 1200, "idempotency_key": f"roll-{session_id}"},
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)
        first_value = roll_response.json()["attempt"]["result_value"]
        claim_value = reported_value if reported_value is not None else first_value

        prepare_response = self.client.post(
            f"/v1/session/{session_id}/prepare-report",
            json={"idempotency_key": f"prepare-{session_id}"},
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)

        submit_response = self.client.post(
            f"/v1/session/{session_id}/submit-report",
            json={
                "reported_value": claim_value,
                "reaction_ms": 1800,
                "idempotency_key": f"submit-{session_id}",
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        return submit_response.json()["session"]

    def set_valid_completed_count(self, value: int) -> None:
        with Session(engine) as db:
            state = get_or_create_experiment_state(db)
            state.valid_completed_count = value
            state.updated_at = datetime.now(UTC).replace(tzinfo=None)
            db.add(state)
            db.commit()

    def activate_phase_2_manually(self) -> None:
        with Session(engine) as db:
            state = get_or_create_experiment_state(db)
            state.current_phase = PHASE_2_ROBUSTNESS
            state.phase_2_activated_at = datetime.now(UTC).replace(tzinfo=None)
            state.treatment_version = treatment_version_for_phase(PHASE_2_ROBUSTNESS)
            state.allocation_version = allocation_version_for_phase(PHASE_2_ROBUSTNESS)
            state.updated_at = datetime.now(UTC).replace(tzinfo=None)
            db.add(state)
            db.commit()

    def test_phase_1_does_not_activate_before_threshold(self) -> None:
        self.set_valid_completed_count(PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD - 2)
        session = self.access_session(bracelet_code(1))
        completed = self.roll_prepare_submit(session["session_id"])

        with Session(engine) as db:
            state = get_or_create_experiment_state(db)
            persisted = db.get(SessionRecord, completed["session_id"])
            self.assertEqual(state.current_phase, PHASE_1_MAIN)
            self.assertEqual(
                state.valid_completed_count,
                PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD - 1,
            )
            self.assertEqual(persisted.experiment_phase, PHASE_1_MAIN)
            self.assertTrue(persisted.is_valid_completed)

    def test_phase_2_activates_exactly_at_threshold_and_only_once(self) -> None:
        self.set_valid_completed_count(PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD - 1)
        phase_1_session = self.access_session(bracelet_code(2))
        completed = self.roll_prepare_submit(phase_1_session["session_id"])

        with Session(engine) as db:
            state = get_or_create_experiment_state(db)
            activation_events = db.exec(
                select(AuditEvent).where(AuditEvent.action == "phase_2_activated")
            ).all()
            self.assertEqual(completed["experiment_phase"], PHASE_1_MAIN)
            self.assertEqual(state.current_phase, PHASE_2_ROBUSTNESS)
            self.assertEqual(
                state.valid_completed_count,
                PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD,
            )
            self.assertIsNotNone(state.phase_2_activated_at)
            self.assertEqual(len(activation_events), 1)

        next_session = self.access_session(bracelet_code(3))
        self.assertEqual(next_session["experiment_phase"], PHASE_2_ROBUSTNESS)
        self.roll_prepare_submit(next_session["session_id"])

        with Session(engine) as db:
            activation_events = db.exec(
                select(AuditEvent).where(AuditEvent.action == "phase_2_activated")
            ).all()
            state = db.get(ExperimentState, "global")
            self.assertEqual(len(activation_events), 1)
            self.assertEqual(state.current_phase, PHASE_2_ROBUSTNESS)

    def test_phase_2_uses_new_roots_and_phase_2_treatment_set(self) -> None:
        self.activate_phase_2_manually()
        session = self.access_session(bracelet_code(4))
        expected_treatments = set(phase_treatments(PHASE_2_ROBUSTNESS).keys())

        with Session(engine) as db:
            persisted = db.get(SessionRecord, session["session_id"])
            root = db.get(SeriesRoot, persisted.root_id)
            self.assertEqual(persisted.experiment_phase, PHASE_2_ROBUSTNESS)
            self.assertEqual(root.experiment_phase, PHASE_2_ROBUSTNESS)
            self.assertIn(persisted.treatment_key, expected_treatments)

    def test_seed_windows_for_five_norm_treatments_are_initialized_correctly(self) -> None:
        five_norm_keys = [
            treatment_key
            for treatment_key, config in phase_treatments(PHASE_2_ROBUSTNESS).items()
            if config["treatment_family"] == "five_norm"
        ]

        for treatment_key in five_norm_keys:
            config = treatment_config(PHASE_2_ROBUSTNESS, treatment_key)
            values = seed_window_values(PHASE_2_ROBUSTNESS, treatment_key)
            target_value = int(config["norm_target_value"])
            seed_count = int(config["seed_initial_count"])
            fill_order = str(config.get("seed_fill_order"))

            self.assertEqual(len(values), WINDOW_SIZE)
            self.assertEqual(sum(1 for value in values if value == target_value), seed_count)
            if fill_order == "target_first":
                self.assertEqual(values[:5], [target_value] * 5)
            else:
                self.assertNotEqual(values[:5], [target_value] * 5)

    def test_phase_2_snapshot_can_show_norms_over_five(self) -> None:
        self.activate_phase_2_manually()
        target_session = None
        bracelet_seed = 20
        five_norm_keys = {
            treatment_key
            for treatment_key, config in phase_treatments(PHASE_2_ROBUSTNESS).items()
            if config["treatment_family"] == "five_norm"
        }
        expected_counts = {
            int(config["seed_initial_count"])
            for config in phase_treatments(PHASE_2_ROBUSTNESS).values()
            if config["treatment_family"] == "five_norm"
        }

        while target_session is None:
            session = self.access_session(bracelet_code(bracelet_seed))
            bracelet_seed += 1
            if session["treatment_key"] in five_norm_keys:
                target_session = session

        roll_response = self.client.post(
            f"/v1/session/{target_session['session_id']}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 900,
                "idempotency_key": f"roll-{target_session['session_id']}",
            },
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)

        prepare_response = self.client.post(
            f"/v1/session/{target_session['session_id']}/prepare-report",
            json={"idempotency_key": f"prepare-{target_session['session_id']}"},
        )
        self.assertEqual(prepare_response.status_code, 200, prepare_response.text)
        snapshot = prepare_response.json()["session"]["report_snapshot"]

        self.assertEqual(snapshot["target_value"], 5)
        self.assertIn(snapshot["count_target"], expected_counts)
        self.assertIn(" 5.", snapshot["message"])

    def test_prepared_phase_1_sessions_do_not_reactivate_phase_2_twice(self) -> None:
        self.set_valid_completed_count(PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD - 1)
        session_a = self.access_session(bracelet_code(30))
        session_b = self.access_session(bracelet_code(31))

        self.roll_prepare_submit(session_a["session_id"])
        self.roll_prepare_submit(session_b["session_id"])

        with Session(engine) as db:
            activation_events = db.exec(
                select(AuditEvent).where(AuditEvent.action == "phase_2_activated")
            ).all()
            state = db.get(ExperimentState, "global")
            self.assertEqual(len(activation_events), 1)
            self.assertEqual(state.current_phase, PHASE_2_ROBUSTNESS)


if __name__ == "__main__":
    unittest.main()
