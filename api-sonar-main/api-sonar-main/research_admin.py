import csv
import hashlib
from html import escape
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from experiment import (
    CAMPAIGN_CODE,
    CONSENT_VERSION,
    DECK_VERSION,
    DEPLOYMENT_CONTEXT,
    ENVIRONMENT_LABEL,
    EXPERIMENT_VERSION,
    LEXICON_VERSION,
    PAYMENT_VERSION,
    SCHEMA_VERSION,
    SITE_CODE,
    TELEMETRY_VERSION,
    UI_VERSION,
)
from models import (
    AuditEvent,
    Claim,
    ConsentRecord,
    DeckPosition,
    ExperimentState,
    FraudFlag,
    InterestSignup,
    Payment,
    PayoutRequest,
    Series,
    SeriesRoot,
    SessionRecord,
    SessionClientContext,
    ScreenSpell,
    SnapshotRecord,
    TelemetryEvent,
    Throw,
)


DATASET_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "sessions": {
        "category": "analytic",
        "description": "Sesion analitica derivada, lista para modelos y tablas.",
        "sensitivity": "baja",
    },
    "throws": {
        "category": "analytic",
        "description": "Plan de tiradas servidas por sesion e intento.",
        "sensitivity": "baja",
    },
    "claims": {
        "category": "analytic",
        "description": "Claims finales y snapshot congelado del reporte.",
        "sensitivity": "baja",
    },
    "payments_admin": {
        "category": "administrative",
        "description": "Pagos, codigos de cobro y solicitudes administrativas.",
        "sensitivity": "alta",
    },
    "interest_signups": {
        "category": "administrative",
        "description": "Emails voluntarios para futuros experimentos cuando el estudio esta cerrado.",
        "sensitivity": "alta",
    },
    "telemetry": {
        "category": "operational",
        "description": "Telemetria cruda de interaccion y errores.",
        "sensitivity": "media",
    },
    "technical_events": {
        "category": "operational",
        "description": "Errores, latencias, retries y eventos tecnicos de red.",
        "sensitivity": "media",
    },
    "screen_events": {
        "category": "operational",
        "description": "Estancias en pantalla agregadas por spell.",
        "sensitivity": "media",
    },
    "client_contexts": {
        "category": "operational",
        "description": "Contexto de navegador, dispositivo y viewport por sesion.",
        "sensitivity": "media",
    },
    "referrals": {
        "category": "analytic",
        "description": "Red de referidos y profundidad de invitacion.",
        "sensitivity": "baja",
    },
    "series_state": {
        "category": "analytic",
        "description": "Estado de roots y series por fase y tratamiento.",
        "sensitivity": "baja",
    },
    "position_plan": {
        "category": "analytic",
        "description": "Plan preasignado de resultados y payout por posicion.",
        "sensitivity": "baja",
    },
    "quality_flags": {
        "category": "analytic",
        "description": "Flags de calidad explotados por sesion.",
        "sensitivity": "baja",
    },
    "fraud_flags": {
        "category": "operational",
        "description": "Flags antifraude generados por el backend.",
        "sensitivity": "media",
    },
    "consent_records": {
        "category": "analytic",
        "description": "Consentimientos, idioma y uso de paneles informativos.",
        "sensitivity": "media",
    },
    "snapshot_records": {
        "category": "analytic",
        "description": "Snapshot auditable de lo que vio el participante.",
        "sensitivity": "media",
    },
    "audit_events": {
        "category": "operational",
        "description": "Trazabilidad de acciones y transiciones criticas.",
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


def safe_ms_delta(
    later: Optional[datetime], earlier: Optional[datetime]
) -> Optional[int]:
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


def load_lookup_table(db: Session, model: Any, key_field: str) -> dict[str, Any]:
    rows = db.exec(select(model)).all()
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


def analytic_sessions_rows(db: Session) -> list[dict[str, Any]]:
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    claims_by_session = load_lookup_table(db, Claim, "session_id")
    payments_by_session = load_lookup_table(db, Payment, "session_id")
    consent_by_session = load_lookup_table(db, ConsentRecord, "session_id")
    snapshot_by_session = load_lookup_table(db, SnapshotRecord, "session_id")
    client_context_by_session = load_lookup_table(db, SessionClientContext, "session_id")
    throws = db.exec(select(Throw).order_by(Throw.session_id, Throw.attempt_index)).all()
    screen_spells = db.exec(
        select(ScreenSpell).order_by(ScreenSpell.session_id, ScreenSpell.entered_server_ts)
    ).all()
    seen_by_session: dict[str, list[int]] = {}
    screen_metrics_by_session: dict[str, dict[str, int]] = {}
    for throw in throws:
        seen_by_session.setdefault(throw.session_id, []).append(throw.result_value)
    for spell in screen_spells:
        key_prefix = spell.screen_name
        bucket = screen_metrics_by_session.setdefault(spell.session_id, {})
        bucket[f"{key_prefix}_visible_ms"] = bucket.get(
            f"{key_prefix}_visible_ms", 0
        ) + int(spell.visible_ms or 0)
        bucket[f"{key_prefix}_hidden_ms"] = bucket.get(
            f"{key_prefix}_hidden_ms", 0
        ) + int(spell.hidden_ms or 0)
        bucket[f"{key_prefix}_blur_ms"] = bucket.get(
            f"{key_prefix}_blur_ms", 0
        ) + int(spell.blur_ms or 0)
        bucket[f"{key_prefix}_click_count"] = bucket.get(
            f"{key_prefix}_click_count", 0
        ) + int(spell.click_count or 0)
    referral_depths = build_referral_depth_map(sessions)

    rows: list[dict[str, Any]] = []
    for record in sessions:
        claim = claims_by_session.get(record.id)
        consent = consent_by_session.get(record.id)
        snapshot = snapshot_by_session.get(record.id)
        client_context = client_context_by_session.get(record.id)
        seen_values = seen_by_session.get(record.id, [])
        screen_metrics = screen_metrics_by_session.get(record.id, {})
        reported_value = claim.reported_value if claim else record.reported_value
        true_first_result = claim.true_first_result if claim else record.first_result_value
        rows.append(
            {
                "session_id": record.id,
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
                "deployment_context": record.deployment_context,
                "site_code": record.site_code,
                "campaign_code": record.campaign_code,
                "environment_label": record.environment_label,
                "language_at_access": record.language_at_access,
                "language_at_claim": record.language_at_claim,
                "language_changed_during_session": record.language_changed_during_session,
                "treatment_key": record.treatment_key,
                "treatment_family": record.treatment_family,
                "norm_target_value": record.norm_target_value,
                "position_index": record.position_index,
                "root_id": record.root_id,
                "series_id": record.series_id,
                "selected_for_payment": record.selected_for_payment,
                "reported_value": reported_value,
                "true_first_result": true_first_result,
                "reported_six": int(reported_value == 6) if reported_value is not None else None,
                "reported_five": int(reported_value == 5) if reported_value is not None else None,
                "reported_high": int(reported_value in {5, 6}) if reported_value is not None else None,
                "is_honest": record.is_honest,
                "lie_to_six": int(reported_value == 6 and true_first_result != 6)
                if reported_value is not None and true_first_result is not None
                else None,
                "overreport_amount": (
                    reported_value - true_first_result
                    if reported_value is not None and true_first_result is not None
                    else None
                ),
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
                "reported_unseen": (
                    int(reported_value not in seen_values)
                    if reported_value is not None and seen_values
                    else None
                ),
                "report_rt_ms": (
                    claim.reaction_ms
                    if claim and claim.reaction_ms is not None
                    else safe_ms_delta(record.claim_submitted_at, record.report_prepared_at)
                ),
                "game_decision_rt_ms": safe_ms_delta(record.report_prepared_at, record.first_roll_at),
                "total_session_ms": safe_ms_delta(record.completed_at, record.created_at),
                "displayed_count_target": record.report_snapshot_count_target,
                "displayed_denominator": record.report_snapshot_denominator,
                "displayed_message_version": record.report_snapshot_message_version,
                "displayed_message_text": snapshot.displayed_message_text if snapshot else record.report_snapshot_message,
                "control_message_text": snapshot.control_message_text if snapshot else None,
                "final_message_text": snapshot.final_message_text if snapshot else None,
                "landing_visible_ms": consent.landing_visible_ms if consent else None,
                "referral_code": record.referral_code,
                "invited_by_session_id": record.invited_by_session_id,
                "invited_by_referral_code": record.invited_by_referral_code,
                "referral_source": record.referral_source,
                "referral_medium": record.referral_medium,
                "referral_campaign": record.referral_campaign,
                "referral_link_id": record.referral_link_id,
                "referral_arrived_at": isoformat_or_none(record.referral_arrived_at),
                "referral_depth": referral_depths.get(record.id, 0),
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
                "landing_to_start_ms": consent.landing_visible_ms if consent else None,
                "consent_total_ms": consent.landing_visible_ms if consent else None,
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
            "position_index": sessions[throw.session_id].position_index,
            "attempt_index": throw.attempt_index,
            "result_value": throw.result_value,
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
            "displayed_count_target": claim.displayed_count_target,
            "displayed_denominator": claim.displayed_denominator,
            "displayed_target_value": claim.displayed_target_value,
            "displayed_window_version": claim.displayed_window_version,
            "displayed_message": claim.displayed_message,
            "displayed_message_version": claim.displayed_message_version,
            "max_seen_value": claim.max_seen_value,
            "last_seen_value": claim.last_seen_value,
            "matches_last_seen": claim.matches_last_seen,
            "matches_any_seen": claim.matches_any_seen,
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
                "eligible": payment.eligible,
                "amount_cents": payment.amount_cents,
                "amount_eur": int(payment.amount_cents / 100),
                "status": payment.status,
                "payout_reference": payment.payout_reference,
                "requested_phone": request.requested_phone if request else None,
                "donation_requested": request.donation_requested if request else None,
                "request_language": request.language_used if request else None,
                "request_message_text": request.message_text if request else None,
                "request_created_at": isoformat_or_none(request.created_at) if request else None,
                "created_at": isoformat_or_none(payment.created_at),
                "paid_at": isoformat_or_none(payment.paid_at),
            }
        )
    return rows


def telemetry_rows(db: Session) -> list[dict[str, Any]]:
    events = db.exec(select(TelemetryEvent).order_by(TelemetryEvent.server_ts)).all()
    session_map = load_lookup_table(db, SessionRecord, "id")
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
            "payload_json": event.payload_json,
            "server_ts": isoformat_or_none(event.server_ts),
        }
        for event in events
    ]


