from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, Float, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def make_uuid() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExperimentState(SQLModel, table=True):
    __tablename__ = "experiment_state"

    id: str = Field(default="global", primary_key=True)
    current_phase: str = Field(default="phase_1_main", index=True)
    experiment_status: str = Field(default="active", index=True)
    phase_transition_threshold: int = Field(default=6000)
    valid_completed_count: int = Field(default=0)
    phase_2_activated_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    pause_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    treatment_version: str
    allocation_version: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Pulsera(SQLModel, table=True):
    __tablename__ = "pulsera"

    id: str = Field(primary_key=True, description="ID de la pulsera")
    created_at: datetime = Field(default_factory=utcnow)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    bracelet_id: str = Field(foreign_key="pulsera.id", unique=True, index=True)
    bracelet_hash: str = Field(unique=True, index=True)
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    is_blocked: bool = Field(default=False)


class SeriesRoot(SQLModel, table=True):
    __tablename__ = "series_roots"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    root_sequence: int = Field(unique=True, index=True)
    experiment_phase: str = Field(index=True)
    treatment_version: str
    allocation_version: str
    status: str = Field(default="active", index=True)
    close_reason: Optional[str] = Field(default=None, index=True)
    deck_seed_commitment: str
    experiment_version: str
    created_at: datetime = Field(default_factory=utcnow)
    closed_at: Optional[datetime] = None


