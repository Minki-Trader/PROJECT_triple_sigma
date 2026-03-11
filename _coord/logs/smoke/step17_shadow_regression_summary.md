# STEP17 Shadow Regression Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step17/step17_tester_shadow_regression.ini`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=false`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`

Observed results:
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- deinit summary kept the live outcome aligned with the control trade smoke:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0]`
  - `shadow=[eval:733 trig:706 min_hold:27 pass:733 opposite:0 other:0]`
  - `force_exit=7`

Trade-log checks:
- `ENTRY=14`
- `EXIT=13`
- `EARLY_EXIT=0`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`

Interpretation:
- STEP17 kept the STEP16 shadow-only mode intact.
- Shadow counters still populate, while live trade semantics remain unchanged.

Retained artifact copy:
- `_coord/artifacts/step17_shadow_regression_smoke/trade_log.csv`
- `_coord/artifacts/step17_shadow_regression_smoke/exec_state.ini`
- `_coord/artifacts/step17_shadow_regression_smoke/tester_log_tail.txt`
