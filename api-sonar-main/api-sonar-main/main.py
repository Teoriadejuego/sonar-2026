import csv
import hashlib
import io
import json
import threading
import time
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, func, select

from database import database_ready, engine, get_session
from experiment import (
    CAMPAIGN_CODE,
    CONTROL_TREATMENT_KEY,
    CONSENT_VERSION,
    DECK_VERSION,
    DEPLOYMENT_CONTEXT,
    DEMO_PULSERA_COUNT,
    DISPLAYED_DENOMINATOR,
    ENVIRONMENT_LABEL,
    EXPERIMENT_VERSION,
    DEFAULT_NORM_TARGET_VALUE,
    LEXICON_VERSION,
    MAX_ATTEMPTS,
    PAYMENT_VERSION,
    PARTICIPANT_LIMIT,
    PHASE_1_MAIN,
    PHASE_2_ROBUSTNESS,
    PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD,
    PRIZE_EUR,
    QUALITY_THRESHOLDS,
    SCHEMA_VERSION,
    SITE_CODE,
    TELEMETRY_VERSION,
    UI_VERSION,
    WINDOW_SIZE,
    allocation_version_for_phase,
    assignment_weights_for_phase,
    balanced_sequence,
    commitment_hash,
    deck_commitment,
    demo_override,
    deterministic_seed,
    displayed_message_version_for_phase,
    normalize_bracelet_id,
    payment_deck_seed,
    payment_deck_values,
    phase_treatments,
    phase_version_for_phase,
    public_copy,
    public_support,
    payout_amount_for_claim,
    payout_eligible,
    payout_reference_code,
    referral_code,
    reroll_value_for_session,
    result_deck_seed,
    result_deck_values,
    seed_initial_counts_for_phase,
    seed_window_values,
    series_labels_for_phase,
    stable_hash,
    stable_json,
    treatment_deck_seed,
    treatment_deck_values,
    TREATMENT_KEYS,
    treatment_config,
    treatment_message,
    treatment_version_for_phase,
    COLLAPSE_CONSECUTIVE_CLAIMS,
    PAYMENT_DECK_SIZE,
    RESULT_DECK_SIZE,
    TREATMENT_DECK_SIZE,
)
from research_admin import (
    DATASET_DESCRIPTIONS,
    build_export_bundle,
    dashboard_page_html,
    dataset_export_stats,
    dataset_rows,
    export_filename,
    exports_page_html,
    rows_to_csv_bytes,
)
from models import (
    ActionReceipt,
    AuditEvent,
    Claim,
    ConsentRecord,
    DeckPosition,
    ExperimentState,
    FraudFlag,
    InterestSignup,
    OperationalNote,
    Payment,
    PaymentDeck,
    PaymentDeckCard,
    PayoutRequest,
    Pulsera,
    ResultDeck,
    ResultDeckCard,
    Series,
    SeriesRoot,
    SeriesWindowEntry,
    SessionRecord,
    SessionClientContext,
    SnapshotRecord,
    ScreenSpell,
    TelemetryEvent,
    TreatmentDeck,
    TreatmentDeckCard,
    Throw,
    User,
    make_uuid,
)
from runtime import (
    cache_receipt,
    check_admin_credentials,
    distributed_lock,
    get_cached_receipt,
    get_experiment_status_cache,
    logger,
    rate_limit,
    redis_ping,
    request_log_payload,
    set_experiment_status_cache,
)
from settings import settings

app = FastAPI(title="Sonar Experimental API")

_STARTUP_STATE_UNSET = object()
_startup_state_lock = threading.Lock()
_startup_state: dict[str, Any] = {
    "initialized": False,
    "initializing": False,
    "error": None,
    "last_readiness": {
        "database_ready": False,
        "redis_ready": not settings.require_redis,
        "schema_ready": False,
    },
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def admin_and_request_logging(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        try:
            check_admin_credentials(request)
        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers or {},
            )
            logger.info(
                "http_request",
                extra={
                    "structured_payload": request_log_payload(
                        request,
                        status_code=response.status_code,
                        duration_ms=0.0,
                    )
                },
            )
            return response
    start_time = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "http_request",
        extra={
            "structured_payload": request_log_payload(
                request,
                status_code=response.status_code,
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )
        },
    )
    return response


class AccessRequest(BaseModel):
    bracelet_id: str
    consent_accepted: bool = True
    consent_age_confirmed: bool = False
    consent_info_accepted: bool = False
    consent_data_accepted: bool = False
    language: Optional[str] = None
    landing_visible_ms: Optional[int] = None
    info_panels_opened: Optional[list[str]] = None
    info_panel_durations_ms: Optional[dict[str, int]] = None
    client_installation_id: Optional[str] = None
    referral_code: Optional[str] = None
    referral_source: Optional[str] = None
    referral_medium: Optional[str] = None
    referral_campaign: Optional[str] = None
    referral_link_id: Optional[str] = None
    qr_entry_code: Optional[str] = None
    referral_path: Optional[str] = None
    consent_checkbox_order: Optional[list[str]] = None
    consent_checkbox_timestamps_ms: Optional[dict[str, int]] = None
    consent_continue_blocked_count: Optional[int] = 0
    client_context: Optional[dict[str, Any]] = None


class RollRequest(BaseModel):
    attempt_index: int = PydanticField(ge=1, le=MAX_ATTEMPTS)
    reaction_ms: Optional[int] = None
    idempotency_key: str


class PrepareReportRequest(BaseModel):
    idempotency_key: str


class SubmitReportRequest(BaseModel):
    reported_value: int = PydanticField(ge=1, le=6)
    reaction_ms: Optional[int] = None
    idempotency_key: str
    language: Optional[str] = None


class ClaimFollowupRequest(BaseModel):
    crowd_prediction_value: Optional[int] = PydanticField(default=None, ge=1, le=6)
    social_recall_count: Optional[int] = PydanticField(default=None, ge=0, le=60)
    language: Optional[str] = None


class DisplaySnapshotRequest(BaseModel):
    screen_name: str
    language: Optional[str] = None
    treatment_message_text: Optional[str] = None
    control_message_text: Optional[str] = None
    final_message_text: Optional[str] = None
    payout_reference_shown: Optional[str] = None
    payout_phone_shown: Optional[str] = None
    final_amount_eur: Optional[int] = None
    rerolls_visible: Optional[list[int]] = None


def is_social_recall_answer_correct(
    submitted_value: int,
    displayed_count_target: Optional[int],
) -> bool:
    if displayed_count_target is None:
        return False
    if submitted_value == 20:
        return 0 <= displayed_count_target <= 20
    if submitted_value == 40:
        return 21 <= displayed_count_target <= 40
    if submitted_value == 60:
        return 41 <= displayed_count_target <= 60
    return submitted_value == displayed_count_target


class PaymentLookupRequest(BaseModel):
    code: str


class PaymentSubmitRequest(BaseModel):
    code: str
    bracelet_id: str
    phone: Optional[str] = None
    language: Optional[str] = None
    donation_requested: bool = False
    message_text: Optional[str] = None


class ScreenCursorRequest(BaseModel):
    screen: str


class InterestSignupRequest(BaseModel):
    email: str = PydanticField(min_length=5, max_length=320)
    language: Optional[str] = None


class AdminExperimentControlRequest(BaseModel):
    reason: Optional[str] = None


class AdminOperationalNoteRequest(BaseModel):
    note_text: str = PydanticField(min_length=3, max_length=1000)


class TelemetryItem(BaseModel):
    event_type: str
    event_name: str
    screen_name: Optional[str] = None
    client_ts: Optional[int] = None
    event_sequence_number: Optional[int] = None
    timezone_offset_minutes: Optional[int] = None
    duration_ms: Optional[int] = None
    value: Optional[int] = None
    app_language: Optional[str] = None
    browser_language: Optional[str] = None
    spell_id: Optional[str] = None
    interaction_target: Optional[str] = None
    interaction_role: Optional[str] = None
    cta_kind: Optional[str] = None
    endpoint_name: Optional[str] = None
    request_method: Optional[str] = None
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    attempt_number: Optional[int] = None
    is_retry: bool = False
    error_name: Optional[str] = None
    network_status: Optional[str] = None
    visibility_state: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    client_context: Optional[dict[str, Any]] = None


class TelemetryBatchRequest(BaseModel):
    session_id: str
    events: list[TelemetryItem]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def parse_user_agent(raw_user_agent: str) -> dict[str, Optional[str]]:
    browser_family = "Unknown"
    browser_version: Optional[str] = None
    os_family = "Unknown"
    os_version: Optional[str] = None
    device_type = "desktop"

    browser_patterns = [
        ("Edg/", "Edge"),
        ("OPR/", "Opera"),
        ("CriOS/", "Chrome"),
        ("Chrome/", "Chrome"),
        ("FxiOS/", "Firefox"),
        ("Firefox/", "Firefox"),
        ("Version/", "Safari"),
    ]
    for marker, family in browser_patterns:
        if marker in raw_user_agent:
            browser_family = family
            browser_version = raw_user_agent.split(marker, 1)[1].split(" ", 1)[0]
            break

    if "Android" in raw_user_agent:
        os_family = "Android"
        os_version = raw_user_agent.split("Android", 1)[1].split(";", 1)[0].strip()
        device_type = "mobile" if "Mobile" in raw_user_agent else "tablet"
    elif "iPhone" in raw_user_agent:
        os_family = "iOS"
        os_version = (
            raw_user_agent.split("OS ", 1)[1].split(" ", 1)[0].replace("_", ".")
            if "OS " in raw_user_agent
            else None
        )
        device_type = "mobile"
    elif "iPad" in raw_user_agent:
        os_family = "iPadOS"
        os_version = (
            raw_user_agent.split("OS ", 1)[1].split(" ", 1)[0].replace("_", ".")
            if "OS " in raw_user_agent
            else None
        )
        device_type = "tablet"
    elif "Windows NT" in raw_user_agent:
        os_family = "Windows"
        os_version = raw_user_agent.split("Windows NT", 1)[1].split(";", 1)[0].strip()
    elif "Mac OS X" in raw_user_agent:
        os_family = "macOS"
        os_version = (
            raw_user_agent.split("Mac OS X", 1)[1].split(")", 1)[0].strip().replace("_", ".")
        )
    elif "Linux" in raw_user_agent:
        os_family = "Linux"

    if "Mobile" in raw_user_agent and device_type == "desktop":
        device_type = "mobile"
    if "Tablet" in raw_user_agent and device_type == "desktop":
        device_type = "tablet"

    return {
        "browser_family": browser_family,
        "browser_version": browser_version,
        "os_family": os_family,
        "os_version": os_version,
        "device_type": device_type,
    }


def normalize_client_context(
    raw_context: Optional[dict[str, Any]],
    request: Optional[Request] = None,
    app_language: Optional[str] = None,
) -> dict[str, Any]:
    context = dict(raw_context or {})
    raw_user_agent = context.get("user_agent_raw") or (
        request.headers.get("user-agent", "") if request else ""
    )
    parsed_ua = parse_user_agent(raw_user_agent)
    browser_language = (
        context.get("language_browser")
        or context.get("browser_language")
        or (request.headers.get("accept-language", "").split(",")[0] if request else None)
    )

    normalized = {
        "user_agent_raw": raw_user_agent or None,
        "user_agent_hash": stable_hash(raw_user_agent) if raw_user_agent else None,
        "browser_family": context.get("browser_family") or parsed_ua["browser_family"],
        "browser_version": context.get("browser_version") or parsed_ua["browser_version"],
        "os_family": context.get("os_family") or parsed_ua["os_family"],
        "os_version": context.get("os_version") or parsed_ua["os_version"],
        "device_type": context.get("device_type") or parsed_ua["device_type"],
        "platform": context.get("platform"),
        "language_browser": browser_language,
        "language_app_selected": context.get("language_app_selected") or app_language,
        "screen_width": context.get("screen_width"),
        "screen_height": context.get("screen_height"),
        "viewport_width": context.get("viewport_width"),
        "viewport_height": context.get("viewport_height"),
        "device_pixel_ratio": context.get("device_pixel_ratio"),
        "orientation": context.get("orientation"),
        "touch_capable": context.get("touch_capable"),
        "hardware_concurrency": context.get("hardware_concurrency"),
        "max_touch_points": context.get("max_touch_points"),
        "color_scheme_preference": context.get("color_scheme_preference"),
        "online_status": context.get("online_status"),
        "connection_type": context.get("connection_type"),
        "estimated_downlink": context.get("estimated_downlink"),
        "estimated_rtt": context.get("estimated_rtt"),
        "timezone_offset_minutes": context.get("timezone_offset_minutes"),
    }
    normalized["context_json"] = stable_json(
        {
            key: value
            for key, value in normalized.items()
            if key not in {"user_agent_raw", "user_agent_hash", "context_json"}
            and value is not None
        }
    )
    return normalized


def upsert_session_client_context(
    db: Session,
    *,
    session_id: str,
    raw_context: Optional[dict[str, Any]],
    request: Optional[Request] = None,
    app_language: Optional[str] = None,
) -> Optional[SessionClientContext]:
    normalized = normalize_client_context(raw_context, request=request, app_language=app_language)
    if not any(value is not None for key, value in normalized.items() if key != "context_json"):
        return None

    context_record = db.exec(
        select(SessionClientContext).where(SessionClientContext.session_id == session_id)
    ).first()
    if not context_record:
        context_record = SessionClientContext(session_id=session_id)

    for key, value in normalized.items():
        setattr(context_record, key, value)
    context_record.updated_at = utcnow()
    if not context_record.captured_at:
        context_record.captured_at = utcnow()
    db.add(context_record)
    db.flush()
    return context_record


