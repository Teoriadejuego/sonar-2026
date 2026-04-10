import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Any


CONTROL_TREATMENT_KEY = "control"
LEGACY_PHASE_DISABLED = "legacy_disabled"


def project_parameters_path() -> Path:
    configured_path = os.getenv("PROJECT_PARAMETERS_PATH")
    if configured_path:
        configured = Path(configured_path).expanduser().resolve()
        if configured.exists():
            return configured

    current = Path(__file__).resolve()
    for base in [current.parent, *current.parents]:
        candidate = base / "project_parameters.json"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No se encontro project_parameters.json. "
        "Configura PROJECT_PARAMETERS_PATH o incluye el archivo en la imagen."
    )


def load_project_parameters() -> dict[str, Any]:
    with project_parameters_path().open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_project_parameters(payload)
    return payload


def validate_project_parameters(payload: dict[str, Any]) -> None:
    experiment = payload["experiment"]
    window_size = int(experiment["window_size"])
    displayed_denominator = int(experiment["displayed_denominator"])
    max_attempts = int(experiment["max_attempts"])
    participant_limit = int(experiment["participant_limit"])
    treatment_deck_size = int(experiment["treatment_deck_size"])
    result_deck_size = int(experiment["result_deck_size"])
    payment_deck_size = int(experiment["payment_deck_size"])
    payment_winners_per_deck = int(experiment["payment_winners_per_deck"])
    prize_eur = experiment["prize_eur"]
    demo_ids = experiment.get("demo_ids", {})
    bracelet_pattern = re.compile(experiment["bracelet_pattern"])

    if window_size <= 0:
        raise ValueError("window_size debe ser mayor que 0")
    if displayed_denominator != window_size:
        raise ValueError("displayed_denominator debe coincidir con window_size")
    if max_attempts <= 0:
        raise ValueError("max_attempts debe ser mayor que 0")
    if participant_limit <= 0:
        raise ValueError("participant_limit debe ser mayor que 0")
    if treatment_deck_size != displayed_denominator + 2:
        raise ValueError(
            "treatment_deck_size debe ser exactamente window_size + 2 (norm_0..norm_60 y control)"
        )
    if result_deck_size != 24:
        raise ValueError("result_deck_size debe ser exactamente 24")
    if payment_deck_size != 100:
        raise ValueError("payment_deck_size debe ser exactamente 100")
    if payment_winners_per_deck != 1:
        raise ValueError("payment_winners_per_deck debe ser exactamente 1")
    if sorted(int(key) for key in prize_eur.keys()) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("prize_eur debe definir valores para 1, 2, 3, 4, 5 y 6")

    valid_treatment_keys = {f"norm_{count}" for count in range(window_size + 1)}
    valid_treatment_keys.add(CONTROL_TREATMENT_KEY)
    for bracelet_id, config in demo_ids.items():
        normalized = bracelet_id.strip().upper()
        if not bracelet_pattern.fullmatch(normalized):
            raise ValueError(
                f"demo_ids.{bracelet_id} no cumple el patron 8 alfanumerico con 4 letras y 4 numeros"
            )
        treatment_key = str(config["treatment_key"])
        if treatment_key not in valid_treatment_keys:
            raise ValueError(f"demo_ids.{bracelet_id}.treatment_key no es valido")
        result_value = int(config["result_value"])
        if result_value not in {1, 2, 3, 4, 5, 6}:
            raise ValueError(f"demo_ids.{bracelet_id}.result_value no es valido")


PROJECT_PARAMETERS = load_project_parameters()
METADATA = PROJECT_PARAMETERS["metadata"]
EXPERIMENT_SETTINGS = PROJECT_PARAMETERS["experiment"]
SUPPORT_SETTINGS = PROJECT_PARAMETERS["support"]
COPY_SETTINGS = PROJECT_PARAMETERS["copy"]

SCHEMA_VERSION = METADATA["schema_version"]
EXPERIMENT_VERSION = METADATA["experiment_version"]
UI_VERSION = METADATA["ui_version"]
CONSENT_VERSION = METADATA["consent_version"]
DECK_VERSION = METADATA["deck_version"]
PAYMENT_VERSION = METADATA["payment_version"]
TELEMETRY_VERSION = METADATA["telemetry_version"]
LEXICON_VERSION = METADATA["lexicon_version"]
DEPLOYMENT_CONTEXT = os.getenv("DEPLOYMENT_CONTEXT", METADATA["deployment_context"])
SITE_CODE = os.getenv("SITE_CODE", METADATA["site_code"])
CAMPAIGN_CODE = os.getenv("CAMPAIGN_CODE", METADATA["campaign_code"])
ENVIRONMENT_LABEL = os.getenv("ENVIRONMENT_LABEL", METADATA["environment_label"])

