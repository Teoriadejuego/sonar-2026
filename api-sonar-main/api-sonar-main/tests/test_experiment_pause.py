import csv
import io
import json
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
from models import (
    EmailInterest,
    ExperimentClosureLog,
    ExperimentState,
    InterestSignup,
    SessionRecord,
    Throw,
)


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
            mirrored = db.exec(select(EmailInterest)).all()
            self.assertEqual(len(mirrored), 1)
            self.assertEqual(mirrored[0].email, "user@example.com")
            self.assertEqual(mirrored[0].source, "experiment_paused")

        export_response = self.client.get("/admin/export/interest_signups.csv")
        self.assertEqual(export_response.status_code, 200, export_response.text)
        rows = self.parse_csv(export_response.content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["email_normalized"], "user@example.com")

    def test_interest_signup_is_also_available_when_experiment_is_closed(self) -> None:
        self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closed", "reason": "festival end"},
        )
        response = self.client.post(
            "/v1/interest-signup",
            json={"email": "closed@example.com", "language": "es"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        with Session(engine) as db:
            stored = db.exec(select(InterestSignup)).all()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0].email_normalized, "closed@example.com")
            self.assertEqual(stored[0].source_screen, "experiment_closed")
            mirrored = db.exec(select(EmailInterest)).all()
            self.assertEqual(len(mirrored), 1)
            self.assertEqual(mirrored[0].email, "closed@example.com")
            self.assertEqual(mirrored[0].source, "experiment_closed")

    def test_interest_endpoint_stores_email_interest_with_panic_screen_source(self) -> None:
        response = self.client.post(
            "/interest",
            json={"email": "panic@example.com"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["stored"])
        self.assertTrue(payload["created"])
        self.assertEqual(payload["source"], "panic_screen")

        with Session(engine) as db:
            stored = db.exec(select(EmailInterest)).all()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0].email, "panic@example.com")
            self.assertEqual(stored[0].source, "panic_screen")

    def test_interest_endpoint_is_idempotent_per_email_and_source(self) -> None:
        first = self.client.post(
            "/interest",
            json={"email": "panic@example.com", "source": "panic-screen"},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["created"])

        second = self.client.post(
            "/interest",
            json={"email": "panic@example.com", "source": "panic_screen"},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertFalse(second.json()["created"])

        with Session(engine) as db:
            stored = db.exec(select(EmailInterest)).all()
            self.assertEqual(len(stored), 1)

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
        self.assertIn("Modo actual", dashboard_response.text)
        self.assertIn("Activar cierre suave", dashboard_response.text)
        self.assertIn("Cerrar ahora", dashboard_response.text)
        self.assertIn("Personas premiadas", dashboard_response.text)
        self.assertIn("Importe total de premios", dashboard_response.text)

    def test_pause_state_is_persisted(self) -> None:
        self.client.post("/admin/experiment/pause", json={"reason": "manual"})
        with Session(engine) as db:
            state = db.get(ExperimentState, "global")
            self.assertEqual(state.experiment_status, "paused")
            self.assertIsNotNone(state.paused_at)
            self.assertEqual(state.pause_reason, "manual")

    def test_closing_mode_blocks_new_access_but_keeps_config_visible(self) -> None:
        mode_response = self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closing", "reason": "cierre progresivo"},
        )
        self.assertEqual(mode_response.status_code, 200, mode_response.text)
        self.assertEqual(mode_response.json()["experiment_mode"], "closing")
        self.assertFalse(mode_response.json()["accepting_entries"])
        self.assertTrue(mode_response.json()["accepting_inflight_sessions"])

        blocked = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(30),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "closing-blocked",
            },
        )
        self.assertEqual(blocked.status_code, 423, blocked.text)
        self.assertIn("cerrando", blocked.text)

        config_response = self.client.get("/v1/config")
        self.assertEqual(config_response.status_code, 200, config_response.text)
        self.assertEqual(config_response.json()["experiment_control"]["mode"], "closing")

    def test_closing_mode_still_allows_existing_sessions(self) -> None:
        session = self.access_session(bracelet_code(32))

        mode_response = self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closing", "reason": "cierre progresivo"},
        )
        self.assertEqual(mode_response.status_code, 200, mode_response.text)

        resumed = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(32),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": f"pause-{bracelet_code(32)}",
            },
        )
        self.assertEqual(resumed.status_code, 200, resumed.text)
        payload = resumed.json()
        self.assertFalse(payload["created_now"])
        self.assertEqual(payload["session"]["session_id"], session["session_id"])
        self.assertEqual(payload["session"]["state"], "assigned")
        self.assertEqual(payload["session"]["screen"], "instructions")

    def test_closed_mode_blocks_new_access_and_terminalizes_existing_session(self) -> None:
        session = self.access_session(bracelet_code(31))

        mode_response = self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closed", "reason": "evento finalizado"},
        )
        self.assertEqual(mode_response.status_code, 200, mode_response.text)
        self.assertEqual(mode_response.json()["experiment_mode"], "closed")
        self.assertFalse(mode_response.json()["accepting_entries"])
        self.assertFalse(mode_response.json()["accepting_inflight_sessions"])

        existing = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(31),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": f"pause-{bracelet_code(31)}",
            },
        )
        self.assertEqual(existing.status_code, 200, existing.text)
        existing_payload = existing.json()["session"]
        self.assertEqual(existing_payload["session_id"], session["session_id"])
        self.assertEqual(existing_payload["state"], "completed_no_win")
        self.assertEqual(existing_payload["screen"], "exit")
        self.assertFalse(existing_payload["selected_for_payment"])
        self.assertFalse(existing_payload["payment"]["eligible"])
        self.assertIn("experiment_closed", existing_payload["quality_flags"])
        self.assertEqual(existing_payload["terminal_reason"], "experiment_closed")

        blocked = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(310),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "closed-blocked",
            },
        )
        self.assertEqual(blocked.status_code, 423, blocked.text)
        self.assertIn("cerrado", blocked.text)

        with Session(engine) as db:
            state = db.get(ExperimentState, "global")
            self.assertEqual(state.experiment_mode, "closed")
            record = db.get(SessionRecord, session["session_id"])
            self.assertEqual(record.state, "assigned")
            self.assertEqual(record.screen_cursor, "instructions")

    def test_resume_returns_terminal_session_when_mode_closed(self) -> None:
        session = self.access_session(bracelet_code(33))
        self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closed", "reason": "evento finalizado"},
        )

        response = self.client.get(f"/v1/session/{session['session_id']}/resume")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["session"]
        self.assertEqual(payload["state"], "completed_no_win")
        self.assertEqual(payload["screen"], "exit")
        self.assertEqual(payload["terminal_reason"], "experiment_closed")

        with Session(engine) as db:
            record = db.get(SessionRecord, session["session_id"])
            self.assertEqual(record.state, "assigned")
            self.assertEqual(record.screen_cursor, "instructions")
            self.assertEqual(record.resume_count, 1)

    def test_roll_returns_terminal_session_when_mode_closed_without_persisting_throw(self) -> None:
        session = self.access_session(bracelet_code(34))
        self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closed", "reason": "evento finalizado"},
        )

        response = self.client.post(
            f"/v1/session/{session['session_id']}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 500,
                "idempotency_key": f"closed-roll-{session['session_id']}",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["attempt"]["blocked"])
        self.assertEqual(payload["attempt"]["reason"], "experiment_closed")
        self.assertEqual(payload["session"]["state"], "completed_no_win")
        self.assertEqual(payload["session"]["screen"], "exit")

        with Session(engine) as db:
            record = db.get(SessionRecord, session["session_id"])
            self.assertEqual(record.state, "assigned")
            throws = db.exec(
                select(Throw).where(Throw.session_id == session["session_id"])
            ).all()
            self.assertEqual(len(throws), 0)

    def test_prepare_report_returns_terminal_session_when_mode_closed_without_snapshot(self) -> None:
        session = self.access_session(bracelet_code(35))
        roll_response = self.client.post(
            f"/v1/session/{session['session_id']}/roll",
            json={
                "attempt_index": 1,
                "reaction_ms": 500,
                "idempotency_key": f"prepare-live-roll-{session['session_id']}",
            },
        )
        self.assertEqual(roll_response.status_code, 200, roll_response.text)

        self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closed", "reason": "evento finalizado"},
        )

        response = self.client.post(
            f"/v1/session/{session['session_id']}/prepare-report",
            json={"idempotency_key": f"closed-prepare-{session['session_id']}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["session"]
        self.assertEqual(payload["state"], "completed_no_win")
        self.assertEqual(payload["screen"], "exit")
        self.assertEqual(payload["terminal_reason"], "experiment_closed")
        self.assertFalse(payload["payment"]["eligible"])

        with Session(engine) as db:
            record = db.get(SessionRecord, session["session_id"])
            self.assertEqual(record.state, "in_game")
            self.assertEqual(record.screen_cursor, "game")
            self.assertIsNone(record.report_prepared_at)
            self.assertIsNone(record.report_snapshot_treatment)

    def test_closing_mode_creates_closure_log_with_session_and_series_snapshot(self) -> None:
        self.access_session(bracelet_code(36))
        self.access_session(bracelet_code(37))

        response = self.client.post(
            "/admin/experiment/mode",
            json={"mode": "closing", "reason": "cierre analitico"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        with Session(engine) as db:
            logs = db.exec(select(ExperimentClosureLog)).all()
            self.assertEqual(len(logs), 1)
            log_entry = logs[0]
            self.assertEqual(log_entry.experiment_mode, "closing")
            self.assertEqual(log_entry.actor, "admin")
            self.assertEqual(log_entry.reason, "cierre analitico")
            self.assertEqual(log_entry.session_count_total, 2)

            session_counts = json.loads(log_entry.session_state_counts_json)
            self.assertEqual(session_counts, {"assigned": 2})

            series_state = json.loads(log_entry.series_state_json)
            self.assertEqual(log_entry.series_count_total, len(series_state))
            self.assertGreater(len(series_state), 0)
            self.assertIn("series_id", series_state[0])
            self.assertIn("treatment_key", series_state[0])
            self.assertIn("position_counter", series_state[0])

    def test_closure_logs_endpoint_returns_history_without_duplicates_for_idempotent_calls(self) -> None:
        self.access_session(bracelet_code(38))

        self.client.post(
            "/admin/panic",
            json={"soft": True, "reason": "cierre suave"},
        )
        repeat_soft = self.client.post(
            "/admin/panic",
            json={"soft": True, "reason": "cierre suave"},
        )
        self.assertEqual(repeat_soft.status_code, 200, repeat_soft.text)
        self.assertTrue(repeat_soft.json()["idempotent"])

        self.client.post(
            "/admin/panic",
            json={"mode": "closed", "reason": "cierre final"},
        )

        logs_response = self.client.get("/admin/experiment/closure-logs?limit=5")
        self.assertEqual(logs_response.status_code, 200, logs_response.text)
        payload = logs_response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            [item["experiment_mode"] for item in payload["logs"]],
            ["closed", "closing"],
        )
        self.assertEqual(payload["logs"][0]["session_count_total"], 1)
        self.assertIn("assigned", payload["logs"][0]["session_state_counts"])
        self.assertGreater(payload["logs"][0]["series_count_total"], 0)

        experiment_response = self.client.get("/admin/experiment")
        self.assertEqual(experiment_response.status_code, 200, experiment_response.text)
        self.assertEqual(
            experiment_response.json()["latest_closure_log"]["experiment_mode"],
            "closed",
        )

        with Session(engine) as db:
            logs = db.exec(select(ExperimentClosureLog)).all()
            self.assertEqual(len(logs), 2)

    def test_admin_panic_supports_soft_and_hard_modes_idempotently(self) -> None:
        soft_response = self.client.post(
            "/admin/panic",
            json={"soft": True, "reason": "cierre controlado"},
        )
        self.assertEqual(soft_response.status_code, 200, soft_response.text)
        soft_payload = soft_response.json()
        self.assertEqual(soft_payload["experiment_mode"], "closing")
        self.assertFalse(soft_payload["accepting_entries"])
        self.assertTrue(soft_payload["accepting_inflight_sessions"])
        self.assertFalse(soft_payload["idempotent"])
        self.assertTrue(soft_payload["activated_by"])
        self.assertTrue(soft_payload["activated_at"])

        repeat_soft = self.client.post(
            "/admin/panic",
            json={"soft": True, "reason": "cierre controlado"},
        )
        self.assertEqual(repeat_soft.status_code, 200, repeat_soft.text)
        self.assertTrue(repeat_soft.json()["idempotent"])
        self.assertEqual(repeat_soft.json()["experiment_mode"], "closing")

        hard_response = self.client.post(
            "/admin/panic",
            json={"mode": "closed", "reason": "parada inmediata"},
        )
        self.assertEqual(hard_response.status_code, 200, hard_response.text)
        hard_payload = hard_response.json()
        self.assertEqual(hard_payload["experiment_mode"], "closed")
        self.assertFalse(hard_payload["accepting_entries"])
        self.assertFalse(hard_payload["accepting_inflight_sessions"])
        self.assertFalse(hard_payload["idempotent"])

        with Session(engine) as db:
            state = db.get(ExperimentState, "global")
            self.assertEqual(state.experiment_mode, "closed")
            self.assertIsNotNone(state.experiment_mode_changed_at)
            self.assertTrue(state.experiment_mode_changed_by)
            self.assertEqual(state.experiment_mode_reason, "parada inmediata")

    def test_admin_unpanic_restores_live_mode_and_preserves_closure_logs(self) -> None:
        self.access_session(bracelet_code(39))

        panic_response = self.client.post(
            "/admin/panic",
            json={"mode": "closed", "reason": "cierre por error"},
        )
        self.assertEqual(panic_response.status_code, 200, panic_response.text)
        self.assertEqual(panic_response.json()["experiment_mode"], "closed")

        unpanic_response = self.client.post(
            "/admin/unpanic",
            json={"reason": "reapertura tras revision"},
        )
        self.assertEqual(unpanic_response.status_code, 200, unpanic_response.text)
        payload = unpanic_response.json()
        self.assertFalse(payload["idempotent"])
        self.assertEqual(payload["experiment_mode"], "live")
        self.assertTrue(payload["accepting_entries"])
        self.assertTrue(payload["accepting_inflight_sessions"])
        self.assertTrue(payload["closure_logs_kept"])

        reopened = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_code(40),
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "unpanic-reopened",
            },
        )
        self.assertEqual(reopened.status_code, 200, reopened.text)

        with Session(engine) as db:
            state = db.get(ExperimentState, "global")
            self.assertEqual(state.experiment_mode, "live")
            self.assertEqual(state.experiment_mode_reason, "reapertura tras revision")
            logs = db.exec(select(ExperimentClosureLog)).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].experiment_mode, "closed")

    def test_admin_unpanic_is_idempotent_when_already_live(self) -> None:
        response = self.client.post(
            "/admin/unpanic",
            json={"reason": "sin cambios"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["idempotent"])
        self.assertEqual(payload["experiment_mode"], "live")
        self.assertTrue(payload["accepting_entries"])
        self.assertTrue(payload["accepting_inflight_sessions"])

        with Session(engine) as db:
            logs = db.exec(select(ExperimentClosureLog)).all()
            self.assertEqual(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
