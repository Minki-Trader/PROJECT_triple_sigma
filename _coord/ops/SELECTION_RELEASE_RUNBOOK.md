# Selection & Release Runbook

Status:
- Governs the promotion path from optimization shortlist to release candidate.
- Follows WF8 (Release Candidate) in the Optimization Operator Runbook.

## Scope

This runbook covers:
1. Shortlist assembly from optimization results.
2. Selection committee evaluation.
3. Release candidate packaging.
4. Handoff verification.

## Prerequisites

- WF5 (branch optimization) completed for the chosen layer.
- WF6 (benchmark/OOS/stress restage) passed.
- WF7 (limited joint sweep) passed or explicitly deferred with rationale.
- All operating checkpoints CP0-CP7 satisfied.

## Step 1: Shortlist Assembly

Inputs:
- Parsed analytics from `parser_outputs/`.
- KPI summaries from `daily_risk_metrics.parquet` and `counterfactual_eval.parquet`.

Actions:
1. Rank candidates by primary KPIs (expectancy_r, profit_factor, drawdown profile).
2. Filter by mandatory thresholds:
   - Runtime invariants pass (CP1).
   - OOS profit_factor >= 1.0.
   - Max cumulative drawdown within acceptable bounds.
   - No fatal runtime anomaly in stress window.
3. Retain top N candidates (recommended: 3-5).
4. Save shortlist to `_coord/campaigns/<id>/shortlist/`.

Output: `_coord/campaigns/<id>/shortlist/shortlist_summary.json`

## Step 2: Selection Committee Evaluation

Inputs:
- Shortlist candidates.
- Full KPI framework (ML signal, EA policy, execution, portfolio/risk).

Actions:
1. Compare candidates across all four KPI layers.
2. Check for fragile single-interaction dependence.
3. Verify no overfitting indicators:
   - Benchmark vs OOS performance gap < threshold.
   - Window dispersion within acceptable range.
   - Concentration HHI below threshold.
4. Document selection rationale.

Output: `reports/selection_decision.md`

Pass condition: exactly one candidate selected with documented rationale.

## Step 3: Release Candidate Packaging

Inputs:
- Selected candidate parameters and pack.
- Current EA source (commit hash).

Actions:
1. Package the following into `_coord/releases/<rc_id>/`:
   - Model pack directory (copy from MQL5/Files/).
   - EA parameter snapshot (`.ini` preset).
   - Runtime patch inputs (from `triple_sigma_runtime_patch/`, if active).
   - `rc_manifest.yaml` containing:
     - campaign_id, candidate_id.
     - EA commit hash.
     - Model pack version and lineage.
     - All parameter values.
     - KPI snapshot (key metrics at selection time).
     - File hashes (SHA-256) for all included files.
   - Link to selection_decision.md.
   - Link to this runbook.
2. Verify file hashes.
3. Test reproducibility: re-run with packaged preset on benchmark window,
   confirm output matches within tolerance.

Output: `_coord/releases/<rc_id>/rc_manifest.yaml`

Pass condition:
- All files present and hashed.
- Reproducibility test passes.
- Handoff checklist complete.

## Step 4: Handoff Verification

Checklist:
- [ ] rc_manifest.yaml exists and is complete.
- [ ] Model pack files match hashes.
- [ ] EA preset is valid and compiles clean.
- [ ] KPI snapshot is attached.
- [ ] Selection rationale is documented.
- [ ] Rollback point exists (see ROLLBACK_POINT_STANDARD.md).
- [ ] Operator runbook is updated with RC reference.

## RC Naming Convention

Format: `RC_<campaign_id>_<sequence>_<date>`

Example: `RC_C2026Q1_stage1_refresh_001_20260315`
