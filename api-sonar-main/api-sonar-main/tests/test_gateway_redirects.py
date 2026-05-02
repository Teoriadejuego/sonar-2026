import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_gateway_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["GATEWAY_PUBLIC_BASE_URL"] = "https://play.sonar-experiment.com"
os.environ["GATEWAY_FAILOVER_ENABLED"] = "false"
os.environ["GATEWAY_PRIMARY_HEALTHCHECK_URL"] = "https://primary.sonar.test/health"
os.environ["GATEWAY_BACKUP_HEALTHCHECK_URL"] = "https://backup.sonar.test/health"
os.environ["GATEWAY_HEALTHCHECK_FAILURE_THRESHOLD"] = "3"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

import main as main_module
from database import engine
from main import app, bootstrap_demo_data
from models import GatewayAccessLog


class GatewayRedirectTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        self.original_gateway_settings = {
            "gateway_failover_enabled": main_module.settings.gateway_failover_enabled,
            "gateway_primary_healthcheck_url": (
                main_module.settings.gateway_primary_healthcheck_url
            ),
            "gateway_backup_healthcheck_url": (
                main_module.settings.gateway_backup_healthcheck_url
            ),
            "gateway_healthcheck_failure_threshold": (
                main_module.settings.gateway_healthcheck_failure_threshold
            ),
            "gateway_auto_failback_enabled": (
                main_module.settings.gateway_auto_failback_enabled
            ),
            "gateway_healthcheck_success_threshold": (
                main_module.settings.gateway_healthcheck_success_threshold
            ),
        }
        object.__setattr__(main_module.settings, "gateway_failover_enabled", False)
        object.__setattr__(
            main_module.settings,
            "gateway_primary_healthcheck_url",
            "https://primary.sonar.test/health",
        )
        object.__setattr__(
            main_module.settings,
            "gateway_backup_healthcheck_url",
            "https://backup.sonar.test/health",
        )
        object.__setattr__(
            main_module.settings, "gateway_healthcheck_failure_threshold", 3
        )
        object.__setattr__(main_module.settings, "gateway_auto_failback_enabled", False)
        object.__setattr__(
            main_module.settings, "gateway_healthcheck_success_threshold", 2
        )
        with main_module._gateway_failover_state_lock:
            main_module._gateway_failover_state["monitor_enabled"] = False
            main_module._gateway_failover_state["monitor_running"] = False
            main_module._gateway_failover_state["last_checked_at"] = None
            main_module._gateway_failover_state["last_event"] = None
            main_module._gateway_failover_state["primary"].update(
                {
                    "url": "https://primary.sonar.test/health",
                    "healthy": None,
                    "consecutive_failures": 0,
                    "consecutive_successes": 0,
                    "last_status_code": None,
                    "last_latency_ms": None,
                    "last_error": None,
                    "last_checked_at": None,
                }
            )
            main_module._gateway_failover_state["backup"].update(
                {
                    "url": "https://backup.sonar.test/health",
                    "healthy": None,
                    "consecutive_failures": 0,
                    "consecutive_successes": 0,
                    "last_status_code": None,
                    "last_latency_ms": None,
                    "last_error": None,
                    "last_checked_at": None,
                }
            )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for setting_name, value in self.original_gateway_settings.items():
            object.__setattr__(main_module.settings, setting_name, value)

    def create_route(
        self,
        *,
        qr_code: str = "poster-entrada-a",
        active_target: str = "primary",
        enabled: bool = True,
        backup_target_url: str | None = "https://dice-backup.sonar2026.es/",
    ) -> dict:
        response = self.client.post(
            "/admin/gateway/routes",
            json={
                "qr_code": qr_code,
                "primary_target_url": "https://dice.sonar2026.es/",
                "backup_target_url": backup_target_url,
                "active_target": active_target,
                "enabled": enabled,
                "notes": "QR festival acceso principal",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["route"]

    def gateway_logs(self) -> list[GatewayAccessLog]:
        with Session(engine) as db:
            return db.exec(
                select(GatewayAccessLog).order_by(GatewayAccessLog.id)
            ).all()

    def fake_health_response(self, status_code: int) -> Mock:
        response = Mock()
        response.status_code = status_code
        return response

    def test_play_path_redirects_to_primary_and_preserves_tracking(self) -> None:
        route = self.create_route()
        self.assertEqual(
            route["public_url"],
            "https://play.sonar-experiment.com/play/poster-entrada-a",
        )

        response = self.client.get(
            "/play/poster-entrada-a?utm_campaign=festival&src=qr",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 307, response.text)
        location = response.headers["location"]
        parsed = urlsplit(location)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.netloc, "dice.sonar2026.es")
        self.assertEqual(query["qr"], ["poster-entrada-a"])
        self.assertEqual(query["utm_campaign"], ["festival"])
        self.assertEqual(query["src"], ["qr"])

        logs = self.gateway_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, "redirected")
        self.assertEqual(logs[0].selected_target, "primary")
        self.assertEqual(logs[0].qr_code, "poster-entrada-a")

    def test_switch_to_backup_changes_redirect_without_redeploy(self) -> None:
        self.create_route()

        switch = self.client.post(
            "/admin/gateway/routes/poster-entrada-a/switch",
            json={"active_target": "backup"},
        )
        self.assertEqual(switch.status_code, 200, switch.text)
        self.assertEqual(switch.json()["route"]["active_target"], "backup")

        response = self.client.get(
            "/play/poster-entrada-a",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 307, response.text)
        self.assertEqual(
            urlsplit(response.headers["location"]).netloc,
            "dice-backup.sonar2026.es",
        )

        logs = self.gateway_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].selected_target, "backup")

    def test_global_gateway_mode_switch_moves_all_routes_without_restart(self) -> None:
        self.create_route(qr_code="zona-a-1")
        self.create_route(qr_code="zona-b-1")

        before = self.client.get("/admin/gateway/mode")
        self.assertEqual(before.status_code, 200, before.text)
        self.assertEqual(before.json()["mode"], "primary")

        switched = self.client.post(
            "/admin/gateway/mode",
            json={"mode": "backup"},
        )
        self.assertEqual(switched.status_code, 200, switched.text)
        self.assertEqual(switched.json()["mode"], "backup")
        self.assertEqual(switched.json()["changed_routes"], 2)

        route_a = self.client.get("/play/zona-a-1", follow_redirects=False)
        route_b = self.client.get("/play/zona-b-1", follow_redirects=False)
        self.assertEqual(route_a.status_code, 307, route_a.text)
        self.assertEqual(route_b.status_code, 307, route_b.text)
        self.assertEqual(
            urlsplit(route_a.headers["location"]).netloc,
            "dice-backup.sonar2026.es",
        )
        self.assertEqual(
            urlsplit(route_b.headers["location"]).netloc,
            "dice-backup.sonar2026.es",
        )

    def test_global_backup_mode_rejects_routes_without_backup(self) -> None:
        self.create_route(qr_code="zona-ok")
        self.create_route(
            qr_code="zona-sin-backup",
            backup_target_url=None,
        )

        switched = self.client.post(
            "/admin/gateway/mode",
            json={"mode": "backup"},
        )
        self.assertEqual(switched.status_code, 400, switched.text)
        self.assertIn("zona-sin-backup", switched.text)

    def test_automatic_failover_switches_to_backup_after_three_failures(self) -> None:
        self.create_route(qr_code="zona-a-1")

        with patch(
            "main.httpx.get",
            side_effect=[
                RuntimeError("primary down"),
                self.fake_health_response(200),
                RuntimeError("primary down"),
                self.fake_health_response(200),
                RuntimeError("primary down"),
                self.fake_health_response(200),
            ],
        ):
            first = self.client.post("/admin/gateway/failover/check-now")
            second = self.client.post("/admin/gateway/failover/check-now")
            third = self.client.post("/admin/gateway/failover/check-now")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(third.status_code, 200, third.text)
        self.assertEqual(third.json()["gateway_mode"]["mode"], "backup")
        self.assertEqual(third.json()["last_event"]["type"], "auto_failover")

        redirected = self.client.get("/play/zona-a-1", follow_redirects=False)
        self.assertEqual(redirected.status_code, 307, redirected.text)
        self.assertEqual(
            urlsplit(redirected.headers["location"]).netloc,
            "dice-backup.sonar2026.es",
        )

    def test_automatic_failover_does_not_switch_before_threshold(self) -> None:
        self.create_route(qr_code="zona-a-1")

        with patch(
            "main.httpx.get",
            side_effect=[
                RuntimeError("primary down"),
                self.fake_health_response(200),
                RuntimeError("primary down"),
                self.fake_health_response(200),
            ],
        ):
            first = self.client.post("/admin/gateway/failover/check-now")
            second = self.client.post("/admin/gateway/failover/check-now")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["gateway_mode"]["mode"], "primary")
        self.assertIsNone(second.json()["last_event"])

    def test_query_param_variant_redirects_and_auto_injects_qr_source(self) -> None:
        self.create_route(qr_code="cartel-vip")

        response = self.client.get(
            "/play?qr=cartel-vip&utm_medium=poster",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 307, response.text)
        parsed = urlsplit(response.headers["location"])
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.netloc, "dice.sonar2026.es")
        self.assertEqual(query["qr"], ["cartel-vip"])
        self.assertEqual(query["utm_medium"], ["poster"])
        self.assertEqual(query["src"], ["qr_gateway"])
        self.assertIn("link_id", query)

    def test_missing_and_disabled_routes_are_logged(self) -> None:
        missing = self.client.get("/play?qr=inexistente", follow_redirects=False)
        self.assertEqual(missing.status_code, 404, missing.text)

        self.create_route(qr_code="pausado", enabled=False)
        disabled = self.client.get("/play/pausado", follow_redirects=False)
        self.assertEqual(disabled.status_code, 503, disabled.text)

        logs = self.gateway_logs()
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].status, "missing_route")
        self.assertEqual(logs[1].status, "disabled_route")

    def test_qr_tracking_links_scan_to_session_and_summarizes_by_zone(self) -> None:
        self.create_route(qr_code="ZONE_A_01")

        redirect = self.client.get("/play?qr_id=ZONE_A_01", follow_redirects=False)
        self.assertEqual(redirect.status_code, 307, redirect.text)
        parsed = urlsplit(redirect.headers["location"])
        query = parse_qs(parsed.query)
        self.assertEqual(query["qr_id"], ["ZONE_A_01"])
        visit_id = query["link_id"][0]

        access = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": "GATE1001",
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": "gateway-install-1",
                "referral_source": "qr_gateway",
                "referral_medium": "offline_qr",
                "referral_link_id": visit_id,
                "qr_entry_code": "ZONE_A_01",
                "referral_path": "/?qr_id=ZONE_A_01",
            },
        )
        self.assertEqual(access.status_code, 200, access.text)
        session_id = access.json()["session"]["session_id"]

        logs_response = self.client.get("/admin/gateway/logs")
        self.assertEqual(logs_response.status_code, 200, logs_response.text)
        logs_payload = logs_response.json()["logs"]
        self.assertEqual(logs_payload[0]["session_id"], session_id)
        self.assertEqual(logs_payload[0]["zone_code"], "zone_a")
        self.assertEqual(logs_payload[0]["traffic_source"], "direct_qr")
        self.assertEqual(logs_payload[0]["gateway_visit_id"], visit_id)
        self.assertTrue(logs_payload[0]["request_user_agent"])

        summary = self.client.get("/admin/gateway/summary")
        self.assertEqual(summary.status_code, 200, summary.text)
        payload = summary.json()
        self.assertEqual(payload["summary"]["scans_total"], 1)
        self.assertEqual(payload["summary"]["sessions_started"], 1)
        self.assertEqual(payload["by_qr"][0]["qr_code"], "zone_a_01")
        self.assertEqual(payload["by_qr"][0]["zone_code"], "zone_a")
        self.assertEqual(payload["by_qr"][0]["scans_total"], 1)
        self.assertEqual(payload["by_qr"][0]["sessions_started"], 1)
        self.assertEqual(payload["by_qr"][0]["conversion_rate"], 1.0)
        self.assertEqual(payload["by_zone"][0]["zone_code"], "zone_a")
        self.assertEqual(payload["by_zone"][0]["scans_total"], 1)


if __name__ == "__main__":
    unittest.main()
