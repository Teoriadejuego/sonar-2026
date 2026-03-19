import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Any


PHASE_1_MAIN = "phase_1_main"
PHASE_2_ROBUSTNESS = "phase_2_robustness"


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
    block_size = int(experiment["deck_block_size"])
    max_attempts = int(experiment["max_attempts"])
    participant_limit = int(experiment["participant_limit"])
    phase_threshold = int(experiment["phase_transition_valid_completed_threshold"])
    prize_eur = experiment["prize_eur"]
    phases = experiment["phases"]

    if window_size <= 0:
        raise ValueError("window_size debe ser mayor que 0")
    if max_attempts <= 0:
        raise ValueError("max_attempts debe ser mayor que 0")
    if participant_limit <= 0:
        raise ValueError("participant_limit debe ser mayor que 0")
    if phase_threshold <= 0:
        raise ValueError("phase_transition_valid_completed_threshold debe ser mayor que 0")
    if block_size <= 0 or block_size % 6 != 0:
        raise ValueError("deck_block_size debe ser positivo y multiplo de 6")
    if sorted(int(key) for key in prize_eur.keys()) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("prize_eur debe definir valores para 1, 2, 3, 4, 5 y 6")

    if PHASE_1_MAIN not in phases or PHASE_2_ROBUSTNESS not in phases:
        raise ValueError("phases debe incluir phase_1_main y phase_2_robustness")

    for phase_key, phase_settings in phases.items():
        treatments = phase_settings["treatments"]
        if "control" not in treatments:
            raise ValueError(f"{phase_key} debe incluir el tratamiento control")
        total_weight = sum(float(item["assignment_weight"]) for item in treatments.values())
        if abs(total_weight - 1.0) > 1e-9:
            raise ValueError(f"Los pesos de {phase_key} deben sumar 1.0")
        for treatment_key, treatment in treatments.items():
            target_value = treatment["norm_target_value"]
            seed_initial_count = treatment["seed_initial_count"]
            if target_value is not None and int(target_value) not in {1, 2, 3, 4, 5, 6}:
                raise ValueError(f"{phase_key}.{treatment_key}.norm_target_value no es valido")
            if seed_initial_count is not None:
                if int(seed_initial_count) < 0 or int(seed_initial_count) > window_size:
                    raise ValueError(
                        f"{phase_key}.{treatment_key}.seed_initial_count debe estar entre 0 y window_size"
                    )
            if treatment["treatment_family"] not in {"control", "six_norm", "five_norm"}:
                raise ValueError(
                    f"{phase_key}.{treatment_key}.treatment_family no es valido"
                )


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
WINDOW_SIZE = int(EXPERIMENT_SETTINGS["window_size"])
MAX_ATTEMPTS = int(EXPERIMENT_SETTINGS["max_attempts"])
PARTICIPANT_LIMIT = int(EXPERIMENT_SETTINGS["participant_limit"])
BLOCK_SIZE = int(EXPERIMENT_SETTINGS["deck_block_size"])
DEMO_PULSERA_COUNT = int(EXPERIMENT_SETTINGS["demo_pulsera_count"])
PAYOUT_RATE_DENOMINATOR = int(EXPERIMENT_SETTINGS["payout_rate_denominator"])
COLLAPSE_CONSECUTIVE_CLAIMS = int(
    EXPERIMENT_SETTINGS["collapse_consecutive_claims"]
)
PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD = int(
    EXPERIMENT_SETTINGS["phase_transition_valid_completed_threshold"]
)
BRACELET_PATTERN = re.compile(EXPERIMENT_SETTINGS["bracelet_pattern"])
PHASES: dict[str, dict[str, Any]] = EXPERIMENT_SETTINGS["phases"]
QUALITY_THRESHOLDS = {
    key: int(value)
    for key, value in EXPERIMENT_SETTINGS["quality_thresholds"].items()
}
WINNER_WHATSAPP_PHONE = str(SUPPORT_SETTINGS["winner_whatsapp_phone"])
PRIZE_EUR = {
    int(key): int(value) for key, value in EXPERIMENT_SETTINGS["prize_eur"].items()
}


def phase_config(phase_key: str) -> dict[str, Any]:
    if phase_key not in PHASES:
        raise KeyError(f"Fase no configurada: {phase_key}")
    return PHASES[phase_key]


def phase_treatments(phase_key: str) -> dict[str, dict[str, Any]]:
    return phase_config(phase_key)["treatments"]


