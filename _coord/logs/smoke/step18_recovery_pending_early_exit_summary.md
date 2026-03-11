# STEP18 Recovery Pending EARLY_EXIT Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step18/step18_tester_recovery_pending_early_exit.ini`

Purpose:
- validate the pending `EARLY_EXIT` recovery probe with STEP18 diagnostics in
  place
- confirm recovery coverage does not change retained live artifacts

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpTestRecoveryReloadEnabled=true`
- `InpTestRecoveryReloadMode=2`

Observed results:
- tester reported `final balance 504.00 USD`
- tester reported `Test passed`
- tester recovery probe was observed:
  - `probe_begin mode=PENDING_EXIT ... pending_exit_reason=EARLY_EXIT`
  - `probe_complete mode=PENDING_EXIT has_position=false ... exited_this_bar=true`
- deinit summary matched the retained live early-exit semantics:
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:101 exec:101 reject:0]`
  - `retcode=[done:204 partial:0 zero:0 other:0]`
  - `tx=[request:204 deal_add:205 position:0 other:410]`
  - `diag=[entry:10009/done_at_25592.14_exit:10009/done_at_25564.64_exit_synth:false_tx:DEAL/10009/-_other:0/_other_synth:false]`
  - `early=[eval:305 attempt:101 exec:101 reject:0 min_hold:204 pass:305]`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to `_coord/artifacts/step17_recovery_pending_early_exit_smoke/trade_log.csv`
- `exec_state.ini` is byte-identical to `_coord/artifacts/step17_recovery_pending_early_exit_smoke/exec_state.ini`

Interpretation:
- Recovery coverage remains tester-only, but it runs on top of the same actual
  live close path as the ordinary live early-exit run.
- The retained artifacts stayed unchanged while the recovery probe and
  diagnostics were visible.

Retained artifact copy:
- `_coord/artifacts/step18_recovery_pending_early_exit/trade_log.csv`
- `_coord/artifacts/step18_recovery_pending_early_exit/exec_state.ini`
- `_coord/artifacts/step18_recovery_pending_early_exit/tester_log_tail.txt`
