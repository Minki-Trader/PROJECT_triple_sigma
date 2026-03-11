# STEP16 Recovery Pending-Exit Smoke Artifact

This folder retains the concrete files copied from the STEP16 pending-exit
recovery smoke run on 2026-03-08.

Included files:
- `trade_log.csv`: live trade-log output from the tester agent
- `exec_state.ini`: persisted execution state after the run
- `tester_log_tail.txt`: excerpt showing recovery probe begin/load/complete and
  final summary lines

Source run:
- preset: `_coord/tester/step16/step16_tester_recovery_pending_exit.ini`
- summary note: `_coord/logs/smoke/step16_recovery_pending_exit_summary.md`

Behavior note:
- this run enables a tester-only execution-state recovery probe after
  `pending_exit_*` has been persisted
- live trade semantics remain unchanged
