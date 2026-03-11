# STEP21 Live Opposite Regression Artifact Summary

Run date:
- 2026-03-09

Preset:
- `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_live_opposite_regression.ini`

Validation class:
- `live-opposite-regression`

Trigger source:
- `feature-off opposite close regression gate`
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

Baseline compare:
- baseline: `_coord/artifacts/step20_live_opposite_regression`
- core-row match: `true`
- row count match: `true`
- common columns: `trade_id, event_type, direction, lot, entry_price, exit_price, sl_price, tp_price, pnl, k_sl_req, k_tp_req, k_sl_eff, k_tp_eff, hold_bars, bars_held, exit_reason, regime_id_at_entry, spread_atr_at_entry, flip_used, model_pack_version, clf_version, prm_version, cost_model_version`