def schema_needs_reset() -> bool:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required_tables = {
        "experiment_state",
        "pulsera",
        "users",
        "series_roots",
        "series",
        "series_window_entries",
        "deck_positions",
        "treatment_decks",
        "treatment_deck_cards",
        "result_decks",
        "result_deck_cards",
        "payment_decks",
        "payment_deck_cards",
        "sessions",
        "throws",
        "claims",
        "payments",
        "consent_records",
        "snapshot_records",
        "session_client_contexts",
        "screen_spells",
        "payout_requests",
        "interest_signups",
        "telemetry_events",
        "fraud_flags",
        "audit_events",
        "action_receipts",
    }
    if not required_tables.issubset(tables):
        return True

    sessions_columns = {column["name"] for column in inspector.get_columns("sessions")}
    roots_columns = {column["name"] for column in inspector.get_columns("series_roots")}
    series_columns = {column["name"] for column in inspector.get_columns("series")}
    treatment_deck_columns = {
        column["name"] for column in inspector.get_columns("treatment_decks")
    }
    treatment_deck_card_columns = {
        column["name"] for column in inspector.get_columns("treatment_deck_cards")
    }
    result_deck_columns = {
        column["name"] for column in inspector.get_columns("result_decks")
    }
    result_deck_card_columns = {
        column["name"] for column in inspector.get_columns("result_deck_cards")
    }
    payment_deck_columns = {
        column["name"] for column in inspector.get_columns("payment_decks")
    }
    payment_deck_card_columns = {
        column["name"] for column in inspector.get_columns("payment_deck_cards")
    }
    claims_columns = {column["name"] for column in inspector.get_columns("claims")}
    consent_columns = {column["name"] for column in inspector.get_columns("consent_records")}
    snapshot_columns = {column["name"] for column in inspector.get_columns("snapshot_records")}
    client_context_columns = {
        column["name"] for column in inspector.get_columns("session_client_contexts")
    }
    screen_spell_columns = {
        column["name"] for column in inspector.get_columns("screen_spells")
    }
    telemetry_columns = {
        column["name"] for column in inspector.get_columns("telemetry_events")
    }
    payout_request_columns = {column["name"] for column in inspector.get_columns("payout_requests")}
    experiment_state_columns = {
        column["name"] for column in inspector.get_columns("experiment_state")
    }
    interest_signup_columns = {
        column["name"] for column in inspector.get_columns("interest_signups")
    }
    required_experiment_state_columns = {
        "experiment_status",
        "paused_at",
        "resumed_at",
        "pause_reason",
    }
    required_session_columns = {
        "experiment_version",
        "experiment_phase",
        "phase_version",
        "phase_activation_status",
        "ui_version",
        "consent_version",
        "treatment_text_version",
        "deck_version",
        "payment_version",
        "telemetry_version",
        "lexicon_version",
        "treatment_family",
        "treatment_type",
        "norm_target_value",
        "displayed_count_target",
        "displayed_denominator",
        "treatment_deck_id",
        "treatment_card_position",
        "result_deck_id",
        "result_card_position",
        "payment_deck_id",
        "payment_card_position",
        "language_at_access",
        "language_at_claim",
        "language_changed_during_session",
        "deployment_context",
        "site_code",
        "campaign_code",
        "environment_label",
        "report_snapshot_count_target",
        "report_snapshot_target_value",
        "report_snapshot_message_version",
        "is_valid_completed",
        "valid_completed_at",
        "treatment_key",
        "position_index",
        "report_snapshot_treatment",
        "quality_flags_json",
        "antifraud_flags_json",
        "referral_code",
        "invited_by_session_id",
        "referral_source",
        "referral_medium",
        "referral_campaign",
        "referral_link_id",
        "referral_arrived_at",
        "consent_age_confirmed",
        "consent_info_accepted",
        "consent_data_accepted",
        "consent_accepted_at",
        "retry_count",
        "click_count_total",
        "screen_changes_count",
        "language_change_count",
        "telemetry_event_count",
        "max_event_sequence_number",
    }
    required_root_columns = {
        "experiment_phase",
        "treatment_version",
        "allocation_version",
    }
    required_treatment_deck_columns = {
        "deck_index",
        "deck_seed",
        "legacy_root_id",
        "card_count",
        "status",
    }
    required_treatment_deck_card_columns = {
        "deck_id",
        "legacy_series_id",
        "card_position",
        "treatment_key",
        "assigned_session_id",
        "assigned_at",
    }
    required_result_deck_columns = {
        "deck_index",
        "deck_seed",
        "treatment_key",
        "treatment_cycle_index",
        "card_count",
        "status",
    }
    required_result_deck_card_columns = {
        "deck_id",
        "card_position",
        "result_value",
        "assigned_session_id",
        "assigned_at",
    }
    required_payment_deck_columns = {
        "deck_index",
        "deck_seed",
        "card_count",
        "status",
    }
    required_payment_deck_card_columns = {
        "deck_id",
        "card_position",
        "payout_eligible",
        "assigned_session_id",
        "assigned_at",
    }
    required_series_columns = {
        "experiment_phase",
        "treatment_family",
        "norm_target_value",
        "visible_count_target",
        "actual_count_target",
        "full_target_streak",
    }
    required_claim_columns = {
        "experiment_phase",
        "phase_activation_status",
        "treatment_version",
        "allocation_version",
        "treatment_family",
        "norm_target_value",
        "displayed_count_target",
        "displayed_target_value",
        "displayed_message_version",
        "crowd_prediction_value",
        "crowd_prediction_submitted_at",
        "social_recall_count",
        "social_recall_correct",
        "social_recall_submitted_at",
    }
    required_consent_columns = {
        "consent_version",
        "language_at_access",
        "landing_visible_ms",
        "info_panels_opened_json",
        "info_panel_durations_json",
        "info_panel_open_count",
        "checkbox_order_json",
        "checkbox_timestamps_json",
        "continue_blocked_count",
    }
    required_snapshot_columns = {
        "language_used",
        "is_control",
        "displayed_message_text",
        "control_message_text",
        "final_message_text",
        "payout_reference_shown",
        "all_values_seen_json",
    }
    required_client_context_columns = {
        "user_agent_raw",
        "browser_family",
        "browser_version",
        "os_family",
        "os_version",
        "device_type",
        "language_browser",
        "language_app_selected",
        "screen_width",
        "viewport_width",
        "orientation",
        "touch_capable",
        "timezone_offset_minutes",
        "context_json",
    }
    required_screen_spell_columns = {
        "spell_id",
        "screen_name",
        "duration_total_ms",
        "visible_ms",
        "hidden_ms",
        "blur_ms",
        "click_count",
        "primary_click_count",
        "secondary_click_count",
        "entered_via_resume",
        "language_changed_during_spell",
    }
    required_telemetry_columns = {
        "event_sequence_number",
        "timezone_offset_minutes",
        "client_clock_skew_estimate_ms",
        "app_language",
        "browser_language",
        "spell_id",
        "interaction_target",
        "cta_kind",
        "endpoint_name",
        "request_method",
        "status_code",
        "latency_ms",
        "attempt_number",
        "is_retry",
        "error_name",
    }
    required_payout_request_columns = {
        "requested_phone",
        "donation_requested",
        "language_used",
        "message_text",
    }
    required_interest_signup_columns = {
        "email_normalized",
        "email_hash",
        "language_used",
        "source_screen",
        "experiment_status",
        "deployment_context",
        "site_code",
        "campaign_code",
        "environment_label",
    }
    return (
        not required_experiment_state_columns.issubset(experiment_state_columns)
        or
        not required_session_columns.issubset(sessions_columns)
        or not required_root_columns.issubset(roots_columns)
        or not required_treatment_deck_columns.issubset(treatment_deck_columns)
        or not required_treatment_deck_card_columns.issubset(
            treatment_deck_card_columns
        )
        or not required_result_deck_columns.issubset(result_deck_columns)
        or not required_result_deck_card_columns.issubset(result_deck_card_columns)
        or not required_payment_deck_columns.issubset(payment_deck_columns)
        or not required_payment_deck_card_columns.issubset(payment_deck_card_columns)
        or not required_series_columns.issubset(series_columns)
        or not required_claim_columns.issubset(claims_columns)
        or not required_consent_columns.issubset(consent_columns)
        or not required_snapshot_columns.issubset(snapshot_columns)
        or not required_client_context_columns.issubset(client_context_columns)
        or not required_screen_spell_columns.issubset(screen_spell_columns)
        or not required_telemetry_columns.issubset(telemetry_columns)
        or not required_payout_request_columns.issubset(payout_request_columns)
        or not required_interest_signup_columns.issubset(interest_signup_columns)
    )


def drop_legacy_tables() -> None:
    inspector = inspect(engine)
    current_tables = set(inspector.get_table_names())
    expected_tables = set(SQLModel.metadata.tables.keys())
    legacy_tables = sorted(current_tables - expected_tables)
    if not legacy_tables:
        return

    with engine.begin() as connection:
        for table_name in legacy_tables:
            connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))


def get_or_create_pulseras(db: Session) -> None:
    desired_ids = ["CTRL1234", "NORM0000", "NORM0001"]
    existing_ids = set(
        db.exec(select(Pulsera.id).where(Pulsera.id.in_(desired_ids))).all()
    )
    missing = [
        Pulsera(id=bracelet_id)
        for bracelet_id in desired_ids
        if bracelet_id not in existing_ids
    ]
    if not missing:
        return
    db.add_all(missing)
    db.flush()


def create_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    session_id: Optional[str] = None,
    old_state: Optional[str] = None,
    new_state: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        AuditEvent(
            session_id=session_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_state=old_state,
            new_state=new_state,
            idempotency_key=idempotency_key,
            payload_json=json.dumps(payload) if payload is not None else None,
        )
    )


def create_fraud_flag(
    db: Session,
    *,
    flag_key: str,
    severity: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        FraudFlag(
            session_id=session_id,
            user_id=user_id,
            flag_key=flag_key,
            severity=severity,
            payload_json=json.dumps(payload) if payload is not None else None,
        )
    )


def get_existing_receipt(
    db: Session, *, session_id: str, endpoint: str, idempotency_key: str
) -> Optional[dict[str, Any]]:
    cached = get_cached_receipt(endpoint, session_id, idempotency_key)
    if cached:
        return cached
    receipt = db.exec(
        select(ActionReceipt).where(
            ActionReceipt.session_id == session_id,
            ActionReceipt.endpoint == endpoint,
            ActionReceipt.idempotency_key == idempotency_key,
        )
    ).first()
    if receipt:
        return json.loads(receipt.response_json)
    return None


def save_receipt(
    db: Session,
    *,
    session_id: str,
    endpoint: str,
    idempotency_key: str,
    response_payload: dict[str, Any],
) -> None:
    cache_receipt(endpoint, session_id, idempotency_key, response_payload)
    db.add(
        ActionReceipt(
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            response_json=json.dumps(response_payload),
        )
    )


def with_optional_for_update(statement, enabled: bool):
    return statement.with_for_update() if enabled and not settings.database_is_sqlite else statement


