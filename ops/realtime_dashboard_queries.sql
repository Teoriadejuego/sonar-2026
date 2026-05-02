-- Dashboard live: consultas SQL base para las secciones con respaldo en BD.
-- Ajusta INTERVAL '30 minutes' a la ventana operativa deseada.

-- 1. Participantes totales, activos y completados
SELECT
    COUNT(*) AS participants_total,
    COUNT(*) FILTER (WHERE last_seen_at >= NOW() - INTERVAL '30 minutes') AS participants_active,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS participants_completed,
    ROUND(
        COUNT(*) FILTER (WHERE completed_at IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS completion_rate_total
FROM sessions;


-- 2. Experimento: tasa de 6 reportado, mentiras y distribucion
SELECT
    COUNT(*) FILTER (WHERE claim_submitted_at IS NOT NULL) AS claims_total,
    COUNT(*) FILTER (WHERE reported_value = 6) AS reported_six_count,
    ROUND(
        COUNT(*) FILTER (WHERE reported_value = 6)::NUMERIC
        / NULLIF(COUNT(*) FILTER (WHERE claim_submitted_at IS NOT NULL), 0),
        4
    ) AS reported_six_rate,
    COUNT(*) FILTER (WHERE is_honest = FALSE) AS lies_count,
    ROUND(
        COUNT(*) FILTER (WHERE is_honest = FALSE)::NUMERIC
        / NULLIF(COUNT(*) FILTER (WHERE claim_submitted_at IS NOT NULL), 0),
        4
    ) AS lie_rate
FROM sessions;

SELECT
    reported_value,
    COUNT(*) AS reported_count
FROM sessions
WHERE claim_submitted_at IS NOT NULL
GROUP BY reported_value
ORDER BY reported_value;

SELECT
    first_result_value,
    COUNT(*) AS truth_count
FROM sessions
WHERE first_result_value IS NOT NULL
GROUP BY first_result_value
ORDER BY first_result_value;


-- 3. Pagos: ganadores e importe total
SELECT
    COUNT(*) FILTER (WHERE eligible = TRUE) AS winners_total,
    ROUND(SUM(amount_cents) FILTER (WHERE eligible = TRUE) / 100.0, 2) AS amount_total_eur
FROM payments;

SELECT
    p.session_id,
    u.bracelet_id,
    COALESCE(pr.payout_reference, p.payout_reference) AS reference_code,
    ROUND(p.amount_cents / 100.0, 2) AS amount_eur,
    COALESCE(pr.donation_requested, FALSE) AS donation_requested,
    COALESCE(pr.created_at, p.created_at) AS submitted_at,
    p.status AS payment_status,
    pr.status AS payout_request_status
FROM payments p
LEFT JOIN sessions s ON s.id = p.session_id
LEFT JOIN users u ON u.id = s.user_id
LEFT JOIN payout_requests pr ON pr.payment_id = p.id
WHERE p.eligible = TRUE
ORDER BY submitted_at DESC
LIMIT 20;


-- 4. QR: trafico por QR y rendimiento por zona
SELECT
    qr_code,
    zone_code,
    COUNT(*) AS scans_total,
    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS sessions_started,
    ROUND(
        COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL)::NUMERIC
        / NULLIF(COUNT(*), 0),
        4
    ) AS conversion_rate
FROM gateway_access_logs
GROUP BY qr_code, zone_code
ORDER BY scans_total DESC, qr_code;

SELECT
    zone_code,
    COUNT(*) AS scans_total,
    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS sessions_started,
    ROUND(
        COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL)::NUMERIC
        / NULLIF(COUNT(*), 0),
        4
    ) AS conversion_rate
FROM gateway_access_logs
GROUP BY zone_code
ORDER BY scans_total DESC, zone_code;


-- 5. Viralidad: invitaciones, clicks y usuarios por referral
SELECT
    COUNT(*) AS invitations_sent_total,
    COALESCE(SUM(click_count), 0) AS clicks_total,
    COALESCE(SUM(conversion_count), 0) AS users_by_referral_total,
    ROUND(
        COALESCE(SUM(conversion_count), 0)::NUMERIC
        / NULLIF(COALESCE(SUM(click_count), 0), 0),
        4
    ) AS invite_to_entry_ratio
FROM referral_links;

SELECT
    inviter_session_id,
    inviter_referral_code,
    COUNT(*) AS links_total,
    COALESCE(SUM(click_count), 0) AS clicks_total,
    COALESCE(SUM(conversion_count), 0) AS users_by_referral,
    ROUND(
        COALESCE(SUM(conversion_count), 0)::NUMERIC
        / NULLIF(COALESCE(SUM(click_count), 0), 0),
        4
    ) AS invite_to_entry_ratio
FROM referral_links
GROUP BY inviter_session_id, inviter_referral_code
ORDER BY users_by_referral DESC, clicks_total DESC;

SELECT
    invited_by_session_id AS inviter_session_id,
    invited_by_referral_code AS inviter_referral_code,
    COUNT(*) AS invited_users_total
FROM sessions
WHERE invited_by_session_id IS NOT NULL
GROUP BY invited_by_session_id, invited_by_referral_code
ORDER BY invited_users_total DESC, inviter_session_id;


-- 6. Latencia y errores: se sirven desde metrica runtime/Redis, no desde SQL.
-- Fuente operativa: /admin/dashboard/live o /admin/metrics
-- Claves Redis:
--   sonar:metrics:http:*
--   sonar:metrics:counters:*
