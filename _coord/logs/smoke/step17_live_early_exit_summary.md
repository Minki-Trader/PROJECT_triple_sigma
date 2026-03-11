# STEP17 Live Early Exit Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step17/step17_tester_live_early_exit.ini`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`
- `InpTestEarlyExitRejectOnce=false`

Observed results:
- tester reported `final balance 504.00 USD`
- tester reported `Test passed`
- deinit summary confirmed the minimal live Early Exit path executed:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:101 exec:101 reject:0]`
  - `early=[eval:305 attempt:101 exec:101 reject:0 min_hold:204 pass:305]`
  - `shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0]`
  - `force_exit=0`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`
- non-early exit counts:
  - `SL=1`
  - `TP=0`
  - `FORCE_EXIT=0`

Interpretation:
- STEP17 minimal live Early Exit is active only through the existing `EXIT`
  row type.
- The new executable path materially changes hold-time and PnL, but it does so
  through the narrow `P_EXIT_PASS` trigger only.

Retained artifact copy:
- `_coord/artifacts/step17_live_early_exit_smoke/trade_log.csv`
- `_coord/artifacts/step17_live_early_exit_smoke/exec_state.ini`
- `_coord/artifacts/step17_live_early_exit_smoke/tester_log_tail.txt`
