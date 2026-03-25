from __future__ import annotations

import base64
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from settings import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "structured_payload", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("sonar")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    if settings.structured_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logging()
_redis_client: Redis | None = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.redis_socket_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
        )
    return _redis_client


def redis_ping() -> bool:
    try:
        return bool(get_redis().ping())
    except RedisError:
        return False


@contextmanager
def distributed_lock(lock_name: str) -> Iterator[None]:
    if not settings.require_redis:
        yield
        return

    lock = get_redis().lock(
        f"sonar:lock:{lock_name}",
        timeout=settings.redis_lock_timeout_seconds,
        blocking_timeout=settings.redis_blocking_timeout_seconds,
    )
    acquired = False
    try:
        acquired = bool(lock.acquire())
        if not acquired:
            raise HTTPException(status_code=409, detail="Recurso temporalmente bloqueado")
        yield
    finally:
        if acquired:
            try:
                lock.release()
            except RedisError:
                logger.warning(
                    "redis_lock_release_failed",
                    extra={"structured_payload": {"lock_name": lock_name}},
                )


def rate_limit(resource_key: str, limit: int, window_seconds: int = 60) -> None:
    if not settings.require_redis:
        return
    redis_client = get_redis()
    counter_key = f"sonar:ratelimit:{resource_key}"
    current_value = redis_client.incr(counter_key)
    if current_value == 1:
        redis_client.expire(counter_key, window_seconds)
    if current_value > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def cache_receipt(endpoint: str, session_id: str, idempotency_key: str, payload: dict[str, Any]) -> None:
    if not settings.require_redis:
        return
    redis_client = get_redis()
    cache_key = f"sonar:receipt:{endpoint}:{session_id}:{idempotency_key}"
    redis_client.setex(
        cache_key,
        settings.idempotency_cache_ttl_seconds,
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
    )


def get_cached_receipt(endpoint: str, session_id: str, idempotency_key: str) -> Optional[dict[str, Any]]:
    if not settings.require_redis:
        return None
    redis_client = get_redis()
    cache_key = f"sonar:receipt:{endpoint}:{session_id}:{idempotency_key}"
    raw_value = redis_client.get(cache_key)
    if not raw_value:
        return None
    return json.loads(raw_value)


def set_experiment_status_cache(status: str, pause_reason: str | None = None) -> None:
    if not settings.require_redis:
        return
    redis_client = get_redis()
    redis_client.hset(
        "sonar:experiment:status",
        mapping={"status": status, "pause_reason": pause_reason or ""},
    )


def get_experiment_status_cache() -> Optional[dict[str, str]]:
    if not settings.require_redis:
        return None
    payload = get_redis().hgetall("sonar:experiment:status")
    return payload or None


def check_admin_credentials(request: Request) -> None:
    if not settings.require_admin_auth:
        return
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Admin credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        ) from exc
    if username != settings.admin_username or password != settings.admin_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def request_log_payload(
    request: Request,
    *,
    status_code: int,
    duration_ms: float,
) -> dict[str, Any]:
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return {
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": client_ip,
    }
