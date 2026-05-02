from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "api-sonar-main" / "api-sonar-main"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlmodel import Session  # noqa: E402

from database import engine  # noqa: E402
from experiment import DEMO_ID_OVERRIDES, TREATMENT_KEYS  # noqa: E402
from main import (  # noqa: E402
    demo_override,
    ensure_demo_payment_deck,
    ensure_demo_result_deck,
    ensure_demo_treatment_deck,
    get_active_payment_deck,
    get_active_result_deck,
    get_active_treatment_deck,
    get_or_create_experiment_state,
)
from runtime import redis_ping, set_experiment_status_cache  # noqa: E402


DEFAULT_ENDPOINTS = [
    "/health/live",
    "/health/ready",
    "/health",
    "/v1/config",
]


@dataclass
class EndpointStats:
    path: str
    iterations: int
    status_codes: list[int]
    samples_ms: list[float]

    @property
    def avg_ms(self) -> float:
        return round(mean(self.samples_ms), 2) if self.samples_ms else 0.0

    @property
    def max_ms(self) -> float:
        return round(max(self.samples_ms), 2) if self.samples_ms else 0.0

    @property
    def min_ms(self) -> float:
        return round(min(self.samples_ms), 2) if self.samples_ms else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "iterations": self.iterations,
            "status_codes": self.status_codes,
            "samples_ms": [round(sample, 2) for sample in self.samples_ms],
            "avg_ms": self.avg_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "all_ok": all(status == 200 for status in self.status_codes),
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def warm_database_structures() -> dict[str, Any]:
    result_deck_indices: dict[str, int] = {}
    demo_decks: dict[str, dict[str, Any]] = {}

    with Session(engine) as db:
        state = get_or_create_experiment_state(db)
        treatment_deck = get_active_treatment_deck(db)
        payment_deck = get_active_payment_deck(db)

        for treatment_key in TREATMENT_KEYS:
            result_deck = get_active_result_deck(db, treatment_key=treatment_key)
            result_deck_indices[treatment_key] = int(result_deck.deck_index)

        for bracelet_id in sorted(DEMO_ID_OVERRIDES.keys()):
            override = demo_override(bracelet_id)
            if not override:
                continue
            demo_treatment = ensure_demo_treatment_deck(
                db,
                bracelet_id=bracelet_id,
                treatment_key=str(override["treatment_key"]),
            )
            demo_result = ensure_demo_result_deck(
                db,
                bracelet_id=bracelet_id,
                treatment_key=str(override["treatment_key"]),
                result_value=int(override["result_value"]),
            )
            demo_payment = ensure_demo_payment_deck(
                db,
                bracelet_id=bracelet_id,
                payout_allowed=bool(override["payout_eligible"]),
            )
            demo_decks[bracelet_id] = {
                "treatment_key": str(override["treatment_key"]),
                "result_value": int(override["result_value"]),
                "payout_eligible": bool(override["payout_eligible"]),
                "treatment_deck_index": int(demo_treatment.deck_index),
                "result_deck_index": int(demo_result.deck_index),
                "payment_deck_index": int(demo_payment.deck_index),
            }

        db.commit()

        try:
            set_experiment_status_cache(state.experiment_status, state.pause_reason)
        except Exception:
            pass

        return {
            "started_at": utc_now_iso(),
            "redis_ping_ok": redis_ping(),
            "experiment_status": state.experiment_status,
            "phase": state.current_phase,
            "valid_completed_count": int(state.valid_completed_count),
            "active_treatment_deck_index": int(treatment_deck.deck_index),
            "active_treatment_card_count": int(treatment_deck.card_count),
            "active_payment_deck_index": int(payment_deck.deck_index),
            "active_payment_card_count": int(payment_deck.card_count),
            "active_result_deck_count": len(result_deck_indices),
            "active_result_treatments": sorted(result_deck_indices.keys()),
            "result_deck_indices": result_deck_indices,
            "demo_decks": demo_decks,
            "notes": [
                "Precarga segura: crea mazos y series sin consumir cartas reales.",
                "No precargar un segundo treatment deck activo ni un segundo payment deck activo.",
                "Los result decks se crean por tratamiento para evitar cold path en la primera asignacion de cada brazo.",
            ],
        }


