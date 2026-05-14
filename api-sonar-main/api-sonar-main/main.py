import csv
import hashlib
import httpx
import io
import json
import os
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import inspect, or_, text
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
    normalize_phase_key,
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
    ANALYSIS_READY_DATASET_NAME,
    ANALYSIS_READY_DATASET_VERSION,
    ANALYSIS_READY_EXTENDED_DATASET_NAME,
    ANALYSIS_READY_EXTENDED_DATASET_VERSION,
    analysis_ready_export_filename,
    DATASET_DESCRIPTIONS,
    admin_payments_page_html,
    admin_payments_payload,
    build_export_bundle,
    dashboard_page_html,
    dataset_csv_fieldnames,
    dataset_export_stats,
    dataset_rows,
    export_filename,
    exports_page_html,
    live_dashboard_payload,
    live_dashboard_page_html_v3,
    participant_analysis_export_filename,
    rows_to_csv_bytes,
)
from models import (
    ActionReceipt,
    AuditEvent,
    Claim,
    ConsentRecord,
    DeckPosition,
    EmailInterest,
    ExperimentClosureLog,
    ExperimentState,
    FraudFlag,
    GatewayAccessLog,
    GatewayRoute,
    InterestSignup,
    OperationalNote,
    Payment,
    PaymentDeck,
    PaymentDeckCard,
    PayoutRequest,
    Pulsera,
    ReferralClick,
    ReferralLink,
    ResultDeck,
    ResultDeckCard,
    Series,
    SeriesRoot,
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
    clear_runtime_state,
    cache_receipt,
    check_admin_credentials,
    distributed_lock,
    get_admin_actor,
    get_cached_receipt,
    get_experiment_status_cache,
    logger,
    record_http_metric,
    record_screen_transition,
    record_session_completed,
    record_session_started,
    rate_limit,
    redis_ping,
    request_log_payload,
    set_experiment_status_cache,
)
from settings import settings

app = FastAPI(title="Sonar Experimental API")

SESSION_INSTALLATION_HEADER = "x-sonar-installation"
GATEWAY_TARGET_PRIMARY = "primary"
GATEWAY_TARGET_BACKUP = "backup"
GATEWAY_TARGETS = {GATEWAY_TARGET_PRIMARY, GATEWAY_TARGET_BACKUP}
EXPERIMENT_MODE_LIVE = "live"
EXPERIMENT_MODE_CLOSING = "closing"
EXPERIMENT_MODE_CLOSED = "closed"
EXPERIMENT_MODES = {
    EXPERIMENT_MODE_LIVE,
    EXPERIMENT_MODE_CLOSING,
    EXPERIMENT_MODE_CLOSED,
}
GATEWAY_QR_QUERY_KEYS = (
    "qr",
    "qr_id",
    "poster",
    "poster_id",
    "cartel",
    "cartel_id",
)

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
_gateway_failover_state_lock = threading.Lock()
_gateway_failover_state: dict[str, Any] = {
    "monitor_enabled": settings.gateway_failover_enabled,
    "monitor_running": False,
    "last_checked_at": None,
    "last_event": None,
    "primary": {
        "url": settings.gateway_primary_healthcheck_url,
        "healthy": None,
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "last_status_code": None,
        "last_latency_ms": None,
        "last_error": None,
        "last_checked_at": None,
    },
    "backup": {
        "url": settings.gateway_backup_healthcheck_url,
        "healthy": None,
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "last_status_code": None,
        "last_latency_ms": None,
        "last_error": None,
        "last_checked_at": None,
    },
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def admin_and_request_logging(request: Request, call_next):
    start_time = time.perf_counter()
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
            record_http_metric(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=0.0,
            )
            return response
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "http_request_failed",
            extra={
                "structured_payload": request_log_payload(
                    request,
                    status_code=500,
                    duration_ms=duration_ms,
                )
            },
        )
        record_http_metric(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
        )
        raise
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "http_request",
        extra={
            "structured_payload": request_log_payload(
                request,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        },
    )
    if response.headers.get("X-Sonar-Skip-Metrics") != "1":
        record_http_metric(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
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
    gateway_visit_id: Optional[str] = None
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


class InterestCaptureRequest(BaseModel):
    email: str = PydanticField(min_length=5, max_length=320)
    source: str = PydanticField(default="panic_screen", min_length=3, max_length=64)


class AdminExperimentControlRequest(BaseModel):
    reason: Optional[str] = None


class AdminExperimentModeRequest(BaseModel):
    mode: str = PydanticField(min_length=4, max_length=7)
    reason: Optional[str] = None


class AdminPanicRequest(BaseModel):
    mode: str = PydanticField(default=EXPERIMENT_MODE_CLOSED, min_length=6, max_length=7)
    soft: bool = False
    reason: Optional[str] = None


class AdminSystemResetRequest(BaseModel):
    passphrase: str = PydanticField(min_length=8, max_length=256)
    reason: Optional[str] = None


class AdminOperationalNoteRequest(BaseModel):
    note_text: str = PydanticField(min_length=3, max_length=1000)


class AdminGatewayRouteUpsertRequest(BaseModel):
    qr_code: str = PydanticField(min_length=1, max_length=128)
    zone_code: Optional[str] = PydanticField(default=None, max_length=128)
    primary_target_url: str = PydanticField(min_length=8, max_length=2048)
    backup_target_url: Optional[str] = PydanticField(default=None, max_length=2048)
    active_target: str = PydanticField(default="primary", min_length=6, max_length=7)
    enabled: bool = True
    notes: Optional[str] = PydanticField(default=None, max_length=2000)


class AdminGatewayRouteSwitchRequest(BaseModel):
    active_target: str = PydanticField(min_length=6, max_length=7)


class AdminGatewayModeRequest(BaseModel):
    mode: str = PydanticField(min_length=6, max_length=7)


class ReferralLinkCreateRequest(BaseModel):
    session_id: str = PydanticField(min_length=8, max_length=64)
    channel: str = PydanticField(default="whatsapp", min_length=2, max_length=64)
    traffic_source: Optional[str] = PydanticField(default=None, max_length=64)
    traffic_medium: Optional[str] = PydanticField(default=None, max_length=64)
    campaign_code: Optional[str] = PydanticField(default=None, max_length=128)
    target_path: str = PydanticField(default="/", min_length=1, max_length=1024)


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


MINIMAL_TELEMETRY_EVENT_NAMES = {
    "session_start",
    "first_throw",
    "reroll_count",
    "report_value",
    "reaction_time_ms",
    "session_end",
}

SESSION_PAYLOAD_MODE_FLOW = "flow"
SESSION_PAYLOAD_MODE_ANALYTICS = "analytics"
SessionPayloadMode = Literal["flow", "analytics"]


@dataclass
class SessionPayloadRelations:
    series: Series
    root: Optional[SeriesRoot] = None
    treatment_deck: Optional[TreatmentDeck] = None
    result_deck: Optional[ResultDeck] = None
    payment_deck: Optional[PaymentDeck] = None
    throws: Optional[list[Throw]] = None
    claim: Optional[Claim] = None
    payment: Optional[Payment] = None
    consent_record: Optional[ConsentRecord] = None
    snapshot_record: Optional[SnapshotRecord] = None
    client_context: Optional[SessionClientContext] = None


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def json_dumps_compact(payload: Any, *, sort_keys: bool = False) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=sort_keys,
    )


