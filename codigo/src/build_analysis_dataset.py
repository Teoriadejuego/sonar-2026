from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config_analysis import DATA_DIR, RANDOM_SEED, SERIES_MAX_LENGTH
from utils import append_log, ensure_directories, position_segment, save_dataframe


def main() -> None:
    ensure_directories()
    sessions = pd.read_csv(DATA_DIR / "sonar_sessions_simulated.csv")
    throws = pd.read_csv(DATA_DIR / "sonar_throws_simulated.csv")
    referrals = pd.read_csv(DATA_DIR / "sonar_referrals_simulated.csv")

    throws_summary = (
        throws.groupby("session_id")
        .agg(
            seen_values_csv=("result_value", lambda values: ",".join(str(int(item)) for item in values)),
            seen_any_5=("result_value", lambda values: int(5 in set(values))),
            seen_any_6=("result_value", lambda values: int(6 in set(values))),
            mean_throw_reaction_ms=("reaction_ms", "mean"),
        )
        .reset_index()
    )

    analysis = sessions.merge(throws_summary, on="session_id", how="left", validate="one_to_one")
    analysis = analysis.merge(
        referrals[
            [
                "session_id",
                "was_referred",
                "referral_depth",
                "shared_any",
                "share_channel",
            ]
        ],
        on="session_id",
        how="left",
        suffixes=("", "_ref"),
    )

    analysis["position_segment"] = analysis["position_index"].map(position_segment)
    analysis["series_progress_share"] = analysis["position_index"] / SERIES_MAX_LENGTH
    analysis["treated_high_norm"] = (analysis["treatment_key"] == "seed_83").astype(int)
    analysis["treatment_seed_level"] = analysis["treatment_key"].map(
        {"control": 0, "seed_17": 17, "seed_83": 83}
    )
    analysis["reported_matches_max_seen"] = (
        analysis["reported_value"] == analysis["max_seen_value"]
    ).astype(int)
    analysis["report_gap_from_max_seen"] = analysis["max_seen_value"] - analysis["reported_value"]
    analysis["report_gap_from_last_seen"] = analysis["last_seen_value"] - analysis["reported_value"]
    analysis["lie_to_six"] = (
        (analysis["reported_value"] == 6) & (analysis["true_first_result"] != 6)
    ).astype(int)
    analysis["overreport_amount"] = (analysis["reported_value"] - analysis["true_first_result"]).clip(lower=0)
    analysis["multiple_focus_loss"] = (
        analysis["focus_loss_pre_claim"] + (analysis["reload_count"] >= 1).astype(int) >= 2
    ).astype(int)
    analysis["network_error_any"] = (analysis["network_error_count"] > 0).astype(int)
    analysis["used_info_modal"] = (analysis["consent_panels_opened_count"] > 0).astype(int)
    analysis["analysis_seed"] = RANDOM_SEED
    analysis["root_position_id"] = analysis["root_id"] + "_p" + analysis["position_index"].astype(str)
    analysis["hour_bin"] = analysis["hour_of_day"].astype(str).str.zfill(2)
    analysis["session_rank"] = analysis["session_started_at"].rank(method="first").astype(int)
    analysis["was_referred"] = analysis["was_referred"].fillna(0).astype(int)
    analysis["referral_depth"] = analysis["referral_depth"].fillna(0).astype(int)
    analysis["shared_any"] = analysis["shared_any"].fillna(0).astype(int)
    analysis["share_channel"] = analysis["share_channel"].fillna("")
    analysis["seen_values_count"] = analysis["seen_values_csv"].fillna("").map(
        lambda text: 0 if not text else len(str(text).split(","))
    )
    analysis["reported_unseen"] = analysis["reported_unseen"].astype(int)
    analysis["quality_flag_fast_report"] = analysis["quality_flag_fast_report"].astype(int)
    analysis["fraud_flag_critical"] = analysis["fraud_flag_critical"].astype(int)
    analysis["selected_for_payment"] = analysis["selected_for_payment"].astype(int)

    output_path = DATA_DIR / "sonar_analysis_dataset_simulated.csv"
    save_dataframe(analysis, output_path)

    manifest = {
        "dataset": "sonar_analysis_dataset_simulated.csv",
        "rows": int(len(analysis)),
        "columns": analysis.columns.tolist(),
        "source_files": [
            "sonar_sessions_simulated.csv",
            "sonar_throws_simulated.csv",
            "sonar_referrals_simulated.csv",
        ],
    }
    (DATA_DIR / "sonar_analysis_dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    append_log(
        "build_analysis_dataset.log",
        f"Built analysis dataset with {len(analysis)} rows and {len(analysis.columns)} columns.",
    )
    print(output_path)


if __name__ == "__main__":
    main()