def technical_events_rows(db: Session) -> list[dict[str, Any]]:
    events = db.exec(select(TelemetryEvent).order_by(TelemetryEvent.server_ts)).all()
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
            "payload_json": event.payload_json,
            "server_ts": isoformat_or_none(event.server_ts),
        }
        for event in technical_events
    ]


def screen_events_rows(db: Session) -> list[dict[str, Any]]:
    spells = db.exec(select(ScreenSpell).order_by(ScreenSpell.entered_server_ts)).all()
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
        }
        for spell in spells
    ]


def client_contexts_rows(db: Session) -> list[dict[str, Any]]:
    contexts = db.exec(
        select(SessionClientContext).order_by(SessionClientContext.captured_at)
    ).all()
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
            "referral_landing_path": record.referral_landing_path,
            "referral_arrived_at": isoformat_or_none(record.referral_arrived_at),
            "referral_depth": depths.get(record.id, 0),
            "experiment_phase": record.experiment_phase,
            "treatment_key": record.treatment_key,
            "created_at": isoformat_or_none(record.created_at),
        }
        for record in sessions
    ]


def series_state_rows(db: Session) -> list[dict[str, Any]]:
    roots = db.exec(select(SeriesRoot).order_by(SeriesRoot.root_sequence)).all()
    rows: list[dict[str, Any]] = []
    for root in roots:
        series_items = db.exec(
            select(Series).where(Series.root_id == root.id).order_by(Series.treatment_key)
        ).all()
        for series in series_items:
            rows.append(
                {
                    "root_id": root.id,
                    "root_sequence": root.root_sequence,
                    "root_phase": root.experiment_phase,
                    "root_status": root.status,
                    "root_close_reason": root.close_reason,
                    "root_created_at": isoformat_or_none(root.created_at),
                    "root_closed_at": isoformat_or_none(root.closed_at),
                    "series_id": series.id,
                    "treatment_key": series.treatment_key,
                    "treatment_family": series.treatment_family,
                    "norm_target_value": series.norm_target_value,
                    "assignment_weight": series.assignment_weight,
                    "position_counter": series.position_counter,
                    "completed_count": series.completed_count,
                    "visible_count_target": series.visible_count_target,
                    "actual_count_target": series.actual_count_target,
                    "visible_window_version": series.visible_window_version,
                    "actual_window_version": series.actual_window_version,
                    "full_target_streak": series.full_target_streak,
                    "is_closed": series.is_closed,
                    "close_reason": series.close_reason,
                }
            )
    return rows


