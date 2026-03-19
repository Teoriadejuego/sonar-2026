from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_analysis import (
    BASE_DIR,
    BASE_START_UTC,
    CLUSTER_BOOTSTRAP_REPS,
    DATA_DIR,
    FIGURE_DPI,
    FIGURES_DIR,
    LOGS_DIR,
    OUTPUTS_DIR,
    POSITION_SEGMENTS,
    TABLES_DIR,
)


def ensure_directories() -> None:
    for path in (DATA_DIR, OUTPUTS_DIR, TABLES_DIR, FIGURES_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def stable_code(prefix: str, raw_value: str, length: int = 8) -> str:
    digest = hashlib.sha1(raw_value.encode("utf-8")).hexdigest()
    return f"{prefix}{digest[:length]}"


def stable_hash(raw_value: str, length: int = 12) -> str:
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:length]


def save_dataframe(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def save_markdown_table(frame: pd.DataFrame, path: Path, title: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    lines.append(frame.to_markdown(index=False))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def save_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def append_log(file_name: str, message: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    with (LOGS_DIR / file_name).open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def logistic(value: float) -> float:
    return 1.0 / (1.0 + np.exp(-value))


def seeded_rng(seed: int | None = None) -> np.random.Generator:
    return np.random.default_rng(seed)


def time_block_from_hour(hour_of_day: int) -> str:
    if 12 <= hour_of_day < 15:
        return "12-15"
    if 15 <= hour_of_day < 18:
        return "15-18"
    if 18 <= hour_of_day < 21:
        return "18-21"
    if 21 <= hour_of_day <= 23:
        return "21-00"
    return "00-03"


def position_segment(position_index: int) -> str:
    for label, (start, end) in POSITION_SEGMENTS.items():
        if start <= position_index <= end:
            return label
    return "outside_preregistered_window"


def festival_datetime(day_index: int, hour_of_day: int, minute: int) -> datetime:
    day_offset = timedelta(days=max(day_index - 1, 0))
    return BASE_START_UTC + day_offset + timedelta(hours=hour_of_day - 12, minutes=minute)


def build_referral_depth_map(frame: pd.DataFrame) -> dict[str, int]:
    parent_map = {
        row["session_id"]: row.get("invited_by_session_id")
        for _, row in frame.iterrows()
    }
    depths: dict[str, int] = {}

    def depth_for(session_id: str) -> int:
        if session_id in depths:
            return depths[session_id]
        parent_id = parent_map.get(session_id)
        if not parent_id or parent_id == session_id:
            depths[session_id] = 0
            return 0
        depth = depth_for(parent_id) + 1
        depths[session_id] = depth
        return depth

    for session_id in parent_map:
        depth_for(session_id)
    return depths


def moving_average_by_position(
    frame: pd.DataFrame,
    value_column: str,
    treatment_column: str = "treatment_key",
    window: int = 15,
) -> pd.DataFrame:
    grouped = (
        frame.groupby([treatment_column, "position_index"], as_index=False)[value_column]
        .mean()
        .sort_values([treatment_column, "position_index"])
    )
    grouped[f"{value_column}_smoothed"] = (
        grouped.groupby(treatment_column)[value_column]
        .transform(lambda series: series.rolling(window, min_periods=1, center=True).mean())
    )
    return grouped


def bootstrap_cluster_difference(
    frame: pd.DataFrame,
    outcome_column: str,
    high_treatment: str,
    low_treatment: str,
    cluster_column: str = "root_id",
    repetitions: int = CLUSTER_BOOTSTRAP_REPS,
    seed: int = 20260319,
) -> tuple[float, float]:
    clusters = sorted(frame[cluster_column].dropna().unique().tolist())
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    for _ in range(repetitions):
        sampled_clusters = rng.choice(clusters, size=len(clusters), replace=True)
        pieces = [frame.loc[frame[cluster_column] == cluster] for cluster in sampled_clusters]
        sampled = pd.concat(pieces, ignore_index=True)
        high = sampled.loc[sampled["treatment_key"] == high_treatment, outcome_column].mean()
        low = sampled.loc[sampled["treatment_key"] == low_treatment, outcome_column].mean()
        estimates.append(float(high - low))
    lower, upper = np.quantile(estimates, [0.025, 0.975])
    return float(lower), float(upper)


def configure_matplotlib() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.dpi": FIGURE_DPI,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.alpha": 0.15,
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 12,
            "legend.frameon": False,
        }
    )


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def relative_to_base(path: Path) -> str:
    return str(path.relative_to(BASE_DIR))

