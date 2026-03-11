# STEP16 Shadow Smoke Artifact

This folder retains the concrete files copied from the STEP16 phase-2
shadow-only smoke run on 2026-03-08.

Included files:
- `trade_log.csv`: live trade-log output from the tester agent
- `exec_state.ini`: persisted execution state after the run
- `tester_log_tail.txt`: tester-agent excerpt showing shadow-only signals and
  final deinit summary

Source run:
- preset: `_coord/tester/step16/step16_tester_shadow_smoke.ini`
- summary note: `_coord/logs/smoke/step16_shadow_smoke_summary.md`

Behavior note:
- this run enables `InpEarlyExitEnabled=true` only for shadow evaluation
- no live `EARLY_EXIT` or `MODIFY` row is expected in `trade_log.csv`
