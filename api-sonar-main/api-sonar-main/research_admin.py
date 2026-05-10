import csv
import hashlib
from html import escape
import io
import json
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from experiment import (
    CAMPAIGN_CODE,
    CONSENT_VERSION,
    CONTROL_TREATMENT_KEY,
    DECK_VERSION,
    DEPLOYMENT_CONTEXT,
    ENVIRONMENT_LABEL,
    EXPERIMENT_VERSION,
    LEXICON_VERSION,
    PAYMENT_VERSION,
    PHASE_1_MAIN,
    QUALITY_THRESHOLDS,
    SCHEMA_VERSION,
    SITE_CODE,
    TELEMETRY_VERSION,
    TREATMENT_KEYS,
    UI_VERSION,
    public_support,
)
from models import (
    AuditEvent,
    Claim,
    ConsentRecord,
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
    ReferralClick,
    ReferralLink,
    ResultDeck,
    ResultDeckCard,
    SessionClientContext,
    SessionRecord,
    SnapshotRecord,
    ScreenSpell,
    TelemetryEvent,
    Throw,
    TreatmentDeck,
    TreatmentDeckCard,
    User,
)
from runtime import get_counter_group_snapshot, get_http_metrics_snapshot
from settings import settings

logger = logging.getLogger("sonar")

OPTIONAL_EXPORT_MODEL_TABLES = frozenset(
    {
        getattr(ScreenSpell, "__tablename__", "screen_spells"),
        getattr(SessionClientContext, "__tablename__", "session_client_contexts"),
        getattr(TelemetryEvent, "__tablename__", "telemetry_events"),
        getattr(FraudFlag, "__tablename__", "fraud_flags"),
        getattr(OperationalNote, "__tablename__", "operational_notes"),
        getattr(InterestSignup, "__tablename__", "interest_signups"),
    }
)


DATASET_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "sessions": {
        "category": "analytic",
        "description": "Sesion analitica derivada con tratamiento, resultado y pago reconstruibles sin ambiguedad.",
        "sensitivity": "baja",
    },
    "throws": {
        "category": "analytic",
        "description": "Tiradas servidas por sesion e intento, incluyendo primera tirada balanceada y rerolls reproducibles.",
        "sensitivity": "baja",
    },
    "claims": {
        "category": "analytic",
        "description": "Claims finales con snapshot del mensaje mostrado al participante.",
        "sensitivity": "baja",
    },
    "referrals": {
        "category": "analytic",
        "description": "Red de referidos, QR y procedencia de WhatsApp.",
        "sensitivity": "baja",
    },
    "treatment_decks": {
        "category": "analytic",
        "description": "Estado de los mazos de tratamientos de 62 cartas.",
        "sensitivity": "baja",
    },
    "treatment_deck_cards": {
        "category": "analytic",
        "description": "Cartas individuales de tratamiento y su asignacion por sesion.",
        "sensitivity": "baja",
    },
    "result_decks": {
        "category": "analytic",
        "description": "Estado de los mazos de resultados de 24 cartas estratificados por tratamiento.",
        "sensitivity": "baja",
    },
    "result_deck_cards": {
        "category": "analytic",
        "description": "Cartas individuales de resultado para la primera tirada, balanceadas por tratamiento.",
        "sensitivity": "baja",
    },
    "payment_decks": {
        "category": "analytic",
        "description": "Estado de los mazos de pago de 100 cartas con 1 ganador exacto.",
        "sensitivity": "baja",
    },
    "payment_deck_cards": {
        "category": "analytic",
        "description": "Cartas individuales de elegibilidad de pago asignadas por sesion.",
        "sensitivity": "baja",
    },
    "quality_flags": {
        "category": "analytic",
        "description": "Flags de calidad explotados por sesion.",
        "sensitivity": "baja",
    },
    "consent_records": {
        "category": "analytic",
        "description": "Consentimientos, idioma y paneles eticos abiertos.",
        "sensitivity": "media",
    },
    "snapshot_records": {
        "category": "analytic",
        "description": "Snapshot auditable de lo que vio y recibio el participante.",
        "sensitivity": "media",
    },
    "payments_admin": {
        "category": "administrative",
        "description": "Pagos, codigos de cobro y solicitudes administrativas de Bizum o donacion.",
        "sensitivity": "alta",
    },
    "interest_signups": {
        "category": "administrative",
        "description": "Emails voluntarios para futuras olas si el experimento esta detenido.",
        "sensitivity": "alta",
    },
    "telemetry": {
        "category": "operational",
        "description": "Telemetria cruda de interaccion y errores.",
        "sensitivity": "media",
    },
    "technical_events": {
        "category": "operational",
        "description": "Errores, latencias, retries y eventos tecnicos.",
        "sensitivity": "media",
    },
    "screen_events": {
        "category": "operational",
        "description": "Spells agregados por pantalla con tiempos visibles y clicks.",
        "sensitivity": "media",
    },
    "client_contexts": {
        "category": "operational",
        "description": "Contexto de navegador, dispositivo y viewport por sesion.",
        "sensitivity": "media",
    },
    "fraud_flags": {
        "category": "operational",
        "description": "Flags antifraude generados por el backend.",
        "sensitivity": "media",
    },
    "audit_events": {
        "category": "operational",
        "description": "Trazabilidad de acciones criticas, asignacion, claims y pagos.",
        "sensitivity": "media",
    },
    "operational_notes": {
        "category": "operational",
        "description": "Notas operativas activadas durante el trabajo de campo.",
        "sensitivity": "media",
    },
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_doc_or_default(filename: str, default_content: str) -> str:
    path = project_root() / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return default_content


