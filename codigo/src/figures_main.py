from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from config_analysis import (
    DATA_DIR,
    EARLY_SEGMENT,
    FULL_SEGMENT,
    HIGH_TREATMENT_KEY,
    LATE_SEGMENT,
    LINE_SMOOTHING_WINDOW,
    LOW_TREATMENT_KEY,
    MAIN_COMPARISON,
    TREATMENT_COLORS,
    TREATMENT_LABELS,
    TREATMENT_ORDER,
)
from utils import append_log, configure_matplotlib, ensure_directories, moving_average_by_position


def load_analysis_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sonar_analysis_dataset_simulated.csv")


def figure_path(file_name: str):
    from config_analysis import FIGURES_DIR

    return FIGURES_DIR / file_name


def trajectory_reported_6(frame: pd.DataFrame) -> None:
    position_means = moving_average_by_position(frame, "reported_6", window=LINE_SMOOTHING_WINDOW)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for treatment_key in [LOW_TREATMENT_KEY, HIGH_TREATMENT_KEY, "control"]:
        subset = position_means.loc[position_means["treatment_key"] == treatment_key]
        if subset.empty:
            continue
        ax.plot(
            subset["position_index"],
            subset["reported_6_smoothed"],
            label=treatment_key,
            color=TREATMENT_COLORS[treatment_key],
            linewidth=2.2 if treatment_key != "control" else 1.6,
        )
    ax.set_title("Figure 1. Reported 6 by position")
    ax.set_xlabel("Position in series")
    ax.set_ylabel("Mean reported 6")
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_1_reported_6_trajectory.png"))
    plt.close(fig)


def difference_reported_6(frame: pd.DataFrame) -> None:
    pivot = (
        frame.loc[frame["treatment_key"].isin(list(MAIN_COMPARISON))]
        .groupby(["position_index", "treatment_key"], as_index=False)["reported_6"]
        .mean()
        .pivot(index="position_index", columns="treatment_key", values="reported_6")
        .sort_index()
    )
    pivot["difference"] = pivot[HIGH_TREATMENT_KEY] - pivot[LOW_TREATMENT_KEY]
    pivot["smoothed"] = pivot["difference"].rolling(LINE_SMOOTHING_WINDOW, min_periods=1, center=True).mean()

    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.axhline(0, color="#999999", linewidth=1)
    ax.plot(pivot.index, pivot["smoothed"], color="#6a1b9a", linewidth=2.2)
    ax.set_title(
        f"Figure 2. {TREATMENT_LABELS[HIGH_TREATMENT_KEY]} minus {TREATMENT_LABELS[LOW_TREATMENT_KEY]}"
    )
    ax.set_xlabel("Position in series")
    ax.set_ylabel("Difference in reported 6")
    fig.tight_layout()
    fig.savefig(figure_path("figure_2_reported_6_difference.png"))
    plt.close(fig)


def segment_bars(frame: pd.DataFrame) -> None:
    early_start, early_end = EARLY_SEGMENT
    late_start, late_end = LATE_SEGMENT
    full_start, full_end = FULL_SEGMENT
    segments = {
        f"{early_start}-{early_end}": frame.loc[frame["position_index"].between(early_start, early_end)],
        f"{late_start}-{late_end}": frame.loc[frame["position_index"].between(late_start, late_end)],
        f"{full_start}-{full_end}": frame.loc[frame["position_index"].between(full_start, full_end)],
    }
    treatments = TREATMENT_ORDER
    x = np.arange(len(segments))
    width = 0.23

    fig, ax = plt.subplots(figsize=(8, 4.8))
    for offset, treatment_key in enumerate(treatments):
        means = [
            segment.loc[segment["treatment_key"] == treatment_key, "reported_6"].mean()
            for segment in segments.values()
        ]
        ax.bar(
            x + (offset - 1) * width,
            means,
            width=width,
            label=treatment_key,
            color=TREATMENT_COLORS[treatment_key],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(list(segments.keys()))
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean reported 6")
    ax.set_title("Figure 3. Reported 6 by segment")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_3_reported_6_segments.png"))
    plt.close(fig)


def distribution_reported_value(frame: pd.DataFrame) -> None:
    distribution = (
        frame.groupby(["treatment_key", "reported_value"], as_index=False)
        .size()
        .pivot(index="reported_value", columns="treatment_key", values="size")
        .fillna(0)
    )
    distribution = distribution / distribution.sum(axis=0)

    values = distribution.index.to_numpy(dtype=float)
    width = 0.22
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for offset, treatment_key in enumerate(TREATMENT_ORDER):
        ax.bar(
            values + (offset - 1) * width,
            distribution[treatment_key],
            width=width,
            label=treatment_key,
            color=TREATMENT_COLORS[treatment_key],
        )
    ax.set_xticks(range(1, 7))
    ax.set_xlabel("Reported value")
    ax.set_ylabel("Share within treatment")
    ax.set_title("Figure 4. Distribution of reported values")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_4_report_distribution.png"))
    plt.close(fig)


def heatmap_truth_report(frame: pd.DataFrame) -> None:
    matrix = (
        frame.groupby(["true_first_result", "reported_value"], as_index=False)
        .size()
        .pivot(index="true_first_result", columns="reported_value", values="size")
        .fillna(0)
    )
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    image = ax.imshow(matrix.to_numpy(), cmap="Greys", aspect="auto")
    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns.tolist())
    ax.set_yticks(np.arange(matrix.shape[0]))
    ax.set_yticklabels(matrix.index.tolist())
    ax.set_xlabel("Reported value")
    ax.set_ylabel("True first result")
    ax.set_title("Figure 5. Truth by report")
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            ax.text(col_index, row_index, int(matrix.iat[row_index, col_index]), ha="center", va="center")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(figure_path("figure_5_truth_report_heatmap.png"))
    plt.close(fig)


def main() -> None:
    ensure_directories()
    configure_matplotlib()
    analysis = load_analysis_data()
    trajectory_reported_6(analysis)
    difference_reported_6(analysis)
    segment_bars(analysis)
    distribution_reported_value(analysis)
    heatmap_truth_report(analysis)
    append_log("figures_main.log", "Generated Figures 1-5.")
    print("Main figures completed.")


if __name__ == "__main__":
    main()
