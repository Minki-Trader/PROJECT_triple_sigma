# STEP18 Live Early Exit Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step18/step18_tester_live_early_exit.ini`

Purpose:
- validate the ordinary live Early-Exit request/result path after STEP18
  observability hardening
- confirm the new diagnostics appear without changing STEP17 live semantics

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`
- `InpTestEarlyExitRejectOnce=false`

Observed results:
- tester reported `final balance 504.00 USD`
- tester reported `Test passed`
- deinit summary confirmed the actual live close path executed:
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:101 exec:101 reject:0]`
  - `retcode=[done:204 partial:0 zero:0 other:0]`
  - `tx=[request:204 deal_add:205 position:0 other:410]`
  - `diag=[entry:10009/done_at_25592.14_exit:10009/done_at_25564.64_exit_synth:false_tx:DEAL/10009/-_other:0/_other_synth:false]`
  - `early=[eval:305 attempt:101 exec:101 reject:0 min_hold:204 pass:305]`
  - `shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0]`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to `_coord/artifacts/step17_live_early_exit_smoke/trade_log.csv`
- `exec_state.ini` is byte-identical to `_coord/artifacts/step17_live_early_exit_smoke/exec_state.ini`

Interpretation:
- This run is the STEP18 actual-path check.
- It uses the normal tester execution path with real `CTrade.Result*` values and
  `TRADE_TRANSACTION_REQUEST` observer diagnostics.
- No synthetic reject was involved in this run.

Retained artifact copy:
- `_coord/artifacts/step18_live_early_exit/trade_log.csv`
- `_coord/artifacts/step18_live_early_exit/exec_state.ini`
- `_coord/artifacts/step18_live_early_exit/tester_log_tail.txt`
