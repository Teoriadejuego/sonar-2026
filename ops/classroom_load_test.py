from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


DEFAULT_TIMEOUT = 30.0
LOAD_TEST_BRACELET_PREFIX = "LOAD"


@dataclass
class FlowResult:
    bracelet_id: str
    session_id: str | None
    series_id: str | None
    treatment_key: str | None
    treatment_deck_index: int | None
    position_index: int | None
    final_state: str | None
    payment_selected: bool
    payout_amount_cents: int
    success: bool
    error: str | None
    total_ms: int
    access_ms: int | None
    roll_ms: int | None
    prepare_ms: int | None
    submit_ms: int | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stress test de aula para SONAR usando el backend real.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=60)
    parser.add_argument("--bracelet-start", type=int, default=1)
    parser.add_argument("--language", default="es")
    parser.add_argument("--admin-username", default="")
    parser.add_argument("--admin-password", default="")
    parser.add_argument(
        "--output-dir",
        default=str(
            Path(__file__).resolve().parents[1]
            / "outputs"
            / "classroom_load_test"
        ),
    )
    return parser.parse_args()


def idempotency_key(prefix: str, bracelet_id: str) -> str:
    return f"{prefix}-{bracelet_id}-{uuid4().hex}"


def bracelet_code(seed: int) -> str:
    return f"{LOAD_TEST_BRACELET_PREFIX}{seed % 10000:04d}"


def basic_auth_tuple(args: argparse.Namespace) -> tuple[str, str] | None:
    if args.admin_username and args.admin_password:
        return (args.admin_username, args.admin_password)
    return None


