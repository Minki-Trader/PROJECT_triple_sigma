# STEP21 Recovery Pending Modify Tx Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_recovery_pending_modify_tx.ini`

Validation class:
- `recovery-pending-modify-tx`

Trigger source:
- `synthetic BE trigger + recovery reload + tx authority`
- synthetic: `true`

Trade log stats:
- rows: `2084`
- event counts: `{"ENTRY": 928, "EXIT": 927, "MODIFY": 229}`
- exit reasons: `{"FORCE_EXIT": 495, "SL": 357, "TP": 75}`
- modify reasons: `{"BREAK_EVEN": 229}`
- duplicate non-modify `(trade_id,event_type)` groups: `0`
- duplicate `EXIT` groups: `0`
- same-timestamp `EXIT -> ENTRY`: `0`
- tx authority tags: `{"TX_DEAL": 1855, "TX_OR_SYNC": 229}`

Runtime tail state:
- active model pack: `triple_sigma_pack_long_step16`
- runtime status: `INIT`
- runtime counters: `attempt=0 success=0 rollback=0`
