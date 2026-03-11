# STEP19 Reject-Once Opposite Probe Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step19/step19_tester_reject_once_opposite_probe.ini`

Validation class:
- synthetic trigger source + synthetic negative path + actual close path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=true`
- `InpPExitPass=1.00`
- `InpTestForceOppositeEarlyExit=true`
- `InpTestEarlyExitRejectOnce=true`

Observed results:
- tester reported `final balance 277.70 USD`
- tester reported `Test passed`
- tester log emitted one deterministic synthetic reject before normal close flow resumed:
  - `[TS][TEST][EARLY_EXIT] reject_once ... detail=OPPOSITE_DIR ... synthetic=true`
- deinit summary shows one extra opposite-path reject over the non-reject probe:
  - `entry=[attempt:6501 exec:6500 reject:1]`
  - `exit=[attempt:6474 exec:6455 reject:19]`
  - `retcode=[done:12955 partial:0 zero:0 other:20]`
  - `diag=[... other:10018/market_closed_other_synth:false]`
  - `early=[eval:19420 attempt:6474 exec:6455 reject:19 min_hold:12946 pass:0 opposite:19420 other:0 last:OPPOSITE_DIR]`

Artifact checks:
- `trade_log.csv` rows: `12999`
- event counts: `ENTRY=6500`, `EXIT=6499`
- exit reasons:
  - `EARLY_EXIT=6455`
  - `SL=38`
  - `TP=6`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- `trade_log.csv` SHA-256:
  - `a78ea6e3ed0fca34caf1f7d2f7a493bd80a7a3d7b7d4e3dcd3f16283db43300e`
- `exec_state.ini` SHA-256:
  - `222fbdcda1904f2ba092f247c4528e55a45fce14d0f63c5c130d409ee23a44d4`
- retained bar logs: `240` day-rotated files

Interpretation note:
- This run proves the negative path remains bounded:
  - one deterministic synthetic reject is labeled as synthetic,
  - no phantom `EXIT` appears,
  - no same-timestamp `EXIT -> ENTRY` appears,
  - normal opposite-detail early exits continue afterward on the actual tester
    close path.

Retained artifact copy:
- `_coord/artifacts/step19_reject_once_opposite_probe/`

Representative evidence:
- `[TS][TEST][EARLY_EXIT] reject_once trade_id=TS_00001 detail=OPPOSITE_DIR ... synthetic=true`
- `[TS][MON][deinit] ... early=[eval:19420 attempt:6474 exec:6455 reject:19 min_hold:12946 pass:0 opposite:19420 other:0 last:OPPOSITE_DIR] ...`
- `final balance 277.70 USD`
- `US100,M5: 73541142 ticks, 65332 bars generated. ... Test passed ...`
