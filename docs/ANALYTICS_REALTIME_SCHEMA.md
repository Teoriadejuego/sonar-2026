# Esquema Analítico En Tiempo Real

## Objetivo
Definir un esquema analítico separado del `OLTP` de la app para consultas de:

- KPIs agregados en tiempo real
- trazabilidad por `session_id` o `user_id`
- rendimiento por `qr_code` o `zone_code`

La recomendación es usar un esquema dedicado `analytics` dentro de PostgreSQL o en un réplica de lectura. El backend operativo sigue escribiendo en `public.*`; la capa analítica replica o transforma esos datos hacia `analytics.*`.

## Principios
- Un `grano` claro por tabla.
- Campos de tiempo en todas las tablas.
- Claves de negocio repetidas donde mejoran consulta y evitan joins caros.
- Índices para tres patrones de consulta:
  - agregados por tiempo
  - drill-down por usuario/sesión
  - atribución por QR/zona

## Tablas

### `analytics.sessions`
Grano: `1 fila = 1 sesión experimental`

Propósito:
- funnel principal
- segmentación por tratamiento
- estado actual y tiempos clave
- relación entre usuario, claim y QR

Campos clave:
- `session_id` PK
- `user_id`
- `bracelet_hash`
- `gateway_visit_id`
- `qr_code`
- `zone_code`
- `treatment_key`
- `treatment_family`
- `norm_target_value`
- `state`
- `screen_cursor`
- `reroll_count`
- `valid_completed`
- `selected_for_payment`
- `payout_amount_cents`
- `first_result_value`
- `reported_value`
- `is_honest`
- `referral_source`
- `referral_medium`
- `referral_campaign`
- `referral_landing_path`
- `consent_accepted_at`
- `first_roll_at`
- `report_prepared_at`
- `claim_submitted_at`
- `completed_at`
- `last_seen_at`
- `created_at`
- `updated_at`
- `ingestion_ts`

Fuente sugerida:
- `public.sessions`
- enriquecida con `public.gateway_access_logs`

### `analytics.claims`
Grano: `1 fila = 1 claim`

Propósito:
- análisis de honestidad
- análisis por tratamiento
- tiempos de respuesta y calidad
- payout y outcome

Campos clave:
- `claim_id` PK
- `session_id`
- `user_id`
- `qr_code`
- `zone_code`
- `treatment_key`
- `treatment_family`
- `norm_target_value`
- `position_index`
- `true_first_result`
- `reported_value`
- `is_honest`
- `reroll_count`
- `displayed_count_target`
- `displayed_denominator`
- `displayed_target_value`
- `reaction_ms`
- `crowd_prediction_value`
- `social_recall_count`
- `social_recall_correct`
- `eligible_for_payment`
- `payment_amount_cents`
- `payment_status`
- `quality_flags_json`
- `antifraud_flags_json`
- `submitted_at`
- `created_at`
- `updated_at`
- `ingestion_ts`

Fuente sugerida:
- `public.claims`
- join con `public.payments`
- join con `public.sessions`

### `analytics.qr_scans`
Grano: `1 fila = 1 escaneo / visita al gateway`

Propósito:
- atribución por QR
- rendimiento por zona
- conversión `scan -> access -> completed`
- monitorización de destino `primary/backup`

Campos clave:
- `qr_scan_id` PK
- `gateway_visit_id` UNIQUE
- `route_id`
- `session_id`
- `user_id`
- `qr_code`
- `zone_code`
- `request_host`
- `request_path`
- `query_string`
- `traffic_source`
- `traffic_medium`
- `selected_target`
- `resolved_target_url`
- `redirect_status_code`
- `status`
- `request_user_agent`
- `user_agent_hash`
- `ip_hash`
- `scanned_at`
- `linked_session_at`
- `created_at`
- `updated_at`
- `ingestion_ts`

Fuente sugerida:
- `public.gateway_access_logs`

### `analytics.invites`
Grano: `1 fila = 1 invitación o referral link`

Propósito:
- medir invitaciones generadas
- atribución de invitador -> invitado
- conversión por código, QR o canal

Campos clave:
- `invite_id` PK
- `invite_code` UNIQUE
- `inviter_session_id`
- `inviter_user_id`
- `invited_session_id`
- `invited_user_id`
- `gateway_visit_id`
- `qr_code`
- `zone_code`
- `channel`
- `campaign_code`
- `status`
- `opened_at`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`
- `ingestion_ts`

Fuente sugerida:
- derivada de `public.sessions.referral_code`
- `public.sessions.invited_by_session_id`
- `public.gateway_access_logs.gateway_visit_id`

### `analytics.events`
Grano: `1 fila = 1 evento analítico`

Propósito:
- latencia por endpoint
- errores por endpoint
- telemetría mínima del experimento
- reconstrucción fina de una sesión

Campos clave:
- `event_id` PK
- `session_id`
- `user_id`
- `gateway_visit_id`
- `qr_code`
- `zone_code`
- `event_type`
- `event_name`
- `screen_name`
- `endpoint_name`
- `request_method`
- `status_code`
- `duration_ms`
- `latency_ms`
- `value`
- `attempt_number`
- `is_retry`
- `error_name`
- `network_status`
- `app_language`
- `browser_language`
- `payload_json`
- `client_ts`
- `server_ts`
- `created_at`
- `updated_at`
- `ingestion_ts`

Fuente sugerida:
- `public.telemetry_events`
- opcionalmente una vista unificada con `public.audit_events` para eventos operativos

## Relaciones
- `analytics.sessions.session_id -> analytics.claims.session_id`
- `analytics.sessions.gateway_visit_id -> analytics.qr_scans.gateway_visit_id`
- `analytics.sessions.session_id -> analytics.events.session_id`
- `analytics.invites.invited_session_id -> analytics.sessions.session_id`
- `analytics.invites.inviter_session_id -> analytics.sessions.session_id`

## Consultas objetivo

### Agregadas
- sesiones iniciadas por hora
- sesiones completadas por hora
- tasa de conversión por tratamiento
- honestidad por tratamiento
- errores por endpoint en 5 minutos
- latencia p95 por endpoint

### Por usuario
- timeline de una sesión
- invitaciones emitidas por un usuario
- relación entre resultados vistos, claim y payout

### Por QR
- escaneos por QR/zona
- `scan -> access -> completed`
- rendimiento de `primary` vs `backup`

## Índices mínimos
- `sessions(created_at)`
- `sessions(user_id, created_at desc)`
- `sessions(qr_code, created_at desc)`
- `sessions(treatment_key, created_at desc)`
- `claims(submitted_at)`
- `claims(session_id)`
- `claims(qr_code, submitted_at desc)`
- `qr_scans(qr_code, scanned_at desc)`
- `qr_scans(zone_code, scanned_at desc)`
- `qr_scans(session_id)`
- `events(server_ts)`
- `events(session_id, server_ts)`
- `events(endpoint_name, server_ts desc)`
- `events(qr_code, server_ts desc)`

## Recomendación operativa
- `sessions`, `claims`, `invites`: actualización incremental tipo `upsert`
- `qr_scans`, `events`: inserción append-only
- refresco cada `5-15s` si se quiere panel en vivo

## SQL de referencia
El DDL listo para PostgreSQL está en:

- [analytics_realtime_schema.sql](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/ops/analytics_realtime_schema.sql>)
