# STEP17 Reject-Once Smoke Summary

Run date:
- 2026-03-08

Preset:
- `_coord/tester/step17/step17_tester_reject_once.ini`

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpPExitPass=0.09`
- `InpMinHoldBarsBeforeExit=3`
- `InpTestEarlyExitRejectOnce=true`

Observed results:
- tester reported `final balance 502.99 USD`
- tester reported `Test passed`
- tester-only injected reject was observed:
  - `[TS][TEST][EARLY_EXIT] reject_once trade_id=TS_00001 bars_held=3 p_pass=0.100000`
- deinit summary confirmed one rejected close attempt followed by later success:
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:102 exec:101 reject:1]`
  - `retcode=[done:204 partial:0 zero:0 other:1]`
  - `early=[eval:306 attempt:102 exec:101 reject:1 min_hold:204 pass:306]`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`

Interpretation:
- The first eligible live Early Exit was rejected deterministically in tester
  mode.
- That rejection did not create a phantom `EXIT` row and did not prevent a
  later eligible `EARLY_EXIT` from completing normally.

Retained artifact copy:
- `_coord/artifacts/step17_reject_once_smoke/trade_log.csv`
- `_coord/artifacts/step17_reject_once_smoke/exec_state.ini`
- `_coord/artifacts/step17_reject_once_smoke/tester_log_tail.txt`
