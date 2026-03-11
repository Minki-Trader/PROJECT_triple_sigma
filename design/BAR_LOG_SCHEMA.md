# BAR_LOG_SCHEMA

Status:
- This document describes the actual current runtime log schema emitted by
  `src/include/TS_Logger.mqh`.
- It reflects the STEP21 tx-authoritative protective runtime.
- Current log schema version is `2.0`.

Scope:
- `bar_log_YYYYMMDD.csv`
- `trade_log.csv`
- `broker_audit.csv`

## bar_log_YYYYMMDD.csv

Column groups:

Core bar snapshot:
- `time`
- `symbol`
- `timeframe`
- `price_basis`
- `open`
- `high`
- `low`
- `close`
- `spread_points`
- `atr14`
- `adx14`
- `atr_pct`
- `regime_id`
- `cand_long`
- `cand_short`
- `entry_allowed`

Feature window snapshot:
- `feature_0` .. `feature_21`

Stage1 output:
- `onnx_p_long`
- `onnx_p_short`
- `onnx_p_pass`
- `stage1_argmax`

Stage2 output:
- `prm_raw_0` .. `prm_raw_5`
- `final_dir`
- `flip_used`
- `k_sl_req`
- `k_tp_req`
- `k_sl_eff`
- `k_tp_eff`
- `hold_bars`

Gate and execution state:
- `gate_pass`
- `gate_reject_reason`
- `dyn_spread_atr_max`
- `dyn_dev_points`
- `risk_pct`
- `dist_atr`
- `dist_atr_max_t`
- `dist_atr_max_mode`
- `has_position`
- `bars_held`

Version snapshot:
- `ea_version`
- `schema_version`
- `candidate_policy_version`
- `regime_policy_version`
- `model_pack_version`
- `clf_version`
- `prm_version`
- `cost_model_version`

Step21 runtime / audit tail:
- `pending_exit_reason`
- `pending_modify_reason`
- `last_modify_reason`
- `modify_count`
- `be_applied`
- `entry_log_emitted`
- `tx_authority_enabled`
- `broker_audit_enabled`
- `active_model_pack_dir`
- `pack_dir_at_entry`
- `runtime_reload_attempts`
- `runtime_reload_successes`
- `runtime_reload_rollbacks`
- `runtime_reload_status`
- `log_schema_version`

Current-state notes:
- `pending_exit_reason` and `pending_modify_reason` are the persisted intent
  fields from `TS_Execution.mqh`.
- `last_modify_reason` is the latest executed protective modify family.
- `tx_authority_enabled=1` means entry / exit emission is being finalized from
  transaction observation, with sync fallback still retained for recovery.
- `runtime_reload_status` currently appears as values such as `INIT`,
  `RELOADED`, and `ROLLED_BACK`.

## trade_log.csv

Current emitted columns:
- `trade_id`
- `timestamp`
- `symbol`
- `event_type`
- `direction`
- `lot`
- `entry_price`
- `exit_price`
- `sl_price`
- `tp_price`
- `pnl`
- `k_sl_req`
- `k_tp_req`
- `k_sl_eff`
- `k_tp_eff`
- `hold_bars`
- `bars_held`
- `exit_reason`
- `regime_id_at_entry`
- `spread_atr_at_entry`
- `flip_used`
- `model_pack_version`
- `clf_version`
- `prm_version`
- `cost_model_version`
- `event_detail`
- `deal_ticket`
- `position_id`
- `modify_reason`
- `modify_count`
- `tx_authority`
- `pack_dir_at_entry`
- `active_model_pack_dir`
- `runtime_reload_status`
- `ea_version`
- `log_schema_version`

Event semantics:
- `event_type` is currently emitted as:
  - `ENTRY`
  - `EXIT`
  - `MODIFY`
- `modify_reason` currently appears as:
  - `BREAK_EVEN`
  - `TRAILING`
  - `TP_RESHAPE`
  - `TIME_POLICY`
- `tx_authority` identifies the log-emission path and currently appears as
  values such as:
  - `TX_DEAL`
  - `TX_POSITION`
  - `SYNC_POSITION`
  - `TX_OR_SYNC`

Current-state notes:
- Feature-off STEP21 regression presets preserve the STEP20 core trade rows.
- `MODIFY` rows are emitted only when a live protective modify actually
  executes.
- Close-before-modify precedence means a bar that closes a position should not
  also emit a `MODIFY` row for the same position lifecycle.

## broker_audit.csv

Current emitted columns:
- `timestamp`
- `symbol`
- `tag`
- `detail`
- `trade_id`
- `position_id`
- `pending_exit_reason`
- `pending_modify_reason`
- `modify_count`
- `active_model_pack_dir`
- `pack_dir_at_entry`
- `tx_authority_enabled`
- `runtime_reload_status`
- `account_login`
- `account_server`
- `ea_version`
- `log_schema_version`

Current audit tags:
- `init`
- `deinit`
- `entry_logged`
- `exit_logged`
- `runtime_reload_attempt`
- `runtime_reload_success`
- `runtime_reload_rollback`
- `modify_applied`

## Validation invariants

The retained STEP21 summaries currently verify:
- feature-off control / live-pass / live-opposite regressions core-row match
  their retained STEP20 artifacts
- duplicate non-modify `(trade_id,event_type)` groups remain `0`
- duplicate `EXIT` groups remain `0`
- same-timestamp `EXIT -> ENTRY` remains `0`