def fetch_json(url: str, timeout_seconds: float) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "sonar-pre-event-warmup/1.0",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
            return int(response.status), json.loads(payload)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"raw": payload}
        return int(exc.code), parsed


def warm_http_endpoints(
    *,
    base_url: str,
    endpoints: list[str],
    iterations: int,
    timeout_seconds: float,
    pause_seconds: float,
) -> dict[str, Any]:
    stats: list[EndpointStats] = []

    for endpoint in endpoints:
        status_codes: list[int] = []
        samples_ms: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            status_code, _payload = fetch_json(
                f"{base_url.rstrip('/')}{endpoint}",
                timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            status_codes.append(status_code)
            samples_ms.append(elapsed_ms)
            if pause_seconds > 0:
                time.sleep(pause_seconds)
        stats.append(
            EndpointStats(
                path=endpoint,
                iterations=iterations,
                status_codes=status_codes,
                samples_ms=samples_ms,
            )
        )

    return {
        "started_at": utc_now_iso(),
        "base_url": base_url,
        "iterations": iterations,
        "timeout_seconds": timeout_seconds,
        "pause_seconds": pause_seconds,
        "endpoints": [item.to_dict() for item in stats],
        "all_ok": all(
            item.to_dict()["all_ok"]
            for item in stats
        ),
    }


def print_summary(report: dict[str, Any]) -> None:
    print("")
    print("=== PRE-EVENT WARMUP SUMMARY ===")
    print(f"timestamp: {report['timestamp']}")
    if report.get("db_warmup"):
        db = report["db_warmup"]
        if "error" in db:
            print(f"db warmup error: {db['error']}")
        else:
            print(
                f"db warmup: treatment_deck={db['active_treatment_deck_index']} "
                f"payment_deck={db['active_payment_deck_index']} "
                f"result_decks={db['active_result_deck_count']} "
                f"redis_ok={db['redis_ping_ok']}"
            )
    if report.get("http_warmup"):
        http = report["http_warmup"]
        if "error" in http:
            print(f"http warmup error: {http['error']}")
        else:
            print(f"http warmup: base_url={http['base_url']} all_ok={http['all_ok']}")
            for endpoint in http["endpoints"]:
                print(
                    f"  {endpoint['path']}: avg={endpoint['avg_ms']}ms "
                    f"max={endpoint['max_ms']}ms status={endpoint['status_codes']}"
                )
    print("")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepara SONAR para el primer pico creando estructuras y calentando endpoints."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL de la API para el warmup HTTP.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Numero de peticiones por endpoint para el test de latencia.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Timeout por peticion HTTP.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.15,
        help="Pausa entre peticiones HTTP.",
    )
    parser.add_argument(
        "--skip-db-warmup",
        action="store_true",
        help="No precargar treatment deck, payment deck, result decks ni demos.",
    )
    parser.add_argument(
        "--skip-http-warmup",
        action="store_true",
        help="No ejecutar GETs de warmup sobre la API.",
    )
    parser.add_argument(
        "--json-out",
        help="Ruta opcional para guardar el informe JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "base_url": args.base_url,
        "db_warmup": None,
        "http_warmup": None,
        "ok": True,
    }

    try:
        if not args.skip_db_warmup:
            report["db_warmup"] = warm_database_structures()
    except Exception as exc:  # noqa: BLE001
        report["db_warmup"] = {"error": str(exc)}
        report["ok"] = False

    try:
        if not args.skip_http_warmup:
            report["http_warmup"] = warm_http_endpoints(
                base_url=args.base_url,
                endpoints=DEFAULT_ENDPOINTS,
                iterations=args.iterations,
                timeout_seconds=args.timeout_seconds,
                pause_seconds=args.pause_seconds,
            )
            if not report["http_warmup"]["all_ok"]:
                report["ok"] = False
    except Exception as exc:  # noqa: BLE001
        report["http_warmup"] = {"error": str(exc)}
        report["ok"] = False

    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print_summary(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
