---
description: "[SKELETON] Compute KPIs from parsed run and determine ML-first vs EA-first optimization branch. Requires build_kpi_summary.py which is not yet implemented."
user-invocable: true
---

# KPI Branch Decision (Skeleton)

> **STATUS: PARTIALLY IMPLEMENTED** — `tools/build_kpi_summary.py` does not exist yet.
> Manual KPI analysis is supported using existing parsed outputs.

## Arguments
- `$ARGUMENTS` = parsed directory path (e.g. `_coord/campaigns/.../runs/RUN_<ts>/30_parsed`)

## Manual KPI Analysis (available now)

Read and analyze from existing parsed outputs:

1. **Daily risk metrics** (`daily_risk_metrics.parquet`):
   - Gross/Net PnL, Max equity DD, Win rate, Profit Factor
   - Daily PnL distribution, consecutive loss streaks

2. **Counterfactual eval** (`counterfactual_eval.parquet`):
   - Gate regret mean — if high, EA gates are too restrictive
   - Exit opportunity cost — if high, exits are too early
   - Exit risk saved — if high, exits are protective
   - Decision type distribution (GATE_BLOCK count indicates gate filtering level)

3. **Trades master** (`trades_master.parquet`):
   - Long/short PnL split
   - Hold time distribution
   - Exit reason distribution (SL/TP/EARLY_EXIT)

## Decision Matrix (from OPTIMIZATION_OPERATOR_RUNBOOK.md WF4)

| Signal | Direction |
|--------|-----------|
| Stage1 classifier accuracy low, many false entries | **ML-first** (retrain Stage1) |
| Gate rejection rate high with positive regret | **EA-first** (relax gates) |
| Exit timing poor (high opportunity cost) | **EA-first** (tune early exit) |
| Model predictions reasonable but PnL negative | **EA-first** (parameter tuning) |
| Model predictions poor across all regimes | **ML-first** (fundamental retrain) |

## Future Implementation
When `tools/build_kpi_summary.py` is built:
- Automate KPI extraction
- Generate decision packet JSON
- Route to appropriate WF5 branch
