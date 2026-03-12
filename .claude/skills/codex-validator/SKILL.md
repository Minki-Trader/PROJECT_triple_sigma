---
description: Run the independent Codex validator thread (F6/AG4) on a sealed and parsed campaign run. Packages frozen evidence and invokes Codex gpt-5.4 for cross-review. Use after integrity-gate passes.
user-invocable: true
---

# Codex Validator (Independent Validator Thread)

F6 remediation: independent validation via Codex gpt-5.4. Implements the **independent-validator** role from AGENT_ROLE_POLICY.md.

## Arguments
- `$ARGUMENTS` = run directory path (e.g. `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z`)

## Pre-checks
Verify all required artifacts exist before proceeding:
- `$ARGUMENTS/run_manifest.json`
- `$ARGUMENTS/21_hash/raw_hash_manifest.json`
- `$ARGUMENTS/21_hash/pack_hash_manifest.json`
- `$ARGUMENTS/30_parsed/parse_manifest.json`
- `$ARGUMENTS/50_validator/validator_report.json` (from validate_campaign_run.py)

If any are missing, report and stop.

## Evidence Bundle
Collect the following into the Codex prompt context:
1. `run_manifest.json` — run metadata, window boundaries, pack reference
2. `21_hash/raw_hash_manifest.json` — raw file integrity hashes
3. `30_parsed/parse_manifest.json` — parse results, clipping stats, invariants
4. `50_validator/validator_report.json` — 9-gate validation results
5. Key stats from parsed outputs (trade count, bar count, KPIs)

## Codex Invocation
```bash
codex exec --full-auto -m gpt-5.4 "<constructed_prompt>"
```

The prompt MUST include:
- Role constraint: "You are the independent-validator. Read-only access to frozen evidence. No code modification."
- All evidence from the bundle above
- Specific review criteria:
  - Raw hash integrity (do file counts match?)
  - Window boundary compliance (any FAIL gates?)
  - Parse invariants (any violations?)
  - Trade lifecycle integrity (clipping stats reasonable?)
  - Schema conformance (all manifests valid?)
- Request verdict: APPROVED / HOLD (with specific items)

## Output
Save Codex response to `$ARGUMENTS/50_validator/codex_validator_report.md`.

Report the verdict to the user.

## Role Boundary
This skill operates as **independent-validator**:
- Reads sealed artifacts ONLY (20_raw/, 21_hash/, 30_parsed/, 50_validator/)
- Writes ONLY to `50_validator/codex_validator_report.md`
- Does NOT modify source code, tools, or any other directory
- **No-self-promotion**: This is a separate validation channel from the writer-orchestrator (Claude main thread)

## Fallback
If Codex is unavailable (API key issue, model not found), instruct the user to:
1. Review the evidence bundle manually
2. Or run the Codex command directly from terminal
