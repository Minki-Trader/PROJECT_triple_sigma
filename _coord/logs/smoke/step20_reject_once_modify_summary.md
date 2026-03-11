# STEP20 Reject-Once Modify Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_reject_once_modify.ini`

Validation class:
- synthetic trigger + synthetic modify reject

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpProtectiveAdjustEnabled=true`
- `InpBreakEvenEnabled=true`
- `InpTestForceBreakEvenOnce=true`
- `InpTestModifyRejectOnce=true`

Observed results:
- tester reported `final balance 476.29 USD`
- tester reported `Test passed`
- tester log shows the intended negative path:
  - blocked at `bars_held=1/2`
  - one `reject_once ... reason=BREAK_EVEN ... synthetic=true`
  - later `pending_modify_cleared ... reason=BREAK_EVEN`
- deinit summary confirms the negative path stayed bounded:
  - `entry=[attempt:928 exec:928 reject:0]`
  - `exit=[attempt:498 exec:495 reject:3]`
  - `modify=[eval:239 attempt:237 exec:231 reject:6 min_hold:2 be:239 other:0 cleared:231 last:BREAK_EVEN]`

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
- This run validates the synthetic modify reject branch only.
- The app-level negative path was exercised without introducing phantom `EXIT`
  rows, and later actual modify success still cleared pending modify state.

Retained artifact copy:
- `_coord/artifacts/step20_reject_once_modify/`
