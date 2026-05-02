from __future__ import annotations

import base64
import json
import logging
import re
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import Lock
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
_metrics_lock = Lock()
_inmemory_http_metrics: dict[str, dict[str, Any]] = {}
_inmemory_http_samples: dict[str, deque[float]] = defaultdict(
    lambda: deque(maxlen=settings.observability_latency_sample_size)
)
_inmemory_counter_groups: dict[str, dict[str, int]] = defaultdict(dict)
_SESSION_PATH_RE = re.compile(r"/v1/session/[0-9a-fA-F]{32}")
_HTTP_METRICS_KEY_PREFIX = "sonar:metrics:http:"
_HTTP_METRICS_SAMPLES_SUFFIX = ":samples"
_COUNTER_GROUP_KEY_PREFIX = "sonar:metrics:counters:"
_RUNTIME_RESET_REDIS_PATTERNS = (
    f"{_HTTP_METRICS_KEY_PREFIX}*",
    f"{_COUNTER_GROUP_KEY_PREFIX}*",
    "sonar:ratelimit:*",
    "sonar:receipt:*",
    "sonar:experiment:status",
)


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


def _utc_iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_metric_path(path: str) -> str:
    return _SESSION_PATH_RE.sub("/v1/session/{session_id}", path)


def metric_endpoint_label(method: str, path: str) -> str:
    return f"{method.upper()} {_normalize_metric_path(path)}"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return round(float(ordered[index]), 2)


def reset_observability_metrics() -> None:
    with _metrics_lock:
        _inmemory_http_metrics.clear()
        _inmemory_http_samples.clear()
        _inmemory_counter_groups.clear()


def clear_runtime_state() -> dict[str, int]:
    reset_observability_metrics()
    deleted_redis_keys = 0
    if settings.require_redis:
        redis_client = get_redis()
        keys_to_delete: set[str] = set()
        for pattern in _RUNTIME_RESET_REDIS_PATTERNS:
            keys_to_delete.update(str(key) for key in redis_client.scan_iter(pattern))
        if keys_to_delete:
            deleted_redis_keys = int(redis_client.delete(*sorted(keys_to_delete)) or 0)
    return {"deleted_redis_keys": deleted_redis_keys}


def _record_http_metric_inmemory(
    endpoint: str,
    *,
    status_code: int,
    duration_ms: float,
) -> None:
    with _metrics_lock:
        metric = _inmemory_http_metrics.setdefault(
            endpoint,
            {
                "count": 0,
                "error_count": 0,
                "total_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "last_status_code": None,
                "last_seen_at": None,
            },
        )
        metric["count"] += 1
        if status_code >= 400:
            metric["error_count"] += 1
        metric["total_duration_ms"] += float(duration_ms)
        metric["max_duration_ms"] = max(metric["max_duration_ms"], float(duration_ms))
        metric["last_status_code"] = status_code
        metric["last_seen_at"] = _utc_iso_now()
        _inmemory_http_samples[endpoint].append(float(duration_ms))


def _record_http_metric_redis(
    endpoint: str,
    *,
    status_code: int,
    duration_ms: float,
) -> None:
    redis_client = get_redis()
    metric_key = f"{_HTTP_METRICS_KEY_PREFIX}{endpoint}"
    samples_key = f"{metric_key}{_HTTP_METRICS_SAMPLES_SUFFIX}"
    current_max_raw = redis_client.hget(metric_key, "max_duration_ms")
    current_max = float(current_max_raw) if current_max_raw is not None else 0.0
    pipeline = redis_client.pipeline()
    pipeline.hincrby(metric_key, "count", 1)
    if status_code >= 400:
        pipeline.hincrby(metric_key, "error_count", 1)
    pipeline.hincrbyfloat(metric_key, "total_duration_ms", round(float(duration_ms), 2))
    if float(duration_ms) > current_max:
        pipeline.hset(metric_key, "max_duration_ms", round(float(duration_ms), 2))
    pipeline.hset(
        metric_key,
        mapping={
            "last_status_code": status_code,
            "last_seen_at": _utc_iso_now(),
        },
    )
    pipeline.lpush(samples_key, round(float(duration_ms), 2))
    pipeline.ltrim(samples_key, 0, settings.observability_latency_sample_size - 1)
    pipeline.execute()


