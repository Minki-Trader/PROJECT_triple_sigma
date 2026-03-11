# STEP16 Trade Smoke Artifact

This folder retains the concrete files copied from the latest STEP16
trade-producing smoke run on 2026-03-08.

Included files:
- `trade_log.csv`: exercised `trade_log` lifecycle output from the tester agent
- `exec_state.ini`: persisted execution state after the run
- `tester_log_tail.txt`: tail excerpt from the tester-agent log for the same run

Source run:
- preset: `_coord/tester/step16/step16_tester_trade_smoke.ini`
- summary note: `_coord/logs/smoke/step16_trade_smoke_summary.md`

Smoke-pack note:
- `triple_sigma_pack_long_step16` is a deterministic constant-LONG smoke pack
  used only to validate execution/logging behavior.
