# STEP21 Runtime Reload Success Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_runtime_reload_success.ini`

Validation class:
- `runtime-reload-success`

Trigger source:
- `runtime patch success path + broker audit`
- synthetic: `false`

Trade log stats:
- rows: `323`
- event counts: `{"ENTRY": 162, "EXIT": 161}`
- exit reasons: `{"FORCE_EXIT": 16, "SL": 103, "TP": 42}`
- modify reasons: `{}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 323}`

Runtime tail state:
- active model pack: `triple_sigma_pack_step15_q1`
- runtime status: `RELOADED`
- runtime counters: `attempt=1 success=1 rollback=0`

Broker audit stats:
- rows: `327`
- tags: `{"deinit": 1, "entry_logged": 162, "exit_logged": 161, "init": 1, "runtime_reload_attempt": 1, "runtime_reload_success": 1}`
