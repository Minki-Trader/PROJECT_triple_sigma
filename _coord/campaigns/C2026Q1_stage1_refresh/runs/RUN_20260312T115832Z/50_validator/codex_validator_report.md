# Codex Validator Report - RUN_20260312T115832Z

- Scope: frozen admissibility review for WF4 routing on `C2026Q1_stage1_refresh`
- Reviewer role: `codex-validator`
- Verdict: `APPROVED`

## Evidence Checked

- `run_manifest.json`
- `21_hash/raw_hash_manifest.json`
- `21_hash/pack_hash_manifest.json`
- `30_parsed/parse_manifest.json`
- `30_parsed/trades_master.parquet`
- `30_parsed/counterfactual_eval.parquet`
- `30_parsed/daily_risk_metrics.parquet`
- `50_validator/validator_report.json`

## Findings

- `validator_report.json` = `PASS` with `require_parse=true`, `total_checks=10`, `fails=0`
- Raw and pack hash integrity passed under strict validator replay
- Exact A' clipping confirmed:
  - `bars_clipped=198`
  - `trade_ids_clipped=11`
  - `trade_rows_clipped=22`
  - `window_from=2024.06.04 17:25`
  - `window_to=2025.04.02 09:00`
- Parser integrity confirmed:
  - `pass=true`
  - `invariants_pass=true`
  - `master_tables_pass=true`
  - `coverage_pass=true`
- Benchmark KPI packet exists in `40_kpi/kpi_summary.json`
- WF4 routing packet exists in `60_decision/branch_decision_packet.json`

## Operator Notes

- Left-boundary raw overcapture remains expected MT5 date-only behavior and is contained by parser clipping.
- Refreshed risk evidence now uses `tester_baseline.deposit=500`, so `max_equity_dd_pct=-92.21%` is the correct benchmark risk figure for this run.
- `branch_decision_packet.json` recommends `ML-first` with `high` confidence; this memo does not approve any release candidate or promotion bundle.
