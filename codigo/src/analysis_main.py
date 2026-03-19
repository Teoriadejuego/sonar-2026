from __future__ import annotations

import json

import pandas as pd
import statsmodels.formula.api as smf

from config_analysis import (
    DATA_DIR,
    EARLY_SEGMENT,
    FULL_SEGMENT,
    LATE_SEGMENT,
    MAIN_COMPARISON,
)
from utils import (
    append_log,
    bootstrap_cluster_difference,
    ensure_directories,
    save_dataframe,
    save_markdown_table,
)


def load_analysis_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sonar_analysis_dataset_simulated.csv")


def restricted_window(frame: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    return frame.loc[frame["position_index"].between(start, end)].copy()


def diff_in_means_row(
    frame: pd.DataFrame,
    outcome: str,
    label: str,
    start: int,
    end: int,
) -> dict[str, object]:
    sample = restricted_window(frame, start, end)
    high_treatment, low_treatment = MAIN_COMPARISON
    high = sample.loc[sample["treatment_key"] == high_treatment, outcome]
    low = sample.loc[sample["treatment_key"] == low_treatment, outcome]
    estimate = float(high.mean() - low.mean())
    ci_low, ci_high = bootstrap_cluster_difference(
        sample,
        outcome_column=outcome,
        high_treatment=high_treatment,
        low_treatment=low_treatment,
    )
    return {
        "specification": label,
        "window": f"{start}-{end}",
        "model_type": "Difference in means",
        "estimate": estimate,
        "std_error": "",
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "p_value": "",
        "n_obs": int(len(sample)),
        "n_roots": int(sample["root_id"].nunique()),
    }


def regression_row(
    frame: pd.DataFrame,
    outcome: str,
    label: str,
    start: int,
    end: int,
    with_truth_control: bool,
) -> dict[str, object]:
    sample = restricted_window(frame, start, end)
    sample = sample.loc[sample["treatment_key"].isin(list(MAIN_COMPARISON))].copy()
    sample["high_seed"] = (sample["treatment_key"] == MAIN_COMPARISON[0]).astype(int)
    formula = f"{outcome} ~ high_seed + position_index + I(position_index ** 2) + I(position_index ** 3) + C(root_id)"
    if with_truth_control:
        formula += " + C(true_first_result)"
    result = smf.ols(formula=formula, data=sample).fit(
        cov_type="cluster",
        cov_kwds={"groups": sample["root_id"]},
    )
    return {
        "specification": label,
        "window": f"{start}-{end}",
        "model_type": "LPM + root FE" if not with_truth_control else "LPM + root FE + truth",
        "estimate": float(result.params["high_seed"]),
        "std_error": float(result.bse["high_seed"]),
        "ci_lower": float(result.conf_int().loc["high_seed", 0]),
        "ci_upper": float(result.conf_int().loc["high_seed", 1]),
        "p_value": float(result.pvalues["high_seed"]),
        "n_obs": int(result.nobs),
        "n_roots": int(sample["root_id"].nunique()),
    }


def build_table_1(frame: pd.DataFrame) -> pd.DataFrame:
    table = (
        frame.groupby("treatment_key", as_index=False)
        .agg(
            n_sessions=("session_id", "count"),
            reported_6_mean=("reported_6", "mean"),
            reported_5_mean=("reported_5", "mean"),
            is_honest_mean=("is_honest", "mean"),
            lie_amount_mean=("lie_amount", "mean"),
            relative_lie_mean=("relative_lie", "mean"),
            reroll_count_mean=("reroll_count", "mean"),
            true_first_result_mean=("true_first_result", "mean"),
            report_rt_ms_mean=("report_rt_ms", "mean"),
            total_session_ms_mean=("total_session_ms", "mean"),
            referred_share=("was_referred", "mean"),
        )
        .sort_values("treatment_key")
    )
    numeric_cols = [column for column in table.columns if column != "treatment_key"]
    table[numeric_cols] = table[numeric_cols].round(4)
    return table


def build_main_results(frame: pd.DataFrame, outcome: str) -> pd.DataFrame:
    seed_sample = frame.loc[frame["treatment_key"].isin(list(MAIN_COMPARISON))].copy()
    early_start, early_end = EARLY_SEGMENT
    late_start, late_end = LATE_SEGMENT
    full_start, full_end = FULL_SEGMENT
    rows = [
        diff_in_means_row(seed_sample, outcome, "Main sample", full_start, full_end),
        diff_in_means_row(seed_sample, outcome, "Early positions", early_start, early_end),
        diff_in_means_row(seed_sample, outcome, "Late positions", late_start, late_end),
        regression_row(seed_sample, outcome, "Model B", full_start, full_end, with_truth_control=False),
        regression_row(seed_sample, outcome, "Model B early", early_start, early_end, with_truth_control=False),
        regression_row(seed_sample, outcome, "Model B late", late_start, late_end, with_truth_control=False),
        regression_row(seed_sample, outcome, "Model C", full_start, full_end, with_truth_control=True),
        regression_row(seed_sample, outcome, "Model C early", early_start, early_end, with_truth_control=True),
        regression_row(seed_sample, outcome, "Model C late", late_start, late_end, with_truth_control=True),
    ]
    result = pd.DataFrame(rows)
    float_cols = ["estimate", "std_error", "ci_lower", "ci_upper", "p_value"]
    for column in float_cols:
        result[column] = result[column].replace("", pd.NA)
    return result.round(4)


def main() -> None:
    ensure_directories()
    analysis = load_analysis_data()

    table_1 = build_table_1(analysis)
    table_2 = build_main_results(analysis, "reported_6")
    table_3 = build_main_results(analysis, "lie_amount")

    save_dataframe(table_1, analysis_path("table_1_descriptives_by_treatment.csv"))
    save_markdown_table(table_1, analysis_path("table_1_descriptives_by_treatment.md"), "Table 1")
    save_dataframe(table_2, analysis_path("table_2_main_results_reported_6.csv"))
    save_markdown_table(table_2, analysis_path("table_2_main_results_reported_6.md"), "Table 2")
    save_dataframe(table_3, analysis_path("table_3_main_results_lie_amount.csv"))
    save_markdown_table(table_3, analysis_path("table_3_main_results_lie_amount.md"), "Table 3")

    summary = {
        "primary_outcome": "reported_6",
        "main_comparison": list(MAIN_COMPARISON),
        "full_sample_difference": float(
            table_2.loc[table_2["specification"] == "Main sample", "estimate"].iloc[0]
        ),
        "early_difference": float(
            table_2.loc[table_2["specification"] == "Early positions", "estimate"].iloc[0]
        ),
        "late_difference": float(
            table_2.loc[table_2["specification"] == "Late positions", "estimate"].iloc[0]
        ),
    }
    analysis_path("main_results_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    append_log("analysis_main.log", "Generated Tables 1-3 and main result summary.")
    print("Main analysis completed.")


def analysis_path(file_name: str):
    from config_analysis import TABLES_DIR

    return TABLES_DIR / file_name


if __name__ == "__main__":
    main()
