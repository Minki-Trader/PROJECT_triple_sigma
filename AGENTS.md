# PROJECT_triple_sigma

## Codex-Only Phase B+
- Phase B+ agent orchestration is Codex-only.
- Do not use Claude workflows, `.claude/`, or `CLAUDE.md` as active operating assets.
- Use [_coord/ops/AGENT_ROLE_POLICY.md](C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\ops\AGENT_ROLE_POLICY.md) for role boundaries.
- Use [_coord/ops/CODEX_PHASE_B_PLUS_PLAYBOOK.md](C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\ops\CODEX_PHASE_B_PLUS_PLAYBOOK.md) for Phase B+ workflows.

## Architecture
- EA: `src/ea/TripleSigma.mq5`
- Parser pipeline: `tools/parse_step21_run.py` -> `tools/build_master_tables.py` -> `tools/build_counterfactual_eval.py` -> `tools/build_daily_risk_metrics.py`
- Campaign runner: `tools/run_campaign_backtest.py`
- Campaign validator: `tools/validate_campaign_run.py`
- Codex hook helpers: `tools/codex_hooks/post-seal-check.py`, `tools/codex_hooks/pre-promotion-guard.py`

## Active Codex Roles
- `codex-writer-orchestrator`: repo changes, runner changes, tool changes, documentation changes
- `codex-validator`: frozen evidence review only, writes only to `50_validator/`
- `codex-gatekeeper`: promotion and rollback gating, writes only to `60_decision/` and bundle directories
- `human-principal`: explicit override only

## Hard Rules
1. `20_raw/` is immutable after seal.
2. `21_hash/` manifests are immutable after seal.
3. Promotion requires:
   - `python tools/validate_campaign_run.py <run_dir> --require-parse`
   - `python tools/codex_hooks/pre-promotion-guard.py <run_dir>`
4. Independent validation evidence must exist in `50_validator/codex_validator_report.md` before promotion.
5. Do not let the same Codex role both generate and approve a release candidate in one pass.

## Workflow Triggers
- Bootstrap or preset generation: open the `campaign-bootstrap` or `mt5-preset-builder` section in [_coord/ops/CODEX_PHASE_B_PLUS_PLAYBOOK.md](C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\ops\CODEX_PHASE_B_PLUS_PLAYBOOK.md)
- Seal or post-seal validation: use `campaign-run-sealer` and `tools/codex_hooks/post-seal-check.py`
- Parse, master, counterfactual, risk rebuild: use `parser-replay`
- Strict admissibility review: use `integrity-gate`
- Independent validation: use `codex-validator`
- Branch decision and release skeleton work: use the matching sections in the playbook and respect status markers for not-yet-implemented tooling
