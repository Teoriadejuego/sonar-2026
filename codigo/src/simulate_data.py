from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config_analysis import (
    ALLOCATION_VERSION,
    BASE_START_UTC,
    DECK_BLOCK_SIZE,
    DECK_VERSION,
    EXPERIMENT_PHASE,
    EXPERIMENT_VERSION,
    FESTIVAL_DAYS,
    LANGUAGES,
    LANGUAGE_WEIGHTS,
    MAX_ATTEMPTS,
    PAYMENT_VERSION,
    PRIZE_MAP,
    RANDOM_SEED,
    ROOT_COUNT,
    ROOT_IDS,
    SEED_INITIAL_COUNTS,
    SERIES_MAX_LENGTH,
    TARGET_VALUES,
    TREATMENT_COUNTS,
    TREATMENT_FAMILIES,
    TREATMENT_LABELS,
    TREATMENT_VERSION,
    UI_VERSION,
    VALID_COMPLETED_SESSIONS,
    VISIBLE_WINDOW,
)
from utils import (
    append_log,
    ensure_directories,
    festival_datetime,
    logistic,
    save_dataframe,
    stable_code,
    stable_hash,
    time_block_from_hour,
)


DATASETS = {
    "sessions": "sonar_sessions_simulated.csv",
    "throws": "sonar_throws_simulated.csv",
    "series": "sonar_series_simulated.csv",
    "position_plan": "sonar_position_plan_simulated.csv",
    "referrals": "sonar_referrals_simulated.csv",
}


