from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx

from qa_reporting import DEFAULT_REPORT_DIR, export_results_csv, log_test_result

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "api-sonar-main" / "api-sonar-main"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SIM_DB_DIR = tempfile.mkdtemp(prefix="sonar_festival_sim_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(SIM_DB_DIR, 'simulation.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["STRUCTURED_LOGS"] = "false"
os.environ["AUTO_BOOTSTRAP_DEMO_DATA"] = "false"
os.environ["DB_POOL_SIZE"] = "80"
os.environ["DB_MAX_OVERFLOW"] = "160"
os.environ["DB_POOL_TIMEOUT_SECONDS"] = "120"
os.environ["DB_SQLITE_BUSY_TIMEOUT_SECONDS"] = "60"

from sqlmodel import Session, SQLModel, select

from database import engine
from main import app, bootstrap_demo_data, ensure_runtime_ready
from models import Claim, Payment, SessionRecord, Throw
from runtime import reset_observability_metrics

ProfileName = Literal["honest", "liar", "self_deception", "abandon"]
AbandonStage = Literal[
    "instructions",
    "comprehension",
    "game",
    "after_first_roll",
    "report",
]

DEFAULT_USERS = 1000
DEFAULT_CONCURRENCY = 40
DEFAULT_TIMEOUT = 30.0
DEFAULT_SEED = 20260502


@dataclass(slots=True)
class ParticipantResult:
    bracelet_id: str
    profile: ProfileName
    session_id: str | None
    success: bool
    abandoned: bool
    abandon_stage: str | None
    error: str | None
    final_state: str | None
    final_screen: str | None
    treatment_key: str | None
    treatment_deck_index: int | None
    position_index: int | None
    first_result_value: int | None
    last_seen_value: int | None
    seen_values: list[int]
    reported_value: int | None
    is_honest: bool | None
    matches_last_seen: bool | None
    matches_any_seen: bool | None
    selected_for_payment: bool | None
    payment_amount_cents: int | None
    throws_count: int
    reroll_count: int
    window_consistent: bool | None
    control_pure: bool | None
    access_ms: int | None
    screens_ms: list[int]
    roll_ms: list[int]
    prepare_ms: int | None
    submit_ms: int | None
    total_ms: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulación preflight de 1000 usuarios para SONAR.",
    )
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_REPORT_DIR),
    )
    return parser.parse_args()


def bracelet_code(index: int) -> str:
    return f"SIMA{index:04d}"


def installation_id(index: int) -> str:
    return f"festival-sim-{index:04d}"


def idempotency_key(prefix: str, bracelet_id: str, attempt: int | None = None) -> str:
    attempt_suffix = f"-{attempt}" if attempt is not None else ""
    return f"{prefix}-{bracelet_id}{attempt_suffix}-{uuid4().hex}"


def iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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


def summarize_latency(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "avg_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    return {
        "count": len(values),
        "avg_ms": round(sum(values) / len(values), 2),
        "p50_ms": percentile(values, 0.5),
        "p95_ms": percentile(values, 0.95),
        "max_ms": max(values),
    }


