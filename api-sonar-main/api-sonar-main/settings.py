from __future__ import annotations

import os
import socket
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://sonar:sonar@localhost:5432/sonar",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cors_origins_raw: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )
    cors_origin_regex: str = os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "changeme")
    admin_reset_enabled: bool = env_bool("ADMIN_RESET_ENABLED", True)
    admin_reset_passphrase: str = os.getenv(
        "ADMIN_RESET_PASSPHRASE",
        "antonioalfonsoautoriza",
    )
    auto_bootstrap_demo_data: bool = env_bool("AUTO_BOOTSTRAP_DEMO_DATA", True)
    require_redis: bool = env_bool("REQUIRE_REDIS", True)
    require_admin_auth: bool = env_bool("REQUIRE_ADMIN_AUTH", False)
    structured_logs: bool = env_bool("STRUCTURED_LOGS", True)
    sql_echo: bool = env_bool("SQL_ECHO", False)
    reset_db: bool = env_bool("RESET_DB", False)
    db_pool_size: int = env_int("DB_POOL_SIZE", 10)
    db_max_overflow: int = env_int("DB_MAX_OVERFLOW", 20)
    db_connect_timeout_seconds: int = env_int("DB_CONNECT_TIMEOUT_SECONDS", 5)
    db_pool_timeout_seconds: int = env_int("DB_POOL_TIMEOUT_SECONDS", 30)
    db_pool_recycle_seconds: int = env_int("DB_POOL_RECYCLE_SECONDS", 1800)
    db_sqlite_busy_timeout_seconds: float = env_float(
        "DB_SQLITE_BUSY_TIMEOUT_SECONDS", 30.0
    )
    migration_lock_key: int = env_int("MIGRATION_LOCK_KEY", 2026050201)
    migration_lock_timeout_seconds: int = env_int(
        "MIGRATION_LOCK_TIMEOUT_SECONDS", 300
    )
    migration_lock_retry_interval_seconds: float = env_float(
        "MIGRATION_LOCK_RETRY_INTERVAL_SECONDS", 1.0
    )
    startup_dependency_timeout_seconds: int = env_int(
        "STARTUP_DEPENDENCY_TIMEOUT_SECONDS", 90
    )
    startup_dependency_retry_interval_seconds: float = env_float(
        "STARTUP_DEPENDENCY_RETRY_INTERVAL_SECONDS", 2.0
    )
    redis_lock_timeout_seconds: int = env_int("REDIS_LOCK_TIMEOUT_SECONDS", 15)
    redis_blocking_timeout_seconds: int = env_int("REDIS_BLOCKING_TIMEOUT_SECONDS", 5)
    redis_socket_connect_timeout_seconds: float = env_float(
        "REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", 2.0
    )
    redis_socket_timeout_seconds: float = env_float(
        "REDIS_SOCKET_TIMEOUT_SECONDS", 2.0
    )
    observability_active_window_seconds: int = env_int(
        "OBSERVABILITY_ACTIVE_WINDOW_SECONDS", 300
    )
    observability_recent_window_seconds: int = env_int(
        "OBSERVABILITY_RECENT_WINDOW_SECONDS", 900
    )
    observability_stalled_screen_seconds: int = env_int(
        "OBSERVABILITY_STALLED_SCREEN_SECONDS", 300
    )
    observability_latency_sample_size: int = env_int(
        "OBSERVABILITY_LATENCY_SAMPLE_SIZE", 200
    )
    data_quality_fast_throw_ms: int = env_int(
        "DATA_QUALITY_FAST_THROW_MS", 600
    )
    alert_quality_min_completed: int = env_int(
        "ALERT_QUALITY_MIN_COMPLETED", 5
    )
    alert_fast_throw_rate_threshold: float = env_float(
        "ALERT_FAST_THROW_RATE_THRESHOLD", 0.35
    )
    alert_fast_report_rate_threshold: float = env_float(
        "ALERT_FAST_REPORT_RATE_THRESHOLD", 0.35
    )
    alert_report_top_share_threshold: float = env_float(
        "ALERT_REPORT_TOP_SHARE_THRESHOLD", 0.75
    )
    alert_report_six_gap_threshold: float = env_float(
        "ALERT_REPORT_SIX_GAP_THRESHOLD", 0.25
    )
    alert_device_reuse_count_threshold: int = env_int(
        "ALERT_DEVICE_REUSE_COUNT_THRESHOLD", 3
    )
    alert_endpoint_error_rate_threshold: float = env_float(
        "ALERT_ENDPOINT_ERROR_RATE_THRESHOLD", 0.2
    )
    alert_endpoint_error_count_threshold: int = env_int(
        "ALERT_ENDPOINT_ERROR_COUNT_THRESHOLD", 5
    )
    alert_completion_rate_threshold: float = env_float(
        "ALERT_COMPLETION_RATE_THRESHOLD", 0.2
    )
    alert_completion_min_started: int = env_int(
        "ALERT_COMPLETION_MIN_STARTED", 10
    )
    frontend_public_base_url: str = os.getenv(
        "FRONTEND_PUBLIC_BASE_URL",
        "https://dice.sonar2026.es",
    )
    gateway_public_base_url: str = os.getenv(
        "GATEWAY_PUBLIC_BASE_URL",
        "https://play.sonar-experiment.com",
    )
    gateway_failover_enabled: bool = env_bool("GATEWAY_FAILOVER_ENABLED", True)
    gateway_primary_healthcheck_url: str | None = os.getenv(
        "GATEWAY_PRIMARY_HEALTHCHECK_URL"
    )
    gateway_backup_healthcheck_url: str | None = os.getenv(
        "GATEWAY_BACKUP_HEALTHCHECK_URL"
    )
    gateway_healthcheck_interval_seconds: float = env_float(
        "GATEWAY_HEALTHCHECK_INTERVAL_SECONDS", 5.0
    )
    gateway_healthcheck_timeout_seconds: float = env_float(
        "GATEWAY_HEALTHCHECK_TIMEOUT_SECONDS", 2.5
    )
    gateway_healthcheck_failure_threshold: int = env_int(
        "GATEWAY_HEALTHCHECK_FAILURE_THRESHOLD", 3
    )
    gateway_auto_failback_enabled: bool = env_bool(
        "GATEWAY_AUTO_FAILBACK_ENABLED", False
    )
    gateway_healthcheck_success_threshold: int = env_int(
        "GATEWAY_HEALTHCHECK_SUCCESS_THRESHOLD", 2
    )
    idempotency_cache_ttl_seconds: int = env_int("IDEMPOTENCY_CACHE_TTL_SECONDS", 7200)
    access_rate_limit_per_minute: int = env_int("ACCESS_RATE_LIMIT_PER_MINUTE", 120)
    action_rate_limit_per_minute: int = env_int("ACTION_RATE_LIMIT_PER_MINUTE", 240)
    payment_rate_limit_per_minute: int = env_int("PAYMENT_RATE_LIMIT_PER_MINUTE", 60)
    deployment_context_override: str | None = os.getenv("DEPLOYMENT_CONTEXT")
    site_code_override: str | None = os.getenv("SITE_CODE")
    campaign_code_override: str | None = os.getenv("CAMPAIGN_CODE")
    environment_label_override: str | None = os.getenv("ENVIRONMENT_LABEL")
    instance_name: str = os.getenv("INSTANCE_NAME") or socket.gethostname()

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
