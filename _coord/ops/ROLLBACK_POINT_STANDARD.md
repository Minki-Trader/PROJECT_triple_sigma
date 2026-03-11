# Rollback Point Standard

Status:
- Governs WF9 (Rollback Point) in the Optimization Operator Runbook.
- Every release candidate must have a matching rollback point.

## Purpose

A rollback point is a full snapshot of the previous stable state that allows
reverting to a known-good configuration if the new release candidate fails
in live operation or subsequent validation.

## Rollback Bundle Contents

Each rollback point stored in `_coord/rollback_points/<rb_id>/` must contain:

1. **Model pack** - complete copy of the previous stable model pack directory.
2. **EA preset** - `.ini` file with the previous parameter set.
3. **Runtime patch inputs** - any files from `triple_sigma_runtime_patch/`
   that were active during the previous stable state.
4. **rollback_manifest.yaml** containing:
   - `rollback_id`
   - `created_date`
   - `superseded_by` - the RC that triggered this rollback point creation.
   - `previous_rc_id` - if this rolls back to a prior RC.
   - `model_pack_version` and lineage.
   - `ea_commit_hash`
   - `parameter_snapshot` - all EA input values.
   - `file_hashes` - SHA-256 of every file in the bundle.
   - `validation_status` - result of hash verification.
5. **KPI snapshot** - key metrics of the previous stable state.

## Creation Procedure

1. Before promoting a new RC, package the current stable state.
2. Copy all required files to `_coord/rollback_points/<rb_id>/`.
3. Generate SHA-256 hashes for every file.
4. Write `rollback_manifest.yaml`.
5. Verify hashes match the originals.

## Rollback Execution Procedure

1. Identify the rollback point to restore.
2. Verify file hashes against `rollback_manifest.yaml`.
3. Copy model pack back to `MQL5/Files/`.
4. Restore EA preset to `_coord/tester/` or apply parameters manually.
5. If runtime patch inputs exist, restore them to `triple_sigma_runtime_patch/`.
6. Recompile EA and verify compile clean.
7. Run CP0-CP1 checks (build integrity + runtime invariants).
8. Document the rollback event in `_coord/campaigns/<campaign_id>/reports/`.

## Naming Convention

Format: `RB_<campaign_id>_<sequence>_<date>`

Example: `RB_C2026Q1_stage1_refresh_001_20260315`

## Non-Negotiable Rules

1. A release candidate MUST NOT be promoted without a matching rollback point.
2. Rollback points are immutable once created. Do not modify in place.
3. Rollback execution must restore runtime invariants (CP1) before
   any further optimization work resumes.
4. Patch inputs must be retained. A rollback point without patch inputs
   for a state that had runtime reload is non-reproducible and invalid.

## Hash Verification

Use SHA-256 for all files. Verification script pattern:

```python
import hashlib
from pathlib import Path

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```
