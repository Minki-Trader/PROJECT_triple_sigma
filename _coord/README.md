# _coord Layout

Purpose:
- Keep collaboration, validation artifacts, logs, and tester presets out of `src/`.

Root files:
- `CHAT.md`: archived chat thread
- `CHAT_02.md`: active collaboration thread
- `BACKTEST_BASELINE.md`: fixed backtest baseline notes

Folders:
- `artifacts/`: immutable retained step evidence
- `logs/compile/`: compile logs by step
- `logs/smoke/`: smoke-test logs
- `ops/`: retained artifact standards, triage notes, and recovery matrices
- `tester/stepXX/`: tester `.ini` and `.set` files grouped by step

Current retained STEP16 artifacts:
- `artifacts/step16_passonly_smoke/`
- `artifacts/step16_trade_smoke/`
- `artifacts/step16_shadow_smoke/`
- `artifacts/step16_recovery_open_smoke/`
- `artifacts/step16_recovery_pending_exit_smoke/`

Current retained STEP16 smoke summaries:
- `logs/smoke/step16_passonly_summary.md`
- `logs/smoke/step16_trade_smoke_summary.md`
- `logs/smoke/step16_shadow_smoke_summary.md`
- `logs/smoke/step16_recovery_open_summary.md`
- `logs/smoke/step16_recovery_pending_exit_summary.md`

Current retained STEP16 tester presets:
- `tester/step16/step16_tester_passonly.ini`
- `tester/step16/step16_tester_trade_smoke.ini`
- `tester/step16/step16_tester_shadow_smoke.ini`
- `tester/step16/step16_tester_recovery_open.ini`
- `tester/step16/step16_tester_recovery_pending_exit.ini`

Current retained STEP17 artifacts:
- `artifacts/step17_control_trade_smoke/`
- `artifacts/step17_shadow_regression_smoke/`
- `artifacts/step17_live_early_exit_smoke/`
- `artifacts/step17_recovery_pending_early_exit_smoke/`
- `artifacts/step17_reject_once_smoke/`

Current retained STEP17 smoke summaries:
- `logs/smoke/step17_control_trade_summary.md`
- `logs/smoke/step17_shadow_regression_summary.md`
- `logs/smoke/step17_live_early_exit_summary.md`
- `logs/smoke/step17_recovery_pending_early_exit_summary.md`
- `logs/smoke/step17_reject_once_summary.md`

Current retained STEP17 tester presets:
- `tester/step17/step17_tester_control_trade.ini`
- `tester/step17/step17_tester_shadow_regression.ini`
- `tester/step17/step17_tester_live_early_exit.ini`
- `tester/step17/step17_tester_recovery_pending_early_exit.ini`
- `tester/step17/step17_tester_reject_once.ini`

Current retained STEP18 artifacts:
- `artifacts/step18_control_trade/`
- `artifacts/step18_live_early_exit/`
- `artifacts/step18_recovery_pending_early_exit/`
- `artifacts/step18_reject_once/`

Current retained STEP18 smoke summaries:
- `logs/smoke/step18_control_trade_summary.md`
- `logs/smoke/step18_live_early_exit_summary.md`
- `logs/smoke/step18_recovery_pending_early_exit_summary.md`
- `logs/smoke/step18_reject_once_summary.md`

Current retained STEP18 tester presets:
- `tester/step18/step18_tester_control_trade.ini`
- `tester/step18/step18_tester_live_early_exit.ini`
- `tester/step18/step18_tester_recovery_pending_early_exit.ini`
- `tester/step18/step18_tester_reject_once.ini`

Current retained STEP19 artifacts:
- `artifacts/step19_control_trade/`
- `artifacts/step19_live_pass_regression/`
- `artifacts/step19_live_opposite_probe/`
- `artifacts/step19_recovery_pending_opposite_probe/`
- `artifacts/step19_reject_once_opposite_probe/`

Current retained STEP19 smoke summaries:
- `logs/smoke/step19_control_trade_summary.md`
- `logs/smoke/step19_live_pass_regression_summary.md`
- `logs/smoke/step19_live_opposite_probe_summary.md`
- `logs/smoke/step19_recovery_pending_opposite_probe_summary.md`
- `logs/smoke/step19_reject_once_opposite_probe_summary.md`

Current retained STEP19 tester presets:
- `tester/step19/step19_tester_control_trade.ini`
- `tester/step19/step19_tester_live_pass_regression.ini`
- `tester/step19/step19_tester_live_opposite_probe.ini`
- `tester/step19/step19_tester_recovery_pending_opposite_probe.ini`
- `tester/step19/step19_tester_reject_once_opposite_probe.ini`

Current retained STEP20 artifacts:
- `artifacts/step20_control_trade/`
- `artifacts/step20_live_pass_regression/`
- `artifacts/step20_live_opposite_regression/`
- `artifacts/step20_live_be_probe/`
- `artifacts/step20_recovery_pending_modify/`
- `artifacts/step20_reject_once_modify/`
- `artifacts/step20_close_vs_modify_precedence/`

