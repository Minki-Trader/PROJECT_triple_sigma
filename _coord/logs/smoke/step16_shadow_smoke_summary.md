# STEP16 Shadow Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step16/step16_tester_shadow_smoke.ini`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpLogHeartbeat=false`
- `InpDebugAlignment=false`
- `InpEarlyExitEnabled=true`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`

Purpose:
- validate the post-decision seam
- validate shadow-only Early Exit observability
- confirm live trade semantics stay unchanged

Observed results:
- tester reported `final balance 504.35 USD`
- tester reported `Test passed`
- live deinit summary matched the trade smoke on the live path:
  - `final=[PASS:289 LONG:798 SHORT:0]`
  - `entry=[attempt:14 exec:14 reject:0]`
  - `exit=[attempt:7 exec:7 reject:0]`
  - `force_exit=7`
- shadow-only counters were populated:
  - `shadow=[eval:733 trig:706 min_hold:27 pass:733 opposite:0 other:0]`
- tester log emitted both blocked and trigger shadow lines:
  - blocked at `bars_held=1/2` before `min_hold=3`
  - trigger from `bars_held=3` onward while position remained open
- `trade_log.csv` remained unchanged in schema and behavior:
  - `EARLY_EXIT=0`
  - `MODIFY=0`
  - ENTRY rows `14`, EXIT rows `13`

Interpretation note:
- this smoke confirms the intended STEP16 phase-2 contract:
  - shadow evaluation runs after current-bar decision assembly
  - shadow counters/log lines are emitted
  - no live `EARLY_EXIT` event is executed
  - trade lifecycle and PnL stay aligned with the non-shadow trade smoke

Retained artifact copy:
- `_coord/artifacts/step16_shadow_smoke/trade_log.csv`
- `_coord/artifacts/step16_shadow_smoke/exec_state.ini`
- `_coord/artifacts/step16_shadow_smoke/tester_log_tail.txt`

Representative evidence:
- `[TS][SHADOW_EXIT] blocked trade_id=TS_00001 reason=P_EXIT_PASS bars_held=1 min_hold=3 ...`
- `[TS][SHADOW_EXIT] trigger trade_id=TS_00001 reason=P_EXIT_PASS bars_held=3 ...`
- `[TS][MON][deinit] bars=1087 ... final=[PASS:289 LONG:798 SHORT:0] ... shadow=[eval:733 trig:706 min_hold:27 pass:733 opposite:0 other:0] ...`
- `final balance 504.35 USD`
- `Test passed in 0:00:02.061`
