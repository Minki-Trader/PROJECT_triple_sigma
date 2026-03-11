# STEP18 Reject-Once Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step18/step18_tester_reject_once.ini`

Purpose:
- keep the retained negative-path probe
- distinguish the synthetic reject branch from the ordinary actual-path
  request/result runs

Tester input highlights:
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpTestEarlyExitRejectOnce=true`

Observed results:
- tester reported `final balance 502.99 USD`
- tester reported `Test passed`
- tester-only injected reject was observed:
  - `[TS][TEST][EARLY_EXIT] reject_once trade_id=TS_00001 bars_held=3 p_pass=0.100000`
- deinit summary confirmed one synthetic rejected close attempt followed by
  later success:
  - `entry=[attempt:103 exec:103 reject:0]`
  - `exit=[attempt:102 exec:101 reject:1]`
  - `retcode=[done:204 partial:0 zero:0 other:1]`
  - `tx=[request:204 deal_add:205 position:0 other:410]`
  - `diag=[entry:10009/done_at_25592.14_exit:10009/done_at_25564.64_exit_synth:false_tx:DEAL/10009/-_other:10006/synthetic_reject_once_other_synth:true]`
  - `early=[eval:306 attempt:102 exec:101 reject:1 min_hold:204 pass:306]`

Trade-log checks:
- `ENTRY=103`
- `EXIT=102`
- `EARLY_EXIT=101`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY` transitions: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to `_coord/artifacts/step17_reject_once_smoke/trade_log.csv`
- `exec_state.ini` is byte-identical to `_coord/artifacts/step17_reject_once_smoke/exec_state.ini`

Interpretation:
- STEP18 does not try to pretend this is an actual server-side reject.
- The retained reject-once path remains synthetic by design and is now labeled
  as synthetic in the diagnostic summary.
- The actual-path coverage for STEP18 comes from the control/live/recovery runs.

Retained artifact copy:
- `_coord/artifacts/step18_reject_once/trade_log.csv`
- `_coord/artifacts/step18_reject_once/exec_state.ini`
- `_coord/artifacts/step18_reject_once/tester_log_tail.txt`
