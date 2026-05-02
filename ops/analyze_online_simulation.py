from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats


sns.set_theme(style="whitegrid", context="talk")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analiza una corrida de simulacion online de SONAR.",
    )
    parser.add_argument("--input-dir", required=True)
    return parser.parse_args()


def proportion_confidence_interval(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    se = (p * (1 - p) / total) ** 0.5
    margin = 1.96 * se
    return max(0.0, p - margin), min(1.0, p + margin)


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_required_data_check(df: pd.DataFrame) -> dict[str, bool]:
    required_columns = [
        "bracelet_id",
        "session_id",
        "treatment_key",
        "displayed_count_target",
        "displayed_denominator",
        "first_result_value",
        "reported_value",
        "lied",
        "lie_probability",
        "selected_for_payment",
        "payout_amount_cents",
        "access_status",
        "roll_status",
        "prepare_status",
        "submit_status",
    ]
    return {column: column in df.columns for column in required_columns}


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    figures_dir = input_dir / "figures"
    rows_path = input_dir / "simulation_rows.csv"
    summary_path = input_dir / "summary.json"

    if not rows_path.exists():
        raise FileNotFoundError(f"No existe {rows_path}")

    df = pd.read_csv(rows_path)
    successful = df[df["success"] == True].copy()  # noqa: E712
    successful["reported_6"] = (successful["reported_value"] == 6).astype(int)
    successful["actual_6"] = (successful["first_result_value"] == 6).astype(int)
    successful["reported_value"] = successful["reported_value"].astype("Int64")
    successful["first_result_value"] = successful["first_result_value"].astype("Int64")

    if successful.empty:
        raise RuntimeError("No hay sesiones exitosas para analizar.")

    # Figure 1: actual dice outcomes
    actual_counts = (
        successful["first_result_value"]
        .value_counts()
        .reindex([1, 2, 3, 4, 5, 6], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(
        x=actual_counts.index.astype(str),
        y=actual_counts.values,
        color="black",
        ax=ax,
    )
    ax.set_title("Resultados reales del dado")
    ax.set_xlabel("Valor real de la primera tirada")
    ax.set_ylabel("Frecuencia")
    save_figure(fig, figures_dir / "figure_actual_dice_distribution.png")

    # Figure 2: reported outcomes
    reported_counts = (
        successful["reported_value"]
        .value_counts()
        .reindex([1, 2, 3, 4, 5, 6], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(
        reported_counts.index.astype(str),
        reported_counts.values,
        color=["#1a1a1a" if value != 6 else "#c0392b" for value in reported_counts.index],
    )
    ax.set_title("Valores reportados por los sujetos simulados")
    ax.set_xlabel("Valor reportado")
    ax.set_ylabel("Frecuencia")
    save_figure(fig, figures_dir / "figure_reported_distribution.png")

    # Figure 3: treatment x actual result heatmap
    heatmap = (
        successful.pivot_table(
            index="treatment_key",
            columns="first_result_value",
            values="session_id",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(index=["control", "seed_low", "seed_high"], fill_value=0)
        .reindex(columns=[1, 2, 3, 4, 5, 6], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(heatmap, annot=True, fmt="d", cmap="Greys", cbar=False, ax=ax)
    ax.set_title("Tratamiento asignado y resultado real obtenido")
    ax.set_xlabel("Resultado real de la primera tirada")
    ax.set_ylabel("Tratamiento")
    save_figure(fig, figures_dir / "figure_treatment_by_true_result_heatmap.png")

    # Figure 4: main hypothesis graph
    treatment_order = ["control", "seed_low", "seed_high"]
    hypothesis_rows = []
    for treatment_key in treatment_order:
        subset = successful[successful["treatment_key"] == treatment_key]
        n = int(len(subset))
        reported_6 = int(subset["reported_6"].sum())
        low, high = proportion_confidence_interval(reported_6, n)
        hypothesis_rows.append(
            {
                "treatment_key": treatment_key,
                "n": n,
                "reported_6_rate": reported_6 / n if n else 0.0,
                "ci_low": low,
                "ci_high": high,
            }
        )
    hypothesis_df = pd.DataFrame(hypothesis_rows)
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.pointplot(
        data=hypothesis_df,
        x="treatment_key",
        y="reported_6_rate",
        linestyle="none",
        color="black",
        ax=ax,
    )
    ax.errorbar(
        x=range(len(hypothesis_df)),
        y=hypothesis_df["reported_6_rate"],
        yerr=[
            hypothesis_df["reported_6_rate"] - hypothesis_df["ci_low"],
            hypothesis_df["ci_high"] - hypothesis_df["reported_6_rate"],
        ],
        fmt="none",
        ecolor="black",
        capsize=5,
        lw=1.5,
    )
    ax.set_ylim(0, 1)
    ax.set_title("Hipótesis principal: porcentaje que reporta un 6")
    ax.set_xlabel("Tratamiento")
    ax.set_ylabel("Proporción que reporta 6")
    save_figure(fig, figures_dir / "figure_reported6_by_treatment.png")

    # Stats for main hypothesis
    control = successful[successful["treatment_key"] == "control"]
    low = successful[successful["treatment_key"] == "seed_low"]
    high = successful[successful["treatment_key"] == "seed_high"]

    fisher_low_high = stats.fisher_exact(
        [
            [int(low["reported_6"].sum()), int(len(low) - low["reported_6"].sum())],
            [int(high["reported_6"].sum()), int(len(high) - high["reported_6"].sum())],
        ]
    )
    fisher_control_high = stats.fisher_exact(
        [
            [int(control["reported_6"].sum()), int(len(control) - control["reported_6"].sum())],
            [int(high["reported_6"].sum()), int(len(high) - high["reported_6"].sum())],
        ]
    )
    fisher_control_low = stats.fisher_exact(
        [
            [int(control["reported_6"].sum()), int(len(control) - control["reported_6"].sum())],
            [int(low["reported_6"].sum()), int(len(low) - low["reported_6"].sum())],
        ]
    )

    analysis_summary = {
        "input_dir": str(input_dir),
        "rows_total": int(len(df)),
        "rows_successful": int(len(successful)),
        "rows_failed": int(len(df) - len(successful)),
        "required_data_check": build_required_data_check(successful),
        "reported_6_rates": hypothesis_rows,
        "fisher_tests": {
            "seed_high_vs_seed_low": {
                "odds_ratio": fisher_low_high.statistic,
                "p_value": fisher_low_high.pvalue,
            },
            "seed_high_vs_control": {
                "odds_ratio": fisher_control_high.statistic,
                "p_value": fisher_control_high.pvalue,
            },
            "seed_low_vs_control": {
                "odds_ratio": fisher_control_low.statistic,
                "p_value": fisher_control_low.pvalue,
            },
        },
        "mean_reported_value_by_treatment": (
            successful.groupby("treatment_key")["reported_value"].mean().round(4).to_dict()
        ),
        "mean_actual_value_by_treatment": (
            successful.groupby("treatment_key")["first_result_value"].mean().round(4).to_dict()
        ),
        "lie_rate_by_treatment": (
            successful.groupby("treatment_key")["lied"].mean().round(4).to_dict()
        ),
        "payout_rate": float(successful["selected_for_payment"].mean()),
        "payout_count": int(successful["selected_for_payment"].sum()),
    }
    if summary_path.exists():
        analysis_summary["simulation_summary"] = json.loads(summary_path.read_text(encoding="utf-8"))

    (input_dir / "analysis_summary.json").write_text(
        json.dumps(analysis_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    hypothesis_df.to_csv(input_dir / "hypothesis_table.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
