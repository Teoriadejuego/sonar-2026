import csv
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_telemetry_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine
from main import app, bootstrap_demo_data


def bracelet_code(seed: int) -> str:
    return f"TELE{seed:04d}"


class TelemetryPipelineTests(unittest.TestCase):
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
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        return list(reader)

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
                "landing_visible_ms": 4200,
                "info_panels_opened": ["consent_bundle"],
                "info_panel_durations_ms": {"consent_bundle": 1900},
                "consent_checkbox_order": ["age", "participation", "data"],
                "consent_checkbox_timestamps_ms": {
                    "age": 200,
                    "participation": 400,
                    "data": 620,
                },
                "consent_continue_blocked_count": 2,
                "client_installation_id": f"telemetry-{bracelet_id}",
                "referral_code": "seed-referral",
                "referral_source": "whatsapp",
                "referral_medium": "social",
                "referral_campaign": "vip-push",
                "referral_link_id": "invite-a1",
                "referral_path": "/?ref=seed-referral&src=whatsapp",
                "client_context": {
                    "user_agent_raw": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                    "platform": "iPhone",
                    "language_browser": "es-ES",
                    "language_app_selected": "es",
                    "screen_width": 390,
                    "screen_height": 844,
                    "viewport_width": 390,
                    "viewport_height": 760,
                    "device_pixel_ratio": 3,
                    "orientation": "portrait",
                    "touch_capable": True,
                    "hardware_concurrency": 6,
                    "max_touch_points": 5,
                    "color_scheme_preference": "light",
                    "online_status": "online",
                    "connection_type": "4g",
                    "estimated_downlink": 12.4,
                    "estimated_rtt": 45,
                    "timezone_offset_minutes": -60,
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def get_admin_session(self, bracelet_id: str) -> dict:
        response = self.client.get(f"/admin/session/{bracelet_id}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_only_minimal_experimental_telemetry_is_persisted(self) -> None:
        session = self.access_session(bracelet_code(20))
        session_id = session["session_id"]
        base_client_ts = 1_774_191_605_666

        telemetry_response = self.client.post(
            "/v1/telemetry/batch",
            json={
                "session_id": session_id,
                "events": [
                    {
                        "event_type": "experiment",
                        "event_name": "session_start",
                        "client_ts": base_client_ts,
                        "event_sequence_number": 1,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "first_throw",
                        "client_ts": base_client_ts + 200,
                        "event_sequence_number": 2,
                        "value": 4,
                    },
                    {
                        "event_type": "screen_enter",
                        "event_name": "screen_enter",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 250,
                        "event_sequence_number": 3,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "reroll_count",
                        "client_ts": base_client_ts + 400,
                        "event_sequence_number": 4,
                        "value": 2,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "report_value",
                        "client_ts": base_client_ts + 600,
                        "event_sequence_number": 5,
                        "value": 6,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "reaction_time_ms",
                        "client_ts": base_client_ts + 700,
                        "event_sequence_number": 6,
                        "duration_ms": 840,
                    },
                    {
                        "event_type": "error",
                        "event_name": "js_error",
                        "client_ts": base_client_ts + 750,
                        "event_sequence_number": 7,
                        "payload": {"message": "ignored"},
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "session_end",
                        "client_ts": base_client_ts + 900,
                        "event_sequence_number": 8,
                    },
                ],
            },
        )
        self.assertEqual(telemetry_response.status_code, 200, telemetry_response.text)
        self.assertEqual(telemetry_response.json()["accepted_count"], 6)

        resume_response = self.client.get(f"/v1/session/{session_id}/resume")
        self.assertEqual(resume_response.status_code, 200, resume_response.text)
        resumed_session = resume_response.json()["session"]
        self.assertEqual(resumed_session["payload_mode"], "flow")
        self.assertEqual(
            resumed_session["session_metrics"],
            {"max_event_sequence_number": 8},
        )
        self.assertNotIn("consent_record", resumed_session)
        self.assertNotIn("client_context", resumed_session)
        self.assertNotIn("snapshot_record", resumed_session)
        self.assertNotIn("screen_metrics", resumed_session)

        analytics_session = self.get_admin_session(bracelet_code(20))
        self.assertEqual(analytics_session["payload_mode"], "analytics")
        self.assertEqual(
            analytics_session["consent_record"]["checkbox_order"],
            ["age", "participation", "data"],
        )
        self.assertEqual(
            analytics_session["consent_record"]["continue_blocked_count"],
            2,
        )
        self.assertEqual(analytics_session["session_metrics"]["click_count_total"], 0)
        self.assertEqual(analytics_session["session_metrics"]["screen_changes_count"], 0)
        self.assertEqual(analytics_session["session_metrics"]["network_error_count"], 0)
        self.assertEqual(analytics_session["session_metrics"]["telemetry_event_count"], 6)
        self.assertEqual(analytics_session["screen_metrics"], None)
        self.assertEqual(
            analytics_session["client_context"]["browser_family"],
            "Safari",
        )

        telemetry_rows = self.parse_csv(
            self.client.get("/admin/export/telemetry.csv").content
        )
        self.assertEqual(len(telemetry_rows), 6)
        self.assertEqual(
            {row["event_name"] for row in telemetry_rows},
            {
                "session_start",
                "first_throw",
                "reroll_count",
                "report_value",
                "reaction_time_ms",
                "session_end",
            },
        )
        first_throw_row = next(
            row for row in telemetry_rows if row["event_name"] == "first_throw"
        )
        self.assertEqual(first_throw_row["value"], "4")
        reaction_row = next(
            row for row in telemetry_rows if row["event_name"] == "reaction_time_ms"
        )
        self.assertEqual(reaction_row["duration_ms"], "840")
        self.assertTrue(all(not row["screen_name"] for row in telemetry_rows))

        screen_rows = self.parse_csv(
            self.client.get("/admin/export/screen_events.csv").content
        )
        self.assertEqual(screen_rows, [])

        technical_rows = self.parse_csv(
            self.client.get("/admin/export/technical_events.csv").content
        )
        self.assertEqual(technical_rows, [])

        client_rows = self.parse_csv(
            self.client.get("/admin/export/client_contexts.csv").content
        )
        self.assertEqual(client_rows[0]["device_type"], "mobile")
        self.assertEqual(client_rows[0]["connection_type"], "4g")

        session_rows = self.parse_csv(
            self.client.get("/admin/export/sessions.csv").content
        )
        self.assertIn("browser_family", session_rows[0])
        self.assertEqual(session_rows[0]["click_count_total"], "0")
        self.assertEqual(session_rows[0]["screen_changes_count"], "0")

    def test_duplicate_minimal_events_are_deduplicated(self) -> None:
        session = self.access_session(bracelet_code(21))
        session_id = session["session_id"]
        base_client_ts = 1_774_191_700_000

        telemetry_response = self.client.post(
            "/v1/telemetry/batch",
            json={
                "session_id": session_id,
                "events": [
                    {
                        "event_type": "experiment",
                        "event_name": "session_start",
                        "client_ts": base_client_ts,
                        "event_sequence_number": 1,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "session_start",
                        "client_ts": base_client_ts + 5,
                        "event_sequence_number": 2,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "first_throw",
                        "client_ts": base_client_ts + 100,
                        "event_sequence_number": 3,
                        "value": 3,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "first_throw",
                        "client_ts": base_client_ts + 120,
                        "event_sequence_number": 4,
                        "value": 5,
                    },
                ],
            },
        )
        self.assertEqual(telemetry_response.status_code, 200, telemetry_response.text)
        self.assertEqual(telemetry_response.json()["accepted_count"], 2)

        second_response = self.client.post(
            "/v1/telemetry/batch",
            json={
                "session_id": session_id,
                "events": [
                    {
                        "event_type": "experiment",
                        "event_name": "session_start",
                        "client_ts": base_client_ts + 200,
                        "event_sequence_number": 5,
                    },
                    {
                        "event_type": "experiment",
                        "event_name": "first_throw",
                        "client_ts": base_client_ts + 220,
                        "event_sequence_number": 6,
                        "value": 6,
                    },
                ],
            },
        )
        self.assertEqual(second_response.status_code, 200, second_response.text)
        self.assertEqual(second_response.json()["accepted_count"], 0)

        telemetry_rows = self.parse_csv(
            self.client.get("/admin/export/telemetry.csv").content
        )
        session_rows = [row for row in telemetry_rows if row["session_id"] == session_id]
        self.assertEqual(len(session_rows), 2)
        self.assertEqual(
            {row["event_name"] for row in session_rows},
            {"session_start", "first_throw"},
        )


if __name__ == "__main__":
    unittest.main()
