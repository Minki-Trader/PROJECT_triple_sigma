# STEP21 Runtime Reload Rollback Artifact

Included files:
- `README.md`
- `manifest.json`
- `trade_log.csv`
- `exec_state.ini`
- `broker_audit.csv` when enabled
- `tester_log_tail.txt`
- `bar_log_YYYYMMDD.csv` files emitted by the run

Source run:
- preset: `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_runtime_reload_rollback.ini`
- summary: `_coord/logs/smoke/step21_runtime_reload_rollback_summary.md`
- validation class: `runtime-reload-rollback`
- trigger source: `runtime patch forced failure + rollback + broker audit`
- synthetic: `false`
