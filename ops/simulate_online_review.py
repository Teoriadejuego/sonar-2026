from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


BASE_URL = "https://api-production-9fe7b.up.railway.app"
DEFAULT_USERS = 1000
DEFAULT_BATCH_SIZE = 10
DEFAULT_LANGUAGE = "es"
DEFAULT_PREFIX = "PNAS"
DEFAULT_SEED = 20260408
DEFAULT_BATCH_PAUSE_SECONDS = 8.0
DEFAULT_MIN_STEP_DELAY_SECONDS = 1.2
DEFAULT_MAX_STEP_DELAY_SECONDS = 3.4
DEFAULT_BATCH_STAGGER_SECONDS = 5.5


@dataclass
class SimulationRow:
    bracelet_id: str
    session_id: str | None
    treatment_key: str | None
    displayed_count_target: int | None
    displayed_denominator: int | None
    first_result_value: int | None
    reported_value: int | None
    lied: bool | None
    lie_probability: float | None
    selected_for_payment: bool | None
    payout_amount_cents: int | None
    crowd_prediction_value: int | None
    social_recall_count: int | None
    social_recall_correct: bool | None
    access_attempts: int | None
    roll_attempts: int | None
    prepare_attempts: int | None
    submit_attempts: int | None
    followup_attempts: int | None
    transient_status_history: str | None
    access_status: int | None
    roll_status: int | None
    prepare_status: int | None
    submit_status: int | None
    followup_status: int | None
    success: bool
    error: str | None
    total_ms: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simula sesiones online en SONAR con mentira controlada por tratamiento.",
    )
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch-pause-seconds", type=float, default=DEFAULT_BATCH_PAUSE_SECONDS)
    parser.add_argument("--min-step-delay-seconds", type=float, default=DEFAULT_MIN_STEP_DELAY_SECONDS)
    parser.add_argument("--max-step-delay-seconds", type=float, default=DEFAULT_MAX_STEP_DELAY_SECONDS)
    parser.add_argument("--batch-stagger-seconds", type=float, default=DEFAULT_BATCH_STAGGER_SECONDS)
    parser.add_argument(
        "--output-dir",
        default=str(
            Path(__file__).resolve().parents[1]
            / "simulation"
            / datetime.now().strftime("%Y-%m-%d_online_review")
        ),
    )
    return parser.parse_args()


def bracelet_code(prefix: str, index: int) -> str:
    return f"{prefix}{index:04d}"


def idempotency_key(prefix: str, bracelet_id: str) -> str:
    return f"{prefix}-{bracelet_id}-{uuid4().hex}"


def recall_bucket(count_target: int | None) -> int | None:
    if count_target is None:
        return None
    if count_target <= 20:
        return 20
    if count_target <= 40:
        return 40
    return 60


def random_recall_bucket(rng: random.Random) -> int:
    return rng.choice([20, 40, 60])


def lie_probability_for_snapshot(
    treatment_key: str | None,
    count_target: int | None,
    denominator: int | None,
) -> float:
    if treatment_key == "control":
        return 0.5
    if count_target is None or denominator in {None, 0}:
        return 0.5
    return max(0.0, min(1.0, count_target / denominator))


async def paced_sleep(rng: random.Random, minimum: float, maximum: float) -> None:
    await asyncio.sleep(rng.uniform(minimum, maximum))


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None, str]:
    try:
        response = await client.request(method, url, json=json_payload)
    except Exception as exc:  # noqa: BLE001
        return 0, None, str(exc) or repr(exc)
    text = response.text
    parsed: dict[str, Any] | None = None
    try:
        parsed = response.json()
    except Exception:  # noqa: BLE001
        parsed = None
    return response.status_code, parsed, text


async def resume_session_payload(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    session_id: str,
) -> tuple[int, dict[str, Any] | None, str]:
    return await request_json(
        client,
        "GET",
        f"{base_url}/v1/session/{session_id}/resume",
    )


async def recover_completed_session(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    session_id: str,
    attempts: int = 4,
    pause_seconds: float = 2.0,
) -> dict[str, Any] | None:
    for _ in range(attempts):
        status, payload, _ = await resume_session_payload(
            client,
            base_url=base_url,
            session_id=session_id,
        )
        if status == 200 and payload:
            session = payload.get("session") or {}
            if session.get("state") in {"completed_win", "completed_no_win"} and session.get("claim"):
                return session
        await asyncio.sleep(pause_seconds)
    return None