def interest_signups_rows(db: Session) -> list[dict[str, Any]]:
    signups = db.exec(select(InterestSignup).order_by(InterestSignup.created_at)).all()
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
            "created_at": isoformat_or_none(signup.created_at),
            "updated_at": isoformat_or_none(signup.updated_at),
        }
        for signup in signups
    ]


def position_plan_rows(db: Session) -> list[dict[str, Any]]:
    roots = load_lookup_table(db, SeriesRoot, "id")
    positions = db.exec(
        select(DeckPosition).order_by(
            DeckPosition.root_id, DeckPosition.position_index, DeckPosition.attempt_index
        )
    ).all()
    return [
        {
            "root_id": item.root_id,
            "root_sequence": roots[item.root_id].root_sequence if item.root_id in roots else None,
            "experiment_phase": roots[item.root_id].experiment_phase if item.root_id in roots else None,
            "position_index": item.position_index,
            "attempt_index": item.attempt_index,
            "result_value": item.result_value,
            "payout_eligible": item.payout_eligible,
            "commitment_hash": item.commitment_hash,
            "created_at": isoformat_or_none(item.created_at),
        }
        for item in positions
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
    flags = db.exec(select(FraudFlag).order_by(FraudFlag.created_at)).all()
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
    "payments_admin": payments_admin_rows,
    "interest_signups": interest_signups_rows,
    "telemetry": telemetry_rows,
    "technical_events": technical_events_rows,
    "screen_events": screen_events_rows,
    "client_contexts": client_contexts_rows,
    "referrals": referrals_rows,
    "series_state": series_state_rows,
    "position_plan": position_plan_rows,
    "quality_flags": quality_flags_rows,
    "fraud_flags": fraud_flags_rows,
    "consent_records": consent_records_rows,
    "snapshot_records": snapshot_records_rows,
    "audit_events": audit_events_rows,
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
            "series_state",
            "position_plan",
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
            "- analytic: datos listos para analisis cientifico.",
            "- operational: logs y telemetria cruda.",
            "- administrative: cobros y datos administrativos sensibles.",
        ]
    )
    return "\n".join(lines)


