# STEP16 Recovery Pending-Exit Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step16/step16_tester_recovery_pending_exit.ini`

Purpose:
- validate persisted `pending_exit_*` recovery after the exit state is saved
- confirm STEP16 phase-2 live semantics stay aligned with the control trade smoke

Tester note:
- This smoke uses a tester-only execution-state recovery probe.
- The probe path is:
  persisted save -> reset execution globals -> load `exec_state.ini` ->
  `TS_SyncPositionState()`
- It validates the save/load/reconcile path in the MT5 tester without widening
  live runtime semantics.

Observed results:
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- live deinit summary stayed aligned with the control trade smoke:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `force_exit=7`
- pending-exit recovery probe fired once:
  - `probe_begin mode=PENDING_EXIT trade_id=TS_00003 trade_counter=3 bars_held=72 pending_exit_reason=FORCE_EXIT`
  - `loaded persisted state ... has_position=true trade_id=TS_00003 trade_counter=3`
  - `probe_complete ... has_position=false trade_counter=3 bars_held=0 exited_this_bar=true`
- `trade_log.csv` remained aligned with the control trade smoke:
  - `ENTRY=14`
  - `EXIT=13`
  - `FORCE_EXIT=7`
  - no duplicate `ENTRY`
  - no extra `EXIT`
  - `EARLY_EXIT=0`
  - `MODIFY=0`

Interpretation note:
- The pending-exit probe confirms that persisted `pending_exit_reason`,
  `pending_exit_deal`, and the saved trade identity are sufficient for a
  conservative exit reconciliation path.
- The probe completes with `has_position=false` and `exited_this_bar=true`,
  which is the intended post-reconcile state.

Retained artifact copy:
- `_coord/artifacts/step16_recovery_pending_exit_smoke/trade_log.csv`
- `_coord/artifacts/step16_recovery_pending_exit_smoke/exec_state.ini`
- `_coord/artifacts/step16_recovery_pending_exit_smoke/tester_log_tail.txt`
