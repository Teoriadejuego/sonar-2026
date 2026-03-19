from __future__ import annotations

from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "simulated"
OUTPUTS_DIR = BASE_DIR / "outputs"
TABLES_DIR = OUTPUTS_DIR / "tables"
FIGURES_DIR = OUTPUTS_DIR / "figures"
LOGS_DIR = OUTPUTS_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"

RANDOM_SEED = 20260319
EXPERIMENT_VERSION = "sonar-2026-field-v2"
EXPERIMENT_PHASE = "phase_1_main"
TREATMENT_VERSION = "phase_1_six_norms_v1"
ALLOCATION_VERSION = "phase_1_10_45_45_v1"
DECK_VERSION = "balanced-deck-v2"
PAYMENT_VERSION = "payment-v2"
TELEMETRY_VERSION = "telemetry-v3"
LEXICON_VERSION = "lexicon-v4"
UI_VERSION = "ui-v7"

VALID_COMPLETED_SESSIONS = 6000
SERIES_MAX_LENGTH = 250
VISIBLE_WINDOW = 100
MAX_ATTEMPTS = 10
DECK_BLOCK_SIZE = 24
ROOT_COUNT = 11
ROOT_IDS = [f"root_{index:02d}" for index in range(1, ROOT_COUNT + 1)]
FESTIVAL_DAYS = 4
BASE_START_UTC = datetime(2026, 6, 11, 12, 0, 0)

TREATMENT_COUNTS = {
    "control": 600,
    "seed_17": 2700,
    "seed_83": 2700,
}

TREATMENT_FAMILIES = {
    "control": "control",
    "seed_17": "six_norm",
    "seed_83": "six_norm",
}

TREATMENT_LABELS = {
    "control": "Control",
    "seed_17": "Seed 17",
    "seed_83": "Seed 83",
}

TREATMENT_COLORS = {
    "control": "#7a7a7a",
    "seed_17": "#1f4e79",
    "seed_83": "#c84c09",
}

SEED_INITIAL_COUNTS = {
    "control": None,
    "seed_17": 17,
    "seed_83": 83,
}

TARGET_VALUES = {
    "control": None,
    "seed_17": 6,
    "seed_83": 6,
}

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
    1: 10,
    2: 20,
    3: 30,
    4: 40,
    5: 50,
    6: 60,
}

MAIN_COMPARISON = ("seed_83", "seed_17")
POSITION_SEGMENTS = {
    "positions_1_100": (1, 100),
    "positions_101_250": (101, 250),
    "positions_1_250": (1, 250),
}

FIGURE_DPI = 180
LINE_SMOOTHING_WINDOW = 15
CLUSTER_BOOTSTRAP_REPS = 500

