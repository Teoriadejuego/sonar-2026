# Datasets Codebook

## Capas de datos
- `analytic`: datasets para analisis experimental y reconstruccion de tratamiento, resultado y pago.
- `operational`: telemetria, eventos tecnicos, spells de pantalla y auditoria.
- `administrative`: cobro y opt-ins, separados del dataset analitico.

## sessions
Una fila por sesion.

Columnas clave:
- versionado: `experiment_version`, `experiment_phase`, `phase_version`, `ui_version`, `consent_version`, `treatment_version`, `allocation_version`, `deck_version`, `payment_version`, `telemetry_version`, `lexicon_version`
- tratamiento: `treatment_key`, `treatment_type`, `treatment_family`, `is_control`, `displayed_count_target`, `displayed_denominator`, `norm_target_value`, `displayed_message_version`, `displayed_message_text`
- decks: `treatment_deck_index`, `treatment_card_position`, `result_deck_index`, `result_card_position`, `payment_deck_index`, `payment_card_position`
- resultado y reporte: `reported_value`, `true_first_result`, `reported_six`, `is_honest`, `reroll_count`, `used_any_reroll`, `last_seen_value`, `max_seen_value`, `reported_matches_first`, `reported_matches_last`, `reported_matches_any_seen`
- pago: `selected_for_payment`, `payout_eligible`
- tiempos: `landing_visible_ms`, `landing_to_start_ms`, `consent_total_ms`, `instructions_visible_ms`, `comprehension_visible_ms`, `game_visible_ms`, `report_visible_ms`, `exit_visible_ms`, `report_rt_ms`, `game_decision_rt_ms`, `total_session_ms`
- interaccion: `click_count_total`, `click_count_by_screen_json`, `focus_loss_pre_claim`, `multiple_focus_loss`, `reload_count`, `resume_count`, `network_error_count`, `retry_count`, `consent_panels_opened_count`, `screen_changes_count`, `language_change_count`
- contexto tecnico: `browser_family`, `browser_version`, `os_family`, `os_version`, `device_type`, `platform`, `language_browser`, `screen_width`, `screen_height`, `viewport_width`, `viewport_height`, `device_pixel_ratio`, `orientation`, `touch_capable`, `hardware_concurrency`, `max_touch_points`, `color_scheme_preference`, `online_status`, `connection_type`, `estimated_downlink`, `estimated_rtt`, `timezone_offset_minutes`
- referidos: `referral_code`, `invited_by_session_id`, `invited_by_referral_code`, `referral_source`, `referral_medium`, `referral_campaign`, `referral_link_id`, `qr_entry_code`, `referral_arrived_at`, `referral_depth`

Interpretacion:
- `treatment_key` identifica el mensaje social asignado al individuo: `norm_0` a `norm_60` o `control`.
- `true_first_result` identifica la primera tirada real asignada desde el mazo de resultados.
- `payout_eligible` identifica si esa sesion ocupa la carta ganadora del mazo de pagos.

## throws
Una fila por tirada servida por backend.

Columnas clave:
- `session_id`, `attempt_index`, `result_value`, `reaction_ms`, `delivered_at`
- `attempt_index = 1`: primera tirada balanceada por mazo de resultados
- `attempt_index > 1`: rerolls autoritativos generados por semilla reproducible

## claims
Una fila por reporte final.

Columnas clave:
- `session_id`, `reported_value`, `true_first_result`, `is_honest`, `reroll_count`, `reaction_ms`
- snapshot mostrado: `displayed_treatment_key`, `displayed_count_target`, `displayed_denominator`, `displayed_target_value`, `displayed_message`, `displayed_message_version`
- consistencia conductual: `max_seen_value`, `last_seen_value`, `matches_last_seen`, `matches_any_seen`

## referrals
Una fila por evento de llegada o enlace compartido.

Columnas clave:
- `session_id`, `referral_code`, `invited_by_session_id`, `invited_by_referral_code`
- `source`, `medium`, `campaign`, `link_id`, `qr_entry_code`

## treatment_decks
Una fila por mazo de tratamiento.

Columnas clave:
- `id`, `deck_index`, `deck_seed`, `status`, `created_at`

Interpretacion:
- cada mazo contiene exactamente 62 cartas
- cada tratamiento aparece exactamente una vez

## treatment_deck_cards
Una fila por carta de mazo de tratamiento.

Columnas clave:
- `deck_id`, `card_position`, `treatment_key`, `assigned_session_id`, `assigned_at`

Interpretacion:
- una carta asignada queda consumida y no se recicla

## result_decks
Una fila por mazo de resultados.

Columnas clave:
- `id`, `deck_index`, `deck_seed`, `status`, `created_at`

