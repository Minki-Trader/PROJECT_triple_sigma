# STEP16 Recovery Open-Position Smoke Artifact

This folder retains the concrete files copied from the STEP16 open-position
recovery smoke run on 2026-03-08.

Included files:
- `trade_log.csv`: live trade-log output from the tester agent
- `exec_state.ini`: persisted execution state after the run
- `tester_log_tail.txt`: excerpt showing recovery probe begin/load/complete and
  final summary lines

Source run:
- preset: `_coord/tester/step16/step16_tester_recovery_open.ini`
- summary note: `_coord/logs/smoke/step16_recovery_open_summary.md`

Behavior note:
- this run enables a tester-only execution-state recovery probe at an
  open-position checkpoint
- live trade semantics remain unchanged
