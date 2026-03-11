# STEP21 Close Vs Modify Precedence Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_close_vs_modify_precedence.ini`

Validation class:
- `close-vs-modify-precedence`

Trigger source:
- `synthetic close trigger + synthetic BE trigger + precedence gate`
- synthetic: `true`

Trade log stats:
- rows: `13009`
- event counts: `{"ENTRY": 6505, "EXIT": 6504}`
- exit reasons: `{"EARLY_EXIT": 6460, "SL": 38, "TP": 6}`
- modify reasons: `{}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 13009}`

Runtime tail state:
- active model pack: `triple_sigma_pack_long_step16`
- runtime status: `INIT`
- runtime counters: `attempt=0 success=0 rollback=0`