def treatment_config(phase_key: str, treatment_key: str) -> dict[str, Any]:
    treatments = phase_treatments(phase_key)
    if treatment_key not in treatments:
        raise KeyError(f"Tratamiento no configurado: {phase_key}/{treatment_key}")
    return treatments[treatment_key]


def assignment_weights_for_phase(phase_key: str) -> dict[str, float]:
    return {
        treatment_key: float(config["assignment_weight"])
        for treatment_key, config in phase_treatments(phase_key).items()
    }


def series_labels_for_phase(phase_key: str) -> dict[str, str]:
    return {
        treatment_key: str(config["label"])
        for treatment_key, config in phase_treatments(phase_key).items()
    }


def seed_initial_counts_for_phase(phase_key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for treatment_key, config in phase_treatments(phase_key).items():
        if config["seed_initial_count"] is not None:
            counts[treatment_key] = int(config["seed_initial_count"])
    return counts


def treatment_version_for_phase(phase_key: str) -> str:
    return str(phase_config(phase_key)["treatment_version"])


def phase_version_for_phase(phase_key: str) -> str:
    return str(phase_config(phase_key)["phase_version"])


def allocation_version_for_phase(phase_key: str) -> str:
    return str(phase_config(phase_key)["allocation_version"])


def displayed_message_version_for_phase(phase_key: str) -> str:
    return str(phase_config(phase_key)["displayed_message_version"])


def app_pepper() -> str:
    return os.getenv("APP_HASH_PEPPER", "sonar-2026-local-pepper")


def normalize_bracelet_id(raw_id: str) -> str:
    normalized = raw_id.strip().upper()
    if not BRACELET_PATTERN.fullmatch(normalized):
        raise ValueError("El formato de pulsera no es valido. Usa solo letras y numeros.")
    return normalized


def stable_hash(raw_value: str) -> str:
    return hashlib.sha256(f"{app_pepper()}::{raw_value}".encode("utf-8")).hexdigest()


def stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def deterministic_seed(root_sequence: int) -> str:
    base_seed = os.getenv("EXPERIMENT_MASTER_SEED", "sonar-2026-master-seed")
    return stable_hash(f"{base_seed}:{root_sequence}")


def deck_commitment(root_seed: str) -> str:
    return hashlib.sha256(f"deck::{root_seed}".encode("utf-8")).hexdigest()


def balanced_sequence(root_seed: str, attempt_index: int, max_positions: int) -> list[int]:
    rng = random.Random(f"{root_seed}:attempt:{attempt_index}")
    sequence: list[int] = []
    base_block = [1, 2, 3, 4, 5, 6] * (BLOCK_SIZE // 6)
    while len(sequence) < max_positions:
        block = base_block[:]
        rng.shuffle(block)
        sequence.extend(block)
    return sequence[:max_positions]


def payout_eligible(root_seed: str, position_index: int) -> bool:
    digest = hashlib.sha256(
        f"{root_seed}:payment:{position_index}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) % PAYOUT_RATE_DENOMINATOR == 0


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


def commitment_hash(
    root_seed: str, position_index: int, attempt_index: int, result_value: int
) -> str:
    raw = f"{root_seed}:{position_index}:{attempt_index}:{result_value}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def non_target_seed_pattern(target_value: int) -> list[int]:
    return [value for value in range(1, 7) if value != target_value]


def seed_window_values(phase_key: str, treatment_key: str) -> list[int]:
    treatment = treatment_config(phase_key, treatment_key)
    target_value = treatment["norm_target_value"]
    seed_initial_count = treatment["seed_initial_count"]

    if target_value is None or seed_initial_count is None:
        return []

    initial_target_count = int(seed_initial_count)
    non_target_count = max(0, WINDOW_SIZE - initial_target_count)
    pattern = non_target_seed_pattern(int(target_value))
    non_target_values = [
        pattern[index % len(pattern)] for index in range(non_target_count)
    ]
    target_values = [int(target_value)] * initial_target_count

    if "seed_17" in treatment_key:
        return non_target_values + target_values
    return target_values + non_target_values


def treatment_message(
    treatment_key: str,
    count_target: int | None,
    denominator: int | None,
    target_value: int | None,
) -> str:
    if treatment_key == "control":
        return COPY_SETTINGS["messages"]["control"]
    template = COPY_SETTINGS["messages"]["social_template"]
    return template.format(
        count=count_target,
        denominator=denominator,
        target=target_value,
    )


def public_copy() -> dict[str, Any]:
    return COPY_SETTINGS


def public_support() -> dict[str, Any]:
    return SUPPORT_SETTINGS
