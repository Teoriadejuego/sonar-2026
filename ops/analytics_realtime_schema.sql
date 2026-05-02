CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    bracelet_hash TEXT,
    gateway_visit_id TEXT,
    qr_code TEXT,
    zone_code TEXT,
    treatment_key TEXT NOT NULL,
    treatment_family TEXT NOT NULL,
    norm_target_value SMALLINT,
    deployment_context TEXT,
    site_code TEXT,
    campaign_code TEXT,
    environment_label TEXT,
    state TEXT NOT NULL,
    screen_cursor TEXT NOT NULL,
    language_at_access TEXT,
    language_at_claim TEXT,
    referral_source TEXT,
    referral_medium TEXT,
    referral_campaign TEXT,
    referral_landing_path TEXT,
    selected_for_payment BOOLEAN NOT NULL DEFAULT FALSE,
    payout_amount_cents INTEGER NOT NULL DEFAULT 0,
    first_result_value SMALLINT,
    max_seen_value SMALLINT,
    reported_value SMALLINT,
    is_honest BOOLEAN,
    reroll_count INTEGER NOT NULL DEFAULT 0,
    valid_completed BOOLEAN NOT NULL DEFAULT FALSE,
    consent_accepted_at TIMESTAMPTZ,
    first_roll_at TIMESTAMPTZ,
    report_prepared_at TIMESTAMPTZ,
    claim_submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_sessions_created_at
    ON analytics.sessions (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_sessions_user_created_at
    ON analytics.sessions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_sessions_qr_created_at
    ON analytics.sessions (qr_code, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_sessions_treatment_created_at
    ON analytics.sessions (treatment_key, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_sessions_completed_at
    ON analytics.sessions (completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_sessions_gateway_visit_id
    ON analytics.sessions (gateway_visit_id);


CREATE TABLE IF NOT EXISTS analytics.claims (
    claim_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    qr_code TEXT,
    zone_code TEXT,
    treatment_key TEXT NOT NULL,
    treatment_family TEXT NOT NULL,
    norm_target_value SMALLINT,
    position_index INTEGER NOT NULL,
    true_first_result SMALLINT NOT NULL,
    reported_value SMALLINT NOT NULL,
    is_honest BOOLEAN NOT NULL,
    reroll_count INTEGER NOT NULL DEFAULT 0,
    displayed_count_target SMALLINT,
    displayed_denominator SMALLINT,
    displayed_target_value SMALLINT,
    reaction_ms BIGINT,
    crowd_prediction_value SMALLINT,
    social_recall_count INTEGER,
    social_recall_correct BOOLEAN,
    eligible_for_payment BOOLEAN NOT NULL DEFAULT FALSE,
    payment_amount_cents INTEGER NOT NULL DEFAULT 0,
    payment_status TEXT,
    quality_flags_json JSONB,
    antifraud_flags_json JSONB,
    submitted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_claims_submitted_at
    ON analytics.claims (submitted_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_claims_qr_submitted_at
    ON analytics.claims (qr_code, submitted_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_claims_treatment_submitted_at
    ON analytics.claims (treatment_key, submitted_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_claims_user_submitted_at
    ON analytics.claims (user_id, submitted_at DESC);


CREATE TABLE IF NOT EXISTS analytics.qr_scans (
    qr_scan_id BIGSERIAL PRIMARY KEY,
    gateway_visit_id TEXT NOT NULL UNIQUE,
    route_id TEXT,
    session_id TEXT,
    user_id TEXT,
    qr_code TEXT NOT NULL,
    zone_code TEXT,
    request_host TEXT,
    request_path TEXT NOT NULL,
    query_string TEXT,
    traffic_source TEXT,
    traffic_medium TEXT,
    selected_target TEXT NOT NULL,
    resolved_target_url TEXT,
    redirect_status_code INTEGER,
    status TEXT NOT NULL,
    referer TEXT,
    request_user_agent TEXT,
    user_agent_hash TEXT,
    ip_hash TEXT,
    scanned_at TIMESTAMPTZ NOT NULL,
    linked_session_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_qr_scans_scanned_at
    ON analytics.qr_scans (scanned_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_qr_scans_qr_scanned_at
    ON analytics.qr_scans (qr_code, scanned_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_qr_scans_zone_scanned_at
    ON analytics.qr_scans (zone_code, scanned_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_qr_scans_session_id
    ON analytics.qr_scans (session_id);
CREATE INDEX IF NOT EXISTS ix_analytics_qr_scans_selected_target_scanned_at
    ON analytics.qr_scans (selected_target, scanned_at DESC);


CREATE TABLE IF NOT EXISTS analytics.invites (
    invite_id TEXT PRIMARY KEY,
    invite_code TEXT NOT NULL UNIQUE,
    inviter_session_id TEXT NOT NULL,
    inviter_user_id TEXT NOT NULL,
    invited_session_id TEXT,
    invited_user_id TEXT,
    gateway_visit_id TEXT,
    qr_code TEXT,
    zone_code TEXT,
    channel TEXT,
    campaign_code TEXT,
    status TEXT NOT NULL,
    opened_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_invites_created_at
    ON analytics.invites (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_invites_inviter_created_at
    ON analytics.invites (inviter_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_invites_invited_session_id
    ON analytics.invites (invited_session_id);
CREATE INDEX IF NOT EXISTS ix_analytics_invites_qr_created_at
    ON analytics.invites (qr_code, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_invites_status_created_at
    ON analytics.invites (status, created_at DESC);


CREATE TABLE IF NOT EXISTS analytics.events (
    event_id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    user_id TEXT,
    gateway_visit_id TEXT,
    qr_code TEXT,
    zone_code TEXT,
    event_type TEXT NOT NULL,
    event_name TEXT NOT NULL,
    screen_name TEXT,
    endpoint_name TEXT,
    request_method TEXT,
    status_code INTEGER,
    duration_ms BIGINT,
    latency_ms BIGINT,
    value INTEGER,
    attempt_number INTEGER,
    is_retry BOOLEAN NOT NULL DEFAULT FALSE,
    error_name TEXT,
    network_status TEXT,
    app_language TEXT,
    browser_language TEXT,
    payload_json JSONB,
    client_ts BIGINT,
    server_ts TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_events_server_ts
    ON analytics.events (server_ts DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_events_session_server_ts
    ON analytics.events (session_id, server_ts DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_events_user_server_ts
    ON analytics.events (user_id, server_ts DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_events_qr_server_ts
    ON analytics.events (qr_code, server_ts DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_events_endpoint_server_ts
    ON analytics.events (endpoint_name, server_ts DESC);
CREATE INDEX IF NOT EXISTS ix_analytics_events_type_name_server_ts
    ON analytics.events (event_type, event_name, server_ts DESC);


CREATE VIEW analytics.session_funnel_live AS
SELECT
    DATE_TRUNC('minute', created_at) AS bucket_minute,
    COUNT(*) AS sessions_started,
    COUNT(*) FILTER (WHERE first_roll_at IS NOT NULL) AS sessions_with_roll,
    COUNT(*) FILTER (WHERE report_prepared_at IS NOT NULL) AS sessions_with_report,
    COUNT(*) FILTER (WHERE claim_submitted_at IS NOT NULL) AS sessions_with_claim,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS sessions_completed
FROM analytics.sessions
GROUP BY 1;


CREATE VIEW analytics.qr_performance_live AS
SELECT
    qr_code,
    zone_code,
    COUNT(*) AS scans_total,
    COUNT(*) FILTER (WHERE session_id IS NOT NULL) AS sessions_started,
    COUNT(*) FILTER (WHERE status = 'redirected') AS redirects_ok,
    ROUND(
        COUNT(*) FILTER (WHERE session_id IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS scan_to_session_rate
FROM analytics.qr_scans
GROUP BY qr_code, zone_code;


CREATE VIEW analytics.endpoint_health_live AS
SELECT
    endpoint_name,
    DATE_TRUNC('minute', server_ts) AS bucket_minute,
    COUNT(*) AS request_count,
    COUNT(*) FILTER (WHERE status_code >= 400) AS error_count,
    ROUND(AVG(latency_ms)::NUMERIC, 2) AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms
FROM analytics.events
WHERE endpoint_name IS NOT NULL
GROUP BY endpoint_name, DATE_TRUNC('minute', server_ts);
