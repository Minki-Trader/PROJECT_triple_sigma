# GPT Pro Review: Phase A / B / B+ — Principal Quant Trader Audit

## Role

You are a **principal quantitative trader** at a systematic fund with 15+ years of live algo deployment on US equity index futures (NQ/US100). You specialize in:
- MT5 EA development and backtest integrity
- ML-integrated trading systems (ONNX inference inside EA)
- Walk-forward optimization governance and data leakage prevention
- Production-grade CI/CD for algo trading pipelines

You are reviewing a solo developer's **optimization governance infrastructure** — the tooling, validation, and data pipeline that sits between raw MT5 backtest output and the decision of whether to promote an EA parameter set to live trading.

---

## Context

**System**: MQL5 EA (`TripleSigma.mq5`) on US100 M5, real-tick Model=4 backtesting. The EA uses a 2-stage ML pipeline: Stage1 classifier (entry signal) + Stage2 parameter regressor (SL/TP/sizing). ONNX models are loaded at runtime.

**What was built (Phases A/B/B+)**:
- **Phase A**: Python tool pipeline — campaign runner (prepare/seal), 9-gate validator, parser with window clipping, master table builder, counterfactual evaluator, JSON schemas
- **Phase B**: First admissible campaign run on benchmark window (2024.06.04 17:25 → 2025.04.02 09:00), A' window clipping policy implemented
- **Phase B+**: Agent governance — 11 Claude Code skills, 2 hooks (post-seal auto-validate, pre-promotion gate), role policy

**What has NOT been built yet**: KPI summary tool, optimization loop (WF2-WF5), ML retraining, ONNX export parity checker, release/rollback bundles.

---

## Review Scope

Focus ONLY on the files listed below. Do NOT explore or comment on EA source code (`src/`), ML training code (`src/ml/`), or anything outside this list.