class Series(SQLModel, table=True):
    __tablename__ = "series"
    __table_args__ = (
        UniqueConstraint("root_id", "treatment_key", name="uq_series_root_treatment"),
    )

    id: str = Field(default_factory=make_uuid, primary_key=True)
    root_id: str = Field(foreign_key="series_roots.id", index=True)
    experiment_phase: str = Field(index=True)
    treatment_key: str = Field(index=True)
    treatment_family: str = Field(index=True)
    norm_target_value: Optional[int] = Field(default=None, index=True)
    label: str
    assignment_weight: float = Field(
        default=0.0, sa_column=Column(Float, nullable=False)
    )
    participant_limit: int = Field(default=250)
    sample_size: int = Field(default=100)
    position_counter: int = Field(default=0)
    completed_count: int = Field(default=0)
    visible_count_target: int = Field(default=0)
    actual_count_target: int = Field(default=0)
    full_target_streak: int = Field(default=0)
    visible_window_version: int = Field(default=0)
    actual_window_version: int = Field(default=0)
    is_closed: bool = Field(default=False, index=True)
    close_reason: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class SeriesWindowEntry(SQLModel, table=True):
    __tablename__ = "series_window_entries"
    __table_args__ = (
        UniqueConstraint(
            "series_id", "window_type", "slot_index", name="uq_window_slot"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    series_id: str = Field(foreign_key="series.id", index=True)
    window_type: str = Field(index=True)
    slot_index: int = Field(index=True)
    value: int
    source: str = Field(default="seed")
    claim_id: Optional[str] = Field(default=None, index=True)
    inserted_at: datetime = Field(default_factory=utcnow)


class DeckPosition(SQLModel, table=True):
    __tablename__ = "deck_positions"
    __table_args__ = (
        UniqueConstraint(
            "root_id",
            "position_index",
            "attempt_index",
            name="uq_deck_root_position_attempt",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    root_id: str = Field(foreign_key="series_roots.id", index=True)
    position_index: int = Field(index=True)
    attempt_index: int = Field(index=True)
    result_value: int
    payout_eligible: bool = Field(default=False)
    commitment_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_sessions_user"),
        UniqueConstraint("series_id", "position_index", name="uq_session_series_position"),
    )

    id: str = Field(default_factory=make_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True, index=True)
    root_id: str = Field(foreign_key="series_roots.id", index=True)
    series_id: str = Field(foreign_key="series.id", index=True)
    experiment_version: str
    experiment_phase: str = Field(index=True)
    phase_version: str
    phase_activation_status: str = Field(index=True)
    ui_version: str
    consent_version: str
    treatment_version: str
    treatment_text_version: str
    allocation_version: str
    deck_version: str
    payment_version: str
    telemetry_version: str
    lexicon_version: str
    treatment_key: str = Field(index=True)
    treatment_family: str = Field(index=True)
    norm_target_value: Optional[int] = Field(default=None, index=True)
    language_at_access: Optional[str] = Field(default=None, index=True)
    language_at_claim: Optional[str] = Field(default=None, index=True)
    language_changed_during_session: bool = Field(default=False)
    deployment_context: str = Field(index=True)
    site_code: str = Field(index=True)
    campaign_code: str = Field(index=True)
    environment_label: str = Field(index=True)
    referral_code: str = Field(unique=True, index=True)
    invited_by_session_id: Optional[str] = Field(
        default=None, foreign_key="sessions.id", index=True
    )
    invited_by_referral_code: Optional[str] = Field(default=None, index=True)
    referral_source: Optional[str] = Field(default=None, index=True)
    referral_medium: Optional[str] = Field(default=None, index=True)
    referral_campaign: Optional[str] = Field(default=None, index=True)
    referral_link_id: Optional[str] = Field(default=None, index=True)
    referral_landing_path: Optional[str] = None
    referral_arrived_at: Optional[datetime] = None
    position_index: int = Field(index=True)
    state: str = Field(default="assigned", index=True)
    screen_cursor: str = Field(default="instructions", index=True)
    consent_accepted: bool = Field(default=True)
    consent_age_confirmed: bool = Field(default=False)
    consent_info_accepted: bool = Field(default=False)
    consent_data_accepted: bool = Field(default=False)
    consent_accepted_at: Optional[datetime] = None
    max_attempts: int = Field(default=10)
    selected_for_payment: bool = Field(default=False)
    payout_amount: int = Field(default=0)
    reported_value: Optional[int] = None
    is_honest: Optional[bool] = None
    first_result_value: Optional[int] = None
    max_seen_value: Optional[int] = None
    last_seen_value: Optional[int] = None
    report_snapshot_treatment: Optional[str] = None
    report_snapshot_count_target: Optional[int] = None
    report_snapshot_denominator: Optional[int] = None
    report_snapshot_target_value: Optional[int] = None
    report_snapshot_version: Optional[int] = None
    report_snapshot_message: Optional[str] = None
    report_snapshot_message_version: Optional[str] = None
    displayed_message_version: Optional[str] = None
    is_valid_completed: bool = Field(default=False, index=True)
    valid_completed_at: Optional[datetime] = None
    claim_submitted_at: Optional[datetime] = None
    first_roll_at: Optional[datetime] = None
    report_prepared_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    resume_count: int = Field(default=0)
    refresh_count: int = Field(default=0)
    blur_count: int = Field(default=0)
    network_error_count: int = Field(default=0)
    retry_count: int = Field(default=0)
    click_count_total: int = Field(default=0)
    screen_changes_count: int = Field(default=0)
    language_change_count: int = Field(default=0)
    telemetry_event_count: int = Field(default=0)
    max_event_sequence_number: int = Field(default=0)
    reroll_count: int = Field(default=0)
    client_installation_id: Optional[str] = None
    device_hash: Optional[str] = Field(default=None, index=True)
    ip_hash: Optional[str] = Field(default=None, index=True)
    user_agent_hash: Optional[str] = Field(default=None, index=True)
    quality_flags_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    antifraud_flags_json: Optional[str] = Field(default=None, sa_column=Column(Text))


class Throw(SQLModel, table=True):
    __tablename__ = "throws"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_index", name="uq_throw_attempt"),
        UniqueConstraint("session_id", "idempotency_key", name="uq_throw_idempotency"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    attempt_index: int = Field(index=True)
    result_value: int
    reaction_ms: Optional[int] = None
    delivered_at: datetime = Field(default_factory=utcnow)
    idempotency_key: str = Field(index=True)


class ConsentRecord(SQLModel, table=True):
    __tablename__ = "consent_records"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    bracelet_id: str = Field(index=True)
    consent_version: str
    language_at_access: Optional[str] = Field(default=None, index=True)
    age_confirmed: bool
    participation_accepted: bool
    data_accepted: bool
    accepted_at: datetime = Field(default_factory=utcnow)
    landing_visible_ms: Optional[int] = None
    info_panels_opened_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    info_panel_durations_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    info_panel_open_count: int = Field(default=0)
    checkbox_order_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    checkbox_timestamps_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    continue_blocked_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)


class SnapshotRecord(SQLModel, table=True):
    __tablename__ = "snapshot_records"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    language_used: Optional[str] = Field(default=None, index=True)
    treatment_key: Optional[str] = Field(default=None, index=True)
    treatment_family: Optional[str] = Field(default=None, index=True)
    norm_target_value: Optional[int] = Field(default=None, index=True)
    displayed_count_target: Optional[int] = None
    displayed_denominator: Optional[int] = None
    displayed_message_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    displayed_message_version: Optional[str] = None
    control_message_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    first_result_value: Optional[int] = None
    last_seen_value: Optional[int] = None
    all_values_seen_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    rerolls_visible_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    final_state_shown: Optional[str] = None
    final_message_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    final_amount_eur: Optional[int] = None
    payout_reference_shown: Optional[str] = None
    payout_phone_shown: Optional[str] = None
    updated_at: datetime = Field(default_factory=utcnow)


class SessionClientContext(SQLModel, table=True):
    __tablename__ = "session_client_contexts"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    user_agent_raw: Optional[str] = Field(default=None, sa_column=Column(Text))
    user_agent_hash: Optional[str] = Field(default=None, index=True)
    browser_family: Optional[str] = Field(default=None, index=True)
    browser_version: Optional[str] = None
    os_family: Optional[str] = Field(default=None, index=True)
    os_version: Optional[str] = None
    device_type: Optional[str] = Field(default=None, index=True)
    platform: Optional[str] = None
    language_browser: Optional[str] = Field(default=None, index=True)
    language_app_selected: Optional[str] = Field(default=None, index=True)
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    device_pixel_ratio: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True)
    )
    orientation: Optional[str] = None
    touch_capable: Optional[bool] = None
    hardware_concurrency: Optional[int] = None
    max_touch_points: Optional[int] = None
    color_scheme_preference: Optional[str] = None
    online_status: Optional[str] = None
    connection_type: Optional[str] = None
    estimated_downlink: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True)
    )
    estimated_rtt: Optional[int] = None
    timezone_offset_minutes: Optional[int] = None
    context_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    captured_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ScreenSpell(SQLModel, table=True):
    __tablename__ = "screen_spells"
    __table_args__ = (
        UniqueConstraint("session_id", "spell_id", name="uq_screen_spell"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    spell_id: str = Field(index=True)
    screen_name: str = Field(index=True)
    entry_origin: Optional[str] = None
    entered_client_ts: Optional[int] = None
    entered_server_ts: datetime = Field(default_factory=utcnow)
    exited_client_ts: Optional[int] = None
    exited_server_ts: Optional[datetime] = None
    duration_total_ms: Optional[int] = None
    visible_ms: Optional[int] = None
    hidden_ms: Optional[int] = None
    blur_ms: Optional[int] = None
    focus_change_count: int = Field(default=0)
    visibility_change_count: int = Field(default=0)
    click_count: int = Field(default=0)
    primary_click_count: int = Field(default=0)
    secondary_click_count: int = Field(default=0)
    first_click_ms: Optional[int] = None
    primary_cta_ms: Optional[int] = None
    secondary_cta_ms: Optional[int] = None
    first_click_target: Optional[str] = None
    click_targets_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    entered_via_resume: bool = Field(default=False)
    language_at_entry: Optional[str] = Field(default=None, index=True)
    language_at_exit: Optional[str] = Field(default=None, index=True)
    language_changed_during_spell: bool = Field(default=False)
    event_sequence_start: Optional[int] = None
    event_sequence_end: Optional[int] = None
    updated_at: datetime = Field(default_factory=utcnow)


class Claim(SQLModel, table=True):
    __tablename__ = "claims"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    root_id: str = Field(foreign_key="series_roots.id", index=True)
    series_id: str = Field(foreign_key="series.id", index=True)
    experiment_phase: str = Field(index=True)
    phase_activation_status: str = Field(index=True)
    treatment_version: str
    allocation_version: str
    treatment_family: str = Field(index=True)
    norm_target_value: Optional[int] = Field(default=None, index=True)
    position_index: int = Field(index=True)
    true_first_result: int
    reported_value: int
    is_honest: bool
    reroll_count: int
    displayed_treatment_key: str = Field(index=True)
    displayed_count_target: Optional[int] = None
    displayed_denominator: Optional[int] = None
    displayed_target_value: Optional[int] = None
    displayed_window_version: Optional[int] = None
    displayed_message: Optional[str] = None
    displayed_message_version: Optional[str] = None
    max_seen_value: Optional[int] = None
    last_seen_value: Optional[int] = None
    matches_last_seen: bool = Field(default=False)
    matches_any_seen: bool = Field(default=False)
    reaction_ms: Optional[int] = None
    quality_flags_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    antifraud_flags_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    submitted_at: datetime = Field(default_factory=utcnow)


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    claim_id: str = Field(foreign_key="claims.id", unique=True, index=True)
    eligible: bool
    amount_cents: int
    status: str = Field(default="pending", index=True)
    payout_reference: Optional[str] = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    paid_at: Optional[datetime] = None


class PayoutRequest(SQLModel, table=True):
    __tablename__ = "payout_requests"

    id: str = Field(default_factory=make_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    payment_id: str = Field(foreign_key="payments.id", unique=True, index=True)
    payout_reference: str = Field(index=True)
    requested_phone: str
    donation_requested: bool = Field(default=False)
    language_used: Optional[str] = Field(default=None, index=True)
    message_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="submitted", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    processed_at: Optional[datetime] = None


class InterestSignup(SQLModel, table=True):
    __tablename__ = "interest_signups"
    __table_args__ = (
        UniqueConstraint("email_normalized", name="uq_interest_signups_email"),
    )

    id: str = Field(default_factory=make_uuid, primary_key=True)
    email_normalized: str = Field(index=True)
    email_hash: str = Field(index=True)
    language_used: Optional[str] = Field(default=None, index=True)
    source_screen: str = Field(default="experiment_paused", index=True)
    experiment_status: str = Field(default="paused", index=True)
    deployment_context: str = Field(index=True)
    site_code: str = Field(index=True)
    campaign_code: str = Field(index=True)
    environment_label: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TelemetryEvent(SQLModel, table=True):
    __tablename__ = "telemetry_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    event_type: str = Field(index=True)
    event_name: str = Field(index=True)
    screen_name: Optional[str] = Field(default=None, index=True)
    client_ts: Optional[int] = None
    event_sequence_number: Optional[int] = Field(default=None, index=True)
    timezone_offset_minutes: Optional[int] = None
    client_clock_skew_estimate_ms: Optional[int] = None
    duration_ms: Optional[int] = None
    value: Optional[int] = None
    app_language: Optional[str] = Field(default=None, index=True)
    browser_language: Optional[str] = Field(default=None, index=True)
    spell_id: Optional[str] = Field(default=None, index=True)
    interaction_target: Optional[str] = Field(default=None, index=True)
    interaction_role: Optional[str] = Field(default=None, index=True)
    cta_kind: Optional[str] = Field(default=None, index=True)
    endpoint_name: Optional[str] = Field(default=None, index=True)
    request_method: Optional[str] = Field(default=None, index=True)
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    attempt_number: Optional[int] = None
    is_retry: bool = Field(default=False, index=True)
    error_name: Optional[str] = None
    network_status: Optional[str] = None
    visibility_state: Optional[str] = None
    payload_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    server_ts: datetime = Field(default_factory=utcnow)


class FraudFlag(SQLModel, table=True):
    __tablename__ = "fraud_flags"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.id", index=True)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id", index=True)
    flag_key: str = Field(index=True)
    severity: str = Field(default="low", index=True)
    payload_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.id", index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    action: str = Field(index=True)
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, index=True)
    payload_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)


class ActionReceipt(SQLModel, table=True):
    __tablename__ = "action_receipts"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "endpoint", "idempotency_key", name="uq_receipt_idempotency"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    endpoint: str = Field(index=True)
    idempotency_key: str = Field(index=True)
    response_json: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
