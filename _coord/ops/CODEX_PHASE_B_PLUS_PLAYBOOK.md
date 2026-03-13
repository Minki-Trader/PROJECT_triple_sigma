# Codex Phase B+ Playbook

> Status: Active Phase B+ operating playbook
> Scope: Codex-only agent workflows for WF2-WF4 governance, validation, and promotion gating

## 1. campaign-bootstrap

Purpose: initialize a new campaign run workspace from `manifest.yaml` at the start of WF2.

Arguments:
- `manifest_path`
- `window_alias`

Steps:
1. Run `python tools/run_campaign_backtest.py prepare <manifest_path> --window <window_alias>`
2. Report the created `runs/RUN_<ts>/` path
3. Report `00_request/preset_snapshot.ini` and `00_request/request_meta.json`
4. If `window_alias=benchmark`, restate that the window is comparison-only, not optimization
5. Restate that MT5 date-only presets require parser-side exact clipping

Next operator actions:
1. Compile EA
2. Run MT5 tester
3. Copy tester outputs into `20_raw/`
4. Run `campaign-run-sealer`

Role boundary:
- `codex-writer-orchestrator`

## 2. mt5-preset-builder

Purpose: inspect or generate MT5 tester presets from campaign manifest parameters.

Usage modes:
- Run directory input: inspect `00_request/preset_snapshot.ini`, compare to manifest, flag bad date overrides
- Manifest input: extract `diagnostic_baseline_params`, `tester_baseline`, and window boundaries to build a preset

Critical rule:
- `source_preset_dates_are: oos` means explicit date overrides are required for benchmark or other windows

Role boundary:
- `codex-writer-orchestrator`

## 3. campaign-run-sealer

Purpose: seal raw backtest outputs and validate the sealed run.

Arguments:
- `run_dir`

Steps:
1. Run `python tools/run_campaign_backtest.py seal <run_dir>`
2. If seal succeeds, run `python tools/codex_hooks/post-seal-check.py <run_dir>`
3. Report:
   - `run_manifest.json`
   - `21_hash/raw_hash_manifest.json`
   - `21_hash/pack_hash_manifest.json`
   - validation verdict from `validator_report.json`

Role boundary:
- `codex-writer-orchestrator`
- Do not write independent validator output in this step

## 4. parser-replay

Purpose: rebuild the full parser pipeline on a sealed run with exact window clipping.

Arguments:
- `run_dir`

Steps:
1. Read `window_from` and `window_to` from `run_manifest.json`
2. Run `python tools/parse_step21_run.py <run_dir>/20_raw <run_dir>/30_parsed --window-from "<window_from>" --window-to "<window_to>"`
3. Run `python tools/build_master_tables.py <run_dir>/30_parsed`
4. Run `python tools/build_counterfactual_eval.py <run_dir>/30_parsed`
5. Run `python tools/build_daily_risk_metrics.py <run_dir>/30_parsed`
6. Report clipping stats, invariant status, decision type distribution, and headline KPIs

Role boundary:
- `parser-analytics`
- Read `20_raw/` only, write only `30_parsed/`

## 5. integrity-gate

Purpose: perform strict CP0-CP4 admissibility review after parser replay.

Arguments:
- `run_dir`

Steps:
1. Run `python tools/validate_campaign_run.py <run_dir> --require-parse`
2. Read `30_parsed/parse_manifest.json`
3. Read `30_parsed/coverage_manifest.json` if present
4. Report:
   - CP0 compile clean
   - CP1 runtime invariants
   - CP2 manifest window/data readiness
   - CP3 control-pack sealing
   - CP4 parser readiness and coverage

Role boundary:
- `parser-analytics` or `codex-validator`
- This step does not write `codex_validator_report.md`

## 6. codex-validator

Purpose: run the independent Codex validation pass on a frozen run bundle.

Arguments:
- `run_dir`

Required artifacts:
- `run_manifest.json`
- `21_hash/raw_hash_manifest.json`
- `21_hash/pack_hash_manifest.json`
- `30_parsed/parse_manifest.json`
- `50_validator/validator_report.json`

Review requirements:
- Raw and pack hash integrity
- Window boundary compliance
- Parse invariants and clipping integrity
- Trade lifecycle integrity
- Schema conformance