def deployment_config_fingerprint() -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "ui_version": UI_VERSION,
        "consent_version": CONSENT_VERSION,
        "deck_version": DECK_VERSION,
        "payment_version": PAYMENT_VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        "lexicon_version": LEXICON_VERSION,
        "deployment_context": DEPLOYMENT_CONTEXT,
        "site_code": SITE_CODE,
        "campaign_code": CAMPAIGN_CODE,
        "environment_label": ENVIRONMENT_LABEL,
        "database_url": settings.database_url,
        "redis_url": settings.redis_url,
        "require_redis": settings.require_redis,
        "app_hash_pepper": os.getenv("APP_HASH_PEPPER", ""),
        "experiment_master_seed": os.getenv("EXPERIMENT_MASTER_SEED", ""),
        "project_parameters_path": os.getenv("PROJECT_PARAMETERS_PATH", ""),
    }
    return hashlib.sha256(
        json_dumps_compact(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def normalize_gateway_qr_code(raw_qr_code: str) -> str:
    qr_code = raw_qr_code.strip().lower()
    if not qr_code:
        raise ValueError("QR invalido")
    if any(character in qr_code for character in "/?#"):
        raise ValueError("QR invalido")
    if any(character.isspace() for character in qr_code):
        raise ValueError("QR invalido")
    allowed_extra = {".", "_", ":", "-"}
    if not all(character.isalnum() or character in allowed_extra for character in qr_code):
        raise ValueError("QR invalido")
    return qr_code


def derive_zone_code(qr_code: str) -> str:
    normalized_qr_code = normalize_gateway_qr_code(qr_code)
    parts = [part for part in normalized_qr_code.split("_") if part]
    if len(parts) >= 2:
        return "_".join(parts[:-1])
    if "-" in normalized_qr_code:
        dashed_parts = [part for part in normalized_qr_code.split("-") if part]
        if len(dashed_parts) >= 2:
            return "-".join(dashed_parts[:-1])
    return normalized_qr_code


def normalize_gateway_zone_code(raw_zone_code: Optional[str], *, qr_code: str) -> str:
    if raw_zone_code and raw_zone_code.strip():
        return normalize_gateway_qr_code(raw_zone_code)
    return derive_zone_code(qr_code)


def normalize_gateway_target(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in GATEWAY_TARGETS:
        raise ValueError("Destino invalido")
    return normalized


def normalize_gateway_target_url(raw_url: Optional[str]) -> Optional[str]:
    if raw_url is None:
        return None
    value = raw_url.strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("La URL de destino debe ser absoluta y usar http o https")
    return urlunsplit(parsed)


def gateway_public_url_for_qr(qr_code: str) -> str:
    return f"{settings.gateway_public_base_url.rstrip('/')}/play/{qr_code}"


def gateway_route_payload(route: GatewayRoute) -> dict[str, Any]:
    active_url = (
        route.backup_target_url
        if route.active_target == GATEWAY_TARGET_BACKUP
        else route.primary_target_url
    )
    return {
        "id": route.id,
        "qr_code": route.qr_code,
        "zone_code": route.zone_code,
        "public_url": gateway_public_url_for_qr(route.qr_code),
        "primary_target_url": route.primary_target_url,
        "backup_target_url": route.backup_target_url,
        "active_target": route.active_target,
        "active_target_url": active_url,
        "enabled": route.enabled,
        "notes": route.notes,
        "last_switched_at": (
            route.last_switched_at.isoformat() if route.last_switched_at else None
        ),
        "created_at": route.created_at.isoformat(),
        "updated_at": route.updated_at.isoformat(),
    }


def gateway_access_log_payload(log_item: GatewayAccessLog) -> dict[str, Any]:
    return {
        "id": log_item.id,
        "route_id": log_item.route_id,
        "qr_code": log_item.qr_code,
        "zone_code": log_item.zone_code,
        "session_id": log_item.session_id,
        "gateway_visit_id": log_item.gateway_visit_id,
        "request_host": log_item.request_host,
        "request_path": log_item.request_path,
        "query_string": log_item.query_string,
        "selected_target": log_item.selected_target,
        "resolved_target_url": log_item.resolved_target_url,
        "redirect_status_code": log_item.redirect_status_code,
        "status": log_item.status,
        "referer": log_item.referer,
        "traffic_source": log_item.traffic_source,
        "traffic_medium": log_item.traffic_medium,
        "request_user_agent": log_item.request_user_agent,
        "created_at": log_item.created_at.isoformat(),
    }


def resolve_gateway_target_url(route: GatewayRoute) -> tuple[str, str]:
    active_target = route.active_target
    if active_target == GATEWAY_TARGET_BACKUP:
        if not route.backup_target_url:
            raise ValueError("La ruta no tiene destino backup configurado")
        return active_target, route.backup_target_url
    return GATEWAY_TARGET_PRIMARY, route.primary_target_url


def build_gateway_redirect_url(
    base_target_url: str,
    *,
    request: Request,
    qr_code: str,
    gateway_visit_id: str,
) -> str:
    parsed_target = urlsplit(base_target_url)
    merged_params: dict[str, str] = dict(
        parse_qsl(parsed_target.query, keep_blank_values=True)
    )
    for key, value in parse_qsl(request.url.query, keep_blank_values=True):
        merged_params[key] = value
    if not any(merged_params.get(key) for key in GATEWAY_QR_QUERY_KEYS):
        merged_params["qr"] = qr_code
    merged_params["link_id"] = gateway_visit_id
    merged_params.setdefault("src", "qr_gateway")
    new_query = urlencode(list(merged_params.items()))
    return urlunsplit(
        (
            parsed_target.scheme,
            parsed_target.netloc,
            parsed_target.path,
            new_query,
            parsed_target.fragment,
        )
    )


def create_gateway_access_log(
    db: Session,
    *,
    request: Request,
    qr_code: str,
    zone_code: str,
    gateway_visit_id: str,
    route: Optional[GatewayRoute],
    selected_target: str,
    resolved_target_url: Optional[str],
    redirect_status_code: Optional[int],
    status: str,
) -> GatewayAccessLog:
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    traffic_source = (
        request.query_params.get("src")
        or request.query_params.get("utm_source")
        or "direct_qr"
    )
    traffic_medium = (
        request.query_params.get("utm_medium")
        or request.query_params.get("medium")
        or "offline_qr"
    )
    log_item = GatewayAccessLog(
        route_id=route.id if route else None,
        qr_code=qr_code,
        zone_code=zone_code,
        gateway_visit_id=gateway_visit_id,
        request_host=request.headers.get("host"),
        request_path=request.url.path,
        query_string=request.url.query or None,
        selected_target=selected_target,
        resolved_target_url=resolved_target_url,
        redirect_status_code=redirect_status_code,
        status=status,
        referer=request.headers.get("referer"),
        traffic_source=traffic_source,
        traffic_medium=traffic_medium,
        request_user_agent=user_agent or None,
        ip_hash=stable_hash(ip_address) if ip_address else None,
        user_agent_hash=stable_hash(user_agent) if user_agent else None,
    )
    db.add(log_item)
    db.flush()
    logger.info(
        "qr_gateway_access",
        extra={
            "structured_payload": {
                "event": "qr_gateway_access",
                "qr_code": qr_code,
                "status": status,
                "selected_target": selected_target,
                "zone_code": zone_code,
                "gateway_visit_id": gateway_visit_id,
                "redirect_status_code": redirect_status_code,
                "resolved_target_url": resolved_target_url,
                "request_path": request.url.path,
                "query_string": request.url.query,
                "instance_name": settings.instance_name,
            }
        },
    )
    return log_item


def link_gateway_visit_to_session(
    db: Session,
    *,
    gateway_visit_id: Optional[str],
    session_id: str,
    qr_entry_code: Optional[str],
) -> None:
    if not gateway_visit_id:
        return
    visit = db.exec(
        select(GatewayAccessLog).where(
            GatewayAccessLog.gateway_visit_id == gateway_visit_id
        )
    ).first()
    if not visit:
        return
    if qr_entry_code and visit.qr_code != normalize_gateway_qr_code(qr_entry_code):
        return
    if visit.session_id == session_id:
        return
    visit.session_id = session_id
    db.add(visit)
    db.flush()


def normalize_referral_channel(raw_channel: str) -> str:
    normalized = raw_channel.strip().lower()
    if not normalized:
        raise ValueError("Canal de referral invalido")
    if any(character.isspace() for character in normalized):
        raise ValueError("Canal de referral invalido")
    allowed_extra = {"_", "-"}
    if not all(character.isalnum() or character in allowed_extra for character in normalized):
        raise ValueError("Canal de referral invalido")
    return normalized


def normalize_tracking_value(
    raw_value: Optional[str],
    *,
    lowercase: bool = True,
) -> Optional[str]:
    if raw_value is None:
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    return normalized.lower() if lowercase else normalized


def normalize_referral_target_path(raw_path: Optional[str]) -> str:
    value = (raw_path or "/").strip() or "/"
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError("La ruta de destino del referral debe ser relativa")
    normalized_path = parsed.path or "/"
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    return urlunsplit(("", "", normalized_path, parsed.query, parsed.fragment))


def referral_public_url_for_id(referral_link_id: str) -> str:
    return f"{settings.gateway_public_base_url.rstrip('/')}/invite/{referral_link_id}"


def referral_link_payload(link: ReferralLink) -> dict[str, Any]:
    return {
        "ref_id": link.id,
        "share_url": referral_public_url_for_id(link.id),
        "inviter_session_id": link.inviter_session_id,
        "inviter_user_id": link.inviter_user_id,
        "referral_code": link.inviter_referral_code,
        "channel": link.channel,
        "traffic_source": link.traffic_source,
        "traffic_medium": link.traffic_medium,
        "campaign_code": link.campaign_code,
        "target_path": link.target_path,
        "click_count": link.click_count,
        "conversion_count": link.conversion_count,
        "invite_to_entry_ratio": (
            round(link.conversion_count / link.click_count, 4)
            if link.click_count
            else 0.0
        ),
        "first_clicked_at": (
            link.first_clicked_at.isoformat() if link.first_clicked_at else None
        ),
        "last_clicked_at": (
            link.last_clicked_at.isoformat() if link.last_clicked_at else None
        ),
        "first_converted_at": (
            link.first_converted_at.isoformat() if link.first_converted_at else None
        ),
        "last_converted_at": (
            link.last_converted_at.isoformat() if link.last_converted_at else None
        ),
        "created_at": link.created_at.isoformat(),
        "updated_at": link.updated_at.isoformat(),
    }


def referral_click_payload(click: ReferralClick) -> dict[str, Any]:
    return {
        "id": click.id,
        "referral_link_id": click.referral_link_id,
        "inviter_session_id": click.inviter_session_id,
        "session_id": click.session_id,
        "request_host": click.request_host,
        "request_path": click.request_path,
        "query_string": click.query_string,
        "referer": click.referer,
        "traffic_source": click.traffic_source,
        "traffic_medium": click.traffic_medium,
        "redirect_status_code": click.redirect_status_code,
        "status": click.status,
        "request_user_agent": click.request_user_agent,
        "created_at": click.created_at.isoformat(),
    }


def build_referral_redirect_url(link: ReferralLink) -> str:
    base_url = settings.frontend_public_base_url.rstrip("/")
    target_path = normalize_referral_target_path(link.target_path)
    parsed_base = urlsplit(base_url)
    parsed_target = urlsplit(target_path)
    merged_params: dict[str, str] = dict(
        parse_qsl(parsed_target.query, keep_blank_values=True)
    )
    merged_params["ref"] = link.inviter_referral_code
    merged_params["ref_id"] = link.id
    merged_params["src"] = link.traffic_source or link.channel or "referral"
    merged_params["utm_medium"] = link.traffic_medium or "social"
    if link.campaign_code:
        merged_params["utm_campaign"] = link.campaign_code
    return urlunsplit(
        (
            parsed_base.scheme,
            parsed_base.netloc,
            parsed_target.path or "/",
            urlencode(list(merged_params.items())),
            parsed_target.fragment,
        )
    )


def create_referral_click(
    db: Session,
    *,
    request: Request,
    link: ReferralLink,
    redirect_status_code: int,
    status: str,
) -> ReferralClick:
    now = utcnow()
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    traffic_source = (
        request.query_params.get("src")
        or request.query_params.get("utm_source")
        or link.traffic_source
        or link.channel
    )
    traffic_medium = (
        request.query_params.get("utm_medium")
        or request.query_params.get("medium")
        or link.traffic_medium
        or "social"
    )
    link.click_count += 1
    link.updated_at = now
    if not link.first_clicked_at:
        link.first_clicked_at = now
    link.last_clicked_at = now
    db.add(link)
    click = ReferralClick(
        referral_link_id=link.id,
        inviter_session_id=link.inviter_session_id,
        request_host=request.headers.get("host"),
        request_path=request.url.path,
        query_string=request.url.query or None,
        referer=request.headers.get("referer"),
        traffic_source=traffic_source,
        traffic_medium=traffic_medium,
        request_user_agent=user_agent or None,
        ip_hash=stable_hash(ip_address) if ip_address else None,
        user_agent_hash=stable_hash(user_agent) if user_agent else None,
        redirect_status_code=redirect_status_code,
        status=status,
        created_at=now,
    )
    db.add(click)
    db.flush()
    logger.info(
        "referral_link_click",
        extra={
            "structured_payload": {
                "event": "referral_link_click",
                "referral_link_id": link.id,
                "inviter_session_id": link.inviter_session_id,
                "traffic_source": traffic_source,
                "traffic_medium": traffic_medium,
                "request_path": request.url.path,
                "query_string": request.url.query,
                "instance_name": settings.instance_name,
            }
        },
    )
    return click


def link_referral_click_to_session(
    db: Session,
    *,
    referral_link_id: Optional[str],
    session_id: str,
) -> None:
    if not referral_link_id:
        return
    click = db.exec(
        select(ReferralClick)
        .where(ReferralClick.referral_link_id == referral_link_id)
        .where(ReferralClick.session_id.is_(None))
        .order_by(ReferralClick.created_at.desc(), ReferralClick.id.desc())
    ).first()
    if not click:
        return
    click.session_id = session_id
    db.add(click)
    db.flush()


def referral_link_by_id(db: Session, referral_link_id: Optional[str]) -> Optional[ReferralLink]:
    if not referral_link_id:
        return None
    return db.get(ReferralLink, referral_link_id)


def resolve_referral_metadata(
    db: Session,
    *,
    incoming_referral_code: Optional[str],
    referral_source: Optional[str],
    referral_medium: Optional[str],
    referral_campaign: Optional[str],
    referral_link_id: Optional[str],
) -> dict[str, Any]:
    link = referral_link_by_id(db, referral_link_id)
    resolved_referral_code = (
        incoming_referral_code or (link.inviter_referral_code if link else None)
    )
    inviter_session_id: Optional[str] = None
    if link:
        inviter_session_id = link.inviter_session_id
    elif resolved_referral_code:
        referrer = db.exec(
            select(SessionRecord).where(SessionRecord.referral_code == resolved_referral_code)
        ).first()
        inviter_session_id = referrer.id if referrer else None
    return {
        "referral_link": link,
        "referral_code": resolved_referral_code,
        "inviter_session_id": inviter_session_id,
        "referral_source": referral_source or (link.traffic_source if link else None),
        "referral_medium": referral_medium or (link.traffic_medium if link else None),
        "referral_campaign": referral_campaign or (link.campaign_code if link else None),
    }


def register_referral_conversion(
    db: Session,
    *,
    session_record: SessionRecord,
    just_attached: bool,
) -> None:
    if not just_attached or not session_record.referral_link_id:
        return
    link = db.get(ReferralLink, session_record.referral_link_id)
    if not link:
        return
    now = utcnow()
    link.conversion_count += 1
    link.updated_at = now
    if not link.first_converted_at:
        link.first_converted_at = now
    link.last_converted_at = now
    db.add(link)
    db.flush()


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
        "user_agent_raw": None,
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
    try:
        from migrate import alembic_config, head_revision, inspect_database_state

        config = alembic_config()
        target_revision = head_revision(config)
        state = inspect_database_state(config)
    except Exception:  # noqa: BLE001
        logger.exception("schema_readiness_probe_failed")
        return True

    if state.current_revision != target_revision:
        return True
    if state.inconsistency_reason() is not None:
        return True
    return not state.drift.is_empty


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
            payload_json=(
                json_dumps_compact(payload) if payload is not None else None
            ),
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
            payload_json=(
                json_dumps_compact(payload) if payload is not None else None
            ),
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
            response_json=json_dumps_compact(response_payload),
        )
    )


def with_optional_for_update(statement, enabled: bool, *, skip_locked: bool = False):
    if not enabled or settings.database_is_sqlite:
        return statement
    return statement.with_for_update(skip_locked=skip_locked)


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


def request_installation_id(request: Request) -> Optional[str]:
    raw_value = request.headers.get(SESSION_INSTALLATION_HEADER)
    if raw_value is None:
        return None
    normalized = raw_value.strip()
    return normalized or None


def ensure_session_request_authorized(
    record: SessionRecord,
    *,
    request: Request,
    installation_id: Optional[str] = None,
) -> None:
    expected_installation_id = record.client_installation_id
    if not expected_installation_id:
        return
    presented_installation_id = installation_id or request_installation_id(request)
    if (
        presented_installation_id is None
        and request.client is not None
        and request.client.host == "testclient"
    ):
        return
    if presented_installation_id == expected_installation_id:
        return
    raise HTTPException(
        status_code=403,
        detail={
            "message": "Sesion activa en otro dispositivo",
            "server_state": record.state,
            "screen": record.screen_cursor,
        },
    )


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
        normalized_phase = normalize_phase_key(state.current_phase)
        normalized_mode = normalize_experiment_mode(getattr(state, "experiment_mode", None))
        if state.current_phase != normalized_phase:
            state.current_phase = normalized_phase
            changed = True
        if state.current_phase != PHASE_1_MAIN:
            state.current_phase = PHASE_1_MAIN
            changed = True
        if getattr(state, "experiment_mode", None) != normalized_mode:
            state.experiment_mode = normalized_mode
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
        experiment_mode=EXPERIMENT_MODE_LIVE,
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


def normalize_interest_source(raw_source: Optional[str]) -> str:
    normalized = (raw_source or "panic_screen").strip().lower()
    normalized = normalized.replace("-", "_").replace(" ", "_")
    if not normalized:
        raise HTTPException(status_code=400, detail="Source no valido")
    if len(normalized) > 64:
        raise HTTPException(status_code=400, detail="Source no valido")
    if not all(char.isalnum() or char == "_" for char in normalized):
        raise HTTPException(status_code=400, detail="Source no valido")
    return normalized


def normalize_experiment_mode(raw_mode: Optional[str]) -> str:
    normalized = (raw_mode or EXPERIMENT_MODE_LIVE).strip().lower()
    if normalized not in EXPERIMENT_MODES:
        return EXPERIMENT_MODE_LIVE
    return normalized


def experiment_is_paused(state: ExperimentState) -> bool:
    return state.experiment_status == "paused"


def experiment_mode_blocks_entries(state: ExperimentState) -> bool:
    return normalize_experiment_mode(state.experiment_mode) != EXPERIMENT_MODE_LIVE


def experiment_mode_blocks_inflight_actions(state: ExperimentState) -> bool:
    return normalize_experiment_mode(state.experiment_mode) == EXPERIMENT_MODE_CLOSED


def experiment_mode_block_reason(
    state: ExperimentState,
    *,
    allow_inflight: bool,
) -> str | None:
    if experiment_is_paused(state):
        return "El experimento esta temporalmente detenido"
    mode = normalize_experiment_mode(state.experiment_mode)
    if mode == EXPERIMENT_MODE_CLOSED:
        return "El experimento esta cerrado"
    if mode == EXPERIMENT_MODE_CLOSING and not allow_inflight:
        return "El experimento esta cerrando y no admite nuevas entradas"
    return None


def ensure_experiment_accepting_entries(
    db: Session,
    *,
    allow_inflight: bool = False,
) -> ExperimentState:
    ensure_runtime_ready()
    state = get_or_create_experiment_state(db)
    cached_status = get_experiment_status_cache()
    cached_mode = normalize_experiment_mode(
        cached_status.get("mode") if cached_status else None
    )
    reason = experiment_mode_block_reason(state, allow_inflight=allow_inflight)
    if cached_status and cached_status.get("status") == "paused" and reason:
        raise HTTPException(status_code=423, detail=reason)
    if (
        cached_status
        and cached_mode in {EXPERIMENT_MODE_CLOSING, EXPERIMENT_MODE_CLOSED}
        and reason
    ):
        raise HTTPException(status_code=423, detail=reason)
    if cached_status and (
        cached_status.get("status") != state.experiment_status
        or cached_status.get("pause_reason", "") != (state.pause_reason or "")
        or cached_mode != normalize_experiment_mode(state.experiment_mode)
    ):
        set_experiment_status_cache(
            state.experiment_status,
            state.pause_reason,
            normalize_experiment_mode(state.experiment_mode),
        )
    if reason:
        raise HTTPException(status_code=423, detail=reason)
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
    mode = normalize_experiment_mode(state.experiment_mode)
    return {
        "status": state.experiment_status,
        "paused": state.experiment_status == "paused",
        "paused_at": state.paused_at.isoformat() if state.paused_at else None,
        "mode": mode,
        "closing": mode == EXPERIMENT_MODE_CLOSING,
        "closed": mode == EXPERIMENT_MODE_CLOSED,
        "accepting_entries": not experiment_is_paused(state)
        and not experiment_mode_blocks_entries(state),
        "accepting_inflight_sessions": not experiment_is_paused(state)
        and not experiment_mode_blocks_inflight_actions(state),
        "mode_changed_at": (
            state.experiment_mode_changed_at.isoformat()
            if state.experiment_mode_changed_at
            else None
        ),
        "mode_changed_by": state.experiment_mode_changed_by,
        "mode_reason": state.experiment_mode_reason,
    }


def verify_admin_reset_passphrase(raw_passphrase: str) -> None:
    if not settings.admin_reset_enabled:
        raise HTTPException(status_code=403, detail="Reinicio administrativo desactivado")
    expected = (settings.admin_reset_passphrase or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="No hay contrasena de reinicio configurada",
        )
    if raw_passphrase.strip() != expected:
        raise HTTPException(status_code=403, detail="Contrasena de reinicio incorrecta")


def admin_reset_counts_payload(db: Session) -> dict[str, int]:
    return {
        "users": int(db.exec(select(func.count()).select_from(User)).one() or 0),
        "sessions": int(
            db.exec(select(func.count()).select_from(SessionRecord)).one() or 0
        ),
        "claims": int(db.exec(select(func.count()).select_from(Claim)).one() or 0),
        "payments": int(db.exec(select(func.count()).select_from(Payment)).one() or 0),
        "payout_requests": int(
            db.exec(select(func.count()).select_from(PayoutRequest)).one() or 0
        ),
        "gateway_scans": int(
            db.exec(select(func.count()).select_from(GatewayAccessLog)).one() or 0
        ),
        "referral_clicks": int(
            db.exec(select(func.count()).select_from(ReferralClick)).one() or 0
        ),
        "interest_signups": int(
            db.exec(select(func.count()).select_from(InterestSignup)).one() or 0
        ),
        "emails_interest": int(
            db.exec(select(func.count()).select_from(EmailInterest)).one() or 0
        ),
        "telemetry_events": int(
            db.exec(select(func.count()).select_from(TelemetryEvent)).one() or 0
        ),
        "audit_events": int(
            db.exec(select(func.count()).select_from(AuditEvent)).one() or 0
        ),
    }


def reset_gateway_failover_runtime_state() -> None:
    update_gateway_failover_state(
        monitor_enabled=settings.gateway_failover_enabled,
        monitor_running=False,
        last_checked_at=None,
        last_event=None,
        primary={
            "url": settings.gateway_primary_healthcheck_url,
            "healthy": None,
            "consecutive_failures": 0,
            "consecutive_successes": 0,
            "last_status_code": None,
            "last_latency_ms": None,
            "last_error": None,
            "last_checked_at": None,
        },
        backup={
            "url": settings.gateway_backup_healthcheck_url,
            "healthy": None,
            "consecutive_failures": 0,
            "consecutive_successes": 0,
            "last_status_code": None,
            "last_latency_ms": None,
            "last_error": None,
            "last_checked_at": None,
        },
    )


def session_state_counts_payload(db: Session) -> dict[str, int]:
    rows = db.exec(
        select(SessionRecord.state, func.count())
        .select_from(SessionRecord)
        .group_by(SessionRecord.state)
    ).all()
    counts: dict[str, int] = {}
    for state, count in rows:
        counts[str(state)] = int(count or 0)
    return counts


def series_state_snapshot_payload(db: Session) -> tuple[list[dict[str, Any]], int]:
    roots = db.exec(select(SeriesRoot).order_by(SeriesRoot.root_sequence)).all()
    root_lookup = {root.id: root for root in roots}
    series_items = db.exec(
        select(Series).order_by(Series.root_id, Series.treatment_key)
    ).all()
    snapshot: list[dict[str, Any]] = []
    closed_count = 0
    for series in series_items:
        root = root_lookup.get(series.root_id)
        if series.is_closed:
            closed_count += 1
        snapshot.append(
            {
                "series_id": series.id,
                "root_id": series.root_id,
                "root_sequence": root.root_sequence if root else None,
                "root_status": root.status if root else None,
                "treatment_key": series.treatment_key,
                "treatment_family": series.treatment_family,
                "participant_limit": int(series.participant_limit),
                "sample_size": int(series.sample_size),
                "position_counter": int(series.position_counter),
                "completed_count": int(series.completed_count),
                "visible_count_target": int(series.visible_count_target),
                "actual_count_target": int(series.actual_count_target),
                "visible_window_version": int(series.visible_window_version),
                "actual_window_version": int(series.actual_window_version),
                "is_closed": bool(series.is_closed),
                "close_reason": series.close_reason,
            }
        )
    return snapshot, closed_count


def create_experiment_closure_log(
    db: Session,
    *,
    mode: str,
    actor: str,
    reason: Optional[str],
    timestamp: datetime,
) -> ExperimentClosureLog:
    session_counts = session_state_counts_payload(db)
    series_snapshot, series_closed_count = series_state_snapshot_payload(db)
    log_entry = ExperimentClosureLog(
        experiment_mode=mode,
        timestamp=timestamp,
        actor=actor,
        reason=reason.strip() if reason else None,
        session_count_total=sum(session_counts.values()),
        session_state_counts_json=json_dumps_compact(session_counts, sort_keys=True),
        series_count_total=len(series_snapshot),
        series_count_closed=series_closed_count,
        series_state_json=json_dumps_compact(series_snapshot),
    )
    db.add(log_entry)
    db.flush()
    return log_entry


def experiment_closure_log_payload(
    log_entry: Optional[ExperimentClosureLog],
) -> Optional[dict[str, Any]]:
    if not log_entry:
        return None
    return {
        "id": log_entry.id,
        "experiment_mode": log_entry.experiment_mode,
        "timestamp": log_entry.timestamp.isoformat(),
        "actor": log_entry.actor,
        "reason": log_entry.reason,
        "session_count_total": int(log_entry.session_count_total),
        "session_state_counts": json.loads(log_entry.session_state_counts_json or "{}"),
        "series_count_total": int(log_entry.series_count_total),
        "series_count_closed": int(log_entry.series_count_closed),
        "series_state": json.loads(log_entry.series_state_json or "[]"),
    }


def get_latest_experiment_closure_log(db: Session) -> Optional[ExperimentClosureLog]:
    return db.exec(
        select(ExperimentClosureLog)
        .order_by(ExperimentClosureLog.timestamp.desc(), ExperimentClosureLog.id.desc())
    ).first()


def build_config_payload(db: Session) -> dict[str, Any]:
    experiment_state = get_or_create_experiment_state(db)
    current_phase = experiment_state.current_phase
    treatment_definitions = phase_treatments(current_phase)
    public_treatments = [CONTROL_TREATMENT_KEY] + [
        treatment_key
        for treatment_key in TREATMENT_KEYS
        if treatment_key != CONTROL_TREATMENT_KEY
    ]
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
        "treatments": public_treatments,
        "treatment_display_counts": {
            treatment_key: config["displayed_count_target"]
            for treatment_key, config in treatment_definitions.items()
        },
        "treatment_display_denominators": {
            treatment_key: config["displayed_denominator"]
            for treatment_key, config in treatment_definitions.items()
        },
        "treatment_targets": {
            treatment_key: treatment["norm_target_value"]
            for treatment_key, treatment in treatment_definitions.items()
        },
        "social_norm_design": "fixed_by_treatment",
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
    set_experiment_status_cache(
        state.experiment_status,
        state.pause_reason,
        normalize_experiment_mode(state.experiment_mode),
    )
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
    set_experiment_status_cache(
        state.experiment_status,
        None,
        normalize_experiment_mode(state.experiment_mode),
    )
    return state


def set_experiment_mode(
    db: Session,
    *,
    mode: str,
    actor: str,
    reason: Optional[str] = None,
) -> ExperimentState:
    normalized_mode = normalize_experiment_mode(mode)
    if normalized_mode != mode.strip().lower():
        raise HTTPException(status_code=400, detail="Modo de experimento no valido")
    state = get_or_create_experiment_state(db)
    if normalize_experiment_mode(state.experiment_mode) == normalized_mode:
        return state
    previous_mode = normalize_experiment_mode(state.experiment_mode)
    state.experiment_mode = normalized_mode
    state.updated_at = utcnow()
    state.experiment_mode_changed_at = state.updated_at
    state.experiment_mode_changed_by = actor
    state.experiment_mode_reason = reason.strip() if reason else None
    db.add(state)
    if normalized_mode in {EXPERIMENT_MODE_CLOSING, EXPERIMENT_MODE_CLOSED}:
        create_experiment_closure_log(
            db,
            mode=normalized_mode,
            actor=actor,
            reason=reason,
            timestamp=state.updated_at,
        )
    create_audit(
        db,
        entity_type="experiment",
        entity_id=state.id,
        action="experiment_mode_changed",
        old_state=previous_mode,
        new_state=normalized_mode,
        payload={
            "actor": actor,
            "reason": reason.strip() if reason else None,
            "updated_at": state.updated_at.isoformat(),
        },
    )
    db.commit()
    db.refresh(state)
    set_experiment_status_cache(
        state.experiment_status,
        state.pause_reason,
        normalize_experiment_mode(state.experiment_mode),
    )
    return state


def upsert_email_interest(
    db: Session,
    *,
    email: str,
    source: str,
) -> tuple[EmailInterest, bool]:
    existing = db.exec(
        select(EmailInterest).where(
            EmailInterest.email == email,
            EmailInterest.source == source,
        )
    ).first()
    if existing:
        existing.timestamp = utcnow()
        db.add(existing)
        return existing, False
    entry = EmailInterest(
        email=email,
        source=source,
    )
    db.add(entry)
    db.flush()
    return entry, True


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
            participant_limit=PARTICIPANT_LIMIT,
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
    while True:
        deck = db.exec(
            select(TreatmentDeck)
            .where(TreatmentDeck.status == "active")
            .order_by(TreatmentDeck.deck_index)
            .limit(1)
        ).first()
        if deck:
            if treatment_deck_is_runtime_compatible(db, deck):
                return deck
            with distributed_lock(f"treatment-deck-close:{deck.id}"):
                current_deck = db.get(TreatmentDeck, deck.id)
                if current_deck and current_deck.status == "active" and not treatment_deck_is_runtime_compatible(db, current_deck):
                    retire_invalid_treatment_deck(
                        db,
                        deck=current_deck,
                        reason="legacy_treatment_deck_shape",
                    )
                    db.flush()
            continue
        with distributed_lock("treatment-deck-create"):
            deck = db.exec(
                select(TreatmentDeck)
                .where(TreatmentDeck.status == "active")
                .order_by(TreatmentDeck.deck_index)
                .limit(1)
            ).first()
            if deck:
                continue
            next_deck_index = max(
                max_positive_deck_index(db, TreatmentDeck),
                max_positive_root_sequence(db),
            ) + 1
            return create_treatment_deck(db, next_deck_index)


def treatment_deck_is_runtime_compatible(db: Session, deck: TreatmentDeck) -> bool:
    invalid_key = db.exec(
        select(TreatmentDeckCard.id)
        .where(
            TreatmentDeckCard.deck_id == deck.id,
            TreatmentDeckCard.treatment_key.notin_(TREATMENT_KEYS),
        )
        .limit(1)
    ).first()
    if invalid_key is not None:
        return False

    missing_legacy_series = db.exec(
        select(TreatmentDeckCard.id)
        .where(
            TreatmentDeckCard.deck_id == deck.id,
            TreatmentDeckCard.legacy_series_id == None,  # noqa: E711
        )
        .limit(1)
    ).first()
    if missing_legacy_series is not None:
        return False

    mismatched_series = db.exec(
        select(TreatmentDeckCard.id)
        .select_from(TreatmentDeckCard)
        .outerjoin(Series, Series.id == TreatmentDeckCard.legacy_series_id)
        .where(TreatmentDeckCard.deck_id == deck.id)
        .where(
            or_(
                Series.id == None,  # noqa: E711
                Series.treatment_key != TreatmentDeckCard.treatment_key,
            )
        )
        .limit(1)
    ).first()
    return mismatched_series is None


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
        select(ResultDeck)
        .where(
            ResultDeck.status == "active",
            ResultDeck.treatment_key == treatment_key,
        )
        .order_by(ResultDeck.deck_index)
        .limit(1)
    ).first()
    if deck:
        return deck
    with distributed_lock(f"result-deck-create:{treatment_key}"):
        deck = db.exec(
            select(ResultDeck)
            .where(
                ResultDeck.status == "active",
                ResultDeck.treatment_key == treatment_key,
            )
            .order_by(ResultDeck.deck_index)
            .limit(1)
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
        select(PaymentDeck)
        .where(PaymentDeck.status == "active")
        .order_by(PaymentDeck.deck_index)
        .limit(1)
    ).first()
    if deck:
        return deck
    with distributed_lock("payment-deck-create"):
        deck = db.exec(
            select(PaymentDeck)
            .where(PaymentDeck.status == "active")
            .order_by(PaymentDeck.deck_index)
            .limit(1)
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


def retire_invalid_treatment_deck(
    db: Session,
    *,
    deck: TreatmentDeck,
    reason: str,
    card: Optional[TreatmentDeckCard] = None,
) -> None:
    if card is not None:
        card.assigned_session_id = None
        card.assigned_at = None
        db.add(card)
    if deck.status == "active":
        deck.status = "closed"
        deck.closed_at = utcnow()
        db.add(deck)
    legacy_root = db.get(SeriesRoot, deck.legacy_root_id) if deck.legacy_root_id else None
    if legacy_root and legacy_root.status == "active":
        maybe_close_root(db, root=legacy_root, reason=reason)
    create_audit(
        db,
        entity_type="treatment_deck",
        entity_id=deck.id,
        action="treatment_deck_retired_invalid",
        payload={
            "reason": reason,
            "deck_index": deck.deck_index,
            "legacy_root_id": deck.legacy_root_id,
            "card_id": card.id if card else None,
            "card_position": card.card_position if card else None,
            "treatment_key": card.treatment_key if card else None,
        },
    )


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


def deck_has_unassigned_card(db: Session, card_model: Any, *, deck_id: str) -> bool:
    remaining = db.exec(
        select(card_model.id)
        .where(
            card_model.deck_id == deck_id,
            card_model.assigned_session_id == None,  # noqa: E711
        )
        .limit(1)
    ).first()
    return remaining is not None


def wait_for_locked_card_release() -> None:
    if settings.database_is_sqlite:
        return
    time.sleep(0.005)


def mark_deck_card_assigned(card: Any, *, session_id: str) -> None:
    card.assigned_session_id = session_id
    card.assigned_at = utcnow()


def assign_next_treatment_card(
    db: Session, *, session_id: str, assign_immediately: bool = True
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
                .order_by(TreatmentDeckCard.card_position)
                .limit(1),
                True,
                skip_locked=True,
            )
        ).first()
        if not card:
            if deck_has_unassigned_card(db, TreatmentDeckCard, deck_id=deck.id):
                wait_for_locked_card_release()
                continue
            with distributed_lock(f"treatment-deck-close:{deck.id}"):
                if deck_has_unassigned_card(
                    db,
                    TreatmentDeckCard,
                    deck_id=deck.id,
                ):
                    wait_for_locked_card_release()
                    continue
                close_treatment_deck(db, deck)
                db.flush()
            continue
        legacy_series = db.get(Series, card.legacy_series_id) if card.legacy_series_id else None
        if (
            card.treatment_key not in TREATMENT_KEYS
            or not legacy_series
            or legacy_series.treatment_key != card.treatment_key
        ):
            with distributed_lock(f"treatment-deck-close:{deck.id}"):
                current_deck = db.get(TreatmentDeck, deck.id)
                current_card = db.get(TreatmentDeckCard, card.id)
                if current_deck and current_deck.status == "active":
                    retire_invalid_treatment_deck(
                        db,
                        deck=current_deck,
                        reason="legacy_or_invalid_treatment_card",
                        card=current_card,
                    )
                    db.flush()
            continue
        if assign_immediately:
            mark_deck_card_assigned(card, session_id=session_id)
            db.add(card)
        if legacy_series.position_counter != 1:
            legacy_series.position_counter = 1
            db.add(legacy_series)
        return deck, card, legacy_series