def isoformat_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def safe_ms_delta(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[int]:
    if later is None or earlier is None:
        return None
    return int((later - earlier).total_seconds() * 1000)


def mean(values: list[int | float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


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


def is_missing_relation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "no such table",
            "no such column",
            "does not exist",
            "undefined table",
            "undefined column",
            "unknown table",
            "unknown column",
        )
    )


def export_error_summary(exc: Exception) -> str:
    if is_missing_relation_error(exc):
        return "Tabla legacy no disponible en este despliegue."
    return str(exc).splitlines()[0].strip() or exc.__class__.__name__


def load_model_rows(
    db: Session,
    model: Any,
    *,
    order_by: Any = None,
    missing_ok: bool = False,
    export_name: Optional[str] = None,
) -> list[Any]:
    statement = select(model)
    if order_by is not None:
        if isinstance(order_by, (list, tuple)):
            statement = statement.order_by(*order_by)
        else:
            statement = statement.order_by(order_by)
    try:
        return db.exec(statement).all()
    except SQLAlchemyError as exc:
        table_name = getattr(model, "__tablename__", model.__name__)
        if (
            missing_ok
            and table_name in OPTIONAL_EXPORT_MODEL_TABLES
            and is_missing_relation_error(exc)
        ):
            logger.warning(
                "admin_export_optional_table_missing",
                extra={
                    "structured_payload": {
                        "dataset": export_name,
                        "table_name": table_name,
                        "error": export_error_summary(exc),
                    }
                },
            )
            return []
        raise


def load_lookup_table(
    db: Session,
    model: Any,
    key_field: str,
    *,
    missing_ok: bool = False,
    export_name: Optional[str] = None,
) -> dict[Any, Any]:
    rows = load_model_rows(
        db,
        model,
        missing_ok=missing_ok,
        export_name=export_name,
    )
    return {getattr(item, key_field): item for item in rows}


def build_referral_depth_map(records: list[SessionRecord]) -> dict[str, int]:
    by_id = {record.id: record for record in records}
    memo: dict[str, int] = {}

    def depth_for(session_id: str) -> int:
        if session_id in memo:
            return memo[session_id]
        record = by_id[session_id]
        if not record.invited_by_session_id or record.invited_by_session_id not in by_id:
            memo[session_id] = 0
            return 0
        memo[session_id] = depth_for(record.invited_by_session_id) + 1
        return memo[session_id]

    for record in records:
        depth_for(record.id)
    return memo


def deck_summary_rows(
    deck_rows: list[Any],
    deck_cards: list[Any],
    *,
    deck_kind: str,
) -> list[dict[str, Any]]:
    counts_by_deck: dict[str, int] = {}
    for card in deck_cards:
        if getattr(card, "assigned_session_id", None):
            counts_by_deck[card.deck_id] = counts_by_deck.get(card.deck_id, 0) + 1
    rows: list[dict[str, Any]] = []
    for deck in deck_rows:
        assigned_count = counts_by_deck.get(deck.id, 0)
        rows.append(
            {
                f"{deck_kind}_deck_id": deck.id,
                "deck_index": deck.deck_index,
                "deck_seed": deck.deck_seed,
                "treatment_key": getattr(deck, "treatment_key", None),
                "treatment_cycle_index": getattr(deck, "treatment_cycle_index", None),
                "status": deck.status,
                "card_count": deck.card_count,
                "assigned_count": assigned_count,
                "remaining_count": max(deck.card_count - assigned_count, 0),
                "created_at": isoformat_or_none(deck.created_at),
                "closed_at": isoformat_or_none(deck.closed_at),
            }
        )
    return rows


def analytic_sessions_rows(db: Session) -> list[dict[str, Any]]:
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    throws = db.exec(select(Throw).order_by(Throw.session_id, Throw.attempt_index)).all()
    claims_by_session = load_lookup_table(db, Claim, "session_id")
    payments_by_session = load_lookup_table(db, Payment, "session_id")
    consent_by_session = load_lookup_table(db, ConsentRecord, "session_id")
    snapshot_by_session = load_lookup_table(db, SnapshotRecord, "session_id")
    client_context_by_session = load_lookup_table(
        db,
        SessionClientContext,
        "session_id",
        missing_ok=True,
        export_name="sessions",
    )
    treatment_decks = load_lookup_table(db, TreatmentDeck, "id")
    result_decks = load_lookup_table(db, ResultDeck, "id")
    payment_decks = load_lookup_table(db, PaymentDeck, "id")
    screen_spells = load_model_rows(
        db,
        ScreenSpell,
        order_by=(ScreenSpell.session_id, ScreenSpell.entered_server_ts),
        missing_ok=True,
        export_name="sessions",
    )

    seen_by_session: dict[str, list[int]] = {}
    screen_metrics_by_session: dict[str, dict[str, int]] = {}
    for throw in throws:
        seen_by_session.setdefault(throw.session_id, []).append(throw.result_value)
    for spell in screen_spells:
        key_prefix = spell.screen_name
        bucket = screen_metrics_by_session.setdefault(spell.session_id, {})
        for metric_key in [
            "visible_ms",
            "hidden_ms",
            "blur_ms",
            "click_count",
            "primary_click_count",
            "secondary_click_count",
        ]:
            bucket[f"{key_prefix}_{metric_key}"] = bucket.get(
                f"{key_prefix}_{metric_key}",
                0,
            ) + int(getattr(spell, metric_key) or 0)
        for first_metric_key in ["first_click_ms", "primary_cta_ms", "secondary_cta_ms"]:
            metric_value = getattr(spell, first_metric_key)
            if metric_value is None:
                continue
            bucket_key = f"{key_prefix}_{first_metric_key}"
            current_value = bucket.get(bucket_key)
            bucket[bucket_key] = (
                int(metric_value)
                if current_value is None
                else min(int(current_value), int(metric_value))
            )
    referral_depths = build_referral_depth_map(sessions)

    rows: list[dict[str, Any]] = []
    for record in sessions:
        claim = claims_by_session.get(record.id)
        consent = consent_by_session.get(record.id)
        snapshot = snapshot_by_session.get(record.id)
        client_context = client_context_by_session.get(record.id)
        treatment_deck = treatment_decks.get(record.treatment_deck_id)
        result_deck = result_decks.get(record.result_deck_id)
        payment_deck = payment_decks.get(record.payment_deck_id)
        seen_values = seen_by_session.get(record.id, [])
        screen_metrics = screen_metrics_by_session.get(record.id, {})
        consent_panel_total_ms = 0
        if consent and consent.info_panel_durations_json:
            try:
                consent_panel_total_ms = sum(
                    int(value or 0)
                    for value in json.loads(consent.info_panel_durations_json).values()
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                consent_panel_total_ms = 0
        reported_value = claim.reported_value if claim else record.reported_value
        true_first_result = claim.true_first_result if claim else record.first_result_value
        rows.append(
            {
                "session_id": record.id,
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
                "deployment_context": record.deployment_context,
                "site_code": record.site_code,
                "campaign_code": record.campaign_code,
                "environment_label": record.environment_label,
                "language_at_access": record.language_at_access,
                "language_at_claim": record.language_at_claim,
                "language_changed_during_session": record.language_changed_during_session,
                "treatment_key": record.treatment_key,
                "treatment_type": record.treatment_type,
                "treatment_family": record.treatment_family,
                "is_control": int(record.treatment_key == CONTROL_TREATMENT_KEY),
                "displayed_count_target": record.report_snapshot_count_target
                if record.report_snapshot_count_target is not None
                else record.displayed_count_target,
                "displayed_denominator": record.report_snapshot_denominator
                if record.report_snapshot_denominator is not None
                else record.displayed_denominator,
                "norm_target_value": record.norm_target_value,
                "displayed_message_version": record.report_snapshot_message_version,
                "displayed_message_text": snapshot.displayed_message_text
                if snapshot
                else record.report_snapshot_message,
                "position_index": record.position_index,
                "root_id": record.root_id,
                "series_id": record.series_id,
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
                "payout_eligible": int(record.selected_for_payment),
                "reported_value": reported_value,
                "true_first_result": true_first_result,
                "reported_six": int(reported_value == 6) if reported_value is not None else None,
                "is_honest": record.is_honest,
                "reroll_count": record.reroll_count,
                "used_any_reroll": int(record.reroll_count > 0),
                "last_seen_value": record.last_seen_value,
                "max_seen_value": record.max_seen_value,
                "reported_matches_first": (
                    int(reported_value == true_first_result)
                    if reported_value is not None and true_first_result is not None
                    else None
                ),
                "reported_matches_last": (
                    int(reported_value == record.last_seen_value)
                    if reported_value is not None and record.last_seen_value is not None
                    else None
                ),
                "reported_matches_any_seen": (
                    int(reported_value in seen_values) if reported_value is not None else None
                ),
                "crowd_prediction_value": claim.crowd_prediction_value if claim else None,
                "crowd_prediction_submitted_at": (
                    isoformat_or_none(claim.crowd_prediction_submitted_at)
                    if claim
                    else None
                ),
                "social_recall_count": claim.social_recall_count if claim else None,
                "social_recall_correct": claim.social_recall_correct if claim else None,
                "social_recall_submitted_at": (
                    isoformat_or_none(claim.social_recall_submitted_at)
                    if claim
                    else None
                ),
                "report_rt_ms": (
                    claim.reaction_ms
                    if claim and claim.reaction_ms is not None
                    else safe_ms_delta(record.claim_submitted_at, record.report_prepared_at)
                ),
                "game_decision_rt_ms": safe_ms_delta(record.report_prepared_at, record.first_roll_at),
                "total_session_ms": safe_ms_delta(record.completed_at, record.created_at),
                "landing_visible_ms": consent.landing_visible_ms if consent else None,
                "landing_to_start_ms": screen_metrics.get("landing_primary_cta_ms")
                if screen_metrics.get("landing_primary_cta_ms") is not None
                else screen_metrics.get("landing_first_click_ms"),
                "consent_total_ms": (
                    int(consent.landing_visible_ms or 0) + consent_panel_total_ms
                    if consent
                    else None
                ),
                "referral_code": record.referral_code,
                "invited_by_session_id": record.invited_by_session_id,
                "invited_by_referral_code": record.invited_by_referral_code,
                "referral_source": record.referral_source,
                "referral_medium": record.referral_medium,
                "referral_campaign": record.referral_campaign,
                "referral_link_id": record.referral_link_id,
                "qr_entry_code": record.qr_entry_code,
                "referral_arrived_at": isoformat_or_none(record.referral_arrived_at),
                "referral_depth": referral_depths.get(record.id, 0),
                "operational_note_id": record.operational_note_id,
                "operational_note_text": record.operational_note_text,
                "browser_family": client_context.browser_family if client_context else None,
                "browser_version": client_context.browser_version if client_context else None,
                "os_family": client_context.os_family if client_context else None,
                "os_version": client_context.os_version if client_context else None,
                "device_type": client_context.device_type if client_context else None,
                "platform": client_context.platform if client_context else None,
                "language_browser": client_context.language_browser if client_context else None,
                "screen_width": client_context.screen_width if client_context else None,
                "screen_height": client_context.screen_height if client_context else None,
                "viewport_width": client_context.viewport_width if client_context else None,
                "viewport_height": client_context.viewport_height if client_context else None,
                "device_pixel_ratio": client_context.device_pixel_ratio if client_context else None,
                "orientation": client_context.orientation if client_context else None,
                "touch_capable": client_context.touch_capable if client_context else None,
                "hardware_concurrency": client_context.hardware_concurrency if client_context else None,
                "max_touch_points": client_context.max_touch_points if client_context else None,
                "color_scheme_preference": client_context.color_scheme_preference if client_context else None,
                "online_status": client_context.online_status if client_context else None,
                "connection_type": client_context.connection_type if client_context else None,
                "estimated_downlink": client_context.estimated_downlink if client_context else None,
                "estimated_rtt": client_context.estimated_rtt if client_context else None,
                "timezone_offset_minutes": client_context.timezone_offset_minutes if client_context else None,
                "instructions_visible_ms": screen_metrics.get("instructions_visible_ms"),
                "comprehension_visible_ms": screen_metrics.get("comprehension_visible_ms"),
                "game_visible_ms": screen_metrics.get("game_visible_ms"),
                "report_visible_ms": screen_metrics.get("report_visible_ms"),
                "exit_visible_ms": screen_metrics.get("exit_visible_ms"),
                "click_count_total": record.click_count_total,
                "click_count_by_screen_json": json.dumps(screen_metrics, ensure_ascii=False),
                "focus_loss_pre_claim": int(record.blur_count > 0),
                "multiple_focus_loss": int(record.blur_count > 1),
                "reload_count": record.refresh_count,
                "resume_count": record.resume_count,
                "network_error_count": record.network_error_count,
                "retry_count": record.retry_count,
                "consent_panels_opened_count": consent.info_panel_open_count if consent else 0,
                "screen_changes_count": record.screen_changes_count,
                "language_change_count": record.language_change_count,
                "state": record.state,
                "screen_cursor": record.screen_cursor,
                "is_valid_completed": record.is_valid_completed,
                "created_at": isoformat_or_none(record.created_at),
                "completed_at": isoformat_or_none(record.completed_at),
            }
        )
    return rows


def throws_rows(db: Session) -> list[dict[str, Any]]:
    sessions = load_lookup_table(db, SessionRecord, "id")
    throws = db.exec(select(Throw).order_by(Throw.delivered_at)).all()
    return [
        {
            "throw_id": throw.id,
            "session_id": throw.session_id,
            "experiment_phase": sessions[throw.session_id].experiment_phase,
            "treatment_key": sessions[throw.session_id].treatment_key,
            "treatment_type": sessions[throw.session_id].treatment_type,
            "attempt_index": throw.attempt_index,
            "result_value": throw.result_value,
            "result_source": "result_deck" if throw.attempt_index == 1 else "reroll_rng",
            "result_deck_id": sessions[throw.session_id].result_deck_id if throw.attempt_index == 1 else None,
            "result_card_position": sessions[throw.session_id].result_card_position if throw.attempt_index == 1 else None,
            "reaction_ms": throw.reaction_ms,
            "delivered_at": isoformat_or_none(throw.delivered_at),
        }
        for throw in throws
    ]


def claims_rows(db: Session) -> list[dict[str, Any]]:
    claims = db.exec(select(Claim).order_by(Claim.submitted_at)).all()
    return [
        {
            "claim_id": claim.id,
            "session_id": claim.session_id,
            "experiment_phase": claim.experiment_phase,
            "phase_activation_status": claim.phase_activation_status,
            "treatment_version": claim.treatment_version,
            "allocation_version": claim.allocation_version,
            "treatment_family": claim.treatment_family,
            "norm_target_value": claim.norm_target_value,
            "position_index": claim.position_index,
            "true_first_result": claim.true_first_result,
            "reported_value": claim.reported_value,
            "is_honest": claim.is_honest,
            "reroll_count": claim.reroll_count,
            "displayed_treatment_key": claim.displayed_treatment_key,
            "is_control": int(claim.displayed_treatment_key == CONTROL_TREATMENT_KEY),
            "displayed_count_target": claim.displayed_count_target,
            "displayed_denominator": claim.displayed_denominator,
            "displayed_target_value": claim.displayed_target_value,
            "displayed_message": claim.displayed_message,
            "displayed_message_version": claim.displayed_message_version,
            "operational_note_id": claim.operational_note_id,
            "operational_note_text": claim.operational_note_text,
            "max_seen_value": claim.max_seen_value,
            "last_seen_value": claim.last_seen_value,
            "matches_last_seen": claim.matches_last_seen,
            "matches_any_seen": claim.matches_any_seen,
            "crowd_prediction_value": claim.crowd_prediction_value,
            "crowd_prediction_submitted_at": isoformat_or_none(
                claim.crowd_prediction_submitted_at
            ),
            "social_recall_count": claim.social_recall_count,
            "social_recall_correct": claim.social_recall_correct,
            "social_recall_submitted_at": isoformat_or_none(
                claim.social_recall_submitted_at
            ),
            "reaction_ms": claim.reaction_ms,
            "submitted_at": isoformat_or_none(claim.submitted_at),
        }
        for claim in claims
    ]


def payments_admin_rows(db: Session) -> list[dict[str, Any]]:
    payments = db.exec(select(Payment).order_by(Payment.created_at)).all()
    payout_requests_by_payment = load_lookup_table(db, PayoutRequest, "payment_id")
    session_map = load_lookup_table(db, SessionRecord, "id")
    rows: list[dict[str, Any]] = []
    for payment in payments:
        request = payout_requests_by_payment.get(payment.id)
        session_record = session_map.get(payment.session_id)
        rows.append(
            {
                "payment_id": payment.id,
                "session_id": payment.session_id,
                "experiment_phase": session_record.experiment_phase if session_record else None,
                "treatment_key": session_record.treatment_key if session_record else None,
                "payment_deck_id": session_record.payment_deck_id if session_record else None,
                "payment_card_position": session_record.payment_card_position if session_record else None,
                "eligible": payment.eligible,
                "amount_cents": payment.amount_cents,
                "amount_eur": int(payment.amount_cents / 100),
                "status": payment.status,
                "payout_reference": payment.payout_reference,
                "operational_note_id": payment.operational_note_id,
                "operational_note_text": payment.operational_note_text,
                "requested_phone": request.requested_phone if request else None,
                "donation_requested": request.donation_requested if request else None,
                "request_language": request.language_used if request else None,
                "request_message_text": request.message_text if request else None,
                "request_operational_note_id": request.operational_note_id if request else None,
                "request_operational_note_text": request.operational_note_text if request else None,
                "request_created_at": isoformat_or_none(request.created_at) if request else None,
                "created_at": isoformat_or_none(payment.created_at),
                "paid_at": isoformat_or_none(payment.paid_at),
            }
        )
    return rows


def telemetry_rows(db: Session) -> list[dict[str, Any]]:
    events = load_model_rows(
        db,
        TelemetryEvent,
        order_by=TelemetryEvent.server_ts,
        missing_ok=True,
        export_name="telemetry",
    )
    session_map = load_lookup_table(db, SessionRecord, "id")
    return [
        {
            "telemetry_id": event.id,
            "session_id": event.session_id,
            "experiment_phase": session_map[event.session_id].experiment_phase
            if event.session_id in session_map
            else None,
            "treatment_key": session_map[event.session_id].treatment_key
            if event.session_id in session_map
            else None,
            "event_type": event.event_type,
            "event_name": event.event_name,
            "screen_name": event.screen_name,
            "client_ts": event.client_ts,
            "event_sequence_number": event.event_sequence_number,
            "timezone_offset_minutes": event.timezone_offset_minutes,
            "client_clock_skew_estimate_ms": event.client_clock_skew_estimate_ms,
            "duration_ms": event.duration_ms,
            "value": event.value,
            "app_language": event.app_language,
            "browser_language": event.browser_language,
            "spell_id": event.spell_id,
            "interaction_target": event.interaction_target,
            "interaction_role": event.interaction_role,
            "cta_kind": event.cta_kind,
            "endpoint_name": event.endpoint_name,
            "request_method": event.request_method,
            "status_code": event.status_code,
            "latency_ms": event.latency_ms,
            "attempt_number": event.attempt_number,
            "is_retry": event.is_retry,
            "error_name": event.error_name,
            "network_status": event.network_status,
            "visibility_state": event.visibility_state,
            "operational_note_id": event.operational_note_id,
            "operational_note_text": event.operational_note_text,
            "payload_json": event.payload_json,
            "server_ts": isoformat_or_none(event.server_ts),
        }
        for event in events
    ]


def technical_events_rows(db: Session) -> list[dict[str, Any]]:
    events = load_model_rows(
        db,
        TelemetryEvent,
        order_by=TelemetryEvent.server_ts,
        missing_ok=True,
        export_name="technical_events",
    )
    session_map = load_lookup_table(db, SessionRecord, "id")
    technical_events = [
        event
        for event in events
        if event.event_type in {"error", "network", "viewport", "lifecycle"}
        or event.endpoint_name
        or event.status_code is not None
        or event.is_retry
    ]
    return [
        {
            "telemetry_id": event.id,
            "session_id": event.session_id,
            "experiment_phase": session_map[event.session_id].experiment_phase
            if event.session_id in session_map
            else None,
            "event_type": event.event_type,
            "event_name": event.event_name,
            "screen_name": event.screen_name,
            "endpoint_name": event.endpoint_name,
            "request_method": event.request_method,
            "status_code": event.status_code,
            "latency_ms": event.latency_ms,
            "attempt_number": event.attempt_number,
            "is_retry": event.is_retry,
            "error_name": event.error_name,
            "network_status": event.network_status,
            "operational_note_id": event.operational_note_id,
            "operational_note_text": event.operational_note_text,
            "payload_json": event.payload_json,
            "server_ts": isoformat_or_none(event.server_ts),
        }
        for event in technical_events
    ]


def screen_events_rows(db: Session) -> list[dict[str, Any]]:
    spells = load_model_rows(
        db,
        ScreenSpell,
        order_by=ScreenSpell.entered_server_ts,
        missing_ok=True,
        export_name="screen_events",
    )
    session_map = load_lookup_table(db, SessionRecord, "id")
    return [
        {
            "session_id": spell.session_id,
            "spell_id": spell.spell_id,
            "screen_name": spell.screen_name,
            "entry_origin": spell.entry_origin,
            "entered_client_ts": spell.entered_client_ts,
            "entered_server_ts": isoformat_or_none(spell.entered_server_ts),
            "exited_client_ts": spell.exited_client_ts,
            "exited_server_ts": isoformat_or_none(spell.exited_server_ts),
            "duration_total_ms": spell.duration_total_ms,
            "visible_ms": spell.visible_ms,
            "hidden_ms": spell.hidden_ms,
            "blur_ms": spell.blur_ms,
            "focus_change_count": spell.focus_change_count,
            "visibility_change_count": spell.visibility_change_count,
            "click_count": spell.click_count,
            "primary_click_count": spell.primary_click_count,
            "secondary_click_count": spell.secondary_click_count,
            "first_click_ms": spell.first_click_ms,
            "primary_cta_ms": spell.primary_cta_ms,
            "secondary_cta_ms": spell.secondary_cta_ms,
            "first_click_target": spell.first_click_target,
            "click_targets_json": spell.click_targets_json,
            "entered_via_resume": spell.entered_via_resume,
            "language_at_entry": spell.language_at_entry,
            "language_at_exit": spell.language_at_exit,
            "language_changed_during_spell": spell.language_changed_during_spell,
            "event_sequence_start": spell.event_sequence_start,
            "event_sequence_end": spell.event_sequence_end,
            "operational_note_id": session_map[spell.session_id].operational_note_id
            if spell.session_id in session_map
            else None,
            "operational_note_text": session_map[spell.session_id].operational_note_text
            if spell.session_id in session_map
            else None,
        }
        for spell in spells
    ]


def client_contexts_rows(db: Session) -> list[dict[str, Any]]:
    contexts = load_model_rows(
        db,
        SessionClientContext,
        order_by=SessionClientContext.captured_at,
        missing_ok=True,
        export_name="client_contexts",
    )
    return [
        {
            "client_context_id": context.id,
            "session_id": context.session_id,
            "user_agent_hash": context.user_agent_hash,
            "browser_family": context.browser_family,
            "browser_version": context.browser_version,
            "os_family": context.os_family,
            "os_version": context.os_version,
            "device_type": context.device_type,
            "platform": context.platform,
            "language_browser": context.language_browser,
            "language_app_selected": context.language_app_selected,
            "screen_width": context.screen_width,
            "screen_height": context.screen_height,
            "viewport_width": context.viewport_width,
            "viewport_height": context.viewport_height,
            "device_pixel_ratio": context.device_pixel_ratio,
            "orientation": context.orientation,
            "touch_capable": context.touch_capable,
            "hardware_concurrency": context.hardware_concurrency,
            "max_touch_points": context.max_touch_points,
            "color_scheme_preference": context.color_scheme_preference,
            "online_status": context.online_status,
            "connection_type": context.connection_type,
            "estimated_downlink": context.estimated_downlink,
            "estimated_rtt": context.estimated_rtt,
            "timezone_offset_minutes": context.timezone_offset_minutes,
            "context_json": context.context_json,
            "captured_at": isoformat_or_none(context.captured_at),
            "updated_at": isoformat_or_none(context.updated_at),
        }
        for context in contexts
    ]


def referrals_rows(db: Session) -> list[dict[str, Any]]:
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    depths = build_referral_depth_map(sessions)
    return [
        {
            "session_id": record.id,
            "referral_code": record.referral_code,
            "invited_by_session_id": record.invited_by_session_id,
            "invited_by_referral_code": record.invited_by_referral_code,
            "referral_source": record.referral_source,
            "referral_medium": record.referral_medium,
            "referral_campaign": record.referral_campaign,
            "referral_link_id": record.referral_link_id,
            "qr_entry_code": record.qr_entry_code,
            "referral_landing_path": record.referral_landing_path,
            "referral_arrived_at": isoformat_or_none(record.referral_arrived_at),
            "referral_depth": depths.get(record.id, 0),
            "operational_note_id": record.operational_note_id,
            "operational_note_text": record.operational_note_text,
            "experiment_phase": record.experiment_phase,
            "treatment_key": record.treatment_key,
            "created_at": isoformat_or_none(record.created_at),
        }
        for record in sessions
    ]


def treatment_decks_rows(db: Session) -> list[dict[str, Any]]:
    decks = db.exec(select(TreatmentDeck).order_by(TreatmentDeck.deck_index)).all()
    cards = db.exec(select(TreatmentDeckCard)).all()
    rows = deck_summary_rows(decks, cards, deck_kind="treatment")
    for row, deck in zip(rows, decks):
        row["legacy_root_id"] = deck.legacy_root_id
    return rows


def treatment_deck_cards_rows(db: Session) -> list[dict[str, Any]]:
    decks = load_lookup_table(db, TreatmentDeck, "id")
    cards = db.exec(
        select(TreatmentDeckCard).order_by(TreatmentDeckCard.deck_id, TreatmentDeckCard.card_position)
    ).all()
    return [
        {
            "deck_id": card.deck_id,
            "deck_index": decks[card.deck_id].deck_index if card.deck_id in decks else None,
            "card_position": card.card_position,
            "treatment_key": card.treatment_key,
            "legacy_series_id": card.legacy_series_id,
            "assigned_session_id": card.assigned_session_id,
            "assigned_at": isoformat_or_none(card.assigned_at),
        }
        for card in cards
    ]


def result_decks_rows(db: Session) -> list[dict[str, Any]]:
    decks = db.exec(select(ResultDeck).order_by(ResultDeck.deck_index)).all()
    cards = db.exec(select(ResultDeckCard)).all()
    return deck_summary_rows(decks, cards, deck_kind="result")


def result_deck_cards_rows(db: Session) -> list[dict[str, Any]]:
    decks = load_lookup_table(db, ResultDeck, "id")
    cards = db.exec(
        select(ResultDeckCard).order_by(ResultDeckCard.deck_id, ResultDeckCard.card_position)
    ).all()
    return [
        {
            "deck_id": card.deck_id,
            "deck_index": decks[card.deck_id].deck_index if card.deck_id in decks else None,
            "treatment_key": (
                decks[card.deck_id].treatment_key if card.deck_id in decks else None
            ),
            "treatment_cycle_index": (
                decks[card.deck_id].treatment_cycle_index
                if card.deck_id in decks
                else None
            ),
            "card_position": card.card_position,
            "result_value": card.result_value,
            "assigned_session_id": card.assigned_session_id,
            "assigned_at": isoformat_or_none(card.assigned_at),
        }
        for card in cards
    ]


def payment_decks_rows(db: Session) -> list[dict[str, Any]]:
    decks = db.exec(select(PaymentDeck).order_by(PaymentDeck.deck_index)).all()
    cards = db.exec(select(PaymentDeckCard)).all()
    return deck_summary_rows(decks, cards, deck_kind="payment")


def payment_deck_cards_rows(db: Session) -> list[dict[str, Any]]:
    decks = load_lookup_table(db, PaymentDeck, "id")
    cards = db.exec(
        select(PaymentDeckCard).order_by(PaymentDeckCard.deck_id, PaymentDeckCard.card_position)
    ).all()
    return [
        {
            "deck_id": card.deck_id,
            "deck_index": decks[card.deck_id].deck_index if card.deck_id in decks else None,
            "card_position": card.card_position,
            "payout_eligible": card.payout_eligible,
            "assigned_session_id": card.assigned_session_id,
            "assigned_at": isoformat_or_none(card.assigned_at),
        }
        for card in cards
    ]


def interest_signups_rows(db: Session) -> list[dict[str, Any]]:
    signups = load_model_rows(
        db,
        InterestSignup,
        order_by=InterestSignup.created_at,
        missing_ok=True,
        export_name="interest_signups",
    )
    return [
        {
            "interest_signup_id": signup.id,
            "email_normalized": signup.email_normalized,
            "email_hash": signup.email_hash,
            "language_used": signup.language_used,
            "source_screen": signup.source_screen,
            "experiment_status": signup.experiment_status,
            "deployment_context": signup.deployment_context,
            "site_code": signup.site_code,
            "campaign_code": signup.campaign_code,
            "environment_label": signup.environment_label,
            "operational_note_id": signup.operational_note_id,
            "operational_note_text": signup.operational_note_text,
            "created_at": isoformat_or_none(signup.created_at),
            "updated_at": isoformat_or_none(signup.updated_at),
        }
        for signup in signups
    ]


def operational_notes_rows(db: Session) -> list[dict[str, Any]]:
    notes = load_model_rows(
        db,
        OperationalNote,
        order_by=OperationalNote.effective_from,
        missing_ok=True,
        export_name="operational_notes",
    )
    return [
        {
            "operational_note_id": note.id,
            "note_text": note.note_text,
            "status": note.status,
            "effective_from": isoformat_or_none(note.effective_from),
            "cleared_at": isoformat_or_none(note.cleared_at),
            "created_at": isoformat_or_none(note.created_at),
            "updated_at": isoformat_or_none(note.updated_at),
        }
        for note in notes
    ]


def quality_flags_rows(db: Session) -> list[dict[str, Any]]:
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    rows: list[dict[str, Any]] = []
    for record in sessions:
        for flag in parse_json_list(record.quality_flags_json):
            rows.append(
                {
                    "session_id": record.id,
                    "experiment_phase": record.experiment_phase,
                    "treatment_key": record.treatment_key,
                    "flag_key": flag,
                    "created_at": isoformat_or_none(record.completed_at or record.created_at),
                }
            )
    return rows


def fraud_flags_rows(db: Session) -> list[dict[str, Any]]:
    flags = load_model_rows(
        db,
        FraudFlag,
        order_by=FraudFlag.created_at,
        missing_ok=True,
        export_name="fraud_flags",
    )
    return [
        {
            "fraud_flag_id": flag.id,
            "session_id": flag.session_id,
            "user_id": flag.user_id,
            "flag_key": flag.flag_key,
            "severity": flag.severity,
            "payload_json": flag.payload_json,
            "created_at": isoformat_or_none(flag.created_at),
        }
        for flag in flags
    ]


def consent_records_rows(db: Session) -> list[dict[str, Any]]:
    consents = db.exec(select(ConsentRecord).order_by(ConsentRecord.created_at)).all()
    return [
        {
            "consent_id": consent.id,
            "session_id": consent.session_id,
            "bracelet_id": consent.bracelet_id,
            "consent_version": consent.consent_version,
            "language_at_access": consent.language_at_access,
            "age_confirmed": consent.age_confirmed,
            "participation_accepted": consent.participation_accepted,
            "data_accepted": consent.data_accepted,
            "accepted_at": isoformat_or_none(consent.accepted_at),
            "landing_visible_ms": consent.landing_visible_ms,
            "info_panels_opened_json": consent.info_panels_opened_json,
            "info_panel_durations_json": consent.info_panel_durations_json,
            "info_panel_open_count": consent.info_panel_open_count,
            "checkbox_order_json": consent.checkbox_order_json,
            "checkbox_timestamps_json": consent.checkbox_timestamps_json,
            "continue_blocked_count": consent.continue_blocked_count,
        }
        for consent in consents
    ]


def snapshot_records_rows(db: Session) -> list[dict[str, Any]]:
    snapshots = db.exec(select(SnapshotRecord).order_by(SnapshotRecord.updated_at)).all()
    return [
        {
            "snapshot_id": snapshot.id,
            "session_id": snapshot.session_id,
            "language_used": snapshot.language_used,
            "treatment_key": snapshot.treatment_key,
            "treatment_family": snapshot.treatment_family,
            "norm_target_value": snapshot.norm_target_value,
            "is_control": snapshot.is_control,
            "displayed_count_target": snapshot.displayed_count_target,
            "displayed_denominator": snapshot.displayed_denominator,
            "displayed_message_text": snapshot.displayed_message_text,
            "displayed_message_version": snapshot.displayed_message_version,
            "control_message_text": snapshot.control_message_text,
            "first_result_value": snapshot.first_result_value,
            "last_seen_value": snapshot.last_seen_value,
            "all_values_seen_json": snapshot.all_values_seen_json,
            "rerolls_visible_json": snapshot.rerolls_visible_json,
            "final_state_shown": snapshot.final_state_shown,
            "final_message_text": snapshot.final_message_text,
            "final_amount_eur": snapshot.final_amount_eur,
            "payout_reference_shown": snapshot.payout_reference_shown,
            "payout_phone_shown": snapshot.payout_phone_shown,
            "updated_at": isoformat_or_none(snapshot.updated_at),
        }
        for snapshot in snapshots
    ]


def audit_events_rows(db: Session) -> list[dict[str, Any]]:
    events = db.exec(select(AuditEvent).order_by(AuditEvent.created_at)).all()
    return [
        {
            "audit_event_id": event.id,
            "session_id": event.session_id,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "action": event.action,
            "old_state": event.old_state,
            "new_state": event.new_state,
            "idempotency_key": event.idempotency_key,
            "payload_json": event.payload_json,
            "created_at": isoformat_or_none(event.created_at),
        }
        for event in events
    ]


DATASET_BUILDERS = {
    "sessions": analytic_sessions_rows,
    "throws": throws_rows,
    "claims": claims_rows,
    "referrals": referrals_rows,
    "treatment_decks": treatment_decks_rows,
    "treatment_deck_cards": treatment_deck_cards_rows,
    "result_decks": result_decks_rows,
    "result_deck_cards": result_deck_cards_rows,
    "payment_decks": payment_decks_rows,
    "payment_deck_cards": payment_deck_cards_rows,
    "quality_flags": quality_flags_rows,
    "consent_records": consent_records_rows,
    "snapshot_records": snapshot_records_rows,
    "payments_admin": payments_admin_rows,
    "interest_signups": interest_signups_rows,
    "telemetry": telemetry_rows,
    "technical_events": technical_events_rows,
    "screen_events": screen_events_rows,
    "client_contexts": client_contexts_rows,
    "fraud_flags": fraud_flags_rows,
    "audit_events": audit_events_rows,
    "operational_notes": operational_notes_rows,
}


def rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    columns: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def dataset_rows(db: Session, dataset_name: str) -> list[dict[str, Any]]:
    if dataset_name not in DATASET_BUILDERS:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return DATASET_BUILDERS[dataset_name](db)


def bundle_datasets(bundle_name: str) -> list[str]:
    if bundle_name == "analytic":
        return [
            "sessions",
            "throws",
            "claims",
            "referrals",
            "treatment_decks",
            "treatment_deck_cards",
            "result_decks",
            "result_deck_cards",
            "payment_decks",
            "payment_deck_cards",
            "quality_flags",
            "consent_records",
            "snapshot_records",
        ]
    if bundle_name == "administrative":
        return ["payments_admin", "interest_signups"]
    if bundle_name == "operational":
        return [
            "telemetry",
            "technical_events",
            "screen_events",
            "client_contexts",
            "fraud_flags",
            "audit_events",
            "operational_notes",
        ]
    if bundle_name == "all":
        return list(DATASET_BUILDERS.keys())
    raise HTTPException(status_code=404, detail="Bundle no encontrado")


def export_readme_content(bundle_name: str, datasets: list[str]) -> str:
    lines = [
        "# README_EXPORT",
        "",
        f"Paquete generado: {bundle_name}",
        "",
        "Datasets incluidos:",
    ]
    for dataset_name in datasets:
        meta = DATASET_DESCRIPTIONS.get(dataset_name, {})
        lines.append(f"- {dataset_name}: {meta.get('description', 'Sin descripcion')}")
    lines.extend(
        [
            "",
            "Capas:",
            "- analytic: datos listos para analisis cientifico y reconstruccion del tratamiento.",
            "- operational: logs, spells, auditoria y telemetria cruda.",
            "- administrative: pagos y datos administrativos sensibles.",
        ]
    )
    return "\n".join(lines)


def current_versions_payload(db: Session) -> dict[str, Any]:
    state = db.get(ExperimentState, "global")
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "ui_version": UI_VERSION,
        "consent_version": CONSENT_VERSION,
        "deck_version": DECK_VERSION,
        "payment_version": PAYMENT_VERSION,
        "telemetry_version": TELEMETRY_VERSION,
        "lexicon_version": LEXICON_VERSION,
        "deployment_context": DEPLOYMENT_CONTEXT,
        "environment_label": ENVIRONMENT_LABEL,
        "site_code": SITE_CODE,
        "campaign_code": CAMPAIGN_CODE,
        "quality_thresholds": QUALITY_THRESHOLDS,
        "public_support": public_support(),
        "state": {
            "current_phase": state.current_phase if state else PHASE_1_MAIN,
            "experiment_status": state.experiment_status if state else "active",
            "phase_transition_threshold": (
                state.phase_transition_threshold if state else None
            ),
            "valid_completed_count": state.valid_completed_count if state else 0,
            "treatment_version": state.treatment_version if state else None,
            "allocation_version": state.allocation_version if state else None,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "current_phase": state.current_phase if state else None,
        "experiment_status": state.experiment_status if state else None,
        "phase_transition_threshold": state.phase_transition_threshold if state else None,
        "valid_completed_count": state.valid_completed_count if state else None,
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
        "treatment_version": state.treatment_version if state else None,
        "allocation_version": state.allocation_version if state else None,
    }


def build_export_bundle(db: Session, bundle_name: str) -> bytes:
    dataset_names = bundle_datasets(bundle_name)
    file_payloads: dict[str, bytes] = {}
    manifest_tables: list[dict[str, Any]] = []
    skipped_datasets: list[dict[str, str]] = []

    for dataset_name in dataset_names:
        filename = f"{dataset_name}.csv"
        error_message: str | None = None
        try:
            rows = dataset_rows(db, dataset_name)
            csv_bytes = rows_to_csv_bytes(rows)
        except Exception as exc:
            rows = []
            csv_bytes = rows_to_csv_bytes(rows)
            error_message = export_error_summary(exc)
            skipped_datasets.append({"dataset": dataset_name, "error": error_message})
            logger.error(
                "admin_export_bundle_dataset_failed",
                extra={
                    "structured_payload": {
                        "bundle_name": bundle_name,
                        "dataset": dataset_name,
                        "error": error_message,
                    }
                },
            )

        file_payloads[filename] = csv_bytes
        manifest_entry = {
            "dataset": dataset_name,
            "filename": filename,
            "records": len(rows),
            "category": DATASET_DESCRIPTIONS[dataset_name]["category"],
            "sensitivity": DATASET_DESCRIPTIONS[dataset_name]["sensitivity"],
            "description": DATASET_DESCRIPTIONS[dataset_name]["description"],
            "sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "status": "error" if error_message else "ok",
        }
        if error_message:
            manifest_entry["error"] = error_message
        manifest_tables.append(manifest_entry)

    readme_text = export_readme_content(bundle_name, dataset_names)
    codebook_text = read_doc_or_default(
        "DATASETS_CODEBOOK.md",
        "# DATASETS_CODEBOOK\n\nCodebook basico no encontrado en disco.",
    )
    content_hash = hashlib.sha256(
        "".join(item["sha256"] for item in manifest_tables).encode("utf-8")
    ).hexdigest()
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_name": bundle_name,
        "content_hash_sha256": content_hash,
        "versions": current_versions_payload(db),
        "tables": manifest_tables,
        "skipped_datasets": skipped_datasets,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, payload in file_payloads.items():
            archive.writestr(filename, payload)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("README_EXPORT.md", readme_text)
        archive.writestr("DATASETS_CODEBOOK.md", codebook_text)
    return buffer.getvalue()


def exports_page_html(
    state: ExperimentState,
    dataset_stats: dict[str, dict[str, Any]],
    prize_stats: dict[str, Any],
) -> str:
    payments_admin_stats = dataset_stats.get("payments_admin", {})
    rows_html = []
    for dataset_name, meta in DATASET_DESCRIPTIONS.items():
        stats = dataset_stats.get(dataset_name, {})
        error_message = stats.get("error")
        description_html = escape(meta["description"])
        if error_message:
            description_html += (
                f"<br /><span class=\"warn\">No disponible: {escape(str(error_message))}</span>"
            )
        export_html = (
            "<span class=\"warn\">No disponible</span>"
            if error_message
            else f'<a href="/admin/export/{dataset_name}.csv">CSV</a>'
        )
        rows_html.append(
            f"""
            <tr>
              <td><strong>{dataset_name}</strong></td>
              <td>{meta['category']}</td>
              <td>{meta['sensitivity']}</td>
              <td>{stats.get('records', '-')}</td>
              <td>{stats.get('size_label', '0 B' if not error_message else 'Error')}</td>
              <td>{stats.get('generated_at', '-')}</td>
              <td>{description_html}</td>
              <td>{export_html}</td>
            </tr>
            """
        )
    return f"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Research Exports</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin:0; padding:24px; background:#f6f4ee; color:#111; }}
      .wrap {{ max-width:1100px; margin:0 auto; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin:20px 0 28px; }}
      .card {{ background:white; border-radius:20px; padding:20px; box-shadow:0 18px 48px rgba(0,0,0,.06); }}
      h1,h2 {{ margin:0 0 12px; text-transform:uppercase; }}
      a.button {{ display:inline-block; margin-top:12px; padding:12px 16px; border-radius:999px; background:#111; color:white; text-decoration:none; font-weight:700; }}
      a.secondary {{ display:inline-block; padding:10px 14px; border-radius:999px; border:1px solid rgba(0,0,0,.12); color:#111; text-decoration:none; }}
      table {{ width:100%; border-collapse:collapse; background:white; border-radius:20px; overflow:hidden; }}
      th,td {{ padding:14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; vertical-align:top; }}
      .warn {{ color:#8a4b00; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <p>Investigador</p>
      <h1>Data Exports</h1>
      <p>Diseno actual: <strong>{state.current_phase}</strong> | Estado: <strong>{state.experiment_status}</strong> | Validos completados: <strong>{state.valid_completed_count}</strong> / {state.phase_transition_threshold} | Ganadores: <strong>{prize_stats.get('winner_count', 0)}</strong> | Total comprometido: <strong>{prize_stats.get('total_prize_amount_eur', 0)} EUR</strong> | Registros administrativos: <strong>{payments_admin_stats.get('records', 0)}</strong></p>
      <div class="grid">
        <div class="card">
          <h2>Analitico</h2>
          <p>Sessions, claims, tiradas, referidos y mazos balanceados.</p>
          <a class="button" href="/admin/export/bundle/analytic.zip">Exportar dataset analitico completo</a>
        </div>
        <div class="card">
          <h2>Operativo</h2>
          <p>Telemetria cruda, screen spells, auditoria y contexto cliente.</p>
          <a class="button" href="/admin/export/bundle/operational.zip">Exportar telemetria completa</a>
        </div>
        <div class="card">
          <h2>Administrativo</h2>
          <p class="warn">Contiene datos sensibles de cobro y emails voluntarios.</p>
          <a class="button" href="/admin/export/bundle/administrative.zip">Exportar pagos administrativos</a>
        </div>
        <div class="card">
          <h2>Todo</h2>
          <p>ZIP completo con manifest, README y codebook.</p>
          <a class="button" href="/admin/export/bundle/all.zip">Generar paquete completo</a>
        </div>
      </div>
      <h2>Datasets</h2>
      <table>
        <thead><tr><th>Nombre</th><th>Capa</th><th>Sensibilidad</th><th>Registros</th><th>Tamano aprox.</th><th>Generado</th><th>Descripcion</th><th>Exportar</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
      <p style="margin-top:16px; display:flex; gap:12px; flex-wrap:wrap;">
        <a class="secondary" href="/admin/dashboard">Abrir dashboard cientifico-operativo</a>
        <a class="secondary" href="/admin/payments">Abrir panel administrativo Bizum</a>
      </p>
    </div>
  </body>
</html>
"""


def _rows_from_counter(counter: dict[Any, Any]) -> str:
    return "".join(
        f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>"
        for key, value in sorted(counter.items(), key=lambda item: str(item[0]))
    ) or "<tr><td colspan='2'>Sin datos</td></tr>"


def _rows_from_decks(rows: list[dict[str, Any]], *, deck_label: str) -> str:
    return "".join(
        f"<tr><td>{escape(str(row['deck_index']))}</td><td>{escape(str(row['status']))}</td><td>{escape(str(row['assigned_count']))}</td><td>{escape(str(row['remaining_count']))}</td><td>{escape(str(row['card_count']))}</td></tr>"
        for row in rows
    ) or f"<tr><td colspan='5'>Sin mazos de {escape(deck_label)}</td></tr>"


def _rows_from_result_decks(rows: list[dict[str, Any]]) -> str:
    return "".join(
        f"<tr><td>{escape(str(row.get('treatment_key') or '-'))}</td><td>{escape(str(row.get('treatment_cycle_index') or '-'))}</td><td>{escape(str(row['deck_index']))}</td><td>{escape(str(row['status']))}</td><td>{escape(str(row['assigned_count']))}</td><td>{escape(str(row['remaining_count']))}</td><td>{escape(str(row['card_count']))}</td></tr>"
        for row in rows
    ) or "<tr><td colspan='7'>Sin mazos de resultados</td></tr>"


AUTHORITATIVE_SCREEN_FLOW = ["instructions", "comprehension", "game", "report", "exit"]
SCREEN_ORDER = {screen: index for index, screen in enumerate(AUTHORITATIVE_SCREEN_FLOW)}


def _screen_entered(record: SessionRecord, screen_name: str) -> bool:
    current_order = SCREEN_ORDER.get(record.screen_cursor, -1)
    target_order = SCREEN_ORDER.get(screen_name, -1)
    return current_order >= target_order >= 0


def _screen_progressed(record: SessionRecord, screen_name: str) -> bool:
    current_order = SCREEN_ORDER.get(record.screen_cursor, -1)
    target_order = SCREEN_ORDER.get(screen_name, -1)
    return current_order > target_order >= 0


def _empty_die_distribution() -> dict[str, int]:
    return {str(value): 0 for value in range(1, 7)}


def _dominant_distribution_entry(
    distribution: dict[str, int]
) -> tuple[str | None, float]:
    total = sum(distribution.values())
    if total <= 0:
        return None, 0.0
    dominant_value, dominant_count = max(
        distribution.items(),
        key=lambda item: (item[1], int(item[0])),
    )
    return dominant_value, round(dominant_count / total, 4)


def live_data_quality_payload(
    sessions: list[SessionRecord],
    throws: list[Throw],
    recent_cutoff: datetime,
) -> dict[str, Any]:
    recent_completed = [
        record
        for record in sessions
        if record.completed_at is not None and record.completed_at >= recent_cutoff
    ]
    recent_started = [
        record
        for record in sessions
        if record.created_at >= recent_cutoff
    ]

    first_throw_by_session: dict[str, Throw] = {}
    for throw in throws:
        if throw.attempt_index != 1:
            continue
        if throw.session_id not in first_throw_by_session:
            first_throw_by_session[throw.session_id] = throw

    report_distribution = _empty_die_distribution()
    truth_distribution = _empty_die_distribution()
    quality_flag_counts: dict[str, int] = {}
    antifraud_flag_counts: dict[str, int] = {}

    fast_first_throw_count = 0
    fast_report_count = 0
    submit_without_prepare_count = 0
    snapshot_missing_count = 0
    control_contamination_count = 0
    norm_snapshot_incomplete_count = 0
    suspicious_device_reuse_count = 0

    for record in recent_completed:
        first_throw = first_throw_by_session.get(record.id)
        if (
            first_throw
            and first_throw.reaction_ms is not None
            and first_throw.reaction_ms < settings.data_quality_fast_throw_ms
        ):
            fast_first_throw_count += 1

        if record.claim_submitted_at is not None and record.report_prepared_at is None:
            submit_without_prepare_count += 1

        if record.claim_submitted_at and record.report_prepared_at:
            report_ms = int(
                (record.claim_submitted_at - record.report_prepared_at).total_seconds()
                * 1000
            )
            if report_ms < QUALITY_THRESHOLDS["report_fast_ms"]:
                fast_report_count += 1

        if not record.report_snapshot_treatment:
            snapshot_missing_count += 1

        if record.treatment_key == CONTROL_TREATMENT_KEY:
            if (
                record.report_snapshot_count_target is not None
                or record.report_snapshot_denominator is not None
                or record.report_snapshot_target_value is not None
            ):
                control_contamination_count += 1
        else:
            if (
                record.report_snapshot_count_target is None
                or record.report_snapshot_denominator is None
                or record.report_snapshot_target_value is None
            ):
                norm_snapshot_incomplete_count += 1

        if record.reported_value in range(1, 7):
            report_distribution[str(record.reported_value)] += 1
        if record.first_result_value in range(1, 7):
            truth_distribution[str(record.first_result_value)] += 1

        for flag in parse_json_list(record.quality_flags_json):
            key = str(flag)
            quality_flag_counts[key] = quality_flag_counts.get(key, 0) + 1
        for flag in parse_json_list(record.antifraud_flags_json):
            key = str(flag)
            antifraud_flag_counts[key] = antifraud_flag_counts.get(key, 0) + 1
            if key == "same_device_multiple_bracelets":
                suspicious_device_reuse_count += 1

    completed_count = len(recent_completed)
    report_six_share = (
        round(report_distribution["6"] / completed_count, 4) if completed_count else 0.0
    )
    truth_six_share = (
        round(truth_distribution["6"] / completed_count, 4) if completed_count else 0.0
    )
    dominant_report_value, dominant_report_share = _dominant_distribution_entry(
        report_distribution
    )

    return {
        "window_started_sessions": len(recent_started),
        "window_completed_sessions": completed_count,
        "fast_first_throw_threshold_ms": settings.data_quality_fast_throw_ms,
        "fast_report_threshold_ms": QUALITY_THRESHOLDS["report_fast_ms"],
        "fast_first_throw_count": fast_first_throw_count,
        "fast_first_throw_rate": round(fast_first_throw_count / completed_count, 4)
        if completed_count
        else 0.0,
        "fast_report_count": fast_report_count,
        "fast_report_rate": round(fast_report_count / completed_count, 4)
        if completed_count
        else 0.0,
        "submit_without_prepare_count": submit_without_prepare_count,
        "snapshot_missing_count": snapshot_missing_count,
        "control_contamination_count": control_contamination_count,
        "norm_snapshot_incomplete_count": norm_snapshot_incomplete_count,
        "suspicious_device_reuse_count": suspicious_device_reuse_count,
        "report_distribution": report_distribution,
        "truth_distribution": truth_distribution,
        "report_six_share": report_six_share,
        "truth_six_share": truth_six_share,
        "report_truth_six_gap": round(report_six_share - truth_six_share, 4),
        "dominant_report_value": dominant_report_value,
        "dominant_report_share": dominant_report_share,
        "quality_flag_counts": dict(sorted(quality_flag_counts.items())),
        "antifraud_flag_counts": dict(sorted(antifraud_flag_counts.items())),
    }


def _bucket_floor(timestamp: datetime, *, bucket_minutes: int) -> datetime:
    return timestamp.replace(
        minute=(timestamp.minute // bucket_minutes) * bucket_minutes,
        second=0,
        microsecond=0,
    )


def live_experiment_metrics_payload(
    sessions: list[SessionRecord],
    *,
    recent_cutoff: datetime,
    bucket_minutes: int = 5,
) -> dict[str, Any]:
    participants_total = len(sessions)
    participants_recent = len(
        [record for record in sessions if record.created_at >= recent_cutoff]
    )
    completed_sessions = [record for record in sessions if record.completed_at is not None]
    completed_recent = [
        record
        for record in completed_sessions
        if record.completed_at and record.completed_at >= recent_cutoff
    ]
    submitted_claim_sessions = [
        record
        for record in sessions
        if record.claim_submitted_at is not None and record.reported_value is not None
    ]
    submitted_claims_recent = [
        record
        for record in submitted_claim_sessions
        if record.claim_submitted_at and record.claim_submitted_at >= recent_cutoff
    ]
    reported_six_count_total = sum(
        1 for record in submitted_claim_sessions if record.reported_value == 6
    )
    reported_six_count_recent = sum(
        1 for record in submitted_claims_recent if record.reported_value == 6
    )
    lies_count_total = sum(
        1 for record in submitted_claim_sessions if record.is_honest is False
    )
    lies_count_recent = sum(
        1 for record in submitted_claims_recent if record.is_honest is False
    )
    completion_rate_total = round(
        len(completed_sessions) / participants_total, 4
    ) if participants_total else 0.0
    completion_rate_recent = round(
        len(completed_recent) / participants_recent, 4
    ) if participants_recent else 0.0
    reported_six_rate_total = round(
        reported_six_count_total / len(submitted_claim_sessions), 4
    ) if submitted_claim_sessions else 0.0
    reported_six_rate_recent = round(
        reported_six_count_recent / len(submitted_claims_recent), 4
    ) if submitted_claims_recent else 0.0
    lie_rate_total = round(
        lies_count_total / len(submitted_claim_sessions), 4
    ) if submitted_claim_sessions else 0.0
    lie_rate_recent = round(
        lies_count_recent / len(submitted_claims_recent), 4
    ) if submitted_claims_recent else 0.0

    series_map: dict[datetime, dict[str, int]] = {}

    def ensure_bucket(bucket_at: datetime) -> dict[str, int]:
        bucket = series_map.get(bucket_at)
        if bucket is None:
            bucket = {
                "participants_started": 0,
                "participants_completed": 0,
                "claims_submitted": 0,
                "reported_six_count": 0,
                "lies_count": 0,
            }
            series_map[bucket_at] = bucket
        return bucket

    for record in sessions:
        if record.created_at >= recent_cutoff:
            ensure_bucket(
                _bucket_floor(record.created_at, bucket_minutes=bucket_minutes)
            )["participants_started"] += 1
        if record.completed_at and record.completed_at >= recent_cutoff:
            ensure_bucket(
                _bucket_floor(record.completed_at, bucket_minutes=bucket_minutes)
            )["participants_completed"] += 1
        if record.claim_submitted_at and record.claim_submitted_at >= recent_cutoff:
            bucket = ensure_bucket(
                _bucket_floor(record.claim_submitted_at, bucket_minutes=bucket_minutes)
            )
            bucket["claims_submitted"] += 1
            if record.reported_value == 6:
                bucket["reported_six_count"] += 1
            if record.is_honest is False:
                bucket["lies_count"] += 1

    timeseries = []
    for bucket_at in sorted(series_map):
        bucket = series_map[bucket_at]
        claims_submitted = bucket["claims_submitted"]
        participants_started = bucket["participants_started"]
        timeseries.append(
            {
                "bucket_start": bucket_at.replace(tzinfo=UTC).isoformat(),
                "participants_started": participants_started,
                "participants_completed": bucket["participants_completed"],
                "claims_submitted": claims_submitted,
                "completion_rate": round(
                    bucket["participants_completed"] / participants_started, 4
                )
                if participants_started
                else 0.0,
                "reported_six_rate": round(
                    bucket["reported_six_count"] / claims_submitted, 4
                )
                if claims_submitted
                else 0.0,
                "lie_rate": round(bucket["lies_count"] / claims_submitted, 4)
                if claims_submitted
                else 0.0,
            }
        )

    return {
        "participants_total": participants_total,
        "participants_recent": participants_recent,
        "claims_total": len(submitted_claim_sessions),
        "claims_recent": len(submitted_claims_recent),
        "completion_rate_total": completion_rate_total,
        "completion_rate_recent": completion_rate_recent,
        "reported_six_count_total": reported_six_count_total,
        "reported_six_count_recent": reported_six_count_recent,
        "reported_six_rate_total": reported_six_rate_total,
        "reported_six_rate_recent": reported_six_rate_recent,
        "lies_count_total": lies_count_total,
        "lies_count_recent": lies_count_recent,
        "lie_rate_total": lie_rate_total,
        "lie_rate_recent": lie_rate_recent,
        "timeseries_bucket_minutes": bucket_minutes,
        "timeseries": timeseries,
    }


def live_payments_payload(db: Session) -> dict[str, Any]:
    payments = db.exec(select(Payment).order_by(Payment.created_at.desc())).all()
    payout_requests = db.exec(
        select(PayoutRequest).order_by(PayoutRequest.created_at.desc())
    ).all()
    sessions = db.exec(select(SessionRecord)).all()
    users = db.exec(select(User)).all()
    session_by_id = {record.id: record for record in sessions}
    user_by_id = {user.id: user for user in users}
    payout_request_by_payment_id = {request.payment_id: request for request in payout_requests}
    winners = [payment for payment in payments if payment.eligible]
    winners_sorted = sorted(
        winners,
        key=lambda item: (
            payout_request_by_payment_id.get(item.id).created_at
            if payout_request_by_payment_id.get(item.id)
            else item.created_at
        ),
        reverse=True,
    )
    recent_winners = []
    for payment in winners_sorted[:20]:
        session_record = session_by_id.get(payment.session_id)
        user = user_by_id.get(session_record.user_id) if session_record else None
        payout_request = payout_request_by_payment_id.get(payment.id)
        recent_winners.append(
            {
                "session_id": payment.session_id,
                "bracelet_id": user.bracelet_id if user else None,
                "reference_code": (
                    payout_request.payout_reference
                    if payout_request and payout_request.payout_reference
                    else payment.payout_reference
                ),
                "amount_eur": round(payment.amount_cents / 100, 2),
                "donation_requested": bool(
                    payout_request.donation_requested if payout_request else False
                ),
                "submitted_at": (
                    payout_request.created_at.replace(tzinfo=UTC).isoformat()
                    if payout_request and payout_request.created_at
                    else payment.created_at.replace(tzinfo=UTC).isoformat()
                    if payment.created_at
                    else None
                ),
            }
        )
    total_amount_eur = round(sum(payment.amount_cents for payment in winners) / 100, 2)
    donation_count = sum(1 for request in payout_requests if request.donation_requested)
    return {
        "summary": {
            "winners_total": len(winners),
            "payment_requests_total": len(payout_requests),
            "amount_total_eur": total_amount_eur,
            "donations_total": donation_count,
        },
        "recent_winners": recent_winners,
    }


def admin_payments_payload(db: Session) -> dict[str, Any]:
    payments = db.exec(select(Payment).order_by(Payment.created_at.desc())).all()
    payout_requests = db.exec(
        select(PayoutRequest).order_by(PayoutRequest.created_at.desc())
    ).all()
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at.desc())).all()
    users = db.exec(select(User)).all()

    payment_by_id = {payment.id: payment for payment in payments}
    session_by_id = {record.id: record for record in sessions}
    user_by_id = {user.id: user for user in users}

    rows: list[dict[str, Any]] = []
    for payout_request in payout_requests:
        payment = payment_by_id.get(payout_request.payment_id)
        session_record = session_by_id.get(payout_request.session_id)
        user = user_by_id.get(session_record.user_id) if session_record else None
        accepted_conditions = bool(
            session_record
            and session_record.consent_accepted
            and session_record.consent_age_confirmed
            and session_record.consent_info_accepted
            and session_record.consent_data_accepted
        )
        amount_eur = (
            round(payment.amount_cents / 100, 2)
            if payment and payment.amount_cents is not None
            else 0.0
        )
        payment_status = payment.status if payment else "missing"
        request_status = payout_request.status or "submitted"
        needs_action = payment_status in {"queued", "pending"} and request_status != "processed"
        donation_requested = bool(payout_request.donation_requested)
        rows.append(
            {
                "payment_id": payout_request.payment_id,
                "payout_request_id": payout_request.id,
                "session_id": payout_request.session_id,
                "bracelet_id": user.bracelet_id if user else None,
                "reference_code": payout_request.payout_reference or payment.payout_reference if payment else None,
                "requested_phone": payout_request.requested_phone,
                "requested_phone_display": "ONG" if donation_requested else payout_request.requested_phone,
                "donation_requested": donation_requested,
                "accepted_conditions": accepted_conditions,
                "accepted_conditions_label": "Si" if accepted_conditions else "No",
                "amount_eur": amount_eur,
                "payment_status": payment_status,
                "request_status": request_status,
                "language_used": payout_request.language_used,
                "submitted_at": isoformat_or_none(payout_request.created_at),
                "processed_at": isoformat_or_none(payout_request.processed_at),
                "paid_at": isoformat_or_none(payment.paid_at) if payment else None,
                "needs_action": needs_action,
            }
        )

    rows.sort(
        key=lambda item: (
            0 if item["needs_action"] else 1,
            item["submitted_at"] or "",
        )
    )

    pending_rows = [row for row in rows if row["needs_action"]]
    pending_bizum_rows = [row for row in pending_rows if not row["donation_requested"]]
    pending_donation_rows = [row for row in pending_rows if row["donation_requested"]]
    donation_rows = [row for row in rows if row["donation_requested"]]
    processed_rows = [row for row in rows if row["payment_status"] == "paid"]
    processed_donation_rows = [
        row for row in processed_rows if row["donation_requested"]
    ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "requests_total": len(rows),
            "pending_total": len(pending_rows),
            "pending_bizum_count": len(pending_bizum_rows),
            "pending_bizum_amount_eur": round(
                sum(row["amount_eur"] for row in pending_bizum_rows), 2
            ),
            "pending_donation_count": len(pending_donation_rows),
            "pending_donation_amount_eur": round(
                sum(row["amount_eur"] for row in pending_donation_rows), 2
            ),
            "donation_requested_total_eur": round(
                sum(row["amount_eur"] for row in donation_rows), 2
            ),
            "donation_processed_total_eur": round(
                sum(row["amount_eur"] for row in processed_donation_rows), 2
            ),
            "paid_total_eur": round(
                sum(row["amount_eur"] for row in processed_rows), 2
            ),
        },
        "rows": rows,
    }


def admin_payments_page_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows_html: list[str] = []
    for row in payload["rows"]:
        reference_code = escape(str(row["reference_code"] or "-"))
        requested_phone = escape(str(row["requested_phone_display"] or "-"))
        bracelet_id = escape(str(row["bracelet_id"] or "-"))
        amount_eur = escape(f"{row['amount_eur']:.2f}")
        status_label = escape(
            "pendiente"
            if row["needs_action"]
            else "gestionado" if row["payment_status"] == "paid" else row["payment_status"]
        )
        request_label = escape(
            "donacion ONG" if row["donation_requested"] else "bizum"
        )
        action_html = (
            f"""
            <form method="post" action="/admin/payments/{escape(str(row['payment_id']))}/mark-paid" onsubmit="return confirm('¿Marcar esta solicitud como gestionada?');">
              <button type="submit">{'Marcar donacion' if row['donation_requested'] else 'Marcar Bizum'}</button>
            </form>
            """
            if row["needs_action"]
            else "<span class=\"muted\">Ya gestionado</span>"
        )
        rows_html.append(
            f"""
            <tr>
              <td>{escape(str(row['submitted_at'] or '-'))}</td>
              <td><strong>{reference_code}</strong></td>
              <td>{requested_phone}</td>
              <td>{request_label}</td>
              <td>{amount_eur} EUR</td>
              <td>{escape(row['accepted_conditions_label'])}</td>
              <td>{bracelet_id}</td>
              <td>{status_label}</td>
              <td>{action_html}</td>
            </tr>
            """
        )

    if not rows_html:
        rows_html.append(
            """
            <tr>
              <td colspan="9" class="muted">Todavia no hay solicitudes de Bizum o donacion.</td>
            </tr>
            """
        )

    return f"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="refresh" content="20" />
    <title>Panel administrativo Bizum</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin:0; padding:24px; background:#f6f4ee; color:#111; }}
      .wrap {{ max-width:1200px; margin:0 auto; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin:20px 0 28px; }}
      .card {{ background:white; border-radius:20px; padding:20px; box-shadow:0 18px 48px rgba(0,0,0,.06); }}
      h1,h2 {{ margin:0 0 12px; text-transform:uppercase; }}
      .eyebrow {{ color:#555; }}
      .metric {{ font-size:32px; font-weight:800; margin-top:8px; }}
      .muted {{ color:#666; font-size:13px; }}
      .toolbar {{ display:flex; gap:12px; flex-wrap:wrap; margin:12px 0 24px; }}
      a.button, button {{ display:inline-block; padding:12px 16px; border-radius:999px; background:#111; color:white; text-decoration:none; font-weight:700; border:none; cursor:pointer; }}
      a.secondary {{ display:inline-block; padding:10px 14px; border-radius:999px; border:1px solid rgba(0,0,0,.12); color:#111; text-decoration:none; }}
      table {{ width:100%; border-collapse:collapse; background:white; border-radius:20px; overflow:hidden; }}
      th,td {{ padding:14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; vertical-align:top; }}
      th {{ font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:#666; }}
      form {{ margin:0; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <p class="eyebrow">Administrativo</p>
      <h1>Bizum y donaciones</h1>
      <p>Recarga cada 20 segundos. Si prefieres, actualiza manualmente para ver nuevas solicitudes.</p>
      <div class="toolbar">
        <a class="secondary" href="/admin/dashboard">Volver al dashboard</a>
        <a class="secondary" href="/admin/exports">Abrir exports</a>
        <a class="secondary" href="/admin/payments/live">Ver JSON live</a>
      </div>
      <div class="grid">
        <div class="card">
          <div class="muted">Bizum pendientes</div>
          <div class="metric">{summary['pending_bizum_count']}</div>
          <div class="muted">{summary['pending_bizum_amount_eur']:.2f} EUR por transferir</div>
        </div>
        <div class="card">
          <div class="muted">Donacion ONG pendiente</div>
          <div class="metric">{summary['pending_donation_count']}</div>
          <div class="muted">{summary['pending_donation_amount_eur']:.2f} EUR pendientes</div>
        </div>
        <div class="card">
          <div class="muted">Sumatorio ONG</div>
          <div class="metric">{summary['donation_requested_total_eur']:.2f} EUR</div>
          <div class="muted">{summary['donation_processed_total_eur']:.2f} EUR ya gestionados</div>
        </div>
        <div class="card">
          <div class="muted">Solicitudes totales</div>
          <div class="metric">{summary['requests_total']}</div>
          <div class="muted">{summary['paid_total_eur']:.2f} EUR ya pagados o donados</div>
        </div>
      </div>

      <h2>Solicitudes</h2>
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Codigo</th>
            <th>Telefono</th>
            <th>Destino</th>
            <th>Importe</th>
            <th>Acepto condiciones</th>
            <th>Pulsera</th>
            <th>Estado</th>
            <th>Accion</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
  </body>
</html>
"""


def live_qr_metrics_payload(db: Session) -> dict[str, Any]:
    routes = db.exec(select(GatewayRoute).order_by(GatewayRoute.qr_code)).all()
    logs = db.exec(select(GatewayAccessLog).order_by(GatewayAccessLog.created_at)).all()
    route_by_qr = {route.qr_code: route for route in routes}
    per_qr: dict[str, dict[str, Any]] = {}
    per_zone: dict[str, dict[str, Any]] = {}

    for route in routes:
        zone_code = route.zone_code or route.qr_code
        per_qr[route.qr_code] = {
            "qr_code": route.qr_code,
            "zone_code": zone_code,
            "enabled": route.enabled,
            "active_target": route.active_target,
            "scans_total": 0,
            "sessions_started": 0,
            "conversion_rate": 0.0,
            "last_scan_at": None,
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
        zone_code = log_item.zone_code or log_item.qr_code
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
        qr_row["last_scan_at"] = log_item.created_at.replace(tzinfo=UTC).isoformat()
        if log_item.session_id:
            qr_row["_session_ids"].add(log_item.session_id)
            zone_row["_session_ids"].add(log_item.session_id)
        zone_row["scans_total"] += 1

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
        "summary": {
            "qr_count": len(per_qr),
            "zone_count": len(per_zone),
            "scans_total": sum(item["scans_total"] for item in per_qr.values()),
            "sessions_started": sum(
                item["sessions_started"] for item in per_qr.values()
            ),
        },
        "by_qr": sorted(
            per_qr.values(),
            key=lambda item: (-item["scans_total"], item["qr_code"]),
        ),
        "by_zone": sorted(
            per_zone.values(),
            key=lambda item: (-item["scans_total"], item["zone_code"]),
        ),
    }


def live_referral_metrics_payload(db: Session) -> dict[str, Any]:
    links = db.exec(select(ReferralLink).order_by(ReferralLink.created_at.desc())).all()
    clicks = db.exec(select(ReferralClick).order_by(ReferralClick.created_at.desc())).all()
    per_inviter: dict[str, dict[str, Any]] = {}
    top_links: list[dict[str, Any]] = []

    for link in links:
        top_links.append(
            {
                "ref_id": link.id,
                "inviter_session_id": link.inviter_session_id,
                "referral_code": link.inviter_referral_code,
                "channel": link.channel,
                "clicks_total": link.click_count,
                "conversions_total": link.conversion_count,
                "invite_to_entry_ratio": (
                    round(link.conversion_count / link.click_count, 4)
                    if link.click_count
                    else 0.0
                ),
                "created_at": link.created_at.replace(tzinfo=UTC).isoformat(),
            }
        )
        inviter_row = per_inviter.setdefault(
            link.inviter_session_id,
            {
                "inviter_session_id": link.inviter_session_id,
                "referral_code": link.inviter_referral_code,
                "links_total": 0,
                "clicks_total": 0,
                "users_by_referral": 0,
                "invite_to_entry_ratio": 0.0,
            },
        )
        inviter_row["links_total"] += 1
        inviter_row["clicks_total"] += link.click_count
        inviter_row["users_by_referral"] += link.conversion_count

    for inviter_row in per_inviter.values():
        clicks_total = inviter_row["clicks_total"]
        inviter_row["invite_to_entry_ratio"] = (
            round(inviter_row["users_by_referral"] / clicks_total, 4)
            if clicks_total
            else 0.0
        )

    invitations_sent_total = len(links)
    clicks_total = sum(link.click_count for link in links)
    conversions_total = sum(link.conversion_count for link in links)
    return {
        "summary": {
            "invitations_sent_total": invitations_sent_total,
            "clicks_total": clicks_total,
            "users_by_referral_total": conversions_total,
            "invite_to_entry_ratio": (
                round(conversions_total / clicks_total, 4) if clicks_total else 0.0
            ),
        },
        "top_inviters": sorted(
            per_inviter.values(),
            key=lambda item: (
                -item["users_by_referral"],
                -item["clicks_total"],
                item["inviter_session_id"],
            ),
        )[:20],
        "top_links": sorted(
            top_links,
            key=lambda item: (
                -item["conversions_total"],
                -item["clicks_total"],
                item["ref_id"],
            ),
        )[:20],
        "recent_clicks_total": len(clicks),
    }


def live_metrics_payload(db: Session, readiness: dict[str, Any]) -> dict[str, Any]:
    now_aware = datetime.now(UTC)
    now = now_aware.replace(tzinfo=None)
    active_window = timedelta(seconds=settings.observability_active_window_seconds)
    recent_window = timedelta(seconds=settings.observability_recent_window_seconds)
    stalled_window = timedelta(seconds=settings.observability_stalled_screen_seconds)
    active_cutoff = now - active_window
    recent_cutoff = now - recent_window
    stalled_cutoff = now - stalled_window

    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    active_sessions = [
        record
        for record in sessions
        if record.last_seen_at >= active_cutoff
    ]
    active_users = len({record.user_id for record in active_sessions if record.user_id})
    started_recent = [record for record in sessions if record.created_at >= recent_cutoff]
    completed_sessions = [record for record in sessions if record.completed_at is not None]
    completed_recent = [
        record for record in completed_sessions if record.completed_at and record.completed_at >= recent_cutoff
    ]
    valid_completed_sessions = [record for record in sessions if record.is_valid_completed]

    screen_abandonment: list[dict[str, Any]] = []
    for screen_name in AUTHORITATIVE_SCREEN_FLOW[:-1]:
        entered = [record for record in sessions if _screen_entered(record, screen_name)]
        progressed = [record for record in entered if _screen_progressed(record, screen_name)]
        active_on_screen = [
            record
            for record in entered
            if record.screen_cursor == screen_name and record.last_seen_at >= active_cutoff
        ]
        stalled_on_screen = [
            record
            for record in entered
            if record.screen_cursor == screen_name and record.last_seen_at < stalled_cutoff
        ]
        entered_count = len(entered)
        progressed_count = len(progressed)
        active_count = len(active_on_screen)
        stalled_count = len(stalled_on_screen)
        screen_abandonment.append(
            {
                "screen": screen_name,
                "entered": entered_count,
                "progressed": progressed_count,
                "active": active_count,
                "stalled": stalled_count,
                "abandonment_rate": round(stalled_count / entered_count, 4)
                if entered_count
                else 0.0,
            }
        )

    http_metrics = get_http_metrics_snapshot()
    endpoint_metrics = [
        {
            "endpoint": endpoint,
            **payload,
        }
        for endpoint, payload in sorted(
            http_metrics.items(),
            key=lambda item: (
                -(item[1].get("error_count") or 0),
                -(item[1].get("count") or 0),
                item[0],
            ),
        )
    ]
    error_metrics = [
        item for item in endpoint_metrics if int(item.get("error_count") or 0) > 0
    ]

    counters = {
        "sessions": get_counter_group_snapshot("sessions"),
        "screens_entered": get_counter_group_snapshot("screens_entered"),
        "screens_exited": get_counter_group_snapshot("screens_exited"),
    }

    started_total = len(sessions)
    completed_total = len(completed_sessions)
    completion_rate_total = round(completed_total / started_total, 4) if started_total else 0.0
    recent_started_count = len(started_recent)
    recent_completed_count = len(completed_recent)
    completion_rate_recent = (
        round(recent_completed_count / recent_started_count, 4)
        if recent_started_count
        else 0.0
    )
    throws = db.exec(select(Throw)).all()
    data_quality = live_data_quality_payload(sessions, throws, recent_cutoff)
    experiment_metrics = live_experiment_metrics_payload(
        sessions,
        recent_cutoff=recent_cutoff,
    )

    alerts: list[dict[str, Any]] = []
    if not readiness.get("ok", False):
        alerts.append(
            {
                "key": "backend_unready",
                "severity": "critical",
                "message": "El backend no está listo o falta alguna dependencia crítica.",
            }
        )
    failing_endpoints = [
        item
        for item in error_metrics
        if (item.get("count") or 0) >= settings.alert_endpoint_error_count_threshold
        and (item.get("error_rate") or 0.0) >= settings.alert_endpoint_error_rate_threshold
    ]
    if failing_endpoints:
        endpoint_names = ", ".join(item["endpoint"] for item in failing_endpoints[:3])
        alerts.append(
            {
                "key": "endpoint_errors_spike",
                "severity": "high",
                "message": f"Ha aumentado la tasa de errores en: {endpoint_names}.",
            }
        )
    if (
        recent_started_count >= settings.alert_completion_min_started
        and completion_rate_recent < settings.alert_completion_rate_threshold
    ):
        alerts.append(
            {
                "key": "conversion_drop",
                "severity": "high",
                "message": "La conversión reciente de sesión iniciada a sesión completada ha caído por debajo del umbral configurado.",
            }
        )

    if (
        data_quality["window_completed_sessions"] >= settings.alert_quality_min_completed
        and (
            data_quality["fast_first_throw_rate"]
            >= settings.alert_fast_throw_rate_threshold
            or data_quality["fast_report_rate"]
            >= settings.alert_fast_report_rate_threshold
        )
    ):
        alerts.append(
            {
                "key": "suspicious_speed_spike",
                "severity": "high",
                "message": (
                    "Ha subido la tasa de respuestas demasiado rapidas. "
                    f"first_throw_fast={data_quality['fast_first_throw_rate']:.0%}, "
                    f"report_fast={data_quality['fast_report_rate']:.0%}."
                ),
            }
        )
    if (
        data_quality["window_completed_sessions"] >= settings.alert_quality_min_completed
        and (
            data_quality["dominant_report_share"]
            >= settings.alert_report_top_share_threshold
            or data_quality["report_truth_six_gap"]
            >= settings.alert_report_six_gap_threshold
        )
    ):
        dominant_value = data_quality["dominant_report_value"] or "-"
        alerts.append(
            {
                "key": "report_distribution_anomaly",
                "severity": "high",
                "message": (
                    "La distribucion reciente de respuestas parece anomala. "
                    f"valor_dominante={dominant_value}, "
                    f"share={data_quality['dominant_report_share']:.0%}, "
                    f"gap_report_vs_truth_6={data_quality['report_truth_six_gap']:.0%}."
                ),
            }
        )
    if (
        data_quality["submit_without_prepare_count"] > 0
        or data_quality["snapshot_missing_count"] > 0
        or data_quality["control_contamination_count"] > 0
        or data_quality["norm_snapshot_incomplete_count"] > 0
    ):
        alerts.append(
            {
                "key": "data_integrity_break",
                "severity": "critical",
                "message": (
                    "Se han detectado incoherencias en snapshot o secuencia de claim. "
                    f"missing_snapshot={data_quality['snapshot_missing_count']}, "
                    f"submit_without_prepare={data_quality['submit_without_prepare_count']}, "
                    f"control_contamination={data_quality['control_contamination_count']}."
                ),
            }
        )
    if (
        data_quality["suspicious_device_reuse_count"]
        >= settings.alert_device_reuse_count_threshold
    ):
        alerts.append(
            {
                "key": "device_reuse_spike",
                "severity": "high",
                "message": (
                    "Hay un aumento de sesiones recientes con reutilizacion sospechosa de dispositivo. "
                    f"casos={data_quality['suspicious_device_reuse_count']}."
                ),
            }
        )

    return {
        "generated_at": now_aware.isoformat(),
        "instance_name": settings.instance_name,
        "windows": {
            "active_seconds": settings.observability_active_window_seconds,
            "recent_seconds": settings.observability_recent_window_seconds,
            "stalled_seconds": settings.observability_stalled_screen_seconds,
        },
        "readiness": readiness,
        "summary": {
            "users_active": active_users,
            "sessions_active": len(active_sessions),
            "sessions_started_total": started_total,
            "sessions_started_recent": recent_started_count,
            "sessions_completed_total": completed_total,
            "sessions_completed_recent": recent_completed_count,
            "valid_sessions_completed_total": len(valid_completed_sessions),
            "completion_rate_total": completion_rate_total,
            "completion_rate_recent": completion_rate_recent,
        },
        "experiment_metrics": experiment_metrics,
        "screen_abandonment": screen_abandonment,
        "data_quality": data_quality,
        "endpoint_metrics": endpoint_metrics,
        "error_metrics": error_metrics,
        "counters": counters,
        "alerts": alerts,
    }


def live_dashboard_payload(db: Session, readiness: dict[str, Any]) -> dict[str, Any]:
    payload = live_metrics_payload(db, readiness)
    payload["payments"] = live_payments_payload(db)
    payload["qr_metrics"] = live_qr_metrics_payload(db)
    payload["referrals"] = live_referral_metrics_payload(db)
    return payload


def live_dashboard_page_html() -> str:
    return """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SONAR Live Metrics</title>
    <style>
      body { font-family: Arial, sans-serif; margin:0; padding:24px; background:#f5f3ee; color:#111; }
      .wrap { max-width:1280px; margin:0 auto; }
      .topbar { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:20px; flex-wrap:wrap; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:20px; }
      .card { background:#fff; border-radius:20px; padding:18px; box-shadow:0 18px 48px rgba(0,0,0,.06); }
      .alert { border-left:6px solid #b42318; }
      .alert.high { border-left-color:#d97706; }
      table { width:100%; border-collapse:collapse; background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 18px 48px rgba(0,0,0,.06); margin-bottom:20px; }
      th, td { padding:12px 14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; font-size:14px; }
      th { background:#f7f4ee; text-transform:uppercase; letter-spacing:.06em; font-size:12px; }
      .two { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
      .muted { color:#666; font-size:14px; }
      .pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#111; color:#fff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
      @media (max-width: 900px) { .two { grid-template-columns:1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="topbar">
        <div>
          <div class="muted">Monitor en tiempo real</div>
          <h1>SONAR Live</h1>
        </div>
        <div class="muted">
          <span class="pill">Refresco 5s</span>
          <span id="generated-at"></span>
        </div>
      </div>
      <div id="alerts"></div>
      <div class="grid" id="summary-grid"></div>
      <div class="two">
        <div>
          <h2>Abandono por pantalla</h2>
          <table>
            <thead><tr><th>Pantalla</th><th>Entradas</th><th>Progresan</th><th>Activas</th><th>Bloqueadas</th><th>Tasa</th></tr></thead>
            <tbody id="screen-abandonment-body"></tbody>
          </table>
        </div>
        <div>
          <h2>Alertas activas</h2>
          <div id="alerts-panel"></div>
        </div>
      </div>
      <h2>Latencia y errores por endpoint</h2>
      <table>
        <thead><tr><th>Endpoint</th><th>Reqs</th><th>Errores</th><th>Tasa error</th><th>Media ms</th><th>P95 ms</th><th>Máx ms</th><th>Último estado</th></tr></thead>
        <tbody id="endpoint-metrics-body"></tbody>
      </table>
      <p class="muted"><a href="/admin/dashboard">Dashboard operativo</a> · <a href="/admin/exports">Exports</a> · <a href="/health/ready">Health ready</a></p>
    </div>
    <script>
      function percent(value) {
        return `${(Number(value || 0) * 100).toFixed(1)}%`;
      }

      function number(value) {
        return value == null ? "-" : String(value);
      }

      function renderSummary(summary, readiness) {
        const items = [
          ["Usuarios activos", summary.users_active],
          ["Sesiones activas", summary.sessions_active],
          ["Sesiones iniciadas", summary.sessions_started_total],
          ["Sesiones iniciadas (ventana)", summary.sessions_started_recent],
          ["Sesiones completadas", summary.sessions_completed_total],
          ["Sesiones completadas (ventana)", summary.sessions_completed_recent],
          ["Completadas válidas", summary.valid_sessions_completed_total],
          ["Conversión total", percent(summary.completion_rate_total)],
          ["Conversión ventana", percent(summary.completion_rate_recent)],
          ["Backend listo", readiness.ok ? "Sí" : "No"],
        ];
        document.getElementById("summary-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><strong>${label}</strong><div>${number(value)}</div></div>`)
          .join("");
      }

      function renderAlerts(alerts) {
        const html = alerts.length
          ? alerts.map((alert) => `<div class="card alert ${alert.severity === "high" ? "high" : ""}"><strong>${alert.key}</strong><div>${alert.message}</div></div>`).join("")
          : `<div class="card"><strong>Sin alertas</strong><div>No hay alertas activas ahora mismo.</div></div>`;
        document.getElementById("alerts").innerHTML = html;
        document.getElementById("alerts-panel").innerHTML = html;
      }

      function renderScreenAbandonment(rows) {
        document.getElementById("screen-abandonment-body").innerHTML = rows
          .map((row) => `<tr><td>${row.screen}</td><td>${row.entered}</td><td>${row.progressed}</td><td>${row.active}</td><td>${row.stalled}</td><td>${percent(row.abandonment_rate)}</td></tr>`)
          .join("");
      }

      function renderEndpointMetrics(rows) {
        document.getElementById("endpoint-metrics-body").innerHTML = rows
          .map((row) => `<tr><td>${row.endpoint}</td><td>${row.count}</td><td>${row.error_count}</td><td>${percent(row.error_rate)}</td><td>${number(row.avg_duration_ms)}</td><td>${number(row.p95_duration_ms)}</td><td>${number(row.max_duration_ms)}</td><td>${number(row.last_status_code)}</td></tr>`)
          .join("");
      }

      async function refresh() {
        const response = await fetch("/admin/metrics", { headers: { "Accept": "application/json" } });
        const data = await response.json();
        document.getElementById("generated-at").textContent = `Última actualización: ${new Date(data.generated_at).toLocaleTimeString()}`;
        renderSummary(data.summary, data.readiness);
        renderAlerts(data.alerts || []);
        renderScreenAbandonment(data.screen_abandonment || []);
        renderEndpointMetrics(data.endpoint_metrics || []);
      }

      refresh();
      window.setInterval(refresh, 5000);
    </script>
  </body>
</html>
"""


def live_dashboard_page_html_v2() -> str:
    return """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SONAR Live Metrics</title>
    <style>
      body { font-family: Arial, sans-serif; margin:0; padding:24px; background:#f5f3ee; color:#111; }
      .wrap { max-width:1280px; margin:0 auto; }
      .topbar { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:20px; flex-wrap:wrap; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:20px; }
      .card { background:#fff; border-radius:20px; padding:18px; box-shadow:0 18px 48px rgba(0,0,0,.06); }
      .alert { border-left:6px solid #b42318; }
      .alert.high { border-left-color:#d97706; }
      table { width:100%; border-collapse:collapse; background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 18px 48px rgba(0,0,0,.06); margin-bottom:20px; }
      th, td { padding:12px 14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; font-size:14px; }
      th { background:#f7f4ee; text-transform:uppercase; letter-spacing:.06em; font-size:12px; }
      .two { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
      .muted { color:#666; font-size:14px; }
      .pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#111; color:#fff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
      @media (max-width: 900px) { .two { grid-template-columns:1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="topbar">
        <div>
          <div class="muted">Monitor en tiempo real</div>
          <h1>SONAR Live</h1>
        </div>
        <div class="muted">
          <span class="pill">Refresco 5s</span>
          <span id="generated-at"></span>
        </div>
      </div>
      <div id="alerts"></div>
      <div class="grid" id="summary-grid"></div>
      <div class="two">
        <div>
          <h2>Abandono por pantalla</h2>
          <table>
            <thead><tr><th>Pantalla</th><th>Entradas</th><th>Progresan</th><th>Activas</th><th>Bloqueadas</th><th>Tasa</th></tr></thead>
            <tbody id="screen-abandonment-body"></tbody>
          </table>
        </div>
        <div>
          <h2>Alertas activas</h2>
          <div id="alerts-panel"></div>
        </div>
      </div>
      <div class="two">
        <div>
          <h2>Calidad de datos</h2>
          <div class="grid" id="quality-grid"></div>
        </div>
        <div>
          <h2>Distribucion reciente</h2>
          <table>
            <thead><tr><th>Valor</th><th>Reportado</th><th>Verdad</th></tr></thead>
            <tbody id="quality-distribution-body"></tbody>
          </table>
        </div>
      </div>
      <h2>Latencia y errores por endpoint</h2>
      <table>
        <thead><tr><th>Endpoint</th><th>Reqs</th><th>Errores</th><th>Tasa error</th><th>Media ms</th><th>P95 ms</th><th>Max ms</th><th>Ultimo estado</th></tr></thead>
        <tbody id="endpoint-metrics-body"></tbody>
      </table>
      <p class="muted"><a href="/admin/dashboard">Dashboard operativo</a> · <a href="/admin/exports">Exports</a> · <a href="/health/ready">Health ready</a></p>
    </div>
    <script>
      function percent(value) {
        return `${(Number(value || 0) * 100).toFixed(1)}%`;
      }

      function number(value) {
        return value == null ? "-" : String(value);
      }

      function renderSummary(summary, readiness) {
        const items = [
          ["Usuarios activos", summary.users_active],
          ["Sesiones activas", summary.sessions_active],
          ["Sesiones iniciadas", summary.sessions_started_total],
          ["Sesiones iniciadas (ventana)", summary.sessions_started_recent],
          ["Sesiones completadas", summary.sessions_completed_total],
          ["Sesiones completadas (ventana)", summary.sessions_completed_recent],
          ["Completadas validas", summary.valid_sessions_completed_total],
          ["Conversion total", percent(summary.completion_rate_total)],
          ["Conversion ventana", percent(summary.completion_rate_recent)],
          ["Backend listo", readiness.ok ? "Si" : "No"],
        ];
        document.getElementById("summary-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><strong>${label}</strong><div>${number(value)}</div></div>`)
          .join("");
      }

      function renderAlerts(alerts) {
        const html = alerts.length
          ? alerts.map((alert) => `<div class="card alert ${alert.severity === "high" ? "high" : ""}"><strong>${alert.key}</strong><div>${alert.message}</div></div>`).join("")
          : `<div class="card"><strong>Sin alertas</strong><div>No hay alertas activas ahora mismo.</div></div>`;
        document.getElementById("alerts").innerHTML = html;
        document.getElementById("alerts-panel").innerHTML = html;
      }

      function renderScreenAbandonment(rows) {
        document.getElementById("screen-abandonment-body").innerHTML = rows
          .map((row) => `<tr><td>${row.screen}</td><td>${row.entered}</td><td>${row.progressed}</td><td>${row.active}</td><td>${row.stalled}</td><td>${percent(row.abandonment_rate)}</td></tr>`)
          .join("");
      }

      function renderQuality(data) {
        const items = [
          ["Completadas (ventana)", data.window_completed_sessions],
          ["First throw rapido", percent(data.fast_first_throw_rate)],
          ["Reporte rapido", percent(data.fast_report_rate)],
          ["Snapshots rotos", data.snapshot_missing_count],
          ["Submit sin prepare", data.submit_without_prepare_count],
          ["Control contaminado", data.control_contamination_count],
          ["Reuse sospechoso", data.suspicious_device_reuse_count],
          ["Gap reportado vs verdad del 6", percent(data.report_truth_six_gap)],
          ["Valor dominante reportado", data.dominant_report_value || "-"],
          ["Share dominante", percent(data.dominant_report_share)],
        ];
        document.getElementById("quality-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><strong>${label}</strong><div>${number(value)}</div></div>`)
          .join("");

        const values = ["1", "2", "3", "4", "5", "6"];
        document.getElementById("quality-distribution-body").innerHTML = values
          .map((value) => `<tr><td>${value}</td><td>${number(data.report_distribution?.[value] ?? 0)}</td><td>${number(data.truth_distribution?.[value] ?? 0)}</td></tr>`)
          .join("");
      }

      function renderEndpointMetrics(rows) {
        document.getElementById("endpoint-metrics-body").innerHTML = rows
          .map((row) => `<tr><td>${row.endpoint}</td><td>${row.count}</td><td>${row.error_count}</td><td>${percent(row.error_rate)}</td><td>${number(row.avg_duration_ms)}</td><td>${number(row.p95_duration_ms)}</td><td>${number(row.max_duration_ms)}</td><td>${number(row.last_status_code)}</td></tr>`)
          .join("");
      }

      async function refresh() {
        const response = await fetch("/admin/metrics", { headers: { "Accept": "application/json" } });
        const data = await response.json();
        document.getElementById("generated-at").textContent = `Ultima actualizacion: ${new Date(data.generated_at).toLocaleTimeString()}`;
        renderSummary(data.summary, data.readiness);
        renderAlerts(data.alerts || []);
        renderScreenAbandonment(data.screen_abandonment || []);
        renderQuality(data.data_quality || {});
        renderEndpointMetrics(data.endpoint_metrics || []);
      }

      refresh();
      window.setInterval(refresh, 5000);
    </script>
  </body>
</html>
"""


def live_dashboard_page_html_v3() -> str:
    return """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SONAR Live Dashboard</title>
    <style>
      body { font-family: Arial, sans-serif; margin:0; padding:24px; background:#f5f3ee; color:#111; }
      .wrap { max-width:1400px; margin:0 auto; }
      .topbar { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:20px; flex-wrap:wrap; }
      .summary-grid, .mini-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:20px; }
      .section-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:20px; margin-bottom:20px; }
      .card { background:#fff; border-radius:20px; padding:18px; box-shadow:0 18px 48px rgba(0,0,0,.06); }
      .card h2 { margin:0 0 14px; font-size:20px; }
      .metric-label { color:#666; font-size:12px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:8px; }
      .metric-value { font-size:28px; font-weight:700; }
      .metric-subvalue { font-size:14px; color:#666; margin-top:6px; }
      .alert { border-left:6px solid #b42318; margin-bottom:12px; }
      .alert.high { border-left-color:#d97706; }
      .alert.medium { border-left-color:#2563eb; }
      table { width:100%; border-collapse:collapse; background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 18px 48px rgba(0,0,0,.06); }
      th, td { padding:12px 14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; font-size:14px; }
      th { background:#f7f4ee; text-transform:uppercase; letter-spacing:.06em; font-size:12px; }
      .muted { color:#666; font-size:14px; }
      .pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#111; color:#fff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
      .bar-list { display:flex; flex-direction:column; gap:10px; }
      .bar-row { display:grid; grid-template-columns:88px 1fr 64px; gap:12px; align-items:center; }
      .bar-track { height:12px; background:#ece8df; border-radius:999px; overflow:hidden; }
      .bar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#0f766e,#14b8a6); }
      .bar-fill-secondary { background:linear-gradient(90deg,#1d4ed8,#60a5fa); }
      .timeseries-bars { display:grid; gap:10px; }
      .timeseries-row { display:grid; grid-template-columns:72px 1fr auto; gap:12px; align-items:center; }
      .tiny { font-size:12px; color:#666; }
      .status-dot { display:inline-block; width:10px; height:10px; border-radius:999px; margin-right:8px; }
      .status-ok { background:#15803d; }
      .status-bad { background:#b91c1c; }
      .links { margin-top:20px; }
      .links a { color:#0f766e; text-decoration:none; margin-right:12px; }
      @media (max-width: 980px) { .section-grid { grid-template-columns:1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="topbar">
        <div>
          <div class="muted">Panel operativo en tiempo real</div>
          <h1>SONAR Live Dashboard</h1>
        </div>
        <div class="muted">
          <span class="pill">Refresco 5s</span>
          <span id="generated-at"></span><br />
          <span id="readiness-state"></span>
        </div>
      </div>
      <div id="alerts"></div>
      <div class="summary-grid" id="summary-grid"></div>

      <div class="section-grid">
        <div class="card">
          <h2>Experimento</h2>
          <div class="mini-grid" id="experiment-kpi-grid"></div>
          <div class="timeseries-bars" id="experiment-timeseries"></div>
        </div>
        <div class="card">
          <h2>Distribucion de resultados</h2>
          <div class="bar-list" id="distribution-bars"></div>
        </div>
      </div>

      <div class="section-grid">
        <div class="card">
          <h2>Pagos</h2>
          <div class="mini-grid" id="payments-grid"></div>
          <table>
            <thead><tr><th>Pulsera</th><th>Codigo</th><th>Importe</th><th>Donacion</th><th>Hora</th></tr></thead>
            <tbody id="payments-body"></tbody>
          </table>
        </div>
        <div class="card">
          <h2>QR y zonas</h2>
          <div class="mini-grid" id="qr-grid"></div>
          <div class="bar-list" id="zone-bars"></div>
          <table>
            <thead><tr><th>QR</th><th>Zona</th><th>Escaneos</th><th>Entradas</th><th>Conv.</th></tr></thead>
            <tbody id="qr-body"></tbody>
          </table>
        </div>
      </div>

      <div class="section-grid">
        <div class="card">
          <h2>Viralidad</h2>
          <div class="mini-grid" id="referral-grid"></div>
          <table>
            <thead><tr><th>Invitador</th><th>Links</th><th>Clicks</th><th>Usuarios</th><th>Ratio</th></tr></thead>
            <tbody id="referral-body"></tbody>
          </table>
        </div>
        <div class="card">
          <h2>Abandono y calidad</h2>
          <table>
            <thead><tr><th>Pantalla</th><th>Entradas</th><th>Progresan</th><th>Activas</th><th>Bloqueadas</th><th>Tasa</th></tr></thead>
            <tbody id="screen-abandonment-body"></tbody>
          </table>
          <div class="mini-grid" id="quality-grid"></div>
        </div>
      </div>

      <div class="card">
        <h2>Latencia y errores</h2>
        <table>
          <thead><tr><th>Endpoint</th><th>Reqs</th><th>Errores</th><th>Tasa error</th><th>Media ms</th><th>P95 ms</th><th>Max ms</th><th>Ultimo estado</th></tr></thead>
          <tbody id="endpoint-metrics-body"></tbody>
        </table>
      </div>

      <p class="links">
        <a href="/admin/dashboard/live">JSON live</a>
        <a href="/admin/metrics">Metricas base</a>
        <a href="/admin/gateway/summary">QR JSON</a>
        <a href="/admin/referrals/summary">Referrals JSON</a>
        <a href="/admin/dashboard">Dashboard operativo</a>
        <a href="/admin/exports">Exports</a>
        <a href="/health/ready">Health ready</a>
      </p>
    </div>
    <script>
      function percent(value) {
        return `${(Number(value || 0) * 100).toFixed(1)}%`;
      }

      function number(value) {
        return value == null ? "-" : String(value);
      }

      function formatTime(value) {
        if (!value) return "-";
        return new Date(value).toLocaleTimeString();
      }

      function renderSummary(summary, readiness, experiment, payments, qr, referrals) {
        const items = [
          ["Participantes totales", experiment.participants_total, `Ventana: ${number(experiment.participants_recent)}`],
          ["Participantes activos", summary.users_active, `Sesiones activas: ${number(summary.sessions_active)}`],
          ["Completados", summary.sessions_completed_total, `Validos: ${number(summary.valid_sessions_completed_total)}`],
          ["Tasa finalizacion", percent(summary.completion_rate_total), `Ventana: ${percent(summary.completion_rate_recent)}`],
          ["Ganadores", payments.summary.winners_total, `Importe: ${number(payments.summary.amount_total_eur)} EUR`],
          ["Escaneos QR", qr.summary.scans_total, `Entradas: ${number(qr.summary.sessions_started)}`],
          ["Invitaciones", referrals.summary.invitations_sent_total, `Usuarios por referral: ${number(referrals.summary.users_by_referral_total)}`],
          ["Backend", readiness.ok ? "Listo" : "No listo", readiness.ok ? "Sin bloqueo de readiness" : "Revisar dependencias"],
        ];
        document.getElementById("summary-grid").innerHTML = items
          .map(([label, value, subvalue]) => `
            <div class="card">
              <div class="metric-label">${label}</div>
              <div class="metric-value">${number(value)}</div>
              <div class="metric-subvalue">${subvalue || ""}</div>
            </div>
          `)
          .join("");
        document.getElementById("readiness-state").innerHTML = readiness.ok
          ? `<span class="status-dot status-ok"></span>Backend listo`
          : `<span class="status-dot status-bad"></span>Backend no listo`;
      }

      function renderAlerts(alerts) {
        const html = alerts.length
          ? alerts.map((alert) => `<div class="card alert ${alert.severity || ""}"><strong>${alert.key}</strong><div>${alert.message}</div></div>`).join("")
          : `<div class="card"><strong>Sin alertas</strong><div>No hay alertas activas ahora mismo.</div></div>`;
        document.getElementById("alerts").innerHTML = html;
      }

      function renderScreenAbandonment(rows) {
        document.getElementById("screen-abandonment-body").innerHTML = rows
          .map((row) => `<tr><td>${row.screen}</td><td>${row.entered}</td><td>${row.progressed}</td><td>${row.active}</td><td>${row.stalled}</td><td>${percent(row.abandonment_rate)}</td></tr>`)
          .join("");
      }

      function renderQuality(data) {
        const items = [
          ["Completadas (ventana)", data.window_completed_sessions],
          ["First throw rapido", percent(data.fast_first_throw_rate)],
          ["Reporte rapido", percent(data.fast_report_rate)],
          ["Snapshots rotos", data.snapshot_missing_count],
          ["Submit sin prepare", data.submit_without_prepare_count],
          ["Control contaminado", data.control_contamination_count],
          ["Reuse sospechoso", data.suspicious_device_reuse_count],
          ["Gap reportado vs verdad del 6", percent(data.report_truth_six_gap)],
          ["Valor dominante reportado", data.dominant_report_value || "-"],
          ["Share dominante", percent(data.dominant_report_share)],
        ];
        document.getElementById("quality-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><div class="metric-label">${label}</div><div class="metric-value">${number(value)}</div></div>`)
          .join("");
      }

      function renderExperiment(experiment) {
        const kpis = [
          ["Tasa de 6 reportado", percent(experiment.reported_six_rate_total)],
          ["Mentiras", percent(experiment.lie_rate_total)],
          ["Claims", number(experiment.claims_total)],
          ["Bucket", `${number(experiment.timeseries_bucket_minutes)} min`],
        ];
        document.getElementById("experiment-kpi-grid").innerHTML = kpis
          .map(([label, value]) => `<div class="card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div></div>`)
          .join("");

        const maxStarted = Math.max(1, ...((experiment.timeseries || []).map((item) => item.participants_started || 0)));
        document.getElementById("experiment-timeseries").innerHTML = (experiment.timeseries || [])
          .slice(-12)
          .map((item) => `
            <div class="timeseries-row">
              <div class="tiny">${new Date(item.bucket_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
              <div class="bar-track"><div class="bar-fill" style="width:${((item.participants_started || 0) / maxStarted) * 100}%"></div></div>
              <div class="tiny">start ${number(item.participants_started)} | comp ${number(item.participants_completed)} | 6 ${percent(item.reported_six_rate)}</div>
            </div>
          `)
          .join("");
      }

      function renderDistribution(data) {
        const values = ["1", "2", "3", "4", "5", "6"];
        const maxValue = Math.max(
          1,
          ...values.map((value) => Math.max(
            data.report_distribution?.[value] ?? 0,
            data.truth_distribution?.[value] ?? 0,
          )),
        );
        document.getElementById("distribution-bars").innerHTML = values
          .map((value) => `
            <div class="bar-row">
              <div>${value}</div>
              <div>
                <div class="tiny">Reportado ${number(data.report_distribution?.[value] ?? 0)}</div>
                <div class="bar-track"><div class="bar-fill" style="width:${(((data.report_distribution?.[value] ?? 0) / maxValue) * 100)}%"></div></div>
                <div class="tiny" style="margin-top:6px;">Verdad ${number(data.truth_distribution?.[value] ?? 0)}</div>
                <div class="bar-track"><div class="bar-fill bar-fill-secondary" style="width:${(((data.truth_distribution?.[value] ?? 0) / maxValue) * 100)}%"></div></div>
              </div>
              <div class="tiny">${number((data.report_distribution?.[value] ?? 0) - (data.truth_distribution?.[value] ?? 0))}</div>
            </div>
          `)
          .join("");
      }

      function renderPayments(data) {
        const summary = data.summary || {};
        const items = [
          ["Ganadores", summary.winners_total],
          ["Solicitudes", summary.payment_requests_total],
          ["Importe total", `${number(summary.amount_total_eur)} EUR`],
          ["Donaciones", summary.donations_total],
        ];
        document.getElementById("payments-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div></div>`)
          .join("");
        document.getElementById("payments-body").innerHTML = (data.recent_winners || [])
          .map((item) => `<tr><td>${item.bracelet_id || "-"}</td><td>${item.reference_code}</td><td>${number(item.amount_eur)} EUR</td><td>${item.donation_requested ? "Si" : "No"}</td><td>${formatTime(item.submitted_at)}</td></tr>`)
          .join("");
      }

      function renderQrMetrics(data) {
        const summary = data.summary || {};
        const items = [
          ["QR activos", summary.qr_count],
          ["Zonas", summary.zone_count],
          ["Escaneos", summary.scans_total],
          ["Entradas", summary.sessions_started],
        ];
        document.getElementById("qr-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><div class="metric-label">${label}</div><div class="metric-value">${number(value)}</div></div>`)
          .join("");

        const topZones = (data.by_zone || []).slice(0, 8);
        const maxZoneScans = Math.max(1, ...topZones.map((item) => item.scans_total || 0));
        document.getElementById("zone-bars").innerHTML = topZones
          .map((item) => `
            <div class="bar-row">
              <div>${item.zone_code}</div>
              <div class="bar-track"><div class="bar-fill bar-fill-secondary" style="width:${((item.scans_total || 0) / maxZoneScans) * 100}%"></div></div>
              <div class="tiny">${number(item.scans_total)} / ${percent(item.conversion_rate)}</div>
            </div>
          `)
          .join("");

        document.getElementById("qr-body").innerHTML = (data.by_qr || [])
          .slice(0, 12)
          .map((item) => `<tr><td>${item.qr_code}</td><td>${item.zone_code}</td><td>${number(item.scans_total)}</td><td>${number(item.sessions_started)}</td><td>${percent(item.conversion_rate)}</td></tr>`)
          .join("");
      }

      function renderReferrals(data) {
        const summary = data.summary || {};
        const items = [
          ["Invitaciones", summary.invitations_sent_total],
          ["Clicks", summary.clicks_total],
          ["Usuarios por referral", summary.users_by_referral_total],
          ["Ratio invite -> entry", percent(summary.invite_to_entry_ratio)],
        ];
        document.getElementById("referral-grid").innerHTML = items
          .map(([label, value]) => `<div class="card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div></div>`)
          .join("");
        document.getElementById("referral-body").innerHTML = (data.top_inviters || [])
          .slice(0, 12)
          .map((item) => `<tr><td>${item.referral_code}</td><td>${number(item.links_total)}</td><td>${number(item.clicks_total)}</td><td>${number(item.users_by_referral)}</td><td>${percent(item.invite_to_entry_ratio)}</td></tr>`)
          .join("");
      }

      function renderEndpointMetrics(rows) {
        document.getElementById("endpoint-metrics-body").innerHTML = rows
          .map((row) => `<tr><td>${row.endpoint}</td><td>${row.count}</td><td>${row.error_count}</td><td>${percent(row.error_rate)}</td><td>${number(row.avg_duration_ms)}</td><td>${number(row.p95_duration_ms)}</td><td>${number(row.max_duration_ms)}</td><td>${number(row.last_status_code)}</td></tr>`)
          .join("");
      }

      async function refresh() {
        const response = await fetch("/admin/dashboard/live", { headers: { "Accept": "application/json" } });
        const data = await response.json();
        document.getElementById("generated-at").textContent = `Ultima actualizacion: ${new Date(data.generated_at).toLocaleTimeString()}`;
        renderSummary(
          data.summary || {},
          data.readiness || {},
          data.experiment_metrics || {},
          data.payments || {},
          data.qr_metrics || {},
          data.referrals || {},
        );
        renderAlerts(data.alerts || []);
        renderScreenAbandonment(data.screen_abandonment || []);
        renderExperiment(data.experiment_metrics || {});
        renderDistribution(data.data_quality || {});
        renderPayments(data.payments || {});
        renderQrMetrics(data.qr_metrics || {});
        renderReferrals(data.referrals || {});
        renderQuality(data.data_quality || {});
        renderEndpointMetrics(data.endpoint_metrics || []);
      }

      refresh();
      window.setInterval(refresh, 5000);
    </script>
  </body>
</html>
"""


def dashboard_page_html(db: Session) -> str:
    state = db.get(ExperimentState, "global")
    active_operational_note = db.exec(
        select(OperationalNote)
        .where(OperationalNote.status == "active")
        .order_by(OperationalNote.effective_from.desc())
    ).first()
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    claims = db.exec(select(Claim)).all()
    payments = db.exec(select(Payment)).all()
    telemetry = db.exec(select(TelemetryEvent)).all()
    screen_spells = db.exec(select(ScreenSpell)).all()
    fraud_flags = db.exec(select(FraudFlag)).all()
    interest_signups = db.exec(select(InterestSignup)).all()
    treatment_decks = treatment_decks_rows(db)
    result_decks = result_decks_rows(db)
    payment_decks = payment_decks_rows(db)

    completed_valid = [item for item in sessions if item.is_valid_completed]
    dropout_by_screen: dict[str, int] = {}
    treatment_balance: dict[str, int] = {treatment_key: 0 for treatment_key in TREATMENT_KEYS}
    reported_distribution = {value: 0 for value in range(1, 7)}
    truth_distribution = {value: 0 for value in range(1, 7)}
    quality_distribution: dict[str, int] = {}
    fraud_distribution: dict[str, int] = {}
    screen_durations: dict[str, list[int]] = {}
    rerolls = [item.reroll_count for item in sessions]
    network_errors = [
        item
        for item in telemetry
        if item.event_type == "error" or (item.status_code or 0) >= 400
    ]
    eligible_payments = [item for item in payments if item.eligible]
    total_prize_amount_eur = round(sum(item.amount_cents for item in eligible_payments) / 100, 2)
    demo_id_lines = [
        "CTRL1234 -> control + ganador",
        "NORM0000 -> norm_0 + perder",
        "NORM0001 -> norm_1 + perder",
    ]
    escaped_pause_reason = escape(state.pause_reason) if state and state.pause_reason else ""
    escaped_operational_note = escape(active_operational_note.note_text) if active_operational_note else ""
    escaped_operational_note_since = (
        active_operational_note.effective_from.isoformat() if active_operational_note else ""
    )
    experiment_mode = escape(state.experiment_mode if state else "live")
    experiment_mode_changed_at = (
        state.experiment_mode_changed_at.isoformat()
        if state and state.experiment_mode_changed_at
        else ""
    )
    experiment_mode_changed_by = escape(state.experiment_mode_changed_by) if state and state.experiment_mode_changed_by else ""

    for session_record in sessions:
        treatment_balance[session_record.treatment_key] = (
            treatment_balance.get(session_record.treatment_key, 0) + 1
        )
        if not session_record.completed_at:
            dropout_by_screen[session_record.screen_cursor] = (
                dropout_by_screen.get(session_record.screen_cursor, 0) + 1
            )
        for flag in parse_json_list(session_record.quality_flags_json):
            quality_distribution[flag] = quality_distribution.get(flag, 0) + 1

    for claim in claims:
        reported_distribution[claim.reported_value] += 1
        truth_distribution[claim.true_first_result] += 1

    for spell in screen_spells:
        if spell.screen_name and (spell.visible_ms or spell.duration_total_ms):
            screen_durations.setdefault(spell.screen_name, []).append(
                int(spell.visible_ms or spell.duration_total_ms or 0)
            )

    for flag in fraud_flags:
        fraud_distribution[flag.flag_key] = fraud_distribution.get(flag.flag_key, 0) + 1

    screen_stats_rows = "".join(
        f"<tr><td>{escape(screen)}</td><td>{len(values)}</td><td>{mean(values) or 0}</td></tr>"
        for screen, values in sorted(screen_durations.items())
    ) or "<tr><td colspan='3'>Sin datos</td></tr>"

    return f"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Dashboard SONAR</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin:0; padding:24px; background:#f6f4ee; color:#111; }}
      .wrap {{ max-width:1200px; margin:0 auto; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-bottom:24px; }}
      .card {{ background:white; border-radius:20px; padding:20px; box-shadow:0 18px 48px rgba(0,0,0,.06); }}
      h1,h2 {{ text-transform:uppercase; margin:0 0 12px; }}
      table {{ width:100%; border-collapse:collapse; background:white; border-radius:20px; overflow:hidden; margin-bottom:20px; }}
      th,td {{ padding:12px 14px; border-bottom:1px solid rgba(0,0,0,.08); text-align:left; }}
      .two {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
      .three {{ display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }}
      .controls {{ display:grid; gap:12px; }}
      .control-row {{ display:flex; gap:12px; flex-wrap:wrap; }}
      .status {{ font-size:14px; color:#555; }}
      input, textarea {{ width:100%; box-sizing:border-box; padding:12px 14px; border-radius:14px; border:1px solid rgba(0,0,0,.12); font-size:14px; }}
      textarea {{ min-height:110px; resize:vertical; }}
      button {{ padding:12px 18px; border:none; border-radius:999px; background:#111; color:white; font-weight:700; letter-spacing:.08em; text-transform:uppercase; cursor:pointer; }}
      button.secondary {{ background:white; color:#111; border:1px solid rgba(0,0,0,.12); }}
      button.warning {{ background:#b45309; }}
      button.danger {{ background:#b91c1c; }}
      ul {{ margin:0; padding-left:18px; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <p>Investigador</p>
      <h1>Dashboard cientifico-operativo</h1>
      <div class="grid">
        <div class="card"><strong>Diseno</strong><div>{escape(state.current_phase if state else PHASE_1_MAIN)}</div></div>
        <div class="card"><strong>Estado</strong><div>{escape(state.experiment_status if state else 'active')}</div></div>
        <div class="card"><strong>Modo</strong><div>{experiment_mode}</div></div>
        <div class="card"><strong>Sesiones iniciadas</strong><div>{len(sessions)}</div></div>
        <div class="card"><strong>Completadas validas</strong><div>{len(completed_valid)}</div></div>
        <div class="card"><strong>Claims</strong><div>{len(claims)}</div></div>
        <div class="card"><strong>Personas premiadas</strong><div>{len(eligible_payments)}</div></div>
        <div class="card"><strong>Importe total de premios</strong><div>{total_prize_amount_eur} EUR</div></div>
        <div class="card"><strong>Emails interes</strong><div>{len(interest_signups)}</div></div>
        <div class="card"><strong>Media rerolls</strong><div>{mean(rerolls) or 0}</div></div>
        <div class="card"><strong>Errores tecnicos</strong><div>{len(network_errors)}</div></div>
        <div class="card"><strong>Reportes de 6</strong><div>{reported_distribution[6]}</div></div>
        <div class="card"><strong>Verdades de 6</strong><div>{truth_distribution[6]}</div></div>
      </div>
      <div class="card controls">
        <h2>Control del experimento</h2>
        <div class="status">
          Estado actual: <strong>{escape(state.experiment_status if state else 'active')}</strong>
          {" | Pausado en: " + state.paused_at.isoformat() if state and state.paused_at else ""}
        </div>
        <div class="status">
          Modo actual: <strong>{experiment_mode}</strong>
          {" | Cambiado en: " + experiment_mode_changed_at if experiment_mode_changed_at else ""}
          {" | Por: " + experiment_mode_changed_by if experiment_mode_changed_by else ""}
        </div>
        <input id="experiment-reason" placeholder="Motivo interno opcional: pausa operativa, incidencia tecnica, control de campo..." />
        {"<div class='status'>Ultimo motivo de pausa: <strong>" + escaped_pause_reason + "</strong></div>" if escaped_pause_reason else ""}
        <div class="control-row">
          <button id="pause-button">Parar experimento</button>
          <button id="resume-button" class="secondary">Reactivar experimento</button>
        </div>
        <div class="control-row">
          <button id="panic-soft-button" class="warning">Activar cierre suave</button>
          <button id="panic-hard-button" class="danger">Cerrar ahora</button>
        </div>
        <div class="status">
          `closing` bloquea nuevas entradas y deja terminar sesiones activas. `closed` corta tambien las sesiones en curso.
        </div>
        <div class="status danger" style="margin-top:16px;">
          Reinicio total online: borra sesiones, claims, pagos, QR, referrals, telemetria y metricas acumuladas. Despues deja el backend otra vez en `live`.
        </div>
        <input
          id="reset-passphrase"
          type="password"
          placeholder="Contrasena de reinicio total"
          autocomplete="off"
          spellcheck="false"
        />
        <div class="control-row">
          <button id="system-reset-button" class="danger">Reiniciar todo online</button>
        </div>
        <div id="control-status" class="status"></div>
      </div>
      <div class="card controls">
        <h2>Contexto operativo</h2>
        <div class="status">
          {"Nota activa desde: <strong>" + escaped_operational_note_since + "</strong>" if escaped_operational_note_since else "No hay nota operativa activa."}
        </div>
        {"<div class='status'><strong>Nota actual:</strong> " + escaped_operational_note + "</div>" if escaped_operational_note else ""}
        <textarea id="operational-note-text" placeholder="Escribe aqui incidencias operativas, cambios de ubicacion, pausas o anotaciones de campo.">{escaped_operational_note}</textarea>
        <div class="control-row">
          <button id="operational-note-save">Guardar nota activa</button>
          <button id="operational-note-clear" class="secondary">Cerrar nota activa</button>
        </div>
        <div id="operational-note-status" class="status"></div>
      </div>
      <div class="two">
        <div><h2>Balance por tratamiento</h2><table><tbody>{_rows_from_counter(treatment_balance)}</tbody></table></div>
        <div><h2>Dropout por pantalla</h2><table><tbody>{_rows_from_counter(dropout_by_screen)}</tbody></table></div>
      </div>
      <div class="two">
        <div><h2>Distribucion de reportes</h2><table><tbody>{_rows_from_counter(reported_distribution)}</tbody></table></div>
        <div><h2>Distribucion real primera tirada</h2><table><tbody>{_rows_from_counter(truth_distribution)}</tbody></table></div>
      </div>
      <div class="two">
        <div><h2>Flags de calidad</h2><table><tbody>{_rows_from_counter(quality_distribution)}</tbody></table></div>
        <div><h2>Flags de fraude</h2><table><tbody>{_rows_from_counter(fraud_distribution)}</tbody></table></div>
      </div>
      <div class="two">
        <div>
          <h2>Screen timings</h2>
          <table><thead><tr><th>Pantalla</th><th>Eventos</th><th>Media ms</th></tr></thead><tbody>{screen_stats_rows}</tbody></table>
        </div>
        <div class="card">
          <h2>Demo IDs</h2>
          <ul>{''.join(f'<li>{escape(item)}</li>' for item in demo_id_lines)}</ul>
          <p style="margin-top:12px;">WhatsApp de soporte cobro: {escape(public_support()['winner_whatsapp_phone'])}</p>
        </div>
      </div>
      <div class="three">
        <div>
          <h2>Mazos de tratamientos</h2>
          <table>
            <thead><tr><th>Deck</th><th>Estado</th><th>Asignadas</th><th>Restantes</th><th>Cartas</th></tr></thead>
            <tbody>{_rows_from_decks(treatment_decks, deck_label='tratamientos')}</tbody>
          </table>
        </div>
        <div>
          <h2>Mazos de resultados</h2>
          <table>
            <thead><tr><th>Tratamiento</th><th>Ciclo</th><th>Deck</th><th>Estado</th><th>Asignadas</th><th>Restantes</th><th>Cartas</th></tr></thead>
            <tbody>{_rows_from_result_decks(result_decks)}</tbody>
          </table>
        </div>
        <div>
          <h2>Mazos de pago</h2>
          <table>
            <thead><tr><th>Deck</th><th>Estado</th><th>Asignadas</th><th>Restantes</th><th>Cartas</th></tr></thead>
            <tbody>{_rows_from_decks(payment_decks, deck_label='pagos')}</tbody>
          </table>
        </div>
      </div>
      <p><a href="/admin/exports">Ir a Data Exports</a></p>
    </div>
    <script>
      async function postExperimentControl(path) {{
        const status = document.getElementById('control-status');
        const reason = document.getElementById('experiment-reason').value;
        status.textContent = 'Actualizando estado del experimento...';
        try {{
          const response = await fetch(path, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ reason }})
          }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'No se pudo actualizar el estado');
          status.textContent = `Estado actualizado: ${{data.experiment_status}}. Ganadores: ${{data.prizes.winner_count}}. Total comprometido: ${{data.prizes.total_prize_amount_eur}} EUR.`;
          window.setTimeout(() => window.location.reload(), 700);
        }} catch (error) {{
          status.textContent = error.message || 'No se pudo actualizar el estado';
        }}
      }}
      async function postPanic(mode, confirmationText) {{
        const status = document.getElementById('control-status');
        const reason = document.getElementById('experiment-reason').value;
        if (!window.confirm(confirmationText)) {{
          return;
        }}
        status.textContent = 'Activando cierre del experimento...';
        try {{
          const response = await fetch('/admin/panic', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(mode === 'closing'
              ? {{ soft: true, reason }}
              : {{ mode: 'closed', reason }}),
          }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'No se pudo activar el cierre');
          status.textContent = `Modo actualizado: ${{data.experiment_mode}}. Entradas nuevas: ${{data.accepting_entries ? 'abiertas' : 'cerradas'}}. Sesiones en curso: ${{data.accepting_inflight_sessions ? 'permitidas' : 'bloqueadas'}}.`;
          window.setTimeout(() => window.location.reload(), 700);
        }} catch (error) {{
          status.textContent = error.message || 'No se pudo activar el cierre';
        }}
      }}
      async function postSystemReset() {{
        const status = document.getElementById('control-status');
        const reason = document.getElementById('experiment-reason').value;
        const passphrase = document.getElementById('reset-passphrase').value;
        if (!passphrase.trim()) {{
          status.textContent = 'Escribe la contrasena de reinicio total.';
          return;
        }}
        if (!window.confirm('Esto borrara todos los datos online del experimento y reabrira el sistema vacio. Quieres continuar?')) {{
          return;
        }}
        status.textContent = 'Reiniciando todo el sistema online...';
        try {{
          const response = await fetch('/admin/system/reset', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ passphrase, reason }}),
          }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'No se pudo reiniciar el sistema');
          document.getElementById('reset-passphrase').value = '';
          status.textContent = `Reset completado. Sesiones antes: ${{data.before_counts.sessions}}. Sesiones ahora: ${{data.after_counts.sessions}}. Backend listo: ${{data.readiness.ok ? 'si' : 'no'}}.`;
          window.setTimeout(() => window.location.reload(), 1200);
        }} catch (error) {{
          status.textContent = error.message || 'No se pudo reiniciar el sistema';
        }}
      }}
      async function postOperationalNote(path, body) {{
        const status = document.getElementById('operational-note-status');
        status.textContent = 'Actualizando contexto operativo...';
        try {{
          const response = await fetch(path, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: body ? JSON.stringify(body) : null,
          }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'No se pudo actualizar la nota operativa');
          const note = data.active_operational_note?.note_text || 'Sin nota activa';
          status.textContent = `Contexto operativo actualizado. Nota activa: ${{note}}`;
          window.setTimeout(() => window.location.reload(), 700);
        }} catch (error) {{
          status.textContent = error.message || 'No se pudo actualizar la nota operativa';
        }}
      }}
      document.getElementById('pause-button').addEventListener('click', () => postExperimentControl('/admin/experiment/pause'));
      document.getElementById('resume-button').addEventListener('click', () => postExperimentControl('/admin/experiment/resume'));
      document.getElementById('panic-soft-button').addEventListener('click', () => postPanic(
        'closing',
        'Se bloquearan nuevas entradas pero las sesiones ya iniciadas podran terminar. Quieres activar el cierre suave?'
      ));
      document.getElementById('panic-hard-button').addEventListener('click', () => postPanic(
        'closed',
        'Se cerrara el experimento de inmediato y tambien se bloquearan las sesiones en curso. Quieres continuar?'
      ));
      document.getElementById('system-reset-button').addEventListener('click', () => postSystemReset());
      document.getElementById('operational-note-save').addEventListener('click', () => {{
        const noteText = document.getElementById('operational-note-text').value.trim();
        if (!noteText) {{
          document.getElementById('operational-note-status').textContent = 'Escribe una nota antes de guardarla.';
          return;
        }}
        postOperationalNote('/admin/operational-notes/activate', {{ note_text: noteText }});
      }});
      document.getElementById('operational-note-clear').addEventListener('click', () => postOperationalNote('/admin/operational-notes/clear'));
    </script>
  </body>
</html>
"""


def export_filename(prefix: str, extension: str) -> str:
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{extension}"


def dataset_export_stats(db: Session) -> dict[str, dict[str, Any]]:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    stats: dict[str, dict[str, Any]] = {}
    for dataset_name in DATASET_DESCRIPTIONS:
        try:
            rows = dataset_rows(db, dataset_name)
            csv_bytes = rows_to_csv_bytes(rows)
            size_bytes = len(csv_bytes)
            if size_bytes < 1024:
                size_label = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_label = f"{round(size_bytes / 1024, 1)} KB"
            else:
                size_label = f"{round(size_bytes / (1024 * 1024), 2)} MB"
            stats[dataset_name] = {
                "records": len(rows),
                "size_bytes": size_bytes,
                "size_label": size_label,
                "generated_at": generated_at,
            }
        except Exception as exc:
            logger.exception(
                "admin_export_dataset_stats_failed",
                extra={
                    "structured_payload": {
                        "dataset": dataset_name,
                        "error": export_error_summary(exc),
                    }
                },
            )
            stats[dataset_name] = {
                "records": "-",
                "size_bytes": 0,
                "size_label": "Error",
                "generated_at": generated_at,
                "error": export_error_summary(exc),
            }
    return stats