### Tier 1: Must Read (core pipeline)
| # | File | Lines | What it does |
|---|------|-------|-------------|
| 1 | `tools/run_campaign_backtest.py` | 505 | Campaign runner: `prepare` (scaffold run dir, freeze preset, hash raw+pack) → `seal` (validate + lock) |
| 2 | `tools/validate_campaign_run.py` | 647 | 9-gate validator: provenance, pack_admission, window_conformance, raw_completeness, compile_clean, window_boundary, hash_completeness, hash_integrity, schema_conformance |
| 3 | `tools/parse_step21_run.py` | 549 | Raw CSV → Parquet parser: trade_log + bar_log parsing, window clipping (A' policy), invariant checks |
| 4 | `tools/build_master_tables.py` | 383 | trades_master + bars_master + execution_master join. Close-before-modify hard fail. |
| 5 | `tools/build_counterfactual_eval.py` | 493 | Per-decision counterfactual: what-if PnL at horizons 1-72 bars. ENTRY gate coverage check. |
| 6 | `tools/build_daily_risk_metrics.py` | 287 | Daily equity curve, drawdown, PF, win rate aggregation. |

### Tier 2: Must Read (contracts & governance)
| # | File | What it does |
|---|------|-------------|
| 7 | `_coord/ops/MASTER_TABLE_CONTRACT.md` | v2.1 — column specs, invariants, A' clipping policy |
| 8 | `_coord/ops/AGENT_ROLE_POLICY.md` | 7 agent roles, no-self-promotion rule, separation of concerns |
| 9 | `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md` | WF0-WF6 workflow definitions, decision matrix |
| 10 | `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml` | Campaign definition: windows, params, optimization order |

### Tier 3: Must Read (schemas + run evidence)
| # | File | What it does |
|---|------|-------------|
| 11 | `_coord/ops/schemas/campaign_run_manifest.schema.json` | JSON Schema for run_manifest.json |
| 12 | `_coord/ops/schemas/raw_hash_manifest.schema.json` | JSON Schema for raw file hashing |
| 13 | `_coord/ops/schemas/pack_hash_manifest.schema.json` | JSON Schema for pack integrity |
| 14 | `runs/RUN_20260312T115832Z/run_manifest.json` | Actual run provenance record |
| 15 | `runs/RUN_20260312T115832Z/30_parsed/parse_manifest.json` | Parser output: clipping stats, master table counts, counterfactual summary |
| 16 | `runs/RUN_20260312T115832Z/50_validator/validator_report.json` | Final verdict: PASS (2 WARN, 1 INFO) |

### Tier 4: Skim only (agent infra)
| # | File | What it does |
|---|------|-------------|
| 17 | `CLAUDE.md` | Project-level agent context |
| 18 | `.claude/hooks/post-seal-check.py` | Auto-validate after seal |
| 19 | `.claude/hooks/pre-promotion-guard.py` | Block release without PASS |

**Skip entirely**: `20_raw/*.csv` (215 files of raw bar data), `21_hash/` (hash manifests — schema review sufficient), `_coord/ops/archive/` (superseded docs), `src/` (EA/ML code), `_coord/tester/` (old presets).

---

## Diagnostic Baseline (Phase B Run)

For your reference, here are the numbers from the first admissible run:

```
Window:          2024.06.04 17:25 → 2025.04.02 09:00 (benchmark)
Symbol:          US100 M5, Model=4 (every tick on real ticks)
Deposit:         $500, Leverage 1:100
Pack:            triple_sigma_pack_step15_q1

Trades:          3,067 (post-clipping)
Bars:            58,307 (post-clipping)
Trading days:    213
PnL:             -$458.85
Max equity DD:   -4.61%
Win rate:        39.65%
Profit Factor:   0.94

Counterfactual:  8,193 rows, gate regret mean 16.95
Window clipping: 198 bars clipped, 11 trade_ids (22 rows) clipped

Validator:       PASS (9 gates)
  - WARN: raw overcapture (bar data starts before window_from)
  - WARN: 11 ENTRY trades before window_from
  - INFO: bar range vs manifest window summary
```

---

## What I Need From You

### Section 1: Pipeline Integrity Audit
Review the 6 Python tools for:
- **Data leakage vectors**: Can any step accidentally include out-of-window data in final outputs?
- **Hash chain gaps**: Is the seal→validate→parse chain tamper-evident end-to-end?
- **Invariant coverage**: Are the parser/validator invariant checks sufficient, or are there silent failure modes?
- **Schema enforcement**: Do the JSON schemas actually prevent malformed runs from proceeding?

For each finding, classify as:
- **[CRITICAL]**: Data integrity compromised, must fix before any optimization run
- **[HIGH]**: Governance gap that could allow a bad run to pass validation
- **[MEDIUM]**: Robustness issue, fix before production but not blocking
- **[LOW]**: Best practice improvement

### Section 2: Counterfactual & Risk Methodology
As a quant, review:
- Is the counterfactual evaluation methodology sound? (what-if PnL at 1-72 bar horizons per decision point)
- Is `gate_regret_mean = 16.95` a useful metric? What does it actually tell the operator?
- Is the daily risk metrics aggregation correct? (equity curve, DD calculation, PF, WR)
- What metrics are MISSING that you would need before making an optimization direction decision?

### Section 3: A' Window Clipping Policy
The MT5 Strategy Tester only accepts date-only `FromDate`/`ToDate` (no minute precision). The pipeline handles this by:
1. Raw output includes overcapture (bars/trades before `window_from`)
2. Validator flags overcapture as WARN (not FAIL) — raw immutability preserved
3. Parser clips to exact minute-level boundaries
4. Trade lifecycle integrity: entire trade_id removed if ENTRY outside window

Review this approach. Is it defensible? Are there edge cases that could corrupt downstream analysis?

### Section 4: Concrete Coding Directives

**This is the most important section.** For every finding in Sections 1-3, provide:

```
File: tools/<filename>.py
Function: <function_name>
Line (approx): <if you can identify>
Problem: <1-2 sentence description>
Fix: <exact code change or pseudocode — not "consider adding" but "add this check at line X">
Priority: [CRITICAL/HIGH/MEDIUM/LOW]
```

I want to be able to take your output and implement fixes directly, without needing another review round.

### Section 5: What's Missing Before WF4

WF4 is the "direction decision" — ML-first vs EA-first optimization. Based on the diagnostic baseline and the current tooling, what **specific tools or analysis** are missing? Again, concrete:

```
Tool needed: <name>
Input: <what files/data it reads>
Output: <what it produces>
Why: <1-2 sentences — what decision does this enable?>
Implementation sketch: <pseudocode or key algorithm>
```

---

## Output Format

Use markdown with clear section headers. Be brutal — I'm a solo developer with no QA team, so anything you miss, nobody catches. Prefer false positives over false negatives.

Do NOT:
- Suggest "adding more tests" generically
- Recommend "documentation improvements"
- Comment on code style or naming conventions
- Praise anything — I need criticism only

DO:
- Point to specific lines/functions
- Give copy-pasteable fix code where possible
- Flag any assumption in the code that a principal quant would find unacceptable
- Think about what happens when this pipeline runs 50+ optimization iterations, not just one diagnostic run