CURRENT_PHASE = str(EXPERIMENT_SETTINGS["design_key"])
PHASE_1_MAIN = CURRENT_PHASE
PHASE_2_ROBUSTNESS = LEGACY_PHASE_DISABLED

# Railway/production has carried forward legacy experiment_state.current_phase
# values from older designs. The 62-treatment design is now the only active
# runtime, so any stale or malformed phase key must resolve to the current
# design instead of taking the API down.
PHASE_COMPATIBILITY_ALIASES = {
    "": PHASE_1_MAIN,
    PHASE_1_MAIN: PHASE_1_MAIN,
    "seed_low": PHASE_1_MAIN,
    "seed_high": PHASE_1_MAIN,
    "phase_2": PHASE_1_MAIN,
    LEGACY_PHASE_DISABLED: PHASE_1_MAIN,
}

WINDOW_SIZE = int(EXPERIMENT_SETTINGS["window_size"])
DISPLAYED_DENOMINATOR = int(EXPERIMENT_SETTINGS["displayed_denominator"])
DEFAULT_NORM_TARGET_VALUE = int(EXPERIMENT_SETTINGS["norm_target_value"])
MAX_ATTEMPTS = int(EXPERIMENT_SETTINGS["max_attempts"])
PARTICIPANT_LIMIT = int(EXPERIMENT_SETTINGS["participant_limit"])
DEMO_PULSERA_COUNT = int(EXPERIMENT_SETTINGS["demo_pulsera_count"])
TREATMENT_DECK_SIZE = int(EXPERIMENT_SETTINGS["treatment_deck_size"])
RESULT_DECK_SIZE = int(EXPERIMENT_SETTINGS["result_deck_size"])
PAYMENT_DECK_SIZE = int(EXPERIMENT_SETTINGS["payment_deck_size"])
PAYMENT_WINNERS_PER_DECK = int(EXPERIMENT_SETTINGS["payment_winners_per_deck"])
PAYOUT_RATE_DENOMINATOR = PAYMENT_DECK_SIZE
COLLAPSE_CONSECUTIVE_CLAIMS = int(
    EXPERIMENT_SETTINGS.get("collapse_consecutive_claims", 0)
)
PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD = int(
    EXPERIMENT_SETTINGS["phase_transition_valid_completed_threshold"]
)
BRACELET_PATTERN = re.compile(EXPERIMENT_SETTINGS["bracelet_pattern"])
QUALITY_THRESHOLDS = {
    key: int(value)
    for key, value in EXPERIMENT_SETTINGS["quality_thresholds"].items()
}
WINNER_WHATSAPP_PHONE = str(SUPPORT_SETTINGS["winner_whatsapp_phone"])
PRIZE_EUR = {
    int(key): int(value) for key, value in EXPERIMENT_SETTINGS["prize_eur"].items()
}

PHASE_VERSION = str(EXPERIMENT_SETTINGS["phase_version"])
TREATMENT_VERSION = str(EXPERIMENT_SETTINGS["treatment_version"])
ALLOCATION_VERSION = str(EXPERIMENT_SETTINGS["allocation_version"])
DISPLAYED_MESSAGE_VERSION = str(EXPERIMENT_SETTINGS["displayed_message_version"])

TREATMENT_KEYS = [f"norm_{count}" for count in range(WINDOW_SIZE + 1)] + [
    CONTROL_TREATMENT_KEY
]


def _build_treatment_definitions() -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for count in range(WINDOW_SIZE + 1):
        treatment_key = f"norm_{count}"
        definitions[treatment_key] = {
            "label": f"norm_{count}",
            "treatment_family": "six_norm",
            "treatment_type": "social_norm",
            "norm_target_value": DEFAULT_NORM_TARGET_VALUE,
            "displayed_count_target": count,
            "displayed_denominator": DISPLAYED_DENOMINATOR,
            "assignment_weight": 1.0 / TREATMENT_DECK_SIZE,
            "is_control": False,
        }
    definitions[CONTROL_TREATMENT_KEY] = {
        "label": "control",
        "treatment_family": "control",
        "treatment_type": "control",
        "norm_target_value": None,
        "displayed_count_target": None,
        "displayed_denominator": None,
        "assignment_weight": 1.0 / TREATMENT_DECK_SIZE,
        "is_control": True,
    }
    return definitions