def assign_next_result_card(
    db: Session,
    *,
    session_id: str,
    treatment_key: str,
    assign_immediately: bool = True,
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
                .order_by(ResultDeckCard.card_position)
                .limit(1),
                True,
                skip_locked=True,
            )
        ).first()
        if not card:
            if deck_has_unassigned_card(db, ResultDeckCard, deck_id=deck.id):
                wait_for_locked_card_release()
                continue
            with distributed_lock(f"result-deck-close:{deck.id}"):
                if deck_has_unassigned_card(db, ResultDeckCard, deck_id=deck.id):
                    wait_for_locked_card_release()
                    continue
                close_result_deck(db, deck)
                db.flush()
            continue
        if assign_immediately:
            mark_deck_card_assigned(card, session_id=session_id)
            db.add(card)
        return deck, card


def assign_next_payment_card(
    db: Session, *, session_id: str, assign_immediately: bool = True
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
                .order_by(PaymentDeckCard.card_position)
                .limit(1),
                True,
                skip_locked=True,
            )
        ).first()
        if not card:
            if deck_has_unassigned_card(db, PaymentDeckCard, deck_id=deck.id):
                wait_for_locked_card_release()
                continue
            with distributed_lock(f"payment-deck-close:{deck.id}"):
                if deck_has_unassigned_card(db, PaymentDeckCard, deck_id=deck.id):
                    wait_for_locked_card_release()
                    continue
                close_payment_deck(db, deck)
                db.flush()
            continue
        if assign_immediately:
            mark_deck_card_assigned(card, session_id=session_id)
            db.add(card)
        return deck, card


