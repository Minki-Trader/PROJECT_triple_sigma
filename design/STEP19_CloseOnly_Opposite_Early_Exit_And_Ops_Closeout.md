# STEP19 Close-Only Opposite Early Exit And Ops Closeout

Purpose:
- Add the smallest safe widening after STEP18:
  - default-off close-only opposite-direction live Early Exit
- Close the operator-facing gaps needed to understand and retain evidence for
  that branch over a longer tester window.

In scope:
- `InpEarlyExitOppositeEnabled=false` default-off runtime flag
- tester-only opposite-trigger fabrication for deterministic coverage
- close-only opposite branch reusing the existing `TS_ClosePositionByReason()`
  path
- live early-exit reason observability in the monitor summary
- retained artifact standard, recovery matrix, and early-exit triage runbook
- longer-window tester evidence:
  - `2025.04.02` to `2026.03.06`

Out of scope:
- `BE` / `MODIFY`
- core `bar_log` / `trade_log` schema expansion
- authoritative persistence of Early Exit subtype detail
- making `OnTradeTransaction()` the authoritative state machine
- broker-connected / live-account testing
- profitability sign-off or model optimization work

Authoritative runtime rule:
- direct `CTrade.Result*`:
  immediate call-site diagnostics
- `pending_exit_*`:
  persisted generic exit intent
- `TS_SyncPositionState()`:
  authoritative final reconciliation
- `OnTradeTransaction()`:
  observer-only diagnostic surface

Runtime modes after STEP19:
- OFF:
  - `InpEarlyExitEnabled=false`
- SHADOW_ONLY:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=false`
- LIVE_PASS_ONLY:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - `InpEarlyExitOppositeEnabled=false`
- LIVE_PASS_PLUS_OPPOSITE:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - `InpEarlyExitOppositeEnabled=true`

Close-only Early Exit resolver:
- priority:
  1. `OPPOSITE_DIR`
  2. `P_EXIT_PASS`
- both still require:
  - held position exists
  - decision ready
  - no pending exit already set
  - `bars_held >= min_hold_bars_before_exit`

Synthetic vs actual-path taxonomy:
- synthetic:
  - `InpTestForceOppositeEarlyExit=true`
  - `InpTestEarlyExitRejectOnce=true`
  - recovery reload probes
- actual-path in tester:
  - `PositionClose()`
  - direct `CTrade.Result*`
  - `TRADE_TRANSACTION_REQUEST` observer diagnostics
  - `pending_exit_*` persistence
  - `TS_SyncPositionState()` reconciliation
  - final `trade_log.csv` emission

Long-window validation matrix:
- control trade
  - early exit disabled
- live pass regression
  - live pass-only branch, opposite disabled
- live opposite probe
  - opposite enabled
  - tester-only opposite trigger on
  - `InpPExitPass=1.0` to isolate the opposite branch
- recovery pending opposite probe
  - live opposite probe + recovery reload probe
- reject-once opposite probe
  - live opposite probe + synthetic reject-once

Acceptance:
- compile clean
- control trade artifacts valid
- live pass regression keeps opposite count at `0`
- live opposite probe produces `early.opposite > 0`
- `trade_log.csv` still uses only `ENTRY` / `EXIT`
- `exit_reason=EARLY_EXIT` still carries all live early exits
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`
- recovery clears pending exit state without duplicate `EXIT`
- retained artifact directories include README, manifest, bar logs, and a
  single-run tester log excerpt

Rollback:
- any control/pass regression that changes trade semantics with
  `InpEarlyExitOppositeEnabled=false`
- duplicate `EXIT`
- same-bar `EXIT -> ENTRY`
- stuck `pending_exit_*` after recovery
- subtype visibility requiring core CSV schema changes
- tester-only opposite trigger leaking into non-tester mode