TREATMENT_DEFINITIONS = _build_treatment_definitions()
DEMO_ID_OVERRIDES = {
    bracelet_id.strip().upper(): {
        "treatment_key": str(config["treatment_key"]),
        "result_value": int(config["result_value"]),
        "payout_eligible": bool(config["payout_eligible"]),
    }
    for bracelet_id, config in EXPERIMENT_SETTINGS.get("demo_ids", {}).items()
}


def normalize_phase_key(phase_key: str | None) -> str:
    candidate = str(phase_key or "").strip()
    return PHASE_COMPATIBILITY_ALIASES.get(candidate, PHASE_1_MAIN)


def phase_config(_phase_key: str) -> dict[str, Any]:
    return {
        "label": "Diseno con 62 tratamientos individuales",
        "phase_version": PHASE_VERSION,
        "treatment_version": TREATMENT_VERSION,
        "allocation_version": ALLOCATION_VERSION,
        "displayed_message_version": DISPLAYED_MESSAGE_VERSION,
    }


def phase_treatments(_phase_key: str) -> dict[str, dict[str, Any]]:
    return TREATMENT_DEFINITIONS


def treatment_config(_phase_key: str, treatment_key: str) -> dict[str, Any]:
    normalize_phase_key(_phase_key)
    if treatment_key not in TREATMENT_DEFINITIONS:
        raise KeyError(f"Tratamiento no configurado: {treatment_key}")
    return TREATMENT_DEFINITIONS[treatment_key]


def assignment_weights_for_phase(_phase_key: str) -> dict[str, float]:
    normalize_phase_key(_phase_key)
    return {
        treatment_key: float(config["assignment_weight"])
        for treatment_key, config in TREATMENT_DEFINITIONS.items()
    }


def series_labels_for_phase(_phase_key: str) -> dict[str, str]:
    normalize_phase_key(_phase_key)
    return {
        treatment_key: str(config["label"])
        for treatment_key, config in TREATMENT_DEFINITIONS.items()
    }


def seed_initial_counts_for_phase(_phase_key: str) -> dict[str, int]:
    normalize_phase_key(_phase_key)
    return {
        treatment_key: int(config["displayed_count_target"])
        for treatment_key, config in TREATMENT_DEFINITIONS.items()
        if config["displayed_count_target"] is not None
    }


def treatment_version_for_phase(_phase_key: str) -> str:
    normalize_phase_key(_phase_key)
    return TREATMENT_VERSION


def phase_version_for_phase(_phase_key: str) -> str:
    normalize_phase_key(_phase_key)
    return PHASE_VERSION


def allocation_version_for_phase(_phase_key: str) -> str:
    normalize_phase_key(_phase_key)
    return ALLOCATION_VERSION


def displayed_message_version_for_phase(_phase_key: str) -> str:
    normalize_phase_key(_phase_key)
    return DISPLAYED_MESSAGE_VERSION


def app_pepper() -> str:
    return os.getenv("APP_HASH_PEPPER", "sonar-2026-local-pepper")


def experiment_master_seed() -> str:
    return os.getenv("EXPERIMENT_MASTER_SEED", "sonar-2026-master-seed")


def normalize_bracelet_id(raw_id: str) -> str:
    normalized = raw_id.strip().upper()
    if not BRACELET_PATTERN.fullmatch(normalized):
        raise ValueError(
            "El formato de pulsera no es valido. Usa 8 caracteres con 4 letras y 4 numeros."
        )
    return normalized


def stable_hash(raw_value: str) -> str:
    return hashlib.sha256(f"{app_pepper()}::{raw_value}".encode("utf-8")).hexdigest()


def stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def deterministic_seed(*parts: Any) -> str:
    joined = ":".join(str(part) for part in parts)
    return hashlib.sha256(
        f"{experiment_master_seed()}::{joined}".encode("utf-8")
    ).hexdigest()


def deck_commitment(deck_seed: str) -> str:
    return hashlib.sha256(f"deck::{deck_seed}".encode("utf-8")).hexdigest()


