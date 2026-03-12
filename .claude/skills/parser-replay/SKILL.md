---
description: Re-run the full parser pipeline (parse -> master -> counterfactual -> daily_risk) on a sealed campaign run with window clipping.
user-invocable: true
---

# Parser Replay

Run the 4-stage parser pipeline on a sealed campaign run.

## Arguments
- `$ARGUMENTS` = run directory path (e.g. `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z`)

## Steps

1. **Read window boundaries from run manifest:**
```bash
python -c "import json; m=json.load(open('$ARGUMENTS/run_manifest.json')); print(m['window_from']); print(m['window_to'])"
```
Extract `window_from` and `window_to` values.

2. **Parse raw outputs with window clipping (A' policy):**
```bash
python tools/parse_step21_run.py "$ARGUMENTS/20_raw" "$ARGUMENTS/30_parsed" --window-from "<window_from>" --window-to "<window_to>"
```

3. **Build master tables:**
```bash
python tools/build_master_tables.py "$ARGUMENTS/30_parsed"
```

4. **Build counterfactual eval:**
```bash
python tools/build_counterfactual_eval.py "$ARGUMENTS/30_parsed"
```

5. **Build daily risk metrics:**
```bash
python tools/build_daily_risk_metrics.py "$ARGUMENTS/30_parsed"
```

6. **Report results:**
- Read `$ARGUMENTS/30_parsed/parse_manifest.json` for clipping stats and validation status
- Report trade count, bar count, clipping stats, invariant pass/fail
- Report counterfactual decision type distribution
- Report daily risk headline KPIs (PnL, DD, WR, PF)

## Role Boundary
This skill operates as **parser-analytics**. It reads `20_raw/` (immutable, never modified) and writes to `30_parsed/`. Does NOT write to `50_validator/`.