def get_session_or_404(db: Session, session_id: str, *, for_update: bool = False) -> SessionRecord:
    record = db.exec(
        with_optional_for_update(
            select(SessionRecord).where(SessionRecord.id == session_id),
            for_update,
        )
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return record


def get_series_or_404(db: Session, series_id: str, *, for_update: bool = False) -> Series:
    series = db.exec(
        with_optional_for_update(
            select(Series).where(Series.id == series_id),
            for_update,
        )
    ).first()
    if not series:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    return series


def get_or_create_experiment_state(db: Session, *, for_update: bool = False) -> ExperimentState:
    state = db.exec(
        with_optional_for_update(
            select(ExperimentState).where(ExperimentState.id == "global"),
            for_update,
        )
    ).first()
    if state:
        changed = False
        if state.current_phase != PHASE_1_MAIN:
            state.current_phase = PHASE_1_MAIN
            changed = True
        expected_treatment_version = treatment_version_for_phase(PHASE_1_MAIN)
        expected_allocation_version = allocation_version_for_phase(PHASE_1_MAIN)
        if state.phase_transition_threshold != PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD:
            state.phase_transition_threshold = PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD
            changed = True
        if state.treatment_version != expected_treatment_version:
            state.treatment_version = expected_treatment_version
            changed = True
        if state.allocation_version != expected_allocation_version:
            state.allocation_version = expected_allocation_version
            changed = True
        if changed:
            state.updated_at = utcnow()
            db.add(state)
        return state

    state = ExperimentState(
        id="global",
        current_phase=PHASE_1_MAIN,
        experiment_status="active",
        phase_transition_threshold=PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD,
        valid_completed_count=0,
        treatment_version=treatment_version_for_phase(PHASE_1_MAIN),
        allocation_version=allocation_version_for_phase(PHASE_1_MAIN),
    )
    db.add(state)
    return state


def normalize_email(raw_email: str) -> str:
    normalized = raw_email.strip().lower()
    if "@" not in normalized or "." not in normalized.split("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="Email no valido")
    if len(normalized) > 320:
        raise HTTPException(status_code=400, detail="Email no valido")
    return normalized


def experiment_is_paused(state: ExperimentState) -> bool:
    return state.experiment_status == "paused"


def ensure_experiment_accepting_entries(db: Session) -> ExperimentState:
    state = get_or_create_experiment_state(db)
    cached_status = get_experiment_status_cache()
    if cached_status and cached_status.get("status") == "paused":
        raise HTTPException(
            status_code=423,
            detail="El experimento esta temporalmente detenido",
        )
    if experiment_is_paused(state):
        raise HTTPException(
            status_code=423,
            detail="El experimento esta temporalmente detenido",
        )
    return state


def prize_summary(db: Session) -> dict[str, Any]:
    payments = db.exec(select(Payment)).all()
    eligible_payments = [item for item in payments if item.eligible]
    total_amount_cents = sum(item.amount_cents for item in eligible_payments)
    by_status: dict[str, int] = {}
    for payment in eligible_payments:
        by_status[payment.status] = by_status.get(payment.status, 0) + 1
    return {
        "winner_count": len(eligible_payments),
        "total_prize_amount_cents": total_amount_cents,
        "total_prize_amount_eur": round(total_amount_cents / 100, 2),
        "winner_count_by_status": by_status,
    }


def experiment_control_payload(state: ExperimentState) -> dict[str, Any]:
    return {
        "status": state.experiment_status,
        "paused": state.experiment_status == "paused",
        "paused_at": state.paused_at.isoformat() if state.paused_at else None,
    }


def build_config_payload(db: Session) -> dict[str, Any]:
    experiment_state = get_or_create_experiment_state(db)
    current_phase = experiment_state.current_phase
    treatment_definitions = phase_treatments(current_phase)
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "ui_version": UI_VERSION,
        "consent_version": CONSENT_VERSION,
        "deck_version": DECK_VERSION,
        "payment_version": PAYMENT_VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        "lexicon_version": LEXICON_VERSION,
        "current_phase": current_phase,
        "phase_transition_threshold": PHASE_TRANSITION_VALID_COMPLETED_THRESHOLD,
        "max_attempts": MAX_ATTEMPTS,
        "participant_limit": PARTICIPANT_LIMIT,
        "window_size": WINDOW_SIZE,
        "displayed_denominator": DISPLAYED_DENOMINATOR,
        "treatment_deck_size": TREATMENT_DECK_SIZE,
        "result_deck_size": RESULT_DECK_SIZE,
        "payment_deck_size": PAYMENT_DECK_SIZE,
        "payment_winners_per_deck": 1,
        "prize_eur": PRIZE_EUR,
        "treatments": list(TREATMENT_KEYS),
        "seed_initial_counts": {
            treatment_key: int(config["displayed_count_target"])
            for treatment_key, config in treatment_definitions.items()
            if config["displayed_count_target"] is not None
        },
        "treatment_display_counts": {
            treatment_key: config["displayed_count_target"]
            for treatment_key, config in treatment_definitions.items()
        },
        "treatment_targets": {
            treatment_key: treatment["norm_target_value"]
            for treatment_key, treatment in treatment_definitions.items()
        },
        "collapse_consecutive_claims": 0,
        "treatment_version": treatment_version_for_phase(current_phase),
        "allocation_version": allocation_version_for_phase(current_phase),
        "deployment_context": DEPLOYMENT_CONTEXT,
        "site_code": SITE_CODE,
        "campaign_code": CAMPAIGN_CODE,
        "environment_label": ENVIRONMENT_LABEL,
        "demo_ids": {
            "winner_control": "CTRL1234",
            "loser_norm_0": "NORM0000",
            "loser_norm_1": "NORM0001",
        },
        "experiment_control": experiment_control_payload(experiment_state),
        "copy": public_copy(),
        "support": public_support(),
    }


def deck_status_payload(
    db: Session,
    *,
    deck_model: Any,
    card_model: Any,
) -> dict[str, Any]:
    active_decks = db.exec(
        select(deck_model)
        .where(deck_model.status == "active")
        .order_by(deck_model.deck_index)
    ).all()
    if not active_decks:
        return {
            "active_deck_index": None,
            "active_deck_indices": [],
            "active_deck_count": 0,
            "assigned_cards": 0,
            "remaining_cards": 0,
            "card_count": 0,
            "closed_decks": db.exec(
                select(func.count()).select_from(deck_model).where(deck_model.status == "closed")
            ).one(),
        }
    active_deck_ids = [deck.id for deck in active_decks]
    assigned_cards = db.exec(
        select(func.count())
        .select_from(card_model)
        .where(
            card_model.deck_id.in_(active_deck_ids),
            card_model.assigned_session_id != None,  # noqa: E711
        )
    ).one()
    assigned_count = int(assigned_cards or 0)
    card_count = sum(int(deck.card_count) for deck in active_decks)
    payload = {
        "active_deck_index": active_decks[0].deck_index,
        "active_deck_indices": [deck.deck_index for deck in active_decks],
        "active_deck_count": len(active_decks),
        "assigned_cards": assigned_count,
        "remaining_cards": max(card_count - assigned_count, 0),
        "card_count": card_count,
        "closed_decks": int(
            db.exec(
                select(func.count())
                .select_from(deck_model)
                .where(deck_model.status == "closed")
            ).one()
            or 0
        ),
    }
    if hasattr(deck_model, "treatment_key"):
        payload["active_treatment_keys"] = [
            getattr(deck, "treatment_key", None) for deck in active_decks
        ]
    return payload


def get_active_operational_note(
    db: Session, *, for_update: bool = False
) -> Optional[OperationalNote]:
    return db.exec(
        with_optional_for_update(
            select(OperationalNote)
            .where(OperationalNote.status == "active")
            .order_by(OperationalNote.effective_from.desc()),
            for_update,
        )
    ).first()


def operational_note_payload(note: Optional[OperationalNote]) -> dict[str, Any]:
    if not note:
        return {
            "id": None,
            "note_text": None,
            "status": "inactive",
            "effective_from": None,
            "cleared_at": None,
        }
    return {
        "id": note.id,
        "note_text": note.note_text,
        "status": note.status,
        "effective_from": note.effective_from.isoformat(),
        "cleared_at": note.cleared_at.isoformat() if note.cleared_at else None,
    }


def activate_operational_note(db: Session, *, note_text: str) -> OperationalNote:
    now = utcnow()
    previous = get_active_operational_note(db, for_update=True)
    if previous:
        previous.status = "ended"
        previous.cleared_at = now
        previous.updated_at = now
        db.add(previous)

    note = OperationalNote(
        note_text=note_text.strip(),
        status="active",
        effective_from=now,
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.flush()
    create_audit(
        db,
        entity_type="operational_note",
        entity_id=note.id,
        action="operational_note_activated",
        payload={"note_text": note.note_text, "effective_from": note.effective_from.isoformat()},
    )
    db.commit()
    db.refresh(note)
    return note


def clear_operational_note(db: Session) -> Optional[OperationalNote]:
    note = get_active_operational_note(db, for_update=True)
    if not note:
        return None
    now = utcnow()
    note.status = "ended"
    note.cleared_at = now
    note.updated_at = now
    db.add(note)
    create_audit(
        db,
        entity_type="operational_note",
        entity_id=note.id,
        action="operational_note_cleared",
        payload={"cleared_at": now.isoformat()},
    )
    db.commit()
    db.refresh(note)
    return note


def pause_experiment(
    db: Session,
    *,
    reason: Optional[str],
) -> ExperimentState:
    state = get_or_create_experiment_state(db)
    if state.experiment_status == "paused":
        return state
    old_status = state.experiment_status
    state.experiment_status = "paused"
    state.paused_at = utcnow()
    state.pause_reason = reason.strip() if reason else None
    state.updated_at = utcnow()
    db.add(state)
    create_audit(
        db,
        entity_type="experiment",
        entity_id=state.id,
        action="experiment_paused",
        old_state=old_status,
        new_state=state.experiment_status,
        payload={
            "reason": state.pause_reason,
            "paused_at": state.paused_at.isoformat() if state.paused_at else None,
        },
    )
    db.commit()
    db.refresh(state)
    set_experiment_status_cache(state.experiment_status, state.pause_reason)
    return state


def resume_experiment(
    db: Session,
    *,
    reason: Optional[str],
) -> ExperimentState:
    state = get_or_create_experiment_state(db)
    if state.experiment_status == "active":
        return state
    old_status = state.experiment_status
    state.experiment_status = "active"
    state.resumed_at = utcnow()
    state.updated_at = utcnow()
    state.pause_reason = None
    db.add(state)
    create_audit(
        db,
        entity_type="experiment",
        entity_id=state.id,
        action="experiment_resumed",
        old_state=old_status,
        new_state=state.experiment_status,
        payload={
            "reason": reason.strip() if reason else None,
            "resumed_at": state.resumed_at.isoformat() if state.resumed_at else None,
        },
    )
    db.commit()
    db.refresh(state)
    set_experiment_status_cache(state.experiment_status, None)
    return state


def current_phase_activation_status(phase_key: str) -> str:
    if phase_key == PHASE_1_MAIN:
        return "balanced_decks_active_at_assignment"
    return "legacy_disabled"


def series_target_value(series: Series) -> Optional[int]:
    return series.norm_target_value


def legacy_root_status(deck_status: str) -> str:
    if deck_status == "active":
        return "active"
    if deck_status == "demo":
        return "demo"
    return "closed"


def legacy_root_for_sequence(
    db: Session, *, root_sequence: int, for_update: bool = False
) -> Optional[SeriesRoot]:
    return db.exec(
        with_optional_for_update(
            select(SeriesRoot).where(SeriesRoot.root_sequence == root_sequence),
            for_update,
        )
    ).first()


def create_root_with_series(
    db: Session,
    phase_key: str,
    *,
    root_sequence: int,
    treatment_keys: list[str],
    deck_status: str = "active",
) -> SeriesRoot:
    root = SeriesRoot(
        root_sequence=root_sequence,
        experiment_phase=phase_key,
        treatment_version=treatment_version_for_phase(phase_key),
        allocation_version=allocation_version_for_phase(phase_key),
        status=legacy_root_status(deck_status),
        close_reason="demo_override" if deck_status == "demo" else None,
        deck_seed_commitment=deck_commitment(
            treatment_deck_seed(root_sequence)
            if root_sequence > 0
            else deterministic_seed("demo_root", root_sequence)
        ),
        experiment_version=EXPERIMENT_VERSION,
        closed_at=utcnow() if deck_status == "closed" else None,
    )
    db.add(root)
    db.flush()

    for treatment_key in treatment_keys:
        treatment = treatment_config(phase_key, treatment_key)
        displayed_count_target = treatment["displayed_count_target"]
        series = Series(
            root_id=root.id,
            experiment_phase=phase_key,
            treatment_key=treatment_key,
            treatment_family=treatment["treatment_family"],
            norm_target_value=treatment["norm_target_value"],
            label=series_labels_for_phase(phase_key)[treatment_key],
            assignment_weight=float(treatment["assignment_weight"]),
            participant_limit=1,
            sample_size=DISPLAYED_DENOMINATOR,
            position_counter=0,
            completed_count=0,
            visible_count_target=int(displayed_count_target or 0),
            actual_count_target=0,
            full_target_streak=0,
            visible_window_version=1 if displayed_count_target is not None else 0,
            actual_window_version=0,
            is_closed=deck_status == "closed",
            close_reason="demo_override" if deck_status == "demo" else None,
        )
        db.add(series)
    db.flush()
    return root


def max_positive_deck_index(db: Session, model: Any) -> int:
    current_max = db.exec(
        select(func.max(model.deck_index)).where(model.deck_index > 0)
    ).one()
    return int(current_max) if current_max is not None else 0


def max_positive_root_sequence(db: Session) -> int:
    current_max = db.exec(
        select(func.max(SeriesRoot.root_sequence)).where(SeriesRoot.root_sequence > 0)
    ).one()
    return int(current_max) if current_max is not None else 0


def close_legacy_root(db: Session, root_id: Optional[str], reason: str) -> None:
    if not root_id:
        return
    root = db.get(SeriesRoot, root_id)
    if not root or root.status == "closed":
        return
    root.status = "closed"
    root.close_reason = reason
    root.closed_at = utcnow()
    db.add(root)
    for series in db.exec(select(Series).where(Series.root_id == root.id)).all():
        series.is_closed = True
        series.close_reason = reason
        db.add(series)


def get_series_for_treatment_root(
    db: Session, *, root_id: str, treatment_key: str
) -> Series:
    series = db.exec(
        select(Series).where(
            Series.root_id == root_id,
            Series.treatment_key == treatment_key,
        )
    ).first()
    if not series:
        raise HTTPException(
            status_code=500,
            detail="No existe la serie legacy para el tratamiento asignado",
        )
    return series


def create_treatment_deck(db: Session, deck_index: int) -> TreatmentDeck:
    deck_seed = treatment_deck_seed(deck_index)
    deck_values = treatment_deck_values(deck_seed)
    legacy_root = create_root_with_series(
        db,
        PHASE_1_MAIN,
        root_sequence=deck_index,
        treatment_keys=TREATMENT_KEYS,
        deck_status="active",
    )
    deck = TreatmentDeck(
        deck_index=deck_index,
        deck_seed=deck_seed,
        legacy_root_id=legacy_root.id,
        card_count=len(deck_values),
        status="active",
    )
    db.add(deck)
    db.flush()

    for card_position, treatment_key in enumerate(deck_values, start=1):
        legacy_series = get_series_for_treatment_root(
            db, root_id=legacy_root.id, treatment_key=treatment_key
        )
        db.add(
            TreatmentDeckCard(
                deck_id=deck.id,
                legacy_series_id=legacy_series.id,
                card_position=card_position,
                treatment_key=treatment_key,
            )
        )
    db.flush()
    return deck


def create_result_deck(
    db: Session,
    *,
    deck_index: int,
    treatment_key: str,
    treatment_cycle_index: int,
) -> ResultDeck:
    deck_seed = result_deck_seed(treatment_key, treatment_cycle_index)
    deck_values = result_deck_values(deck_seed)
    deck = ResultDeck(
        deck_index=deck_index,
        deck_seed=deck_seed,
        treatment_key=treatment_key,
        treatment_cycle_index=treatment_cycle_index,
        card_count=len(deck_values),
        status="active",
    )
    db.add(deck)
    db.flush()
    for card_position, result_value in enumerate(deck_values, start=1):
        db.add(
            ResultDeckCard(
                deck_id=deck.id,
                card_position=card_position,
                result_value=result_value,
            )
        )
    db.flush()
    return deck


def create_payment_deck(db: Session, deck_index: int) -> PaymentDeck:
    deck_seed = payment_deck_seed(deck_index)
    deck_values = payment_deck_values(deck_seed)
    deck = PaymentDeck(
        deck_index=deck_index,
        deck_seed=deck_seed,
        card_count=len(deck_values),
        status="active",
    )
    db.add(deck)
    db.flush()
    for card_position, eligible in enumerate(deck_values, start=1):
        db.add(
            PaymentDeckCard(
                deck_id=deck.id,
                card_position=card_position,
                payout_eligible=eligible,
            )
        )
    db.flush()
    return deck


def demo_deck_index(bracelet_id: str) -> int:
    return {
        "CTRL1234": -1,
        "NORM0000": -2,
        "NORM0001": -3,
    }[bracelet_id]


def ensure_demo_treatment_deck(
    db: Session, *, bracelet_id: str, treatment_key: str
) -> TreatmentDeck:
    deck_index = demo_deck_index(bracelet_id)
    existing = db.exec(
        select(TreatmentDeck).where(TreatmentDeck.deck_index == deck_index)
    ).first()
    if existing:
        return existing

    legacy_root = create_root_with_series(
        db,
        PHASE_1_MAIN,
        root_sequence=deck_index,
        treatment_keys=[treatment_key],
        deck_status="demo",
    )
    legacy_series = get_series_for_treatment_root(
        db, root_id=legacy_root.id, treatment_key=treatment_key
    )
    deck = TreatmentDeck(
        deck_index=deck_index,
        deck_seed=deterministic_seed("demo_treatment", bracelet_id, treatment_key),
        legacy_root_id=legacy_root.id,
        card_count=1,
        status="demo",
    )
    db.add(deck)
    db.flush()
    db.add(
        TreatmentDeckCard(
            deck_id=deck.id,
            legacy_series_id=legacy_series.id,
            card_position=1,
            treatment_key=treatment_key,
        )
    )
    db.flush()
    return deck


def ensure_demo_result_deck(
    db: Session, *, bracelet_id: str, treatment_key: str, result_value: int
) -> ResultDeck:
    deck_index = demo_deck_index(bracelet_id)
    existing = db.exec(
        select(ResultDeck).where(ResultDeck.deck_index == deck_index)
    ).first()
    if existing:
        return existing
    deck = ResultDeck(
        deck_index=deck_index,
        deck_seed=deterministic_seed(
            "demo_result",
            bracelet_id,
            treatment_key,
            result_value,
        ),
        treatment_key=treatment_key,
        treatment_cycle_index=deck_index,
        card_count=1,
        status="demo",
    )
    db.add(deck)
    db.flush()
    db.add(
        ResultDeckCard(
            deck_id=deck.id,
            card_position=1,
            result_value=result_value,
        )
    )
    db.flush()
    return deck


def ensure_demo_payment_deck(
    db: Session, *, bracelet_id: str, payout_allowed: bool
) -> PaymentDeck:
    deck_index = demo_deck_index(bracelet_id)
    existing = db.exec(
        select(PaymentDeck).where(PaymentDeck.deck_index == deck_index)
    ).first()
    if existing:
        return existing
    deck = PaymentDeck(
        deck_index=deck_index,
        deck_seed=deterministic_seed("demo_payment", bracelet_id, payout_allowed),
        card_count=1,
        status="demo",
    )
    db.add(deck)
    db.flush()
    db.add(
        PaymentDeckCard(
            deck_id=deck.id,
            card_position=1,
            payout_eligible=payout_allowed,
        )
    )
    db.flush()
    return deck


def get_active_treatment_deck(db: Session) -> TreatmentDeck:
    deck = db.exec(
        with_optional_for_update(
            select(TreatmentDeck)
            .where(TreatmentDeck.status == "active")
            .order_by(TreatmentDeck.deck_index),
            True,
        )
    ).first()
    if deck:
        return deck
    next_deck_index = max(
        max_positive_deck_index(db, TreatmentDeck),
        max_positive_root_sequence(db),
    ) + 1
    return create_treatment_deck(db, next_deck_index)


def next_result_treatment_cycle_index(db: Session, *, treatment_key: str) -> int:
    latest_cycle = db.exec(
        select(func.max(ResultDeck.treatment_cycle_index)).where(
            ResultDeck.treatment_key == treatment_key,
            ResultDeck.deck_index > 0,
        )
    ).one()
    return int(latest_cycle or 0) + 1


def get_active_result_deck(db: Session, *, treatment_key: str) -> ResultDeck:
    deck = db.exec(
        with_optional_for_update(
            select(ResultDeck)
            .where(
                ResultDeck.status == "active",
                ResultDeck.treatment_key == treatment_key,
            )
            .order_by(ResultDeck.deck_index),
            True,
        )
    ).first()
    if deck:
        return deck
    return create_result_deck(
        db,
        deck_index=max_positive_deck_index(db, ResultDeck) + 1,
        treatment_key=treatment_key,
        treatment_cycle_index=next_result_treatment_cycle_index(
            db,
            treatment_key=treatment_key,
        ),
    )


def get_active_payment_deck(db: Session) -> PaymentDeck:
    deck = db.exec(
        with_optional_for_update(
            select(PaymentDeck)
            .where(PaymentDeck.status == "active")
            .order_by(PaymentDeck.deck_index),
            True,
        )
    ).first()
    if deck:
        return deck
    return create_payment_deck(db, max_positive_deck_index(db, PaymentDeck) + 1)


def close_treatment_deck(db: Session, deck: TreatmentDeck) -> None:
    if deck.status != "active":
        return
    deck.status = "closed"
    deck.closed_at = utcnow()
    db.add(deck)
    close_legacy_root(db, deck.legacy_root_id, "treatment_deck_exhausted")


def close_result_deck(db: Session, deck: ResultDeck) -> None:
    if deck.status != "active":
        return
    deck.status = "closed"
    deck.closed_at = utcnow()
    db.add(deck)


def close_payment_deck(db: Session, deck: PaymentDeck) -> None:
    if deck.status != "active":
        return
    deck.status = "closed"
    deck.closed_at = utcnow()
    db.add(deck)


def assign_next_treatment_card(
    db: Session, *, session_id: str
) -> tuple[TreatmentDeck, TreatmentDeckCard, Series]:
    while True:
        deck = get_active_treatment_deck(db)
        card = db.exec(
            with_optional_for_update(
                select(TreatmentDeckCard)
                .where(
                    TreatmentDeckCard.deck_id == deck.id,
                    TreatmentDeckCard.assigned_session_id == None,  # noqa: E711
                )
                .order_by(TreatmentDeckCard.card_position),
                True,
            )
        ).first()
        if not card:
            close_treatment_deck(db, deck)
            db.flush()
            continue
        card.assigned_session_id = session_id
        card.assigned_at = utcnow()
        db.add(card)
        legacy_series = db.get(Series, card.legacy_series_id) if card.legacy_series_id else None
        if not legacy_series:
            raise HTTPException(status_code=500, detail="Carta de tratamiento sin serie legacy")
        legacy_series.position_counter = 1
        db.add(legacy_series)
        return deck, card, legacy_series


def assign_next_result_card(
    db: Session, *, session_id: str, treatment_key: str
) -> tuple[ResultDeck, ResultDeckCard]:
    while True:
        deck = get_active_result_deck(db, treatment_key=treatment_key)
        card = db.exec(
            with_optional_for_update(
                select(ResultDeckCard)
                .where(
                    ResultDeckCard.deck_id == deck.id,
                    ResultDeckCard.assigned_session_id == None,  # noqa: E711
                )
                .order_by(ResultDeckCard.card_position),
                True,
            )
        ).first()
        if not card:
            close_result_deck(db, deck)
            db.flush()
            continue
        card.assigned_session_id = session_id
        card.assigned_at = utcnow()
        db.add(card)
        return deck, card


def assign_next_payment_card(
    db: Session, *, session_id: str
) -> tuple[PaymentDeck, PaymentDeckCard]:
    while True:
        deck = get_active_payment_deck(db)
        card = db.exec(
            with_optional_for_update(
                select(PaymentDeckCard)
                .where(
                    PaymentDeckCard.deck_id == deck.id,
                    PaymentDeckCard.assigned_session_id == None,  # noqa: E711
                )
                .order_by(PaymentDeckCard.card_position),
                True,
            )
        ).first()
        if not card:
            close_payment_deck(db, deck)
            db.flush()
            continue
        card.assigned_session_id = session_id
        card.assigned_at = utcnow()
        db.add(card)
        return deck, card


def assign_demo_cards(
    db: Session, *, bracelet_id: str, session_id: str
) -> tuple[TreatmentDeck, TreatmentDeckCard, Series, ResultDeck, ResultDeckCard, PaymentDeck, PaymentDeckCard]:
    override = demo_override(bracelet_id)
    if not override:
        raise HTTPException(status_code=500, detail="Demo override no configurado")

    treatment_deck = ensure_demo_treatment_deck(
        db,
        bracelet_id=bracelet_id,
        treatment_key=str(override["treatment_key"]),
    )
    treatment_card = db.exec(
        select(TreatmentDeckCard).where(TreatmentDeckCard.deck_id == treatment_deck.id)
    ).first()
    if not treatment_card:
        raise HTTPException(status_code=500, detail="Carta demo de tratamiento inexistente")
    treatment_card.assigned_session_id = session_id
    treatment_card.assigned_at = utcnow()
    db.add(treatment_card)
    legacy_series = db.get(Series, treatment_card.legacy_series_id)
    if not legacy_series:
        raise HTTPException(status_code=500, detail="Serie demo inexistente")
    legacy_series.position_counter = 1
    db.add(legacy_series)

    result_deck = ensure_demo_result_deck(
        db,
        bracelet_id=bracelet_id,
        treatment_key=str(override["treatment_key"]),
        result_value=int(override["result_value"]),
    )
    result_card = db.exec(
        select(ResultDeckCard).where(ResultDeckCard.deck_id == result_deck.id)
    ).first()
    if not result_card:
        raise HTTPException(status_code=500, detail="Carta demo de resultado inexistente")
    result_card.assigned_session_id = session_id
    result_card.assigned_at = utcnow()
    db.add(result_card)

    payment_deck = ensure_demo_payment_deck(
        db,
        bracelet_id=bracelet_id,
        payout_allowed=bool(override["payout_eligible"]),
    )
    payment_card = db.exec(
        select(PaymentDeckCard).where(PaymentDeckCard.deck_id == payment_deck.id)
    ).first()
    if not payment_card:
        raise HTTPException(status_code=500, detail="Carta demo de pago inexistente")
    payment_card.assigned_session_id = session_id
    payment_card.assigned_at = utcnow()
    db.add(payment_card)

    return (
        treatment_deck,
        treatment_card,
        legacy_series,
        result_deck,
        result_card,
        payment_deck,
        payment_card,
    )


def bootstrap_demo_data(db: Session) -> None:
    get_or_create_pulseras(db)
    get_or_create_experiment_state(db)
    get_active_treatment_deck(db)
    get_active_payment_deck(db)
    for bracelet_id in ["CTRL1234", "NORM0000", "NORM0001"]:
        override = demo_override(bracelet_id)
        if not override:
            continue
        ensure_demo_treatment_deck(
            db,
            bracelet_id=bracelet_id,
            treatment_key=str(override["treatment_key"]),
        )
        ensure_demo_result_deck(
            db,
            bracelet_id=bracelet_id,
            treatment_key=str(override["treatment_key"]),
            result_value=int(override["result_value"]),
        )
        ensure_demo_payment_deck(
            db,
            bracelet_id=bracelet_id,
            payout_allowed=bool(override["payout_eligible"]),
        )
    db.commit()


def get_deck_value(
    db: Session, *, root_id: str, position_index: int, attempt_index: int
) -> DeckPosition:
    deck = db.exec(
        select(DeckPosition).where(
            DeckPosition.root_id == root_id,
            DeckPosition.position_index == position_index,
            DeckPosition.attempt_index == attempt_index,
        )
    ).first()
    if not deck:
        raise HTTPException(
            status_code=500,
            detail="No existe plan preasignado para esa posicion",
        )
    return deck


def get_window_entries(
    db: Session, *, series_id: str, window_type: str
) -> list[SeriesWindowEntry]:
    return db.exec(
        select(SeriesWindowEntry)
        .where(
            SeriesWindowEntry.series_id == series_id,
            SeriesWindowEntry.window_type == window_type,
        )
        .order_by(SeriesWindowEntry.slot_index)
    ).all()


def session_has_critical_fraud(db: Session, record: SessionRecord) -> bool:
    critical_flag = db.exec(
        select(FraudFlag).where(
            FraudFlag.session_id == record.id,
            FraudFlag.severity == "critical",
        )
    ).first()
    return critical_flag is not None


def is_valid_completed_session(db: Session, record: SessionRecord) -> bool:
    if not record.consent_accepted:
        return False
    if record.first_result_value is None:
        return False
    if record.claim_submitted_at is None or record.completed_at is None:
        return False
    if record.state not in {"completed_win", "completed_no_win"}:
        return False
    if session_has_critical_fraud(db, record):
        return False
    return True


def maybe_activate_phase_2(
    db: Session,
    *,
    state: ExperimentState,
    triggering_session_id: str,
) -> bool:
    return False


def maybe_close_root(db: Session, *, root: SeriesRoot, reason: str) -> None:
    if root.status != "active":
        return
    root.status = "closed"
    root.close_reason = reason
    root.closed_at = utcnow()
    db.add(root)
    series_items = db.exec(select(Series).where(Series.root_id == root.id)).all()
    for series in series_items:
        series.is_closed = True
        if not series.close_reason:
            series.close_reason = reason
        db.add(series)
    create_audit(
        db,
        entity_type="root",
        entity_id=root.id,
        action="root_closed",
        payload={"reason": reason, "root_sequence": root.root_sequence},
    )


def ensure_valid_state(
    record: SessionRecord, allowed_states: set[str], action: str
) -> None:
    if record.state not in allowed_states:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Estado invalido para {action}",
                "server_state": record.state,
                "screen": record.screen_cursor,
            },
        )


