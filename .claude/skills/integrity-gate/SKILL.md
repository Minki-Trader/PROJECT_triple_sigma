---
description: Run CP1/CP4 strict validation on a parsed campaign run. Checks 9-gate validator + runtime invariants + parser coverage. Use after parser-replay completes.
user-invocable: true
---

# Integrity Gate

Aggregate checkpoint validation for a campaign run.

## Arguments
- `$ARGUMENTS` = run directory path (e.g. `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z`)

## Steps

1. **Run 9-gate campaign validator:**
```bash
python tools/validate_campaign_run.py $ARGUMENTS
```
Report verdict and all issues (FAIL/WARN/INFO).

2. **Check parse_manifest.json (CP4 — parser readiness):**
Read `$ARGUMENTS/30_parsed/parse_manifest.json`:
- `pass` field — overall parse success
- `invariants_pass` — CP1 runtime invariants
- `window_clipping` — clipping stats if present
- `issues` — any schema or invariant failures

3. **Check coverage_manifest.json (if exists):**
Read `$ARGUMENTS/30_parsed/coverage_manifest.json`:
- EXIT coverage percentage
- ENTRY gate status
- Unmapped event count

4. **Aggregate CP verdicts:**

| CP | Check | Source |
|----|-------|--------|
| CP0 | Compile clean | `10_compile/compile_log.txt` — 0 errors |
| CP1 | Runtime invariants | `parse_manifest.json` `invariants_pass` |
| CP2 | Data readiness | Manifest window matches freeze |
| CP3 | Control-pack | `21_hash/pack_hash_manifest.json` exists |
| CP4 | Parser readiness | `parse_manifest.json` `pass` + coverage |

Report each CP as PASS/FAIL/PROVISIONAL.

## Role Boundary
This skill operates as **parser-analytics** (read-only analysis). It does NOT write to `50_validator/` — that is the independent-validator's scope. Output goes to stdout only.
