from __future__ import annotations

import json

import pandas as pd

from utils import (
    DATA_DIR,
    HIGH_TREATMENT_KEY,
    LOW_TREATMENT_KEY,
    LOGS_DIR,
    TABLES_DIR,
    exact_counts,
    load_config,
    save_dataframe,
    validation_row,
)


def run_validation() -> pd.DataFrame:
    config = load_config()
    sessions = pd.read_csv(DATA_DIR / "simulated_sessions.csv")
    series = pd.read_csv(DATA_DIR / "simulated_series.csv")
    position_plan = pd.read_csv(DATA_DIR / "simulated_position_plan.csv")

    expected_treatment_counts = exact_counts(
        int(config["participants_valid_completed"]),
        config["treatment_weights"],
    )
    expected_robot_counts = exact_counts(
        int(config["participants_valid_completed"]),
        config["robot_mix"],
    )

    checks: list[dict] = []
    checks.append(
        validation_row(
            "n_total_valid_completed",
            len(sessions) == int(config["participants_valid_completed"]),
            f"observed={len(sessions)} expected={config['participants_valid_completed']}",
        )
    )

    observed_treatment_counts = sessions["treatment_key"].value_counts().to_dict()
    treatment_ok = all(
        observed_treatment_counts.get(key, 0) == expected_treatment_counts[key]
        for key in expected_treatment_counts
    )
    checks.append(
        validation_row(
            "treatment_proportions_exact",
            treatment_ok,
            json.dumps(observed_treatment_counts, ensure_ascii=False),
        )
    )

    observed_robot_counts = sessions["robot_type"].value_counts().to_dict()
    robot_ok = all(
        abs(observed_robot_counts.get(key, 0) - expected_robot_counts[key]) <= 1
        for key in expected_robot_counts
    )
    checks.append(
        validation_row(
            "robot_mix_approximately_correct",
            robot_ok,
            json.dumps(observed_robot_counts, ensure_ascii=False),
        )
    )

    mirror_truth_groups = (
        sessions.groupby(["root_id", "position_index"])["true_first_result"].nunique().max()
    )
    checks.append(
        validation_row(
            "mirror_positions_share_same_truth",
            int(mirror_truth_groups) == 1,
            f"max_unique_truths_per_mirror_position={mirror_truth_groups}",
        )
    )

    type_a = sessions[sessions["robot_type"] == "type_a_norm_imitator"]
    type_a_seed_low = type_a.loc[
        type_a["treatment_key"] == LOW_TREATMENT_KEY,
        "reported_6",
    ].mean()
    type_a_seed_high = type_a.loc[
        type_a["treatment_key"] == HIGH_TREATMENT_KEY,
        "reported_6",
    ].mean()
    checks.append(
        validation_row(
            "type_a_reports_more_6_in_seed_high_than_seed_low",
            bool(type_a_seed_high > type_a_seed_low),
            f"seed_high={type_a_seed_high:.3f} seed_low={type_a_seed_low:.3f}",
        )
    )

    type_c = sessions[sessions["robot_type"] == "type_c_prudent_five"]
    c_low_truth = type_c[type_c["true_first_result"].isin([1, 2])]
    c_high_truth = type_c[~type_c["true_first_result"].isin([1, 2])]
    type_c_ok = bool((c_low_truth["reported_value"] == 5).all() and (c_high_truth["reported_value"] == c_high_truth["true_first_result"]).all())
    checks.append(
        validation_row(
            "type_c_generates_prudent_five_only_for_truth_1_or_2",
            type_c_ok,
            f"low_truth_rows={len(c_low_truth)} high_truth_rows={len(c_high_truth)}",
        )
    )

    type_d = sessions[sessions["robot_type"] == "type_d_honest"]
    checks.append(
        validation_row(
            "type_d_always_honest",
            bool((type_d["is_honest"] == 1).all()),
            f"dishonest_rows={(type_d['is_honest'] == 0).sum()}",
        )
    )

    treatment_means = sessions.groupby("treatment_key")["reported_6"].mean().to_dict()
    treatment_diff = max(treatment_means.values()) - min(treatment_means.values())
    checks.append(
        validation_row(
            "aggregate_reports_differ_by_treatment",
            bool(treatment_diff > 0.03),
            json.dumps(treatment_means, ensure_ascii=False),
        )
    )

    control_mean = treatment_means.get("control", 0.0)
    checks.append(
        validation_row(
            "series_evolution_seed_high_above_seed_low_with_control_reference",
            bool(
                treatment_means.get(HIGH_TREATMENT_KEY, 0.0)
                > treatment_means.get(LOW_TREATMENT_KEY, 1.0)
                and treatment_means.get(HIGH_TREATMENT_KEY, 0.0) > control_mean
            ),
            json.dumps(treatment_means, ensure_ascii=False),
        )
    )

    mirrored_from_plan = sessions.merge(
        position_plan[position_plan["attempt_index"] == 1][["root_id", "position_index", "result_value"]],
        on=["root_id", "position_index"],
        how="left",
    )
    checks.append(
        validation_row(
            "position_plan_matches_session_truth",
            bool((mirrored_from_plan["true_first_result"] == mirrored_from_plan["result_value"]).all()),
            f"mismatches={(mirrored_from_plan['true_first_result'] != mirrored_from_plan['result_value']).sum()}",
        )
    )

    checks.append(
        validation_row(
            "series_outputs_generated",
            bool(not series.empty and not position_plan.empty),
            f"series_rows={len(series)} position_plan_rows={len(position_plan)}",
        )
    )

    backend_flow_path = DATA_DIR / "backend_flow_sessions.csv"
    backend_ok = backend_flow_path.exists()
    detail = "backend_flow_sessions.csv missing"
    if backend_ok:
        backend_rows = pd.read_csv(backend_flow_path)
        backend_ok = len(backend_rows) > 0
        detail = f"backend_rows={len(backend_rows)}"
    checks.append(validation_row("backend_flow_outputs_generated", backend_ok, detail))

    validation_df = pd.DataFrame(checks)
    save_dataframe(validation_df, TABLES_DIR / "table_4_validation_checks.csv")
    (LOGS_DIR / "validation_summary.json").write_text(
        validation_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8",
    )
    return validation_df


if __name__ == "__main__":
    validation = run_validation()
    print(validation[["check_name", "status", "detail"]].to_string(index=False))
