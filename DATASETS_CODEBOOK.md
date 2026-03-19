# Datasets Codebook

## Capas de datos
- `analytic`: listas para análisis científico y preregistro.
- `operational`: telemetría cruda, errores, red, spells de pantalla y auditoría técnica.
- `administrative`: cobro y operaciones sensibles separadas del dataset analítico.

## sessions
Una fila por sesión.

Variables clave:
- versionado completo: `experiment_version`, `experiment_phase`, `phase_version`, `ui_version`, `consent_version`, `treatment_version`, `allocation_version`, `deck_version`, `payment_version`, `telemetry_version`, `lexicon_version`
- tratamiento y diseño: `treatment_key`, `treatment_family`, `norm_target_value`, `position_index`, `root_id`, `series_id`
- outcomes: `reported_value`, `true_first_result`, `reported_six`, `reported_five`, `reported_high`, `is_honest`, `lie_to_six`, `overreport_amount`
- juego: `reroll_count`, `used_any_reroll`, `last_seen_value`, `max_seen_value`, `reported_matches_first`, `reported_matches_last`, `reported_matches_any_seen`, `reported_unseen`
- tiempos derivados: `landing_to_start_ms`, `consent_total_ms`, `instructions_visible_ms`, `comprehension_visible_ms`, `game_visible_ms`, `report_visible_ms`, `exit_visible_ms`, `report_rt_ms`, `game_decision_rt_ms`, `total_session_ms`
- interacción y atención: `click_count_total`, `click_count_by_screen_json`, `focus_loss_pre_claim`, `multiple_focus_loss`, `reload_count`, `resume_count`, `network_error_count`, `retry_count`, `consent_panels_opened_count`, `screen_changes_count`, `language_change_count`
- idioma y contexto: `language_at_access`, `language_at_claim`, `language_changed_during_session`, `language_browser`, `browser_family`, `os_family`, `device_type`, `screen_width`, `viewport_width`, `orientation`, `connection_type`
- referidos: `referral_code`, `invited_by_session_id`, `invited_by_referral_code`, `referral_source`, `referral_medium`, `referral_campaign`, `referral_link_id`, `referral_arrived_at`, `referral_depth`

## throws
Una fila por tirada servida por backend.

Variables clave:
- `session_id`, `attempt_index`, `result_value`, `reaction_ms`, `delivered_at`
- contexto experimental: `experiment_phase`, `treatment_key`, `position_index`

## claims
Una fila por claim final.

Variables clave:
- `reported_value`, `true_first_result`, `is_honest`, `reroll_count`
- snapshot del tratamiento: `displayed_treatment_key`, `displayed_count_target`, `displayed_denominator`, `displayed_target_value`, `displayed_window_version`, `displayed_message`, `displayed_message_version`
- interpretación conductual: `max_seen_value`, `last_seen_value`, `matches_last_seen`, `matches_any_seen`, `reaction_ms`

## telemetry
Una fila por evento crudo.

Variables clave:
- `server_ts`, `client_ts`, `event_sequence_number`, `timezone_offset_minutes`, `client_clock_skew_estimate_ms`
- `event_type`, `event_name`, `screen_name`, `spell_id`
- `interaction_target`, `interaction_role`, `cta_kind`
- `endpoint_name`, `request_method`, `status_code`, `latency_ms`, `attempt_number`, `is_retry`, `error_name`
- `app_language`, `browser_language`, `network_status`, `visibility_state`, `payload_json`

## technical_events
Subconjunto operativo de errores, red, retries, viewport y eventos técnicos.

Útil para:
- depuración
- auditoría de latencias
- separar fricción técnica de comportamiento experimental

## screen_events
Una fila por screen spell.

