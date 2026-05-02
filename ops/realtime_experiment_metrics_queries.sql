-- Métricas live principales sobre el esquema analytics.
-- Sustituye INTERVAL '30 minutes' por la ventana operativa deseada.

-- 1. Participantes totales
SELECT COUNT(*) AS participants_total
FROM analytics.sessions;


-- 2. Tasa de finalización total
SELECT
    COUNT(*) AS participants_total,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS participants_completed,
    ROUND(
        COUNT(*) FILTER (WHERE completed_at IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS completion_rate_total
FROM analytics.sessions;


-- 3. Tasa de reporte de 6
SELECT
    COUNT(*) AS claims_total,
    COUNT(*) FILTER (WHERE reported_value = 6) AS reported_six_count,
    ROUND(
        COUNT(*) FILTER (WHERE reported_value = 6)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS reported_six_rate_total
FROM analytics.claims;


-- 4. Porcentaje de mentiras
SELECT
    COUNT(*) AS claims_total,
    COUNT(*) FILTER (WHERE is_honest = FALSE) AS lies_count,
    ROUND(
        COUNT(*) FILTER (WHERE is_honest = FALSE)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS lie_rate_total
FROM analytics.claims;


-- 5. Evolución temporal en buckets de 5 minutos
WITH started AS (
    SELECT
        DATE_TRUNC('hour', created_at)
        + FLOOR(EXTRACT(MINUTE FROM created_at) / 5) * INTERVAL '5 minutes' AS bucket_start,
        COUNT(*) AS participants_started
    FROM analytics.sessions
    WHERE created_at >= NOW() - INTERVAL '30 minutes'
    GROUP BY 1
),
completed AS (
    SELECT
        DATE_TRUNC('hour', completed_at)
        + FLOOR(EXTRACT(MINUTE FROM completed_at) / 5) * INTERVAL '5 minutes' AS bucket_start,
        COUNT(*) AS participants_completed
    FROM analytics.sessions
    WHERE completed_at >= NOW() - INTERVAL '30 minutes'
    GROUP BY 1
),
claims AS (
    SELECT
        DATE_TRUNC('hour', submitted_at)
        + FLOOR(EXTRACT(MINUTE FROM submitted_at) / 5) * INTERVAL '5 minutes' AS bucket_start,
        COUNT(*) AS claims_submitted,
        COUNT(*) FILTER (WHERE reported_value = 6) AS reported_six_count,
        COUNT(*) FILTER (WHERE is_honest = FALSE) AS lies_count
    FROM analytics.claims
    WHERE submitted_at >= NOW() - INTERVAL '30 minutes'
    GROUP BY 1
)
SELECT
    bucket_start,
    SUM(participants_started) AS participants_started,
    SUM(participants_completed) AS participants_completed,
    SUM(claims_submitted) AS claims_submitted,
    ROUND(
        SUM(participants_completed)::NUMERIC / NULLIF(SUM(participants_started), 0),
        4
    ) AS completion_rate,
    ROUND(
        SUM(reported_six_count)::NUMERIC / NULLIF(SUM(claims_submitted), 0),
        4
    ) AS reported_six_rate,
    ROUND(
        SUM(lies_count)::NUMERIC / NULLIF(SUM(claims_submitted), 0),
        4
    ) AS lie_rate
FROM (
    SELECT bucket_start, participants_started, 0 AS participants_completed, 0 AS claims_submitted, 0 AS reported_six_count, 0 AS lies_count
    FROM started
    UNION ALL
    SELECT bucket_start, 0, participants_completed, 0, 0, 0
    FROM completed
    UNION ALL
    SELECT bucket_start, 0, 0, claims_submitted, reported_six_count, lies_count
    FROM claims
) unioned
GROUP BY bucket_start
ORDER BY bucket_start;


-- 6. Variantes por QR
SELECT
    qr_code,
    zone_code,
    COUNT(*) AS participants_total,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS participants_completed,
    ROUND(
        COUNT(*) FILTER (WHERE completed_at IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS completion_rate,
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
FROM analytics.sessions
GROUP BY qr_code, zone_code
ORDER BY participants_total DESC, qr_code;