def record_http_metric(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    endpoint = metric_endpoint_label(method, path)
    if settings.require_redis:
        try:
            _record_http_metric_redis(
                endpoint,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            return
        except RedisError:
            logger.warning(
                "observability_http_metric_redis_failed",
                extra={
                    "structured_payload": {
                        "endpoint": endpoint,
                        "status_code": status_code,
                    }
                },
            )
    _record_http_metric_inmemory(
        endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
    )


def _increment_counter_group_inmemory(group: str, field: str, delta: int) -> None:
    with _metrics_lock:
        current_value = _inmemory_counter_groups[group].get(field, 0)
        _inmemory_counter_groups[group][field] = current_value + delta


def _increment_counter_group_redis(group: str, field: str, delta: int) -> None:
    get_redis().hincrby(f"{_COUNTER_GROUP_KEY_PREFIX}{group}", field, delta)


def increment_counter_group(group: str, field: str, delta: int = 1) -> None:
    if settings.require_redis:
        try:
            _increment_counter_group_redis(group, field, delta)
            return
        except RedisError:
            logger.warning(
                "observability_counter_redis_failed",
                extra={
                    "structured_payload": {
                        "group": group,
                        "field": field,
                        "delta": delta,
                    }
                },
            )
    _increment_counter_group_inmemory(group, field, delta)


def record_session_started(initial_screen: str = "instructions") -> None:
    increment_counter_group("sessions", "started_total", 1)
    increment_counter_group("screens_entered", initial_screen, 1)


def record_session_completed() -> None:
    increment_counter_group("sessions", "completed_total", 1)


def record_screen_transition(
    from_screen: str | None,
    to_screen: str | None,
) -> None:
    if from_screen and from_screen != to_screen:
        increment_counter_group("screens_exited", from_screen, 1)
    if to_screen and from_screen != to_screen:
        increment_counter_group("screens_entered", to_screen, 1)


def get_counter_group_snapshot(group: str) -> dict[str, int]:
    if settings.require_redis:
        try:
            raw = get_redis().hgetall(f"{_COUNTER_GROUP_KEY_PREFIX}{group}")
            return {
                key: int(value)
                for key, value in raw.items()
            }
        except RedisError:
            logger.warning(
                "observability_counter_snapshot_redis_failed",
                extra={"structured_payload": {"group": group}},
            )
    with _metrics_lock:
        return dict(_inmemory_counter_groups.get(group, {}))


def get_http_metrics_snapshot() -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    if settings.require_redis:
        try:
            redis_client = get_redis()
            for metric_key in redis_client.scan_iter(f"{_HTTP_METRICS_KEY_PREFIX}*"):
                if metric_key.endswith(_HTTP_METRICS_SAMPLES_SUFFIX):
                    continue
                endpoint = metric_key.replace(_HTTP_METRICS_KEY_PREFIX, "", 1)
                raw_metric = redis_client.hgetall(metric_key)
                samples_raw = redis_client.lrange(
                    f"{metric_key}{_HTTP_METRICS_SAMPLES_SUFFIX}",
                    0,
                    settings.observability_latency_sample_size - 1,
                )
                count = int(raw_metric.get("count", 0))
                error_count = int(raw_metric.get("error_count", 0))
                total_duration_ms = float(raw_metric.get("total_duration_ms", 0.0))
                max_duration_ms = float(raw_metric.get("max_duration_ms", 0.0))
                samples = [float(item) for item in samples_raw]
                snapshots[endpoint] = {
                    "count": count,
                    "error_count": error_count,
                    "error_rate": round(error_count / count, 4) if count else 0.0,
                    "avg_duration_ms": round(total_duration_ms / count, 2) if count else 0.0,
                    "p95_duration_ms": _percentile(samples, 0.95),
                    "max_duration_ms": round(max_duration_ms, 2),
                    "last_status_code": int(raw_metric["last_status_code"])
                    if raw_metric.get("last_status_code")
                    else None,
                    "last_seen_at": raw_metric.get("last_seen_at"),
                }
            return dict(sorted(snapshots.items()))
        except RedisError:
            logger.warning("observability_http_snapshot_redis_failed")

    with _metrics_lock:
        for endpoint, raw_metric in _inmemory_http_metrics.items():
            count = int(raw_metric["count"])
            error_count = int(raw_metric["error_count"])
            total_duration_ms = float(raw_metric["total_duration_ms"])
            max_duration_ms = float(raw_metric["max_duration_ms"])
            samples = list(_inmemory_http_samples.get(endpoint, []))
            snapshots[endpoint] = {
                "count": count,
                "error_count": error_count,
                "error_rate": round(error_count / count, 4) if count else 0.0,
                "avg_duration_ms": round(total_duration_ms / count, 2) if count else 0.0,
                "p95_duration_ms": _percentile(samples, 0.95),
                "max_duration_ms": round(max_duration_ms, 2),
                "last_status_code": raw_metric.get("last_status_code"),
                "last_seen_at": raw_metric.get("last_seen_at"),
            }
    return dict(sorted(snapshots.items()))


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


def set_experiment_status_cache(
    status: str,
    pause_reason: str | None = None,
    mode: str = "live",
) -> None:
    if not settings.require_redis:
        return
    redis_client = get_redis()
    redis_client.hset(
        "sonar:experiment:status",
        mapping={
            "status": status,
            "pause_reason": pause_reason or "",
            "mode": mode,
        },
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


def get_admin_actor(request: Request) -> str:
    if not settings.require_admin_auth:
        return settings.admin_username or "local_admin"
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Basic "):
        return settings.admin_username or "admin"
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        username, _password = decoded.split(":", 1)
        return username or settings.admin_username or "admin"
    except Exception:  # noqa: BLE001
        return settings.admin_username or "admin"


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
