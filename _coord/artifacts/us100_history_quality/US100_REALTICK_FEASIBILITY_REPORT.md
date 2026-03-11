# US100 Real-Tick Feasibility Report

## Executive Summary
- Full contiguous actual-tick coverage exists only from `2022-08-01` to `2026-03-06 23:55`.
- Inside that contiguous actual-tick range, intraday bar-side missing exposure is `17` M5 bars over `254262` bars total (`0.006686`%).
- Missing tick months inside the broader observed tick range account for `180275` M5 bars (`37.0%` of bars).
- Conclusion: using the entire long history as one Model=4 optimization/evaluation range is not recommended.

## Direct Answers
1. Maximum practical actual-tick backtest span:
   - Use the contiguous actual-tick range `2022-08-01` -> `2026-03-06 23:55` as the outer limit.
2. Missing-data status under `Every tick based on real ticks`:
   - There are `31` whole months with no `.tkc` files in the broader observed tick range.
   - There are `10` intraday missing-bar events even inside the contiguous actual-tick range.
3. If generated ticks substitute the missing regions, is that acceptable?
   - For final backtest comparison and optimizer selection across the full long range: no.
   - For exploratory stress runs inside the contiguous actual-tick span with only sparse bar-side gaps: sometimes acceptable, but only with explicit contamination notes.
   - For ML training, the impact is lower because STEP11+ are bar-close driven, but that does not make generated-tick backtests equivalent to actual-tick execution studies.
4. If contamination matters, what is the best backtest plan?
   - Use a segment-aware rolling plan over clean actual-tick windows instead of one long contaminated period.
5. Can you just run the whole range anyway?
   - You can run it, but it should be tagged exploratory only, not as the main optimization/final-comparison corpus.
6. What is most suitable for training/optimization?
   - Best single high-confidence window: the largest clean actual-tick window.
   - Best overall research plan: the segmented clean actual-tick rolling pack.
   - Worst option for optimizer/final comparison: the full long range with missing tick months substituted/generated.

## Recommendation Matrix

### full_available_m5_range
- Period: `2018-05-08 01:00` -> `2026-03-06 23:55`
- Bars: `549608`
- Calendar span (days): `2859.95`
- Actual tick coverage: `incomplete`
- Generated tick exposure: `very_high (37.00% of bars fall inside months without .tkc coverage between 201904 and 202603)`
- Training suitability: `low_to_medium`
- Optimization suitability: `low`
- Final backtest suitability: `low`
- Notes: Not suitable as a single Model=4 optimization/final-evaluation range. If the tester substitutes generated ticks across missing tick months, the contamination is too large.

### largest_clean_bar_only_segment
- Period: `2021-02-01 03:00` -> `2022-09-13 17:05`
- Bars: `114049`
- Calendar span (days): `589.59`
- Actual tick coverage: `partial_or_none`
- Generated tick exposure: `n/a_for_training_bars`
- Training suitability: `medium_to_high`
- Optimization suitability: `low`
- Final backtest suitability: `low`
- Notes: Useful only as auxiliary bar-based training data. Keep it out of final Model=4 optimization/reporting because actual tick coverage is not continuous.

### full_contiguous_actual_tick_range
- Period: `2022-08-01` -> `2026-03-06 23:55`
- Bars: `254262`
- Calendar span (days): `1314.0`
- Actual tick coverage: `contiguous_months_present`
- Generated tick exposure: `low (17 missing M5 bars inside range, 0.0067% of bars)`
- Training suitability: `medium_to_high`
- Optimization suitability: `medium`
- Final backtest suitability: `medium`
- Notes: Viable for exploratory backtests and broad stress runs, but still crosses 10 intraday missing-bar events. Keep gap dates visible in evaluation notes.

### largest_clean_actual_tick_window
- Period: `2024-06-04 17:25` -> `2025-04-02 09:00`
- Bars: `58405`
- Calendar span (days): `301.65`
- Actual tick coverage: `clean_and_contiguous`
- Generated tick exposure: `none_expected`
- Training suitability: `high`
- Optimization suitability: `high`
- Final backtest suitability: `high`
- Notes: Best single clean window for high-confidence Model=4 optimization and final comparisons.

### segment_aware_clean_actual_tick_pack
- Period: `2022-09-13 17:15` -> `2025-11-24 14:50`
- Bars: `206766`
- Calendar span (days): `1069.0`
- Actual tick coverage: `clean_and_contiguous_by_segment`
- Generated tick exposure: `none_inside_selected_segments`
- Training suitability: `high`
- Optimization suitability: `high`
- Final backtest suitability: `medium_to_high`
- Notes: Best choice for rolling or walk-forward optimization. Use the four >=180-day clean actual-tick windows as separate folds instead of forcing one contaminated continuous range.

## Recommended Segment-Aware Rolling Pack
- Candidate clean actual-tick windows >=180 days: `4`
- Aggregate bars across those windows: `206766`
- Aggregate calendar days across those windows: `1069.0`

- `2024-06-04 17:25` -> `2025-04-02 09:00` | bars=`58405` | days=`301.65`
- `2023-05-03 09:55` -> `2024-02-26 20:05` | bars=`57596` | days=`299.42`
- `2025-04-02 09:10` -> `2025-11-24 14:50` | bars=`45902` | days=`236.24`
- `2022-09-13 17:15` -> `2023-05-03 09:45` | bars=`44863` | days=`231.69`

## Practical Policy
- Primary optimization / final comparison:
  use the largest clean actual-tick window first.
- Preferred broader workflow:
  use the clean actual-tick rolling pack as separate folds/windows.
- Exploratory stress runs only:
  use the full contiguous actual-tick span and annotate the sparse intraday gap dates.
- Do not treat the full long range with generated/missing tick substitution as the main optimizer or final backtest corpus.
- If additional training volume is needed, the largest clean M5-only segment may be used as auxiliary train-only data, but keep it out of final Model=4 selection/reporting.

## Files
- `US100_REALTICK_FEASIBILITY_REPORT.md`
- `US100_REALTICK_FEASIBILITY_SUMMARY.json`
- `US100_REALTICK_RECOMMENDATION_MATRIX.csv`
- `US100_REALTICK_WINDOW_CANDIDATES.csv`