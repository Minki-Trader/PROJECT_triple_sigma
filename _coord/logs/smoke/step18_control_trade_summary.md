# STEP18 Control Trade Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step18/step18_tester_control_trade.ini`

Purpose:
- prove STEP18 observability hardening does not widen OFF-mode trade semantics
- capture direct-result and transaction-request diagnostics on the ordinary
  tester request/result path

Observed results:
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- deinit summary confirmed baseline trade semantics were unchanged:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `retcode=[done:21 partial:0 zero:0 other:0]`
  - `tx=[request:21 deal_add:27 position:0 other:54]`
  - `diag=[entry:10009/done_at_25592.14_exit:10009/done_at_25536.89_exit_synth:false_tx:DEAL/10009/-_other:0/_other_synth:false]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0]`
  - `force_exit=7`

Trade-log checks:
- `ENTRY=14`
- `EXIT=13`
- `EARLY_EXIT=0`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to `_coord/artifacts/step17_control_trade_smoke/trade_log.csv`
- `exec_state.ini` is byte-identical to `_coord/artifacts/step17_control_trade_smoke/exec_state.ini`

Interpretation:
- STEP18 does not replace smoke with a no-smoke path.
- For this step, the ordinary tester entry/exit run is the actual-path
  validation surface, and the added diagnostics are visible without changing
  trade semantics.

Retained artifact copy:
- `_coord/artifacts/step18_control_trade/trade_log.csv`
- `_coord/artifacts/step18_control_trade/exec_state.ini`
- `_coord/artifacts/step18_control_trade/tester_log_tail.txt`