async def timed_post(
    client: httpx.AsyncClient,
    url: str,
    *,
    json_payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    response = await client.post(url, json=json_payload)
    latency_ms = int((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    return response.json(), latency_ms


async def run_participant(
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
    *,
    base_url: str,
    bracelet_id: str,
    language: str,
) -> FlowResult:
    async with semaphore:
        started = time.perf_counter()
        access_ms = roll_ms = prepare_ms = submit_ms = None
        session_id = None
        series_id = None
        treatment_key = None
        treatment_deck_index = None
        position_index = None
        final_state = None
        payment_selected = False
        payout_amount_cents = 0
        try:
            access_payload = {
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": language,
                "landing_visible_ms": 1800,
                "info_panels_opened": [],
                "info_panel_durations_ms": {},
                "client_installation_id": f"classroom-{bracelet_id}",
                "consent_checkbox_order": ["age", "participation", "data"],
                "consent_checkbox_timestamps_ms": {
                    "age": 300,
                    "participation": 600,
                    "data": 900,
                },
                "consent_continue_blocked_count": 0,
                "client_context": {
                    "browser_family": "load-test",
                    "device_type": "desktop",
                    "platform": "classroom",
                    "language_browser": language,
                    "viewport_width": 1280,
                    "viewport_height": 720,
                    "screen_width": 1280,
                    "screen_height": 720,
                    "touch_capable": False,
                    "online_status": "online",
                },
            }
            access_data, access_ms = await timed_post(
                client,
                f"{base_url}/v1/session/access",
                json_payload=access_payload,
            )
            session_payload = access_data["session"]
            session_id = session_payload["session_id"]
            series_id = session_payload["series_id"]
            treatment_key = session_payload["treatment_key"]
            treatment_deck_index = session_payload.get("treatment_deck_index")
            position_index = session_payload["position_index"]

            roll_data, roll_ms = await timed_post(
                client,
                f"{base_url}/v1/session/{session_id}/roll",
                json_payload={
                    "attempt_index": 1,
                    "reaction_ms": 1200,
                    "idempotency_key": idempotency_key("roll", bracelet_id),
                },
            )
            first_value = int(roll_data["attempt"]["result_value"])

            _, prepare_ms = await timed_post(
                client,
                f"{base_url}/v1/session/{session_id}/prepare-report",
                json_payload={
                    "idempotency_key": idempotency_key("prepare", bracelet_id),
                },
            )

            submit_data, submit_ms = await timed_post(
                client,
                f"{base_url}/v1/session/{session_id}/submit-report",
                json_payload={
                    "reported_value": first_value,
                    "reaction_ms": 900,
                    "idempotency_key": idempotency_key("submit", bracelet_id),
                    "language": language,
                },
            )
            final_payload = submit_data["session"]
            final_state = final_payload["state"]
            payment_selected = bool(final_payload["selected_for_payment"])
            payout_amount_cents = int(final_payload["payout_amount_cents"])
            total_ms = int((time.perf_counter() - started) * 1000)
            return FlowResult(
                bracelet_id=bracelet_id,
                session_id=session_id,
                series_id=series_id,
                treatment_key=treatment_key,
                treatment_deck_index=treatment_deck_index,
                position_index=position_index,
                final_state=final_state,
                payment_selected=payment_selected,
                payout_amount_cents=payout_amount_cents,
                success=True,
                error=None,
                total_ms=total_ms,
                access_ms=access_ms,
                roll_ms=roll_ms,
                prepare_ms=prepare_ms,
                submit_ms=submit_ms,
            )
        except Exception as exc:  # noqa: BLE001
            total_ms = int((time.perf_counter() - started) * 1000)
            return FlowResult(
                bracelet_id=bracelet_id,
                session_id=session_id,
                series_id=series_id,
                treatment_key=treatment_key,
                treatment_deck_index=treatment_deck_index,
                position_index=position_index,
                final_state=final_state,
                payment_selected=payment_selected,
                payout_amount_cents=payout_amount_cents,
                success=False,
                error=str(exc),
                total_ms=total_ms,
                access_ms=access_ms,
                roll_ms=roll_ms,
                prepare_ms=prepare_ms,
                submit_ms=submit_ms,
            )


def percentile(values: list[int], probability: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def summarize_results(results: list[FlowResult]) -> dict[str, Any]:
    successful = [item for item in results if item.success]
    failures = [item for item in results if not item.success]
    positions = [
        (item.treatment_deck_index, item.position_index)
        for item in successful
        if item.treatment_deck_index is not None and item.position_index is not None
    ]
    duplicate_positions = len(positions) - len(set(positions))
    state_counts: dict[str, int] = {}
    treatment_counts: dict[str, int] = {}
    for item in successful:
        state_counts[item.final_state or "unknown"] = (
            state_counts.get(item.final_state or "unknown", 0) + 1
        )
        treatment_counts[item.treatment_key or "unknown"] = (
            treatment_counts.get(item.treatment_key or "unknown", 0) + 1
        )
    total_latencies = [item.total_ms for item in successful]
    return {
        "requested_users": len(results),
        "successful_users": len(successful),
        "failed_users": len(failures),
        "duplicate_treatment_positions": duplicate_positions,
        "all_states_completed": all(
            item.final_state in {"completed_win", "completed_no_win"}
            for item in successful
        ),
        "winner_count": sum(1 for item in successful if item.payment_selected),
        "total_prize_amount_eur": round(
            sum(item.payout_amount_cents for item in successful) / 100, 2
        ),
        "treatment_counts": treatment_counts,
        "final_state_counts": state_counts,
        "p50_total_ms": percentile(total_latencies, 0.50),
        "p95_total_ms": percentile(total_latencies, 0.95),
        "mean_total_ms": round(statistics.mean(total_latencies), 2)
        if total_latencies
        else None,
        "errors": [
            {"bracelet_id": item.bracelet_id, "error": item.error}
            for item in failures[:20]
        ],
    }


async def fetch_admin_json(
    client: httpx.AsyncClient,
    *,
    url: str,
) -> Any:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def fetch_admin_csv(
    client: httpx.AsyncClient,
    *,
    url: str,
) -> list[dict[str, str]]:
    response = await client.get(url)
    response.raise_for_status()
    reader = csv.DictReader(response.text.splitlines())
    return list(reader)


async def enrich_with_admin_checks(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    roots = await fetch_admin_json(client, url=f"{base_url}/admin/roots")
    session_rows = await fetch_admin_csv(
        client,
        url=f"{base_url}/admin/export/sessions.csv",
    )
    invalid_session_rows = []
    seen_treatment_positions: set[tuple[str, str]] = set()
    seen_result_positions: set[tuple[str, str]] = set()
    seen_payment_positions: set[tuple[str, str]] = set()
    for row in session_rows:
        try:
            treatment_deck_index = str(int(row.get("treatment_deck_index") or 0))
            treatment_card_position = str(int(row.get("treatment_card_position") or 0))
            result_deck_index = str(int(row.get("result_deck_index") or 0))
            result_card_position = str(int(row.get("result_card_position") or 0))
            payment_deck_index = str(int(row.get("payment_deck_index") or 0))
            payment_card_position = str(int(row.get("payment_card_position") or 0))
        except ValueError:
            invalid_session_rows.append(
                {"session_id": row.get("session_id"), "reason": "parse_error"}
            )
            continue

        treatment_position = (treatment_deck_index, treatment_card_position)
        result_position = (result_deck_index, result_card_position)
        payment_position = (payment_deck_index, payment_card_position)

        if treatment_position in seen_treatment_positions:
            invalid_session_rows.append(
                {
                    "session_id": row.get("session_id"),
                    "reason": "duplicate_treatment_position",
                }
            )
        if result_position in seen_result_positions:
            invalid_session_rows.append(
                {
                    "session_id": row.get("session_id"),
                    "reason": "duplicate_result_position",
                }
            )
        if payment_position in seen_payment_positions:
            invalid_session_rows.append(
                {
                    "session_id": row.get("session_id"),
                    "reason": "duplicate_payment_position",
                }
            )

        seen_treatment_positions.add(treatment_position)
        seen_result_positions.add(result_position)
        seen_payment_positions.add(payment_position)

    summary["admin_checks"] = {
        "root_count": len(roots),
        "invalid_session_rows": invalid_session_rows,
        "sessions_rows_checked": len(session_rows),
    }
    return summary


def write_outputs(
    output_dir: Path,
    results: list[FlowResult],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "classroom_load_test_results.csv"
    summary_path = output_dir / "classroom_load_test_summary.json"

    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "bracelet_id",
                "session_id",
                "series_id",
                "treatment_key",
                "treatment_deck_index",
                "position_index",
                "final_state",
                "payment_selected",
                "payout_amount_cents",
                "success",
                "error",
                "total_ms",
                "access_ms",
                "roll_ms",
                "prepare_ms",
                "submit_ms",
            ],
        )
        writer.writeheader()
        for item in results:
            writer.writerow(item.__dict__)

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


async def async_main(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    output_dir = Path(args.output_dir)
    semaphore = asyncio.Semaphore(args.concurrency)
    admin_auth = basic_auth_tuple(args)
    limits = httpx.Limits(max_connections=args.concurrency + 10, max_keepalive_connections=args.concurrency + 10)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT),
        limits=limits,
        auth=admin_auth,
    ) as client:
        health_response = await client.get(f"{base_url}/health/ready")
        health_response.raise_for_status()
        bracelets = [
            bracelet_code(args.bracelet_start + offset)
            for offset in range(args.users)
        ]
        tasks = [
            run_participant(
                semaphore,
                client,
                base_url=base_url,
                bracelet_id=bracelet_id,
                language=args.language,
            )
            for bracelet_id in bracelets
        ]
        results = await asyncio.gather(*tasks)
        summary = summarize_results(results)
        if admin_auth:
            summary = await enrich_with_admin_checks(
                client,
                base_url=base_url,
                summary=summary,
            )
        write_outputs(output_dir, results, summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if summary["failed_users"] > 0 or summary["duplicate_treatment_positions"] > 0:
            return 1
        if "admin_checks" in summary and summary["admin_checks"]["invalid_session_rows"]:
            return 1
        return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
