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

    def test_high_resolution_telemetry_is_persisted_and_exported(self) -> None:
        session = self.access_session("10000020")
        session_id = session["session_id"]
        base_client_ts = 1_774_191_605_666

        telemetry_response = self.client.post(
            "/v1/telemetry/batch",
            json={
                "session_id": session_id,
                "events": [
                    {
                        "event_type": "screen_enter",
                        "event_name": "screen_enter",
                        "screen_name": "landing",
                        "client_ts": base_client_ts,
                        "event_sequence_number": 1,
                        "timezone_offset_minutes": -60,
                        "app_language": "es",
                        "browser_language": "es-ES",
                        "spell_id": "landing-1",
                        "payload": {
                            "entry_origin": "navigate",
                            "screen_name": "landing",
                            "entered_via_resume": False,
                        },
                    },
                    {
                        "event_type": "click",
                        "event_name": "start_session",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 220,
                        "event_sequence_number": 2,
                        "spell_id": "landing-1",
                        "interaction_target": "start_session",
                        "interaction_role": "button",
                        "cta_kind": "primary",
                    },
                    {
                        "event_type": "network",
                        "event_name": "api_success",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 280,
                        "event_sequence_number": 3,
                        "endpoint_name": "/v1/session/access",
                        "request_method": "POST",
                        "status_code": 200,
                        "latency_ms": 180,
                    },
                    {
                        "event_type": "lifecycle",
                        "event_name": "blur",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 320,
                        "event_sequence_number": 4,
                        "spell_id": "landing-1",
                    },
                    {
                        "event_type": "screen_exit",
                        "event_name": "screen_exit",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 1_100,
                        "event_sequence_number": 5,
                        "spell_id": "landing-1",
                        "duration_ms": 1_100,
                        "payload": {
                            "screen_name": "landing",
                            "visible_ms": 860,
                            "hidden_ms": 120,
                            "blur_ms": 120,
                            "focus_change_count": 1,
                            "visibility_change_count": 1,
                            "click_count": 1,
                            "primary_click_count": 1,
                            "secondary_click_count": 0,
                            "first_click_ms": 220,
                            "primary_cta_ms": 220,
                            "secondary_cta_ms": None,
                            "first_click_target": "start_session",
                            "click_targets": ["start_session"],
                            "language_changed_during_spell": False,
                            "language_at_entry": "es",
                            "language_at_exit": "es",
                        },
                    },
                    {
                        "event_type": "error",
                        "event_name": "js_error",
                        "screen_name": "landing",
                        "client_ts": base_client_ts + 1_150,
                        "event_sequence_number": 6,
                        "error_name": "TypeError",
                        "payload": {"message": "Synthetic render failure"},
                    },
                ],
            },
        )
        self.assertEqual(telemetry_response.status_code, 200, telemetry_response.text)
        self.assertEqual(telemetry_response.json()["accepted_count"], 6)

        resume_response = self.client.get(f"/v1/session/{session_id}/resume")
        self.assertEqual(resume_response.status_code, 200, resume_response.text)
        resumed_session = resume_response.json()["session"]
        self.assertEqual(
            resumed_session["consent_record"]["checkbox_order"],
            ["age", "participation", "data"],
        )
        self.assertEqual(
            resumed_session["consent_record"]["continue_blocked_count"],
            2,
        )
        self.assertEqual(resumed_session["session_metrics"]["click_count_total"], 1)
        self.assertEqual(resumed_session["session_metrics"]["telemetry_event_count"], 6)
        self.assertEqual(
            resumed_session["client_context"]["browser_family"],
            "Safari",
        )

        telemetry_rows = self.parse_csv(
            self.client.get("/admin/export/telemetry.csv").content
        )
        self.assertIn("event_sequence_number", telemetry_rows[0])
        self.assertIn("client_clock_skew_estimate_ms", telemetry_rows[0])
        self.assertTrue(any(row["spell_id"] == "landing-1" for row in telemetry_rows))
        self.assertTrue(any(row["client_ts"] == str(base_client_ts) for row in telemetry_rows))

        screen_rows = self.parse_csv(
            self.client.get("/admin/export/screen_events.csv").content
        )
        self.assertEqual(len(screen_rows), 1)
        self.assertEqual(screen_rows[0]["spell_id"], "landing-1")
        self.assertEqual(screen_rows[0]["visible_ms"], "860")
        self.assertEqual(screen_rows[0]["primary_click_count"], "1")

        technical_rows = self.parse_csv(
            self.client.get("/admin/export/technical_events.csv").content
        )
        self.assertTrue(any(row["event_name"] == "js_error" for row in technical_rows))
        self.assertTrue(any(row["endpoint_name"] == "/v1/session/access" for row in technical_rows))

        client_rows = self.parse_csv(
            self.client.get("/admin/export/client_contexts.csv").content
        )
        self.assertEqual(client_rows[0]["device_type"], "mobile")
        self.assertEqual(client_rows[0]["connection_type"], "4g")

        session_rows = self.parse_csv(
            self.client.get("/admin/export/sessions.csv").content
        )
        self.assertIn("browser_family", session_rows[0])
        self.assertIn("landing_to_start_ms", session_rows[0])
        self.assertIn("click_count_total", session_rows[0])
        self.assertIn("language_change_count", session_rows[0])


if __name__ == "__main__":
    unittest.main()
