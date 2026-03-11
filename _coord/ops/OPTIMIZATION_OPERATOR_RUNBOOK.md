# Optimization Operator Runbook

Status:
- Step21 runtime integrity is code-complete and verified.
- This runbook governs the optimization phase that follows.

Source of truth:
- Current Step21 code + retained artifacts + logs + current docs.
- `_coord/ops/control_pack_registry.yaml` for pack governance.
- `_coord/campaigns/*/manifest.yaml` for campaign definitions.
- `_coord/ops/MASTER_TABLE_CONTRACT.md` for derived-table schema.

## Non-negotiable rules

1. Do not optimize profitability on the Step16 smoke pack.
2. Do not use the long-range generated-tick history (2018-05-08 ~ 2026-03-06)
   as primary optimization or Model=4 comparison range.
3. Runtime invariants must pass before and after every optimization step:
   - duplicate non-modify `(trade_id, event_type)` groups = 0
   - duplicate EXIT groups = 0
   - same-timestamp EXIT -> ENTRY = 0
   - feature-off core-row alignment = true
4. One optimization layer at a time. Do not open joint sweeps until
   single-layer attribution is established.
5. Each campaign run must produce a `parse_manifest.json` that passes
   schema validation against the master table contract.

## WF0: Data freeze

Inputs:
- `design/US100_RealTick_Backtest_Data_Policy.md`
- US100 history quality audit

Actions:
1. Confirm data windows in campaign `manifest.yaml`.
2. Verify no overlap between optimization folds and OOS window.
3. Document any new gaps or quality issues in `freeze/` directory.

Output: `freeze/data_freeze_manifest.yaml`

Pass condition: no role overlap between windows.

## WF1: Control-pack selection

Inputs:
- `_coord/ops/control_pack_registry.yaml`
- `_coord/artifacts/step15_export_q1_out/export_validation_report.json`

Actions:
1. Confirm runtime integrity pack is `triple_sigma_pack_long_step16`.
2. Confirm profitability pack is `triple_sigma_pack_step15_q1`.
3. Verify parity evidence is present and all acceptance criteria pass.

Output: confirmed `control_pack_registry.yaml`

Pass condition: dual-control separation is explicit with evidence.

## WF2: Backtest execution

Inputs:
- Campaign `manifest.yaml`
- Step21 tester preset templates
- Selected data window and pack

Actions:
1. Build campaign-specific `.ini` preset from Step21 template.
   - Set `InpModelPackDir` to profitability pack.
   - Set `FromDate` / `ToDate` from campaign window.
   - Set `Report` path to `raw_tester_outputs/` directory.
2. Run backtest via MT5 Strategy Tester.
3. Collect outputs: `trade_log.csv`, `bar_log_*.csv`, `exec_state.ini`.
4. Copy raw outputs to `raw_tester_outputs/` immutably.

Output: raw tester results in `raw_tester_outputs/`

Pass condition: compile clean, raw-output files complete.

## WF3: Parsing and analytics

Inputs:
- Raw tester outputs from WF2
- `MASTER_TABLE_CONTRACT.md`

Actions:
1. Run `tools/parse_step21_run.py` on raw outputs.
2. Run `tools/build_master_tables.py` to materialize derived tables.
3. Run `tools/build_counterfactual_eval.py` for H=72 evaluation.
4. Run `tools/build_daily_risk_metrics.py` for daily KPIs.
5. Validate outputs against master table contract.

Output: derived tables in `parser_outputs/`, `parse_manifest.json`

Pass condition: schema sanity pass, validation invariants hold.

## WF4: Branch decision

Inputs:
- Parsed analytics from WF3
- Decision matrix (below)

Actions:
1. Evaluate KPIs across ML signal, EA policy, execution, and risk layers.
2. Choose exactly one primary branch: ML-first, EA-first, or runtime-fix-first.

Decision matrix:

| Observed symptom | Primary layer | Action |
|------------------|---------------|--------|
| Low Stage1 margin, short-side collapse | ML | Stage1 data expansion + recalibration |
| High Stage2 regret, hold-boundary pressure | ML | Stage2 search space retune |
| Good signal, high gate regret | EA policy | Relax or condition gates |
| Early-exit cost > risk saved | EA policy | Soften thresholds |
| Protective modify destroys more alpha than saves | EA policy | Raise triggers, regime-selective |
| Rising retcodes / authority disagreement | Execution | Stop profitability work, fix runtime |
| Dup EXIT / phantom EXIT / core-row drift | Runtime | Mandatory stop, rebuild anchors |

