# Codebook - Simulated Data

## sonar_sessions_simulated.csv
One row per valid completed session in the simulated preregistration sample.

Core identifiers:
- `session_id`
- `bracelet_id_hash`
- `root_id`
- `series_id`
- `position_index`

Experimental variables:
- `treatment_key`
- `treatment_family`
- `experiment_phase`
- `experiment_version`
- `treatment_version`
- `allocation_version`
- `deck_version`

Truth and reports:
- `true_first_result`
- `reported_value`
- `reported_6`
- `reported_5`
- `reported_5_or_6`
- `reported_high`
- `is_honest`
- `lie_amount`
- `opportunity_to_lie`
- `relative_lie`

Observed play:
- `reroll_count`
- `used_any_reroll`
- `max_seen_value`
- `last_seen_value`
- `reported_matches_first`
- `reported_matches_last`
- `reported_matches_any_seen`
- `reported_unseen`

Displayed norm:
- `displayed_count_target`
- `displayed_denominator`
- `norm_target_value`

Timing:
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

Context:
- `hour_of_day`
- `time_block`
- `day_index`
- `language`
- `browser_family`
- `os_family`
- `device_type`

Quality and frictions:
- `focus_loss_pre_claim`
- `reload_count`
- `network_error_count`
- `quality_flag_fast_report`
- `fraud_flag_critical`

Referral fields:
- `was_referred`
- `referral_depth`
- `referral_code`
- `invited_by_session_id`
- `invited_by_referral_code`
- `referral_source`
- `referral_medium`
- `referral_campaign`
- `referral_landing_path`
- `referral_link_id`
- `shared_any`
- `share_channel`

## sonar_throws_simulated.csv
One row per observed throw shown to the participant.

Variables:
- `throw_id`
- `session_id`
- `root_id`
- `series_id`
- `treatment_key`
- `position_index`
- `attempt_index`
- `result_value`
- `reaction_ms`
- `delivered_at`

## sonar_series_simulated.csv
One row per root-treatment series.

Variables:
- `root_id`
- `root_sequence`
- `series_id`
- `treatment_key`
- `treatment_family`
- `norm_target_value`
- `seed_initial_count`
- `completed_count`
- `position_counter`
- `max_position_filled`
- `visible_count_target`
- `actual_count_target`

## sonar_position_plan_simulated.csv
One row per root-position-attempt in the shared deck.

Variables:
- `root_id`
- `root_sequence`
- `position_index`
- `attempt_index`
- `result_value`
- `payout_eligible`
- `commitment_hash`

## sonar_referrals_simulated.csv
One row per session with network metadata.

Variables:
- `session_id`
- `referral_code`
- `invited_by_session_id`
- `invited_by_referral_code`
- `referral_source`
- `referral_medium`
- `referral_campaign`
- `referral_landing_path`
- `referral_link_id`
- `referral_arrived_at`
- `was_referred`
- `referral_depth`
- `shared_any`
- `share_channel`

## sonar_analysis_dataset_simulated.csv
Clean analytic dataset built from the simulated raw files.

Extra derived variables:
- `position_segment`
- `series_progress_share`
- `treated_high_norm`
- `treatment_seed_level`
- `reported_matches_max_seen`
- `report_gap_from_max_seen`
- `report_gap_from_last_seen`
- `lie_to_six`
- `overreport_amount`
- `multiple_focus_loss`
- `network_error_any`
- `used_info_modal`
- `root_position_id`