Variables clave:
- `session_id`, `spell_id`, `screen_name`, `entry_origin`, `entered_via_resume`
- `entered_client_ts`, `entered_server_ts`, `exited_client_ts`, `exited_server_ts`
- `duration_total_ms`, `visible_ms`, `hidden_ms`, `blur_ms`
- `focus_change_count`, `visibility_change_count`
- `click_count`, `primary_click_count`, `secondary_click_count`
- `first_click_ms`, `primary_cta_ms`, `secondary_cta_ms`
- `first_click_target`, `click_targets_json`
- `language_at_entry`, `language_at_exit`, `language_changed_during_spell`
- `event_sequence_start`, `event_sequence_end`

## client_contexts
Una fila por sesión con el contexto técnico consolidado del dispositivo y navegador.

Variables clave:
- `user_agent_hash`
- `browser_family`, `browser_version`
- `os_family`, `os_version`
- `device_type`, `platform`
- `language_browser`, `language_app_selected`
- `screen_width`, `screen_height`, `viewport_width`, `viewport_height`, `device_pixel_ratio`
- `orientation`, `touch_capable`, `hardware_concurrency`, `max_touch_points`
- `color_scheme_preference`, `online_status`, `connection_type`, `estimated_downlink`, `estimated_rtt`
- `timezone_offset_minutes`, `context_json`

## referrals
Una fila por sesión con trazabilidad de red.

Variables clave:
- `referral_code`
- `invited_by_session_id`
- `invited_by_referral_code`
- `referral_source`, `referral_medium`, `referral_campaign`, `referral_link_id`
- `referral_landing_path`, `referral_arrived_at`, `referral_depth`

## series_state
Estado de raíces y series por fase.

Variables clave:
- `root_sequence`, `root_phase`, `root_status`, `root_close_reason`
- `treatment_key`, `treatment_family`, `norm_target_value`
- `position_counter`, `completed_count`
- `visible_count_target`, `actual_count_target`
- `visible_window_version`, `actual_window_version`

## position_plan
Plan preasignado por posición e intento.

Variables clave:
- `root_id`, `root_sequence`, `experiment_phase`, `position_index`, `attempt_index`
- `result_value`, `payout_eligible`, `commitment_hash`

## quality_flags
Una fila por flag de calidad derivado.

Ejemplos:
- `fast_consent`
- `fast_instructions`
- `fast_report`
- `blur_pre_claim`
- `reroll_ge_5`

## fraud_flags
Una fila por flag antifraude generado por backend.

Variables clave:
- `session_id`, `user_id`, `flag_key`, `severity`, `payload_json`, `created_at`

## consent_records
Una fila por consentimiento.

Variables clave:
- `language_at_access`
- `accepted_at`
- `landing_visible_ms`
- `info_panels_opened_json`, `info_panel_durations_json`, `info_panel_open_count`
- `checkbox_order_json`, `checkbox_timestamps_json`
- `continue_blocked_count`

## snapshot_records
Una fila por snapshot visible congelado.

Variables clave:
- `language_used`
- `treatment_key`, `treatment_family`, `norm_target_value`
- `displayed_count_target`, `displayed_denominator`, `displayed_message_text`, `displayed_message_version`
- `control_message_text`
- `first_result_value`, `last_seen_value`, `all_values_seen_json`, `rerolls_visible_json`
- `final_state_shown`, `final_message_text`, `final_amount_eur`
- `payout_reference_shown`, `payout_phone_shown`

## payments_admin
Una fila por pago administrativo.

Variables sensibles:
- `payout_reference`
- `requested_phone`
- `request_message_text`

## audit_events
Una fila por evento crítico del backend.

Variables clave:
- `entity_type`, `entity_id`, `action`
- `old_state`, `new_state`
- `idempotency_key`
- `payload_json`
- `created_at`

## interest_signups
Una fila por email voluntario dejado cuando el experimento esta pausado o cerrado.

Variables sensibles:
- `email_normalized`
- `email_hash`
- `language_used`
- `source_screen`
- `experiment_status`
- `deployment_context`, `site_code`, `campaign_code`, `environment_label`
- `created_at`, `updated_at`
