# STEP19 Live Opposite Probe Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step19/step19_tester_live_opposite_probe.ini`

Validation class:
- synthetic trigger source + actual close path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=true`
- `InpPExitPass=1.00`
- `InpTestForceOppositeEarlyExit=true`
- `InpMinHoldBarsBeforeExit=3`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- tester log emitted opposite-detail early-exit lines:
  - blocked at `bars_held=1/2`
  - trigger from `bars_held=3`
  - `reason=OPPOSITE_DIR`
- live deinit summary shows the opposite branch was exercised while core trade
  semantics stayed aligned:
  - `final=[PASS:15267 LONG:50066 SHORT:0]`
  - `entry=[attempt:6506 exec:6505 reject:1]`
  - `exit=[attempt:6478 exec:6460 reject:18]`
  - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR]`
  - `diag=[entry:10009/... exit:10009/... tx:DEAL/10009/... other:10018/market_closed_other_synth:false]`

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
- `trade_log.csv` SHA-256 is identical to the pass-only live regression:
  - `5373aaf47894f4e3f0790920cb9c1403ab076317d8332ba04e43126d8481b4ae`
- `exec_state.ini` SHA-256 is identical to the pass-only live regression:
  - `0711e32968a44cb1f850610c35e1c45843a88dcf8fcaba5a7179e00a7f16c95f`
- retained bar logs: `240` day-rotated files

Interpretation note:
- This run proves the new opposite-detail branch can be opened without widening
  the core runtime contract.
- Only the monitor/tester-log subtype changes from `P_EXIT_PASS` to
  `OPPOSITE_DIR`; the retained `trade_log.csv` and `exec_state.ini` stay
  byte-identical to the long pass-only live regression.

Retained artifact copy:
- `_coord/artifacts/step19_live_opposite_probe/`

Representative evidence:
- `[TS][EARLY_EXIT] trigger ... reason=OPPOSITE_DIR bars_held=3 ...`
- `[TS][MON][deinit] ... early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR] ...`
- `final balance 278.29 USD`
- `US100,M5: 73541142 ticks, 65332 bars generated. ... Test passed ...`
