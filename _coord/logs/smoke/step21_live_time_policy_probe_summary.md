# STEP21 Live Time Policy Probe Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_live_time_policy_probe.ini`

Validation class:
- `live-time-policy-probe`

Trigger source:
- `actual time-policy modify path`
- synthetic: `false`

Trade log stats:
- rows: `3828`
- event counts: `{"ENTRY": 1680, "EXIT": 1679, "MODIFY": 469}`
- exit reasons: `{"FORCE_EXIT": 252, "SL": 1262, "TP": 165}`
- modify reasons: `{"TIME_POLICY": 469}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 3359, "TX_OR_SYNC": 469}`

Runtime tail state:
- active model pack: `triple_sigma_pack_long_step16`
- runtime status: `INIT`
- runtime counters: `attempt=0 success=0 rollback=0`