def build_quality_flags(db: Session, record: SessionRecord) -> list[str]:
    flags: list[str] = []
    events = db.exec(
        select(TelemetryEvent).where(TelemetryEvent.session_id == record.id)
    ).all()
    screen_durations = {
        screen: int(metrics.get("visible_ms") or metrics.get("duration_total_ms") or 0)
        for screen, metrics in build_screen_metrics_summary(db, record.id).items()
    }

    if record.claim_submitted_at is not None and record.report_prepared_at is None:
        flags.append("submit_without_prepare")
    if record.reroll_count >= 3:
        flags.append("reroll_ge_3")
    if record.reroll_count >= 5:
        flags.append("reroll_ge_5")
    if record.blur_count >= 1:
        flags.append("blur_pre_claim")
    if record.blur_count >= 2:
        flags.append("multiple_blurs_pre_claim")
    if record.resume_count >= 1:
        flags.append("reload_ge_1")
    if record.resume_count >= 2:
        flags.append("reload_ge_2")
    if record.network_error_count >= 1:
        flags.append("network_retry")

    for event in events:
        if (
            event.event_name in {"screen_exit", "screen_duration"}
            and event.screen_name
            and event.duration_ms
        ):
            screen_durations[event.screen_name] = max(
                screen_durations.get(event.screen_name, 0), event.duration_ms
            )

    if (
        screen_durations.get("landing", 10_000)
        < QUALITY_THRESHOLDS["landing_fast_ms"]
    ):
        flags.append("fast_consent")
    if (
        screen_durations.get("instructions", 10_000)
        < QUALITY_THRESHOLDS["instructions_fast_ms"]
    ):
        flags.append("fast_instructions")
    if record.claim_submitted_at and record.report_prepared_at:
        report_rt = int(
            (record.claim_submitted_at - record.report_prepared_at).total_seconds()
            * 1000
        )
        if report_rt < QUALITY_THRESHOLDS["report_fast_ms"]:
            flags.append("fast_report")
    if record.report_prepared_at and not record.report_snapshot_treatment:
        flags.append("missing_report_snapshot")
    return sorted(set(flags))


def build_antifraud_flags(db: Session, record: SessionRecord) -> list[str]:
    flags = {
        item.flag_key
        for item in db.exec(
            select(FraudFlag).where(FraudFlag.session_id == record.id)
        ).all()
    }
    return sorted(flags)


def parse_json_list(raw_value: Optional[str]) -> list[Any]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def parse_json_dict(raw_value: Optional[str]) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def get_or_create_snapshot_record(db: Session, session_id: str) -> SnapshotRecord:
    snapshot = db.exec(
        select(SnapshotRecord).where(SnapshotRecord.session_id == session_id)
    ).first()
    if snapshot:
        return snapshot
    snapshot = SnapshotRecord(session_id=session_id)
    db.add(snapshot)
    db.flush()
    return snapshot


def get_or_create_screen_spell(
    db: Session, *, session_id: str, spell_id: str, screen_name: str
) -> ScreenSpell:
    with db.no_autoflush:
        spell = db.exec(
            select(ScreenSpell).where(
                ScreenSpell.session_id == session_id,
                ScreenSpell.spell_id == spell_id,
            )
        ).first()
    if spell:
        return spell
    spell = ScreenSpell(
        session_id=session_id,
        spell_id=spell_id,
        screen_name=screen_name,
    )
    db.add(spell)
    db.flush()
    return spell


def update_screen_spell_from_event(
    db: Session,
    *,
    session_id: str,
    item: TelemetryItem,
    server_now: datetime,
) -> None:
    spell_id = item.spell_id or (item.payload or {}).get("spell_id")
    screen_name = item.screen_name or (item.payload or {}).get("screen_name")
    if not spell_id or not screen_name:
        return

    spell = get_or_create_screen_spell(
        db, session_id=session_id, spell_id=spell_id, screen_name=screen_name
    )
    payload = item.payload or {}

    if item.event_name == "screen_enter":
        spell.screen_name = screen_name
        spell.entry_origin = payload.get("entry_origin")
        spell.entered_client_ts = item.client_ts
        spell.entered_server_ts = server_now
        spell.entered_via_resume = bool(payload.get("entered_via_resume", False))
        spell.language_at_entry = item.app_language or payload.get("language")
        spell.event_sequence_start = item.event_sequence_number
    elif item.event_name in {"screen_exit", "screen_duration"}:
        spell.exited_client_ts = item.client_ts
        spell.exited_server_ts = server_now
        spell.duration_total_ms = item.duration_ms or payload.get("duration_total_ms")
        spell.visible_ms = payload.get("visible_ms")
        spell.hidden_ms = payload.get("hidden_ms")
        spell.blur_ms = payload.get("blur_ms")
        spell.focus_change_count = int(payload.get("focus_change_count") or 0)
        spell.visibility_change_count = int(payload.get("visibility_change_count") or 0)
        spell.click_count = int(payload.get("click_count") or 0)
        spell.primary_click_count = int(payload.get("primary_click_count") or 0)
        spell.secondary_click_count = int(payload.get("secondary_click_count") or 0)
        spell.first_click_ms = payload.get("first_click_ms")
        spell.primary_cta_ms = payload.get("primary_cta_ms")
        spell.secondary_cta_ms = payload.get("secondary_cta_ms")
        spell.first_click_target = payload.get("first_click_target")
        click_targets = payload.get("click_targets")
        if click_targets is not None:
            spell.click_targets_json = stable_json(click_targets)
        spell.language_at_exit = item.app_language or payload.get("language")
        spell.language_changed_during_spell = bool(
            payload.get("language_changed_during_spell", False)
        )
        spell.event_sequence_end = item.event_sequence_number
    spell.updated_at = server_now
    db.add(spell)


def build_screen_metrics_summary(
    db: Session, session_id: str
) -> dict[str, dict[str, int | None]]:
    spells = db.exec(
        select(ScreenSpell)
        .where(ScreenSpell.session_id == session_id)
        .order_by(ScreenSpell.entered_server_ts)
    ).all()
    summary: dict[str, dict[str, int | None]] = {}
    for spell in spells:
        bucket = summary.setdefault(
            spell.screen_name,
            {
                "entries": 0,
                "duration_total_ms": 0,
                "visible_ms": 0,
                "hidden_ms": 0,
                "blur_ms": 0,
                "click_count": 0,
                "primary_click_count": 0,
                "secondary_click_count": 0,
            },
        )
        bucket["entries"] = int(bucket["entries"] or 0) + 1
        for key in [
            "duration_total_ms",
            "visible_ms",
            "hidden_ms",
            "blur_ms",
            "click_count",
            "primary_click_count",
            "secondary_click_count",
        ]:
            bucket[key] = int(bucket[key] or 0) + int(getattr(spell, key) or 0)
    return summary


def normalize_phone(raw_phone: str) -> str:
    digits = "".join(character for character in raw_phone if character.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) < 9 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Telefono no valido")
    return digits


