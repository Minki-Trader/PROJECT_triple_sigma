# STEP14 Validation And Tuning

> **Status: BASELINE IMPLEMENTED**
>
> STEP14 is implemented as the first validation/tuning/selection layer built on
> top of the already accepted STEP12 and STEP13 baselines.
> STEP15 remains responsible for ONNX export and production packaging.

## Scope

STEP14 must act as a reproducible, leak-free selection gate.

- Reuse the accepted q1 STEP12 outer split exactly.
- Build a deterministic inner validation manifest inside outer-train only.
- Tune only the current baseline families.
- Compare every challenger against the explicit baseline control.
- Select a provisional winner from inner CV.
- Confirm or reject that provisional winner on the untouched outer holdout.
- Emit final selected pre-export artifacts plus a STEP15 handoff manifest.

## Frozen Inputs

STEP14 inherits the frozen rules and must not alter them.

- Document priority remains:
  `POLICY_FREEZE.md -> CONTRACT.md -> EA_RUNTIME.md -> ONNX_DEV_SPEC.md`
- Candidate state remains one-hot-or-zero with `(1,1)` forbidden.
- PASS defaults remain `(1.5, 2.0, 24)`.
- Hold cap remains `72` bars.
- Runtime fail-safe remains `failure -> PASS`.
- Stage1 continues to include `cand=(0,0)` rows as forced PASS.
- Stage2 continues to use only `cand_long XOR cand_short == 1`.
- Input/output contract remains `[1,64,22] -> [1,6]`.
- Regime thresholds remain shared training/runtime metadata.

## Default Validation Topology

The first implementation should use the narrowest defensible protocol.

- Outer holdout:
  reuse the accepted q1 STEP12 split exactly.
- Inner validation:
  target `2` expanding folds inside outer-train only.
- Inner fold target train ratios:
  `0.60` and `0.80`
- Embargo:
  `72` bars
- Shuffle:
  forbidden
- Relaxed minimum-count fallback:
  forbidden for STEP14 acceptance

If the generator cannot build the target `2` folds while satisfying the hard
minimum-count rules, STEP14 should stop with a clear HOLD/FAIL reason instead of
silently relaxing the protocol.

## Default Tuning Scope

The first implementation stays inside the current baseline families.

Stage1:
- family: `MLPClassifier`
- tune only:
  - `cand0_max_fraction in {0.95, 0.75, 0.50}`
  - `cand0_sample_weight in {1.0, 0.3}`
- all other accepted STEP12 baseline knobs stay fixed

Stage2:
- family: `MultiOutputRegressor(GradientBoostingRegressor(loss="huber"))`
- tune only:
  - `gbr_n_estimators in {120, 180}`
  - `gbr_learning_rate in {0.05, 0.03}`
  - `gbr_max_depth in {2, 3}`
- all other accepted STEP13 baseline knobs stay fixed

Explicitly out of scope for the first implementation:
- new architecture families
- per-regime hyperparameter tuning
- joint Stage1 x Stage2 search
- random/bayesian search frameworks
- ONNX export or packaging

## Scaler And Split Lineage

STEP14 must preserve outer lineage while avoiding inner-fold leakage.

- Outer split plan:
  exact copy of accepted STEP12 q1 split
- Inner folds:
  built deterministically inside outer-train only
- Inner-fold scaler:
  computed from that fold's training bars only
- Final selected outer-train scaler:
  computed from full outer-train bars only

Both Stage1 and Stage2 must share the same outer holdout and the same inner fold
manifest. They do not need joint model search, but they must use the same
time-protocol.

## Selection Defaults

Stage1:
- primary metric:
  equal-weight mean `macro_f1` across `fold x regime`
- hard guardrail:
  `min cand0_pass_recall >= 0.50`
- challenger eligibility:
  unchanged; non-baseline candidates must satisfy the guardrail above
- control fallback:
  if no Stage1 candidate is eligible under the inner-CV guardrail, the explicit
  baseline control becomes the provisional Stage1 control candidate so that
  STEP14 can still complete outer-holdout comparison
- tie-breakers:
  higher mean `cand0_pass_recall`, then lower mean `log_loss`, then baseline preferred

Stage2:
- primary metric:
  equal-weight mean `normalized_effective_mae_mean` across `fold x regime x side`
- hard guardrails:
  - all finite
  - contract-valid postprocess
  - no sparse fallback
  - `max hold_boundary_rate <= 0.05`
- tie-breakers:
  higher share of rows beating the default baseline, then lower mean
  `hold_boundary_rate`, then baseline preferred

Outer-holdout arbitration:
- provisional winner is accepted only if it strictly beats the baseline on the
  stage primary metric and still passes guardrails
- otherwise the baseline remains the final STEP14 handoff choice

## Required Artifacts

The first implementation should write:

- `validation_metadata.json`
- `outer_split_plan.json`
- `outer_split_audit.json`
- `inner_split_manifest.json`
- `inner_scaler_stats/fold_0.json`
- `inner_scaler_stats/fold_1.json`
- `stage1_candidate_registry.csv`
- `stage2_candidate_registry.csv`
- `stage1_cv_summary.csv`
- `stage2_cv_summary.csv`
- `stage1_selection_report.json`
- `stage2_selection_report.json`
- `final_holdout_report.json`
- `handoff_manifest.json`
- `reproducibility_report.json`
- `selected_stage1/` final chosen refit artifacts
- `selected_stage2/` final chosen refit artifacts
- `selected_stage1_smoke.json`
- `selected_stage2_smoke.json`

`selected_stage1` and `selected_stage2` must both inherit the same STEP14
outer-train split/scaler lineage. STEP15 will later consume the selected
metadata and artifacts for export/packaging.

## Acceptance

The implemented STEP14 gate is complete only if all of the following are true.

- `A1_lineage_audit_pass`
- `A2_outer_holdout_matches_step12`
- `A3_inner_split_manifest_valid`
- `A4_candidate_registries_complete`
- `A5_stage1_cv_complete_and_valid`
- `A6_stage2_cv_complete_and_valid`
- `A7_selected_final_artifacts_exist_and_smoke_pass`
- `A8_outer_holdout_handoff_decision_valid`
- `A9_reproducibility_pass`

Reproducibility rules:
- split manifests, candidate registries, provisional winner ids, and final
  handoff ids must match exactly
- aggregate primary metrics must match within a small floating tolerance
  (`1e-8` default for the first implementation)

`A5_stage1_cv_complete_and_valid` means:
- Stage1 CV rows are complete and finite
- Stage1 probabilities are finite and normalized
- a provisional/control Stage1 candidate is resolved for outer-holdout
  comparison

It does not require a non-baseline challenger to satisfy the Stage1 inner-CV
guardrail.

## Out Of Scope

The following should not block STEP14 completion.

- more folds
- larger search spaces
- new families
- calibration layers
- per-regime tuning
- ONNX export
- model-pack packaging
- live-readiness gating
- profitability evaluation
