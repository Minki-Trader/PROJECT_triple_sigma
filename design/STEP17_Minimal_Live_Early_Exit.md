# STEP17 Minimal Live Early Exit

Purpose:
- Open exactly one new executable runtime behavior on top of the closed STEP16
  seam/refactor baseline.
- Keep the widening narrow enough that recovery, logging, and reject-path
  verification can still close in the same step.

In scope:
- Reuse the STEP16 seam:
  - pre-decision live management
  - post-decision Early Exit evaluation
- Add minimal live Early Exit when all of these are true:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - `p_pass >= p_exit_pass`
  - `bars_held >= min_hold_bars_before_exit`
- Emit live Early Exit through the existing close/reconcile path only.
- Keep `trade_log.csv` schema unchanged:
  - `event_type=EXIT`
  - `exit_reason=EARLY_EXIT`
- Add tester-only reject-once injection for the first `EARLY_EXIT` close
  attempt.
- Add STEP17 smoke coverage for:
  - control trade regression
  - shadow regression
  - live Early Exit
  - pending `EARLY_EXIT` recovery
  - reject-once path

Explicitly out of scope:
- live opposite-dir Early Exit
- BE / MODIFY
- `trade_log` `MODIFY` rows
- core `bar_log` / `trade_log` schema expansion
- promoting `OnTradeTransaction()` into the authoritative state machine
- runtime hot reload / rollback
- retraining / repackaging

Mode matrix:
- OFF:
  - `InpEarlyExitEnabled=false`
  - no post-decision Early Exit evaluation
- SHADOW_ONLY:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=false`
  - observe only; never close
- LIVE_PASS_ONLY:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - only `P_EXIT_PASS` is executable

Why only `P_EXIT_PASS` goes live:
- STEP16 retained shadow evidence already exercised the pass bucket heavily.
- The opposite-direction shadow bucket remained `0` in the retained smoke.
- The first executable cut should only promote a reason family that already has
  retained coverage.

Implementation notes:
- Keep `TS_ManagePositionPreDecision()` unchanged.
- Keep the same ordering in `OnTimer()`:
  - sync
  - pre-decision live management
  - inference / decision / gates
  - post-decision Early Exit handling
  - entry attempt
- Keep `g_ts_exec_exited_this_bar` as the same-bar re-entry guard.
- Keep `TS_SyncPositionState()` as the authoritative reconciliation path.
- Keep `OnTradeTransaction()` observer-only.

Files touched by STEP17:
- `src/ea/TripleSigma.mq5`
- `src/include/TS_Execution.mqh`
- `src/include/TS_Monitor.mqh`
- `TRIPLE-SIGMA/EA_RUNTIME.md`
- `design/BAR_LOG_SCHEMA.md`
- `_coord/tester/step17/*.ini`
- `_coord/logs/smoke/step17_*`

Acceptance:
- compile clean
- control trade smoke matches STEP16 baseline
- shadow regression smoke keeps STEP16 live outcome unchanged
- live Early Exit smoke emits `EARLY_EXIT > 0`
- same-bar re-entry does not occur
- duplicate `EXIT` rows do not occur
- pending `EARLY_EXIT` recovery completes cleanly
- reject-once smoke shows one rejected close attempt without phantom `EXIT`
- `MODIFY=0`
- 72-bar `FORCE_EXIT` hard cap remains unchanged

Rollback conditions:
- control trade smoke diverges from STEP16 baseline when live Early Exit is off
- same-bar exit/re-entry appears
- duplicate `EXIT` rows appear
- reject-once path leaves stuck `pending_exit_*`
- live path leaks opposite-dir behavior
- schema drift becomes necessary to explain runtime behavior
