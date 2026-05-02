from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


@dataclass
class CheckResult:
    name: str
    url: str
    ok: bool
    status_code: int | None
    payload: dict[str, Any] | None
    error: str | None = None


def fetch_json(url: str, *, timeout: float) -> CheckResult:
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            return CheckResult(
                name="",
                url=url,
                ok=True,
                status_code=response.status,
                payload=payload,
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        payload = None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            pass
        return CheckResult(
            name="",
            url=url,
            ok=False,
            status_code=exc.code,
            payload=payload,
            error=body or str(exc),
        )
    except (URLError, TimeoutError, OSError) as exc:
        return CheckResult(
            name="",
            url=url,
            ok=False,
            status_code=None,
            payload=None,
            error=str(exc),
        )


def named_result(name: str, result: CheckResult) -> CheckResult:
    result.name = name
    return result


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica dos replicas de API SONAR y un gateway HA."
    )
    parser.add_argument("--api-a", required=True, help="Base URL de api-a")
    parser.add_argument("--api-b", required=True, help="Base URL de api-b")
    parser.add_argument("--gateway", required=True, help="Base URL del gateway")
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Timeout por request en segundos",
    )
    args = parser.parse_args()

    checks = [
        named_result("api-a live", fetch_json(f"{args.api_a.rstrip('/')}/health/live", timeout=args.timeout)),
        named_result("api-a ready", fetch_json(f"{args.api_a.rstrip('/')}/health/ready", timeout=args.timeout)),
        named_result("api-a health", fetch_json(f"{args.api_a.rstrip('/')}/health", timeout=args.timeout)),
        named_result("api-b live", fetch_json(f"{args.api_b.rstrip('/')}/health/live", timeout=args.timeout)),
        named_result("api-b ready", fetch_json(f"{args.api_b.rstrip('/')}/health/ready", timeout=args.timeout)),
        named_result("api-b health", fetch_json(f"{args.api_b.rstrip('/')}/health", timeout=args.timeout)),
        named_result("gateway ready", fetch_json(f"{args.gateway.rstrip('/')}/health/ready", timeout=args.timeout)),
        named_result("gateway health", fetch_json(f"{args.gateway.rstrip('/')}/health", timeout=args.timeout)),
    ]

    errors: list[str] = []
    for result in checks:
        require(result.ok, f"{result.name} fallo: {result.error or result.status_code}", errors)

    api_a_live = checks[0].payload or {}
    api_a_ready = checks[1].payload or {}
    api_a_health = checks[2].payload or {}
    api_b_live = checks[3].payload or {}
    api_b_ready = checks[4].payload or {}
    api_b_health = checks[5].payload or {}
    gateway_ready = checks[6].payload or {}
    gateway_health = checks[7].payload or {}

    require(api_a_ready.get("ok") is True, "api-a no esta ready", errors)
    require(api_b_ready.get("ok") is True, "api-b no esta ready", errors)
    require(gateway_ready.get("ok") is True, "gateway no esta ready", errors)
    require(
        api_a_live.get("instance_name") != api_b_live.get("instance_name"),
        "api-a y api-b exponen el mismo instance_name",
        errors,
    )

    fingerprint_a = api_a_health.get("config_fingerprint")
    fingerprint_b = api_b_health.get("config_fingerprint")
    require(
        bool(fingerprint_a) and fingerprint_a == fingerprint_b,
        "api-a y api-b no comparten el mismo config_fingerprint",
        errors,
    )

    summary = {
        "ok": not errors,
        "api_a": {
            "instance_name": api_a_live.get("instance_name"),
            "config_fingerprint": fingerprint_a,
            "ready": api_a_ready.get("ok"),
            "experiment_mode": api_a_health.get("experiment_mode"),
        },
        "api_b": {
            "instance_name": api_b_live.get("instance_name"),
            "config_fingerprint": fingerprint_b,
            "ready": api_b_ready.get("ok"),
            "experiment_mode": api_b_health.get("experiment_mode"),
        },
        "gateway": {
            "instance_name": gateway_health.get("instance_name"),
            "config_fingerprint": gateway_health.get("config_fingerprint"),
            "ready": gateway_ready.get("ok"),
        },
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
