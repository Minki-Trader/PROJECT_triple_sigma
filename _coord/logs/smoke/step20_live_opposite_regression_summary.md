# STEP20 Live Opposite Regression Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_live_opposite_regression.ini`

Validation class:
- synthetic trigger source + actual close path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=true`
- `InpPExitPass=1.00`
- `InpTestForceOppositeEarlyExit=true`
- `InpProtectiveAdjustEnabled=false`
- `InpBreakEvenEnabled=false`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- deinit summary confirms the opposite-detail branch was exercised while live
  trade semantics stayed aligned:
  - `entry=[attempt:6506 exec:6505 reject:1]`
  - `exit=[attempt:6478 exec:6460 reject:18]`
  - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR]`
  - `modify=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 be:0 other:0 cleared:0 last:-]`

Artifact checks:
- `trade_log.csv` rows: `13009`
- event counts: `ENTRY=6505`, `EXIT=6504`
- exit reasons:
  - `EARLY_EXIT=6460`
  - `SL=38`
  - `TP=6`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to both:
  - `_coord/artifacts/step19_live_opposite_probe/trade_log.csv`
  - `_coord/artifacts/step20_live_pass_regression/trade_log.csv`
- `exec_state.ini` is byte-identical to `_coord/artifacts/step20_live_pass_regression/exec_state.ini`

Interpretation:
- STEP20 kept the close-only opposite branch stable.
- Subtype visibility changed only in monitor/tester diagnostics; the retained
  core CSV contract remained unchanged.

Retained artifact copy:
- `_coord/artifacts/step20_live_opposite_regression/`
