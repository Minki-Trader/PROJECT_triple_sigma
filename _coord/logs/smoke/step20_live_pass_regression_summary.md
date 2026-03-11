# STEP20 Live Pass Regression Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_live_pass_regression.ini`

Validation class:
- actual-path live-pass regression

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=false`
- `InpPExitPass=0.09`
- `InpProtectiveAdjustEnabled=false`
- `InpBreakEvenEnabled=false`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- deinit summary confirms the STEP19 pass-based live branch stayed intact:
  - `entry=[attempt:6506 exec:6505 reject:1]`
  - `exit=[attempt:6478 exec:6460 reject:18]`
  - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:19434 opposite:0 other:0 last:P_EXIT_PASS]`
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
- `trade_log.csv` is byte-identical to `_coord/artifacts/step19_live_pass_regression/trade_log.csv`
- `exec_state.ini` is intentionally extended for STEP20 pending-modify fields:
  - STEP20: `8d2f2ffa4a2080b30f3bb3c1ed0f1d5297932d7552b8cf870326900d8a6a9058`
  - STEP19: `0711e32968a44cb1f850610c35e1c45843a88dcf8fcaba5a7179e00a7f16c95f`
- no active `pending_modify_*` state remained at tester end

Interpretation:
- STEP20 kept the existing minimal live Early Exit path stable.
- The only additive change is the dormant modify/recovery surface; trade-log
  semantics remain unchanged.

Retained artifact copy:
- `_coord/artifacts/step20_live_pass_regression/`
