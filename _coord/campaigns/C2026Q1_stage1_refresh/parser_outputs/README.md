# Retained Artifact Replay Archive

This directory contains parser outputs from a retained artifact replay (non-admissible).

- Source: `_coord/artifacts/step21_live_trailing_probe` (Step21 smoke test, NOT campaign-native)
- Pack: `triple_sigma_pack_long_step16` (runtime integrity pack, NOT profitability pack)
- Status: **NON-ADMISSIBLE** for optimization decisions

Admissible campaign runs use the `runs/RUN_<ts>/` structure. See:
- `tools/run_campaign_backtest.py` for creating admissible runs
- `tools/validate_campaign_run.py` for validating admissibility
- `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md` WF2/WF3 for the full workflow