async def update_screen_cursor(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    session_id: str,
    screen: str,
) -> tuple[int, dict[str, Any] | None, str]:
    return await request_json(
        client,
        "POST",
        f"{base_url}/v1/session/{session_id}/screen",
        json_payload={"screen": screen},
    )


async def capture_display_snapshot(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    session_id: str,
    language: str,
    treatment_message_text: str | None,
    is_control: bool,
) -> tuple[int, dict[str, Any] | None, str]:
    return await request_json(
        client,
        "POST",
        f"{base_url}/v1/session/{session_id}/display-snapshot",
        json_payload={
            "screen_name": "report",
            "language": language,
            "treatment_message_text": treatment_message_text,
            "control_message_text": treatment_message_text if is_control else None,
            "rerolls_visible": [],
        },
    )


async def request_json_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
    transient_statuses: set[int] | None = None,
    max_attempts: int = 10,
    base_backoff_seconds: float = 1.0,
) -> tuple[int, dict[str, Any] | None, str, int, list[int]]:
    retryable = transient_statuses or {0, 409, 429, 500, 502, 503, 504}
    last_status = 0
    last_parsed: dict[str, Any] | None = None
    last_text = ""
    history: list[int] = []
    for attempt in range(1, max_attempts + 1):
        status, parsed, text = await request_json(
            client,
            method,
            url,
            json_payload=json_payload,
        )
        history.append(status)
        last_status = status
        last_parsed = parsed
        last_text = text
        if status not in retryable:
            return status, parsed, text, attempt, history
        if attempt < max_attempts:
            await asyncio.sleep(base_backoff_seconds * attempt)
    return last_status, last_parsed, last_text, max_attempts, history


