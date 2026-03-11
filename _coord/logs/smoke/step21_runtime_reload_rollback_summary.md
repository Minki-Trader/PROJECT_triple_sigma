# STEP21 Runtime Reload Rollback Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_runtime_reload_rollback.ini`

Validation class:
- `runtime-reload-rollback`

Trigger source:
- `runtime patch forced failure + rollback + broker audit`
- synthetic: `false`

Trade log stats:
- rows: `186`
- event counts: `{"ENTRY": 93, "EXIT": 93}`
- exit reasons: `{"FORCE_EXIT": 50, "SL": 34, "TP": 9}`
- modify reasons: `{}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 186}`

Runtime tail state:
- active model pack: `triple_sigma_pack_long_step16`
- runtime status: `ROLLED_BACK`
- runtime counters: `attempt=1 success=0 rollback=1`

Broker audit stats:
- rows: `190`
- tags: `{"deinit": 1, "entry_logged": 93, "exit_logged": 93, "init": 1, "runtime_reload_attempt": 1, "runtime_reload_rollback": 1}`
