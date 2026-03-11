# STEP20 Close-Vs-Modify Precedence Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_close_vs_modify_precedence.ini`

Validation class:
- synthetic close trigger + synthetic BE trigger + actual close path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=true`
- `InpPExitPass=1.00`
- `InpTestForceOppositeEarlyExit=true`
- `InpProtectiveAdjustEnabled=true`
- `InpBreakEvenEnabled=true`
- `InpTestForceBreakEvenOnce=true`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- same-run tester agent log shows the intended precedence:
  - `BREAK_EVEN` blocked at `bars_held=1/2`
  - `EARLY_EXIT` triggered at `bars_held=3`
  - opposite early-exit branch remained active:
    - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR]`
  - modify branch evaluated but never attempted:
    - `modify=[eval:12956 attempt:0 exec:0 reject:0 min_hold:12956 be:12956 other:0 cleared:0 last:BREAK_EVEN]`

Artifact checks:
- `trade_log.csv` rows: `13009`
- event counts: `ENTRY=6505`, `EXIT=6504`
- exit reasons:
  - `EARLY_EXIT=6460`
  - `SL=38`
  - `TP=6`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- packaged `tester_log_tail.txt` was rebuilt from the same-run tester agent log
  because the originally retained tail was empty

Interpretation:
- This run proves close-before-modify precedence.
- The BE branch remained visible at the evaluation layer, but no modify attempt
  was allowed once the close-only Early Exit branch won on the same bar.

Retained artifact copy:
- `_coord/artifacts/step20_close_vs_modify_precedence/`
