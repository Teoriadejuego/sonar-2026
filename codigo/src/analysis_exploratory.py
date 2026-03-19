from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf

from config_analysis import DATA_DIR, EARLY_SEGMENT, LATE_SEGMENT, MAIN_COMPARISON
from utils import append_log, ensure_directories, save_dataframe, save_markdown_table


def load_analysis_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sonar_analysis_dataset_simulated.csv")


def model_row(frame: pd.DataFrame, outcome: str, label: str) -> dict[str, object]:
    sample = frame.loc[frame["treatment_key"].isin(list(MAIN_COMPARISON))].copy()
    sample["high_seed"] = (sample["treatment_key"] == MAIN_COMPARISON[0]).astype(int)
    result = smf.ols(
        formula=f"{outcome} ~ high_seed + position_index + I(position_index ** 2) + I(position_index ** 3) + C(root_id) + C(true_first_result)",
        data=sample,
    ).fit(cov_type="cluster", cov_kwds={"groups": sample["root_id"]})
    return {
        "specification": label,
        "estimate": float(result.params["high_seed"]),
        "std_error": float(result.bse["high_seed"]),
        "ci_lower": float(result.conf_int().loc["high_seed", 0]),
        "ci_upper": float(result.conf_int().loc["high_seed", 1]),
        "p_value": float(result.pvalues["high_seed"]),
        "n_obs": int(result.nobs),
    }


def table_4_reported_5(frame: pd.DataFrame) -> pd.DataFrame:
    early_start, early_end = EARLY_SEGMENT
    late_start, late_end = LATE_SEGMENT
    early = frame.loc[frame["position_index"].between(early_start, early_end)].copy()
    late = frame.loc[frame["position_index"].between(late_start, late_end)].copy()
    rows = [
        model_row(frame, "reported_5", "Full sample"),
        model_row(early, "reported_5", f"Positions {early_start}-{early_end}"),
        model_row(late, "reported_5", f"Positions {late_start}-{late_end}"),
        model_row(frame, "reported_5_or_6", "Full sample: reported 5 or 6"),
    ]
    return pd.DataFrame(rows).round(4)


def build_extras(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    heatmap = (
        frame.groupby(["true_first_result", "reported_value"], as_index=False)
        .size()
        .pivot(index="true_first_result", columns="reported_value", values="size")
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    time_block_summary = (
        frame.groupby(["time_block", "treatment_key"], as_index=False)
        .agg(
            reported_6_mean=("reported_6", "mean"),
            reported_5_mean=("reported_5", "mean"),
            is_honest_mean=("is_honest", "mean"),
            report_rt_ms_mean=("report_rt_ms", "mean"),
        )
        .round(4)
    )
    reroll_summary = (
        frame.groupby("treatment_key", as_index=False)
        .agg(
            reroll_count_mean=("reroll_count", "mean"),
            reported_matches_any_seen_mean=("reported_matches_any_seen", "mean"),
            reported_matches_last_mean=("reported_matches_last", "mean"),
            reported_matches_max_seen_mean=("reported_matches_max_seen", "mean"),
        )
        .round(4)
    )
    referral_summary = (
        frame.groupby("was_referred", as_index=False)
        .agg(
            n_sessions=("session_id", "count"),
            reported_6_mean=("reported_6", "mean"),
            lie_amount_mean=("lie_amount", "mean"),
            is_honest_mean=("is_honest", "mean"),
        )
        .round(4)
    )
    return {
        "exploratory_heatmap_truth_report.csv": heatmap,
        "exploratory_time_block_summary.csv": time_block_summary,
        "exploratory_reroll_summary.csv": reroll_summary,
        "exploratory_referral_summary.csv": referral_summary,
    }


def output_path(file_name: str):
    from config_analysis import TABLES_DIR

    return TABLES_DIR / file_name


def main() -> None:
    ensure_directories()
    analysis = load_analysis_data()
    table_4 = table_4_reported_5(analysis)
    save_dataframe(table_4, output_path("table_4_exploratory_reported_5.csv"))
    save_markdown_table(table_4, output_path("table_4_exploratory_reported_5.md"), "Table 4")

    for file_name, frame in build_extras(analysis).items():
        save_dataframe(frame, output_path(file_name))

    append_log("analysis_exploratory.log", "Generated Table 4 and exploratory summaries.")
    print("Exploratory analysis completed.")


if __name__ == "__main__":
    main()