async def run_participant(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    bracelet_id: str,
    language: str,
    global_rng_seed: int,
    step_delay_min: float,
    step_delay_max: float,
    access_start_delay_seconds: float = 0.0,
    access_gate: asyncio.Lock | None = None,
    submit_gate: asyncio.Lock | None = None,
) -> SimulationRow:
    started = time.perf_counter()
    access_status = roll_status = prepare_status = submit_status = followup_status = None
    access_attempts = roll_attempts = prepare_attempts = submit_attempts = followup_attempts = None
    session_id = treatment_key = None
    count_target = denominator = None
    first_result_value = reported_value = None
    lied = None
    lie_probability = None
    selected_for_payment = None
    payout_amount_cents = None
    crowd_prediction_value = None
    social_recall_count = None
    social_recall_correct = None
    transient_status_history: list[int] = []
    per_person_seed = hash((global_rng_seed, bracelet_id)) & 0xFFFFFFFF
    rng = random.Random(per_person_seed)

    try:
        if access_start_delay_seconds > 0:
            await asyncio.sleep(access_start_delay_seconds)

        async with access_gate or asyncio.Lock():
            access_status, access_data, access_text, access_attempts, access_history = await request_json_with_retries(
                client,
                "POST",
                f"{base_url}/v1/session/access",
                json_payload={
                    "bracelet_id": bracelet_id,
                    "consent_accepted": True,
                    "consent_age_confirmed": True,
                    "consent_info_accepted": True,
                    "consent_data_accepted": True,
                    "language": language,
                    "landing_visible_ms": int(rng.uniform(1800, 4200)),
                    "info_panels_opened": ["study", "contact"],
                    "info_panel_durations_ms": {
                        "study": int(rng.uniform(900, 1800)),
                        "contact": int(rng.uniform(400, 900)),
                    },
                    "client_installation_id": f"online-sim-{bracelet_id}",
                    "consent_checkbox_order": ["age", "participation", "data"],
                    "consent_checkbox_timestamps_ms": {
                        "age": 240,
                        "participation": 520,
                        "data": 860,
                    },
                    "consent_continue_blocked_count": 0,
                    "client_context": {
                        "browser_family": "simulation",
                        "device_type": "mobile",
                        "platform": "python-httpx",
                        "language_browser": language,
                        "viewport_width": 393,
                        "viewport_height": 852,
                        "screen_width": 393,
                        "screen_height": 852,
                        "touch_capable": True,
                        "online_status": "online",
                    },
                },
                max_attempts=12,
                base_backoff_seconds=5.0,
            )
        transient_status_history.extend(access_history[:-1])
        if access_status != 200 or not access_data:
            raise RuntimeError(f"access:{access_status}:{access_text[:200]}")

        session = access_data["session"]
        session_id = session["session_id"]
        treatment_key = session.get("treatment_key")

        # The public review backend still expects the screen cursor path
        # used by the web client before rolling and reporting.
        for screen in ("comprehension", "game"):
            screen_status, _, screen_text = await update_screen_cursor(
                client,
                base_url=base_url,
                session_id=session_id,
                screen=screen,
            )
            if screen_status != 200:
                raise RuntimeError(f"screen:{screen}:{screen_status}:{screen_text[:200]}")

        await paced_sleep(rng, step_delay_min, step_delay_max)
        roll_idempotency_key = idempotency_key("roll", bracelet_id)
        roll_status, roll_data, roll_text, roll_attempts, roll_history = await request_json_with_retries(
            client,
            "POST",
            f"{base_url}/v1/session/{session_id}/roll",
            json_payload={
                "attempt_index": 1,
                "reaction_ms": int(rng.uniform(800, 2200)),
                "idempotency_key": roll_idempotency_key,
            },
        )
        transient_status_history.extend(roll_history[:-1])
        if roll_status != 200 or not roll_data:
            raise RuntimeError(f"roll:{roll_status}:{roll_text[:200]}")
        first_result_value = int(roll_data["attempt"]["result_value"])

        await paced_sleep(rng, step_delay_min, step_delay_max)
        prepare_idempotency_key = idempotency_key("prepare", bracelet_id)
        prepare_status, prepare_data, prepare_text, prepare_attempts, prepare_history = await request_json_with_retries(
            client,
            "POST",
            f"{base_url}/v1/session/{session_id}/prepare-report",
            json_payload={"idempotency_key": prepare_idempotency_key},
        )
        transient_status_history.extend(prepare_history[:-1])
        if prepare_status != 200 or not prepare_data:
            raise RuntimeError(f"prepare:{prepare_status}:{prepare_text[:200]}")

        snapshot = prepare_data["session"].get("report_snapshot") or {}
        count_target = snapshot.get("count_target")
        denominator = snapshot.get("denominator") or 60

        display_status, _, display_text = await capture_display_snapshot(
            client,
            base_url=base_url,
            session_id=session_id,
            language=language,
            treatment_message_text=snapshot.get("message"),
            is_control=bool(snapshot.get("is_control")),
        )
        if display_status != 200:
            raise RuntimeError(
                f"display_snapshot:{display_status}:{display_text[:200]}"
            )

        lie_probability = lie_probability_for_snapshot(
            treatment_key=treatment_key,
            count_target=count_target,
            denominator=denominator,
        )
        will_lie = rng.random() < lie_probability
        if will_lie and first_result_value != 6:
            reported_value = 6
        else:
            reported_value = first_result_value
        lied = reported_value != first_result_value

        await paced_sleep(rng, step_delay_min, step_delay_max)
        submit_idempotency_key = idempotency_key("submit", bracelet_id)
        async with submit_gate or asyncio.Lock():
            submit_status, submit_data, submit_text, submit_attempts, submit_history = await request_json_with_retries(
                client,
                "POST",
                f"{base_url}/v1/session/{session_id}/submit-report",
                json_payload={
                    "reported_value": reported_value,
                    "reaction_ms": int(rng.uniform(700, 1800)),
                    "idempotency_key": submit_idempotency_key,
                    "language": language,
                },
            )
        transient_status_history.extend(submit_history[:-1])
        completed: dict[str, Any] | None = None
        if submit_status == 200 and submit_data:
            completed = submit_data["session"]
        else:
            recovered = await recover_completed_session(
                client,
                base_url=base_url,
                session_id=session_id,
            )
            if recovered is not None:
                completed = recovered
            else:
                raise RuntimeError(f"submit:{submit_status}:{submit_text[:200]}")

        selected_for_payment = bool(completed.get("selected_for_payment"))
        payment_payload = completed.get("payment") or {}
        payout_amount_cents = int(payment_payload.get("amount_cents") or 0)

        crowd_prediction_value = reported_value
        social_recall_count = random_recall_bucket(rng)
        if social_recall_count is not None:
            await paced_sleep(rng, 0.5, 1.5)
            followup_status, followup_data, followup_text, followup_attempts, followup_history = await request_json_with_retries(
                client,
                "POST",
                f"{base_url}/v1/session/{session_id}/claim-followup",
                json_payload={
                    "crowd_prediction_value": crowd_prediction_value,
                    "social_recall_count": social_recall_count,
                    "language": language,
                },
            )
            transient_status_history.extend(followup_history[:-1])
            if followup_status not in {200, 404, 409, 422}:
                raise RuntimeError(f"followup:{followup_status}:{followup_text[:200]}")
            if followup_status == 200 and followup_data:
                claim = (followup_data.get("session") or {}).get("claim") or {}
                social_recall_correct = claim.get("social_recall_correct")
            else:
                social_recall_correct = social_recall_count == recall_bucket(count_target)
        total_ms = int((time.perf_counter() - started) * 1000)
        return SimulationRow(
            bracelet_id=bracelet_id,
            session_id=session_id,
            treatment_key=treatment_key,
            displayed_count_target=count_target,
            displayed_denominator=denominator,
            first_result_value=first_result_value,
            reported_value=reported_value,
            lied=lied,
            lie_probability=round(lie_probability, 4) if lie_probability is not None else None,
            selected_for_payment=selected_for_payment,
            payout_amount_cents=payout_amount_cents,
            crowd_prediction_value=crowd_prediction_value,
            social_recall_count=social_recall_count,
            social_recall_correct=social_recall_correct,
            access_attempts=access_attempts,
            roll_attempts=roll_attempts,
            prepare_attempts=prepare_attempts,
            submit_attempts=submit_attempts,
            followup_attempts=followup_attempts,
            transient_status_history="|".join(str(code) for code in transient_status_history) or None,
            access_status=access_status,
            roll_status=roll_status,
            prepare_status=prepare_status,
            submit_status=submit_status,
            followup_status=followup_status,
            success=True,
            error=None,
            total_ms=total_ms,
        )
    except Exception as exc:  # noqa: BLE001
        total_ms = int((time.perf_counter() - started) * 1000)
        return SimulationRow(
            bracelet_id=bracelet_id,
            session_id=session_id,
            treatment_key=treatment_key,
            displayed_count_target=count_target,
            displayed_denominator=denominator,
            first_result_value=first_result_value,
            reported_value=reported_value,
            lied=lied,
            lie_probability=round(lie_probability, 4) if lie_probability is not None else None,
            selected_for_payment=selected_for_payment,
            payout_amount_cents=payout_amount_cents,
            crowd_prediction_value=crowd_prediction_value,
            social_recall_count=social_recall_count,
            social_recall_correct=social_recall_correct,
            access_attempts=access_attempts,
            roll_attempts=roll_attempts,
            prepare_attempts=prepare_attempts,
            submit_attempts=submit_attempts,
            followup_attempts=followup_attempts,
            transient_status_history="|".join(str(code) for code in transient_status_history) or None,
            access_status=access_status,
            roll_status=roll_status,
            prepare_status=prepare_status,
            submit_status=submit_status,
            followup_status=followup_status,
            success=False,
            error=str(exc) or repr(exc),
            total_ms=total_ms,
        )


