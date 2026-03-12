# PROJECT_triple_sigma

## Architecture
- **EA**: `src/ea/TripleSigma.mq5` + 13 headers `src/include/TS_*.mqh` (MQL5, US100 M5)
- **ML pipeline**: `src/ml/` (step11-15, ONNX export, 2-stage classifier+regressor)
- **Parser pipeline**: `tools/parse_step21_run.py` -> `build_master_tables.py` -> `build_counterfactual_eval.py` -> `build_daily_risk_metrics.py`
- **Campaign runner**: `tools/run_campaign_backtest.py` (prepare + seal)
- **Validator**: `tools/validate_campaign_run.py` (9-gate)
- **Campaign workspace**: `_coord/campaigns/C2026Q1_stage1_refresh/`
- **Ops docs**: `_coord/ops/`

## Agent Role Policy
See `_coord/ops/AGENT_ROLE_POLICY.md` for 7 roles: writer-orchestrator, mt5-operator, parser-analytics, ml-trainer-exporter, independent-validator, release-gatekeeper, human-principal.

**No-self-promotion rule**: Writer proposes, cannot approve own output. Validator (Codex thread) re-verifies against frozen evidence only. Gatekeeper releases only when writer + validator manifests match.

## Campaign Run Structure
```
runs/RUN_<ts>/
  00_request/    preset_snapshot.ini, request_meta.json
  10_compile/    compile_log.txt
  20_raw/        immutable raw tester outputs (sealed)
  21_hash/       raw_hash_manifest.json, pack_hash_manifest.json
  30_parsed/     parquet files + parse_manifest.json
  40_kpi/        kpi_summary.json (future)
  50_validator/  validator_report.json (independent-validator only)
  60_decision/   promotion_decision.json (gatekeeper only)
```

## Key Rules
1. `20_raw/` is immutable after seal — never modify
2. Window clipping at parser level (A' policy) — see MASTER_TABLE_CONTRACT.md v2.1
3. Codex validator = `codex exec --full-auto -m gpt-5.4` (OPENAI_API_KEY in env)
4. One optimization layer at a time (OPTIMIZATION_OPERATOR_RUNBOOK.md)
5. Do not optimize on Step16 smoke pack

## Current Phase
- Phase A: DONE (tool pipeline)
- Phase B: DONE (first admissible run RUN_20260312T115832Z)
- Phase B+: IN PROGRESS (agent infrastructure)
- Next: WF4 direction decision -> WF5 optimization

## User
Korean speaker. Prefers concise responses. Claude+Codex collaborative workflow.