Output: documented decision with rationale in `reports/`

Pass condition: exactly one primary branch opened.

## WF5: Branch optimization

### ML-first order:
1. Data: window freeze, quality audit, auxiliary data assessment.
2. Stage1: expand training data, try new architectures, recalibrate.
   - Guardrail: `min_cand0_pass_recall >= 0.5` (current threshold).
   - Do not open EA search while Stage1 is unstable.
3. Stage2: retune search space if Stage2 regret is high.
   - Delay if Stage1 is still being revised.

### EA-first order:
1. Gates: relax `InpPMinTrade`, `InpSpreadAtrMaxBase`, `InpSpreadAtrMaxHard`.
2. Early exit: tune `InpPExitPass`, `InpMinHoldBarsBeforeExit`.
3. Protective modify: enable and tune break-even, trailing, TP reshape,
   time policy thresholds.
4. Risk sizing: adjust `InpRiskPctBase` and bounds.

Pass condition: layer-specific improvement without OOS damage.

## WF6: Benchmark / OOS / stress restage

Actions:
1. Rerun a small incumbent set on benchmark, OOS, and stress windows.
2. Compare against diagnostic baseline.

Pass condition: acceptable dispersion and concentration across windows.

## WF7: Limited joint sweep

Actions:
1. Evaluate a small interaction matrix only after single-layer work is done.
2. Test ML x EA gate interactions, exit x modify interactions.

Pass condition: no fragile single-interaction dependence.

## WF8: Release candidate

Actions:
1. Package selected pack, EA parameters, KPI snapshot, and this runbook.
2. Record file hashes for reproducibility.
3. Store in `_coord/releases/`.

Output: RC bundle in `_coord/releases/`

Pass condition: reproducibility verified, handoff complete.

## WF9: Rollback point

Actions:
1. Package previous stable state (pack + params + evidence).
2. Verify runtime patch inputs are retained.
3. Record hashes.
4. Store in `_coord/rollback_points/`.

Output: rollback bundle in `_coord/rollback_points/`

Pass condition: patch-input retention and hash verification.

## Operating checkpoints

Run these gates before proceeding to the next workflow stage:

- CP0: compile clean, Step21 schema consistent
- CP1: runtime invariants pass (dup=0, core-row match=true)
- CP2: data windows frozen, gap policy documented
- CP3: dual control separated, parity evidence present
- CP4: parser pipeline builds and validates successfully
- CP5: ML split leakage-free, Stage1 guardrails in place
- CP6: gate regret, exit trade-off, modify trade-off measurable
- CP7: benchmark/OOS/stress all pass without fatal runtime anomaly
- CP8: RC reproducible, rollback bundle complete

## Mandatory stop conditions

Stop all optimization immediately if:
- Duplicate EXIT groups > 0
- Same-timestamp EXIT -> ENTRY > 0
- Feature-off core-row alignment breaks
- Runtime reload evidence exists but patch inputs are missing
- Retcode anomalies or authority disagreement rise

After mandatory stop:
1. Return to runtime integrity investigation.
2. Do not resume optimization until invariants are restored.
3. Document the incident in `reports/`.

## KPI reference

### ML signal layer
- Macro-F1 by regime
- PASS recall (Stage1 abstention discipline)
- Calibration log loss / Brier score
- Margin-decile monotonicity
- SHORT coverage ratio
- Stage2 parameter regret
- Posterior drift PSI

### EA policy layer
- Candidate conversion rate (eligible alpha -> actual entries)
- Gate block rate by reason
- Gate regret (blocked profitable setups)
- Early-exit opportunity cost vs risk saved
- Protective-modify save ratio vs alpha-loss ratio
- Hold utilization / force-exit share

### Execution layer
- Retcode executed share
- Pending clear latency
- Synthetic vs actual reject rate
- Duplicate / phantom EXIT count
- Observer / authority disagreement

### Portfolio / risk layer
- Expectancy R
- Profit factor / payoff ratio
- MAE / MFE capture ratio
- Drawdown / ulcer profile
- Concentration and window dispersion
- Rolling stability
