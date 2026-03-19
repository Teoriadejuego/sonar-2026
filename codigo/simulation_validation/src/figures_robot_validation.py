from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import DATA_DIR, FIGURES_DIR, ROBOT_LABELS, ensure_directories


COLORS = {
    "control": "#7f8c8d",
    "seed_17": "#1f77b4",
    "seed_83": "#d62728",
}


def trajectory_by_position(
    df: pd.DataFrame,
    *,
    value_column: str,
    filename: str,
    title: str,
) -> None:
    grouped = (
        df.groupby(["treatment_key", "position_index"])[value_column]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    for treatment_key in ["seed_17", "seed_83", "control"]:
        subset = grouped[grouped["treatment_key"] == treatment_key].sort_values("position_index")
        if subset.empty:
            continue
        rolling = (
            subset[value_column]
            .rolling(window=12, min_periods=3, center=True)
            .mean()
        )
        ax.plot(
            subset["position_index"],
            rolling,
            label=treatment_key,
            color=COLORS[treatment_key],
            linewidth=2.2,
        )
    ax.set_title(title)
    ax.set_xlabel("Posición en la serie")
    ax.set_ylabel(value_column)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename, dpi=220)
    plt.close(fig)


def distribution_reported_value_by_robot(df: pd.DataFrame) -> None:
    counts = (
        df.groupby(["robot_type", "reported_value"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=list(ROBOT_LABELS), columns=[1, 2, 3, 4, 5, 6], fill_value=0)
    )
    counts = counts.div(counts.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(counts))
    colors = ["#dfe6e9", "#b2bec3", "#74b9ff", "#0984e3", "#fdcb6e", "#e17055"]
    for idx, reported_value in enumerate(counts.columns):
        values = counts[reported_value].to_numpy()
        ax.bar(
            [ROBOT_LABELS[item] for item in counts.index],
            values,
            bottom=bottom,
            label=str(reported_value),
            color=colors[idx],
        )
        bottom += values
    ax.set_title("Distribución de reported_value por robot")
    ax.set_ylabel("Proporción")
    ax.legend(title="Valor", frameon=False, ncols=3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure_3_reported_value_by_robot.png", dpi=220)
    plt.close(fig)


def heatmap_truth_vs_report(df: pd.DataFrame) -> None:
    pivot = (
        df.pivot_table(
            index="true_first_result",
            columns="reported_value",
            values="session_id",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(index=[1, 2, 3, 4, 5, 6], columns=[1, 2, 3, 4, 5, 6], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(pivot.to_numpy(), cmap="Blues")
    ax.set_title("Truth × Report")
    ax.set_xlabel("Reported value")
    ax.set_ylabel("True first result")
    ax.set_xticks(range(6), labels=[1, 2, 3, 4, 5, 6])
    ax.set_yticks(range(6), labels=[1, 2, 3, 4, 5, 6])
    for row_index in range(6):
        for col_index in range(6):
            ax.text(col_index, row_index, int(pivot.iloc[row_index, col_index]), ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure_4_truth_by_report_heatmap.png", dpi=220)
    plt.close(fig)


def honesty_by_robot(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("robot_type")["is_honest"]
        .mean()
        .reindex(list(ROBOT_LABELS))
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(
        [ROBOT_LABELS[item] for item in summary["robot_type"]],
        summary["is_honest"],
        color=["#2d3436", "#636e72", "#fdcb6e", "#00b894"],
    )
    ax.set_title("Honestidad media por robot")
    ax.set_ylim(0, 1)
    ax.set_ylabel("is_honest")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure_5_honesty_by_robot.png", dpi=220)
    plt.close(fig)


def lie_amount_by_robot_and_treatment(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["robot_type", "treatment_key"])["lie_amount"]
        .mean()
        .unstack(fill_value=0)
        .reindex(index=list(ROBOT_LABELS), columns=["control", "seed_17", "seed_83"], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(summary.index))
    width = 0.24
    for offset, treatment_key in enumerate(summary.columns):
        ax.bar(
            x + (offset - 1) * width,
            summary[treatment_key].to_numpy(),
            width=width,
            label=treatment_key,
            color=COLORS[treatment_key],
        )
    ax.set_xticks(x, [ROBOT_LABELS[item] for item in summary.index])
    ax.set_ylabel("Lie amount medio")
    ax.set_title("Lie amount por robot y tratamiento")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure_6_lie_amount_by_robot_treatment.png", dpi=220)
    plt.close(fig)


def main() -> None:
    ensure_directories()
    sessions = pd.read_csv(DATA_DIR / "simulated_sessions.csv")
    trajectory_by_position(
        sessions,
        value_column="reported_6",
        filename="figure_1_reported_6_trajectory.png",
        title="Trayectoria de reportes de 6",
    )
    trajectory_by_position(
        sessions,
        value_column="reported_5",
        filename="figure_2_reported_5_trajectory.png",
        title="Trayectoria de reportes de 5",
    )
    distribution_reported_value_by_robot(sessions)
    heatmap_truth_vs_report(sessions)
    honesty_by_robot(sessions)
    lie_amount_by_robot_and_treatment(sessions)


if __name__ == "__main__":
    main()