Current retained STEP20 smoke summaries:
- `logs/smoke/step20_control_trade_summary.md`
- `logs/smoke/step20_live_pass_regression_summary.md`
- `logs/smoke/step20_live_opposite_regression_summary.md`
- `logs/smoke/step20_live_be_probe_summary.md`
- `logs/smoke/step20_recovery_pending_modify_summary.md`
- `logs/smoke/step20_reject_once_modify_summary.md`
- `logs/smoke/step20_close_vs_modify_precedence_summary.md`

Current retained STEP20 tester presets:
- `tester/step20/step20_tester_control_trade.ini`
- `tester/step20/step20_tester_live_pass_regression.ini`
- `tester/step20/step20_tester_live_opposite_regression.ini`
- `tester/step20/step20_tester_live_be_probe.ini`
- `tester/step20/step20_tester_recovery_pending_modify.ini`
- `tester/step20/step20_tester_reject_once_modify.ini`
- `tester/step20/step20_tester_close_vs_modify_precedence.ini`

Current retained STEP21 artifacts:
- `artifacts/step21_control_trade/`
- `artifacts/step21_live_pass_regression/`
- `artifacts/step21_live_opposite_regression/`
- `artifacts/step21_close_vs_modify_precedence/`
- `artifacts/step21_live_trailing_probe/`
- `artifacts/step21_live_tp_reshape_probe/`
- `artifacts/step21_live_time_policy_probe/`
- `artifacts/step21_recovery_pending_modify_tx/`
- `artifacts/step21_runtime_reload_success/`
- `artifacts/step21_runtime_reload_rollback/`

Current retained STEP21 smoke summaries:
- `logs/smoke/step21_control_trade_summary.md`
- `logs/smoke/step21_live_pass_regression_summary.md`
- `logs/smoke/step21_live_opposite_regression_summary.md`
- `logs/smoke/step21_close_vs_modify_precedence_summary.md`
- `logs/smoke/step21_live_trailing_probe_summary.md`
- `logs/smoke/step21_live_tp_reshape_probe_summary.md`
- `logs/smoke/step21_live_time_policy_probe_summary.md`
- `logs/smoke/step21_recovery_pending_modify_tx_summary.md`
- `logs/smoke/step21_runtime_reload_success_summary.md`
- `logs/smoke/step21_runtime_reload_rollback_summary.md`

Current retained STEP21 tester presets:
- `tester/step21/step21_tester_control_trade.ini`
- `tester/step21/step21_tester_live_pass_regression.ini`
- `tester/step21/step21_tester_live_opposite_regression.ini`
- `tester/step21/step21_tester_close_vs_modify_precedence.ini`
- `tester/step21/step21_tester_live_trailing_probe.ini`
- `tester/step21/step21_tester_live_tp_reshape_probe.ini`
- `tester/step21/step21_tester_live_time_policy_probe.ini`
- `tester/step21/step21_tester_recovery_pending_modify_tx.ini`
- `tester/step21/step21_tester_runtime_reload_success.ini`
- `tester/step21/step21_tester_runtime_reload_rollback.ini`

Current retained ops docs:
- `ops/RETAINED_ARTIFACT_STANDARD.md`
- `ops/EARLY_EXIT_TRIAGE_RUNBOOK.md`
- `ops/RECOVERY_MATRIX.md`
- `ops/PROTECTIVE_MODIFY_TRIAGE_RUNBOOK.md`
- `ops/control_pack_registry.yaml`
- `ops/MASTER_TABLE_CONTRACT.md`
- `ops/OPTIMIZATION_OPERATOR_RUNBOOK.md`

Current campaigns:
- `campaigns/C2026Q1_stage1_refresh/manifest.yaml`

Current campaign output directories:
- `campaigns/C2026Q1_stage1_refresh/raw_tester_outputs/`
- `campaigns/C2026Q1_stage1_refresh/parser_outputs/`
- `campaigns/C2026Q1_stage1_refresh/analytics/`
- `campaigns/C2026Q1_stage1_refresh/benchmark/`
- `campaigns/C2026Q1_stage1_refresh/oos/`
- `campaigns/C2026Q1_stage1_refresh/stress/`
- `campaigns/C2026Q1_stage1_refresh/shortlist/`
- `campaigns/C2026Q1_stage1_refresh/reports/`
- `campaigns/C2026Q1_stage1_refresh/freeze/`

Rule of thumb:
- Keep active coordination files at `_coord/` root.
- Keep historical retained evidence under `artifacts/`.
- Put one-off logs under `logs/`.
- Put reusable tester presets under `tester/stepXX/`.
- Put optimization governance under `ops/`.
- Put campaign-specific work under `campaigns/<campaign_id>/`.