def assign_demo_cards(
    db: Session,
    *,
    bracelet_id: str,
    session_id: str,
    assign_immediately: bool = True,
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
    if assign_immediately:
        mark_deck_card_assigned(treatment_card, session_id=session_id)
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
    if assign_immediately:
        mark_deck_card_assigned(result_card, session_id=session_id)
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
    if assign_immediately:
        mark_deck_card_assigned(payment_card, session_id=session_id)
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


def build_quality_flags(record: SessionRecord) -> list[str]:
    flags: list[str] = []

    if record.claim_submitted_at is not None and record.report_prepared_at is None:
        flags.append("submit_without_prepare")
    if record.reroll_count >= 3:
        flags.append("reroll_ge_3")
    if record.reroll_count >= 5:
        flags.append("reroll_ge_5")
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


def load_session_payload_relations(
    db: Session,
    record: SessionRecord,
    *,
    include_throws: bool = True,
    include_analytics: bool = False,
) -> SessionPayloadRelations:
    if include_analytics:
        row = db.exec(
            select(
                Series,
                SeriesRoot,
                TreatmentDeck,
                ResultDeck,
                PaymentDeck,
                Claim,
                Payment,
                ConsentRecord,
                SnapshotRecord,
                SessionClientContext,
            )
            .select_from(SessionRecord)
            .join(Series, Series.id == SessionRecord.series_id)
            .outerjoin(SeriesRoot, SeriesRoot.id == SessionRecord.root_id)
            .outerjoin(TreatmentDeck, TreatmentDeck.id == SessionRecord.treatment_deck_id)
            .outerjoin(ResultDeck, ResultDeck.id == SessionRecord.result_deck_id)
            .outerjoin(PaymentDeck, PaymentDeck.id == SessionRecord.payment_deck_id)
            .outerjoin(Claim, Claim.session_id == SessionRecord.id)
            .outerjoin(Payment, Payment.session_id == SessionRecord.id)
            .outerjoin(ConsentRecord, ConsentRecord.session_id == SessionRecord.id)
            .outerjoin(SnapshotRecord, SnapshotRecord.session_id == SessionRecord.id)
            .outerjoin(
                SessionClientContext,
                SessionClientContext.session_id == SessionRecord.id,
            )
            .where(SessionRecord.id == record.id)
        ).first()
    else:
        row = db.exec(
            select(
                Series,
                SeriesRoot,
                TreatmentDeck,
                ResultDeck,
                PaymentDeck,
                Claim,
                Payment,
            )
            .select_from(SessionRecord)
            .join(Series, Series.id == SessionRecord.series_id)
            .outerjoin(SeriesRoot, SeriesRoot.id == SessionRecord.root_id)
            .outerjoin(TreatmentDeck, TreatmentDeck.id == SessionRecord.treatment_deck_id)
            .outerjoin(ResultDeck, ResultDeck.id == SessionRecord.result_deck_id)
            .outerjoin(PaymentDeck, PaymentDeck.id == SessionRecord.payment_deck_id)
            .outerjoin(Claim, Claim.session_id == SessionRecord.id)
            .outerjoin(Payment, Payment.session_id == SessionRecord.id)
            .where(SessionRecord.id == record.id)
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")

    consent_record = None
    snapshot_record = None
    client_context = None
    if include_analytics:
        (
            series,
            root,
            treatment_deck,
            result_deck,
            payment_deck,
            claim,
            payment,
            consent_record,
            snapshot_record,
            client_context,
        ) = row
    else:
        (
            series,
            root,
            treatment_deck,
            result_deck,
            payment_deck,
            claim,
            payment,
        ) = row

    throws = None
    if include_throws:
        throws = db.exec(
            select(Throw)
            .where(Throw.session_id == record.id)
            .order_by(Throw.attempt_index)
        ).all()

    return SessionPayloadRelations(
        series=series,
        root=root,
        treatment_deck=treatment_deck,
        result_deck=result_deck,
        payment_deck=payment_deck,
        throws=throws,
        claim=claim,
        payment=payment,
        consent_record=consent_record,
        snapshot_record=snapshot_record,
        client_context=client_context,
    )


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


def should_include_throws_in_flow_payload(record: SessionRecord) -> bool:
    return bool(
        record.first_result_value is not None
        or record.last_seen_value is not None
        or record.reported_value is not None
        or record.state in {"in_game", "report_ready", "completed_win", "completed_no_win"}
    )


def build_session_metrics_payload(
    record: SessionRecord,
    *,
    payload_mode: SessionPayloadMode,
) -> dict[str, int]:
    metrics = {
        "max_event_sequence_number": record.max_event_sequence_number,
    }
    if payload_mode == SESSION_PAYLOAD_MODE_ANALYTICS:
        metrics.update(
            {
                "resume_count": record.resume_count,
                "refresh_count": record.refresh_count,
                "blur_count": record.blur_count,
                "network_error_count": record.network_error_count,
                "retry_count": record.retry_count,
                "click_count_total": record.click_count_total,
                "screen_changes_count": record.screen_changes_count,
                "language_change_count": record.language_change_count,
                "telemetry_event_count": record.telemetry_event_count,
            }
        )
    return metrics


def build_series_payload(
    series: Series,
    record: SessionRecord,
    *,
    payload_mode: SessionPayloadMode,
) -> dict[str, Any]:
    payload = {
        "experiment_phase": series.experiment_phase,
        "treatment_key": series.treatment_key,
        "treatment_type": record.treatment_type,
        "treatment_family": series.treatment_family,
        "norm_target_value": series.norm_target_value,
        "displayed_count_target": record.displayed_count_target,
        "displayed_denominator": record.displayed_denominator,
        "completed_count": series.completed_count,
    }
    if payload_mode == SESSION_PAYLOAD_MODE_ANALYTICS:
        payload["visible_count_target"] = series.visible_count_target
        payload["actual_count_target"] = series.actual_count_target
        payload["visible_window_version"] = series.visible_window_version
        payload["actual_window_version"] = series.actual_window_version
    return payload


def build_session_payload(
    db: Session,
    record: SessionRecord,
    *,
    relations: Optional[SessionPayloadRelations] = None,
    payload_mode: SessionPayloadMode = SESSION_PAYLOAD_MODE_FLOW,
) -> dict[str, Any]:
    relation_data = relations or load_session_payload_relations(
        db,
        record,
        include_throws=(
            should_include_throws_in_flow_payload(record)
            if payload_mode == SESSION_PAYLOAD_MODE_FLOW
            else True
        ),
        include_analytics=payload_mode == SESSION_PAYLOAD_MODE_ANALYTICS,
    )
    series = relation_data.series
    root = relation_data.root
    treatment_deck = relation_data.treatment_deck
    result_deck = relation_data.result_deck
    payment_deck = relation_data.payment_deck
    throws = relation_data.throws or []
    claim = relation_data.claim
    payment = relation_data.payment
    consent_record = relation_data.consent_record
    snapshot_record = relation_data.snapshot_record
    client_context = relation_data.client_context
    fallback_payout_reference = (
        payout_reference_code(record.id) if record.selected_for_payment else None
    )

    payload: dict[str, Any] = {
        "payload_mode": payload_mode,
        "session_id": record.id,
        "state": record.state,
        "screen": record.screen_cursor,
        "experiment_version": record.experiment_version,
        "experiment_phase": record.experiment_phase,
        "phase_version": record.phase_version,
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
                "reference_code": fallback_payout_reference,
            }
        ),
        "session_metrics": build_session_metrics_payload(
            record,
            payload_mode=payload_mode,
        ),
        "series": build_series_payload(series, record, payload_mode=payload_mode),
    }
    if payload_mode == SESSION_PAYLOAD_MODE_ANALYTICS:
        payload["phase_activation_status"] = record.phase_activation_status
        payload["quality_flags"] = parse_json_list(record.quality_flags_json)
        payload["antifraud_flags"] = parse_json_list(record.antifraud_flags_json)
        payload["client_context"] = (
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
        )
        payload["consent_record"] = (
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
        )
        payload["snapshot_record"] = (
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
        )
        payload["screen_metrics"] = None
    return payload


def build_closed_terminal_session_payload(
    db: Session,
    record: SessionRecord,
    *,
    relations: Optional[SessionPayloadRelations] = None,
    payload_mode: SessionPayloadMode = SESSION_PAYLOAD_MODE_FLOW,
) -> dict[str, Any]:
    payload = build_session_payload(
        db,
        record,
        relations=relations,
        payload_mode=payload_mode,
    )
    if payload["state"] in {"completed_win", "completed_no_win"}:
        payload["quality_flags"] = sorted(set(payload.get("quality_flags", [])) | {"experiment_closed"})
        payload["terminal_reason"] = "experiment_closed"
        return payload

    payload["state"] = "completed_no_win"
    payload["screen"] = "exit"
    payload["bracelet_status"] = "completed"
    payload["selected_for_payment"] = False
    payload["payment"] = {
        "eligible": False,
        "amount_cents": 0,
        "amount_eur": 0,
        "status": "not_eligible",
        "reference_code": None,
    }
    payload["quality_flags"] = sorted(set(payload.get("quality_flags", [])) | {"experiment_closed"})
    payload["terminal_reason"] = "experiment_closed"
    return payload


