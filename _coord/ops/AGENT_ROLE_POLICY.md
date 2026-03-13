# Agent Role Policy — PROJECT_triple_sigma

> Version: 1.0
> Created: 2026-03-12
> Basis: GPT Pro Audit Report (2026-03-12) Section 8
> Finding: F6 (Independent validator absent)
> Status: Phase A deliverable (A0)

---

## 1. Role Definitions

### 1.1 codex-writer-orchestrator

| Attribute | Detail |
|-----------|--------|
| Authority | Modify repo code, manifests, scripts, documentation |
| Prohibition | Cannot approve promotion of own outputs |
| Outputs | code diff, candidate spec, runner changes, docs update |
| Scope | Full repo write access within campaign workspace |

### 1.2 mt5-operator

| Attribute | Detail |
|-----------|--------|
| Authority | Compile, tester run, raw output capture |
| Prohibition | Code modification, gate override |
| Outputs | compile log, raw outputs, preset snapshot, run manifest |
| Scope | MT5 terminal + `runs/RUN_<ts>/10_compile/`, `20_raw/` write |

### 1.3 parser-analytics

| Attribute | Detail |
|-----------|--------|
| Authority | Raw outputs read-only, parser/KPI outputs write |
| Prohibition | Raw CSV rewrite |
| Outputs | parse_manifest.json, coverage_manifest.json, master tables, kpi_summary.json |
| Scope | `runs/RUN_<ts>/20_raw/` read, `30_parsed/`, `40_kpi/` write |

### 1.4 ml-trainer-exporter

| Attribute | Detail |
|-----------|--------|
| Authority | Step14/15 retrain, ONNX export, pack rebuild |
| Prohibition | RC promotion |
| Outputs | validation reports, export validation report, pack hash manifest |
| Scope | `src/ml/` write, pack directory write, `21_hash/pack_hash_manifest.json` write |

### 1.5 codex-validator (separate Codex validation thread)

| Attribute | Detail |
|-----------|--------|
| Authority | Frozen evidence bundle read-only |
| Prohibition | Source code write, operator config change |
| Outputs | `codex_validator_report.md`, `validator_signature.json` |
| Scope | `runs/RUN_<ts>/` read-only, `50_validator/` write |
| Implementation | Separate Codex thread/session with frozen evidence bundle only |

### 1.6 codex-gatekeeper

| Attribute | Detail |
|-----------|--------|
| Authority | RC/RB bundle validation, promote/reject decision record |
| Prohibition | Code edit, candidate generation |
| Outputs | promotion_decision.json |
| Scope | `runs/RUN_<ts>/50_validator/` read, `60_decision/` write, `_coord/releases/` write |

### 1.7 human-principal

| Attribute | Detail |
|-----------|--------|
| Authority | Explicit override, waiver, kill-switch reset |
| Prohibition | Undocumented verbal waiver |
| Outputs | override_record.yaml |
| Scope | All directories; override requires retained evidence |

---

## 2. No-Self-Promotion Rule

This is the foundational governance constraint for the agent topology.

1. **Writer proposes only** — `codex-writer-orchestrator` can create candidates but cannot approve them for promotion.
2. **Validator re-verifies** — `codex-validator` checks writer outputs against frozen evidence only. No live code access.
3. **Gatekeeper releases** — `codex-gatekeeper` passes WF8/WF9 only when machine validator evidence and Codex validator evidence both clear.
4. **Human override** — permitted but must be retained in `override_record.yaml` with justification and timestamp.

**Prohibited path:** `codex-writer-orchestrator` approving its own candidate in the same thread/session → always rejected.

---

## 3. Artifact Retention Template

Every campaign run produces the following directory structure:

```
_coord/campaigns/<campaign_id>/runs/RUN_<UTCSTAMP>/
  00_request/    — candidate spec, operator config, preset_snapshot.ini
  10_compile/    — compile_log.txt, terminal build info
  20_raw/        — immutable raw tester outputs (trade_log.csv, bar_log_*.csv, exec_state.ini)
  21_hash/       — raw_hash_manifest.json, pack_hash_manifest.json
  30_parsed/     — parser outputs (master tables, parse_manifest.json, coverage_manifest.json)
  40_kpi/        — kpi_summary.json, branch_decision_packet.json
  50_validator/  — validator_report.json, codex_validator_report.md, validator_signature.json
  60_decision/   — pass/fail decision, override_record.yaml (if applicable)
```

