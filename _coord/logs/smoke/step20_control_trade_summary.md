# STEP20 Control Trade Summary

Run date:
- 2026-03-09

Preset:
- `_coord/tester/step20/step20_tester_control_trade.ini`

Validation class:
- control

Window:
- `2025-04-02` -> `2026-03-06`

Tester input highlights:
- `InpEarlyExitEnabled=false`
- `InpEarlyExitLive=false`
- `InpProtectiveAdjustEnabled=false`
- `InpBreakEvenEnabled=false`

Observed results:
- tester reported `final balance 422.20 USD`
- tester reported `Test passed`
- deinit summary confirms trade semantics stayed inert relative to STEP19:
  - `entry=[attempt:922 exec:922 reject:0]`
  - `exit=[attempt:525 exec:522 reject:3]`
  - `early=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 pass:0 opposite:0 other:0 last:-]`
  - `modify=[eval:0 attempt:0 exec:0 reject:0 min_hold:0 be:0 other:0 cleared:0 last:-]`
  - `force_exit=522`

Artifact checks:
- `trade_log.csv` rows: `1843`
- event counts: `ENTRY=922`, `EXIT=921`
- exit reasons:
  - `SL=322`
  - `TP=77`
  - `FORCE_EXIT=522`
- `EARLY_EXIT=0`
- `MODIFY=0`
- duplicate `(trade_id,event_type)` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`

Baseline diff:
- `trade_log.csv` is byte-identical to `_coord/artifacts/step19_control_trade/trade_log.csv`
- `exec_state.ini` is intentionally extended for STEP20 pending-modify fields:
  - STEP20: `b2bfb6739111179b20a495cb78f6e72a096fa178c3e6f788c660746f489bfb5c`
  - STEP19: `baa8dce756c3d6852e3dff406bcc7ddd088f12d258d4a46df1a4ee4458e551a3`
- no active `pending_modify_*` state remained at tester end

Interpretation:
- This is the STEP20 feature-off regression gate.
- It confirms the additive modify persistence surface did not widen live trade
  semantics when both early-exit and protective-adjust features were disabled.

Retained artifact copy:
- `_coord/artifacts/step20_control_trade/`
