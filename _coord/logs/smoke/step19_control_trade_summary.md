# STEP19 Control Trade Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step19/step19_tester_control_trade.ini`

Validation class:
- actual-path control regression

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpEarlyExitEnabled=false`
- `InpEarlyExitLive=false`
- `InpEarlyExitOppositeEnabled=false`
- `InpTestEarlyExitRejectOnce=false`
- `InpTestForceOppositeEarlyExit=false`

Observed results:
- tester reported `final balance 422.20 USD`
- tester reported `Test passed`
- deinit summary confirmed the control path stayed inert with respect to early exit:
  - `final=[PASS:15267 LONG:50066 SHORT:0]`
  - `entry=[attempt:922 exec:922 reject:0]`
  - `exit=[attempt:525 exec:522 reject:3]`
  - `retcode=[done:1444 partial:0 zero:0 other:3]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0 opposite:0 other:0 last:-]`
  - `force_exit=522`
- retained artifact package contains:
  - `trade_log.csv`
  - `exec_state.ini`
  - `tester_log_tail.txt`
  - `bar_log_YYYYMMDD.csv` x `240`
  - `manifest.json`

Artifact checks:
- `trade_log.csv` rows: `1843`
- event counts: `ENTRY=922`, `EXIT=921`
- exit reasons:
  - `FORCE_EXIT=522`
  - `SL=322`
  - `TP=77`
- `EARLY_EXIT=0`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`

Interpretation note:
- This run is the long-window regression anchor for STEP19.
- It shows that adding opposite-close-only scaffolding does not change baseline
  trade semantics when all early-exit modes are disabled.

Retained artifact copy:
- `_coord/artifacts/step19_control_trade/`

Representative evidence:
- `final balance 422.20 USD`
- `[TS][MON][deinit] ... entry=[attempt:922 exec:922 reject:0] exit=[attempt:525 exec:522 reject:3] ... early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0 opposite:0 other:0 last:-] ...`
- `US100,M5: 73541142 ticks, 65332 bars generated. ... Test passed ...`
