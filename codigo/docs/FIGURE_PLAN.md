# Figure Plan

## Main figures
1. `figure_1_reported_6_trajectory.png`
   - Smoothed trajectory of `reported_6` by position
   - Treatments: `seed_low`, `seed_high`, optional `control`

2. `figure_2_reported_6_difference.png`
   - Smoothed difference `seed_high - seed_low` in `reported_6`

3. `figure_3_reported_6_segments.png`
   - Bars for the early segment, late segment and full segment derived from the current configuration

4. `figure_4_report_distribution.png`
   - Distribution of `reported_value` by treatment

5. `figure_5_truth_report_heatmap.png`
   - Heatmap of `true_first_result x reported_value`

## Exploratory figures
6. `figure_6_reported_5_trajectory.png`
   - Smoothed trajectory of `reported_5`

7. `figure_7_lie_amount_trajectory.png`
   - Smoothed mean `lie_amount` by position

8. `figure_8_relative_lie_distribution.png`
   - Distribution of `relative_lie` by treatment

9. `figure_9_time_block_results.png`
   - Time-block profiles for `reported_6`, `reported_5` and `is_honest`

## Style rules
- Matplotlib only
- Neutral color palette
- Short titles
- Clear axes
- Exported as PNG to `outputs/figures/`
