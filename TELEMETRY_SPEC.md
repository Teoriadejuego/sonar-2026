# Telemetry Spec

## Principio
SONAR registra telemetria de interaccion, contexto tecnico, red y atencion para poder distinguir:
- comportamiento experimental
- friccion tecnica
- errores de interfaz o conectividad
- calidad de la exposicion a cada pantalla

No se capturan permisos intrusivos:
- no geolocalizacion precisa
- no camara
- no microfono
- no contactos
- no portapapeles
- no historial de navegacion

## Evento crudo
Cada fila de `telemetry.csv` puede incluir:
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

Los timestamps cliente se guardan como `BIGINT`, por lo que soportan milisegundos Unix completos sin overflow.

## Tipos principales de evento

### lifecycle
- `resume_session`
- `page_reload`
- `focus`
- `blur`
- `visibility_hidden`
- `visibility_visible`
- `language_change`

### screen
- `screen_enter`
- `screen_exit`

### click
- clicks de CTA primario
- CTA secundario
- checkbox
- selector de idioma
- invitacion por WhatsApp
- acciones de payout

### network
- `api_success`
- `api_error`
- `api_exception`
- `browser_online`
- `browser_offline`
- `connection_change`

### error
- `js_error`
- `unhandled_rejection`
- errores de acceso
- errores de roll
- errores de prepare-report
- errores de submit-report
- errores de display snapshot
- errores de payout

## Screen spells
`screen_events.csv` resume cada estancia en una pantalla.

Campos principales:
- `session_id`, `spell_id`, `screen_name`, `entry_origin`
- `entered_client_ts`, `entered_server_ts`, `exited_client_ts`, `exited_server_ts`
- `duration_total_ms`, `visible_ms`, `hidden_ms`, `blur_ms`
- `focus_change_count`, `visibility_change_count`
- `click_count`, `primary_click_count`, `secondary_click_count`
- `first_click_ms`, `primary_cta_ms`, `secondary_cta_ms`
- `first_click_target`, `click_targets_json`
- `language_at_entry`, `language_at_exit`, `language_changed_during_spell`

## Contexto tecnico
`client_contexts.csv` consolida por sesion:
- navegador y version
- sistema operativo y version
- tipo de dispositivo
- idioma del navegador y de la app
- pantalla y viewport
- device pixel ratio
- orientacion
- touch capability
- hardware concurrency
- max touch points
- color scheme
- online status
- connection type
- estimated downlink
- estimated rtt
- timezone offset

## Consentimiento
`consent_records.csv` conserva:
- idioma de acceso
- timestamp de aceptacion
- `landing_visible_ms`
- paneles eticos abiertos
- duracion por panel
- orden de checkboxes
- tiempos relativos de marcado
- numero de bloqueos al intentar continuar sin completar requisitos

## Snapshot visible
`snapshot_records.csv` conserva la reconstruccion de lo mostrado:
- `treatment_key`
- `norm_target_value`
- `is_control`
- `displayed_count_target`
- `displayed_denominator`
- `displayed_message_text`
- `displayed_message_version`
- `first_result_value`
- `last_seen_value`
- `seen_values_json`
- `reroll_values_json`
- `final_outcome`
- `winner_message_text`
- `loser_message_text`
- `payment_code_displayed`

## Derivados presentes en sessions.csv
Los derivados de telemetria mas utiles para analisis y QA se agregan en `sessions.csv`:
- `landing_visible_ms`
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

Interpretacion de algunos derivados:
- `landing_to_start_ms`: tiempo hasta primer CTA principal o primer click en la pantalla de acceso
- `consent_total_ms`: `landing_visible_ms` mas la suma de los paneles informativos abiertos
- `game_decision_rt_ms`: tiempo entre la primera tirada servida y la preparacion del reporte
- `report_rt_ms`: tiempo entre la preparacion del reporte y el envio del claim, o `reaction_ms` del claim si existe

## Relacion con el nuevo diseno 62/24/100
La telemetria no asigna tratamiento ni pago. Solo observa:
- que mensaje se mostro
- cuando se mostro
- que pantallas se recorrieron
- cuanto tardo el participante
- que eventos de red o error ocurrieron

La asignacion experimental autoritativa vive en:
- `sessions.csv`
- `treatment_deck_cards.csv`
- `result_deck_cards.csv`
- `payment_deck_cards.csv`

## Descarga recomendada
Desde `admin/exports`:
- `sessions.csv`
- `telemetry.csv`
- `technical_events.csv`
- `screen_events.csv`
- `client_contexts.csv`
- `consent_records.csv`
- `snapshot_records.csv`

Si se quiere conservar trazabilidad completa de jornada:
- descargar `operational.zip`
