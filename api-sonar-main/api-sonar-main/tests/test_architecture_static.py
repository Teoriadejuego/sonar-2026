from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "api-sonar-main" / "api-sonar-main"
FRONTEND = ROOT / "sorteo-sonar-main"


class ArchitectureStaticTests(unittest.TestCase):
    def test_required_docs_exist(self) -> None:
        required = [
            ROOT / "ARCHITECTURE.md",
            ROOT / "ENVIRONMENTS.md",
            ROOT / "LOCAL_TO_PRODUCTION.md",
            ROOT / "CONCURRENCY_GUARANTEES.md",
            ROOT / "CLASSROOM_LOAD_TEST.md",
            ROOT / "DEPLOYMENT_CHECKLIST.md",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"Missing {path.name}")

    def test_compose_uses_postgres_and_redis(self) -> None:
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("postgres:", compose_text)
        self.assertIn("redis:", compose_text)
        self.assertIn("DATABASE_URL", compose_text)
        self.assertIn("REDIS_URL", compose_text)
        self.assertIn("health/ready", compose_text)

    def test_ha_compose_and_gateway_exist(self) -> None:
        ha_compose = ROOT / "docker-compose.ha.yml"
        gateway_conf = ROOT / "ops" / "nginx" / "api-ha.conf"
        preflight_script = ROOT / "ops" / "ha_preflight_check.py"
        self.assertTrue(ha_compose.exists())
        self.assertTrue(gateway_conf.exists())
        self.assertTrue(preflight_script.exists())
        ha_text = ha_compose.read_text(encoding="utf-8")
        gateway_text = gateway_conf.read_text(encoding="utf-8")
        self.assertIn("api-a:", ha_text)
        self.assertIn("api-b:", ha_text)
        self.assertIn("api-gateway:", ha_text)
        self.assertIn("INSTANCE_NAME: api-a", ha_text)
        self.assertIn("INSTANCE_NAME: api-b", ha_text)
        self.assertIn("/health/ready", ha_text)
        self.assertIn("proxy_next_upstream", gateway_text)
        self.assertIn("X-Upstream-Addr", gateway_text)
        self.assertIn("server api-a:8000", gateway_text)
        self.assertIn("server api-b:8000", gateway_text)

    def test_backend_defaults_to_postgres(self) -> None:
        settings_text = (BACKEND / "settings.py").read_text(encoding="utf-8")
        self.assertIn("postgresql+psycopg2://", settings_text)
        self.assertIn('redis://localhost:6379/0', settings_text)
        self.assertNotIn("ADMIN_AUTH_ENABLED", settings_text)
        self.assertIn("migration_lock_key", settings_text)
        self.assertIn("instance_name", settings_text)

    def test_backend_container_runs_migrations_before_start(self) -> None:
        dockerfile_text = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python migrate.py && uvicorn main:app", dockerfile_text)
        self.assertIn("/health/ready", dockerfile_text)

    def test_frontend_container_uses_runtime_api_url(self) -> None:
        dockerfile_text = (FRONTEND / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("VITE_API_URL", dockerfile_text)
        self.assertIn("HEALTHCHECK", dockerfile_text)

    def test_load_test_script_exists(self) -> None:
        script_path = ROOT / "ops" / "classroom_load_test.py"
        self.assertTrue(script_path.exists())
        script_text = script_path.read_text(encoding="utf-8")
        self.assertIn("/v1/session/access", script_text)
        self.assertIn("/v1/session/{session_id}/roll", script_text)
        self.assertIn("/admin/export/sessions.csv", script_text)


if __name__ == "__main__":
    unittest.main()
