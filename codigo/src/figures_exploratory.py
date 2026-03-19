from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from config_analysis import DATA_DIR, LINE_SMOOTHING_WINDOW, TREATMENT_COLORS
from utils import append_log, configure_matplotlib, ensure_directories, moving_average_by_position


def load_analysis_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sonar_analysis_dataset_simulated.csv")


def figure_path(file_name: str):
    from config_analysis import FIGURES_DIR

    return FIGURES_DIR / file_name


def trajectory_reported_5(frame: pd.DataFrame) -> None:
    means = moving_average_by_position(frame, "reported_5", window=LINE_SMOOTHING_WINDOW)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for treatment_key in ["control", "seed_17", "seed_83"]:
        subset = means.loc[means["treatment_key"] == treatment_key]
        ax.plot(
            subset["position_index"],
            subset["reported_5_smoothed"],
            label=treatment_key,
            color=TREATMENT_COLORS[treatment_key],
            linewidth=2.0 if treatment_key != "control" else 1.6,
        )
    ax.set_title("Figure 6. Reported 5 by position")
    ax.set_xlabel("Position in series")
    ax.set_ylabel("Mean reported 5")
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_6_reported_5_trajectory.png"))
    plt.close(fig)


def trajectory_lie_amount(frame: pd.DataFrame) -> None:
    means = moving_average_by_position(frame, "lie_amount", window=LINE_SMOOTHING_WINDOW)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for treatment_key in ["control", "seed_17", "seed_83"]:
        subset = means.loc[means["treatment_key"] == treatment_key]
        ax.plot(
            subset["position_index"],
            subset["lie_amount_smoothed"],
            label=treatment_key,
            color=TREATMENT_COLORS[treatment_key],
            linewidth=2.0 if treatment_key != "control" else 1.6,
        )
    ax.set_title("Figure 7. Mean lie amount by position")
    ax.set_xlabel("Position in series")
    ax.set_ylabel("Mean lie amount")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_7_lie_amount_trajectory.png"))
    plt.close(fig)


def distribution_relative_lie(frame: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bins = np.linspace(0, 1, 11)
    for treatment_key in ["control", "seed_17", "seed_83"]:
        subset = frame.loc[frame["treatment_key"] == treatment_key, "relative_lie"]
        ax.hist(
            subset,
            bins=bins,
            alpha=0.35,
            color=TREATMENT_COLORS[treatment_key],
            label=treatment_key,
            density=True,
        )
    ax.set_title("Figure 8. Relative lie distribution")
    ax.set_xlabel("Relative lie")
    ax.set_ylabel("Density")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path("figure_8_relative_lie_distribution.png"))
    plt.close(fig)


def time_block_results(frame: pd.DataFrame) -> None:
    summary = (
        frame.groupby(["time_block", "treatment_key"], as_index=False)
        .agg(
            reported_6=("reported_6", "mean"),
            reported_5=("reported_5", "mean"),
            is_honest=("is_honest", "mean"),
        )
        .sort_values("time_block")
    )

    metrics = ["reported_6", "reported_5", "is_honest"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharex=True)
    for axis, metric in zip(axes, metrics, strict=False):
        pivot = summary.pivot(index="time_block", columns="treatment_key", values=metric)
        for treatment_key in ["control", "seed_17", "seed_83"]:
            axis.plot(
                pivot.index,
                pivot[treatment_key],
                marker="o",
                linewidth=2,
                color=TREATMENT_COLORS[treatment_key],
                label=treatment_key,
            )
        axis.set_title(metric.replace("_", " "))
        axis.tick_params(axis="x", rotation=35)
        axis.set_ylim(0, 1)
    axes[0].set_ylabel("Mean")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3)
    fig.suptitle("Figure 9. Time-block profiles", y=1.02)
    fig.tight_layout()
    fig.savefig(figure_path("figure_9_time_block_results.png"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_directories()
    configure_matplotlib()
    analysis = load_analysis_data()
    trajectory_reported_5(analysis)
    trajectory_lie_amount(analysis)
    distribution_relative_lie(analysis)
    time_block_results(analysis)
    append_log("figures_exploratory.log", "Generated Figures 6-9.")
    print("Exploratory figures completed.")


if __name__ == "__main__":
    main()
