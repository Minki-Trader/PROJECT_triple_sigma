# STEP16 Recovery Open-Position Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step16/step16_tester_recovery_open.ini`

Purpose:
- validate persisted execution-state recovery at an open-position checkpoint
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
  - `shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0]`
- open-position recovery probe fired once:
  - `probe_begin mode=OPEN_POSITION trade_id=TS_00001 trade_counter=1 bars_held=3`
  - `loaded persisted state ... has_position=true trade_id=TS_00001 trade_counter=1`
  - `probe_complete ... has_position=true trade_id=TS_00001 trade_counter=1 bars_held=2`
- `trade_log.csv` remained aligned with the control trade smoke:
  - `ENTRY=14`
  - `EXIT=13`
  - no duplicate `ENTRY`
  - no extra `EXIT`
  - `EARLY_EXIT=0`
  - `MODIFY=0`

Interpretation note:
- The post-probe `bars_held=2` line is the pre-manage snapshot re-derived by
  `TS_SyncPositionState()` on the same bar.
- This smoke still confirms that persisted `trade_id` / `trade_counter` reload
  correctly and that the live position snapshot is recovered conservatively
  without duplicate trade-log rows.

Retained artifact copy:
- `_coord/artifacts/step16_recovery_open_smoke/trade_log.csv`
- `_coord/artifacts/step16_recovery_open_smoke/exec_state.ini`
- `_coord/artifacts/step16_recovery_open_smoke/tester_log_tail.txt`