def build_profiles(total_users: int, seed: int) -> list[ProfileName]:
    base_profiles: list[ProfileName] = [
        "honest",
        "liar",
        "self_deception",
        "abandon",
    ]
    counts = {name: total_users // 4 for name in base_profiles}
    remainder = total_users - sum(counts.values())
    for name in base_profiles[:remainder]:
        counts[name] += 1

    profiles: list[ProfileName] = []
    for name, count in counts.items():
        profiles.extend([name] * count)

    rng = random.Random(seed)
    rng.shuffle(profiles)
    return profiles


def choose_abandon_stage(rng: random.Random) -> AbandonStage:
    roll = rng.random()
    if roll < 0.25:
        return "instructions"
    if roll < 0.5:
        return "comprehension"
    if roll < 0.7:
        return "game"
    if roll < 0.85:
        return "after_first_roll"
    return "report"


def choose_reroll_target_count(
    profile: ProfileName,
    rng: random.Random,
    max_attempts: int,
) -> int:
    if max_attempts <= 1:
        return 0
    if profile == "honest":
        return rng.choices([0, 1, 2], weights=[0.6, 0.3, 0.1], k=1)[0]
    if profile == "liar":
        return rng.choices([0, 1, 2, 3], weights=[0.15, 0.35, 0.3, 0.2], k=1)[0]
    if profile == "self_deception":
        return rng.choices([1, 2, 3, 4], weights=[0.3, 0.35, 0.25, 0.1], k=1)[0]
    return 0


def reported_value_for_profile(
    profile: ProfileName,
    *,
    first_result_value: int,
    seen_values: list[int],
) -> int:
    if profile == "honest":
        return first_result_value
    if profile == "liar":
        return 6
    if profile == "self_deception":
        return seen_values[-1]
    return first_result_value


async def timed_post(
    client: httpx.AsyncClient,
    path: str,
    *,
    json_payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    response = await client.post(path, json=json_payload, headers=headers)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        raise RuntimeError(f"{path} -> {response.status_code}: {response.text}")
    return response.json(), elapsed_ms


async def run_participant(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    *,
    participant_index: int,
    profile: ProfileName,
    seed: int,
) -> ParticipantResult:
    async with semaphore:
        rng = random.Random(seed + participant_index * 104729)
        bracelet_id = bracelet_code(participant_index)
        install_id = installation_id(participant_index)
        request_headers = {"X-Sonar-Installation": install_id}
        started = time.perf_counter()
        access_ms: int | None = None
        prepare_ms: int | None = None
        submit_ms: int | None = None
        screens_ms: list[int] = []
        roll_ms: list[int] = []
        seen_values: list[int] = []
        session_id: str | None = None
        treatment_key: str | None = None
        treatment_deck_index: int | None = None
        position_index: int | None = None
        max_attempts = 1
        access_displayed_count: int | None = None
        access_displayed_denominator: int | None = None
        final_state: str | None = None
        final_screen: str | None = None
        abandon_stage: str | None = None
        first_result_value: int | None = None
        last_seen_value: int | None = None
        reported_value: int | None = None
        is_honest: bool | None = None
        matches_last_seen: bool | None = None
        matches_any_seen: bool | None = None
        selected_for_payment: bool | None = None
        payment_amount_cents: int | None = None
        window_consistent: bool | None = None
        control_pure: bool | None = None

        try:
            access_payload = {
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "landing_visible_ms": rng.randint(650, 2600),
                "info_panels_opened": ["study"] if rng.random() < 0.3 else [],
                "info_panel_durations_ms": {"study": rng.randint(300, 2000)}
                if rng.random() < 0.3
                else {},
                "client_installation_id": install_id,
                "consent_checkbox_order": ["age", "participation", "data"],
                "consent_checkbox_timestamps_ms": {
                    "age": 250,
                    "participation": 520,
                    "data": 810,
                },
                "consent_continue_blocked_count": 0,
                "client_context": {
                    "browser_family": "simulation",
                    "device_type": "mobile",
                    "platform": "festival",
                    "language_browser": "es",
                    "viewport_width": 390,
                    "viewport_height": 844,
                    "screen_width": 390,
                    "screen_height": 844,
                    "touch_capable": True,
                    "online_status": "online",
                },
            }
            access_data, access_ms = await timed_post(
                client,
                "/v1/session/access",
                json_payload=access_payload,
            )
            session = access_data["session"]
            session_id = session["session_id"]
            final_state = session["state"]
            final_screen = session["screen"]
            treatment_key = session["treatment_key"]
            treatment_deck_index = session["treatment_deck_index"]
            position_index = session["position_index"]
            max_attempts = int(session["max_attempts"])
            access_displayed_count = session["displayed_count_target"]
            access_displayed_denominator = session["displayed_denominator"]

            if profile == "abandon":
                abandon_stage = choose_abandon_stage(rng)
                if abandon_stage == "instructions":
                    return ParticipantResult(
                        bracelet_id=bracelet_id,
                        profile=profile,
                        session_id=session_id,
                        success=True,
                        abandoned=True,
                        abandon_stage=abandon_stage,
                        error=None,
                        final_state=final_state,
                        final_screen=final_screen,
                        treatment_key=treatment_key,
                        treatment_deck_index=treatment_deck_index,
                        position_index=position_index,
                        first_result_value=None,
                        last_seen_value=None,
                        seen_values=[],
                        reported_value=None,
                        is_honest=None,
                        matches_last_seen=None,
                        matches_any_seen=None,
                        selected_for_payment=None,
                        payment_amount_cents=None,
                        throws_count=0,
                        reroll_count=0,
                        window_consistent=None,
                        control_pure=None,
                        access_ms=access_ms,
                        screens_ms=screens_ms,
                        roll_ms=roll_ms,
                        prepare_ms=None,
                        submit_ms=None,
                        total_ms=int((time.perf_counter() - started) * 1000),
                    )

            for screen_name in ("comprehension", "game"):
                screen_data, screen_ms = await timed_post(
                    client,
                    f"/v1/session/{session_id}/screen",
                    json_payload={"screen": screen_name},
                    headers=request_headers,
                )
                screens_ms.append(screen_ms)
                final_state = screen_data["session"]["state"]
                final_screen = screen_data["session"]["screen"]
                if profile == "abandon":
                    if abandon_stage == "comprehension" and screen_name == "comprehension":
                        break
                    if abandon_stage == "game" and screen_name == "game":
                        break

            if profile == "abandon" and abandon_stage in {"comprehension", "game"}:
                return ParticipantResult(
                    bracelet_id=bracelet_id,
                    profile=profile,
                    session_id=session_id,
                    success=True,
                    abandoned=True,
                    abandon_stage=abandon_stage,
                    error=None,
                    final_state=final_state,
                    final_screen=final_screen,
                    treatment_key=treatment_key,
                    treatment_deck_index=treatment_deck_index,
                    position_index=position_index,
                    first_result_value=None,
                    last_seen_value=None,
                    seen_values=[],
                    reported_value=None,
                    is_honest=None,
                    matches_last_seen=None,
                    matches_any_seen=None,
                    selected_for_payment=None,
                    payment_amount_cents=None,
                    throws_count=0,
                    reroll_count=0,
                    window_consistent=None,
                    control_pure=None,
                    access_ms=access_ms,
                    screens_ms=screens_ms,
                    roll_ms=roll_ms,
                    prepare_ms=None,
                    submit_ms=None,
                    total_ms=int((time.perf_counter() - started) * 1000),
                )

            first_roll, first_roll_ms = await timed_post(
                client,
                f"/v1/session/{session_id}/roll",
                json_payload={
                    "attempt_index": 1,
                    "reaction_ms": rng.randint(400, 1600),
                    "idempotency_key": idempotency_key("roll", bracelet_id, 1),
                },
                headers=request_headers,
            )
            roll_ms.append(first_roll_ms)
            first_result_value = int(first_roll["attempt"]["result_value"])
            seen_values.append(first_result_value)
            max_attempts = int(first_roll["session"]["max_attempts"])
            final_state = first_roll["session"]["state"]
            final_screen = first_roll["session"]["screen"]

            if profile == "abandon" and abandon_stage == "after_first_roll":
                return ParticipantResult(
                    bracelet_id=bracelet_id,
                    profile=profile,
                    session_id=session_id,
                    success=True,
                    abandoned=True,
                    abandon_stage=abandon_stage,
                    error=None,
                    final_state=final_state,
                    final_screen=final_screen,
                    treatment_key=treatment_key,
                    treatment_deck_index=treatment_deck_index,
                    position_index=position_index,
                    first_result_value=first_result_value,
                    last_seen_value=first_result_value,
                    seen_values=seen_values,
                    reported_value=None,
                    is_honest=None,
                    matches_last_seen=None,
                    matches_any_seen=None,
                    selected_for_payment=None,
                    payment_amount_cents=None,
                    throws_count=1,
                    reroll_count=0,
                    window_consistent=None,
                    control_pure=None,
                    access_ms=access_ms,
                    screens_ms=screens_ms,
                    roll_ms=roll_ms,
                    prepare_ms=None,
                    submit_ms=None,
                    total_ms=int((time.perf_counter() - started) * 1000),
                )

            rerolls_requested = min(
                choose_reroll_target_count(profile, rng, max_attempts),
                max(0, max_attempts - 1),
            )
            for reroll_offset in range(rerolls_requested):
                attempt_index = 2 + reroll_offset
                reroll_data, reroll_latency = await timed_post(
                    client,
                    f"/v1/session/{session_id}/roll",
                    json_payload={
                        "attempt_index": attempt_index,
                        "reaction_ms": rng.randint(450, 1800),
                        "idempotency_key": idempotency_key(
                            "roll",
                            bracelet_id,
                            attempt_index,
                        ),
                    },
                    headers=request_headers,
                )
                roll_ms.append(reroll_latency)
                seen_values.append(int(reroll_data["attempt"]["result_value"]))
                final_state = reroll_data["session"]["state"]
                final_screen = reroll_data["session"]["screen"]

            prepare_data, prepare_ms = await timed_post(
                client,
                f"/v1/session/{session_id}/prepare-report",
                json_payload={
                    "idempotency_key": idempotency_key("prepare", bracelet_id),
                },
                headers=request_headers,
            )
            final_state = prepare_data["session"]["state"]
            final_screen = prepare_data["session"]["screen"]
            snapshot = prepare_data["session"]["report_snapshot"]

            if profile == "abandon" and abandon_stage == "report":
                return ParticipantResult(
                    bracelet_id=bracelet_id,
                    profile=profile,
                    session_id=session_id,
                    success=True,
                    abandoned=True,
                    abandon_stage=abandon_stage,
                    error=None,
                    final_state=final_state,
                    final_screen=final_screen,
                    treatment_key=treatment_key,
                    treatment_deck_index=treatment_deck_index,
                    position_index=position_index,
                    first_result_value=first_result_value,
                    last_seen_value=seen_values[-1],
                    seen_values=seen_values,
                    reported_value=None,
                    is_honest=None,
                    matches_last_seen=None,
                    matches_any_seen=None,
                    selected_for_payment=None,
                    payment_amount_cents=None,
                    throws_count=len(seen_values),
                    reroll_count=max(0, len(seen_values) - 1),
                    window_consistent=None,
                    control_pure=None,
                    access_ms=access_ms,
                    screens_ms=screens_ms,
                    roll_ms=roll_ms,
                    prepare_ms=prepare_ms,
                    submit_ms=None,
                    total_ms=int((time.perf_counter() - started) * 1000),
                )

            reported_value = reported_value_for_profile(
                profile,
                first_result_value=first_result_value,
                seen_values=seen_values,
            )
            submit_data, submit_ms = await timed_post(
                client,
                f"/v1/session/{session_id}/submit-report",
                json_payload={
                    "reported_value": reported_value,
                    "reaction_ms": rng.randint(350, 1500),
                    "idempotency_key": idempotency_key("submit", bracelet_id),
                    "language": "es",
                },
                headers=request_headers,
            )
            final_session = submit_data["session"]
            final_state = final_session["state"]
            final_screen = final_session["screen"]
            claim = final_session["claim"]
            payment = final_session["payment"]

            is_honest = claim["is_honest"]
            matches_last_seen = claim["matches_last_seen"]
            matches_any_seen = claim["matches_any_seen"]
            selected_for_payment = payment["eligible"]
            payment_amount_cents = payment["amount_cents"]
            last_seen_value = final_session["last_seen_value"]

            treatment_window_matches = True
            if final_session["treatment_key"].startswith("norm_"):
                try:
                    expected_count = int(final_session["treatment_key"].split("_", 1)[1])
                    treatment_window_matches = access_displayed_count == expected_count
                except ValueError:
                    treatment_window_matches = False

            window_consistent = (
                access_displayed_count == snapshot["count_target"] == final_session["displayed_count_target"]
                and access_displayed_denominator == snapshot["denominator"] == final_session["displayed_denominator"]
                and treatment_window_matches
            )
            control_pure = (
                (
                    final_session["treatment_key"] == "control"
                    and access_displayed_count is None
                    and access_displayed_denominator is None
                    and snapshot["is_control"] is True
                    and snapshot["count_target"] is None
                    and snapshot["denominator"] is None
                    and final_session["displayed_count_target"] is None
                    and final_session["displayed_denominator"] is None
                )
                or (
                    final_session["treatment_key"] != "control"
                    and access_displayed_denominator == 60
                    and snapshot["denominator"] == 60
                    and final_session["displayed_denominator"] == 60
                )
            )

            return ParticipantResult(
                bracelet_id=bracelet_id,
                profile=profile,
                session_id=session_id,
                success=True,
                abandoned=False,
                abandon_stage=None,
                error=None,
                final_state=final_state,
                final_screen=final_screen,
                treatment_key=treatment_key,
                treatment_deck_index=treatment_deck_index,
                position_index=position_index,
                first_result_value=first_result_value,
                last_seen_value=last_seen_value,
                seen_values=seen_values,
                reported_value=reported_value,
                is_honest=is_honest,
                matches_last_seen=matches_last_seen,
                matches_any_seen=matches_any_seen,
                selected_for_payment=selected_for_payment,
                payment_amount_cents=payment_amount_cents,
                throws_count=len(seen_values),
                reroll_count=max(0, len(seen_values) - 1),
                window_consistent=window_consistent,
                control_pure=control_pure,
                access_ms=access_ms,
                screens_ms=screens_ms,
                roll_ms=roll_ms,
                prepare_ms=prepare_ms,
                submit_ms=submit_ms,
                total_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return ParticipantResult(
                bracelet_id=bracelet_id,
                profile=profile,
                session_id=session_id,
                success=False,
                abandoned=False,
                abandon_stage=abandon_stage,
                error=str(exc),
                final_state=final_state,
                final_screen=final_screen,
                treatment_key=treatment_key,
                treatment_deck_index=treatment_deck_index,
                position_index=position_index,
                first_result_value=first_result_value,
                last_seen_value=last_seen_value,
                seen_values=seen_values,
                reported_value=reported_value,
                is_honest=is_honest,
                matches_last_seen=matches_last_seen,
                matches_any_seen=matches_any_seen,
                selected_for_payment=selected_for_payment,
                payment_amount_cents=payment_amount_cents,
                throws_count=len(seen_values),
                reroll_count=max(0, len(seen_values) - 1),
                window_consistent=window_consistent,
                control_pure=control_pure,
                access_ms=access_ms,
                screens_ms=screens_ms,
                roll_ms=roll_ms,
                prepare_ms=prepare_ms,
                submit_ms=submit_ms,
                total_ms=int((time.perf_counter() - started) * 1000),
            )


def setup_simulation_database() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    reset_observability_metrics()
    with Session(engine) as db:
        bootstrap_demo_data(db)
    ensure_runtime_ready(timeout_seconds=30.0)


async def run_simulation(total_users: int, concurrency: int, seed: int) -> dict[str, Any]:
    setup_simulation_database()
    profiles = build_profiles(total_users, seed)
    transport = httpx.ASGITransport(app=app)
    semaphore = asyncio.Semaphore(concurrency)
    started = time.perf_counter()

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        tasks = [
            run_participant(
                client,
                semaphore,
                participant_index=index,
                profile=profile,
                seed=seed,
            )
            for index, profile in enumerate(profiles)
        ]
        results = await asyncio.gather(*tasks)
        metrics_response = await client.get("/admin/metrics")
        metrics_payload = metrics_response.json()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return build_report(
        results=results,
        metrics_payload=metrics_payload,
        total_users=total_users,
        concurrency=concurrency,
        seed=seed,
        elapsed_ms=elapsed_ms,
    )


def build_report(
    *,
    results: list[ParticipantResult],
    metrics_payload: dict[str, Any],
    total_users: int,
    concurrency: int,
    seed: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    successful = [item for item in results if item.success]
    completed = [item for item in successful if not item.abandoned and item.reported_value is not None]
    abandoned = [item for item in successful if item.abandoned]
    failures = [item for item in results if not item.success]

    by_profile: dict[str, dict[str, Any]] = {}
    for profile_name in ("honest", "liar", "self_deception", "abandon"):
        profile_items = [item for item in results if item.profile == profile_name]
        profile_completed = [item for item in profile_items if item.success and not item.abandoned]
        profile_abandoned = [item for item in profile_items if item.abandoned]
        profile_failures = [item for item in profile_items if not item.success]
        by_profile[profile_name] = {
            "requested": len(profile_items),
            "completed": len(profile_completed),
            "abandoned": len(profile_abandoned),
            "failed": len(profile_failures),
            "avg_total_ms": round(
                sum(item.total_ms for item in profile_items) / len(profile_items),
                2,
            )
            if profile_items
            else None,
            "avg_rerolls_completed": round(
                sum(item.reroll_count for item in profile_completed) / len(profile_completed),
                2,
            )
            if profile_completed
            else None,
        }

    first_result_distribution = Counter(
        item.first_result_value for item in successful if item.first_result_value is not None
    )
    reported_distribution = Counter(
        item.reported_value for item in completed if item.reported_value is not None
    )
    treatment_distribution = Counter(
        item.treatment_key for item in successful if item.treatment_key is not None
    )

    access_latencies = [item.access_ms for item in successful if item.access_ms is not None]
    screen_latencies = [
        latency
        for item in successful
        for latency in item.screens_ms
    ]
    roll_latencies = [
        latency
        for item in successful
        for latency in item.roll_ms
    ]
    prepare_latencies = [item.prepare_ms for item in successful if item.prepare_ms is not None]
    submit_latencies = [item.submit_ms for item in successful if item.submit_ms is not None]
    total_latencies = [item.total_ms for item in successful]

    with Session(engine) as db:
        session_rows = db.exec(select(SessionRecord)).all()
        claim_rows = db.exec(select(Claim)).all()
        payment_rows = db.exec(select(Payment)).all()
        throw_rows = db.exec(select(Throw)).all()

    duplicate_session_ids = len({row.id for row in session_rows}) != len(session_rows)
    duplicate_treatment_slots = len(
        [(row.treatment_deck_id, row.treatment_card_position) for row in session_rows]
    ) - len({(row.treatment_deck_id, row.treatment_card_position) for row in session_rows})
    duplicate_result_slots = len(
        [(row.result_deck_id, row.result_card_position) for row in session_rows]
    ) - len({(row.result_deck_id, row.result_card_position) for row in session_rows})
    duplicate_payment_slots = len(
        [(row.payment_deck_id, row.payment_card_position) for row in session_rows]
    ) - len({(row.payment_deck_id, row.payment_card_position) for row in session_rows})
    duplicate_series_positions = len(
        [(row.series_id, row.position_index) for row in session_rows]
    ) - len({(row.series_id, row.position_index) for row in session_rows})

    snapshot_before_claim_violations = [
        row.id
        for row in session_rows
        if row.report_prepared_at and row.claim_submitted_at and row.report_prepared_at > row.claim_submitted_at
    ]

    window_violations = [
        item.bracelet_id
        for item in completed
        if item.window_consistent is False or item.control_pure is False
    ]

    problems: list[dict[str, Any]] = []
    if failures:
        problems.append(
            {
                "severity": "high",
                "kind": "request_failures",
                "message": f"Se produjeron {len(failures)} fallos inesperados durante la simulación.",
                "examples": [item.error for item in failures[:10]],
            }
        )
    if duplicate_treatment_slots or duplicate_result_slots or duplicate_payment_slots or duplicate_series_positions:
        problems.append(
            {
                "severity": "critical",
                "kind": "assignment_collisions",
                "message": "Se detectaron colisiones de asignación en decks o posiciones de serie.",
                "details": {
                    "duplicate_treatment_slots": duplicate_treatment_slots,
                    "duplicate_result_slots": duplicate_result_slots,
                    "duplicate_payment_slots": duplicate_payment_slots,
                    "duplicate_series_positions": duplicate_series_positions,
                },
            }
        )
    if snapshot_before_claim_violations:
        problems.append(
            {
                "severity": "critical",
                "kind": "snapshot_order",
                "message": "Hay sesiones con claim antes del snapshot de reporte.",
                "count": len(snapshot_before_claim_violations),
                "session_ids": snapshot_before_claim_violations[:10],
            }
        )
    if window_violations:
        problems.append(
            {
                "severity": "critical",
                "kind": "window_inconsistency",
                "message": "La ventana visible no se mantuvo estable en parte de las sesiones completadas.",
                "count": len(window_violations),
                "bracelets": window_violations[:10],
            }
        )

    endpoint_metrics = metrics_payload.get("endpoint_metrics", [])
    if endpoint_metrics:
        slowest = sorted(
            endpoint_metrics,
            key=lambda item: (item.get("p95_duration_ms") or 0, item.get("avg_duration_ms") or 0),
            reverse=True,
        )[:5]
        for item in slowest:
            if (item.get("p95_duration_ms") or 0) > 100:
                problems.append(
                    {
                        "severity": "medium",
                        "kind": "endpoint_latency",
                        "message": f"El endpoint {item['endpoint']} supera 100 ms p95 en la simulación local.",
                        "p95_duration_ms": item.get("p95_duration_ms"),
                        "error_rate": item.get("error_rate"),
                    }
                )

    report = {
        "schema_version": "simulation-report-v1",
        "generated_at": iso_now(),
        "input": {
            "users": total_users,
            "concurrency": concurrency,
            "seed": seed,
            "profiles": dict(Counter(item.profile for item in results)),
        },
        "stability": {
            "requested_users": total_users,
            "successful_users": len(successful),
            "completed_users": len(completed),
            "abandoned_users": len(abandoned),
            "failed_users": len(failures),
            "unexpected_completion_gap": max(
                0,
                len([item for item in results if item.profile != "abandon"]) - len(completed) - len(failures),
            ),
            "elapsed_ms_total": elapsed_ms,
        },
        "profiles": by_profile,
        "distribution": {
            "first_result_value": {str(key): value for key, value in sorted(first_result_distribution.items())},
            "reported_value": {str(key): value for key, value in sorted(reported_distribution.items())},
            "treatment_counts": {
                key: value for key, value in sorted(treatment_distribution.items())
            },
            "distinct_treatments_seen": len(treatment_distribution),
        },
        "consistency": {
            "window_consistent_count": sum(1 for item in completed if item.window_consistent is True),
            "window_checked_count": len(completed),
            "control_pure_count": sum(1 for item in completed if item.control_pure is True),
            "snapshot_before_claim_violation_count": len(snapshot_before_claim_violations),
            "assignment_collisions": {
                "duplicate_session_ids": duplicate_session_ids,
                "duplicate_treatment_slots": duplicate_treatment_slots,
                "duplicate_result_slots": duplicate_result_slots,
                "duplicate_payment_slots": duplicate_payment_slots,
                "duplicate_series_positions": duplicate_series_positions,
            },
            "database_counts": {
                "sessions": len(session_rows),
                "claims": len(claim_rows),
                "payments": len(payment_rows),
                "throws": len(throw_rows),
            },
        },
        "behavioral_summary": {
            "honest_claims": sum(1 for item in completed if item.is_honest is True),
            "dishonest_claims": sum(1 for item in completed if item.is_honest is False),
            "matches_last_seen_claims": sum(1 for item in completed if item.matches_last_seen is True),
            "matches_any_seen_claims": sum(1 for item in completed if item.matches_any_seen is True),
            "avg_reroll_count_completed": round(
                sum(item.reroll_count for item in completed) / len(completed),
                2,
            )
            if completed
            else None,
        },
        "latency": {
            "access": summarize_latency([value for value in access_latencies if value is not None]),
            "screen": summarize_latency(screen_latencies),
            "roll": summarize_latency(roll_latencies),
            "prepare_report": summarize_latency([value for value in prepare_latencies if value is not None]),
            "submit_report": summarize_latency([value for value in submit_latencies if value is not None]),
            "total_flow": summarize_latency(total_latencies),
        },
        "observability": {
            "summary": metrics_payload.get("summary"),
            "alerts": metrics_payload.get("alerts"),
            "screen_abandonment": metrics_payload.get("screen_abandonment"),
            "endpoint_metrics": endpoint_metrics,
        },
        "problems": problems,
        "sample_failures": [asdict(item) for item in failures[:20]],
        "sample_users": [asdict(item) for item in results[:25]],
    }
    return report


def persist_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"festival_simulation_1000_{timestamp}.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    completed_users = report["stability"]["completed_users"]
    failed_users = report["stability"]["failed_users"]
    problems = report["problems"]
    status = "OK" if failed_users == 0 and not any(item["severity"] == "critical" for item in problems) else "WARNING"
    impact = "HIGH" if problems else "MEDIUM"
    actual_result = (
        f"Simulados {report['input']['users']} usuarios con {report['input']['concurrency']} de concurrencia; "
        f"completados {completed_users}, abandonos esperados {report['stability']['abandoned_users']}, "
        f"fallos {failed_users}, alertas {len(report['observability'].get('alerts') or [])}."
    )
    notes = "; ".join(item["kind"] for item in problems[:5]) if problems else "Sin incidencias críticas detectadas."
    log_test_result(
        test_id="SIM-1000-PREFLIGHT",
        scenario="Simulación preflight de 1000 usuarios con perfiles mixtos",
        input_data=report["input"],
        expected_result=(
            "El sistema debe procesar 1000 usuarios con perfiles honestos, mentirosos, autoengaño y abandono "
            "sin colisiones de asignación, sin inconsistencias de ventana y con estabilidad general del flujo."
        ),
        actual_result=actual_result,
        status=status,
        impact=impact,
        notes=notes,
    )
    csv_path = export_results_csv()
    return json_path, csv_path


def main() -> int:
    args = parse_args()
    try:
        report = asyncio.run(
            run_simulation(
                total_users=args.users,
                concurrency=args.concurrency,
                seed=args.seed,
            )
        )
        json_path, csv_path = persist_report(report, Path(args.output_dir))
        print(json.dumps({
            "report_path": str(json_path),
            "csv_path": str(csv_path),
            "completed_users": report["stability"]["completed_users"],
            "failed_users": report["stability"]["failed_users"],
            "problems": report["problems"],
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        shutil.rmtree(SIM_DB_DIR, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
