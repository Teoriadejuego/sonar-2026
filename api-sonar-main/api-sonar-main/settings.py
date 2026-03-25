from __future__ import annotations

import os
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
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "changeme")
    auto_bootstrap_demo_data: bool = env_bool("AUTO_BOOTSTRAP_DEMO_DATA", True)
    require_redis: bool = env_bool("REQUIRE_REDIS", True)
    require_admin_auth: bool = env_bool("REQUIRE_ADMIN_AUTH", False)
    structured_logs: bool = env_bool("STRUCTURED_LOGS", True)
    sql_echo: bool = env_bool("SQL_ECHO", False)
    db_pool_size: int = env_int("DB_POOL_SIZE", 10)
    db_max_overflow: int = env_int("DB_MAX_OVERFLOW", 20)
    db_pool_timeout_seconds: int = env_int("DB_POOL_TIMEOUT_SECONDS", 30)
    db_pool_recycle_seconds: int = env_int("DB_POOL_RECYCLE_SECONDS", 1800)
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
    idempotency_cache_ttl_seconds: int = env_int("IDEMPOTENCY_CACHE_TTL_SECONDS", 7200)
    access_rate_limit_per_minute: int = env_int("ACCESS_RATE_LIMIT_PER_MINUTE", 120)
    action_rate_limit_per_minute: int = env_int("ACTION_RATE_LIMIT_PER_MINUTE", 240)
    payment_rate_limit_per_minute: int = env_int("PAYMENT_RATE_LIMIT_PER_MINUTE", 60)
    deployment_context_override: str | None = os.getenv("DEPLOYMENT_CONTEXT")
    site_code_override: str | None = os.getenv("SITE_CODE")
    campaign_code_override: str | None = os.getenv("CAMPAIGN_CODE")
    environment_label_override: str | None = os.getenv("ENVIRONMENT_LABEL")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
