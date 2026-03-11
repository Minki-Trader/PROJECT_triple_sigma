# Early Exit Triage Runbook

Purpose:
- Give one short operator-facing path for debugging close-only Early Exit runs.

Authoritative order:
1. direct `CTrade.Result*`
2. `pending_exit_*`
3. `OnTradeTransaction()` tx-authoritative entry / exit diagnostics
4. `TS_SyncPositionState()` fallback reconciliation

When `trade_log.csv` shows `EXIT` with `exit_reason=EARLY_EXIT`:
- use the monitor summary to determine subtype:
  - `pass`
  - `opposite`
- do not expect subtype detail in the core CSV

When a synthetic reject is expected:
- look for:
  - `[TS][TEST][EARLY_EXIT] reject_once ... synthetic=true`
- confirm:
  - no phantom `EXIT`
  - later actual close succeeds
  - summary still marks the synthetic reject path as synthetic

When recovery is expected:
- look for:
  - `[TS][TEST][RECOVERY] probe_begin ...`
  - `[TS][TEST][RECOVERY] probe_complete ...`
- confirm:
  - no duplicate `EXIT`
  - final `pending_exit_*` state clears after reconciliation

When opposite branch is expected:
- confirm tester preset has:
  - `InpEarlyExitOppositeEnabled=true`
  - `InpTestForceOppositeEarlyExit=true`
  - `InpPExitPass=1.0`
- then confirm summary shows:
  - `early ... opposite > 0`
  - `early ... pass = 0`

Rollback triggers:
- duplicate `EXIT`
- same-timestamp `EXIT -> ENTRY`
- opposite count appears while opposite flag is disabled
- control/pass regression changes trade semantics
