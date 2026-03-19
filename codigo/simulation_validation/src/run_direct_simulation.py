from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from utils import (
    DATA_DIR,
    LOGS_DIR,
    MAX_ATTEMPTS,
    PARTICIPANT_LIMIT,
    PHASE_1_MAIN,
    WINDOW_SIZE,
    RootState,
    SeriesState,
    append_window,
    assignment_weights_for_phase,
    balanced_sequence,
    build_root_state,
    displayed_message,
    ensure_directories,
    hour_of_day,
    load_config,
    make_population_table,
    payout_amount_for_claim,
    payout_eligible,
    reaction_time_ms,
    report_value_for_robot,
    sample_reroll_count,
    save_dataframe,
    time_block_from_hour,
    treatment_config,
)


def allocate_root_if_needed(
    roots: list[RootState],
    *,
    treatment_weights: dict[str, float],
    config: dict,
) -> RootState:
    if roots and roots[-1].closed_reason is None:
        return roots[-1]
    root_sequence = len(roots) + 1
    root = build_root_state(
        root_sequence=root_sequence,
        phase_key=config["phase_key"],
        treatment_weights=treatment_weights,
        participant_limit=int(config["series_participant_limit"]),
        window_size=int(config["window_size"]),
    )
    roots.append(root)
    return root


def maybe_close_root(root: RootState, participant_limit: int) -> None:
    if any(
        series.completed_count >= participant_limit
        for series in root.series_by_treatment.values()
    ):
        root.closed_reason = "participant_limit"


def series_snapshot(series: SeriesState) -> dict[str, int | None]:
    if series.treatment_family == "control":
        return {
            "displayed_count_target": None,
            "displayed_denominator": None,
            "norm_target_value": None,
        }
    return {
        "displayed_count_target": series.visible_count_target,
        "displayed_denominator": series.sample_size,
        "norm_target_value": series.norm_target_value,
    }