def write_jsonl(path: Path, rows: list[SimulationRow]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[SimulationRow]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def build_summary(rows: list[SimulationRow], args: argparse.Namespace) -> dict[str, Any]:
    success_rows = [row for row in rows if row.success]
    fail_rows = [row for row in rows if not row.success]
    total_transient_retries = 0
    transient_code_counts: dict[str, int] = {}
    for row in rows:
        for attempt_count in [
            row.access_attempts,
            row.roll_attempts,
            row.prepare_attempts,
            row.submit_attempts,
            row.followup_attempts,
        ]:
            if attempt_count and attempt_count > 1:
                total_transient_retries += attempt_count - 1
        if row.transient_status_history:
            for code in row.transient_status_history.split("|"):
                transient_code_counts[code] = transient_code_counts.get(code, 0) + 1
    by_treatment: dict[str, dict[str, Any]] = {}
    for row in success_rows:
        key = row.treatment_key or "unknown"
        bucket = by_treatment.setdefault(
            key,
            {
                "n": 0,
                "reported_6": 0,
                "actual_6": 0,
                "lied": 0,
                "mean_lie_probability": [],
            },
        )
        bucket["n"] += 1
        bucket["reported_6"] += int(row.reported_value == 6)
        bucket["actual_6"] += int(row.first_result_value == 6)
        bucket["lied"] += int(bool(row.lied))
        if row.lie_probability is not None:
            bucket["mean_lie_probability"].append(row.lie_probability)
    for bucket in by_treatment.values():
        probs = bucket.pop("mean_lie_probability")
        bucket["mean_lie_probability"] = round(sum(probs) / len(probs), 4) if probs else None
        bucket["reported_6_rate"] = round(bucket["reported_6"] / bucket["n"], 4) if bucket["n"] else None
        bucket["actual_6_rate"] = round(bucket["actual_6"] / bucket["n"], 4) if bucket["n"] else None
        bucket["lie_rate"] = round(bucket["lied"] / bucket["n"], 4) if bucket["n"] else None
    durations = [row.total_ms for row in success_rows]
    return {
        "run_started_at": datetime.now().isoformat(),
        "base_url": args.base_url,
        "users_requested": args.users,
        "batch_size": args.batch_size,
        "batch_pause_seconds": args.batch_pause_seconds,
        "success_count": len(success_rows),
        "failure_count": len(fail_rows),
        "mean_total_ms": round(statistics.mean(durations), 2) if durations else None,
        "median_total_ms": round(statistics.median(durations), 2) if durations else None,
        "total_transient_retries": total_transient_retries,
        "transient_status_counts": transient_code_counts,
        "treatment_summary": by_treatment,
        "errors": [
            {
                "bracelet_id": row.bracelet_id,
                "session_id": row.session_id,
                "error": row.error,
            }
            for row in fail_rows[:100]
        ],
    }


async def main_async(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[SimulationRow] = []
    batch_log_path = output_dir / "batch_progress.csv"
    with batch_log_path.open("w", newline="", encoding="utf-8") as batch_handle:
        batch_writer = csv.writer(batch_handle)
        batch_writer.writerow(
            [
                "batch_number",
                "started_at",
                "requested_users",
                "completed_users",
                "failed_users",
                "batch_runtime_s",
            ]
        )
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=20.0),
            headers={"User-Agent": "SONAR-online-simulation/1.0"},
            follow_redirects=True,
        ) as client:
            access_gate = asyncio.Lock()
            submit_gate = asyncio.Lock()
            total_batches = (args.users + args.batch_size - 1) // args.batch_size
            for batch_number in range(total_batches):
                batch_started = time.perf_counter()
                batch_users = []
                for offset in range(args.batch_size):
                    absolute_index = args.start_index + batch_number * args.batch_size + offset
                    if absolute_index >= args.start_index + args.users:
                        break
                    batch_users.append(bracelet_code(args.prefix, absolute_index))
                print(
                    f"[batch {batch_number + 1}/{total_batches}] launching {len(batch_users)} sessions...",
                    flush=True,
                )
                results = await asyncio.gather(
                    *[
                        run_participant(
                            client,
                            base_url=args.base_url,
                            bracelet_id=bracelet_id,
                            language=args.language,
                            global_rng_seed=args.seed,
                            step_delay_min=args.min_step_delay_seconds,
                            step_delay_max=args.max_step_delay_seconds,
                            access_start_delay_seconds=offset * args.batch_stagger_seconds,
                            access_gate=access_gate,
                            submit_gate=submit_gate,
                        )
                        for offset, bracelet_id in enumerate(batch_users)
                    ]
                )
                all_rows.extend(results)
                completed = sum(1 for row in results if row.success)
                failed = len(results) - completed
                batch_runtime_s = round(time.perf_counter() - batch_started, 2)
                batch_writer.writerow(
                    [
                        batch_number + 1,
                        datetime.now().isoformat(),
                        len(batch_users),
                        completed,
                        failed,
                        batch_runtime_s,
                    ]
                )
                batch_handle.flush()
                print(
                    f"[batch {batch_number + 1}/{total_batches}] done: ok={completed} fail={failed} runtime={batch_runtime_s}s",
                    flush=True,
                )
                if batch_number < total_batches - 1:
                    await asyncio.sleep(args.batch_pause_seconds)

    write_jsonl(output_dir / "raw_results.jsonl", all_rows)
    write_csv(output_dir / "simulation_rows.csv", all_rows)
    summary = build_summary(all_rows, args)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failure_count"] == 0 else 1


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
