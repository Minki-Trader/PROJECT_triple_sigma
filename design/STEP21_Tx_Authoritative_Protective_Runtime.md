# STEP21 Tx-Authoritative Protective Runtime

Status:
- Implemented on 2026-03-09.
- Compile-clean and tester-validated in the current workspace snapshot.

Purpose:
- Activate the STEP20 deferred runtime surface without reopening accepted
  STEP20 feature-off behavior.
- Extend the protective modify family from BE-only into a wider live runtime.
- Promote transaction-driven execution logging and reconciliation while keeping
  `TS_SyncPositionState()` as a fallback for recovery and out-of-band events.
- Add schema, audit, and runtime-reload observability required for review.

Implemented runtime surface:
- Protective modify family:
  - `BREAK_EVEN`
  - `TRAILING`
  - `TP_RESHAPE`
  - `TIME_POLICY`
- `trade_log.csv` widened with Step21 suffix columns:
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
- `trade_log.csv` now emits `MODIFY` rows.
- `bar_log_YYYYMMDD.csv` widened with pending / modify / tx-authority /
  runtime-reload state.
- `broker_audit.csv` added for runtime reload and entry / exit audit tags.
- `OnTradeTransaction()` is now used for tx-authoritative entry / exit
  observation and log emission.
- Runtime model-pack hot reload / rollback is available through a patch file
  under terminal `Files`.

Deliberate boundary:
- `TS_SyncPositionState()` is still retained as a fallback reconciliation
  surface for recovery and out-of-band state repair.
- Feature-off behavior must remain aligned with STEP20 retained evidence.
- Close-before-modify precedence remains higher priority than protective modify.

Key implementation notes:
- `src/ea/TripleSigma.mq5`
  - adds Step21 protective / tx-authority / broker-audit / runtime-reload
    inputs
  - wires runtime patch handling on the closed-bar timer seam
- `src/include/TS_Execution.mqh`
  - finalizes entry / exit logs through tx-authoritative deal / position events
  - adds runtime reload, rollback, broker audit, and widened protective modify
  - preserves a bar-cycle guard so locally requested closes do not suppress the
    next valid bar, while truly out-of-band exits still block immediate reentry
- `src/include/TS_Logger.mqh`
  - widens `trade_log.csv` and `bar_log_YYYYMMDD.csv`
  - adds `broker_audit.csv`
  - adds `MODIFY` event emission
- `src/include/TS_Monitor.mqh`
  - classifies modify reasons by family
  - tracks runtime reload attempt / success / rollback counters

Validation matrix retained in `_coord/tester/step21/`:
- `step21_tester_control_trade.ini`
- `step21_tester_live_pass_regression.ini`
- `step21_tester_live_opposite_regression.ini`
- `step21_tester_close_vs_modify_precedence.ini`
- `step21_tester_live_trailing_probe.ini`
- `step21_tester_live_tp_reshape_probe.ini`
- `step21_tester_live_time_policy_probe.ini`
- `step21_tester_recovery_pending_modify_tx.ini`
- `step21_tester_runtime_reload_success.ini`
- `step21_tester_runtime_reload_rollback.ini`

Validation results:
- compile:
  - `0 errors, 0 warnings`
- feature-off regressions:
  - control trade core-row match: `true`
  - live-pass regression core-row match: `true`
  - live-opposite regression core-row match: `true`
- precedence / duplicate safety:
  - close-before-modify precedence preserved
  - duplicate non-modify `(trade_id,event_type)` groups: `0`
  - duplicate `EXIT` groups: `0`
  - same-timestamp `EXIT -> ENTRY`: `0` across retained Step21 summaries
- modify-family probes:
  - trailing probe emits `MODIFY` rows with `modify_reason=TRAILING`
  - TP reshape probe emits `MODIFY` rows with `modify_reason=TP_RESHAPE`
  - time-policy probe emits `MODIFY` rows with `modify_reason=TIME_POLICY`
  - recovery pending modify probe emits `MODIFY` rows with
    `modify_reason=BREAK_EVEN`
- runtime reload:
  - success path ends with `runtime_reload_status=RELOADED`
  - forced-failure path ends with `runtime_reload_status=ROLLED_BACK`
  - broker audit retains `runtime_reload_attempt`, success, and rollback tags

Out-of-scope for this checkpoint:
- profitability sign-off
- long-window performance judgement
- model retraining / repackaging
- ONNX graph optimization
- live broker execution validation in a real account session
