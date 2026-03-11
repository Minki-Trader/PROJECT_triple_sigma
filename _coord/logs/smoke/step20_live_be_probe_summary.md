# STEP20 Live BE Probe Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_live_be_probe.ini`

Validation class:
- actual modify path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpEarlyExitEnabled=false`
- `InpProtectiveAdjustEnabled=true`
- `InpBreakEvenEnabled=true`
- `InpBreakEvenRRTrigger=1.00`
- `InpBreakEvenMinHoldBars=3`
- `InpBreakEvenOffsetPoints=0`
- `InpTestForceBreakEvenOnce=true`
- `InpTestModifyRejectOnce=false`

Observed results:
- tester reported `final balance 467.50 USD`
- tester reported `Test passed`
- deinit summary confirms bounded BE-only modify exercised the actual tester
  modify path:
  - `entry=[attempt:1179 exec:1179 reject:0]`
  - `exit=[attempt:375 exec:373 reject:2]`
  - `modify=[eval:836 attempt:761 exec:750 reject:11 min_hold:75 be:836 other:0 cleared:750 last:BREAK_EVEN]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0 opposite:0 other:0 last:-]`

Artifact checks:
- `trade_log.csv` rows: `2357`
- event counts: `ENTRY=1179`, `EXIT=1178`
- exit reasons:
  - `SL=742`
  - `TP=63`
  - `FORCE_EXIT=373`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`

Interpretation:
- This is the first STEP20 actual modify-path check.
- BE-only protective adjust executed without widening the core CSV contract.
- Modify evidence is visible only through monitor/tester diagnostics, pending
  modify persistence, and the later `EXIT` rows.

Retained artifact copy:
- `_coord/artifacts/step20_live_be_probe/`
