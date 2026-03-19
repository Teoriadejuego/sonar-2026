from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


SIMULATION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SIMULATION_ROOT.parents[1]
CONFIG_PATH = SIMULATION_ROOT / "config" / "robot_simulation_config.json"
DATA_DIR = SIMULATION_ROOT / "data"
OUTPUTS_DIR = SIMULATION_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
TABLES_DIR = OUTPUTS_DIR / "tables"
LOGS_DIR = OUTPUTS_DIR / "logs"

BACKEND_DIR = PROJECT_ROOT / "api-sonar-main" / "api-sonar-main"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from experiment import (  # noqa: E402
    MAX_ATTEMPTS,
    PARTICIPANT_LIMIT,
    PHASE_1_MAIN,
    WINDOW_SIZE,
    assignment_weights_for_phase,
    balanced_sequence,
    deterministic_seed,
    payout_amount_for_claim,
    payout_eligible,
    seed_window_values,
    treatment_config,
)


ROBOT_LABELS = {
    "type_a_norm_imitator": "Tipo A",
    "type_b_mixed_random_honest": "Tipo B",
    "type_c_prudent_five": "Tipo C",
    "type_d_honest": "Tipo D",
}

TREATMENT_ORDER = ["control"] + sorted(
    [key for key in assignment_weights_for_phase(PHASE_1_MAIN) if key != "control"],
    key=lambda key: int(treatment_config(PHASE_1_MAIN, key)["seed_initial_count"] or 0),
)
LOW_TREATMENT_KEY = TREATMENT_ORDER[1]
HIGH_TREATMENT_KEY = TREATMENT_ORDER[2]
TREATMENT_COLORS = {
    "control": "#7f8c8d",
    LOW_TREATMENT_KEY: "#1f77b4",
    HIGH_TREATMENT_KEY: "#d62728",
}


@dataclass
class SeriesState:
    root_id: str
    series_id: str
    treatment_key: str
    treatment_family: str
    norm_target_value: int | None
    assignment_weight: float
    participant_limit: int
    sample_size: int
    position_counter: int = 0
    completed_count: int = 0
    visible_window: list[int] = field(default_factory=list)
    actual_window: list[int] = field(default_factory=list)
    visible_count_target: int = 0
    actual_count_target: int = 0
    full_target_streak: int = 0


