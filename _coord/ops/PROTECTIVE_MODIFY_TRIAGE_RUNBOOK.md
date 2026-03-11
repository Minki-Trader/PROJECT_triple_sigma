# Protective Modify Triage Runbook

Purpose:
- Explain how the current STEP21 protective modify runtime should be debugged.

Authoritative order:
1. direct `CTrade.Result*`
2. `pending_modify_*`
3. `OnTradeTransaction()` tx-authoritative entry / exit diagnostics
4. `TS_SyncPositionState()` fallback reconciliation

Current runtime contract:
- protective modify families currently implemented:
  - `BREAK_EVEN`
  - `TRAILING`
  - `TP_RESHAPE`
  - `TIME_POLICY`
- modify intent is persisted through:
  - `pending_modify_reason`
  - `pending_modify_sl_hint`
  - `pending_modify_tp_hint`
- executed modifies emit `trade_log.csv` `MODIFY` rows
- `bar_log_YYYYMMDD.csv` carries pending / last-modify / tx-authority state
- optional `broker_audit.csv` adds `modify_applied`
- the close path remains higher priority than protective modify

Expected modify lifecycle:
1. post-decision protective-adjust path evaluates eligible modify families
2. min-hold or precedence may block the modify attempt
3. `TS_ModifyPositionByReason(...)` sends `PositionModify(...)`
4. direct result is recorded through `CTrade.Result*`
5. `pending_modify_*` persists the intended stop / TP snapshot
6. `TS_ExecRecordModifyApplied(...)` emits the `MODIFY` row on success
7. `TS_SyncPositionState()` or tx observation clears pending modify after the
   live snapshot matches

Validation taxonomy:
- actual-path:
  - real tester `PositionModify(...)`
  - direct `CTrade.Result*`
  - transaction-request diagnostics
  - tx-authoritative or sync-backed final reconcile
- synthetic:
  - `InpTestForceBreakEvenOnce=true`
  - `InpTestModifyRejectOnce=true`
  - recovery reload probes

What to look at first:
- monitor summary `modify=[...]`
- direct result diagnostics in `diag=[...]`
- `pending_modify_*` fields in `exec_state.ini`
- `trade_log.csv` `MODIFY` rows and `modify_reason`
- `broker_audit.csv` `modify_applied` tags when broker audit is enabled

Expected invariants:
- `trade_log.csv` `MODIFY` rows appear only when a live modify succeeds
- duplicate non-modify `(trade_id,event_type)` groups remain `0`
- duplicate `EXIT` groups remain `0`
- same-timestamp `EXIT -> ENTRY` remains `0`
- close-vs-modify precedence keeps modify attempts at `0` on the close bar
- `pending_modify_*` must clear after reconcile
- once break-even is applied, SL must not move away from break-even again

Typical failure patterns:
- `modify attempt > 0` while a same-bar close already won
- `pending_modify_*` remains populated after the live stop matches
- synthetic reject is not labeled as synthetic
- direct retcode is non-executed but monitor still counts modify executed
- missing or duplicated `MODIFY` rows
- `MODIFY` rows appear while the corresponding feature flag is off

Rollback triggers:
- feature-off regressions change retained STEP20 core trade rows
- duplicate `EXIT` or same-bar `EXIT -> ENTRY`
- stuck `pending_modify_*`
- modify widens risk or moves backward after applied
- tester-only trigger or reject injection leaks outside tester mode