def current_versions_payload(db: Session) -> dict[str, Any]:
    state = db.get(ExperimentState, "global")
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

    for dataset_name in dataset_names:
        rows = dataset_rows(db, dataset_name)
        csv_bytes = rows_to_csv_bytes(rows)
        filename = f"{dataset_name}.csv"
        file_payloads[filename] = csv_bytes
        manifest_tables.append(
            {
                "dataset": dataset_name,
                "filename": filename,
                "records": len(rows),
                "category": DATASET_DESCRIPTIONS[dataset_name]["category"],
                "sensitivity": DATASET_DESCRIPTIONS[dataset_name]["sensitivity"],
                "description": DATASET_DESCRIPTIONS[dataset_name]["description"],
                "sha256": hashlib.sha256(csv_bytes).hexdigest(),
            }
        )

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
        rows_html.append(
            f"""
            <tr>
              <td><strong>{dataset_name}</strong></td>
              <td>{meta['category']}</td>
              <td>{meta['sensitivity']}</td>
              <td>{stats.get('records', 0)}</td>
              <td>{stats.get('size_label', '0 B')}</td>
              <td>{stats.get('generated_at', '-')}</td>
              <td>{meta['description']}</td>
              <td><a href="/admin/export/{dataset_name}.csv">CSV</a></td>
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
      <p>Fase actual: <strong>{state.current_phase}</strong> | Estado: <strong>{state.experiment_status}</strong> | Validos completados: <strong>{state.valid_completed_count}</strong> / {state.phase_transition_threshold} | Personas premiadas: <strong>{prize_stats.get('winner_count', 0)}</strong> | Total repartido: <strong>{prize_stats.get('total_prize_amount_eur', 0)} EUR</strong> | Registros administrativos de premios: <strong>{payments_admin_stats.get('records', 0)}</strong></p>
      <div class="grid">
        <div class="card">
          <h2>Analitico</h2>
          <p>Dataset listo para modelos y publicaciones.</p>
          <a class="button" href="/admin/export/bundle/analytic.zip">Exportar dataset analitico completo</a>
        </div>
        <div class="card">
          <h2>Operativo</h2>
          <p>Telemetria cruda, screen spells, contexto de cliente, fraude y auditoria.</p>
          <a class="button" href="/admin/export/bundle/operational.zip">Exportar telemetria completa</a>
        </div>
        <div class="card">
          <h2>Administrativo</h2>
          <p class="warn">Contiene datos sensibles de cobro y emails voluntarios para futuros estudios.</p>
          <a class="button" href="/admin/export/bundle/administrative.zip">Exportar pagos administrativos</a>
        </div>
        <div class="card">
          <h2>Todo</h2>
          <p>ZIP completo con manifest, README y codebook.</p>
          <a class="button" href="/admin/export/bundle/all.zip">Generar paquete para analisis</a>
        </div>
        <div class="card">
          <h2>Red de referidos</h2>
          <p>Trazabilidad de invitador, invitado y profundidad de red.</p>
          <a class="button" href="/admin/export/referrals.csv">Exportar red de referidos</a>
        </div>
        <div class="card">
          <h2>Posicion y series</h2>
          <p>Estado de roots, series espejo y plan preasignado por posicion.</p>
          <a class="button" href="/admin/export/series_state.csv">Exportar posicion y series</a>
        </div>
      </div>
      <h2>Datasets</h2>
      <table>
        <thead><tr><th>Nombre</th><th>Capa</th><th>Sensibilidad</th><th>Registros</th><th>Tamaño aprox.</th><th>Generado</th><th>Descripcion</th><th>Exportar</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
      <p style="margin-top:16px;"><a class="secondary" href="/admin/dashboard">Abrir dashboard cientifico-operativo</a></p>
    </div>
  </body>
</html>
"""


def dashboard_page_html(db: Session) -> str:
    state = db.get(ExperimentState, "global")
    sessions = db.exec(select(SessionRecord).order_by(SessionRecord.created_at)).all()
    claims = db.exec(select(Claim)).all()
    payments = db.exec(select(Payment)).all()
    telemetry = db.exec(select(TelemetryEvent)).all()
    screen_spells = db.exec(select(ScreenSpell)).all()
    fraud_flags = db.exec(select(FraudFlag)).all()
    interest_signups = db.exec(select(InterestSignup)).all()
    series_rows = series_state_rows(db)

    completed_valid = [item for item in sessions if item.is_valid_completed]
    dropout_by_screen: dict[str, int] = {}
    treatment_balance: dict[str, int] = {}
    phase_balance: dict[str, int] = {}
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
    total_prize_amount_eur = round(
        sum(item.amount_cents for item in eligible_payments) / 100,
        2,
    )
    escaped_pause_reason = escape(state.pause_reason) if state and state.pause_reason else ""

    for session_record in sessions:
        treatment_balance[session_record.treatment_key] = (
            treatment_balance.get(session_record.treatment_key, 0) + 1
        )
        phase_balance[session_record.experiment_phase] = (
            phase_balance.get(session_record.experiment_phase, 0) + 1
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

    def rows_from_counter(counter: dict[Any, Any]) -> str:
        return "".join(
            f"<tr><td>{key}</td><td>{value}</td></tr>"
            for key, value in sorted(counter.items(), key=lambda item: str(item[0]))
        ) or "<tr><td colspan='2'>Sin datos</td></tr>"

    screen_stats_rows = "".join(
        f"<tr><td>{screen}</td><td>{len(values)}</td><td>{mean(values) or 0}</td></tr>"
        for screen, values in sorted(screen_durations.items())
    ) or "<tr><td colspan='3'>Sin datos</td></tr>"

    series_html = "".join(
        f"<tr><td>{row['root_sequence']}</td><td>{row['root_phase']}</td><td>{row['treatment_key']}</td><td>{row['position_counter']}</td><td>{row['completed_count']}</td><td>{row['visible_count_target']}</td><td>{row['actual_count_target']}</td></tr>"
        for row in series_rows
    ) or "<tr><td colspan='7'>Sin datos</td></tr>"

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
      .controls {{ display:grid; gap:12px; }}
      .control-row {{ display:flex; gap:12px; flex-wrap:wrap; }}
      .status {{ font-size:14px; color:#555; }}
      input {{ width:100%; box-sizing:border-box; padding:12px 14px; border-radius:14px; border:1px solid rgba(0,0,0,.12); font-size:14px; }}
      button {{ padding:12px 18px; border:none; border-radius:999px; background:#111; color:white; font-weight:700; letter-spacing:.08em; text-transform:uppercase; cursor:pointer; }}
      button.secondary {{ background:white; color:#111; border:1px solid rgba(0,0,0,.12); }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <p>Investigador</p>
      <h1>Dashboard cientifico-operativo</h1>
      <div class="grid">
        <div class="card"><strong>Fase actual</strong><div>{state.current_phase if state else '-'}</div></div>
        <div class="card"><strong>Estado del experimento</strong><div>{state.experiment_status if state else '-'}</div></div>
        <div class="card"><strong>Sesiones iniciadas</strong><div>{len(sessions)}</div></div>
        <div class="card"><strong>Completadas validas</strong><div>{len(completed_valid)}</div></div>
        <div class="card"><strong>Claims totales</strong><div>{len(claims)}</div></div>
        <div class="card"><strong>Personas premiadas</strong><div>{len(eligible_payments)}</div></div>
        <div class="card"><strong>Importe total de premios</strong><div>{total_prize_amount_eur} EUR</div></div>
        <div class="card"><strong>Emails para futuros estudios</strong><div>{len(interest_signups)}</div></div>
        <div class="card"><strong>Media rerolls</strong><div>{mean(rerolls) or 0}</div></div>
        <div class="card"><strong>Errores de red/tecnicos</strong><div>{len(network_errors)}</div></div>
        <div class="card"><strong>Reportes de 5</strong><div>{reported_distribution[5]}</div></div>
        <div class="card"><strong>Reportes de 6</strong><div>{reported_distribution[6]}</div></div>
        <div class="card"><strong>Reportes de 5 o 6</strong><div>{sum(reported_distribution[v] for v in [5, 6])}</div></div>
        <div class="card"><strong>Verdades de 5</strong><div>{truth_distribution[5]}</div></div>
        <div class="card"><strong>Verdades de 6</strong><div>{truth_distribution[6]}</div></div>
        <div class="card"><strong>Verdades de 5 o 6</strong><div>{sum(truth_distribution[v] for v in [5, 6])}</div></div>
      </div>
      <div class="card controls">
        <h2>Control del experimento</h2>
        <div class="status">
          Estado actual: <strong>{state.experiment_status if state else '-'}</strong>
          {" | Pausado en: " + state.paused_at.isoformat() if state and state.paused_at else ""}
        </div>
        <input id="experiment-reason" placeholder="Motivo interno opcional: fraude, incidencia de premios, pausa operativa..." />
        {"<div class='status'>Ultimo motivo de pausa: <strong>" + escaped_pause_reason + "</strong></div>" if escaped_pause_reason else ""}
        <div class="control-row">
          <button id="pause-button">Parar experimento</button>
          <button id="resume-button" class="secondary">Reactivar experimento</button>
        </div>
        <div id="control-status" class="status"></div>
      </div>
      <div class="two">
        <div><h2>Balance por tratamiento</h2><table><tbody>{rows_from_counter(treatment_balance)}</tbody></table></div>
        <div><h2>Balance por fase</h2><table><tbody>{rows_from_counter(phase_balance)}</tbody></table></div>
      </div>
      <div class="two">
        <div><h2>Dropout por pantalla</h2><table><tbody>{rows_from_counter(dropout_by_screen)}</tbody></table></div>
        <div><h2>Flags de calidad</h2><table><tbody>{rows_from_counter(quality_distribution)}</tbody></table></div>
      </div>
      <div class="two">
        <div><h2>Distribucion de reportes 1-6</h2><table><tbody>{rows_from_counter(reported_distribution)}</tbody></table></div>
        <div><h2>Distribucion de verdad 1-6</h2><table><tbody>{rows_from_counter(truth_distribution)}</tbody></table></div>
      </div>
      <div class="two">
        <div>
          <h2>Screen timings</h2>
          <table><thead><tr><th>Pantalla</th><th>Eventos</th><th>Media ms</th></tr></thead><tbody>{screen_stats_rows}</tbody></table>
        </div>
        <div><h2>Flags de fraude</h2><table><tbody>{rows_from_counter(fraud_distribution)}</tbody></table></div>
      </div>
      <h2>Evolucion temporal de series</h2>
      <table>
        <thead><tr><th>Root</th><th>Fase</th><th>Tratamiento</th><th>Asignados</th><th>Completados</th><th>Visible target</th><th>Actual target</th></tr></thead>
        <tbody>
          {series_html}
        </tbody>
      </table>
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
          status.textContent = `Estado actualizado: ${{data.experiment_status}}. Personas premiadas: ${{data.prizes.winner_count}}. Total repartido: ${{data.prizes.total_prize_amount_eur}} EUR.`;
          window.setTimeout(() => window.location.reload(), 700);
        }} catch (error) {{
          status.textContent = error.message || 'No se pudo actualizar el estado';
        }}
      }}
      document.getElementById('pause-button').addEventListener('click', () => postExperimentControl('/admin/experiment/pause'));
      document.getElementById('resume-button').addEventListener('click', () => postExperimentControl('/admin/experiment/resume'));
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
    return stats