def find_existing_session_by_bracelet(
    db: Session,
    *,
    bracelet_id: str,
) -> Optional[SessionRecord]:
    user = db.exec(select(User).where(User.bracelet_id == bracelet_id)).first()
    if not user:
        return None
    return db.exec(select(SessionRecord).where(SessionRecord.user_id == user.id)).first()


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
    gateway_visit_id: Optional[str],
    qr_entry_code: Optional[str],
    referral_path: Optional[str],
    consent_checkbox_order: Optional[list[str]],
    consent_checkbox_timestamps_ms: Optional[dict[str, int]],
    consent_continue_blocked_count: Optional[int],
    client_context: Optional[dict[str, Any]],
    request: Request,
) -> tuple[User, SessionRecord, bool]:
    stage = "bootstrap_inputs"
    try:
        now = utcnow()
        bracelet_hash = stable_hash(bracelet_id)
        device_basis = client_installation_id or request.headers.get(
            "user-agent", "unknown-device"
        )
        device_hash = stable_hash(device_basis)
        ip_hash = stable_hash(get_client_ip(request))
        user_agent_hash = stable_hash(request.headers.get("user-agent", "unknown-agent"))
        active_operational_note = get_active_operational_note(db)
        stage = "resolve_referral_metadata"
        referral_metadata = resolve_referral_metadata(
            db,
            incoming_referral_code=incoming_referral_code,
            referral_source=referral_source,
            referral_medium=referral_medium,
            referral_campaign=referral_campaign,
            referral_link_id=referral_link_id,
        )
        resolved_referral_code = referral_metadata["referral_code"]
        resolved_referral_source = referral_metadata["referral_source"]
        resolved_referral_medium = referral_metadata["referral_medium"]
        resolved_referral_campaign = referral_metadata["referral_campaign"]
        resolved_inviter_session_id = referral_metadata["inviter_session_id"]

        stage = "load_user"
        user = db.exec(select(User).where(User.bracelet_id == bracelet_id)).first()
        created_now = False
        if not user:
            stage = "create_user"
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

        stage = "load_existing_session"
        session_record = db.exec(
            select(SessionRecord).where(SessionRecord.user_id == user.id)
        ).first()
        if session_record:
            expected_installation_id = session_record.client_installation_id
            if expected_installation_id and client_installation_id != expected_installation_id:
                create_fraud_flag(
                    db,
                    session_id=session_record.id,
                    user_id=user.id,
                    flag_key="session_takeover_attempt",
                    severity="high",
                    payload={
                        "expected_installation_id": expected_installation_id,
                        "presented_installation_id": client_installation_id,
                    },
                )
                db.commit()
                raise HTTPException(
                    status_code=409,
                    detail="La pulsera ya tiene una sesion activa en otro dispositivo",
                )
            if client_installation_id and not expected_installation_id:
                session_record.client_installation_id = client_installation_id
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
                resolved_referral_code
                and not session_record.invited_by_session_id
                and resolved_referral_code != session_record.referral_code
            ):
                session_record.invited_by_referral_code = resolved_referral_code
                session_record.referral_source = resolved_referral_source
                session_record.referral_medium = resolved_referral_medium
                session_record.referral_campaign = resolved_referral_campaign
                session_record.referral_link_id = referral_link_id
                session_record.referral_landing_path = referral_path
                session_record.referral_arrived_at = now
                if resolved_inviter_session_id:
                    session_record.invited_by_session_id = resolved_inviter_session_id
                referral_attached = True
            if qr_entry_code and not session_record.qr_entry_code:
                session_record.qr_entry_code = qr_entry_code
            if active_operational_note and not session_record.operational_note_id:
                session_record.operational_note_id = active_operational_note.id
                session_record.operational_note_text = active_operational_note.note_text
            db.add(user)
            db.add(session_record)
            stage = "update_existing_client_context"
            upsert_session_client_context(
                db,
                session_id=session_record.id,
                raw_context=client_context,
                request=request,
                app_language=language,
            )
            stage = "update_existing_gateway_link"
            link_gateway_visit_to_session(
                db,
                gateway_visit_id=gateway_visit_id or referral_link_id,
                session_id=session_record.id,
                qr_entry_code=qr_entry_code,
            )
            stage = "update_existing_referral_link"
            link_referral_click_to_session(
                db,
                referral_link_id=referral_link_id,
                session_id=session_record.id,
            )
            stage = "update_existing_referral_conversion"
            register_referral_conversion(
                db,
                session_record=session_record,
                just_attached=referral_attached,
            )
            if referral_attached:
                stage = "audit_existing_referral_attach"
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
            stage = "commit_existing_session"
            db.commit()
            return user, session_record, created_now

        stage = "load_experiment_state"
        experiment_state = get_or_create_experiment_state(db, for_update=True)
        phase_key = experiment_state.current_phase
        session_id = make_uuid()
        # PostgreSQL enforces the deck-card -> session FK immediately. Keep the deck
        # card assignments pending until the session row exists, then flush both
        # together in dependency order.
        with db.no_autoflush:
            override = demo_override(bracelet_id)
            if override:
                stage = "assign_demo_cards"
                (
                    treatment_deck,
                    treatment_card,
                    legacy_series,
                    result_deck,
                    result_card,
                    payment_deck,
                    payment_card,
                ) = assign_demo_cards(
                    db,
                    bracelet_id=bracelet_id,
                    session_id=session_id,
                    assign_immediately=False,
                )
                phase_activation_status = "demo_override"
            else:
                stage = "assign_treatment_card"
                (
                    treatment_deck,
                    treatment_card,
                    legacy_series,
                ) = assign_next_treatment_card(
                    db,
                    session_id=session_id,
                    assign_immediately=False,
                )
                stage = "assign_result_card"
                result_deck, result_card = assign_next_result_card(
                    db,
                    session_id=session_id,
                    treatment_key=treatment_card.treatment_key,
                    assign_immediately=False,
                )
                stage = "assign_payment_card"
                payment_deck, payment_card = assign_next_payment_card(
                    db,
                    session_id=session_id,
                    assign_immediately=False,
                )
                phase_activation_status = current_phase_activation_status(phase_key)

            stage = "build_session_record"
            root = (
                db.get(SeriesRoot, treatment_deck.legacy_root_id)
                if treatment_deck.legacy_root_id
                else None
            )
            treatment = treatment_config(phase_key, treatment_card.treatment_key)
            position_index = treatment_card.card_position
            root_id = root.id if root else legacy_series.root_id
            session_record = SessionRecord(
                id=session_id,
                user_id=user.id,
                root_id=legacy_series.root_id,
                series_id=legacy_series.id,
                referral_code=referral_code(f"{user.id}:{root_id}:{position_index}"),
                invited_by_referral_code=resolved_referral_code,
                referral_source=resolved_referral_source,
                referral_medium=resolved_referral_medium,
                referral_campaign=resolved_referral_campaign,
                referral_link_id=referral_link_id,
                qr_entry_code=qr_entry_code,
                referral_landing_path=referral_path,
                referral_arrived_at=now if resolved_referral_code else None,
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
            db.add(session_record)
        created_now = True
        referral_attached = False
        if resolved_referral_code and resolved_referral_code != session_record.referral_code:
            session_record.invited_by_session_id = resolved_inviter_session_id
            referral_attached = bool(resolved_inviter_session_id or referral_link_id)

        user.last_seen_at = now
        db.add(user)
        db.add(legacy_series)
        db.add(session_record)
        stage = "flush_session_record"
        db.flush()
        stage = "bind_reserved_cards"
        mark_deck_card_assigned(treatment_card, session_id=session_record.id)
        mark_deck_card_assigned(result_card, session_id=session_record.id)
        mark_deck_card_assigned(payment_card, session_id=session_record.id)
        db.add(treatment_card)
        db.add(result_card)
        db.add(payment_card)
        db.flush()
        stage = "create_consent_record"
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
        stage = "upsert_client_context"
        upsert_session_client_context(
            db,
            session_id=session_record.id,
            raw_context=client_context,
            request=request,
            app_language=language,
        )
        stage = "link_gateway_visit"
        link_gateway_visit_to_session(
            db,
            gateway_visit_id=gateway_visit_id or referral_link_id,
            session_id=session_record.id,
            qr_entry_code=qr_entry_code,
        )
        stage = "link_referral_click"
        link_referral_click_to_session(
            db,
            referral_link_id=referral_link_id,
            session_id=session_record.id,
        )
        stage = "register_referral_conversion"
        register_referral_conversion(
            db,
            session_record=session_record,
            just_attached=referral_attached,
        )
        stage = "audit_session_assigned"
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

        stage = "check_same_device_recent_sessions"
        recent_same_device_user_count = int(
            db.exec(
                select(func.count(func.distinct(SessionRecord.user_id))).where(
                    SessionRecord.device_hash == device_hash,
                    SessionRecord.created_at >= now - timedelta(minutes=15),
                    SessionRecord.user_id != user.id,
                )
            ).one()
            or 0
        )
        if recent_same_device_user_count:
            stage = "create_same_device_flag"
            create_fraud_flag(
                db,
                flag_key="same_device_multiple_bracelets",
                severity="medium",
                session_id=session_record.id,
                user_id=user.id,
                payload={"other_users_in_15m": recent_same_device_user_count},
            )

        stage = "commit_new_session"
        db.commit()
        return user, session_record, created_now
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        setattr(exc, "sonar_stage", stage)
        raise


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


def current_gateway_failover_state() -> dict[str, Any]:
    with _gateway_failover_state_lock:
        return json.loads(json_dumps_compact(_gateway_failover_state))


def update_gateway_failover_state(
    *,
    monitor_running: Optional[bool] = None,
    monitor_enabled: Optional[bool] = None,
    last_checked_at: Optional[str] = None,
    last_event: Optional[dict[str, Any]] = None,
    primary: Optional[dict[str, Any]] = None,
    backup: Optional[dict[str, Any]] = None,
) -> None:
    with _gateway_failover_state_lock:
        if monitor_running is not None:
            _gateway_failover_state["monitor_running"] = monitor_running
        if monitor_enabled is not None:
            _gateway_failover_state["monitor_enabled"] = monitor_enabled
        if last_checked_at is not None:
            _gateway_failover_state["last_checked_at"] = last_checked_at
        if last_event is not None:
            _gateway_failover_state["last_event"] = last_event
        if primary is not None:
            _gateway_failover_state["primary"].update(primary)
        if backup is not None:
            _gateway_failover_state["backup"].update(backup)


def gateway_failover_ready() -> tuple[bool, Optional[str]]:
    if not settings.gateway_failover_enabled:
        return False, "failover_automatico_desactivado"
    if not settings.gateway_primary_healthcheck_url:
        return False, "falta GATEWAY_PRIMARY_HEALTHCHECK_URL"
    if not settings.gateway_backup_healthcheck_url:
        return False, "falta GATEWAY_BACKUP_HEALTHCHECK_URL"
    return True, None


def check_gateway_target_health(url: str) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        response = httpx.get(
            url,
            timeout=settings.gateway_healthcheck_timeout_seconds,
            follow_redirects=True,
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        healthy = 200 <= response.status_code < 400
        return {
            "healthy": healthy,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "error": None if healthy else f"status_{response.status_code}",
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "healthy": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


def apply_gateway_target_health_state(
    target: str,
    result: dict[str, Any],
    *,
    checked_at_iso: str,
) -> dict[str, Any]:
    state = current_gateway_failover_state()[target]
    consecutive_failures = int(state["consecutive_failures"])
    consecutive_successes = int(state["consecutive_successes"])
    if result["healthy"]:
        consecutive_successes += 1
        consecutive_failures = 0
    else:
        consecutive_failures += 1
        consecutive_successes = 0
    updated = {
        "healthy": result["healthy"],
        "consecutive_failures": consecutive_failures,
        "consecutive_successes": consecutive_successes,
        "last_status_code": result["status_code"],
        "last_latency_ms": result["latency_ms"],
        "last_error": result["error"],
        "last_checked_at": checked_at_iso,
    }
    update_gateway_failover_state(**{target: updated}, last_checked_at=checked_at_iso)
    return updated


def ensure_runtime_ready(timeout_seconds: float = 5.0) -> None:
    startup_state = current_startup_state()
    if startup_state["initialized"] and not schema_needs_reset():
        return

    if not startup_state["initializing"]:
        initialize_application_state()
        startup_state = current_startup_state()
        if startup_state["initialized"] and not schema_needs_reset():
            return

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        startup_state = current_startup_state()
        if startup_state["initialized"] and not schema_needs_reset():
            return
        time.sleep(0.05)

    startup_state = current_startup_state()
    raise HTTPException(
        status_code=503,
        detail=startup_state["error"] or "Inicializando el servicio",
    )


def readiness_payload() -> dict[str, Any]:
    dependency_status = startup_dependency_status()
    startup_state = current_startup_state()
    payload = {
        **dependency_status,
        "instance_name": settings.instance_name,
        "config_fingerprint": deployment_config_fingerprint(),
        "startup_initialized": startup_state["initialized"],
        "startup_initializing": startup_state["initializing"],
        "startup_error": startup_state["error"],
    }
    payload["ok"] = (
        dependency_status["database_ready"]
        and dependency_status["redis_ready"]
        and dependency_status["schema_ready"]
        and startup_state["initialized"]
        and not startup_state["initializing"]
        and startup_state["error"] is None
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
            from migrate import apply_migrations

            migrated = apply_migrations(strict=True)
            if not migrated:
                raise RuntimeError(
                    "Migration pipeline did not converge during startup."
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
                        normalize_experiment_mode(state.experiment_mode),
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "startup_status_cache_write_failed_non_blocking"
                    )
            final_readiness = startup_dependency_status()
            if (
                not final_readiness["database_ready"]
                or not final_readiness["redis_ready"]
                or not final_readiness["schema_ready"]
            ):
                raise RuntimeError(
                    "Startup finished without converging dependency/schema readiness."
                )
        except Exception as exc:  # noqa: BLE001
            update_startup_state(
                initialized=False,
                initializing=True,
                error=str(exc),
                last_readiness=startup_dependency_status(),
            )
            logger.exception("startup_initialization_failed")
            time.sleep(settings.startup_dependency_retry_interval_seconds)
            continue
        update_startup_state(
            initialized=True,
            initializing=False,
            error=None,
            last_readiness=final_readiness,
        )
        logger.info(
            "startup_completed",
            extra={
                "structured_payload": {
                    "database_url": settings.database_url,
                    "redis_url": settings.redis_url,
                    "auto_bootstrap_demo_data": settings.auto_bootstrap_demo_data,
                    "readiness": final_readiness,
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
    threading.Thread(
        target=gateway_failover_monitor_loop,
        name="sonar-gateway-failover",
        daemon=True,
    ).start()


def perform_admin_system_reset(*, actor: str, reason: Optional[str] = None) -> dict[str, Any]:
    reset_started_at = utcnow()
    readiness_before = startup_dependency_status()
    update_startup_state(
        initialized=False,
        initializing=True,
        error="Reinicio administrativo en curso",
        last_readiness={
            **readiness_before,
            "schema_ready": False,
        },
    )

    with Session(engine) as snapshot_db:
        before_counts = admin_reset_counts_payload(snapshot_db)

    try:
        try:
            set_experiment_status_cache(
                "active",
                "admin_reset_in_progress",
                EXPERIMENT_MODE_CLOSED,
            )
        except Exception:  # noqa: BLE001
            logger.exception("admin_system_reset_cache_guard_failed_non_blocking")

        from migrate import apply_migrations

        migrated = apply_migrations(reset_requested=True, strict=True)
        if not migrated:
            raise RuntimeError("El reset no pudo converger al esquema actual")

        runtime_cleared = clear_runtime_state()
        reset_gateway_failover_runtime_state()

        with Session(engine) as db:
            if settings.auto_bootstrap_demo_data and settings.database_is_sqlite:
                bootstrap_demo_data(db)
            state = get_or_create_experiment_state(db)
            db.commit()
            after_counts = admin_reset_counts_payload(db)
            experiment_control = experiment_control_payload(state)
            try:
                set_experiment_status_cache(
                    state.experiment_status,
                    state.pause_reason,
                    normalize_experiment_mode(state.experiment_mode),
                )
            except Exception:  # noqa: BLE001
                logger.exception("admin_system_reset_cache_restore_failed_non_blocking")

        final_readiness = startup_dependency_status()
        update_startup_state(
            initialized=True,
            initializing=False,
            error=None,
            last_readiness=final_readiness,
        )
        logger.warning(
            "admin_system_reset_completed",
            extra={
                "structured_payload": {
                    "actor": actor,
                    "reason": reason.strip() if reason else None,
                    "reset_started_at": reset_started_at.isoformat(),
                    "before_counts": before_counts,
                    "after_counts": after_counts,
                    "runtime_cleared": runtime_cleared,
                    "readiness": final_readiness,
                }
            },
        )
        return {
            "ok": True,
            "reset_started_at": reset_started_at.isoformat(),
            "reset_completed_at": utcnow().isoformat(),
            "reset_by": actor,
            "reason": reason.strip() if reason else None,
            "before_counts": before_counts,
            "after_counts": after_counts,
            "runtime_reset": runtime_cleared,
            "experiment_control": experiment_control,
            "readiness": {
                **final_readiness,
                "ok": bool(
                    final_readiness["database_ready"]
                    and final_readiness["redis_ready"]
                    and final_readiness["schema_ready"]
                ),
            },
        }
    except Exception as exc:
        failure_readiness = startup_dependency_status()
        update_startup_state(
            initialized=False,
            initializing=False,
            error=str(exc),
            last_readiness=failure_readiness,
        )
        logger.exception(
            "admin_system_reset_failed",
            extra={
                "structured_payload": {
                    "actor": actor,
                    "reason": reason.strip() if reason else None,
                    "reset_started_at": reset_started_at.isoformat(),
                    "readiness": failure_readiness,
                }
            },
        )
        raise HTTPException(
            status_code=500,
            detail="No se pudo reiniciar completamente el sistema",
        ) from exc


def get_gateway_route(db: Session, qr_code: str) -> Optional[GatewayRoute]:
    normalized_qr_code = normalize_gateway_qr_code(qr_code)
    return db.exec(
        select(GatewayRoute).where(GatewayRoute.qr_code == normalized_qr_code)
    ).first()


def upsert_gateway_route(
    db: Session,
    *,
    qr_code: str,
    zone_code: Optional[str],
    primary_target_url: str,
    backup_target_url: Optional[str],
    active_target: str,
    enabled: bool,
    notes: Optional[str],
) -> GatewayRoute:
    normalized_qr_code = normalize_gateway_qr_code(qr_code)
    normalized_zone_code = normalize_gateway_zone_code(
        zone_code,
        qr_code=normalized_qr_code,
    )
    normalized_primary_target_url = normalize_gateway_target_url(primary_target_url)
    normalized_backup_target_url = normalize_gateway_target_url(backup_target_url)
    normalized_active_target = normalize_gateway_target(active_target)
    if normalized_active_target == GATEWAY_TARGET_BACKUP and not normalized_backup_target_url:
        raise ValueError("No puedes activar backup sin URL backup configurada")

    route = get_gateway_route(db, normalized_qr_code)
    if not route:
        route = GatewayRoute(qr_code=normalized_qr_code)
    previous_active_target = route.active_target
    route.zone_code = normalized_zone_code
    route.primary_target_url = normalized_primary_target_url or ""
    route.backup_target_url = normalized_backup_target_url
    route.active_target = normalized_active_target
    route.enabled = enabled
    route.notes = notes.strip() if notes else None
    route.updated_at = utcnow()
    if previous_active_target != normalized_active_target:
        route.last_switched_at = route.updated_at
    if not route.created_at:
        route.created_at = route.updated_at
    db.add(route)
    db.flush()
    return route


def switch_gateway_route_target(
    db: Session,
    *,
    qr_code: str,
    active_target: str,
) -> GatewayRoute:
    route = get_gateway_route(db, qr_code)
    if not route:
        raise HTTPException(status_code=404, detail="QR no configurado")
    normalized_active_target = normalize_gateway_target(active_target)
    if normalized_active_target == GATEWAY_TARGET_BACKUP and not route.backup_target_url:
        raise HTTPException(status_code=400, detail="La ruta no tiene backup configurado")
    route.active_target = normalized_active_target
    route.last_switched_at = utcnow()
    route.updated_at = route.last_switched_at
    db.add(route)
    db.flush()
    return route


def current_gateway_mode_summary(db: Session) -> dict[str, Any]:
    routes = db.exec(select(GatewayRoute).order_by(GatewayRoute.qr_code)).all()
    if not routes:
        return {
            "mode": GATEWAY_TARGET_PRIMARY,
            "route_count": 0,
            "enabled_route_count": 0,
            "routes_with_backup": 0,
            "mixed": False,
        }

    active_targets = {route.active_target for route in routes}
    enabled_routes = [route for route in routes if route.enabled]
    routes_with_backup = sum(1 for route in routes if route.backup_target_url)
    if len(active_targets) == 1:
        mode = next(iter(active_targets))
        mixed = False
    else:
        mode = "mixed"
        mixed = True
    return {
        "mode": mode,
        "route_count": len(routes),
        "enabled_route_count": len(enabled_routes),
        "routes_with_backup": routes_with_backup,
        "mixed": mixed,
    }


def switch_gateway_mode(db: Session, *, mode: str) -> dict[str, Any]:
    normalized_mode = normalize_gateway_target(mode)
    routes = db.exec(select(GatewayRoute).order_by(GatewayRoute.qr_code)).all()
    if normalized_mode == GATEWAY_TARGET_BACKUP:
        missing_backup = [
            route.qr_code
            for route in routes
            if route.enabled and not route.backup_target_url
        ]
        if missing_backup:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No todas las rutas activas tienen backup configurado: "
                    + ", ".join(missing_backup[:20])
                ),
            )

    switched_at = utcnow()
    changed_routes = 0
    for route in routes:
        if route.active_target == normalized_mode:
            continue
        route.active_target = normalized_mode
        route.last_switched_at = switched_at
        route.updated_at = switched_at
        db.add(route)
        changed_routes += 1
    db.flush()
    return {
        **current_gateway_mode_summary(db),
        "changed_routes": changed_routes,
        "switched_at": switched_at.isoformat(),
    }


def run_gateway_failover_check(*, force: bool = False) -> dict[str, Any]:
    enabled, disabled_reason = gateway_failover_ready()
    checked_at_iso = utcnow().isoformat()
    update_gateway_failover_state(
        monitor_enabled=enabled,
        last_checked_at=checked_at_iso,
    )
    if not enabled and not force:
        snapshot = current_gateway_failover_state()
        snapshot["status"] = "skipped"
        snapshot["reason"] = disabled_reason
        return snapshot

    primary_url = settings.gateway_primary_healthcheck_url
    backup_url = settings.gateway_backup_healthcheck_url
    if not primary_url or not backup_url:
        snapshot = current_gateway_failover_state()
        snapshot["status"] = "skipped"
        snapshot["reason"] = disabled_reason or "healthcheck_urls_missing"
        return snapshot

    try:
        with distributed_lock("gateway-failover-monitor"):
            primary_result = check_gateway_target_health(primary_url)
            backup_result = check_gateway_target_health(backup_url)
            primary_state = apply_gateway_target_health_state(
                GATEWAY_TARGET_PRIMARY,
                primary_result,
                checked_at_iso=checked_at_iso,
            )
            backup_state = apply_gateway_target_health_state(
                GATEWAY_TARGET_BACKUP,
                backup_result,
                checked_at_iso=checked_at_iso,
            )

            with Session(engine) as db:
                mode_summary = current_gateway_mode_summary(db)
                current_mode = mode_summary["mode"]
                event_payload: Optional[dict[str, Any]] = None

                if (
                    current_mode != GATEWAY_TARGET_BACKUP
                    and primary_state["consecutive_failures"]
                    >= settings.gateway_healthcheck_failure_threshold
                    and backup_state["healthy"]
                ):
                    try:
                        switched = switch_gateway_mode(
                            db,
                            mode=GATEWAY_TARGET_BACKUP,
                        )
                    except HTTPException as exc:
                        event_payload = {
                            "type": "auto_failover_blocked",
                            "from_mode": current_mode,
                            "to_mode": GATEWAY_TARGET_BACKUP,
                            "checked_at": checked_at_iso,
                            "detail": exc.detail,
                        }
                        create_audit(
                            db,
                            entity_type="gateway_mode",
                            entity_id="global",
                            action="gateway_auto_failover_blocked",
                            payload=event_payload,
                        )
                        db.commit()
                        logger.warning(
                            "gateway_auto_failover_blocked",
                            extra={"structured_payload": event_payload},
                        )
                        update_gateway_failover_state(last_event=event_payload)
                        snapshot = current_gateway_failover_state()
                        snapshot["status"] = "blocked"
                        snapshot["gateway_mode"] = current_gateway_mode_summary(db)
                        return snapshot
                    event_payload = {
                        "type": "auto_failover",
                        "from_mode": current_mode,
                        "to_mode": GATEWAY_TARGET_BACKUP,
                        "primary_failures": primary_state["consecutive_failures"],
                        "backup_healthy": backup_state["healthy"],
                        "checked_at": checked_at_iso,
                        "mode_summary": switched,
                    }
                    create_audit(
                        db,
                        entity_type="gateway_mode",
                        entity_id="global",
                        action="gateway_auto_failover",
                        payload=event_payload,
                    )
                    db.commit()
                    logger.warning(
                        "gateway_auto_failover",
                        extra={"structured_payload": event_payload},
                    )
                elif (
                    current_mode == GATEWAY_TARGET_BACKUP
                    and settings.gateway_auto_failback_enabled
                    and primary_state["consecutive_successes"]
                    >= settings.gateway_healthcheck_success_threshold
                ):
                    switched = switch_gateway_mode(db, mode=GATEWAY_TARGET_PRIMARY)
                    event_payload = {
                        "type": "auto_failback",
                        "from_mode": current_mode,
                        "to_mode": GATEWAY_TARGET_PRIMARY,
                        "primary_successes": primary_state["consecutive_successes"],
                        "checked_at": checked_at_iso,
                        "mode_summary": switched,
                    }
                    create_audit(
                        db,
                        entity_type="gateway_mode",
                        entity_id="global",
                        action="gateway_auto_failback",
                        payload=event_payload,
                    )
                    db.commit()
                    logger.warning(
                        "gateway_auto_failback",
                        extra={"structured_payload": event_payload},
                    )
                elif (
                    current_mode == GATEWAY_TARGET_BACKUP
                    and not backup_state["healthy"]
                ):
                    event_payload = {
                        "type": "backup_unhealthy",
                        "mode": current_mode,
                        "backup_failures": backup_state["consecutive_failures"],
                        "checked_at": checked_at_iso,
                    }
                    logger.warning(
                        "gateway_backup_unhealthy",
                        extra={"structured_payload": event_payload},
                    )

            if event_payload:
                update_gateway_failover_state(last_event=event_payload)

            snapshot = current_gateway_failover_state()
            snapshot["status"] = "ok"
            with Session(engine) as db:
                snapshot["gateway_mode"] = current_gateway_mode_summary(db)
            return snapshot
    except HTTPException as exc:
        if exc.status_code == 409:
            snapshot = current_gateway_failover_state()
            snapshot["status"] = "skipped"
            snapshot["reason"] = "monitor_lock_contended"
            return snapshot
        raise


def gateway_failover_monitor_loop() -> None:
    update_gateway_failover_state(monitor_running=True)
    interval_seconds = max(settings.gateway_healthcheck_interval_seconds, 1.0)
    while True:
        try:
            run_gateway_failover_check(force=False)
        except Exception:  # noqa: BLE001
            logger.exception("gateway_failover_monitor_cycle_failed")
        time.sleep(interval_seconds)


def qr_gateway_redirect(
    db: Session,
    *,
    request: Request,
    raw_qr_code: str,
) -> Response:
    try:
        qr_code = normalize_gateway_qr_code(raw_qr_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    gateway_visit_id = make_uuid()
    derived_zone_code = derive_zone_code(qr_code)

    route = get_gateway_route(db, qr_code)
    if not route:
        create_gateway_access_log(
            db,
            request=request,
            qr_code=qr_code,
            zone_code=derived_zone_code,
            gateway_visit_id=gateway_visit_id,
            route=None,
            selected_target="none",
            resolved_target_url=None,
            redirect_status_code=404,
            status="missing_route",
        )
        db.commit()
        raise HTTPException(status_code=404, detail="QR no configurado")

    if not route.enabled:
        create_gateway_access_log(
            db,
            request=request,
            qr_code=qr_code,
            zone_code=route.zone_code or derived_zone_code,
            gateway_visit_id=gateway_visit_id,
            route=route,
            selected_target=route.active_target,
            resolved_target_url=None,
            redirect_status_code=503,
            status="disabled_route",
        )
        db.commit()
        raise HTTPException(status_code=503, detail="QR temporalmente desactivado")

    try:
        selected_target, base_target_url = resolve_gateway_target_url(route)
    except ValueError as exc:
        create_gateway_access_log(
            db,
            request=request,
            qr_code=qr_code,
            zone_code=route.zone_code or derived_zone_code,
            gateway_visit_id=gateway_visit_id,
            route=route,
            selected_target=route.active_target,
            resolved_target_url=None,
            redirect_status_code=503,
            status="invalid_route",
        )
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    resolved_target_url = build_gateway_redirect_url(
        base_target_url,
        request=request,
        qr_code=qr_code,
        gateway_visit_id=gateway_visit_id,
    )
    create_gateway_access_log(
        db,
        request=request,
        qr_code=qr_code,
        zone_code=route.zone_code or derived_zone_code,
        gateway_visit_id=gateway_visit_id,
        route=route,
        selected_target=selected_target,
        resolved_target_url=resolved_target_url,
        redirect_status_code=307,
        status="redirected",
    )
    db.commit()
    return RedirectResponse(url=resolved_target_url, status_code=307)


@app.get("/")
def root() -> dict[str, str]:
    return {"ok": "true", "docs": "/docs", "health": "/health"}


@app.get("/health/live")
def health_live() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "live",
        "instance_name": settings.instance_name,
        "config_fingerprint": deployment_config_fingerprint(),
    }


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
            "instance_name": settings.instance_name,
            "config_fingerprint": deployment_config_fingerprint(),
            "schema_version": SCHEMA_VERSION,
            "experiment_version": EXPERIMENT_VERSION,
            "ui_version": UI_VERSION,
            "lexicon_version": LEXICON_VERSION,
            "current_phase": experiment_state.current_phase,
            "experiment_status": experiment_state.experiment_status,
            "experiment_mode": normalize_experiment_mode(experiment_state.experiment_mode),
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


@app.get("/invite/{referral_link_id}")
def referral_invite_redirect(
    referral_link_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> Response:
    link = db.get(ReferralLink, referral_link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link de invitacion no encontrado")
    redirect_url = build_referral_redirect_url(link)
    create_referral_click(
        db,
        request=request,
        link=link,
        redirect_status_code=307,
        status="redirected",
    )
    db.commit()
    return RedirectResponse(url=redirect_url, status_code=307)


@app.get("/play")
def play_query_redirect(
    request: Request,
    qr: Optional[str] = None,
    qr_id: Optional[str] = None,
    poster: Optional[str] = None,
    poster_id: Optional[str] = None,
    cartel: Optional[str] = None,
    cartel_id: Optional[str] = None,
    db: Session = Depends(get_session),
) -> Response:
    raw_qr_code = qr or qr_id or poster or poster_id or cartel or cartel_id
    if not raw_qr_code:
        raise HTTPException(status_code=400, detail="Falta codigo QR")
    return qr_gateway_redirect(db, request=request, raw_qr_code=raw_qr_code)


@app.get("/play/{qr_code}")
def play_path_redirect(
    qr_code: str,
    request: Request,
    db: Session = Depends(get_session),
) -> Response:
    return qr_gateway_redirect(db, request=request, raw_qr_code=qr_code)


@app.get("/v1/config")
def config() -> dict[str, Any]:
    ensure_runtime_ready()
    with Session(engine) as db:
        return build_config_payload(db)


@app.post("/v1/interest-signup")
def interest_signup(
    payload: InterestSignupRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    state = get_or_create_experiment_state(db)
    active_operational_note = get_active_operational_note(db)
    mode = normalize_experiment_mode(state.experiment_mode)
    if not experiment_is_paused(state) and mode != EXPERIMENT_MODE_CLOSED:
        raise HTTPException(
            status_code=409,
            detail="El registro de interes solo esta disponible cuando el experimento esta detenido o cerrado",
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
            source_screen=(
                "experiment_closed"
                if mode == EXPERIMENT_MODE_CLOSED
                else "experiment_paused"
            ),
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
    email_interest, _ = upsert_email_interest(
        db,
        email=normalized_email,
        source=existing.source_screen,
    )
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
    create_audit(
        db,
        entity_type="email_interest",
        entity_id=email_interest.id,
        action="email_interest_captured",
        payload={
            "email": normalized_email,
            "source": email_interest.source,
        },
    )
    db.commit()
    return {"ok": True, "stored": True}


@app.post("/interest")
def capture_interest_email(
    payload: InterestCaptureRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    normalized_email = normalize_email(payload.email)
    normalized_source = normalize_interest_source(payload.source)
    entry, created = upsert_email_interest(
        db,
        email=normalized_email,
        source=normalized_source,
    )
    create_audit(
        db,
        entity_type="email_interest",
        entity_id=entry.id,
        action="email_interest_captured",
        payload={
            "email": normalized_email,
            "source": normalized_source,
            "created": created,
        },
    )
    db.commit()
    return {
        "ok": True,
        "stored": True,
        "created": created,
        "source": normalized_source,
    }


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
        ensure_runtime_ready()
        experiment_state = get_or_create_experiment_state(db)
        mode = normalize_experiment_mode(experiment_state.experiment_mode)
        if experiment_is_paused(experiment_state):
            raise HTTPException(
                status_code=423,
                detail="El experimento esta temporalmente detenido",
            )
        existing_session = find_existing_session_by_bracelet(db, bracelet_id=bracelet_id)
        if mode == EXPERIMENT_MODE_CLOSING and existing_session is None:
            raise HTTPException(
                status_code=423,
                detail="El experimento esta cerrando y no admite nuevas entradas",
            )
        if mode == EXPERIMENT_MODE_CLOSED and existing_session is None:
            raise HTTPException(
                status_code=423,
                detail="El experimento esta cerrado",
            )
        pulsera = db.get(Pulsera, bracelet_id)
        if not pulsera:
            pulsera = Pulsera(id=bracelet_id)
            db.add(pulsera)
            db.flush()
        try:
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
                gateway_visit_id=payload.gateway_visit_id,
                qr_entry_code=payload.qr_entry_code,
                referral_path=payload.referral_path,
                consent_checkbox_order=payload.consent_checkbox_order,
                consent_checkbox_timestamps_ms=payload.consent_checkbox_timestamps_ms,
                consent_continue_blocked_count=payload.consent_continue_blocked_count,
                client_context=payload.client_context,
                request=request,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            failure_stage = getattr(exc, "sonar_stage", "unknown")
            logger.exception(
                "session_access_failed",
                extra={
                    "bracelet_id": bracelet_id,
                    "stage": failure_stage,
                    "error_type": type(exc).__name__,
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "No se pudo inicializar la sesion",
                    "stage": failure_stage,
                },
            ) from exc
        if created_now:
            record_session_started("instructions")
        relations = load_session_payload_relations(db, session_record)
        if mode == EXPERIMENT_MODE_CLOSED:
            return {
                "created_now": False,
                "session": build_closed_terminal_session_payload(
                    db,
                    session_record,
                    relations=relations,
                ),
            }
        return {
            "created_now": created_now,
            "session": build_session_payload(db, session_record, relations=relations),
        }


@app.post("/v1/referrals/link")
def create_referral_link_endpoint(
    payload: ReferralLinkCreateRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    session_record = db.get(SessionRecord, payload.session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    try:
        channel = normalize_referral_channel(payload.channel)
        target_path = normalize_referral_target_path(payload.target_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    link = ReferralLink(
        inviter_session_id=session_record.id,
        inviter_user_id=session_record.user_id,
        inviter_referral_code=session_record.referral_code,
        channel=channel,
        traffic_source=normalize_tracking_value(payload.traffic_source),
        traffic_medium=normalize_tracking_value(payload.traffic_medium),
        campaign_code=normalize_tracking_value(payload.campaign_code),
        target_path=target_path,
    )
    db.add(link)
    db.flush()
    create_audit(
        db,
        entity_type="referral_link",
        entity_id=link.id,
        action="referral_link_created",
        session_id=session_record.id,
        payload=referral_link_payload(link),
    )
    db.commit()
    return {"ok": True, "link": referral_link_payload(link)}


@app.get("/v1/session/{session_id}/resume")
def resume_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"session:{session_id}"):
        ensure_runtime_ready()
        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
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
        experiment_state = get_or_create_experiment_state(db)
        if normalize_experiment_mode(experiment_state.experiment_mode) == EXPERIMENT_MODE_CLOSED:
            return {
                "created_now": False,
                "session": build_closed_terminal_session_payload(db, record),
            }
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
        ensure_runtime_ready()
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
        experiment_state = get_or_create_experiment_state(db)
        if experiment_is_paused(experiment_state):
            raise HTTPException(
                status_code=423,
                detail="El experimento esta temporalmente detenido",
            )
        if normalize_experiment_mode(experiment_state.experiment_mode) == EXPERIMENT_MODE_CLOSED:
            terminal_session = build_closed_terminal_session_payload(db, record)
            last_known_value = (
                record.last_seen_value
                or record.first_result_value
                or 1
            )
            return {
                "attempt": {
                    "attempt_index": payload.attempt_index,
                    "result_value": last_known_value,
                    "is_first_roll": payload.attempt_index == 1,
                    "remaining_attempts": max(record.max_attempts - payload.attempt_index, 0),
                    "blocked": True,
                    "reason": "experiment_closed",
                },
                "session": terminal_session,
            }
        ensure_valid_state(record, {"assigned", "in_game"}, "roll")

        expected_attempt = expected_attempt_index(record)
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

        db.flush()
        throws = db.exec(
            select(Throw)
            .where(Throw.session_id == record.id)
            .order_by(Throw.attempt_index)
        ).all()
        relations = load_session_payload_relations(db, record, include_throws=False)
        relations.throws = throws

        response_payload = {
            "attempt": {
                "attempt_index": payload.attempt_index,
                "result_value": result_value,
                "is_first_roll": payload.attempt_index == 1,
                "remaining_attempts": record.max_attempts - payload.attempt_index,
            },
            "session": build_session_payload(db, record, relations=relations),
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
        ensure_runtime_ready()
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
        experiment_state = get_or_create_experiment_state(db)
        if experiment_is_paused(experiment_state):
            raise HTTPException(
                status_code=423,
                detail="El experimento esta temporalmente detenido",
            )
        if normalize_experiment_mode(experiment_state.experiment_mode) == EXPERIMENT_MODE_CLOSED:
            return {
                "session": build_closed_terminal_session_payload(db, record)
            }
        ensure_valid_state(record, {"in_game"}, "prepare-report")
        if record.first_result_value is None:
            raise HTTPException(
                status_code=409, detail="Todavia no existe primera tirada"
            )

        old_state = record.state
        previous_screen = record.screen_cursor or "game"
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
        record_screen_transition(previous_screen, "report")

        db.flush()
        relations = load_session_payload_relations(db, record)
        response_payload = {
            "session": build_session_payload(db, record, relations=relations)
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


@app.post("/v1/session/{session_id}/screen")
def set_screen(
    session_id: str,
    payload: ScreenCursorRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    allowed_screens = {"instructions", "comprehension", "game", "report", "exit"}
    if payload.screen not in allowed_screens:
        raise HTTPException(status_code=400, detail="Pantalla no valida")

    with distributed_lock(f"session:{session_id}"):
        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
        if record.state in {"completed_win", "completed_no_win"}:
            return {"session": build_session_payload(db, record)}
        ensure_experiment_accepting_entries(db, allow_inflight=True)

        allowed_by_state = {
            "assigned": {
                "instructions": {"instructions", "comprehension"},
                "comprehension": {"comprehension", "game"},
                "game": {"game"},
            },
            "in_game": {"game": {"game"}},
            "report_ready": {"report": {"report"}},
            "completed_win": {"exit": {"exit"}},
            "completed_no_win": {"exit": {"exit"}},
        }
        current_screen = record.screen_cursor or "instructions"
        valid_targets = allowed_by_state.get(record.state, {}).get(
            current_screen,
            set(),
        )
        if payload.screen not in valid_targets:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Pantalla invalida para el estado actual",
                    "server_state": record.state,
                    "screen": record.screen_cursor,
                },
            )

        previous_screen = current_screen
        record.screen_cursor = payload.screen
        record.last_seen_at = utcnow()
        db.add(record)
        record_screen_transition(previous_screen, payload.screen)
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


def expected_attempt_index(record: SessionRecord) -> int:
    if record.first_result_value is None:
        return 1
    return int(record.reroll_count or 0) + 2


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
        ensure_experiment_accepting_entries(db, allow_inflight=True)
        cached = get_existing_receipt(
            db,
            session_id=session_id,
            endpoint=endpoint,
            idempotency_key=payload.idempotency_key,
        )
        if cached:
            return cached

        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
        ensure_valid_state(record, {"report_ready"}, "submit-report")
        if record.first_result_value is None:
            raise HTTPException(status_code=409, detail="No existe primera tirada")

        if record.claim_submitted_at is not None or record.reported_value is not None:
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

        # The active design uses a fixed treatment-level social norm.
        # Completed claims do not update any participant-facing norm state.
        series.completed_count += 1
        series.is_closed = True
        series.close_reason = series.close_reason or "session_completed"
        db.add(series)

        payout_reference = (
            payout_reference_code(record.id) if record.selected_for_payment else None
        )
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
        previous_screen = record.screen_cursor or "report"
        record.screen_cursor = "exit"
        record.state = (
            "completed_win" if record.selected_for_payment else "completed_no_win"
        )
        db.add(record)

        quality_flags = build_quality_flags(record)
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
        record_screen_transition(previous_screen, "exit")
        record_session_completed()

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
        snapshot.payout_reference_shown = payout_reference
        snapshot.updated_at = utcnow()
        db.add(snapshot)

        payment = Payment(
            session_id=record.id,
            claim_id=claim.id,
            eligible=record.selected_for_payment,
            amount_cents=record.payout_amount,
            status="pending" if record.selected_for_payment else "not_eligible",
            payout_reference=payout_reference,
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

        db.flush()
        relations = load_session_payload_relations(db, record, include_throws=False)
        relations.throws = throws
        relations.claim = claim
        relations.payment = payment
        relations.snapshot_record = snapshot
        response_payload = {
            "session": build_session_payload(db, record, relations=relations)
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


@app.post("/v1/session/{session_id}/claim-followup")
def update_claim_followup(
    session_id: str,
    payload: ClaimFollowupRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock(f"session:{session_id}"):
        ensure_experiment_accepting_entries(db, allow_inflight=True)
        record = get_session_or_404(db, session_id, for_update=True)
        ensure_session_request_authorized(record, request=request)
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
        ensure_session_request_authorized(record, request=request)
        existing_event_names = set(
            db.exec(
                select(TelemetryEvent.event_name).where(
                    TelemetryEvent.session_id == record.id,
                    TelemetryEvent.event_name.in_(MINIMAL_TELEMETRY_EVENT_NAMES),
                )
            ).all()
        )
        accepted_items: list[TelemetryItem] = []
        seen_in_batch: set[str] = set()
        for item in payload.events:
            if item.event_name not in MINIMAL_TELEMETRY_EVENT_NAMES:
                continue
            if item.event_name in existing_event_names or item.event_name in seen_in_batch:
                continue
            accepted_items.append(item)
            seen_in_batch.add(item.event_name)
        if not accepted_items:
            record.last_seen_at = utcnow()
            db.add(record)
            db.commit()
            return {"accepted_count": 0}

        accepted = 0
        batch_server_now = utcnow()
        batch_server_ts_ms = int(batch_server_now.timestamp() * 1000)
        for item in accepted_items:
            clock_skew_ms = None
            if item.client_ts is not None:
                clock_skew_ms = batch_server_ts_ms - item.client_ts
            db.add(
                TelemetryEvent(
                    session_id=record.id,
                    event_type=item.event_type or "experiment",
                    event_name=item.event_name,
                    operational_note_id=record.operational_note_id,
                    operational_note_text=record.operational_note_text,
                    client_ts=item.client_ts,
                    event_sequence_number=item.event_sequence_number,
                    timezone_offset_minutes=item.timezone_offset_minutes,
                    client_clock_skew_estimate_ms=clock_skew_ms,
                    duration_ms=item.duration_ms
                    if item.event_name == "reaction_time_ms"
                    else None,
                    value=item.value
                    if item.event_name
                    in {"first_throw", "reroll_count", "report_value"}
                    else None,
                    server_ts=batch_server_now,
                )
            )
            accepted += 1
            if (
                item.event_sequence_number
                and item.event_sequence_number > record.max_event_sequence_number
            ):
                record.max_event_sequence_number = item.event_sequence_number
            record.telemetry_event_count += 1
        record.last_seen_at = utcnow()
        db.add(record)
        db.commit()
        return {"accepted_count": accepted}

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
    latest_closure_log = get_latest_experiment_closure_log(db)
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
        "experiment_mode": normalize_experiment_mode(state.experiment_mode),
        "experiment_mode_changed_at": (
            state.experiment_mode_changed_at.isoformat()
            if state.experiment_mode_changed_at
            else None
        ),
        "experiment_mode_changed_by": state.experiment_mode_changed_by,
        "experiment_mode_reason": state.experiment_mode_reason,
        "phase_transition_threshold": state.phase_transition_threshold,
        "valid_completed_count": state.valid_completed_count,
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
        "latest_closure_log": experiment_closure_log_payload(latest_closure_log),
        "active_operational_note": operational_note_payload(active_operational_note),
    }


@app.get("/admin/experiment/closure-logs")
def admin_experiment_closure_logs(
    limit: int = 20,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit), 200))
    logs = db.exec(
        select(ExperimentClosureLog)
        .order_by(ExperimentClosureLog.timestamp.desc(), ExperimentClosureLog.id.desc())
        .limit(bounded_limit)
    ).all()
    return {
        "logs": [experiment_closure_log_payload(log_entry) for log_entry in logs],
        "count": len(logs),
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


@app.get("/admin/gateway/routes")
def admin_gateway_routes(db: Session = Depends(get_session)) -> dict[str, Any]:
    routes = db.exec(select(GatewayRoute).order_by(GatewayRoute.qr_code)).all()
    return {
        "gateway_public_base_url": settings.gateway_public_base_url,
        "gateway_mode": current_gateway_mode_summary(db),
        "gateway_failover": current_gateway_failover_state(),
        "routes": [gateway_route_payload(route) for route in routes],
    }


@app.get("/admin/gateway/mode")
def admin_gateway_mode(db: Session = Depends(get_session)) -> dict[str, Any]:
    return current_gateway_mode_summary(db)


@app.get("/admin/gateway/failover")
def admin_gateway_failover_state(db: Session = Depends(get_session)) -> dict[str, Any]:
    return {
        **current_gateway_failover_state(),
        "gateway_mode": current_gateway_mode_summary(db),
        "config": {
            "enabled": settings.gateway_failover_enabled,
            "primary_healthcheck_url": settings.gateway_primary_healthcheck_url,
            "backup_healthcheck_url": settings.gateway_backup_healthcheck_url,
            "interval_seconds": settings.gateway_healthcheck_interval_seconds,
            "timeout_seconds": settings.gateway_healthcheck_timeout_seconds,
            "failure_threshold": settings.gateway_healthcheck_failure_threshold,
            "auto_failback_enabled": settings.gateway_auto_failback_enabled,
            "success_threshold": settings.gateway_healthcheck_success_threshold,
        },
    }


@app.post("/admin/gateway/failover/check-now")
def admin_gateway_failover_check_now() -> dict[str, Any]:
    return run_gateway_failover_check(force=True)


@app.post("/admin/gateway/mode")
def admin_gateway_mode_switch(
    payload: AdminGatewayModeRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("gateway-mode-control"):
        try:
            mode_summary = switch_gateway_mode(db, mode=payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        create_audit(
            db,
            entity_type="gateway_mode",
            entity_id="global",
            action="gateway_mode_switched",
            payload=mode_summary,
        )
        db.commit()
        return {"ok": True, **mode_summary}


@app.post("/admin/gateway/routes")
def admin_gateway_route_upsert(
    payload: AdminGatewayRouteUpsertRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("gateway-route-control"):
        try:
            route = upsert_gateway_route(
                db,
                qr_code=payload.qr_code,
                zone_code=payload.zone_code,
                primary_target_url=payload.primary_target_url,
                backup_target_url=payload.backup_target_url,
                active_target=payload.active_target,
                enabled=payload.enabled,
                notes=payload.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        create_audit(
            db,
            entity_type="gateway_route",
            entity_id=route.id,
            action="gateway_route_upserted",
            payload=gateway_route_payload(route),
        )
        db.commit()
        return {"ok": True, "route": gateway_route_payload(route)}


@app.get("/admin/gateway/summary")
def admin_gateway_summary(db: Session = Depends(get_session)) -> dict[str, Any]:
    routes = db.exec(select(GatewayRoute).order_by(GatewayRoute.qr_code)).all()
    logs = db.exec(select(GatewayAccessLog).order_by(GatewayAccessLog.created_at)).all()
    route_by_qr = {route.qr_code: route for route in routes}
    per_qr: dict[str, dict[str, Any]] = {}
    per_zone: dict[str, dict[str, Any]] = {}

    for route in routes:
        zone_code = route.zone_code or derive_zone_code(route.qr_code)
        per_qr[route.qr_code] = {
            "qr_code": route.qr_code,
            "zone_code": zone_code,
            "enabled": route.enabled,
            "active_target": route.active_target,
            "scans_total": 0,
            "sessions_started": 0,
            "conversion_rate": 0.0,
            "last_scan_at": None,
            "traffic_sources": {},
            "traffic_media": {},
            "_session_ids": set(),
        }
        per_zone.setdefault(
            zone_code,
            {
                "zone_code": zone_code,
                "qr_count": 0,
                "scans_total": 0,
                "sessions_started": 0,
                "conversion_rate": 0.0,
                "_session_ids": set(),
            },
        )
        per_zone[zone_code]["qr_count"] += 1

    for log_item in logs:
        zone_code = log_item.zone_code or derive_zone_code(log_item.qr_code)
        qr_row = per_qr.setdefault(
            log_item.qr_code,
            {
                "qr_code": log_item.qr_code,
                "zone_code": zone_code,
                "enabled": route_by_qr.get(log_item.qr_code).enabled
                if route_by_qr.get(log_item.qr_code)
                else None,
                "active_target": route_by_qr.get(log_item.qr_code).active_target
                if route_by_qr.get(log_item.qr_code)
                else None,
                "scans_total": 0,
                "sessions_started": 0,
                "conversion_rate": 0.0,
                "last_scan_at": None,
                "traffic_sources": {},
                "traffic_media": {},
                "_session_ids": set(),
            },
        )
        zone_row = per_zone.setdefault(
            zone_code,
            {
                "zone_code": zone_code,
                "qr_count": 0,
                "scans_total": 0,
                "sessions_started": 0,
                "conversion_rate": 0.0,
                "_session_ids": set(),
            },
        )
        qr_row["scans_total"] += 1
        qr_row["last_scan_at"] = log_item.created_at.isoformat()
        if log_item.session_id:
            qr_row["_session_ids"].add(log_item.session_id)
        if log_item.traffic_source:
            qr_row["traffic_sources"][log_item.traffic_source] = (
                qr_row["traffic_sources"].get(log_item.traffic_source, 0) + 1
            )
        if log_item.traffic_medium:
            qr_row["traffic_media"][log_item.traffic_medium] = (
                qr_row["traffic_media"].get(log_item.traffic_medium, 0) + 1
        )
        zone_row["scans_total"] += 1
        if log_item.session_id:
            zone_row["_session_ids"].add(log_item.session_id)

    for row in per_qr.values():
        scans_total = row["scans_total"]
        row["sessions_started"] = len(row.pop("_session_ids"))
        row["conversion_rate"] = (
            round(row["sessions_started"] / scans_total, 4) if scans_total else 0.0
        )
    for row in per_zone.values():
        scans_total = row["scans_total"]
        row["sessions_started"] = len(row.pop("_session_ids"))
        row["conversion_rate"] = (
            round(row["sessions_started"] / scans_total, 4) if scans_total else 0.0
        )

    return {
        "gateway_mode": current_gateway_mode_summary(db),
        "gateway_failover": current_gateway_failover_state(),
        "summary": {
            "qr_count": len(per_qr),
            "zone_count": len(per_zone),
            "scans_total": sum(item["scans_total"] for item in per_qr.values()),
            "sessions_started": sum(
                item["sessions_started"] for item in per_qr.values()
            ),
        },
        "by_qr": sorted(per_qr.values(), key=lambda item: item["qr_code"]),
        "by_zone": sorted(per_zone.values(), key=lambda item: item["zone_code"]),
    }


@app.get("/admin/referrals/summary")
def admin_referrals_summary(db: Session = Depends(get_session)) -> dict[str, Any]:
    links = db.exec(select(ReferralLink).order_by(ReferralLink.created_at.desc())).all()
    clicks = db.exec(select(ReferralClick).order_by(ReferralClick.created_at.desc())).all()
    per_link: list[dict[str, Any]] = []
    per_inviter: dict[str, dict[str, Any]] = {}
    clicks_by_link: dict[str, int] = {}
    conversions_by_link: dict[str, int] = {}

    for click in clicks:
        clicks_by_link[click.referral_link_id] = clicks_by_link.get(click.referral_link_id, 0) + 1
        if click.session_id:
            conversions_by_link[click.referral_link_id] = (
                conversions_by_link.get(click.referral_link_id, 0) + 1
            )

    for link in links:
        link_payload = referral_link_payload(link)
        per_link.append(link_payload)
        inviter_row = per_inviter.setdefault(
            link.inviter_session_id,
            {
                "inviter_session_id": link.inviter_session_id,
                "inviter_user_id": link.inviter_user_id,
                "referral_code": link.inviter_referral_code,
                "links_total": 0,
                "clicks_total": 0,
                "conversions_total": 0,
                "invite_to_entry_ratio": 0.0,
            },
        )
        inviter_row["links_total"] += 1
        inviter_row["clicks_total"] += link.click_count
        inviter_row["conversions_total"] += link.conversion_count

    for inviter_row in per_inviter.values():
        clicks_total = inviter_row["clicks_total"]
        inviter_row["invite_to_entry_ratio"] = (
            round(inviter_row["conversions_total"] / clicks_total, 4)
            if clicks_total
            else 0.0
        )

    clicks_total = sum(link.click_count for link in links)
    conversions_total = sum(link.conversion_count for link in links)

    return {
        "summary": {
            "links_total": len(links),
            "clicks_total": clicks_total,
            "conversions_total": conversions_total,
            "invite_to_entry_ratio": (
                round(conversions_total / clicks_total, 4) if clicks_total else 0.0
            ),
        },
        "by_link": per_link,
        "by_inviter_session": sorted(
            per_inviter.values(),
            key=lambda item: (
                -item["conversions_total"],
                -item["clicks_total"],
                item["inviter_session_id"],
            ),
        ),
        "recent_clicks": [referral_click_payload(click) for click in clicks[:100]],
        "consistency": {
            "clicks_by_link": clicks_by_link,
            "conversions_by_link": conversions_by_link,
        },
    }


@app.post("/admin/gateway/routes/{qr_code}/switch")
def admin_gateway_route_switch(
    qr_code: str,
    payload: AdminGatewayRouteSwitchRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("gateway-route-control"):
        try:
            route = switch_gateway_route_target(
                db,
                qr_code=qr_code,
                active_target=payload.active_target,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        create_audit(
            db,
            entity_type="gateway_route",
            entity_id=route.id,
            action="gateway_route_switched",
            payload={
                "qr_code": route.qr_code,
                "active_target": route.active_target,
                "active_target_url": (
                    route.backup_target_url
                    if route.active_target == GATEWAY_TARGET_BACKUP
                    else route.primary_target_url
                ),
            },
        )
        db.commit()
        return {"ok": True, "route": gateway_route_payload(route)}


@app.get("/admin/gateway/logs")
def admin_gateway_logs(
    qr_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 500)
    statement = select(GatewayAccessLog)
    if qr_code:
        try:
            normalized_qr_code = normalize_gateway_qr_code(qr_code)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        statement = statement.where(GatewayAccessLog.qr_code == normalized_qr_code)
    if status:
        statement = statement.where(GatewayAccessLog.status == status.strip().lower())
    logs = db.exec(
        statement.order_by(GatewayAccessLog.created_at.desc()).limit(safe_limit)
    ).all()
    return {
        "count": len(logs),
        "logs": [gateway_access_log_payload(item) for item in logs],
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
            "experiment_mode": normalize_experiment_mode(state.experiment_mode),
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
            "experiment_mode": normalize_experiment_mode(state.experiment_mode),
            "resumed_at": state.resumed_at.isoformat() if state.resumed_at else None,
            "prizes": prize_summary(db),
        }


@app.post("/admin/experiment/mode")
def admin_experiment_mode(
    payload: AdminExperimentModeRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    with distributed_lock("experiment-control"):
        state = set_experiment_mode(
            db,
            mode=payload.mode,
            actor=get_admin_actor(request),
            reason=payload.reason,
        )
        return {
            "ok": True,
            "experiment_status": state.experiment_status,
            "experiment_mode": normalize_experiment_mode(state.experiment_mode),
            "accepting_entries": not experiment_is_paused(state)
            and not experiment_mode_blocks_entries(state),
            "accepting_inflight_sessions": not experiment_is_paused(state)
            and not experiment_mode_blocks_inflight_actions(state),
            "updated_at": state.updated_at.isoformat(),
            "mode_changed_at": (
                state.experiment_mode_changed_at.isoformat()
                if state.experiment_mode_changed_at
                else None
            ),
            "mode_changed_by": state.experiment_mode_changed_by,
            "prizes": prize_summary(db),
        }


@app.post("/admin/panic")
def admin_panic(
    payload: AdminPanicRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    requested_mode = EXPERIMENT_MODE_CLOSING if payload.soft else payload.mode
    normalized_mode = normalize_experiment_mode(requested_mode)
    if normalized_mode not in {EXPERIMENT_MODE_CLOSING, EXPERIMENT_MODE_CLOSED}:
        raise HTTPException(status_code=400, detail="Modo de panic no valido")

    actor = get_admin_actor(request)
    with distributed_lock("experiment-control"):
        state = get_or_create_experiment_state(db)
        current_mode = normalize_experiment_mode(state.experiment_mode)
        target_mode = normalized_mode
        if current_mode == EXPERIMENT_MODE_CLOSED:
            target_mode = EXPERIMENT_MODE_CLOSED
        idempotent = current_mode == target_mode
        if not idempotent:
            state = set_experiment_mode(
                db,
                mode=target_mode,
                actor=actor,
                reason=payload.reason,
            )
            logger.warning(
                "experiment_panic",
                extra={
                    "structured_payload": {
                        "actor": actor,
                        "requested_mode": normalized_mode,
                        "applied_mode": normalize_experiment_mode(state.experiment_mode),
                        "reason": payload.reason,
                        "changed_at": (
                            state.experiment_mode_changed_at.isoformat()
                            if state.experiment_mode_changed_at
                            else None
                        ),
                    }
                },
            )
        return {
            "ok": True,
            "idempotent": idempotent,
            "experiment_status": state.experiment_status,
            "experiment_mode": normalize_experiment_mode(state.experiment_mode),
            "requested_mode": normalized_mode,
            "accepting_entries": not experiment_is_paused(state)
            and not experiment_mode_blocks_entries(state),
            "accepting_inflight_sessions": not experiment_is_paused(state)
            and not experiment_mode_blocks_inflight_actions(state),
            "activated_at": (
                state.experiment_mode_changed_at.isoformat()
                if state.experiment_mode_changed_at
                else state.updated_at.isoformat()
            ),
            "activated_by": state.experiment_mode_changed_by or actor,
            "reason": state.experiment_mode_reason,
            "prizes": prize_summary(db),
        }


@app.post("/admin/unpanic")
def admin_unpanic(
    payload: AdminExperimentControlRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    actor = get_admin_actor(request)
    with distributed_lock("experiment-control"):
        state = get_or_create_experiment_state(db)
        current_mode = normalize_experiment_mode(state.experiment_mode)
        idempotent = current_mode == EXPERIMENT_MODE_LIVE
        if not idempotent:
            state = set_experiment_mode(
                db,
                mode=EXPERIMENT_MODE_LIVE,
                actor=actor,
                reason=payload.reason,
            )
            logger.warning(
                "experiment_unpanic",
                extra={
                    "structured_payload": {
                        "actor": actor,
                        "previous_mode": current_mode,
                        "applied_mode": normalize_experiment_mode(state.experiment_mode),
                        "reason": payload.reason,
                        "changed_at": (
                            state.experiment_mode_changed_at.isoformat()
                            if state.experiment_mode_changed_at
                            else None
                        ),
                    }
                },
            )
        return {
            "ok": True,
            "idempotent": idempotent,
            "experiment_status": state.experiment_status,
            "experiment_mode": normalize_experiment_mode(state.experiment_mode),
            "accepting_entries": not experiment_is_paused(state)
            and not experiment_mode_blocks_entries(state),
            "accepting_inflight_sessions": not experiment_is_paused(state)
            and not experiment_mode_blocks_inflight_actions(state),
            "reactivated_at": (
                state.experiment_mode_changed_at.isoformat()
                if state.experiment_mode_changed_at
                else state.updated_at.isoformat()
            ),
            "reactivated_by": state.experiment_mode_changed_by or actor,
            "reason": state.experiment_mode_reason,
            "closure_logs_kept": True,
            "prizes": prize_summary(db),
        }


@app.post("/admin/system/reset")
def admin_system_reset(
    payload: AdminSystemResetRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> JSONResponse:
    actor = get_admin_actor(request)
    verify_admin_reset_passphrase(payload.passphrase)
    db.close()
    with distributed_lock("admin-system-reset"):
        result = perform_admin_system_reset(actor=actor, reason=payload.reason)
    return JSONResponse(
        content=result,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Sonar-Skip-Metrics": "1",
        },
    )


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
    return build_session_payload(
        db,
        record,
        payload_mode=SESSION_PAYLOAD_MODE_ANALYTICS,
    )


@app.get("/admin/exports", response_class=HTMLResponse)
def admin_exports(db: Session = Depends(get_session)) -> HTMLResponse:
    state = get_or_create_experiment_state(db)
    stats = dataset_export_stats(db)
    return HTMLResponse(exports_page_html(state, stats, prize_summary(db)))


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_session)) -> HTMLResponse:
    return HTMLResponse(dashboard_page_html(db))


@app.get("/admin/payments", response_class=HTMLResponse)
def admin_payments_page(db: Session = Depends(get_session)) -> HTMLResponse:
    return HTMLResponse(admin_payments_page_html(admin_payments_payload(db)))


@app.get("/admin/payments/live")
def admin_payments_live(db: Session = Depends(get_session)) -> JSONResponse:
    return JSONResponse(
        content=admin_payments_payload(db),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.post("/admin/payments/{payment_id}/mark-paid")
def admin_mark_payment_paid(
    payment_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> RedirectResponse:
    actor = get_admin_actor(request)
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    payout_request = db.exec(
        select(PayoutRequest).where(PayoutRequest.payment_id == payment.id)
    ).first()
    old_payment_status = payment.status
    old_request_status = payout_request.status if payout_request else None
    changed = False

    if payment.status != "paid":
        payment.status = "paid"
        payment.paid_at = utcnow()
        db.add(payment)
        changed = True

    if payout_request and payout_request.status != "processed":
        payout_request.status = "processed"
        payout_request.processed_at = utcnow()
        db.add(payout_request)
        changed = True

    if changed:
        create_audit(
            db,
            entity_type="payment",
            entity_id=payment.id,
            action="admin_payment_mark_paid",
            session_id=payment.session_id,
            old_state=old_payment_status,
            new_state=payment.status,
            payload={
                "actor": actor,
                "request_status_before": old_request_status,
                "request_status_after": payout_request.status if payout_request else None,
                "donation_requested": bool(
                    payout_request.donation_requested if payout_request else False
                ),
            },
        )
        logger.info(
            "admin_payment_mark_paid",
            extra={
                "structured_payload": {
                    "payment_id": payment.id,
                    "session_id": payment.session_id,
                    "actor": actor,
                    "old_status": old_payment_status,
                    "new_status": payment.status,
                    "request_old_status": old_request_status,
                    "request_new_status": payout_request.status if payout_request else None,
                }
            },
        )
        db.commit()

    return RedirectResponse(url="/admin/payments", status_code=303)


@app.get("/admin/metrics")
def admin_metrics(db: Session = Depends(get_session)) -> JSONResponse:
    payload = live_dashboard_payload(db, readiness_payload())
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/admin/dashboard/live")
def admin_dashboard_live(db: Session = Depends(get_session)) -> JSONResponse:
    payload = live_dashboard_payload(db, readiness_payload())
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/admin/metrics/experiment")
def admin_experiment_metrics(db: Session = Depends(get_session)) -> JSONResponse:
    payload = live_dashboard_payload(db, readiness_payload())
    return JSONResponse(
        content={
            "generated_at": payload["generated_at"],
            "readiness": payload["readiness"],
            "windows": payload["windows"],
            "experiment_metrics": payload["experiment_metrics"],
        },
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/admin/metrics/experiment/timeseries")
def admin_experiment_metrics_timeseries(
    db: Session = Depends(get_session),
) -> JSONResponse:
    payload = live_dashboard_payload(db, readiness_payload())
    experiment_metrics = payload["experiment_metrics"]
    return JSONResponse(
        content={
            "generated_at": payload["generated_at"],
            "bucket_minutes": experiment_metrics["timeseries_bucket_minutes"],
            "timeseries": experiment_metrics["timeseries"],
        },
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/admin/live", response_class=HTMLResponse)
def admin_live() -> HTMLResponse:
    return HTMLResponse(live_dashboard_page_html_v3())


def export_dataset_csv_response(
    dataset_name: str,
    db: Session,
) -> Response:
    rows = dataset_rows(db, dataset_name)
    csv_bytes = rows_to_csv_bytes(rows, fieldnames=dataset_csv_fieldnames(dataset_name))
    filename = (
        analysis_ready_export_filename()
        if dataset_name == ANALYSIS_READY_DATASET_NAME
        else participant_analysis_export_filename()
        if dataset_name == ANALYSIS_READY_EXTENDED_DATASET_NAME
        else export_filename(dataset_name, "csv")
    )
    response_headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if dataset_name == ANALYSIS_READY_DATASET_NAME:
        response_headers["X-Dataset-Version"] = ANALYSIS_READY_DATASET_VERSION
    if dataset_name == ANALYSIS_READY_EXTENDED_DATASET_NAME:
        response_headers["X-Dataset-Version"] = ANALYSIS_READY_EXTENDED_DATASET_VERSION
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers=response_headers,
    )


@app.get("/admin/export/analysis-ready.csv")
def admin_export_analysis_ready_csv(db: Session = Depends(get_session)) -> Response:
    return export_dataset_csv_response(ANALYSIS_READY_DATASET_NAME, db)


@app.get("/admin/export/participant-analysis.csv")
def admin_export_participant_analysis_csv(db: Session = Depends(get_session)) -> Response:
    return export_dataset_csv_response(ANALYSIS_READY_EXTENDED_DATASET_NAME, db)


@app.get("/admin/export/{dataset_name}.csv")
def admin_export_dataset_csv(
    dataset_name: str,
    db: Session = Depends(get_session),
) -> Response:
    return export_dataset_csv_response(dataset_name, db)


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
