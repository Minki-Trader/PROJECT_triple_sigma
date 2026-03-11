# STEP20 Bounded BE Modify

Purpose:
- Add the smallest safe post-entry widening after STEP19:
  - bounded live protective adjustment
  - BE-only, one-way SL modify
- Keep the current close/reconcile contract intact.

In scope:
- `InpProtectiveAdjustEnabled=false` default-off runtime flag
- `InpBreakEvenEnabled=false` default-off BE flag
- one-way SL modify only
- no TP reshape
- no trailing logic
- no extra time-policy logic
- tester-only BE trigger fabrication
- tester-only modify reject-once injection
- pending modify persistence and recovery
- longer-window tester evidence:
  - `2025.04.02` to `2026.03.06`

Out of scope:
- core `trade_log.csv` / `bar_log` schema expansion
- `MODIFY` rows in `trade_log.csv`
- `pending_exit_*` generalization
- authoritative `OnTradeTransaction()` state machine
- broker-connected / live-account testing
- profitability sign-off or model optimization work

Authoritative runtime rule:
- direct `CTrade.Result*`:
  immediate call-site diagnostics
- `pending_exit_*`:
  persisted generic exit intent
- `pending_modify_*`:
  persisted generic modify intent
- `TS_SyncPositionState()`:
  authoritative final reconciliation
- `OnTradeTransaction()`:
  observer-only diagnostic surface

Protective-adjustment rule:
- current runtime still evaluates close-only Early Exit first
- BE modify is evaluated only after the live Early Exit branch
- if close and modify are both eligible on the same bar:
  - close wins
  - modify attempt must stay `0` for that bar

Bounded BE rule:
- trigger family:
  - RR-based break-even threshold
  - optional tester-only synthetic BE trigger
- modify family:
  - SL only moves toward break-even
  - never widens initial risk
  - never moves backward after BE is applied
- TP remains unchanged

Persistence rule:
- `pending_modify_*` is append-only state extension in `exec_state.ini`
- `pending_exit_*` semantics remain unchanged
- restart/reload recovery must clear pending modify only after live-position
  reconciliation observes the expected SL/TP snapshot

Core schema rule:
- `trade_log.csv` still emits only `ENTRY` / `EXIT`
- BE modify must not create `MODIFY` rows
- any effect of BE is observed later through:
  - current live position snapshot
  - later `EXIT` row using the latest `sl_price`
  - monitor summary / tester logs / retained artifacts

Synthetic vs actual-path taxonomy:
- synthetic:
  - `InpTestForceBreakEvenOnce=true`
  - `InpTestModifyRejectOnce=true`
  - recovery reload probes
- actual-path in tester:
  - `PositionModify(ticket, ...)`
  - direct `CTrade.Result*`
  - `TRADE_TRANSACTION_REQUEST` observer diagnostics
  - `pending_modify_*` persistence
  - `TS_SyncPositionState()` reconciliation
  - final `trade_log.csv` emission

Long-window validation matrix:
- control trade
  - early exit disabled
  - protective adjust disabled
- live pass regression
  - existing STEP19 live pass branch
  - protective adjust disabled
- live opposite regression
  - existing STEP19 live opposite branch
  - protective adjust disabled
- live BE probe
  - protective adjust enabled
  - BE enabled
  - tester-only BE trigger on
- recovery pending modify
  - live BE probe + recovery reload probe
- reject-once modify
  - live BE probe + synthetic modify reject-once
- close-vs-modify precedence
  - live opposite close branch + tester-only BE trigger
  - close must win, modify attempt stays zero

Acceptance:
- compile clean
- control trade artifacts remain aligned with STEP19 control
- live pass regression artifacts remain aligned with STEP19 live pass
- live opposite regression artifacts remain aligned with STEP19 live opposite
- BE probe produces modify execution without widening core CSV schema
- pending modify recovery clears after live-position reconcile
- reject-once modify produces no phantom EXIT and later modify succeeds
- close-vs-modify precedence keeps modify attempts at zero on the close bar
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`
- retained artifact directories include README, manifest, bar logs, and a
  single-run tester log excerpt

Rollback:
- any feature-off regression that changes STEP19 trade semantics
- any emitted `MODIFY` row in `trade_log.csv`
- duplicate `EXIT`
- same-bar `EXIT -> ENTRY`
- stuck `pending_modify_*` after recovery
- BE modify moving stop away from break-even once applied
- tester-only BE trigger or reject injection leaking into non-tester mode

Status after closeout:
- `2026-03-09`: STEP20 is treated as closed for its declared scope.
- The following intentionally unimplemented items are promoted to STEP21:
  - wider modify family beyond BE-only:
    - TP reshape
    - trailing logic
    - extra time-policy logic
  - core `trade_log.csv` / `bar_log` schema expansion
  - `MODIFY` row emission in `trade_log.csv`
  - authoritative `OnTradeTransaction()` state machine
  - runtime hot reload / rollback
  - broker-connected / live-account testing
- These promoted items are deferred carry-over only; they are not failed
  STEP20 acceptance items.
