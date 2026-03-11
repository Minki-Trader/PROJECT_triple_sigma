# STEP19 Live Pass Regression Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step19/step19_tester_live_pass_regression.ini`

Validation class:
- actual-path live pass regression

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=false`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- live early-exit path stayed pass-only:
  - `final=[PASS:15267 LONG:50066 SHORT:0]`
  - `entry=[attempt:6506 exec:6505 reject:1]`
  - `exit=[attempt:6478 exec:6460 reject:18]`
  - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:19434 opposite:0 other:0 last:P_EXIT_PASS]`
  - `diag=[entry:10009/... exit:10009/... tx:DEAL/10009/... other:10018/market_closed_other_synth:false]`
- tester log emitted blocked/trigger early-exit lines with:
  - `reason=P_EXIT_PASS`
  - blocks at `bars_held=1/2`
  - triggers at `bars_held=3`

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
- `trade_log.csv` SHA-256:
  - `5373aaf47894f4e3f0790920cb9c1403ab076317d8332ba04e43126d8481b4ae`
- `exec_state.ini` SHA-256:
  - `0711e32968a44cb1f850610c35e1c45843a88dcf8fcaba5a7179e00a7f16c95f`
- retained bar logs: `240` day-rotated files

Interpretation note:
- This is the long-window STEP19 regression anchor for the existing
  `LIVE_PASS_ONLY` behavior.
- It establishes the baseline that later opposite-enabled runs must preserve at
  the core `trade_log.csv` / `exec_state.ini` level when only subtype
  observability changes.

Retained artifact copy:
- `_coord/artifacts/step19_live_pass_regression/`

Representative evidence:
- `final balance 278.29 USD`
- `[TS][EARLY_EXIT] trigger ... reason=P_EXIT_PASS bars_held=3 ...`
- `[TS][MON][deinit] ... early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:19434 opposite:0 other:0 last:P_EXIT_PASS] ...`
- `US100,M5: 73541142 ticks, 65332 bars generated. ... Test passed ...`
