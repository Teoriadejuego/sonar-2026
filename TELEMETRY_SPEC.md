# Telemetry Spec

## Principio
SONAR registra telemetría de interacción, atención, contexto técnico y red con el objetivo de reconstruir qué hizo cada participante, cuándo, en qué idioma, bajo qué condiciones técnicas y con qué calidad de atención.

No se capturan permisos especiales ni datos claramente intrusivos:
- no geolocalización precisa
- no cámara
- no micrófono
- no contactos
- no portapapeles
- no historial de navegación

## Estructura de evento crudo
Cada evento en `telemetry` incluye, cuando aplica:
- `server_ts`
- `client_ts`
- `event_sequence_number`
- `timezone_offset_minutes`
- `client_clock_skew_estimate_ms`
- `event_type`
- `event_name`
- `screen_name`
- `spell_id`
- `app_language`
- `browser_language`
- `interaction_target`
- `interaction_role`
- `cta_kind`
- `endpoint_name`
- `request_method`
- `status_code`
- `latency_ms`
- `attempt_number`
- `is_retry`
- `error_name`
- `network_status`
- `visibility_state`
- `payload_json`

## Tipos principales de evento
### Lifecycle
- `resume_session`
- `page_reload`
- `focus`
- `blur`
- `visibility_hidden`
- `visibility_visible`
- `language_change`

### Screen
- `screen_enter`
- `screen_exit`

### Click
- CTA principal
- CTA secundaria
- checkbox
- selección de idioma
- compartir
- pago

### Network
- `api_success`
- `api_error`
- `api_exception`
- `browser_online`
- `browser_offline`
- `connection_change`

### Error
- `js_error`
- `unhandled_rejection`
- errores de acceso, roll, prepare-report, submit-report y display snapshot

## Screen spells
`screen_events` exporta una fila por spell de pantalla.

Cada spell resume:
- entrada y salida
- duración total
- tiempo visible
- tiempo oculta
- tiempo fuera de foco
- número de cambios de foco
- número de cambios de visibilidad
- número de clics
- tiempo hasta primer clic
- tiempo hasta CTA principal
- tiempo hasta CTA secundaria
- idioma de entrada y de salida
- si hubo cambio de idioma durante esa estancia

## Contexto de cliente
`client_contexts` recoge por sesión:
- navegador y versión
- sistema operativo y versión
- tipo de dispositivo
- idioma del navegador
- idioma de la app
- tamaño de pantalla y viewport
- DPR
- orientación
- capacidad táctil
- hardware concurrency
- max touch points
- preferencia de esquema de color
- estado de red
- effective connection type
- downlink estimado
- RTT estimado
- timezone offset

## Consentimiento y lectura
`consent_records` guarda:
- idioma del consentimiento
- timestamp de aceptación
- tiempo visible en landing
- paneles abiertos
- duración abierta por panel
- orden de marcado de checkboxes
- timestamp relativo de cada checkbox
- número de intentos bloqueados de continuar

## Snapshots
`snapshot_records` permite reconstruir lo visible:
- idioma
- mensaje del tratamiento
- mensaje neutro de control
- primer valor real
- último valor visible
- todos los valores vistos
- rerolls visibles
- estado final mostrado
- mensaje final mostrado
- código de cobro mostrado

## Derivados operativos principales
Se calculan o exportan de forma directa:
- `landing_to_start_ms`
- `consent_total_ms`
- `instructions_visible_ms`
- `comprehension_visible_ms`
- `game_visible_ms`
- `report_visible_ms`
- `exit_visible_ms`
- `report_rt_ms`
- `game_decision_rt_ms`
- `total_session_ms`
- `click_count_total`
- `click_count_by_screen_json`
- `focus_loss_pre_claim`
- `multiple_focus_loss`
- `reload_count`
- `resume_count`
- `network_error_count`
- `retry_count`
- `consent_panels_opened_count`
- `screen_changes_count`
- `language_change_count`

## Descarga para investigador
La salida recomendada está en:
- [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)

Datasets relevantes para telemetría:
- `sessions.csv`
- `telemetry.csv`
- `technical_events.csv`
- `screen_events.csv`
- `client_contexts.csv`
- `consent_records.csv`
- `snapshot_records.csv`
