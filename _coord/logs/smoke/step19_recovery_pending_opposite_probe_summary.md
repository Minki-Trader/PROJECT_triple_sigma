# STEP19 Recovery Pending Opposite Probe Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step19/step19_tester_recovery_pending_opposite_probe.ini`

Validation class:
- synthetic trigger source + synthetic recovery probe + actual close path

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpModelPackDir=triple_sigma_pack_long_step16`
- `InpEarlyExitEnabled=true`
- `InpEarlyExitLive=true`
- `InpEarlyExitOppositeEnabled=true`
- `InpPExitPass=1.00`
- `InpTestForceOppositeEarlyExit=true`
- `InpTestRecoveryReloadEnabled=true`
- `InpTestRecoveryReloadMode=2`

Observed results:
- tester reported `final balance 278.29 USD`
- tester reported `Test passed`
- recovery probe evidence was emitted at the pending-exit point:
  - `probe_begin ... pending_exit_reason=EARLY_EXIT detail=EARLY_EXIT:OPPOSITE_DIR`
  - `probe_complete ... has_position=false ... pending_exit_reason= ... exited_this_bar=true`
- deinit summary stayed aligned with the opposite live probe:
  - `entry=[attempt:6506 exec:6505 reject:1]`
  - `exit=[attempt:6478 exec:6460 reject:18]`
  - `early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR]`

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
- `trade_log.csv` SHA-256 matches the live pass and live opposite probes:
  - `5373aaf47894f4e3f0790920cb9c1403ab076317d8332ba04e43126d8481b4ae`
- `exec_state.ini` SHA-256 matches the live pass and live opposite probes:
  - `0711e32968a44cb1f850610c35e1c45843a88dcf8fcaba5a7179e00a7f16c95f`
- retained bar logs: `240` day-rotated files

Interpretation note:
- Recovery reload probing does not perturb the final retained trade/state
  artifacts for the long opposite-detail path.
- The opposite subtype remains non-core: it is visible in tester logs and
  monitor summaries, while the persisted runtime contract stays generic
  `EARLY_EXIT`.

Retained artifact copy:
- `_coord/artifacts/step19_recovery_pending_opposite_probe/`

Representative evidence:
- `[TS][TEST][RECOVERY] probe_begin mode=PENDING_EXIT ... pending_exit_reason=EARLY_EXIT detail=EARLY_EXIT:OPPOSITE_DIR`
- `[TS][TEST][RECOVERY] probe_complete mode=PENDING_EXIT has_position=false ... pending_exit_reason= exited_this_bar=true`
- `[TS][MON][deinit] ... early=[eval:19434 attempt:6478 exec:6460 reject:18 min_hold:12956 pass:0 opposite:19434 other:0 last:OPPOSITE_DIR] ...`
- `final balance 278.29 USD`