Interpretacion:
- cada mazo contiene 24 cartas
- los valores `1` a `6` aparecen exactamente 4 veces cada uno

## result_deck_cards
Una fila por carta del mazo de resultados.

Columnas clave:
- `deck_id`, `card_position`, `result_value`, `assigned_session_id`, `assigned_at`

## payment_decks
Una fila por mazo de pagos.

Columnas clave:
- `id`, `deck_index`, `deck_seed`, `status`, `created_at`

Interpretacion:
- cada mazo contiene 100 cartas
- exactamente 1 carta tiene `payout_eligible = true`

## payment_deck_cards
Una fila por carta del mazo de pagos.

Columnas clave:
- `deck_id`, `card_position`, `payout_eligible`, `assigned_session_id`, `assigned_at`

## consent_records
Una fila por consentimiento.

Columnas clave:
- `language_at_access`, `accepted_at`
- `landing_visible_ms`
- `info_panels_opened_json`, `info_panel_durations_json`, `info_panel_open_count`
- `checkbox_order_json`, `checkbox_timestamps_json`, `continue_blocked_count`

## snapshot_records
Una fila por snapshot visible persistido.

Columnas clave:
- `treatment_key`, `treatment_family`, `norm_target_value`, `is_control`
- `displayed_count_target`, `displayed_denominator`
- `displayed_message_text`, `displayed_message_version`
- `first_result_value`, `last_seen_value`, `seen_values_json`, `reroll_values_json`
- `final_outcome`, `winner_message_text`, `loser_message_text`, `payment_code_displayed`

## telemetry
Una fila por evento crudo del cliente.

Columnas clave:
- `server_ts`, `client_ts`, `event_sequence_number`, `timezone_offset_minutes`, `client_clock_skew_estimate_ms`
- `event_type`, `event_name`, `screen_name`, `spell_id`
- `interaction_target`, `interaction_role`, `cta_kind`
- `endpoint_name`, `request_method`, `status_code`, `latency_ms`, `attempt_number`, `is_retry`, `error_name`
- `app_language`, `browser_language`, `network_status`, `visibility_state`, `payload_json`

## screen_events
Una fila por spell de pantalla.

Columnas clave:
- `session_id`, `spell_id`, `screen_name`, `entry_origin`
- `entered_client_ts`, `entered_server_ts`, `exited_client_ts`, `exited_server_ts`
- `duration_total_ms`, `visible_ms`, `hidden_ms`, `blur_ms`
- `focus_change_count`, `visibility_change_count`
- `click_count`, `primary_click_count`, `secondary_click_count`
- `first_click_ms`, `primary_cta_ms`, `secondary_cta_ms`
- `first_click_target`, `click_targets_json`

## technical_events
Subconjunto operativo de telemetria tecnica.

Utilidad:
- errores JS
- fallos de red
- latencias de endpoints
- reintentos y estados del navegador

## client_contexts
Una fila por sesion con contexto tecnico consolidado.

Columnas clave:
- `browser_family`, `browser_version`
- `os_family`, `os_version`
- `device_type`, `platform`
- `language_browser`, `language_app_selected`
- `screen_width`, `screen_height`, `viewport_width`, `viewport_height`, `device_pixel_ratio`
- `orientation`, `touch_capable`, `hardware_concurrency`, `max_touch_points`
- `color_scheme_preference`, `online_status`, `connection_type`, `estimated_downlink`, `estimated_rtt`, `timezone_offset_minutes`

## quality_flags
Una fila por sesion con flags derivados de calidad.

Utilidad:
- excluir sesiones problematicas
- construir filtros preregistrados de atencion o friccion tecnica

## fraud_flags
Eventos o indicadores antifraude y de integridad operativa.

## audit_events
Auditoria backend de operaciones relevantes.

Incluye:
- acceso
- asignacion de sesion
- tiradas
- snapshots
- claims
- cobro
- notas operativas

## payments_admin
Dataset administrativo separado.

Columnas clave:
- `session_id`, `payment_id`, `payout_reference`
- `eligible`, `amount_cents`, `status`
- `requested_phone`, `donation_requested`

## interest_signups
Opt-ins de email cuando el experimento esta pausado o cerrado.

## Reconstruccion minima sin ambiguedad
Para reconstruir la asignacion experimental de una sesion basta con:
- `sessions.csv`
- `treatment_decks.csv` y `treatment_deck_cards.csv`
- `result_decks.csv` y `result_deck_cards.csv`
- `payment_decks.csv` y `payment_deck_cards.csv`

Con esas tablas se puede verificar:
- que tratamiento recibio cada participante
- que primera tirada real se asigno
- que elegibilidad de pago recibio
- que no hubo duplicacion de carta dentro de un mismo bloque
