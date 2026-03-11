# STEP21 Live Trailing Probe Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_live_trailing_probe.ini`

Validation class:
- `live-trailing-probe`

Trigger source:
- `actual trailing modify path`
- synthetic: `false`

Trade log stats:
- rows: `5001`
- event counts: `{"ENTRY": 1805, "EXIT": 1804, "MODIFY": 1392}`
- exit reasons: `{"FORCE_EXIT": 227, "SL": 1564, "TP": 13}`
- modify reasons: `{"TRAILING": 1392}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 3609, "TX_OR_SYNC": 1392}`

Runtime tail state:
- active model pack: `triple_sigma_pack_long_step16`
- runtime status: `INIT`
- runtime counters: `attempt=0 success=0 rollback=0`
