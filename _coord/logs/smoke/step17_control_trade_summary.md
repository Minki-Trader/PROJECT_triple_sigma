# STEP17 Control Trade Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step17/step17_tester_control_trade.ini`

Tester input highlights:
- `InpEarlyExitEnabled=false`
- `InpEarlyExitLive=false`
- `InpTestEarlyExitRejectOnce=false`

Observed results:
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- deinit summary confirmed STEP16 baseline behavior was preserved:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0]`
  - `shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0]`
  - `force_exit=7`

Trade-log checks:
- `ENTRY=14`
- `EXIT=13`
- `EARLY_EXIT=0`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- exit reason counts:
  - `FORCE_EXIT=7`
  - `SL=4`
  - `TP=2`

Interpretation:
- This run is the STEP17 control gate.
- With live Early Exit disabled, the live outcome matches the retained STEP16
  trade-producing smoke behavior.

Retained artifact copy:
- `_coord/artifacts/step17_control_trade_smoke/trade_log.csv`
- `_coord/artifacts/step17_control_trade_smoke/exec_state.ini`
- `_coord/artifacts/step17_control_trade_smoke/tester_log_tail.txt`
