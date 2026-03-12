---
description: Initialize a new campaign run workspace from manifest.yaml. Creates the run scaffold with preset and metadata. Use at the start of WF2.
user-invocable: true
---

# Campaign Bootstrap

Create a new campaign run directory with preset and metadata.

## Arguments
- `$0` = manifest path (e.g. `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml`)
- `$1` = window alias (e.g. `benchmark`, `fold_1`, `oos_validation`)

## Steps

1. **Run campaign runner prepare:**
```bash
python tools/run_campaign_backtest.py prepare $0 --window $1
```

2. **Report created artifacts:**
- Run directory path (e.g. `runs/RUN_<ts>/`)
- `00_request/preset_snapshot.ini` — MT5 tester preset
- `00_request/request_meta.json` — run metadata with window boundaries

3. **Warnings:**
- If window alias is `benchmark`, remind that this window is reserved for independent comparison, NOT optimization
- The preset uses date-only FromDate/ToDate (MT5 limitation). Raw overcapture will be clipped at parser level (A' policy)

## Next Steps
After bootstrap, the operator should:
1. Compile EA: `metaeditor64.exe /compile:src/ea/TripleSigma.mq5`
2. Run MT5 tester: `terminal64.exe /config:preset_snapshot.ini`
3. Copy outputs from tester agent sandbox to `20_raw/`
4. Seal: `/campaign-run-sealer <run_dir>`