def get_payment_by_reference(db: Session, code: str, *, for_update: bool = False) -> Payment:
    payment = db.exec(
        with_optional_for_update(
            select(Payment).where(Payment.payout_reference == code),
            for_update,
        )
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Codigo de cobro no encontrado")
    return payment


def build_report_snapshot(record: SessionRecord) -> Optional[dict[str, Any]]:
    if not record.report_snapshot_treatment:
        return None
    return {
        "treatment_key": record.report_snapshot_treatment,
        "count_target": record.report_snapshot_count_target,
        "denominator": record.report_snapshot_denominator,
        "target_value": record.report_snapshot_target_value,
        "window_version": record.report_snapshot_version,
        "message": record.report_snapshot_message,
        "message_version": record.report_snapshot_message_version,
        "is_control": record.report_snapshot_treatment == CONTROL_TREATMENT_KEY,
    }


def build_session_payload(db: Session, record: SessionRecord) -> dict[str, Any]:
    series = get_series_or_404(db, record.series_id)
    root = db.get(SeriesRoot, record.root_id)
    treatment_deck = db.get(TreatmentDeck, record.treatment_deck_id)
    result_deck = db.get(ResultDeck, record.result_deck_id)
    payment_deck = db.get(PaymentDeck, record.payment_deck_id)
    throws = db.exec(
        select(Throw).where(Throw.session_id == record.id).order_by(Throw.attempt_index)
    ).all()
    claim = db.exec(select(Claim).where(Claim.session_id == record.id)).first()
    payment = db.exec(select(Payment).where(Payment.session_id == record.id)).first()
    consent_record = db.exec(
        select(ConsentRecord).where(ConsentRecord.session_id == record.id)
    ).first()
    snapshot_record = db.exec(
        select(SnapshotRecord).where(SnapshotRecord.session_id == record.id)
    ).first()
    client_context = db.exec(
        select(SessionClientContext).where(SessionClientContext.session_id == record.id)
    ).first()
    screen_metrics = build_screen_metrics_summary(db, record.id)

    return {
        "session_id": record.id,
        "state": record.state,
        "screen": record.screen_cursor,
        "experiment_version": record.experiment_version,
        "experiment_phase": record.experiment_phase,
        "phase_version": record.phase_version,
        "phase_activation_status": record.phase_activation_status,
        "ui_version": record.ui_version,
        "consent_version": record.consent_version,
        "treatment_version": record.treatment_version,
        "treatment_text_version": record.treatment_text_version,
        "allocation_version": record.allocation_version,
        "deck_version": record.deck_version,
        "payment_version": record.payment_version,
        "telemetry_version": record.telemetry_version,
        "lexicon_version": record.lexicon_version,
        "treatment_key": record.treatment_key,
        "treatment_type": record.treatment_type,
        "treatment_family": record.treatment_family,
        "norm_target_value": record.norm_target_value,
        "displayed_count_target": record.displayed_count_target,
        "displayed_denominator": record.displayed_denominator,
        "is_control": record.treatment_key == CONTROL_TREATMENT_KEY,
        "language_at_access": record.language_at_access,
        "language_at_claim": record.language_at_claim,
        "language_changed_during_session": record.language_changed_during_session,
        "deployment_context": record.deployment_context,
        "site_code": record.site_code,
        "campaign_code": record.campaign_code,
        "environment_label": record.environment_label,
        "bracelet_status": "completed" if record.completed_at else "active",
        "consent": {
            "accepted": record.consent_accepted,
            "age_confirmed": record.consent_age_confirmed,
            "info_accepted": record.consent_info_accepted,
            "data_accepted": record.consent_data_accepted,
            "accepted_at": (
                record.consent_accepted_at.isoformat()
                if record.consent_accepted_at
                else None
            ),
        },
        "referral_code": record.referral_code,
        "invited_by_session_id": record.invited_by_session_id,
        "invited_by_referral_code": record.invited_by_referral_code,
        "referral_source": record.referral_source,
        "referral_medium": record.referral_medium,
        "referral_campaign": record.referral_campaign,
        "referral_link_id": record.referral_link_id,
        "qr_entry_code": record.qr_entry_code,
        "referral_landing_path": record.referral_landing_path,
        "referral_arrived_at": (
            record.referral_arrived_at.isoformat() if record.referral_arrived_at else None
        ),
        "operational_note": {
            "id": record.operational_note_id,
            "note_text": record.operational_note_text,
        },
        "position_index": record.position_index,
        "root_sequence": root.root_sequence if root else None,
        "phase_root_sequence": root.root_sequence if root else None,
        "treatment_deck_index": treatment_deck.deck_index if treatment_deck else None,
        "treatment_card_position": record.treatment_card_position,
        "result_deck_index": result_deck.deck_index if result_deck else None,
        "result_deck_treatment_key": result_deck.treatment_key if result_deck else None,
        "result_deck_treatment_cycle_index": (
            result_deck.treatment_cycle_index if result_deck else None
        ),
        "result_card_position": record.result_card_position,
        "payment_deck_index": payment_deck.deck_index if payment_deck else None,
        "payment_card_position": record.payment_card_position,
        "selected_for_payment": record.selected_for_payment,
        "max_attempts": record.max_attempts,
        "first_result_value": record.first_result_value,
        "last_seen_value": record.last_seen_value,
        "max_seen_value": record.max_seen_value,
        "reroll_count": record.reroll_count,
        "is_valid_completed": record.is_valid_completed,
        "valid_completed_at": (
            record.valid_completed_at.isoformat() if record.valid_completed_at else None
        ),
        "report_snapshot": build_report_snapshot(record),
        "throws": [
            {
                "attempt_index": item.attempt_index,
                "result_value": item.result_value,
                "reaction_ms": item.reaction_ms,
                "delivered_at": item.delivered_at.isoformat(),
            }
            for item in throws
        ],
        "claim": (
            {
                "reported_value": claim.reported_value,
                "true_first_result": claim.true_first_result,
                "is_honest": claim.is_honest,
                "matches_last_seen": claim.matches_last_seen,
                "matches_any_seen": claim.matches_any_seen,
                "submitted_at": claim.submitted_at.isoformat(),
                "crowd_prediction_value": claim.crowd_prediction_value,
                "crowd_prediction_submitted_at": (
                    claim.crowd_prediction_submitted_at.isoformat()
                    if claim.crowd_prediction_submitted_at
                    else None
                ),
                "social_recall_count": claim.social_recall_count,
                "social_recall_correct": claim.social_recall_correct,
                "social_recall_submitted_at": (
                    claim.social_recall_submitted_at.isoformat()
                    if claim.social_recall_submitted_at
                    else None
                ),
            }
            if claim
            else None
        ),
        "payment": (
            {
                "eligible": payment.eligible,
                "amount_cents": payment.amount_cents,
                "amount_eur": payment.amount_cents / 100,
                "status": payment.status,
                "reference_code": payment.payout_reference,
            }
            if payment
            else {
                "eligible": record.selected_for_payment,
                "amount_cents": record.payout_amount,
                "amount_eur": record.payout_amount / 100,
                "status": "pending"
                if record.selected_for_payment
                else "not_eligible",
                "reference_code": (
                    payout_reference_code(record.id)
                    if record.selected_for_payment
                    else None
                ),
            }
        ),
        "quality_flags": build_quality_flags(db, record),
        "antifraud_flags": build_antifraud_flags(db, record),
        "client_context": (
            {
                "browser_family": client_context.browser_family,
                "browser_version": client_context.browser_version,
                "os_family": client_context.os_family,
                "os_version": client_context.os_version,
                "device_type": client_context.device_type,
                "platform": client_context.platform,
                "language_browser": client_context.language_browser,
                "language_app_selected": client_context.language_app_selected,
                "screen_width": client_context.screen_width,
                "screen_height": client_context.screen_height,
                "viewport_width": client_context.viewport_width,
                "viewport_height": client_context.viewport_height,
                "device_pixel_ratio": client_context.device_pixel_ratio,
                "orientation": client_context.orientation,
                "touch_capable": client_context.touch_capable,
                "hardware_concurrency": client_context.hardware_concurrency,
                "max_touch_points": client_context.max_touch_points,
                "color_scheme_preference": client_context.color_scheme_preference,
                "online_status": client_context.online_status,
                "connection_type": client_context.connection_type,
                "estimated_downlink": client_context.estimated_downlink,
                "estimated_rtt": client_context.estimated_rtt,
                "timezone_offset_minutes": client_context.timezone_offset_minutes,
            }
            if client_context
            else None
        ),
        "session_metrics": {
            "resume_count": record.resume_count,
            "refresh_count": record.refresh_count,
            "blur_count": record.blur_count,
            "network_error_count": record.network_error_count,
            "retry_count": record.retry_count,
            "click_count_total": record.click_count_total,
            "screen_changes_count": record.screen_changes_count,
            "language_change_count": record.language_change_count,
            "telemetry_event_count": record.telemetry_event_count,
            "max_event_sequence_number": record.max_event_sequence_number,
        },
        "consent_record": (
            {
                "language_at_access": consent_record.language_at_access,
                "landing_visible_ms": consent_record.landing_visible_ms,
                "info_panels_opened": parse_json_list(
                    consent_record.info_panels_opened_json
                ),
                "info_panel_durations_ms": parse_json_dict(
                    consent_record.info_panel_durations_json
                ),
                "checkbox_order": parse_json_list(consent_record.checkbox_order_json),
                "checkbox_timestamps_ms": parse_json_dict(
                    consent_record.checkbox_timestamps_json
                ),
                "continue_blocked_count": consent_record.continue_blocked_count,
            }
            if consent_record
            else None
        ),
        "snapshot_record": (
            {
                "language_used": snapshot_record.language_used,
                "displayed_message_text": snapshot_record.displayed_message_text,
                "control_message_text": snapshot_record.control_message_text,
                "final_message_text": snapshot_record.final_message_text,
                "payout_reference_shown": snapshot_record.payout_reference_shown,
                "payout_phone_shown": snapshot_record.payout_phone_shown,
                "first_result_value": snapshot_record.first_result_value,
                "last_seen_value": snapshot_record.last_seen_value,
                "all_values_seen": parse_json_list(snapshot_record.all_values_seen_json),
                "rerolls_visible": parse_json_list(snapshot_record.rerolls_visible_json),
                "final_state_shown": snapshot_record.final_state_shown,
            }
            if snapshot_record
            else None
        ),
        "screen_metrics": screen_metrics,
        "series": {
            "experiment_phase": series.experiment_phase,
            "treatment_key": series.treatment_key,
            "treatment_type": record.treatment_type,
            "treatment_family": series.treatment_family,
            "norm_target_value": series.norm_target_value,
            "displayed_count_target": record.displayed_count_target,
            "displayed_denominator": record.displayed_denominator,
            "completed_count": series.completed_count,
            "visible_count_target": series.visible_count_target,
            "actual_count_target": series.actual_count_target,
            "visible_window_version": series.visible_window_version,
            "actual_window_version": series.actual_window_version,
        },
    }


def ensure_user_and_session(
    db: Session,
    *,
    bracelet_id: str,
    consent_accepted: bool,
    consent_age_confirmed: bool,
    consent_info_accepted: bool,
    consent_data_accepted: bool,
    language: Optional[str],
    landing_visible_ms: Optional[int],
    info_panels_opened: Optional[list[str]],
    info_panel_durations_ms: Optional[dict[str, int]],
    client_installation_id: Optional[str],
    incoming_referral_code: Optional[str],
    referral_source: Optional[str],
    referral_medium: Optional[str],
    referral_campaign: Optional[str],
    referral_link_id: Optional[str],
    qr_entry_code: Optional[str],
    referral_path: Optional[str],
    consent_checkbox_order: Optional[list[str]],
    consent_checkbox_timestamps_ms: Optional[dict[str, int]],
    consent_continue_blocked_count: Optional[int],
    client_context: Optional[dict[str, Any]],
    request: Request,
) -> tuple[User, SessionRecord, bool]:
    now = utcnow()
    bracelet_hash = stable_hash(bracelet_id)
    device_basis = client_installation_id or request.headers.get(
        "user-agent", "unknown-device"
    )
    device_hash = stable_hash(device_basis)
    ip_hash = stable_hash(get_client_ip(request))
    user_agent_hash = stable_hash(request.headers.get("user-agent", "unknown-agent"))
    active_operational_note = get_active_operational_note(db)

    user = db.exec(select(User).where(User.bracelet_id == bracelet_id)).first()
    created_now = False
    if not user:
        user = User(
            bracelet_id=bracelet_id,
            bracelet_hash=bracelet_hash,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(user)
        db.flush()

    if user.is_blocked:
        raise HTTPException(status_code=423, detail="Pulsera bloqueada")

    session_record = db.exec(
        select(SessionRecord).where(SessionRecord.user_id == user.id)
    ).first()
    if session_record:
        user.last_seen_at = now
        session_record.last_seen_at = now
        if language:
            if session_record.language_at_access is None:
                session_record.language_at_access = language
            if (
                session_record.language_at_access
                and session_record.language_at_access != language
            ):
                session_record.language_changed_during_session = True
        referral_attached = False
        if (
            incoming_referral_code
            and not session_record.invited_by_session_id
            and incoming_referral_code != session_record.referral_code
        ):
            referrer = db.exec(
                select(SessionRecord).where(
                    SessionRecord.referral_code == incoming_referral_code
                )
            ).first()
            session_record.invited_by_referral_code = incoming_referral_code
            session_record.referral_source = referral_source
            session_record.referral_medium = referral_medium
            session_record.referral_campaign = referral_campaign
            session_record.referral_link_id = referral_link_id
            session_record.referral_landing_path = referral_path
            session_record.referral_arrived_at = now
            if referrer:
                session_record.invited_by_session_id = referrer.id
            referral_attached = True
        if qr_entry_code and not session_record.qr_entry_code:
            session_record.qr_entry_code = qr_entry_code
        if active_operational_note and not session_record.operational_note_id:
            session_record.operational_note_id = active_operational_note.id
            session_record.operational_note_text = active_operational_note.note_text
        db.add(user)
        db.add(session_record)
        upsert_session_client_context(
            db,
            session_id=session_record.id,
            raw_context=client_context,
            request=request,
            app_language=language,
        )
        if referral_attached:
            create_audit(
                db,
                entity_type="session",
                entity_id=session_record.id,
                action="referral_attached_on_resume",
                session_id=session_record.id,
                old_state=session_record.state,
                new_state=session_record.state,
                payload={
                    "invited_by_referral_code": session_record.invited_by_referral_code,
                    "invited_by_session_id": session_record.invited_by_session_id,
                    "referral_source": session_record.referral_source,
                    "referral_medium": session_record.referral_medium,
                    "referral_campaign": session_record.referral_campaign,
                },
            )
        db.commit()
        db.refresh(session_record)
        return user, session_record, created_now

    experiment_state = get_or_create_experiment_state(db, for_update=True)
    phase_key = experiment_state.current_phase
    session_id = make_uuid()
    override = demo_override(bracelet_id)
    if override:
        (
            treatment_deck,
            treatment_card,
            legacy_series,
            result_deck,
            result_card,
            payment_deck,
            payment_card,
        ) = assign_demo_cards(db, bracelet_id=bracelet_id, session_id=session_id)
        phase_activation_status = "demo_override"
    else:
        (
            treatment_deck,
            treatment_card,
            legacy_series,
        ) = assign_next_treatment_card(db, session_id=session_id)
        result_deck, result_card = assign_next_result_card(
            db,
            session_id=session_id,
            treatment_key=treatment_card.treatment_key,
        )
        payment_deck, payment_card = assign_next_payment_card(
            db, session_id=session_id
        )
        phase_activation_status = current_phase_activation_status(phase_key)

    root = db.get(SeriesRoot, treatment_deck.legacy_root_id) if treatment_deck.legacy_root_id else None
    treatment = treatment_config(phase_key, treatment_card.treatment_key)
    position_index = treatment_card.card_position
    root_id = root.id if root else legacy_series.root_id
    session_record = SessionRecord(
        id=session_id,
        user_id=user.id,
        root_id=legacy_series.root_id,
        series_id=legacy_series.id,
        referral_code=referral_code(f"{user.id}:{root_id}:{position_index}"),
        invited_by_referral_code=incoming_referral_code,
        referral_source=referral_source,
        referral_medium=referral_medium,
        referral_campaign=referral_campaign,
        referral_link_id=referral_link_id,
        qr_entry_code=qr_entry_code,
        referral_landing_path=referral_path,
        referral_arrived_at=now if incoming_referral_code else None,
        operational_note_id=active_operational_note.id if active_operational_note else None,
        operational_note_text=active_operational_note.note_text if active_operational_note else None,
        experiment_version=EXPERIMENT_VERSION,
        experiment_phase=phase_key,
        phase_version=phase_version_for_phase(phase_key),
        phase_activation_status=phase_activation_status,
        ui_version=UI_VERSION,
        consent_version=CONSENT_VERSION,
        treatment_version=treatment_version_for_phase(phase_key),
        treatment_text_version=displayed_message_version_for_phase(phase_key),
        allocation_version=allocation_version_for_phase(phase_key),
        deck_version=DECK_VERSION,
        payment_version=PAYMENT_VERSION,
        telemetry_version=TELEMETRY_VERSION,
        lexicon_version=LEXICON_VERSION,
        treatment_key=treatment_card.treatment_key,
        treatment_type=str(treatment["treatment_type"]),
        treatment_family=str(treatment["treatment_family"]),
        norm_target_value=treatment["norm_target_value"],
        displayed_count_target=treatment["displayed_count_target"],
        displayed_denominator=treatment["displayed_denominator"],
        treatment_deck_id=treatment_deck.id,
        treatment_card_position=treatment_card.card_position,
        result_deck_id=result_deck.id,
        result_card_position=result_card.card_position,
        payment_deck_id=payment_deck.id,
        payment_card_position=payment_card.card_position,
        language_at_access=language,
        language_at_claim=language,
        language_changed_during_session=False,
        deployment_context=DEPLOYMENT_CONTEXT,
        site_code=SITE_CODE,
        campaign_code=CAMPAIGN_CODE,
        environment_label=ENVIRONMENT_LABEL,
        position_index=position_index,
        state="assigned",
        screen_cursor="instructions",
        consent_accepted=consent_accepted,
        consent_age_confirmed=consent_age_confirmed,
        consent_info_accepted=consent_info_accepted,
        consent_data_accepted=consent_data_accepted,
        consent_accepted_at=now,
        max_attempts=MAX_ATTEMPTS,
        selected_for_payment=payment_card.payout_eligible,
        client_installation_id=client_installation_id,
        device_hash=device_hash,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        created_at=now,
        last_seen_at=now,
    )
    created_now = True
    if incoming_referral_code and incoming_referral_code != session_record.referral_code:
        referrer = db.exec(
            select(SessionRecord).where(
                SessionRecord.referral_code == incoming_referral_code
            )
        ).first()
        if referrer:
            session_record.invited_by_session_id = referrer.id

    user.last_seen_at = now
    db.add(user)
    db.add(legacy_series)
    db.add(session_record)
    db.flush()
    db.add(
        ConsentRecord(
            session_id=session_record.id,
            bracelet_id=bracelet_id,
            consent_version=CONSENT_VERSION,
            language_at_access=language,
            age_confirmed=consent_age_confirmed,
            participation_accepted=consent_info_accepted,
            data_accepted=consent_data_accepted,
            accepted_at=now,
            landing_visible_ms=landing_visible_ms,
            info_panels_opened_json=stable_json(info_panels_opened or []),
            info_panel_durations_json=stable_json(info_panel_durations_ms or {}),
            info_panel_open_count=len(info_panels_opened or []),
            checkbox_order_json=stable_json(consent_checkbox_order or []),
            checkbox_timestamps_json=stable_json(consent_checkbox_timestamps_ms or {}),
            continue_blocked_count=int(consent_continue_blocked_count or 0),
        )
    )
    upsert_session_client_context(
        db,
        session_id=session_record.id,
        raw_context=client_context,
        request=request,
        app_language=language,
    )
    create_audit(
        db,
        entity_type="session",
        entity_id=session_record.id,
        action="session_assigned",
        session_id=session_record.id,
        new_state="assigned",
        payload={
                "root_id": legacy_series.root_id,
                "series_id": legacy_series.id,
                "experiment_phase": phase_key,
                "treatment_key": treatment_card.treatment_key,
                "treatment_type": treatment["treatment_type"],
                "treatment_family": treatment["treatment_family"],
                "norm_target_value": treatment["norm_target_value"],
                "displayed_count_target": treatment["displayed_count_target"],
                "displayed_denominator": treatment["displayed_denominator"],
                "position_index": position_index,
                "treatment_deck_index": treatment_deck.deck_index,
                "treatment_card_position": treatment_card.card_position,
                "result_deck_index": result_deck.deck_index,
                "result_card_position": result_card.card_position,
                "payment_deck_index": payment_deck.deck_index,
                "payment_card_position": payment_card.card_position,
                "selected_for_payment": payment_card.payout_eligible,
                "referral_code": session_record.referral_code,
                "invited_by_referral_code": session_record.invited_by_referral_code,
                "invited_by_session_id": session_record.invited_by_session_id,
                "referral_source": session_record.referral_source,
                "referral_medium": session_record.referral_medium,
                "referral_campaign": session_record.referral_campaign,
                "referral_link_id": session_record.referral_link_id,
                "language_at_access": language,
                "demo_override": bool(override),
            },
        )

    recent_same_device = db.exec(
        select(SessionRecord)
        .where(
            SessionRecord.device_hash == device_hash,
            SessionRecord.created_at >= now - timedelta(minutes=15),
        )
        .order_by(SessionRecord.created_at.desc())
    ).all()
    distinct_users = {
        item.user_id for item in recent_same_device if item.user_id != user.id
    }
    if distinct_users:
        create_fraud_flag(
            db,
            flag_key="same_device_multiple_bracelets",
            severity="medium",
            session_id=session_record.id,
            user_id=user.id,
            payload={"other_users_in_15m": len(distinct_users)},
        )

    db.commit()
    db.refresh(session_record)
    return user, session_record, created_now


def startup_dependency_status() -> dict[str, bool]:
    database_ok = database_ready()
    redis_ok = redis_ping() if settings.require_redis else True
    schema_ok = not schema_needs_reset() if database_ok else False
    payload = {
        "database_ready": database_ok,
        "redis_ready": redis_ok,
        "schema_ready": schema_ok,
    }
    with _startup_state_lock:
        _startup_state["last_readiness"] = dict(payload)
    return payload


def current_startup_state() -> dict[str, Any]:
    with _startup_state_lock:
        return {
            "initialized": bool(_startup_state["initialized"]),
            "initializing": bool(_startup_state["initializing"]),
            "error": _startup_state["error"],
            "last_readiness": dict(_startup_state["last_readiness"]),
        }


def update_startup_state(
    *,
    initialized: Optional[bool] = None,
    initializing: Optional[bool] = None,
    error: Any = _STARTUP_STATE_UNSET,
    last_readiness: Optional[dict[str, bool]] = None,
) -> None:
    with _startup_state_lock:
        if initialized is not None:
            _startup_state["initialized"] = initialized
        if initializing is not None:
            _startup_state["initializing"] = initializing
        if error is not _STARTUP_STATE_UNSET:
            _startup_state["error"] = error
        if last_readiness is not None:
            _startup_state["last_readiness"] = dict(last_readiness)


def readiness_payload() -> dict[str, Any]:
    dependency_status = startup_dependency_status()
    startup_state = current_startup_state()
    payload = {
        **dependency_status,
        "startup_initialized": startup_state["initialized"],
        "startup_initializing": startup_state["initializing"],
        "startup_error": startup_state["error"],
    }
    payload["ok"] = (
        dependency_status["database_ready"]
        and dependency_status["redis_ready"]
    )
    return payload


def initialize_application_state() -> None:
    with _startup_state_lock:
        if _startup_state["initialized"] or _startup_state["initializing"]:
            return
        _startup_state["initialized"] = False
        _startup_state["initializing"] = True
        _startup_state["error"] = None
    while True:
        readiness = startup_dependency_status()
        if not readiness["database_ready"] or not readiness["redis_ready"]:
            logger.warning(
                "startup_dependencies_not_ready",
                extra={"structured_payload": readiness},
            )
            time.sleep(settings.startup_dependency_retry_interval_seconds)
            continue
        try:
            try:
                from migrate import apply_migrations

                apply_migrations()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "startup_background_migrations_failed_non_blocking"
                )
            with Session(engine) as db:
                if settings.auto_bootstrap_demo_data and settings.database_is_sqlite:
                    try:
                        bootstrap_demo_data(db)
                    except Exception:  # noqa: BLE001
                        db.rollback()
                        logger.exception(
                                "startup_bootstrap_failed_lazy_runtime_recovery_enabled"
                        )
                state = get_or_create_experiment_state(db)
                db.commit()
                try:
                    set_experiment_status_cache(
                        state.experiment_status,
                        state.pause_reason,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "startup_status_cache_write_failed_non_blocking"
                    )
        except Exception as exc:  # noqa: BLE001
            update_startup_state(initialized=False, initializing=True, error=str(exc))
            logger.exception("startup_initialization_failed")
            time.sleep(settings.startup_dependency_retry_interval_seconds)
            continue
        update_startup_state(
            initialized=True,
            initializing=False,
            error=None,
            last_readiness=readiness,
        )
        logger.info(
            "startup_completed",
            extra={
                "structured_payload": {
                    "database_url": settings.database_url,
                    "redis_url": settings.redis_url,
                    "auto_bootstrap_demo_data": settings.auto_bootstrap_demo_data,
                }
            },
        )
        return


@app.on_event("startup")
def on_startup() -> None:
    threading.Thread(
        target=initialize_application_state,
        name="sonar-startup",
        daemon=True,
    ).start()


@app.get("/")
def root() -> dict[str, str]:
    return {"ok": "true", "docs": "/docs", "health": "/health"}


@app.get("/health/live")
def health_live() -> dict[str, Any]:
    return {"ok": True, "status": "live"}


@app.get("/health/ready")
def health_ready() -> Response:
    payload = readiness_payload()
    status_code = 200 if payload["ok"] else 503
    return JSONResponse(content=payload, status_code=status_code)


@app.get("/health")
def healthcheck() -> Any:
    readiness = readiness_payload()
    if not readiness["ok"]:
        return JSONResponse(content=readiness, status_code=503)
    with Session(engine) as db:
        experiment_state = get_or_create_experiment_state(db)
        prizes = prize_summary(db)
        active_treatment_deck = db.exec(
            select(TreatmentDeck)
            .where(TreatmentDeck.status == "active")
            .order_by(TreatmentDeck.deck_index)
        ).first()
        active_result_deck = db.exec(
            select(ResultDeck)
            .where(ResultDeck.status == "active")
            .order_by(ResultDeck.deck_index)
        ).first()
        active_payment_deck = db.exec(
            select(PaymentDeck)
            .where(PaymentDeck.status == "active")
            .order_by(PaymentDeck.deck_index)
        ).first()
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "experiment_version": EXPERIMENT_VERSION,
            "ui_version": UI_VERSION,
            "lexicon_version": LEXICON_VERSION,
            "current_phase": experiment_state.current_phase,
            "experiment_status": experiment_state.experiment_status,
            "valid_completed_count": experiment_state.valid_completed_count,
            "phase_transition_threshold": experiment_state.phase_transition_threshold,
            "winner_count": prizes["winner_count"],
            "total_prize_amount_eur": prizes["total_prize_amount_eur"],
            "deployment_context": DEPLOYMENT_CONTEXT,
            "site_code": SITE_CODE,
            "campaign_code": CAMPAIGN_CODE,
            "environment_label": ENVIRONMENT_LABEL,
            "active_treatment_deck_index": active_treatment_deck.deck_index if active_treatment_deck else None,
            "active_result_deck_index": active_result_deck.deck_index if active_result_deck else None,
            "active_payment_deck_index": active_payment_deck.deck_index if active_payment_deck else None,
        }


