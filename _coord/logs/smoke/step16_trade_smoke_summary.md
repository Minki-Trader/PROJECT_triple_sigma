# STEP16 Trade-Producing Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step16/step16_tester_trade_smoke.ini`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpLogHeartbeat=false`
- `InpDebugAlignment=false`
- `InpEarlyExitEnabled=false`

Smoke-pack note:
- `triple_sigma_pack_long_step16` is a deterministic constant-LONG smoke pack
  used to validate execution/logging behavior.
- It is not a production/runtime selection pack.

Observed results:
- tester loaded `InpModelPackDir=triple_sigma_pack_long_step16`
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- deinit summary confirmed live decision path activity:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `force_exit=7`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0]`
- no `[TS][SHADOW_EXIT]` lines were emitted in this run
- `trade_log.csv` was created and appended during the run
- `exec_state.ini` persisted `pending_exit_deal` and `pending_exit_price_hint`

Trade-log checks:
- header count: `1`
- ENTRY rows: `14`
- EXIT rows: `13`
- open trade id remaining at tester end: `TS_00014`
- exit reason counts:
  - `FORCE_EXIT=7`
  - `SL=4`
  - `TP=2`
- `EARLY_EXIT=0`
- `MODIFY=0`

Interpretation note:
- `TS_00014` remained open in `trade_log.csv` because the tester auto-closed the
  last position at end-of-test after EA deinitialization.
- This run validates that STEP16 phase-2 keeps live trade semantics unchanged
  when shadow-only Early Exit is disabled.

Retained artifact copy:
- `_coord/artifacts/step16_trade_smoke/trade_log.csv`
- `_coord/artifacts/step16_trade_smoke/exec_state.ini`
- `_coord/artifacts/step16_trade_smoke/tester_log_tail.txt`

Representative evidence:
- `[TS][MON][deinit] bars=1087 ... final=[PASS:289 LONG:798 SHORT:0] ... entry=[attempt:14 exec:14 reject:0] exit=[attempt:7 exec:7 reject:0] ... shadow=[eval:0 trig:0 min_hold:0 pass:0 opposite:0 other:0] ...`
- `final balance 504.35 USD`
- `Test passed in 0:00:03.125`
- `position closed due end of test at 25597.04 [#28 buy 0.07 US100 25592.14 ...]`
