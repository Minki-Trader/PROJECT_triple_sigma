# US100 Real-Tick Backtest Data Policy

- Date: 2026-03-09
- Symbol: `US100`
- Purpose: define which periods are acceptable for backtest optimization,
  final comparison, recent validation, and auxiliary training under
  MT5 `Every tick based on real ticks`.

## Core position

Yes, the practical analysis horizon can be treated as:

- `2022-09-13 17:15` -> `2026-03-06 23:55`

But that does **not** mean this entire span should be used as one homogeneous
clean optimization block.

The correct interpretation is:

- the horizon is shared
- the roles are different
- the windows are split on purpose

In other words, we keep one broad real-tick-era horizon, but we assign
different subranges to different jobs.

## Why the range is split

Inside the broader actual-tick era, the data quality is not uniform.

Fully clean actual-tick windows:

- `2022-09-13 17:15` -> `2023-05-03 09:45`
- `2023-05-03 09:55` -> `2024-02-26 20:05`
- `2024-06-04 17:25` -> `2025-04-02 09:00`
- `2025-04-02 09:10` -> `2025-11-24 14:50`

Recent practical extension:

- `2025-11-24 15:00` -> `2025-11-28 05:00`
- `2025-11-28 05:10` -> `2026-03-06 23:55`

The reason the final tail is treated separately is simple:

- there are two 10-minute intraday gaps
  - `2025-11-24 14:50` -> `2025-11-24 15:00`
  - `2025-11-28 05:00` -> `2025-11-28 05:10`

These gaps are small enough to be operationally acceptable for recent
validation, but they are still not equivalent to a perfectly clean single
window.

## Final recommended usage

### 1. Primary optimization corpus

Use the clean actual-tick rolling pack (benchmark window excluded):

- `2022-09-13 17:15` -> `2023-05-03 09:45`
- `2023-05-03 09:55` -> `2024-02-26 20:05`
- `2025-04-02 09:10` -> `2025-11-24 14:50`

NOTE: The largest clean window (`2024-06-04 17:25` -> `2025-04-02 09:00`) is
reserved exclusively for benchmark (Section 2) and is NOT included here,
to keep benchmark independent from the optimization corpus.

Why:

- no generated-tick substitution inside the selected windows
- no intraday missing-bar contamination inside those clean folds
- better for rolling / walk-forward / fold-based optimization
- benchmark window deliberately excluded to prevent data leakage

### 2. Final single benchmark window

Use:

- `2024-06-04 17:25` -> `2025-04-02 09:00`

Why:

- largest clean single actual-tick window
- best high-confidence single comparison period

### 3. Recent practical OOS validation

Use:

- `2025-11-24 15:00` -> `2026-03-06 23:55`

Interpretation:

- this is the recent validation span
- it intentionally keeps the latest data
- it starts after fold_4 (`2025-04-02 09:10` -> `2025-11-24 14:50`) + 10-min gap
  to guarantee no role overlap with the optimization corpus (WF0)
- it includes one minor 10-minute gap (`2025-11-28 05:00` -> `2025-11-28 05:10`)
- this is acceptable as a practical recent OOS range

Previous version used `2025-04-02 09:10` as start, which caused the OOS window
to fully contain the fourth optimization fold. This was corrected to enforce
strict role separation per WF0.

### 4. Broad exploratory stress run

Use:

- `2022-08-01` -> `2026-03-06 23:55`

Why:

- this is the outer contiguous actual-tick month coverage span
- useful for broad sanity / stress / exploratory runs
- not the preferred main optimization corpus

## Practical interpretation

So the short answer is:

- yes, from a practical decision-making perspective you can think in terms of
  the broad real-tick-era horizon
  `2022-09-13 17:15` -> `2026-03-06 23:55`
- but the horizon is intentionally split by role

Use it like this:

- optimization: clean rolling pack
- final single benchmark: clean single best window
- recent OOS validation: `2025-11-24 15:00` through `2026-03-06 23:55`

## What should not be used as the main corpus

Do **not** use the full long history

- `2018-05-08 01:00` -> `2026-03-06 23:55`

as one main optimizer/final comparison range.

Reason:

- missing tick months from `2020-01` to `2022-07`
- `180,275` M5 bars fall inside those missing tick months
- this is `37.0%` of bars inside the broader observed tick range

That is too much generated/substituted-tick exposure for main optimizer or
final Model=4 comparison use.

## Training note

For pure ML training volume, the risk is lower because the current STEP11+
pipeline is bar-close driven rather than raw-tick driven.

So if extra bar-based training data is needed, the following segment may still
be used as auxiliary train-only data:

- `2021-02-01 03:00` -> `2022-09-13 17:05`

But keep it out of:

- primary optimization selection
- final Model=4 comparison
- real-tick execution evidence

## Operational rule

Use these levels:

1. Strict:
   clean actual-tick only
2. Practical:
   recent OOS may include the two tiny 10-minute gaps
3. Exploratory:
   full contiguous actual-tick month span
4. Disallowed as primary corpus:
   long-range generated-tick-substituted history