def simulate_direct_dataset() -> dict[str, Path]:
    config = load_config()
    ensure_directories()
    rng = random.Random(config["random_seed"])
    total_participants = int(config["participants_valid_completed"])
    context_config = config["context"]
    robot_behavior = config["robot_behavior"]
    treatment_weights = assignment_weights_for_phase(PHASE_1_MAIN)
    treatment_targets = {
        key: int(total_participants * weight)
        for key, weight in treatment_weights.items()
    }
    treatment_targets["control"] = total_participants - (
        treatment_targets["seed_17"] + treatment_targets["seed_83"]
    )
    treatment_progress = {key: 0 for key in treatment_targets}

    population = make_population_table(config)
    save_dataframe(population, DATA_DIR / "robot_population.csv")

    roots: list[RootState] = []
    direct_rows: list[dict] = []
    series_rows: list[dict] = []
    position_plan_rows: list[dict] = []
    referral_pool: list[dict[str, int | str]] = []

    base_started_at = datetime(2026, 6, 12, 15, 0, tzinfo=UTC).replace(tzinfo=None)

    for participant_index, person in population.iterrows():
        root = allocate_root_if_needed(
            roots,
            treatment_weights=treatment_weights,
            config=config,
        )
        series = None
        if root.closed_reason is None:
            candidates = [
                item
                for item in root.series_by_treatment.values()
                if item.position_counter < item.participant_limit
                and treatment_progress[item.treatment_key] < treatment_targets[item.treatment_key]
            ]
            if candidates:
                series = min(
                    candidates,
                    key=lambda item: (
                        item.position_counter / max(item.assignment_weight, 0.0001),
                        item.treatment_key,
                    ),
                )
        if series is None:
            if roots:
                roots[-1].closed_reason = roots[-1].closed_reason or "participant_limit"
            root = allocate_root_if_needed(
                roots,
                treatment_weights=treatment_weights,
                config=config,
            )
            series = min(
                [
                    item
                    for item in root.series_by_treatment.values()
                    if treatment_progress[item.treatment_key] < treatment_targets[item.treatment_key]
                ],
                key=lambda item: (
                    item.position_counter / max(item.assignment_weight, 0.0001),
                    item.treatment_key,
                ),
            )

        series.position_counter += 1
        treatment_progress[series.treatment_key] += 1
        position_index = series.position_counter

        deck_attempts = {
            attempt_index: balanced_sequence(
                root.root_seed,
                attempt_index,
                PARTICIPANT_LIMIT,
            )[position_index - 1]
            for attempt_index in range(1, MAX_ATTEMPTS + 1)
        }
        snapshot = series_snapshot(series)
        true_first_result = deck_attempts[1]
        reroll_count = sample_reroll_count(
            robot_type=person["robot_type"],
            robot_behavior=robot_behavior,
            rng=rng,
        )
        rerolls_visible = [
            deck_attempts[attempt_index]
            for attempt_index in range(2, 2 + reroll_count)
        ]
        seen_values = [true_first_result, *rerolls_visible]
        reported_value = report_value_for_robot(
            robot_type=person["robot_type"],
            true_first_result=true_first_result,
            treatment_key=series.treatment_key,
            displayed_count_target=snapshot["displayed_count_target"],
            displayed_denominator=snapshot["displayed_denominator"],
            rng=rng,
            robot_behavior=robot_behavior,
        )
        visible_message = displayed_message(
            treatment_key=series.treatment_key,
            displayed_count_target=snapshot["displayed_count_target"],
            denominator=snapshot["displayed_denominator"],
            target_value=snapshot["norm_target_value"],
        )
        payment_eligible = payout_eligible(root.root_seed, position_index)
        payment_amount = payout_amount_for_claim(reported_value, payment_eligible)
        focus_loss_pre_claim = rng.random() < context_config["focus_loss_rate"]
        reload_count = 1 if rng.random() < context_config["reload_rate"] else 0
        network_error_count = 1 if rng.random() < context_config["network_error_rate"] else 0
        technical_error_flag = rng.random() < context_config["technical_error_rate"]
        hour = hour_of_day(participant_index, rng)
        report_rt_ms = reaction_time_ms(rng, lower=900, upper=4200)
        game_decision_rt_ms = reaction_time_ms(rng, lower=1600, upper=6200)
        total_session_ms = reaction_time_ms(rng, lower=18000, upper=90000)
        created_at = base_started_at + timedelta(seconds=participant_index * rng.uniform(0.6, 2.8))
        claim_at = created_at + timedelta(milliseconds=total_session_ms)

        series.completed_count += 1
        target_value = series.norm_target_value
        if target_value is not None and reported_value == target_value:
            series.full_target_streak += 1
        else:
            series.full_target_streak = 0
        append_window(series, window_kind="actual", value=reported_value, window_size=WINDOW_SIZE)
        append_window(series, window_kind="visible", value=reported_value, window_size=WINDOW_SIZE)
        maybe_close_root(root, int(config["series_participant_limit"]))

        was_referred = bool(referral_pool) and rng.random() < context_config["referral_rate"]
        invited_by_session_id = None
        invited_by_robot_id = None
        referral_depth = 0
        if was_referred:
            referrer = rng.choice(referral_pool)
            invited_by_session_id = str(referrer["session_id"])
            invited_by_robot_id = str(referrer["robot_id"])
            referral_depth = int(referrer["referral_depth"]) + 1

        quality_flags = []
        if report_rt_ms < 1100:
            quality_flags.append("fast_report")
        if focus_loss_pre_claim:
            quality_flags.append("focus_loss_pre_claim")
        if reload_count:
            quality_flags.append("reload")
        if network_error_count:
            quality_flags.append("network_error")

        row = {
            "session_id": f"sim_session_{participant_index + 1:05d}",
            "robot_id": person["robot_id"],
            "robot_type": person["robot_type"],
            "robot_label": person["robot_label"],
            "root_id": root.root_id,
            "series_id": series.series_id,
            "treatment_key": series.treatment_key,
            "treatment_family": series.treatment_family,
            "position_index": position_index,
            "true_first_result": true_first_result,
            "reported_value": reported_value,
            "reported_6": int(reported_value == 6),
            "reported_5": int(reported_value == 5),
            "reported_high": int(reported_value >= 5),
            "is_honest": int(reported_value == true_first_result),
            "lie_amount": reported_value - true_first_result,
            "opportunity_to_lie": 6 - true_first_result,
            "relative_lie": round(
                (reported_value - true_first_result) / max(6 - true_first_result, 1),
                4,
            ),
            "displayed_count_target": snapshot["displayed_count_target"],
            "displayed_denominator": snapshot["displayed_denominator"],
            "norm_target_value": snapshot["norm_target_value"],
            "visible_message": visible_message,
            "reroll_count": reroll_count,
            "used_any_reroll": int(reroll_count > 0),
            "all_values_seen_json": json.dumps(seen_values),
            "max_seen_value": max(seen_values),
            "last_seen_value": seen_values[-1],
            "reported_matches_any_seen": int(reported_value in seen_values),
            "payment_eligible": int(payment_eligible),
            "payment_amount": payment_amount,
            "experiment_phase": PHASE_1_MAIN,
            "language": person["language"],
            "hour_of_day": hour,
            "time_block": time_block_from_hour(hour),
            "day_index": 1 + (participant_index // 1200),
            "was_referred": int(was_referred),
            "invited_by_session_id": invited_by_session_id,
            "invited_by_robot_id": invited_by_robot_id,
            "referral_depth": referral_depth,
            "focus_loss_pre_claim": int(focus_loss_pre_claim),
            "reload_count": reload_count,
            "network_error_count": network_error_count,
            "quality_flags_json": json.dumps(sorted(set(quality_flags))),
            "fraud_flag_critical": 0,
            "technical_error_flag": int(technical_error_flag),
            "report_rt_ms": report_rt_ms,
            "game_decision_rt_ms": game_decision_rt_ms,
            "total_session_ms": total_session_ms,
            "created_at_utc": created_at.isoformat(),
            "claim_at_utc": claim_at.isoformat(),
            "sequence_order": participant_index + 1,
            "final_visible_snapshot_json": json.dumps(
                {
                    "message": visible_message,
                    "displayed_count_target": snapshot["displayed_count_target"],
                    "displayed_denominator": snapshot["displayed_denominator"],
                    "norm_target_value": snapshot["norm_target_value"],
                    "first_result": true_first_result,
                    "last_seen_value": seen_values[-1],
                    "rerolls_visible": rerolls_visible,
                    "final_state": "completed_win" if payment_eligible else "completed_no_win",
                }
            ),
        }
        direct_rows.append(row)
        referral_pool.append(
            {
                "session_id": row["session_id"],
                "robot_id": row["robot_id"],
                "referral_depth": referral_depth,
            }
        )

    for root in roots:
        for series in root.series_by_treatment.values():
            series_rows.append(
                {
                    "root_id": root.root_id,
                    "root_sequence": root.root_sequence,
                    "series_id": series.series_id,
                    "treatment_key": series.treatment_key,
                    "treatment_family": series.treatment_family,
                    "norm_target_value": series.norm_target_value,
                    "position_counter": series.position_counter,
                    "completed_count": series.completed_count,
                    "visible_count_target": series.visible_count_target,
                    "actual_count_target": series.actual_count_target,
                    "visible_window_size": len(series.visible_window),
                    "actual_window_size": len(series.actual_window),
                    "full_target_streak": series.full_target_streak,
                    "root_closed_reason": root.closed_reason,
                }
            )
        for position_index in range(1, PARTICIPANT_LIMIT + 1):
            payment_flag = payout_eligible(root.root_seed, position_index)
            for attempt_index in range(1, MAX_ATTEMPTS + 1):
                position_plan_rows.append(
                    {
                        "root_id": root.root_id,
                        "root_sequence": root.root_sequence,
                        "position_index": position_index,
                        "attempt_index": attempt_index,
                        "result_value": balanced_sequence(
                            root.root_seed,
                            attempt_index,
                            PARTICIPANT_LIMIT,
                        )[position_index - 1],
                        "payout_eligible": int(payment_flag),
                    }
                )

    sessions_df = pd.DataFrame(direct_rows)
    series_df = pd.DataFrame(series_rows)
    position_plan_df = pd.DataFrame(position_plan_rows)

    save_dataframe(sessions_df, DATA_DIR / "simulated_sessions.csv")
    save_dataframe(series_df, DATA_DIR / "simulated_series.csv")
    save_dataframe(position_plan_df, DATA_DIR / "simulated_position_plan.csv")

    summary = {
        "participants": int(len(sessions_df)),
        "treatment_counts": sessions_df["treatment_key"].value_counts().sort_index().to_dict(),
        "robot_counts": sessions_df["robot_type"].value_counts().sort_index().to_dict(),
        "roots_used": int(series_df["root_id"].nunique()),
        "winners": int(sessions_df["payment_eligible"].sum()),
        "total_prize_amount_eur": round(sessions_df["payment_amount"].sum() / 100, 2),
    }
    (LOGS_DIR / "run_direct_simulation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "sessions": DATA_DIR / "simulated_sessions.csv",
        "series": DATA_DIR / "simulated_series.csv",
        "position_plan": DATA_DIR / "simulated_position_plan.csv",
    }


if __name__ == "__main__":
    output_paths = simulate_direct_dataset()
    print(
        json.dumps(
            {key: str(value) for key, value in output_paths.items()},
            indent=2,
            ensure_ascii=False,
        )
    )