Output:
- Write a read-only validation memo to `50_validator/codex_validator_report.md`
- Use a final verdict of `APPROVED` or `HOLD`
- Include concrete blockers if `HOLD`

Role boundary:
- `codex-validator`
- Read sealed artifacts only
- Write only `50_validator/codex_validator_report.md`

## 7. kpi-branch-decision

Status: implemented.

Inputs:
- `run_manifest.json`
- `30_parsed/parse_manifest.json`
- `30_parsed/trades_master.parquet`
- `30_parsed/bars_master.parquet`
- `30_parsed/counterfactual_eval.parquet`
- `30_parsed/daily_risk_metrics.parquet`
- `50_validator/validator_report.json`

Steps:
1. Run `python tools/build_kpi_summary.py <run_dir>`
2. Review `40_kpi/kpi_summary.json`
3. Run `python tools/build_branch_decision_packet.py <run_dir>`
4. Review `60_decision/branch_decision_packet.json` and `.md`

Outputs:
- `40_kpi/kpi_summary.json`
- `60_decision/branch_decision_packet.json`
- `60_decision/branch_decision_packet.md`

Routing logic:
- admissibility blocker present -> `runtime-fix-first`
- both directional books weak and gate/exit pressure not dominant -> `ML-first`
- gate regret or exit opportunity dominates -> `EA-first`

Role boundary:
- `parser-analytics`

## 8. stage1-refresh-packet

Status: implemented.

Inputs:
- `runs/RUN_<ts>/40_kpi/kpi_summary.json`
- `runs/RUN_<ts>/60_decision/branch_decision_packet.json`
- campaign `manifest.yaml`
- accepted `STEP14` artifact directory

Steps:
1. Run `python tools/build_stage1_refresh_packet.py <run_dir>`
2. Review `reports/stage1_refresh_packet_<run_id>.json` and `.md`
3. Execute the emitted per-fold `step11_labeling.py` commands on the frozen optimization folds
4. Build the merged fold corpus with `python tools/build_step11_fold_union.py --output-dir <union_dir> <fold_dir>...`
5. Re-run `step12_training.py`, `step13_training.py`, and `step14_training.py` on the merged corpus

Outputs:
- `reports/stage1_refresh_packet_<run_id>.json`
- `reports/stage1_refresh_packet_<run_id>.md`

Purpose:
- freeze the WF5 Stage1 kickoff as a machine-readable Codex artifact
- make the current incumbent/OOS mismatch explicit before retraining
- emit concrete launch commands for fold-by-fold Step11 and merged fold union

Role boundary:
- `ml-trainer-exporter`

## 9. ml-export-parity

Status: not implemented.

Future dependencies:
- ONNX parity tool
- Python-side reference outputs
- MQL5-side inference outputs

Role boundary:
- `ml-trainer-exporter`

## 10. pack-hash-capture

Status: not implemented as a standalone tool.

Current state:
- pack hashing is performed inside `tools/run_campaign_backtest.py seal`

Role boundary:
- `ml-trainer-exporter`

## 11. rc-bundle-assembly

Status: not implemented. Requires `tools/bundle_rc.py`.

Future output:
- `_coord/releases/<rc_id>/`

Role boundary:
- `codex-gatekeeper`

## 12. rollback-bundle-verify

Status: not implemented. Requires `tools/bundle_rollback.py`.

Future output:
- rollback verification packet after restore rehearsal

Role boundary:
- `codex-gatekeeper`

## Hook Helpers

### post-seal-check
- Script: `python tools/codex_hooks/post-seal-check.py <run_dir>`
- Purpose: immediate post-seal validator run

### pre-promotion-guard
- Script: `python tools/codex_hooks/pre-promotion-guard.py <run_dir>`
- Purpose: promotion readiness gate on validator verdict, parse readiness, clipping match, and Codex validator memo presence

## Promotion Minimum

Before any release copy into `_coord/releases/`:
1. `validator_report.json` must be `PASS`
2. `parse_manifest.json` must show `pass=true`
3. `parse_manifest.json` must show `invariants_pass=true`
4. `window_clipping.window_from/window_to` must match `run_manifest.json`
5. `50_validator/codex_validator_report.md` must exist and be non-empty
6. `freeze/freeze_hash_manifest.json` must exist and show `role_overlap_pass=true`
7. `freeze/pack_parity_recheck.json` must exist and show `verdict=PASS`