@dataclass
class RootState:
    root_id: str
    root_sequence: int
    root_seed: str
    phase_key: str
    series_by_treatment: dict[str, SeriesState]
    closed_reason: str | None = None


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_directories() -> None:
    for path in [DATA_DIR, FIGURES_DIR, TABLES_DIR, LOGS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def exact_counts(total: int, weight_map: dict[str, float]) -> dict[str, int]:
    ordered = list(weight_map.items())
    raw_counts = {key: total * weight for key, weight in ordered}
    floors = {key: math.floor(value) for key, value in raw_counts.items()}
    remainder = total - sum(floors.values())
    ranked = sorted(
        ordered,
        key=lambda item: (raw_counts[item[0]] - floors[item[0]], item[0]),
        reverse=True,
    )
    for key, _ in ranked[:remainder]:
        floors[key] += 1
    return floors


def sequence_from_counts(counts: dict[str, int], rng: random.Random) -> list[str]:
    values: list[str] = []
    for key, count in counts.items():
        values.extend([key] * count)
    rng.shuffle(values)
    return values


def initialize_series_windows(series: SeriesState) -> None:
    if series.treatment_family == "control":
        series.visible_window = []
        series.visible_count_target = 0
    else:
        series.visible_window = seed_window_values(PHASE_1_MAIN, series.treatment_key)
        series.visible_count_target = sum(
            1 for value in series.visible_window if value == series.norm_target_value
        )
    series.actual_window = []
    series.actual_count_target = 0


def build_root_state(
    *,
    root_sequence: int,
    phase_key: str,
    treatment_weights: dict[str, float],
    participant_limit: int,
    window_size: int,
) -> RootState:
    root_id = f"sim_root_{root_sequence:03d}"
    root_seed = deterministic_seed(root_sequence)
    series_by_treatment: dict[str, SeriesState] = {}
    for treatment_key in treatment_weights:
        config = treatment_config(phase_key, treatment_key)
        series = SeriesState(
            root_id=root_id,
            series_id=f"{root_id}_{treatment_key}",
            treatment_key=treatment_key,
            treatment_family=str(config["treatment_family"]),
            norm_target_value=(
                int(config["norm_target_value"])
                if config["norm_target_value"] is not None
                else None
            ),
            assignment_weight=float(config["assignment_weight"]),
            participant_limit=participant_limit,
            sample_size=window_size,
        )
        initialize_series_windows(series)
        series_by_treatment[treatment_key] = series
    return RootState(
        root_id=root_id,
        root_sequence=root_sequence,
        root_seed=root_seed,
        phase_key=phase_key,
        series_by_treatment=series_by_treatment,
    )


def choose_series_for_assignment(
    root: RootState,
    *,
    treatment_targets: dict[str, int],
    treatment_progress: dict[str, int],
) -> SeriesState | None:
    candidates = [
        series
        for series in root.series_by_treatment.values()
        if series.position_counter < series.participant_limit
        and treatment_progress[series.treatment_key] < treatment_targets[series.treatment_key]
    ]
    if not candidates:
        return None

    def score(item: SeriesState) -> tuple[float, str]:
        return (
            item.position_counter / max(item.assignment_weight, 0.0001),
            item.treatment_key,
        )

    return min(candidates, key=score)


def append_window(series: SeriesState, *, window_kind: str, value: int, window_size: int) -> None:
    target_value = series.norm_target_value
    if window_kind == "visible":
        if series.treatment_family == "control":
            return
        series.visible_window.append(value)
        if len(series.visible_window) > window_size:
            series.visible_window.pop(0)
        series.visible_count_target = sum(
            1 for item in series.visible_window if item == target_value
        )
        return

    series.actual_window.append(value)
    if len(series.actual_window) > window_size:
        series.actual_window.pop(0)
    series.actual_count_target = sum(
        1 for item in series.actual_window if item == target_value
    )


def displayed_message(
    *,
    treatment_key: str,
    displayed_count_target: int | None,
    denominator: int | None,
    target_value: int | None,
) -> str:
    if treatment_key == "control":
        return "Tu respuesta es anónima. Selecciona tu número."
    return f"{displayed_count_target} de cada {denominator} personas eligieron {target_value}"


def draw_from_probabilities(probabilities: list[float], rng: random.Random) -> int:
    roll = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if roll <= cumulative:
            return index
    return len(probabilities) - 1


def report_value_for_robot(
    *,
    robot_type: str,
    true_first_result: int,
    treatment_key: str,
    displayed_count_target: int | None,
    displayed_denominator: int | None,
    rng: random.Random,
    robot_behavior: dict[str, Any],
) -> int:
    if robot_type == "type_a_norm_imitator":
        control_truth_probability = robot_behavior[robot_type]["control_truth_probability"]
        control_six_probability = robot_behavior[robot_type]["control_report_six_probability"]
        if treatment_key == "control":
            if rng.random() <= control_truth_probability:
                return true_first_result
            if rng.random() <= control_six_probability:
                return 6
            return true_first_result
        probability_six = (displayed_count_target or 0) / max(displayed_denominator or 1, 1)
        return 6 if rng.random() <= probability_six else true_first_result

    if robot_type == "type_b_mixed_random_honest":
        if rng.random() <= robot_behavior[robot_type]["truth_probability"]:
            return true_first_result
        return int(rng.randint(1, 6))

    if robot_type == "type_c_prudent_five":
        return 5 if true_first_result in {1, 2} else true_first_result

    if robot_type == "type_d_honest":
        return true_first_result

    raise KeyError(f"Robot no reconocido: {robot_type}")


def sample_reroll_count(
    *,
    robot_type: str,
    robot_behavior: dict[str, Any],
    rng: random.Random,
) -> int:
    probabilities = robot_behavior[robot_type]["reroll_probabilities"]
    return min(draw_from_probabilities(probabilities, rng), MAX_ATTEMPTS - 1)


def reaction_time_ms(rng: random.Random, *, lower: int, upper: int) -> int:
    return int(rng.randint(lower, upper))


def hour_of_day(index: int, rng: random.Random) -> int:
    base_cycle = [15, 16, 17, 18, 19, 20, 21, 22]
    return base_cycle[index % len(base_cycle)] + int(rng.choice([0, 0, 0, 1]))


def time_block_from_hour(hour: int) -> str:
    if hour < 17:
        return "afternoon"
    if hour < 20:
        return "evening"
    return "night"


def derive_quality_flags(
    *,
    report_rt_ms: int,
    total_session_ms: int,
    focus_loss_pre_claim: bool,
    reload_count: int,
    network_error_count: int,
    rng: random.Random,
    context_config: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    if report_rt_ms < 900:
        flags.append("fast_report")
    if total_session_ms < 12000:
        flags.append("short_session")
    if focus_loss_pre_claim:
        flags.append("focus_loss_pre_claim")
    if reload_count > 0:
        flags.append("reload")
    if network_error_count > 0:
        flags.append("network_error")
    if rng.random() < context_config["quality_fast_report_rate"]:
        flags.append("quality_fast_report")
    return sorted(set(flags))


def make_population_table(config: dict[str, Any]) -> pd.DataFrame:
    total = int(config["participants_valid_completed"])
    rng = random.Random(config["random_seed"])
    robot_counts = exact_counts(total, config["robot_mix"])
    language_counts = exact_counts(total, config["language_weights"])
    robot_sequence = sequence_from_counts(robot_counts, rng)
    language_sequence = sequence_from_counts(language_counts, rng)
    population = pd.DataFrame(
        {
            "sequence_order": range(1, total + 1),
            "robot_id": [f"robot_{index:05d}" for index in range(1, total + 1)],
            "robot_type": robot_sequence,
            "language": language_sequence,
        }
    )
    population["robot_label"] = population["robot_type"].map(ROBOT_LABELS)
    return population


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def rolling_mean_by_group(
    df: pd.DataFrame,
    *,
    value_column: str,
    group_column: str,
    window: int = 15,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for group_value, chunk in df.groupby(group_column):
        ordered = chunk.sort_values("position_index").copy()
        ordered["smoothed_value"] = (
            ordered[value_column]
            .rolling(window=window, min_periods=3, center=True)
            .mean()
        )
        ordered[group_column] = group_value
        rows.append(ordered)
    return pd.concat(rows, ignore_index=True)


def validation_row(check_name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "check_name": check_name,
        "passed": bool(passed),
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }

