# STEP13 Stage2 Training

> **Status: BASELINE IMPLEMENTED**
>
> This document describes the current baseline implementation for STEP13.
> Architecture bake-off, hyperparameter tuning, walk-forward validation, and ONNX export remain outside this step.

## Scope

STEP13 trains the Stage2 parameter models for the current-state baseline.

- Input source: clean STEP11 artifacts plus accepted STEP12 artifacts.
- Split/scaler policy: strict reuse of STEP12 `split_plan.json` and `scaler_stats.json`.
- Model family: per-regime, two-direction heads using `MultiOutputRegressor(GradientBoostingRegressor(loss="huber"))`.
- Output form: one bundle per regime, each bundle exposing raw `[N,6]` predictions in the fixed order
  `k_sl_L, k_tp_L, hold_L, k_sl_S, k_tp_S, hold_S`.

## Input Contract

STEP13 requires all of the following before training starts:

- STEP11 validation must already be clean.
- STEP12 `acceptance.A1_no_time_leakage` must be `true`.
- STEP12 `training_metadata.split_plan` must exactly match `split_plan.json`.
- STEP12 scaler source must be `global_train_bars`.
- STEP12 scaler mean/std must be finite, length 12, and strictly positive for std.

If any of these checks fail, STEP13 must stop before fitting models.

## Data Selection

STEP13 operates only on candidate rows where `cand_long + cand_short == 1`.

- `cand=(0,0)` rows are excluded from Stage2 fitting.
- Split assignment is rebuilt from STEP12 `boundary_window_end_idx` and `embargo_bars`.
- Rebuilt train/val/dropped counts must exactly match STEP12 overall counts and per-regime counts.
- Rebuilt `train_end_time`, `val_start_time`, and `no_time_leakage` must also match STEP12.

## Target Masking

Stage2 keeps the fixed six-output contract, but training is direction-aware.

- LONG head uses only `k_sl_L`, `k_tp_L`, `hold_L`.
- SHORT head uses only `k_sl_S`, `k_tp_S`, `hold_S`.
- Exactly one side must be valid per retained row.
- Non-PASS rows must have `label_dir` aligned with the inferred target side.

Rows that violate masking integrity are treated as hard failures.

## Baseline Training Policy

The current baseline trains one regime bundle per regime id `0..5`.

- LONG and SHORT are trained as separate heads.
- PASS rows remain in the training sample but are down-weighted by `pass_row_weight`.
- Sparse heads fall back to the constant default vector `[1.5, 2.0, 24]`.
- Sparse fallback is triggered when either:
  - train count is below `min_train_samples_per_head`, or
  - validation count is below `min_val_samples_per_head`.

This keeps STEP13 deterministic and compatible with later STEP14 comparison work.

## Outputs

STEP13 writes:

- `training_metadata.json`
- `split_plan.json` copied from STEP12
- `scaler_stats.json` copied from STEP12
- `regime_summary.csv`
- `regime_{id}/prm_reg{id}.joblib`
- `regime_{id}/train_report.json`

## Acceptance

The implemented baseline tracks these hard acceptance flags:

- `A1_split_match_step12`
- `A2_step12_no_time_leakage`
- `A3_cand1_only`
- `A4_masking_integrity`
- `A5_bundle_predict_shape_and_finite`
- `A6_postprocess_contract_valid`
- `A7_export_deferred_to_step15`

Additional quality fields are recorded for review, including:

- fallback head count
- number of validation heads beating the default baseline
- maximum hold boundary rate

## Out Of Scope

The following are intentionally deferred:

- model family bake-off
- hyperparameter tuning
- walk-forward or multi-split validation
- ONNX export and production model-pack generation

These remain STEP14 and STEP15 responsibilities.