def balanced_sequence(length: int, rng: np.random.Generator) -> list[int]:
    values: list[int] = []
    while len(values) < length:
        block = np.repeat(np.arange(1, 7), DECK_BLOCK_SIZE // 6)
        rng.shuffle(block)
        take = min(len(block), length - len(values))
        values.extend(block[:take].tolist())
    return values[:length]


def allocate_positions(total_count: int, rng: np.random.Generator) -> dict[str, list[int]]:
    base_count = total_count // ROOT_COUNT
    remainder = total_count % ROOT_COUNT
    extra_roots = set(rng.choice(ROOT_IDS, size=remainder, replace=False).tolist())
    allocation: dict[str, list[int]] = {}
    for root_id in ROOT_IDS:
        draw_count = base_count + (1 if root_id in extra_roots else 0)
        positions = sorted(rng.choice(np.arange(1, SERIES_MAX_LENGTH + 1), size=draw_count, replace=False).tolist())
        allocation[root_id] = positions
    return allocation


def sample_temporal_context(rng: np.random.Generator) -> tuple[int, int, int]:
    day_index = int(rng.integers(1, FESTIVAL_DAYS + 1))
    block = rng.choice(
        ["12-15", "15-18", "18-21", "21-00", "00-03"],
        p=[0.12, 0.18, 0.28, 0.28, 0.14],
    )
    if block == "12-15":
        hour_of_day = int(rng.integers(12, 15))
    elif block == "15-18":
        hour_of_day = int(rng.integers(15, 18))
    elif block == "18-21":
        hour_of_day = int(rng.integers(18, 21))
    elif block == "21-00":
        hour_of_day = int(rng.integers(21, 24))
    else:
        hour_of_day = int(rng.integers(0, 3))
    minute = int(rng.integers(0, 60))
    return day_index, hour_of_day, minute


def sample_reroll_count(
    true_first_result: int,
    treatment_key: str,
    rng: np.random.Generator,
) -> int:
    probability_any = 0.16 + 0.07 * (true_first_result <= 2) + 0.05 * (true_first_result <= 4)
    probability_any += 0.03 * (treatment_key != "control")
    if rng.random() >= min(probability_any, 0.55):
        return 0
    return int(
        rng.choice(
            [1, 2, 3, 4, 5],
            p=[0.54, 0.24, 0.12, 0.07, 0.03],
        )
    )


def choose_reported_value(
    true_first_result: int,
    seen_values: list[int],
    treatment_key: str,
    displayed_count_target: float | None,
    position_index: int,
    hour_of_day: int,
    root_effect: float,
    rng: np.random.Generator,
) -> int:
    max_seen = max(seen_values)
    last_seen = seen_values[-1]
    opportunity = max(0, 6 - true_first_result)
    norm_share = (
        displayed_count_target / VISIBLE_WINDOW
        if displayed_count_target is not None
        else 0.30
    )
    evening_bump = 0.08 if hour_of_day >= 21 or hour_of_day <= 1 else 0.0
    early_series = 0.12 if position_index <= 100 else -0.02
    p_report_6 = logistic(
        -3.10
        + 2.15 * norm_share
        + 0.22 * opportunity
        + 1.95 * (true_first_result == 6)
        + 0.48 * (6 in seen_values[1:])
        + 0.22 * (last_seen == 6)
        + evening_bump
        + early_series
        + root_effect
        + rng.normal(0.0, 0.08)
    )
    if rng.random() < p_report_6:
        return 6

    if true_first_result == 5 and rng.random() < 0.82:
        return 5

    p_report_5 = logistic(
        -2.55
        + 0.42 * (true_first_result <= 4)
        + 0.44 * (5 in seen_values[1:])
        + 0.16 * (max_seen >= 5)
        + 0.14 * opportunity
        + 0.10 * (position_index <= 100)
        + root_effect * 0.4
        + rng.normal(0.0, 0.08)
    )
    if true_first_result < 5 and rng.random() < p_report_5:
        return 5

    candidate_weights: dict[int, float] = defaultdict(float)
    candidate_weights[true_first_result] += 0.72 + 0.08 * (true_first_result >= 4)
    if last_seen > true_first_result:
        candidate_weights[last_seen] += 0.28 + 0.08 * (last_seen >= 5)
    if max_seen > true_first_result:
        candidate_weights[max_seen] += 0.22 + 0.06 * (max_seen >= 5)
    increment_value = min(true_first_result + 1, 4)
    if increment_value > true_first_result:
        candidate_weights[increment_value] += 0.16

    values = np.array(sorted(candidate_weights.keys()))
    weights = np.array([candidate_weights[value] for value in values], dtype=float)
    weights = weights / weights.sum()
    return int(rng.choice(values, p=weights))


def build_position_plan(rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for root_sequence, root_id in enumerate(ROOT_IDS, start=1):
        payout_positions = set(rng.choice(np.arange(1, SERIES_MAX_LENGTH + 1), size=2, replace=False).tolist())
        attempt_sequences = {
            attempt_index: balanced_sequence(SERIES_MAX_LENGTH, np.random.default_rng(RANDOM_SEED + root_sequence * 100 + attempt_index))
            for attempt_index in range(1, MAX_ATTEMPTS + 1)
        }
        for position_index in range(1, SERIES_MAX_LENGTH + 1):
            payout_eligible = position_index in payout_positions
            for attempt_index in range(1, MAX_ATTEMPTS + 1):
                result_value = attempt_sequences[attempt_index][position_index - 1]
                rows.append(
                    {
                        "root_id": root_id,
                        "root_sequence": root_sequence,
                        "experiment_phase": EXPERIMENT_PHASE,
                        "position_index": position_index,
                        "attempt_index": attempt_index,
                        "result_value": result_value,
                        "payout_eligible": payout_eligible,
                        "commitment_hash": stable_hash(
                            f"{root_id}|{position_index}|{attempt_index}|{result_value}|{payout_eligible}"
                        ),
                    }
                )
    return pd.DataFrame(rows)


def build_series_and_sessions(position_plan: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    position_lookup = {
        (row.root_id, int(row.position_index), int(row.attempt_index)): int(row.result_value)
        for row in position_plan.itertuples()
    }
    payout_lookup = {
        (row.root_id, int(row.position_index)): bool(row.payout_eligible)
        for row in position_plan.loc[position_plan["attempt_index"] == 1].itertuples()
    }

    root_effects = {
        root_id: float(rng.normal(0.0, 0.12))
        for root_id in ROOT_IDS
    }

    allocations = {
        treatment_key: allocate_positions(total_count, np.random.default_rng(RANDOM_SEED + offset))
        for offset, (treatment_key, total_count) in enumerate(TREATMENT_COUNTS.items(), start=1)
    }

    sessions_rows: list[dict[str, object]] = []
    throws_rows: list[dict[str, object]] = []
    series_rows: list[dict[str, object]] = []
    session_counter = 0

    for root_sequence, root_id in enumerate(ROOT_IDS, start=1):
        for treatment_key in ("control", "seed_17", "seed_83"):
            series_id = f"series_{root_sequence:02d}_{treatment_key}"
            treatment_family = TREATMENT_FAMILIES[treatment_key]
            norm_target_value = TARGET_VALUES[treatment_key]
            positions = allocations[treatment_key][root_id]
            visible_window: deque[int] | None = None
            if treatment_key != "control":
                seed_count = int(SEED_INITIAL_COUNTS[treatment_key] or 0)
                visible_window = deque(
                    [1] * seed_count + [0] * (VISIBLE_WINDOW - seed_count),
                    maxlen=VISIBLE_WINDOW,
                )

            for series_order, position_index in enumerate(positions, start=1):
                session_counter += 1
                session_id = f"S{session_counter:05d}"
                true_first_result = position_lookup[(root_id, position_index, 1)]
                reroll_count = min(
                    sample_reroll_count(true_first_result, treatment_key, rng),
                    MAX_ATTEMPTS - 1,
                )
                seen_values = [
                    position_lookup[(root_id, position_index, attempt_index)]
                    for attempt_index in range(1, reroll_count + 2)
                ]
                max_seen_value = max(seen_values)
                last_seen_value = seen_values[-1]
                day_index, hour_of_day, minute = sample_temporal_context(rng)
                displayed_count_target = (
                    float(sum(visible_window)) if visible_window is not None else np.nan
                )
                displayed_denominator = float(VISIBLE_WINDOW) if visible_window is not None else np.nan
                reported_value = choose_reported_value(
                    true_first_result=true_first_result,
                    seen_values=seen_values,
                    treatment_key=treatment_key,
                    displayed_count_target=None if np.isnan(displayed_count_target) else displayed_count_target,
                    position_index=position_index,
                    hour_of_day=hour_of_day,
                    root_effect=root_effects[root_id],
                    rng=rng,
                )

                target_indicator = int(reported_value == (norm_target_value or -1))
                if visible_window is not None:
                    visible_window.append(target_indicator)

                landing_to_start_ms = int(rng.lognormal(mean=np.log(3600), sigma=0.34))
                consent_total_ms = int(rng.lognormal(mean=np.log(6200), sigma=0.36))
                instructions_visible_ms = int(rng.lognormal(mean=np.log(3600), sigma=0.28))
                comprehension_visible_ms = int(rng.lognormal(mean=np.log(2100), sigma=0.25))
                game_visible_ms = int(rng.lognormal(mean=np.log(4200 + 900 * reroll_count), sigma=0.31))
                report_rt_ms = int(
                    rng.lognormal(
                        mean=np.log(2100 + 250 * reroll_count + 180 * (reported_value != true_first_result)),
                        sigma=0.33,
                    )
                )
                exit_visible_ms = int(rng.lognormal(mean=np.log(1800), sigma=0.20))
                game_decision_rt_ms = max(game_visible_ms - 900 * reroll_count, 800)
                total_session_ms = (
                    landing_to_start_ms
                    + consent_total_ms
                    + instructions_visible_ms
                    + comprehension_visible_ms
                    + game_visible_ms
                    + report_rt_ms
                    + exit_visible_ms
                )
                session_started_at = festival_datetime(day_index, hour_of_day, minute)
                session_completed_at = session_started_at + timedelta(milliseconds=total_session_ms)

                focus_loss_pre_claim = int(rng.random() < (0.05 + 0.03 * (reroll_count >= 2)))
                reload_count = int(rng.choice([0, 1, 2], p=[0.88, 0.10, 0.02]))
                network_error_count = int(rng.choice([0, 1, 2], p=[0.91, 0.08, 0.01]))
                quality_flag_fast_report = int(report_rt_ms < 900)
                browser = rng.choice(["Chrome", "Safari", "Firefox"], p=[0.62, 0.28, 0.10])
                os_family = rng.choice(["iOS", "Android", "Windows"], p=[0.48, 0.44, 0.08])
                language = str(rng.choice(LANGUAGES, p=LANGUAGE_WEIGHTS))
                selected_for_payment = int(payout_lookup[(root_id, position_index)])
                payment_amount_eur = PRIZE_MAP[reported_value] if selected_for_payment else 0
                click_count_by_screen = {
                    "landing": 4 + int(rng.integers(0, 3)),
                    "instructions": 1,
                    "comprehension": 2,
                    "game": 2 + reroll_count,
                    "report": 1,
                    "exit": 1 if not selected_for_payment else 2,
                }

                sessions_rows.append(
                    {
                        "session_id": session_id,
                        "bracelet_id_hash": stable_hash(f"bracelet-{session_id}"),
                        "root_id": root_id,
                        "root_sequence": root_sequence,
                        "series_id": series_id,
                        "series_order": series_order,
                        "treatment_key": treatment_key,
                        "treatment_label": TREATMENT_LABELS[treatment_key],
                        "treatment_family": treatment_family,
                        "position_index": position_index,
                        "experiment_phase": EXPERIMENT_PHASE,
                        "experiment_version": EXPERIMENT_VERSION,
                        "treatment_version": TREATMENT_VERSION,
                        "allocation_version": ALLOCATION_VERSION,
                        "deck_version": DECK_VERSION,
                        "payment_version": PAYMENT_VERSION,
                        "ui_version": UI_VERSION,
                        "true_first_result": true_first_result,
                        "reported_value": reported_value,
                        "reported_6": int(reported_value == 6),
                        "reported_5": int(reported_value == 5),
                        "reported_5_or_6": int(reported_value >= 5),
                        "reported_high": int(reported_value >= 5),
                        "is_honest": int(reported_value == true_first_result),
                        "lie_amount": int(max(0, reported_value - true_first_result)),
                        "opportunity_to_lie": int(max(0, 6 - true_first_result)),
                        "relative_lie": (
                            (reported_value - true_first_result) / max(1, 6 - true_first_result)
                            if true_first_result < 6
                            else 0.0
                        ),
                        "reroll_count": reroll_count,
                        "used_any_reroll": int(reroll_count > 0),
                        "max_seen_value": max_seen_value,
                        "last_seen_value": last_seen_value,
                        "reported_matches_first": int(reported_value == true_first_result),
                        "reported_matches_last": int(reported_value == last_seen_value),
                        "reported_matches_any_seen": int(reported_value in seen_values),
                        "reported_unseen": int(reported_value not in seen_values),
                        "landing_to_start_ms": landing_to_start_ms,
                        "consent_total_ms": consent_total_ms,
                        "instructions_visible_ms": instructions_visible_ms,
                        "comprehension_visible_ms": comprehension_visible_ms,
                        "game_visible_ms": game_visible_ms,
                        "report_visible_ms": report_rt_ms,
                        "exit_visible_ms": exit_visible_ms,
                        "report_rt_ms": report_rt_ms,
                        "game_decision_rt_ms": game_decision_rt_ms,
                        "total_session_ms": total_session_ms,
                        "displayed_count_target": displayed_count_target,
                        "displayed_denominator": displayed_denominator,
                        "norm_target_value": norm_target_value,
                        "hour_of_day": hour_of_day,
                        "time_block": time_block_from_hour(hour_of_day),
                        "day_index": day_index,
                        "language": language,
                        "focus_loss_pre_claim": focus_loss_pre_claim,
                        "reload_count": reload_count,
                        "network_error_count": network_error_count,
                        "quality_flag_fast_report": quality_flag_fast_report,
                        "fraud_flag_critical": 0,
                        "selected_for_payment": selected_for_payment,
                        "payment_amount_eur": payment_amount_eur,
                        "session_started_at": session_started_at.isoformat(),
                        "session_completed_at": session_completed_at.isoformat(),
                        "browser_family": browser,
                        "os_family": os_family,
                        "device_type": "mobile" if os_family in {"iOS", "Android"} else "desktop",
                        "language_changed_during_session": int(rng.random() < 0.03),
                        "consent_panels_opened_count": int(rng.choice([0, 1, 2], p=[0.54, 0.38, 0.08])),
                        "click_count_total": sum(click_count_by_screen.values()),
                        "click_count_by_screen_json": json.dumps(click_count_by_screen, sort_keys=True),
                        "screen_changes_count": 6,
                        "resume_count": int(rng.choice([0, 1], p=[0.93, 0.07])),
                        "network_retry_count": int(rng.choice([0, 1, 2], p=[0.90, 0.08, 0.02])),
                        "was_referred": 0,
                        "referral_depth": 0,
                        "referral_code": stable_code("rf_", session_id, 8),
                        "invited_by_session_id": "",
                        "invited_by_referral_code": "",
                        "referral_source": "",
                        "referral_medium": "",
                        "referral_campaign": "",
                        "referral_landing_path": "",
                        "referral_link_id": "",
                        "shared_any": 0,
                        "share_channel": "",
                    }
                )

                for attempt_index, result_value in enumerate(seen_values, start=1):
                    throws_rows.append(
                        {
                            "throw_id": stable_code("th_", f"{session_id}|{attempt_index}", 10),
                            "session_id": session_id,
                            "root_id": root_id,
                            "series_id": series_id,
                            "experiment_phase": EXPERIMENT_PHASE,
                            "treatment_key": treatment_key,
                            "position_index": position_index,
                            "attempt_index": attempt_index,
                            "result_value": result_value,
                            "reaction_ms": int(rng.lognormal(mean=np.log(900 + 350 * attempt_index), sigma=0.25)),
                            "delivered_at": (
                                session_started_at + timedelta(milliseconds=landing_to_start_ms + consent_total_ms + instructions_visible_ms + comprehension_visible_ms + 500 * attempt_index)
                            ).isoformat(),
                        }
                    )

            final_visible_count = float(sum(visible_window)) if visible_window is not None else np.nan
            series_rows.append(
                {
                    "root_id": root_id,
                    "root_sequence": root_sequence,
                    "root_phase": EXPERIMENT_PHASE,
                    "root_status": "closed",
                    "series_id": series_id,
                    "treatment_key": treatment_key,
                    "treatment_family": treatment_family,
                    "norm_target_value": norm_target_value,
                    "seed_initial_count": SEED_INITIAL_COUNTS[treatment_key],
                    "completed_count": len(positions),
                    "position_counter": len(positions),
                    "max_position_filled": max(positions) if positions else 0,
                    "visible_count_target": final_visible_count,
                    "actual_count_target": final_visible_count,
                    "visible_window_version": len(positions),
                    "actual_window_version": len(positions),
                    "window_size": VISIBLE_WINDOW if visible_window is not None else np.nan,
                }
            )

    sessions = pd.DataFrame(sessions_rows)
    throws = pd.DataFrame(throws_rows)
    series = pd.DataFrame(series_rows)
    return sessions, throws, series


def attach_referrals(sessions: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    ordered = sessions.sort_values(["session_started_at", "session_id"]).reset_index(drop=True)
    shared_pool: list[dict[str, object]] = []

    for index, row in ordered.iterrows():
        share_probability = 0.22 + 0.10 * int(row["reported_high"]) + 0.12 * int(not row["selected_for_payment"])
        shared_any = int(rng.random() < min(share_probability, 0.62))
        ordered.at[index, "shared_any"] = shared_any
        ordered.at[index, "share_channel"] = "whatsapp" if shared_any else ""
        if shared_any:
            shared_pool.append(
                {
                    "session_id": row["session_id"],
                    "referral_code": row["referral_code"],
                    "share_weight": 1.0 + 0.5 * int(row["reported_high"]),
                }
            )

        if index < 30 or not shared_pool or rng.random() >= 0.23:
            continue

        weights = np.array([float(item["share_weight"]) for item in shared_pool], dtype=float)
        weights = weights / weights.sum()
        inviter = shared_pool[int(rng.choice(np.arange(len(shared_pool)), p=weights))]
        ordered.at[index, "was_referred"] = 1
        ordered.at[index, "invited_by_session_id"] = inviter["session_id"]
        ordered.at[index, "invited_by_referral_code"] = inviter["referral_code"]
        ordered.at[index, "referral_source"] = "share"
        ordered.at[index, "referral_medium"] = "whatsapp"
        ordered.at[index, "referral_campaign"] = "vip_raffle"
        ordered.at[index, "referral_landing_path"] = f"/?ref={inviter['referral_code']}&src=whatsapp"
        ordered.at[index, "referral_link_id"] = stable_code(
            "lnk_",
            f"{inviter['session_id']}->{row['session_id']}",
            10,
        )

    referral_depth = {}
    parent_lookup = dict(zip(ordered["session_id"], ordered["invited_by_session_id"]))
    for session_id in ordered["session_id"]:
        depth = 0
        parent_id = parent_lookup.get(session_id)
        while parent_id:
            depth += 1
            parent_id = parent_lookup.get(parent_id, "")
        referral_depth[session_id] = depth
    ordered["referral_depth"] = ordered["session_id"].map(referral_depth).fillna(0).astype(int)
    return ordered


def referrals_frame(sessions: pd.DataFrame) -> pd.DataFrame:
    return sessions[
        [
            "session_id",
            "referral_code",
            "invited_by_session_id",
            "invited_by_referral_code",
            "referral_source",
            "referral_medium",
            "referral_campaign",
            "referral_landing_path",
            "referral_link_id",
            "session_started_at",
            "was_referred",
            "referral_depth",
            "shared_any",
            "share_channel",
        ]
    ].rename(columns={"session_started_at": "referral_arrived_at"})


def main() -> None:
    ensure_directories()
    rng = np.random.default_rng(RANDOM_SEED)

    position_plan = build_position_plan(rng)
    sessions, throws, series = build_series_and_sessions(position_plan, rng)
    sessions = attach_referrals(sessions, rng)
    referrals = referrals_frame(sessions)

    sessions = sessions.sort_values("session_started_at").reset_index(drop=True)
    throws = throws.sort_values(["session_id", "attempt_index"]).reset_index(drop=True)
    series = series.sort_values(["root_sequence", "treatment_key"]).reset_index(drop=True)
    referrals = referrals.sort_values("referral_arrived_at").reset_index(drop=True)

    output_dir = Path(__file__).resolve().parents[1] / "data" / "simulated"
    save_dataframe(sessions, output_dir / DATASETS["sessions"])
    save_dataframe(throws, output_dir / DATASETS["throws"])
    save_dataframe(series, output_dir / DATASETS["series"])
    save_dataframe(position_plan, output_dir / DATASETS["position_plan"])
    save_dataframe(referrals, output_dir / DATASETS["referrals"])

    append_log(
        "simulate_data.log",
        (
            f"Generated {len(sessions)} sessions, {len(throws)} throws, "
            f"{len(series)} series rows and {len(position_plan)} position-plan rows."
        ),
    )
    print("Simulation completed.")
    print(f"Sessions: {len(sessions)} / expected {VALID_COMPLETED_SESSIONS}")


if __name__ == "__main__":
    main()
