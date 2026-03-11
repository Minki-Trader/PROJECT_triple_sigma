# STEP15. ONNX Export and Model-Pack Packaging

> **Status: BASELINE IMPLEMENTED**
>
> A runtime-compatible STEP15 baseline is implemented in
> `src/ml/triplesigma_ml/step15.py` and `src/ml/step15_training.py`.
> The current implementation consumes the accepted STEP14 handoff bundle and
> produces a deployable model-pack plus export validation reports.

## Scope

STEP15 turns the selected STEP14 artifacts into a runtime-compatible model-pack.

- Input source: STEP14 `handoff_manifest.json` plus `selected_stage1/` and `selected_stage2/`
- Export surface: 6 Stage1 ONNX files + 6 Stage2 ONNX files
- Runtime pack files: `pack_meta.csv` and `scaler_stats.json`
- Validation: ONNX checker, shape inference, ONNX Runtime smoke, and source-vs-ONNX parity smoke

## Input Contract

STEP15 requires all of the following before export starts:

- `handoff_manifest.json` exists in the accepted STEP14 artifact directory
- `selected_stage1/` contains:
  - `training_metadata.json`
  - `split_plan.json`
  - `scaler_stats.json`
  - `regime_{id}/clf_reg{id}.joblib` for `id=0..5`
- `selected_stage2/` contains:
  - `training_metadata.json`
  - `split_plan.json`
  - `scaler_stats.json`
  - `regime_{id}/prm_reg{id}.joblib` for `id=0..5`
- Stage1 and Stage2 must share the same source STEP11 lineage and scaler stats
- `model_pack_version` must be present and must be safe for runtime file naming

The current baseline treats the full STEP14 handoff bundle as the STEP15 input
surface. `handoff_manifest.json` alone is not sufficient.

## Export Policy

The current baseline keeps runtime contracts unchanged.

- Input tensor: fixed `[1,64,22]` float32
- Stage1 output: fixed `[1,3]` float32 probability vector
- Stage2 output: fixed `[1,6]` float32 raw parameter vector in the order
  `k_sl_L, k_tp_L, hold_L, k_sl_S, k_tp_S, hold_S`
- Dynamic axes are not used
- Scaling is not embedded in the ONNX graph
- A reshape/flatten adapter is allowed inside the ONNX graph because the source
  sklearn models were trained on flattened `[1,1408]` inputs

Current filename policy is runtime-driven:

- `clf_reg{rid}_v{model_pack_version}.onnx`
- `prm_reg{rid}_v{model_pack_version}.onnx`

## Pack Files

STEP15 writes a deployable `model_pack/` directory containing:

- 12 ONNX files
- `pack_meta.csv`
- `scaler_stats.json`

`pack_meta.csv` remains a legacy filename for runtime compatibility, but the
current runtime expects a `key=value` text format, one entry per line.

The baseline writes only runtime-compatible keys:

- required:
  - `model_pack_version`
  - `schema_version`
  - `regime_policy_version`
  - `candidate_policy_version`
  - `cost_model_version`
  - `atr_thr`
  - `adx_thr1`
  - `adx_thr2`
- optional when present in source metadata:
  - `thr_method`
  - `thr_seed`
  - `thr_notes`
- required for adaptive distance mode:
  - `dist_atr_max_mode`
  - `dist_atr_max_q`
  - `dist_atr_max_w`
  - `dist_atr_max_clamp_lo`
  - `dist_atr_max_clamp_hi`

`scaler_stats.json` is copied through from the selected STEP14 artifacts.
The expected schema remains:

- `mean[12]`
- `std[12]`
- all `std > 0`

## Outputs

The implemented baseline writes:

- `_coord/artifacts/step15_export_q1_out/export_manifest.json`
- `_coord/artifacts/step15_export_q1_out/export_validation_report.json`
- `_coord/artifacts/step15_export_q1_out/model_pack/`

`export_manifest.json` records:

- source STEP14 directory
- selected candidate ids
- `clf_version`
- `prm_version`
- `model_pack_version`
- threshold and lineage metadata
- pinned opset
- generated filenames
- SHA256 hashes of pack files

`export_validation_report.json` records:

- acceptance flags
- per-regime ONNX shape/dtype validation
- pack-meta validation
- scaler schema validation
- ONNX Runtime smoke results
- source-vs-ONNX parity smoke results
- final accepted status

## Acceptance

The implemented baseline tracks these hard acceptance flags:

- `A1_source_bundle_complete_and_consistent`
- `A2_stage1_onnx_export_complete`
- `A3_stage2_onnx_export_complete`
- `A4_pack_meta_complete_and_runtime_compatible`
- `A5_scaler_stats_packaged_and_valid`
- `A6_static_inference_smoke_pass`
- `A7_source_parity_smoke_pass`
- `A8_pack_layout_runtime_compatible`
- `A9_export_reports_complete`

The current q1 baseline run passes `A1..A9` and reports `accepted = true`.

## Out Of Scope

The following remain outside the current STEP15 baseline:

- ONNX graph optimization research
- alternative model families
- runtime or EA code changes
- `gate_config.json`
- STEP16 monitoring/optimization work
- profitability or live-readiness evaluation

## Implementation Notes

- The current baseline pins `target_opset = 17`
- Stage1 export keeps the sklearn classifier output probability-only by routing
  the dense probability tensor to the final ONNX output
- Stage2 export preserves the raw head concat order and leaves runtime
  post-processing to the EA contract layer
