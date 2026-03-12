---
description: Seal raw backtest outputs with SHA-256 hash manifests after MT5 tester run completes. Use after copying raw outputs to runs/RUN_<ts>/20_raw/.
user-invocable: true
---

# Campaign Run Sealer

Seal a campaign run's raw outputs and validate the result.

## Arguments
- `$ARGUMENTS` = run directory path (e.g. `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z`)

## Steps

1. **Seal raw outputs + generate hash manifests:**
```bash
python tools/run_campaign_backtest.py seal $ARGUMENTS
```
Verify exit code 0. If non-zero, report the error and stop.

2. **Run 9-gate validator on sealed run:**
```bash
python tools/validate_campaign_run.py $ARGUMENTS
```
Report the full verdict (PASS/FAIL) and list any WARN/FAIL issues.

3. **Report sealed artifacts:**
- `run_manifest.json` (sealed run manifest)
- `21_hash/raw_hash_manifest.json` (raw file SHA-256 hashes)
- `21_hash/pack_hash_manifest.json` (model pack SHA-256 hashes)

## Role Boundary
This skill operates as **writer-orchestrator**. It seals and validates but does NOT write to `50_validator/` (that is the independent-validator's scope). The validator report from step 2 goes to stdout only.
