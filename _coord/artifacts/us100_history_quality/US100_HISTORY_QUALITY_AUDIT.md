# US100 History Quality Audit

## Scope
- Symbol: `US100`
- Bar series: `M5` tester-exported bars
- Tick coverage: `FPMarketsSC-Live` monthly `.tkc` files

## Headline Findings
- Earliest exported M5 bar: `2018-05-08 01:00`
- Latest exported M5 bar: `2026-03-06 23:55`
- Exported M5 bars: `549608`
- Gaps greater than 5 minutes: `2853`
- Recurring market-closure gaps: `2705`
- Exceptional closure/missing candidates: `91`
- Intraday missing-bar candidates: `57`

## Tick Coverage
- Tick months present: `53`
- Tick months missing inside observed range: `31`
- Missing tick months: `202001, 202002, 202003, 202004, 202005, 202006, 202007, 202008, 202009, 202010, 202011, 202012, 202101, 202102, 202103, 202104, 202105, 202106, 202107, 202108, 202109, 202110, 202111, 202112, 202201, 202202, 202203, 202204, 202205, 202206, 202207`

## Clean M5 Segment
- Largest segment without intraday missing-bar candidates: `2021-02-01 03:00` -> `2022-09-13 17:05`
- Bars: `114049`
- Calendar span (days): `589.59`

## Clean Real-Tick Segment
- Largest contiguous tick-month segment: `2022-08-01` -> `2026-03-06 23:55`
- Contiguous months: `44`
- Calendar span (days): `1314.0`

## Recommended Clean Real-Tick Backtest Segment
- Best overlap of bar-clean + tick-contiguous coverage: `2024-06-04 17:25` -> `2025-04-02 09:00`
- Calendar span (days): `301.65`

## Intraday Missing-Bar Candidates
- `2018-05-10 16:20` -> `2018-05-10 16:55` : `35` minutes
- `2018-05-10 17:00` -> `2018-05-10 17:10` : `10` minutes
- `2018-06-07 22:20` -> `2018-06-07 22:30` : `10` minutes
- `2018-07-25 04:15` -> `2018-07-25 04:25` : `10` minutes
- `2018-09-26 01:10` -> `2018-09-26 01:45` : `35` minutes
- `2018-10-16 10:30` -> `2018-10-16 10:40` : `10` minutes
- `2018-12-26 22:45` -> `2018-12-26 23:00` : `15` minutes
- `2019-04-11 02:30` -> `2019-04-11 02:55` : `25` minutes
- `2019-04-11 02:55` -> `2019-04-11 03:15` : `20` minutes
- `2019-05-15 17:10` -> `2019-05-15 17:35` : `25` minutes
- `2019-09-18 10:00` -> `2019-09-18 10:10` : `10` minutes
- `2019-10-01 07:40` -> `2019-10-01 07:50` : `10` minutes
- `2020-02-18 02:30` -> `2020-02-18 02:45` : `15` minutes
- `2020-03-02 03:35` -> `2020-03-02 03:45` : `10` minutes
- `2020-03-09 05:05` -> `2020-03-09 05:15` : `10` minutes
- `2020-03-09 05:20` -> `2020-03-09 06:10` : `50` minutes
- `2020-03-09 07:05` -> `2020-03-09 07:25` : `20` minutes
- `2020-03-09 08:35` -> `2020-03-09 08:50` : `15` minutes
- `2020-03-09 09:10` -> `2020-03-09 09:25` : `15` minutes
- `2020-03-09 11:05` -> `2020-03-09 11:25` : `20` minutes

## Exceptional Closure Or Missing Candidates
- `2018-05-18 23:10` -> `2018-05-21 02:25` : `3075` minutes (pattern_count=1)
- `2018-05-25 23:10` -> `2018-05-28 01:55` : `3045` minutes (pattern_count=1)
- `2018-07-03 20:15` -> `2018-07-04 01:00` : `285` minutes (pattern_count=1)
- `2018-07-04 20:00` -> `2018-07-05 01:00` : `300` minutes (pattern_count=2)
- `2018-08-22 20:15` -> `2018-08-22 22:00` : `105` minutes (pattern_count=1)
- `2018-08-28 23:55` -> `2018-08-29 01:20` : `85` minutes (pattern_count=1)
- `2018-09-14 19:30` -> `2018-09-14 21:35` : `125` minutes (pattern_count=1)
- `2018-10-17 23:55` -> `2018-10-18 01:35` : `100` minutes (pattern_count=1)
- `2018-10-26 23:10` -> `2018-10-29 03:15` : `3125` minutes (pattern_count=1)
- `2018-11-22 19:55` -> `2018-11-23 01:00` : `305` minutes (pattern_count=4)
- `2018-11-23 20:15` -> `2018-11-26 01:00` : `3165` minutes (pattern_count=7)
- `2018-12-05 16:25` -> `2018-12-06 01:00` : `515` minutes (pattern_count=1)
- `2018-12-24 20:10` -> `2018-12-26 01:00` : `1730` minutes (pattern_count=1)
- `2018-12-31 23:55` -> `2019-01-02 01:00` : `1505` minutes (pattern_count=1)
- `2019-02-27 02:50` -> `2019-02-27 05:45` : `175` minutes (pattern_count=1)
- `2019-04-11 03:30` -> `2019-04-11 06:05` : `155` minutes (pattern_count=1)
- `2019-04-18 23:55` -> `2019-04-22 01:00` : `4385` minutes (pattern_count=7)
- `2019-05-27 20:05` -> `2019-05-28 01:00` : `295` minutes (pattern_count=1)
- `2019-07-01 01:20` -> `2019-07-01 02:55` : `95` minutes (pattern_count=1)
- `2019-07-03 20:15` -> `2019-07-04 01:00` : `285` minutes (pattern_count=2)

## Recommended Backtest Usage
- For `Model=4` real-tick backtests, prefer the largest contiguous tick-month segment first.
- Use `m5_clean_segments.csv` to inspect bar-continuous windows separately from tick-month continuity.
- Treat `intraday_missing_candidate` rows as the primary data-quality red flag for bar continuity.

## Files
- `summary.json`
- `m5_gap_events.csv`
- `m5_clean_segments.csv`
- `tick_month_coverage.csv`
- `tick_contiguous_segments.csv`
- `combined_clean_realtick_segments.csv`
- `US100_HISTORY_QUALITY_AUDIT.xlsx`