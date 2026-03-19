from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data" / "simulated"
OUTPUTS_DIR = BASE_DIR / "outputs"
TABLES_DIR = OUTPUTS_DIR / "tables"
FIGURES_DIR = OUTPUTS_DIR / "figures"
LOGS_DIR = OUTPUTS_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
PROJECT_PARAMETERS_PATH = PROJECT_ROOT / "project_parameters.json"


def _load_project_parameters() -> dict:
    return json.loads(PROJECT_PARAMETERS_PATH.read_text(encoding="utf-8"))


def _exact_counts(total: int, weight_map: dict[str, float]) -> dict[str, int]:
    raw_counts = {key: total * weight for key, weight in weight_map.items()}
    floors = {key: math.floor(value) for key, value in raw_counts.items()}
    remainder = total - sum(floors.values())
    ranked = sorted(
        weight_map,
        key=lambda key: (raw_counts[key] - floors[key], key),
        reverse=True,
    )
    for key in ranked[:remainder]:
        floors[key] += 1
    return floors


PROJECT_PARAMETERS = _load_project_parameters()
METADATA = PROJECT_PARAMETERS["metadata"]
EXPERIMENT = PROJECT_PARAMETERS["experiment"]
PHASE_KEY = "phase_1_main"
PHASE_SETTINGS = EXPERIMENT["phases"][PHASE_KEY]
PHASE_TREATMENTS = PHASE_SETTINGS["treatments"]

RANDOM_SEED = 20260319
EXPERIMENT_VERSION = str(METADATA["experiment_version"])
EXPERIMENT_PHASE = PHASE_KEY
TREATMENT_VERSION = str(PHASE_SETTINGS["treatment_version"])
ALLOCATION_VERSION = str(PHASE_SETTINGS["allocation_version"])
DECK_VERSION = str(METADATA["deck_version"])
PAYMENT_VERSION = str(METADATA["payment_version"])
TELEMETRY_VERSION = str(METADATA["telemetry_version"])
LEXICON_VERSION = str(METADATA["lexicon_version"])
UI_VERSION = str(METADATA["ui_version"])

VALID_COMPLETED_SESSIONS = 6000
SERIES_MAX_LENGTH = int(EXPERIMENT["participant_limit"])
VISIBLE_WINDOW = int(EXPERIMENT["window_size"])
MAX_ATTEMPTS = int(EXPERIMENT["max_attempts"])
DECK_BLOCK_SIZE = int(EXPERIMENT["deck_block_size"])
FESTIVAL_DAYS = 4
BASE_START_UTC = datetime(2026, 6, 11, 12, 0, 0)

TREATMENT_ORDER = ["control"] + sorted(
    [key for key in PHASE_TREATMENTS if key != "control"],
    key=lambda key: int(PHASE_TREATMENTS[key]["seed_initial_count"] or 0),
)
NON_CONTROL_TREATMENTS = [key for key in TREATMENT_ORDER if key != "control"]
LOW_TREATMENT_KEY = NON_CONTROL_TREATMENTS[0]
HIGH_TREATMENT_KEY = NON_CONTROL_TREATMENTS[-1]
LOW_SEED_COUNT = int(PHASE_TREATMENTS[LOW_TREATMENT_KEY]["seed_initial_count"])
HIGH_SEED_COUNT = int(PHASE_TREATMENTS[HIGH_TREATMENT_KEY]["seed_initial_count"])

TREATMENT_WEIGHTS = {
    key: float(settings["assignment_weight"])
    for key, settings in PHASE_TREATMENTS.items()
}
TREATMENT_COUNTS = _exact_counts(VALID_COMPLETED_SESSIONS, TREATMENT_WEIGHTS)
TREATMENT_FAMILIES = {
    key: str(settings["treatment_family"])
    for key, settings in PHASE_TREATMENTS.items()
}
TREATMENT_LABELS = {
    key: str(settings["label"])
    for key, settings in PHASE_TREATMENTS.items()
}
TREATMENT_COLORS = {
    "control": "#6f6f6f",
    LOW_TREATMENT_KEY: "#204a87",
    HIGH_TREATMENT_KEY: "#b04a11",
}
SEED_INITIAL_COUNTS = {
    key: (
        int(settings["seed_initial_count"])
        if settings["seed_initial_count"] is not None
        else None
    )
    for key, settings in PHASE_TREATMENTS.items()
}
SEED_FILL_ORDERS = {
    key: str(settings.get("seed_fill_order") or "target_first")
    for key, settings in PHASE_TREATMENTS.items()
}
TARGET_VALUES = {
    key: (
        int(settings["norm_target_value"])
        if settings["norm_target_value"] is not None
        else None
    )
    for key, settings in PHASE_TREATMENTS.items()
}

ROOT_COUNT = math.ceil(max(TREATMENT_COUNTS.values()) / SERIES_MAX_LENGTH)
ROOT_IDS = [f"root_{index:02d}" for index in range(1, ROOT_COUNT + 1)]

LANGUAGES = ["es", "ca", "en", "fr", "pt"]
LANGUAGE_WEIGHTS = [0.54, 0.14, 0.16, 0.08, 0.08]

TIME_BLOCK_LABELS = [
    "12-15",
    "15-18",
    "18-21",
    "21-00",
    "00-03",
]

PRIZE_MAP = {
    int(key): int(value) for key, value in EXPERIMENT["prize_eur"].items()
}

MAIN_COMPARISON = (HIGH_TREATMENT_KEY, LOW_TREATMENT_KEY)
POSITION_SEGMENTS = {
    f"positions_1_{VISIBLE_WINDOW}": (1, VISIBLE_WINDOW),
    f"positions_{VISIBLE_WINDOW + 1}_{SERIES_MAX_LENGTH}": (
        VISIBLE_WINDOW + 1,
        SERIES_MAX_LENGTH,
    ),
    f"positions_1_{SERIES_MAX_LENGTH}": (1, SERIES_MAX_LENGTH),
}
EARLY_SEGMENT = POSITION_SEGMENTS[f"positions_1_{VISIBLE_WINDOW}"]
LATE_SEGMENT = POSITION_SEGMENTS[
    f"positions_{VISIBLE_WINDOW + 1}_{SERIES_MAX_LENGTH}"
]
FULL_SEGMENT = POSITION_SEGMENTS[f"positions_1_{SERIES_MAX_LENGTH}"]

FIGURE_DPI = 180
LINE_SMOOTHING_WINDOW = 15
CLUSTER_BOOTSTRAP_REPS = 500