def shuffle_values(values: list[Any], deck_seed: str) -> list[Any]:
    rng = random.Random(deck_seed)
    shuffled = values[:]
    rng.shuffle(shuffled)
    return shuffled


def treatment_deck_seed(deck_index: int) -> str:
    return deterministic_seed("treatment_deck", deck_index)


def result_deck_seed(treatment_key: str, treatment_cycle_index: int) -> str:
    return deterministic_seed("result_deck", treatment_key, treatment_cycle_index)


def payment_deck_seed(deck_index: int) -> str:
    return deterministic_seed("payment_deck", deck_index)


def treatment_deck_values(deck_seed: str) -> list[str]:
    return shuffle_values(TREATMENT_KEYS, deck_seed)


def result_deck_values(deck_seed: str) -> list[int]:
    values: list[int] = []
    for block_index in range(4):
        block_seed = deterministic_seed("result_deck_block", deck_seed, block_index)
        values.extend(shuffle_values([1, 2, 3, 4, 5, 6], block_seed))
    return values


def payment_deck_values(deck_seed: str) -> list[bool]:
    values = [True] * PAYMENT_WINNERS_PER_DECK + [False] * (
        PAYMENT_DECK_SIZE - PAYMENT_WINNERS_PER_DECK
    )
    return shuffle_values(values, deck_seed)


def reroll_value_for_session(session_id: str, attempt_index: int) -> int:
    rng = random.Random(deterministic_seed("reroll", session_id, attempt_index))
    return rng.randint(1, 6)


def balanced_sequence(root_seed: str, attempt_index: int, max_positions: int) -> list[int]:
    sequence: list[int] = []
    if attempt_index == 1:
        block_index = 0
        while len(sequence) < max_positions:
            block_seed = hashlib.sha256(
                f"{root_seed}:result_block:{block_index}".encode("utf-8")
            ).hexdigest()
            sequence.extend(result_deck_values(block_seed))
            block_index += 1
        return sequence[:max_positions]

    for position_index in range(1, max_positions + 1):
        seed = deterministic_seed("reroll-compat", root_seed, position_index, attempt_index)
        rng = random.Random(seed)
        sequence.append(rng.randint(1, 6))
    return sequence


def payout_eligible(root_seed: str, position_index: int) -> bool:
    block_index = (position_index - 1) // PAYMENT_DECK_SIZE
    block_seed = hashlib.sha256(
        f"{root_seed}:payment_block:{block_index}".encode("utf-8")
    ).hexdigest()
    winners = payment_deck_values(block_seed)
    block_position = (position_index - 1) % PAYMENT_DECK_SIZE
    return winners[block_position]


def payout_amount_for_claim(claimed_value: int, eligible: bool) -> int:
    return PRIZE_EUR[claimed_value] * 100 if eligible else 0


def payout_reference_code(raw_value: str) -> str:
    digest = stable_hash(f"payout:{raw_value}")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    value = int(digest[:12], 16)
    chars: list[str] = []
    for _ in range(6):
        value, remainder = divmod(value, len(alphabet))
        chars.append(alphabet[remainder])
    return f"#{''.join(reversed(chars))}"


def referral_code(raw_value: str) -> str:
    digest = stable_hash(f"referral:{raw_value}")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    value = int(digest[:16], 16)
    chars: list[str] = []
    for _ in range(10):
        value, remainder = divmod(value, len(alphabet))
        chars.append(alphabet[remainder])
    return f"r{''.join(reversed(chars))}"


def commitment_hash(*parts: Any) -> str:
    raw = ":".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seed_window_values(_phase_key: str, _treatment_key: str) -> list[int]:
    return []


def treatment_message(
    treatment_key: str,
    count_target: int | None,
    denominator: int | None,
    target_value: int | None,
) -> str:
    if treatment_key == CONTROL_TREATMENT_KEY:
        return COPY_SETTINGS["messages"]["control"]
    template = COPY_SETTINGS["messages"]["social_template"]
    return template.format(
        count=count_target,
        denominator=denominator,
        target=target_value,
    )


def demo_override(bracelet_id: str) -> dict[str, Any] | None:
    return DEMO_ID_OVERRIDES.get(bracelet_id.strip().upper())


def public_copy() -> dict[str, Any]:
    return COPY_SETTINGS


def public_support() -> dict[str, Any]:
    return SUPPORT_SETTINGS