### Immutability rules
- `20_raw/` is **write-once**: sealed immediately after tester run via `raw_hash_manifest.json`
- `21_hash/` manifests are sealed and never modified after creation
- Selected candidates promoted to `_coord/releases/<rc_id>/` and `_coord/rollback_points/<rb_id>/`

---

## 4. Escalation Paths

| Trigger | Escalation |
|---------|-----------|
| Operator infra failure | mt5-operator retry budget → codex-writer-orchestrator + human |
| Integrity failure | Immediate: codex-validator + human, optimization halted |
| Writer/validator disagreement | human-principal arbitration |
| Promotion failure | codex-gatekeeper reject → writer revision → new candidate re-entry |

---

## 5. Contract Validation Layer

Required schema validators (repo-resident):

| Schema | Phase | Status |
|--------|-------|--------|
| campaign_run_manifest.schema.json | A (S1) | Complete |
| raw_hash_manifest.schema.json | A (S2) | Complete |
| pack_hash_manifest.schema.json | A (S3) | Complete |
| kpi_summary.schema.json | C (S4) | Deferred |
| rc_manifest.schema.json | C (S5) | Deferred |
| rollback_manifest.schema.json | C (S6) | Deferred |
| parse_manifest semantic validator | A | Existing (parse_step21_run.py) |
| coverage_manifest semantic validator | A | Existing (build_counterfactual_eval.py) |

---

## 6. Future Infrastructure (Phase B+)

### 6.1 Codex Playbook Workflows

Active workflow definitions live in:
- `AGENTS.md`
- `_coord/ops/CODEX_PHASE_B_PLUS_PLAYBOOK.md`

Phase B+ workflows:
1. **campaign-bootstrap** — initialize campaign workspace from manifest
2. **mt5-preset-builder** — generate or inspect tester presets
3. **campaign-run-sealer** — seal raw outputs + hash manifests
4. **parser-replay** — re-run parser pipeline on sealed run
5. **integrity-gate** — CP0-CP4 strict validation
6. **codex-validator** — independent read-only evidence review
7. **kpi-branch-decision** — compute KPIs and route to branch
8. **ml-export-parity** — verify ONNX export matches training
9. **pack-hash-capture** — seal external pack payload
10. **rc-bundle-assembly** — assemble release candidate bundle
11. **rollback-bundle-verify** — verify rollback point integrity

### 6.2 Codex Hook Helpers (`tools/codex_hooks/`)

5-stage hook pipeline:

**pre-run**
- Freeze manifest schema check
- Control-pack separation check
- External pack hash capture presence check

**post-run**
- Raw file completeness
- Raw hash sealing
- Compile/tester log copy
- Single-run contamination detection

**post-parse**
- CP1/CP4 strict validator
- Coverage gate
- KPI summary build

**pre-promotion**
- CP0-CP8 aggregate validator
- RC/RB bundle presence
- Dual-signature check

**post-rollback**
- CP0/CP1 rerun
- Restore verification packet write

### 6.3 MCP Integration Points

7 integration points for tooling:

1. **github MCP** — issues, PR, commit metadata, artifact links
2. **shell/filesystem MCP** — runner execution, hash sealing
3. **mt5-runner MCP** — compile/test backtest control
4. **parquet-json MCP** — parser outputs inspection
5. **onnx-inspector MCP** — pack contents, shape, hash verification
6. **thread-bridge MCP** — Codex writer <> Codex validator packet exchange
7. **signing/hash MCP** — SHA-256 + optional signature sealing

---

## 7. Quantitative Acceptance Criteria Reference

Full thresholds are defined in the Audit Report Section 10. Key gates for `codex-validator` and `codex-gatekeeper`:

### Hard Gates (zero tolerance)
- duplicate EXIT = 0
- same-ts EXIT->ENTRY = 0
- close-before-modify overlap = 0
- unmapped ENTRY/EXIT/MODIFY = 0
- unresolved NO_EXIT = 0

### Performance Thresholds
- Benchmark PF >= 1.15, OOS PF >= 1.05, Combined PF >= 1.10
- Benchmark expectancy >= +0.05R, OOS >= +0.02R
- Benchmark max DD <= 8%, OOS <= 10%, Stress <= 12%
- Worst regime PF (n>=30) >= 0.90
- Regime PnL HHI <= 0.30
- OOS profitable months >= 60%
- OOS PF / Benchmark PF >= 0.75

See Audit Report Section 10.1-10.13 for complete specification.