@app.get("/v1/config")
def config() -> dict[str, Any]:
    with Session(engine) as db:
        return build_config_payload(db)


@app.post("/v1/interest-signup")
def interest_signup(
    payload: InterestSignupRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    state = get_or_create_experiment_state(db)
    active_operational_note = get_active_operational_note(db)
    if not experiment_is_paused(state):
        raise HTTPException(
            status_code=409,
            detail="El registro de interes solo esta disponible cuando el experimento esta detenido",
        )
    normalized_email = normalize_email(payload.email)
    existing = db.exec(
        select(InterestSignup).where(
            InterestSignup.email_normalized == normalized_email
        )
    ).first()
    if not existing:
        existing = InterestSignup(
            email_normalized=normalized_email,
            email_hash=stable_hash(f"interest:{normalized_email}"),
            language_used=payload.language,
            source_screen="experiment_paused",
            experiment_status=state.experiment_status,
            deployment_context=DEPLOYMENT_CONTEXT,
            site_code=SITE_CODE,
            campaign_code=CAMPAIGN_CODE,
            environment_label=ENVIRONMENT_LABEL,
            operational_note_id=active_operational_note.id if active_operational_note else None,
            operational_note_text=active_operational_note.note_text if active_operational_note else None,
        )
    else:
        existing.language_used = payload.language or existing.language_used
        existing.experiment_status = state.experiment_status
        existing.operational_note_id = active_operational_note.id if active_operational_note else existing.operational_note_id
        existing.operational_note_text = active_operational_note.note_text if active_operational_note else existing.operational_note_text
        existing.updated_at = utcnow()
    db.add(existing)
    create_audit(
        db,
        entity_type="interest_signup",
        entity_id=existing.id,
        action="interest_signup_saved",
        payload={
            "language": payload.language,
            "deployment_context": DEPLOYMENT_CONTEXT,
        },
    )
    db.commit()
    return {"ok": True, "stored": True}


@app.post("/v1/session/access")
def access_session(
    payload: AccessRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    consent_ok = (
        payload.consent_accepted
        and payload.consent_age_confirmed
        and payload.consent_info_accepted
        and payload.consent_data_accepted
    )
    if not consent_ok:
        raise HTTPException(
            status_code=400,
            detail="Es necesario confirmar edad, participacion y tratamiento de datos",
        )
    try:
        bracelet_id = normalize_bracelet_id(payload.bracelet_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rate_limit(f"access:{stable_hash(get_client_ip(request))}", settings.access_rate_limit_per_minute)
    with distributed_lock(f"bracelet:{bracelet_id}"):
        with distributed_lock("assignment"):
            ensure_experiment_accepting_entries(db)
            pulsera = db.get(Pulsera, bracelet_id)
            if not pulsera:
                pulsera = Pulsera(id=bracelet_id)
                db.add(pulsera)
                db.flush()
            _, session_record, created_now = ensure_user_and_session(
                db,
                bracelet_id=bracelet_id,
                consent_accepted=consent_ok,
                consent_age_confirmed=payload.consent_age_confirmed,
                consent_info_accepted=payload.consent_info_accepted,
                consent_data_accepted=payload.consent_data_accepted,
                language=payload.language,
                landing_visible_ms=payload.landing_visible_ms,
                info_panels_opened=payload.info_panels_opened,
                info_panel_durations_ms=payload.info_panel_durations_ms,
                client_installation_id=payload.client_installation_id,
                incoming_referral_code=payload.referral_code,
                referral_source=payload.referral_source,
                referral_medium=payload.referral_medium,
                referral_campaign=payload.referral_campaign,
                referral_link_id=payload.referral_link_id,
                qr_entry_code=payload.qr_entry_code,
                referral_path=payload.referral_path,
                consent_checkbox_order=payload.consent_checkbox_order,
                consent_checkbox_timestamps_ms=payload.consent_checkbox_timestamps_ms,
                consent_continue_blocked_count=payload.consent_continue_blocked_count,
                client_context=payload.client_context,
                request=request,
            )
            return {
                "created_now": created_now,
                "session": build_session_payload(db, session_record),
            }


@app.get("/v1/session/{session_id}/resume")
def resume_session(session_id: str, db: Session = Depends(get_session)) -> dict[str, Any]:
    with distributed_lock(f"session:{session_id}"):
        record = get_session_or_404(db, session_id, for_update=True)
        record.resume_count += 1
        record.last_seen_at = utcnow()
        db.add(record)
        create_audit(
            db,
            entity_type="session",
            entity_id=record.id,
            action="session_resumed",
            session_id=record.id,
            old_state=record.state,
            new_state=record.state,
        )
        db.commit()
        return {"created_now": False, "session": build_session_payload(db, record)}


@app.post("/v1/session/{session_id}/roll")
def roll(
    session_id: str,
    payload: RollRequest,
    request: Request,
    db: Session = Depends(get_session),
 ) -> dict[str, Any]:
    endpoint = "roll"
    rate_limit(f"action:{session_id}", settings.action_rate_limit_per_minute)
    with distributed_lock(f"session:{session_id}"):
        ensure_experiment_accepting_entries(db)
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_valid_state(record, {"assigned", "in_game"}, "roll")

        existing_throws = db.exec(
            select(Throw).where(Throw.session_id == record.id).order_by(Throw.attempt_index)
        ).all()
        expected_attempt = len(existing_throws) + 1
        if payload.attempt_index != expected_attempt:
            create_fraud_flag(
                db,
                session_id=record.id,
                user_id=record.user_id,
                flag_key="attempt_skip",
                severity="high",
                payload={"expected": expected_attempt, "received": payload.attempt_index},
            )
            db.commit()
            raise HTTPException(status_code=409, detail="Secuencia de tiradas invalida")
        if payload.attempt_index > record.max_attempts:
            raise HTTPException(
                status_code=409, detail="No quedan mas tiradas permitidas"
            )

        if payload.attempt_index == 1:
            result_card = db.exec(
                select(ResultDeckCard).where(
                    ResultDeckCard.deck_id == record.result_deck_id,
                    ResultDeckCard.card_position == record.result_card_position,
                )
            ).first()
            if not result_card:
                raise HTTPException(
                    status_code=500,
                    detail="No existe primera tirada preasignada para la sesion",
                )
            result_value = result_card.result_value
        else:
            result_value = reroll_value_for_session(record.id, payload.attempt_index)

        throw = Throw(
            session_id=record.id,
            attempt_index=payload.attempt_index,
            result_value=result_value,
            reaction_ms=payload.reaction_ms,
            idempotency_key=payload.idempotency_key,
        )
        db.add(throw)

        old_state = record.state
        record.state = "in_game"
        record.screen_cursor = "game"
        record.last_seen_at = utcnow()
        record.last_seen_value = result_value
        record.max_seen_value = max(
            record.max_seen_value or result_value,
            result_value,
        )
        if payload.attempt_index == 1:
            record.first_result_value = result_value
            record.first_roll_at = record.first_roll_at or utcnow()
        else:
            record.reroll_count = payload.attempt_index - 1
        db.add(record)

        create_audit(
            db,
            entity_type="session",
            entity_id=record.id,
            action="roll_delivered",
            session_id=record.id,
            old_state=old_state,
            new_state=record.state,
            idempotency_key=payload.idempotency_key,
            payload={
                "attempt_index": payload.attempt_index,
                "result_value": result_value,
                "result_source": "result_deck"
                if payload.attempt_index == 1
                else "session_reroll_rng",
            },
        )

        response_payload = {
            "attempt": {
                "attempt_index": payload.attempt_index,
                "result_value": result_value,
                "is_first_roll": payload.attempt_index == 1,
                "remaining_attempts": record.max_attempts - payload.attempt_index,
            },
            "session": build_session_payload(db, record),
        }
        save_receipt(
            db,
            session_id=record.id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
            response_payload=response_payload,
        )
        db.commit()
        return response_payload


@app.post("/v1/session/{session_id}/prepare-report")
def prepare_report(
    session_id: str,
    payload: PrepareReportRequest,
    request: Request,
    db: Session = Depends(get_session),
 ) -> dict[str, Any]:
    endpoint = "prepare-report"
    rate_limit(f"action:{session_id}", settings.action_rate_limit_per_minute)
    with distributed_lock(f"session:{session_id}"):
        ensure_experiment_accepting_entries(db)
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_valid_state(record, {"in_game"}, "prepare-report")
        if record.first_result_value is None:
            raise HTTPException(
                status_code=409, detail="Todavia no existe primera tirada"
            )

        old_state = record.state
        record.state = "report_ready"
        record.screen_cursor = "report"
        record.report_prepared_at = utcnow()
        record.last_seen_at = utcnow()
        if record.treatment_key == CONTROL_TREATMENT_KEY:
            record.report_snapshot_treatment = CONTROL_TREATMENT_KEY
            record.report_snapshot_count_target = None
            record.report_snapshot_denominator = None
            record.report_snapshot_target_value = None
            record.report_snapshot_version = None
            record.report_snapshot_message = treatment_message(
                CONTROL_TREATMENT_KEY,
                None,
                None,
                None,
            )
            record.report_snapshot_message_version = displayed_message_version_for_phase(
                record.experiment_phase
            )
        else:
            record.report_snapshot_treatment = record.treatment_key
            record.report_snapshot_count_target = record.displayed_count_target
            record.report_snapshot_denominator = record.displayed_denominator
            record.report_snapshot_target_value = record.norm_target_value
            record.report_snapshot_version = 1
            record.report_snapshot_message = treatment_message(
                record.treatment_key,
                record.displayed_count_target,
                record.displayed_denominator,
                record.norm_target_value,
            )
            record.report_snapshot_message_version = displayed_message_version_for_phase(
                record.experiment_phase
            )
        record.displayed_message_version = record.report_snapshot_message_version
        db.add(record)

        create_audit(
            db,
            entity_type="session",
            entity_id=record.id,
            action="report_prepared",
            session_id=record.id,
            old_state=old_state,
            new_state=record.state,
            idempotency_key=payload.idempotency_key,
            payload={"snapshot": build_report_snapshot(record)},
        )

        response_payload = {"session": build_session_payload(db, record)}
        save_receipt(
            db,
            session_id=record.id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
            response_payload=response_payload,
        )
        db.commit()
        return response_payload


@app.post("/v1/session/{session_id}/screen")
def set_screen(
    session_id: str,
    payload: ScreenCursorRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    allowed_screens = {"instructions", "comprehension", "game", "report", "exit"}
    if payload.screen not in allowed_screens:
        raise HTTPException(status_code=400, detail="Pantalla no valida")

    with distributed_lock(f"session:{session_id}"):
        record = get_session_or_404(db, session_id, for_update=True)
        if record.state in {"completed_win", "completed_no_win"}:
            return {"session": build_session_payload(db, record)}
        ensure_experiment_accepting_entries(db)

        allowed_by_state = {
            "assigned": {"instructions", "comprehension", "game"},
            "in_game": {"game"},
            "report_ready": {"report"},
            "completed_win": {"exit"},
            "completed_no_win": {"exit"},
        }
        valid_targets = allowed_by_state.get(record.state, set())
        if payload.screen not in valid_targets:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Pantalla invalida para el estado actual",
                    "server_state": record.state,
                    "screen": record.screen_cursor,
                },
            )

        record.screen_cursor = payload.screen
        record.last_seen_at = utcnow()
        db.add(record)
        create_audit(
            db,
            entity_type="session",
            entity_id=record.id,
            action="screen_cursor_updated",
            session_id=record.id,
            old_state=record.state,
            new_state=record.state,
            payload={"screen": payload.screen},
        )
        db.commit()
        return {"session": build_session_payload(db, record)}


@app.post("/v1/session/{session_id}/submit-report")
def submit_report(
    session_id: str,
    payload: SubmitReportRequest,
    request: Request,
    db: Session = Depends(get_session),
 ) -> dict[str, Any]:
    endpoint = "submit-report"
    rate_limit(f"action:{session_id}", settings.action_rate_limit_per_minute)
    with distributed_lock(f"session:{session_id}"):
        ensure_experiment_accepting_entries(db)
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_valid_state(record, {"report_ready"}, "submit-report")
        if record.first_result_value is None:
            raise HTTPException(status_code=409, detail="No existe primera tirada")

        existing_claim = db.exec(
            select(Claim).where(Claim.session_id == record.id)
        ).first()
        if existing_claim:
            raise HTTPException(status_code=409, detail="La sesion ya tiene claim")

        series = get_series_or_404(db, record.series_id, for_update=True)
        active_operational_note = get_active_operational_note(db)
        throws = db.exec(
            select(Throw).where(Throw.session_id == record.id).order_by(Throw.attempt_index)
        ).all()
        seen_values = [item.result_value for item in throws]
        claim = Claim(
            session_id=record.id,
            root_id=record.root_id,
            series_id=record.series_id,
            experiment_phase=record.experiment_phase,
            phase_activation_status=record.phase_activation_status,
            treatment_version=record.treatment_version,
            allocation_version=record.allocation_version,
            treatment_family=record.treatment_family,
            norm_target_value=record.norm_target_value,
            position_index=record.position_index,
            true_first_result=record.first_result_value,
            reported_value=payload.reported_value,
            is_honest=payload.reported_value == record.first_result_value,
            reroll_count=record.reroll_count,
            displayed_treatment_key=record.report_snapshot_treatment or record.treatment_key,
            displayed_count_target=record.report_snapshot_count_target,
            displayed_denominator=record.report_snapshot_denominator,
            displayed_target_value=record.report_snapshot_target_value,
            displayed_window_version=record.report_snapshot_version,
            displayed_message=record.report_snapshot_message,
            displayed_message_version=record.report_snapshot_message_version,
            operational_note_id=active_operational_note.id if active_operational_note else None,
            operational_note_text=active_operational_note.note_text if active_operational_note else None,
            max_seen_value=record.max_seen_value,
            last_seen_value=record.last_seen_value,
            matches_last_seen=record.last_seen_value == payload.reported_value,
            matches_any_seen=payload.reported_value in seen_values,
            reaction_ms=payload.reaction_ms,
        )
        db.add(claim)
        db.flush()

        series.completed_count += 1
        series.is_closed = True
        series.close_reason = series.close_reason or "session_completed"
        db.add(series)

        old_state = record.state
        record.reported_value = payload.reported_value
        record.is_honest = payload.reported_value == record.first_result_value
        record.payout_amount = payout_amount_for_claim(
            payload.reported_value, record.selected_for_payment
        )
        if payload.language:
            record.language_at_claim = payload.language
            if (
                record.language_at_access
                and record.language_at_access != payload.language
            ):
                record.language_changed_during_session = True
        record.claim_submitted_at = utcnow()
        record.completed_at = utcnow()
        record.screen_cursor = "exit"
        record.state = (
            "completed_win" if record.selected_for_payment else "completed_no_win"
        )
        db.add(record)

        quality_flags = build_quality_flags(db, record)
        antifraud_flags = build_antifraud_flags(db, record)
        claim.quality_flags_json = stable_json(quality_flags)
        claim.antifraud_flags_json = stable_json(antifraud_flags)
        record.quality_flags_json = stable_json(quality_flags)
        record.antifraud_flags_json = stable_json(antifraud_flags)
        db.add(claim)
        db.add(record)

        is_valid_completed = is_valid_completed_session(db, record)
        if is_valid_completed and not record.is_valid_completed:
            record.is_valid_completed = True
            record.valid_completed_at = utcnow()
            db.add(record)
            experiment_state = get_or_create_experiment_state(db, for_update=True)
            experiment_state.valid_completed_count += 1
            experiment_state.updated_at = utcnow()
            db.add(experiment_state)

        snapshot = get_or_create_snapshot_record(db, record.id)
        snapshot.language_used = (
            snapshot.language_used
            or record.language_at_claim
            or record.language_at_access
        )
        snapshot.treatment_key = record.report_snapshot_treatment or record.treatment_key
        snapshot.treatment_family = record.treatment_family
        snapshot.norm_target_value = record.report_snapshot_target_value
        snapshot.is_control = (
            (record.report_snapshot_treatment or record.treatment_key)
            == CONTROL_TREATMENT_KEY
        )
        snapshot.displayed_count_target = record.report_snapshot_count_target
        snapshot.displayed_denominator = record.report_snapshot_denominator
        snapshot.displayed_message_text = (
            snapshot.displayed_message_text or record.report_snapshot_message
        )
        snapshot.displayed_message_version = record.report_snapshot_message_version
        snapshot.control_message_text = (
            (
                snapshot.control_message_text
                or record.report_snapshot_message
            )
            if (record.report_snapshot_treatment or record.treatment_key) == "control"
            else snapshot.control_message_text
        )
        snapshot.first_result_value = record.first_result_value
        snapshot.last_seen_value = record.last_seen_value
        snapshot.rerolls_visible_json = stable_json(seen_values[1:])
        snapshot.final_state_shown = record.state
        snapshot.final_amount_eur = int(record.payout_amount / 100)
        snapshot.payout_reference_shown = (
            payout_reference_code(record.id) if record.selected_for_payment else None
        )
        snapshot.updated_at = utcnow()
        db.add(snapshot)

        payment = Payment(
            session_id=record.id,
            claim_id=claim.id,
            eligible=record.selected_for_payment,
            amount_cents=record.payout_amount,
            status="pending" if record.selected_for_payment else "not_eligible",
            payout_reference=(
                payout_reference_code(record.id)
                if record.selected_for_payment
                else None
            ),
            operational_note_id=active_operational_note.id if active_operational_note else None,
            operational_note_text=active_operational_note.note_text if active_operational_note else None,
        )
        db.add(payment)

        if record.selected_for_payment and "same_device_multiple_bracelets" in antifraud_flags:
            create_fraud_flag(
                db,
                session_id=record.id,
                user_id=record.user_id,
                flag_key="manual_review_winner",
                severity="high",
                payload={"reason": "winner_with_device_duplication"},
            )

        create_audit(
            db,
            entity_type="session",
            entity_id=record.id,
            action="claim_submitted",
            session_id=record.id,
            old_state=old_state,
            new_state=record.state,
            idempotency_key=payload.idempotency_key,
            payload={
                "reported_value": payload.reported_value,
                "is_honest": record.is_honest,
                "is_valid_completed": record.is_valid_completed,
                "treatment_key": record.treatment_key,
                "treatment_deck_id": record.treatment_deck_id,
                "treatment_card_position": record.treatment_card_position,
                "result_deck_id": record.result_deck_id,
                "result_card_position": record.result_card_position,
                "payment_deck_id": record.payment_deck_id,
                "payment_card_position": record.payment_card_position,
            },
        )

        response_payload = {"session": build_session_payload(db, record)}
        save_receipt(
            db,
            session_id=record.id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
            response_payload=response_payload,
        )
        db.commit()
        return response_payload


@app.post("/v1/session/{session_id}/claim-followup")
def update_claim_followup(
    session_id: str,
    payload: ClaimFollowupRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"session:{session_id}"):
        record = get_session_or_404(db, session_id, for_update=True)
        ensure_valid_state(
            record,
            {"completed_win", "completed_no_win"},
            "claim-followup",
        )
        claim = db.exec(select(Claim).where(Claim.session_id == record.id)).first()
        if not claim:
            raise HTTPException(status_code=409, detail="La sesion todavia no tiene claim")
        if (
            payload.crowd_prediction_value is None
            and payload.social_recall_count is None
        ):
            raise HTTPException(status_code=400, detail="No hay respuestas para guardar")

        now = utcnow()
        updated_fields: dict[str, Any] = {}

        if payload.language:
            record.language_at_claim = payload.language
            if (
                record.language_at_access
                and record.language_at_access != payload.language
            ):
                record.language_changed_during_session = True

        if payload.crowd_prediction_value is not None:
            if claim.crowd_prediction_value is None:
                claim.crowd_prediction_value = payload.crowd_prediction_value
                claim.crowd_prediction_submitted_at = now
                updated_fields["crowd_prediction_value"] = payload.crowd_prediction_value
            elif claim.crowd_prediction_value == payload.crowd_prediction_value:
                updated_fields["crowd_prediction_value"] = claim.crowd_prediction_value

        if payload.social_recall_count is not None:
            if claim.social_recall_count is None:
                claim.social_recall_count = payload.social_recall_count
                claim.social_recall_correct = (
                    is_social_recall_answer_correct(
                        payload.social_recall_count,
                        claim.displayed_count_target,
                    )
                )
                claim.social_recall_submitted_at = now
                updated_fields["social_recall_count"] = payload.social_recall_count
                updated_fields["social_recall_correct"] = claim.social_recall_correct
            elif claim.social_recall_count == payload.social_recall_count:
                updated_fields["social_recall_count"] = claim.social_recall_count
                updated_fields["social_recall_correct"] = claim.social_recall_correct

        db.add(claim)
        db.add(record)
        create_audit(
            db,
            entity_type="claim",
            entity_id=claim.id,
            action="claim_followup_updated",
            session_id=record.id,
            old_state=record.state,
            new_state=record.state,
            payload=updated_fields,
        )
        db.commit()
        return {"session": build_session_payload(db, record)}


@app.post("/v1/telemetry/batch")
def telemetry_batch(
    payload: TelemetryBatchRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"session:{payload.session_id}:telemetry"):
        record = get_session_or_404(db, payload.session_id, for_update=True)
        active_operational_note = get_active_operational_note(db)
        accepted = 0
        for item in payload.events:
            server_now = utcnow()
            clock_skew_ms = None
            if item.client_ts is not None:
                clock_skew_ms = int(server_now.timestamp() * 1000 - item.client_ts)
            db.add(
                TelemetryEvent(
                    session_id=record.id,
                    event_type=item.event_type,
                    event_name=item.event_name,
                    screen_name=item.screen_name,
                    client_ts=item.client_ts,
                    event_sequence_number=item.event_sequence_number,
                    timezone_offset_minutes=item.timezone_offset_minutes,
                    client_clock_skew_estimate_ms=clock_skew_ms,
                    duration_ms=item.duration_ms,
                    value=item.value,
                    app_language=item.app_language,
                    browser_language=item.browser_language,
                    spell_id=item.spell_id,
                    interaction_target=item.interaction_target,
                    interaction_role=item.interaction_role,
                    cta_kind=item.cta_kind,
                    endpoint_name=item.endpoint_name,
                    request_method=item.request_method,
                    status_code=item.status_code,
                    latency_ms=item.latency_ms,
                    attempt_number=item.attempt_number,
                    is_retry=item.is_retry,
                    error_name=item.error_name,
                    network_status=item.network_status,
                    visibility_state=item.visibility_state,
                    operational_note_id=active_operational_note.id if active_operational_note else None,
                    operational_note_text=active_operational_note.note_text if active_operational_note else None,
                    payload_json=stable_json(item.payload)
                    if item.payload is not None
                    else None,
                    server_ts=server_now,
                )
            )
            accepted += 1
            update_screen_spell_from_event(
                db,
                session_id=record.id,
                item=item,
                server_now=server_now,
            )
            if item.client_context is not None:
                upsert_session_client_context(
                    db,
                    session_id=record.id,
                    raw_context=item.client_context,
                    request=request,
                    app_language=item.app_language or record.language_at_claim or record.language_at_access,
                )
            if item.event_name in {"blur", "visibility_hidden"}:
                record.blur_count += 1
            if item.event_name in {"page_reload", "reload"}:
                record.refresh_count += 1
            if item.event_type == "error" or (item.status_code and item.status_code >= 400):
                record.network_error_count += 1
            if item.is_retry or item.event_name in {"retry", "retry_success", "retry_error"}:
                record.retry_count += 1
            if item.event_type == "click":
                record.click_count_total += 1
            if item.event_name == "screen_enter":
                record.screen_changes_count += 1
            if item.event_name == "language_change":
                record.language_change_count += 1
                record.language_changed_during_session = True
            if item.event_sequence_number and item.event_sequence_number > record.max_event_sequence_number:
                record.max_event_sequence_number = item.event_sequence_number
            if item.app_language:
                if record.language_at_access is None:
                    record.language_at_access = item.app_language
                if record.language_at_claim and record.language_at_claim != item.app_language:
                    record.language_changed_during_session = True
                if record.language_at_access and record.language_at_access != item.app_language:
                    record.language_changed_during_session = True
                if item.screen_name in {"report", "exit"}:
                    record.language_at_claim = item.app_language
            record.telemetry_event_count += 1
        record.last_seen_at = utcnow()
        db.add(record)
        db.commit()
        return {"accepted_count": accepted}


@app.post("/v1/session/{session_id}/display-snapshot")
def capture_display_snapshot(
    session_id: str,
    payload: DisplaySnapshotRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"session:{session_id}:snapshot"):
        record = get_session_or_404(db, session_id, for_update=True)
        snapshot = get_or_create_snapshot_record(db, record.id)
        snapshot.language_used = payload.language or snapshot.language_used or record.language_at_claim or record.language_at_access
        snapshot.treatment_key = record.report_snapshot_treatment or record.treatment_key
        snapshot.treatment_family = record.treatment_family
        snapshot.norm_target_value = (
            record.report_snapshot_target_value
            if record.report_snapshot_target_value is not None
            else record.norm_target_value
        )
        snapshot.is_control = (
            (record.report_snapshot_treatment or record.treatment_key)
            == CONTROL_TREATMENT_KEY
        )
        snapshot.displayed_count_target = record.report_snapshot_count_target
        snapshot.displayed_denominator = record.report_snapshot_denominator
        if payload.treatment_message_text:
            snapshot.displayed_message_text = payload.treatment_message_text
        if payload.control_message_text:
            snapshot.control_message_text = payload.control_message_text
        snapshot.displayed_message_version = record.report_snapshot_message_version
        snapshot.first_result_value = record.first_result_value
        snapshot.last_seen_value = record.last_seen_value
        if payload.rerolls_visible is not None:
            snapshot.rerolls_visible_json = stable_json(payload.rerolls_visible)
        elif snapshot.rerolls_visible_json is None:
            throws = db.exec(
                select(Throw)
                .where(Throw.session_id == record.id)
                .order_by(Throw.attempt_index)
            ).all()
            snapshot.rerolls_visible_json = stable_json(
                [item.result_value for item in throws[1:]]
            )
        throws = db.exec(
            select(Throw)
            .where(Throw.session_id == record.id)
            .order_by(Throw.attempt_index)
        ).all()
        snapshot.all_values_seen_json = stable_json([item.result_value for item in throws])
        if payload.final_message_text:
            snapshot.final_message_text = payload.final_message_text
        if payload.final_amount_eur is not None:
            snapshot.final_amount_eur = payload.final_amount_eur
        if payload.payout_reference_shown:
            snapshot.payout_reference_shown = payload.payout_reference_shown
        if payload.payout_phone_shown:
            snapshot.payout_phone_shown = payload.payout_phone_shown
        if payload.screen_name == "exit":
            snapshot.final_state_shown = record.state
        snapshot.updated_at = utcnow()
        db.add(snapshot)
        create_audit(
            db,
            entity_type="snapshot",
            entity_id=snapshot.id,
            action="display_snapshot_captured",
            session_id=record.id,
            payload={
                "screen_name": payload.screen_name,
                "language": snapshot.language_used,
            },
        )
        db.commit()
        return {"ok": True}


@app.post("/v1/payment/lookup")
def payment_lookup(
    payload: PaymentLookupRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"payment:{payload.code}:lookup"):
        payment = get_payment_by_reference(db, payload.code)
        session_record = get_session_or_404(db, payment.session_id)
        return {
            "valid": payment.eligible and payment.status in {"pending", "queued"},
            "status": payment.status,
            "amount_eur": int(payment.amount_cents / 100),
            "code": payment.payout_reference,
            "can_submit": payment.eligible and payment.status == "pending",
            "donation_available": True,
            "experiment_phase": session_record.experiment_phase,
        }


@app.post("/v1/payment/submit")
def payment_submit(
    payload: PaymentSubmitRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    rate_limit(f"payment:{payload.code}", settings.payment_rate_limit_per_minute)
    with distributed_lock(f"payment:{payload.code}"):
        active_operational_note = get_active_operational_note(db)
        try:
            normalized_bracelet_id = normalize_bracelet_id(payload.bracelet_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        normalized_phone = (
            "DONATION"
            if payload.donation_requested
            else normalize_phone(payload.phone or "")
        )
        payment = get_payment_by_reference(db, payload.code, for_update=True)
        if not payment.eligible:
            raise HTTPException(status_code=400, detail="Codigo no elegible para cobro")
        if payment.status != "pending":
            raise HTTPException(status_code=409, detail="Codigo de cobro ya utilizado")
        session_record = db.get(SessionRecord, payment.session_id)
        if not session_record:
            raise HTTPException(status_code=404, detail="Sesion no encontrada")
        user = db.get(User, session_record.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Sesion no encontrada")
        if user.bracelet_id != normalized_bracelet_id:
            raise HTTPException(
                status_code=400,
                detail="Pulsera erronea, no coincide con la registrada inicialmente.",
            )

        existing_request = db.exec(
            select(PayoutRequest).where(PayoutRequest.payment_id == payment.id)
        ).first()
        if existing_request:
            raise HTTPException(status_code=409, detail="Codigo de cobro ya utilizado")

        payout_request = PayoutRequest(
            session_id=payment.session_id,
            payment_id=payment.id,
            payout_reference=payload.code,
            requested_phone=normalized_phone,
            donation_requested=payload.donation_requested,
            language_used=payload.language,
            message_text=payload.message_text,
            status="submitted",
            operational_note_id=active_operational_note.id if active_operational_note else None,
            operational_note_text=active_operational_note.note_text if active_operational_note else None,
        )
        db.add(payout_request)
        payment.status = "queued"
        db.add(payment)
        create_audit(
            db,
            entity_type="payment",
            entity_id=payment.id,
            action="payout_request_submitted",
            session_id=payment.session_id,
            payload={
                "payout_reference": payload.code,
                "bracelet_id_verified": True,
                "donation_requested": payload.donation_requested,
                "language": payload.language,
            },
        )
        db.commit()
        return {
            "ok": True,
            "status": payment.status,
            "amount_eur": int(payment.amount_cents / 100),
            "requested_phone": normalized_phone,
            "donation_requested": payload.donation_requested,
        }


@app.get("/payout", response_class=HTMLResponse)
def payout_page(code: Optional[str] = None) -> HTMLResponse:
    safe_code = code or ""
    html = f"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Cobro SONAR 2026</title>
    <style>
      body {{ font-family: Arial, sans-serif; background:#f4f1eb; margin:0; padding:24px; color:#111; }}
      .card {{ max-width:480px; margin:0 auto; background:white; border-radius:24px; padding:24px; box-shadow:0 20px 60px rgba(0,0,0,.08); }}
      h1 {{ font-size:28px; margin:0 0 12px; text-transform:uppercase; }}
      p {{ line-height:1.5; color:#444; }}
      label {{ display:block; font-size:12px; letter-spacing:.16em; text-transform:uppercase; color:#666; margin:16px 0 8px; }}
      input, textarea {{ width:100%; box-sizing:border-box; padding:14px 16px; border-radius:16px; border:1px solid rgba(0,0,0,.12); font-size:16px; }}
      textarea {{ min-height:120px; resize:vertical; }}
      button {{ width:100%; margin-top:20px; padding:16px; border:none; border-radius:999px; background:#111; color:white; font-weight:700; letter-spacing:.14em; text-transform:uppercase; cursor:pointer; }}
      .muted {{ font-size:13px; color:#666; }}
      .notice {{ margin-top:16px; padding:14px 16px; border-radius:16px; background:#f7f7f7; }}
      .error {{ background:#fff1f1; color:#8a1f1f; }}
      .success {{ background:#eefcf2; color:#116b2e; }}
    </style>
  </head>
  <body>
    <div class="card">
      <p class="muted">Cobro separado del experimento</p>
      <h1>Solicitar cobro</h1>
      <p>Introduce tu codigo de cobro y el telefono donde quieres recibir el Bizum. Si prefieres donar el premio, indicalo al final.</p>
      <label for="code">Codigo de cobro</label>
      <input id="code" value="{safe_code}" />
      <label for="bracelet">ID de la pulsera</label>
      <input id="bracelet" placeholder="Ej: AB12CD34" />
      <label for="phone">Telefono</label>
      <input id="phone" placeholder="Ej: 34612345678" />
      <label for="message">Mensaje adicional</label>
      <textarea id="message" placeholder="Puedes anadir ONG si prefieres donar el premio."></textarea>
      <div class="notice muted">Este formulario solo registra la solicitud administrativa de cobro. No modifica tu respuesta experimental.</div>
      <button id="submit">Enviar solicitud</button>
      <div id="status" class="notice" style="display:none;"></div>
    </div>
    <script>
      const statusEl = document.getElementById('status');
      document.getElementById('submit').addEventListener('click', async () => {{
        statusEl.style.display = 'none';
        const payload = {{
          code: document.getElementById('code').value.trim(),
          bracelet_id: document.getElementById('bracelet').value.trim().toUpperCase(),
          phone: document.getElementById('phone').value.trim(),
          language: document.documentElement.lang || 'es',
          donation_requested: /\\bONG\\b/i.test(document.getElementById('message').value),
          message_text: document.getElementById('message').value
        }};
        try {{
          const response = await fetch('/v1/payment/submit', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload)
          }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'No se pudo enviar la solicitud');
          statusEl.className = 'notice success';
          statusEl.textContent = 'Solicitud enviada correctamente. El equipo revisara tu cobro.';
          statusEl.style.display = 'block';
        }} catch (error) {{
          statusEl.className = 'notice error';
          statusEl.textContent = error.message || 'No se pudo enviar la solicitud';
          statusEl.style.display = 'block';
        }}
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(html)


@app.get("/admin/experiment")
def admin_experiment(db: Session = Depends(get_session)) -> dict[str, Any]:
    state = get_or_create_experiment_state(db)
    prizes = prize_summary(db)
    active_operational_note = get_active_operational_note(db)
    treatment_counts: dict[str, int] = {}
    for treatment_key in TREATMENT_KEYS:
        treatment_counts[treatment_key] = int(
            db.exec(
                select(func.count())
                .select_from(SessionRecord)
                .where(SessionRecord.treatment_key == treatment_key)
            ).one()
            or 0
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "current_phase": state.current_phase,
        "experiment_status": state.experiment_status,
        "phase_transition_threshold": state.phase_transition_threshold,
        "valid_completed_count": state.valid_completed_count,
        "phase_2_activated_at": (
            state.phase_2_activated_at.isoformat()
            if state.phase_2_activated_at
            else None
        ),
        "paused_at": state.paused_at.isoformat() if state.paused_at else None,
        "resumed_at": state.resumed_at.isoformat() if state.resumed_at else None,
        "pause_reason": state.pause_reason,
        "ui_version": UI_VERSION,
        "consent_version": CONSENT_VERSION,
        "treatment_version": state.treatment_version,
        "allocation_version": state.allocation_version,
        "deck_version": DECK_VERSION,
        "payment_version": PAYMENT_VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        "lexicon_version": LEXICON_VERSION,
        "deployment_context": DEPLOYMENT_CONTEXT,
        "site_code": SITE_CODE,
        "campaign_code": CAMPAIGN_CODE,
        "environment_label": ENVIRONMENT_LABEL,
        "prizes": prizes,
        "treatment_observations": treatment_counts,
        "treatment_decks": deck_status_payload(
            db,
            deck_model=TreatmentDeck,
            card_model=TreatmentDeckCard,
        ),
        "result_decks": deck_status_payload(
            db,
            deck_model=ResultDeck,
            card_model=ResultDeckCard,
        ),
        "payment_decks": deck_status_payload(
            db,
            deck_model=PaymentDeck,
            card_model=PaymentDeckCard,
        ),
        "demo_ids": {
            "winner_control": "CTRL1234",
            "loser_norm_0": "NORM0000",
            "loser_norm_1": "NORM0001",
        },
        "active_operational_note": operational_note_payload(active_operational_note),
    }


@app.post("/admin/operational-notes/activate")
def admin_activate_operational_note(
    payload: AdminOperationalNoteRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("operational-note"):
        note = activate_operational_note(db, note_text=payload.note_text)
        return {"ok": True, "active_operational_note": operational_note_payload(note)}


@app.post("/admin/operational-notes/clear")
def admin_clear_operational_note(db: Session = Depends(get_session)) -> dict[str, Any]:
    with distributed_lock("operational-note"):
        cleared = clear_operational_note(db)
        return {
            "ok": True,
            "cleared_operational_note": operational_note_payload(cleared),
            "active_operational_note": operational_note_payload(None),
        }


@app.post("/admin/experiment/pause")
def admin_experiment_pause(
    payload: AdminExperimentControlRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("experiment-control"):
        state = pause_experiment(db, reason=payload.reason)
        return {
            "ok": True,
            "experiment_status": state.experiment_status,
            "paused_at": state.paused_at.isoformat() if state.paused_at else None,
            "pause_reason": state.pause_reason,
            "prizes": prize_summary(db),
        }


@app.post("/admin/experiment/resume")
def admin_experiment_resume(
    payload: AdminExperimentControlRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("experiment-control"):
        state = resume_experiment(db, reason=payload.reason)
        return {
            "ok": True,
            "experiment_status": state.experiment_status,
            "resumed_at": state.resumed_at.isoformat() if state.resumed_at else None,
            "prizes": prize_summary(db),
        }


@app.get("/admin/roots")
def admin_roots(db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    roots = db.exec(select(SeriesRoot).order_by(SeriesRoot.root_sequence)).all()
    response: list[dict[str, Any]] = []
    for root in roots:
        treatment_deck = db.exec(
            select(TreatmentDeck).where(TreatmentDeck.legacy_root_id == root.id)
        ).first()
        series_items = db.exec(
            select(Series).where(Series.root_id == root.id).order_by(Series.treatment_key)
        ).all()
        payment_deck = None
        if treatment_deck and treatment_deck.deck_index > 0:
            payment_deck = db.exec(
                select(PaymentDeck).where(PaymentDeck.deck_index == treatment_deck.deck_index)
            ).first()
        payment_winner_positions = []
        if payment_deck:
            payment_winner_positions = [
                card.card_position
                for card in db.exec(
                    select(PaymentDeckCard).where(
                        PaymentDeckCard.deck_id == payment_deck.id,
                        PaymentDeckCard.payout_eligible == True,  # noqa: E712
                    )
                ).all()
            ]
        response.append(
            {
                "root_id": root.id,
                "root_sequence": root.root_sequence,
                "experiment_phase": root.experiment_phase,
                "treatment_version": root.treatment_version,
                "allocation_version": root.allocation_version,
                "status": root.status,
                "close_reason": root.close_reason,
                "treatment_deck_id": treatment_deck.id if treatment_deck else None,
                "treatment_deck_index": treatment_deck.deck_index if treatment_deck else None,
                "treatment_deck_status": treatment_deck.status if treatment_deck else None,
                "payment_deck_id": payment_deck.id if payment_deck else None,
                "payment_deck_index": payment_deck.deck_index if payment_deck else None,
                "payment_winner_positions": payment_winner_positions,
                "series": [
                    {
                        "series_id": item.id,
                        "treatment_key": item.treatment_key,
                        "experiment_phase": item.experiment_phase,
                        "treatment_family": item.treatment_family,
                        "norm_target_value": item.norm_target_value,
                        "position_counter": item.position_counter,
                        "completed_count": item.completed_count,
                        "visible_count_target": item.visible_count_target,
                        "actual_count_target": item.actual_count_target,
                        "visible_window_version": item.visible_window_version,
                        "actual_window_version": item.actual_window_version,
                        "is_closed": item.is_closed,
                        "close_reason": item.close_reason,
                    }
                    for item in series_items
                ],
            }
        )
    return response


@app.get("/admin/session/{bracelet_id}")
def admin_session(bracelet_id: str, db: Session = Depends(get_session)) -> dict[str, Any]:
    try:
        normalized = normalize_bracelet_id(bracelet_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.exec(select(User).where(User.bracelet_id == normalized)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Pulsera no encontrada")
    record = db.exec(select(SessionRecord).where(SessionRecord.user_id == user.id)).first()
    if not record:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return build_session_payload(db, record)


@app.get("/admin/exports", response_class=HTMLResponse)
def admin_exports(db: Session = Depends(get_session)) -> HTMLResponse:
    state = get_or_create_experiment_state(db)
    stats = dataset_export_stats(db)
    return HTMLResponse(exports_page_html(state, stats, prize_summary(db)))


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_session)) -> HTMLResponse:
    return HTMLResponse(dashboard_page_html(db))


@app.get("/admin/export/{dataset_name}.csv")
def admin_export_dataset_csv(
    dataset_name: str,
    db: Session = Depends(get_session),
) -> Response:
    rows = dataset_rows(db, dataset_name)
    csv_bytes = rows_to_csv_bytes(rows)
    filename = export_filename(dataset_name, "csv")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/admin/export/bundle/{bundle_name}.zip")
def admin_export_bundle(
    bundle_name: str,
    db: Session = Depends(get_session),
) -> Response:
    bundle_bytes = build_export_bundle(db, bundle_name)
    filename = export_filename(f"sonar_{bundle_name}", "zip")
    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/admin/export/sessions")
def admin_export_sessions(db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return dataset_rows(db, "sessions")
