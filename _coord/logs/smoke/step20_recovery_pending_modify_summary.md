# STEP20 Recovery Pending Modify Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_recovery_pending_modify.ini`

Validation class:
- synthetic trigger + recovery probe + actual modify path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpProtectiveAdjustEnabled=true`
- `InpBreakEvenEnabled=true`
- `InpTestForceBreakEvenOnce=true`
- `InpTestRecoveryReloadEnabled=true`
- `InpTestRecoveryReloadMode=3`

Observed results:
- tester reported `final balance 476.32 USD`
- tester reported `Test passed`
- tester log shows recovery at pending modify:
  - `probe_begin mode=PENDING_MODIFY ... pending_modify_reason=BREAK_EVEN detail=BREAK_EVEN`
  - `pending_modify_cleared ... reason=BREAK_EVEN`
  - `probe_complete mode=PENDING_MODIFY ... pending_modify_reason=`
- deinit summary confirms recovery closed cleanly:
  - `entry=[attempt:928 exec:928 reject:0]`
  - `exit=[attempt:498 exec:495 reject:3]`
  - `modify=[eval:237 attempt:235 exec:231 reject:4 min_hold:2 be:237 other:0 cleared:231 last:BREAK_EVEN]`

Artifact checks:
- `trade_log.csv` rows: `1855`
- event counts: `ENTRY=928`, `EXIT=927`
- exit reasons:
  - `SL=357`
  - `TP=75`
  - `FORCE_EXIT=495`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`

Interpretation:
- The persisted `pending_modify_*` contract survived a tester reload probe and
  cleared only after live stop reconciliation matched the expected snapshot.
- No duplicate `EXIT` or schema widening was introduced.

Retained artifact copy:
- `_coord/artifacts/step20_recovery_pending_modify/`
