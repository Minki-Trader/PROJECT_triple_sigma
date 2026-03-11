# STEP17 Pending EARLY_EXIT Recovery Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step17/step17_tester_recovery_pending_early_exit.ini`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`
- `InpTestRecoveryReloadEnabled=true`
- `InpTestRecoveryReloadMode=2`

Observed results:
- tester reported `final balance 504.00 USD`
- tester reported `Test passed`
- recovery probe lines were emitted:
  - `probe_begin mode=PENDING_EXIT trade_id=TS_00001 trade_counter=1 bars_held=3 pending_exit_reason=EARLY_EXIT detail=EARLY_EXIT`
  - `probe_complete mode=PENDING_EXIT has_position=false trade_id= trade_counter=1 bars_held=0 pending_exit_reason= exited_this_bar=true`
- deinit summary matched the live Early Exit smoke:
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:101 exec:101 reject:0]`
  - `early=[eval:305 attempt:101 exec:101 reject:0 min_hold:204 pass:305]`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- duplicate `(trade_id,event_type)` groups: `0`

Interpretation:
- The pending `EARLY_EXIT` persistence path survives the reload probe and closes
  cleanly without duplicating the `EXIT` row.

Retained artifact copy:
- `_coord/artifacts/step17_recovery_pending_early_exit_smoke/trade_log.csv`
- `_coord/artifacts/step17_recovery_pending_early_exit_smoke/exec_state.ini`
- `_coord/artifacts/step17_recovery_pending_early_exit_smoke/tester_log_tail.txt`
