# GPT Pro Review: Phase A / B / B+ — Principal Quant Trader Audit

## 역할

당신은 미국 주가지수 선물(NQ/US100) 라이브 알고리즘 운용 경력 15년 이상의 **principal quantitative trader**입니다. 전문 분야는 다음과 같습니다.

- MT5 EA 개발 및 백테스트 무결성 검증
- EA 내부 ONNX 추론을 포함한 ML 결합형 트레이딩 시스템
- Walk-forward optimization 거버넌스 및 데이터 누수 방지
- 알고리즘 트레이딩 파이프라인의 production-grade CI/CD

당신의 검토 대상은 한 명의 개발자가 구축한 **optimization governance infrastructure**입니다. 즉, MT5 raw backtest output과 EA 파라미터 세트의 live promotion 결정 사이에 위치한 tooling, validation, data pipeline 전체입니다.

---

## 컨텍스트

**시스템**: MQL5 EA (`TripleSigma.mq5`)가 US100 M5에서 동작하며, real-tick `Model=4` 백테스트를 사용합니다. EA는 2-stage ML pipeline을 사용합니다.

- Stage1 classifier: entry signal 생성
- Stage2 regressor: SL / TP / sizing 산출
- ONNX 모델은 런타임에 로드됨

**이미 구현된 범위 (Phase A / B / B+)**

- **Phase A**: Python tool pipeline
  - campaign runner (`prepare` / `seal`)
  - 9-gate validator
  - window clipping parser
  - master table builder
  - counterfactual evaluator
  - JSON schemas
- **Phase B**: benchmark window에 대한 첫 admissible campaign run
  - benchmark window: `2024-06-04 17:25 -> 2025-04-02 09:00`
  - A' window clipping policy 적용
- **Phase B+**: agent governance
  - Claude Code skills 11개
  - hooks 2개 (`post-seal`, `pre-promotion`)
  - role policy

**아직 구현되지 않은 것**

- KPI summary tool
- optimization loop (WF2-WF5)
- ML retraining
- ONNX export parity checker
- release / rollback bundles

---

## 검토 범위

아래에 나열된 파일만 검토 대상으로 삼으세요. 다만, **나열된 파일의 동작을 해석하기 위해 직접 필요한 의존 파일은 예외적으로 읽을 수 있으며**, 그 경우 응답에서 어떤 파일을 추가로 읽었는지 명시하세요.

다음 항목은 검토하거나 코멘트하지 마세요.

- EA source code (`src/`)
- ML training code (`src/ml/`)
- `_coord/tester/`
- `_coord/ops/archive/`
- raw CSV 전체 덤프를 훑는 광범위한 탐색

**중요**

- 이 프롬프트의 설명과 저장소 실증(evidence)이 충돌하면, **프롬프트가 아니라 저장소 실증을 신뢰**하고 그 충돌을 명시적으로 지적하세요.
- 확인된 문제와 추정 리스크를 구분하세요.
  - `Confirmed`: 검토 범위 내 파일/산출물로 직접 입증된 문제
  - `Suspected`: 합리적 리스크이지만 현재 스코프 내에서 완전 입증되지는 않은 문제

### Tier 1: 필독 (핵심 파이프라인)

| # | 파일 | 설명 |
|---|------|------|
| 1 | `tools/run_campaign_backtest.py` | campaign runner: `prepare`(run dir scaffold, preset freeze, raw+pack hash) -> `seal`(validate + lock) |
| 2 | `tools/validate_campaign_run.py` | 9-gate validator: provenance, pack_admission, window_conformance, raw_completeness, compile_clean, window_boundary, hash_completeness, hash_integrity, schema_conformance |
| 3 | `tools/parse_step21_run.py` | raw CSV -> Parquet parser: trade_log + bar_log parsing, A' window clipping, invariant checks |
| 4 | `tools/build_master_tables.py` | trades_master + bars_master + execution_master join, close-before-modify 검증 |
| 5 | `tools/build_counterfactual_eval.py` | per-decision counterfactual: 1-72 bar horizon what-if PnL, ENTRY gate coverage check |
| 6 | `tools/build_daily_risk_metrics.py` | daily equity curve, drawdown, PF, WR 집계 |

### Tier 2: 필독 (계약 및 거버넌스)

| # | 파일 | 설명 |
|---|------|------|
| 7 | `_coord/ops/MASTER_TABLE_CONTRACT.md` | v2.1 column specs, invariants, A' clipping policy |
| 8 | `_coord/ops/AGENT_ROLE_POLICY.md` | 7 agent roles, no-self-promotion rule, separation of concerns |
| 9 | `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md` | WF0-WF6 workflow, decision matrix |
| 10 | `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml` | campaign definition: windows, params, optimization order |

### Tier 3: 필독 (schema + 실행 증적)

| # | 파일 | 설명 |
|---|------|------|
| 11 | `_coord/ops/schemas/campaign_run_manifest.schema.json` | `run_manifest.json` schema |
| 12 | `_coord/ops/schemas/raw_hash_manifest.schema.json` | raw file hashing schema |
| 13 | `_coord/ops/schemas/pack_hash_manifest.schema.json` | pack integrity schema |
| 14 | `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z/run_manifest.json` | 실제 run provenance record |
| 15 | `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z/21_hash/raw_hash_manifest.json` | 실제 raw hash evidence |
| 16 | `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z/21_hash/pack_hash_manifest.json` | 실제 pack hash evidence |
| 17 | `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z/30_parsed/parse_manifest.json` | parser output: clipping stats, master table counts, counterfactual summary |
| 18 | `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_20260312T115832Z/50_validator/validator_report.json` | final verdict: PASS (2 WARN, 1 INFO) |

### Tier 4: 가볍게 확인 (agent infra)

| # | 파일 | 설명 |
|---|------|------|
| 19 | `CLAUDE.md` | project-level agent context |
| 20 | `.claude/hooks/post-seal-check.py` | auto-validate after seal |
| 21 | `.claude/hooks/pre-promotion-guard.py` | PASS 없으면 release 차단 |

### 완전 스킵

- `20_raw/*.csv` 전체 내용을 대량으로 읽는 행위
- `src/`
- `src/ml/`
- `_coord/tester/`
- `_coord/ops/archive/`

참고: 실제 hash chain 검토를 위해 **해당 run의 `21_hash/*.json` 두 파일은 읽어도 됩니다**. 다만 raw CSV 본문 전체를 수동 검토 대상으로 삼지는 마세요.

---

## Diagnostic Baseline (Phase B Run)

다음은 첫 admissible run의 기준 수치입니다.

```text
Window:          2024.06.04 17:25 -> 2025.04.02 09:00 (benchmark)
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

## 내가 원하는 결과

### Section 1: Pipeline Integrity Audit

6개의 Python 도구를 중심으로 다음을 검토하세요.

- **Data leakage vectors**: 최종 산출물에 out-of-window 데이터가 섞일 수 있는 경로가 있는가?
- **Hash chain gaps**: `prepare -> seal -> validate -> parse` 체인이 end-to-end tamper-evident 한가?
- **Invariant coverage**: parser / validator의 invariant check가 충분한가? 조용히 통과하는 silent failure mode가 있는가?
- **Schema enforcement**: JSON schema가 malformed run을 실제로 차단하는가?

각 finding은 다음 심각도로 분류하세요.

- **[CRITICAL]**: 데이터 무결성이 깨지며 optimization run 전에 반드시 수정해야 함
- **[HIGH]**: 잘못된 run이 validation을 통과할 수 있는 governance gap
- **[MEDIUM]**: production 전에는 고쳐야 하는 robustness 문제
- **[LOW]**: best practice 수준의 개선점

각 finding마다 `Confirmed` 또는 `Suspected`를 함께 표기하세요.

### Section 2: Counterfactual & Risk Methodology

퀀트 관점에서 다음을 검토하세요.

- 현재 counterfactual 평가 방식은 타당한가?
  - 각 decision point에 대해 1-72 bar horizon what-if PnL
- `gate_regret_mean = 16.95`는 유의미한 metric인가?
  - 운영자가 실제로 무엇을 해석할 수 있는가?
- daily risk metrics 집계는 올바른가?
  - equity curve
  - max drawdown
  - profit factor
  - win rate
- optimization direction decision 전에 반드시 필요한데 현재 빠져 있는 지표는 무엇인가?

### Section 3: A' Window Clipping Policy

MT5 Strategy Tester는 `FromDate` / `ToDate`를 date-only로만 받습니다. 현재 파이프라인은 이를 다음과 같이 처리합니다.

1. raw output에는 `window_from` 이전 데이터가 일부 포함됨
2. validator는 이를 FAIL이 아니라 WARN으로 표시함
3. parser가 exact minute boundary로 clipping 수행
4. ENTRY가 window 밖에서 시작된 trade는 `trade_id` 전체를 제거함

이 접근이 방어 가능한지 검토하세요. 또한 downstream analysis를 오염시킬 수 있는 edge case가 있는지 보세요.

### Section 4: Concrete Coding Directives

이 섹션이 가장 중요합니다. Section 1-3의 각 finding마다 다음 형식으로 작성하세요.

```text
File: tools/<filename>.py
Function: <function_name>
Line (approx): <가능하면>
Evidence: <Confirmed 또는 Suspected>
Problem: <1-2문장>
Fix: <정확한 코드 변경 또는 구체적 pseudocode>
Priority: [CRITICAL/HIGH/MEDIUM/LOW]
```

중요 제약:

- `consider adding` 같은 표현은 쓰지 마세요.
- 실제로 구현 가능한 수정 지시를 주세요.
- 만약 안전한 직접 코드 수정이 불가능하고 운영 정책/거버넌스 판단이 필요한 사안이면 이렇게 적으세요.

```text
Fix: No direct code fix; governance/policy/operator decision required.
```

### Section 5: What's Missing Before WF4

WF4는 ML-first vs EA-first 방향 결정을 의미합니다. 현재 baseline과 tooling만으로는 부족할 수 있습니다. 방향 결정을 위해 추가로 필요한 **구체적 도구 또는 분석**을 제안하세요.

형식은 다음과 같습니다.

```text
Tool needed: <name>
Input: <읽는 파일/데이터>
Output: <생성 산출물>
Why: <어떤 결정을 가능하게 하는가>
Implementation sketch: <핵심 알고리즘 또는 pseudocode>
```

---

## 출력 형식

응답은 **한국어로 작성**하세요. 다만 다음은 원문 그대로 유지하세요.

- file path
- function name
- schema name
- code identifier
- literal column name / field name

Markdown 섹션 헤더를 사용하세요.

응답 마지막에는 반드시 다음 2개를 추가하세요.

### Final Blockers Before WF4

- 현재 상태에서 WF4 전에 막아야 할 blocker 1-3개를 severity 순으로 요약

### Assumptions / Scope Limits

- 이번 스코프 제한 때문에 확정하지 못한 사항 요약

---

## 하지 말 것

- "테스트를 더 추가해라" 같은 일반론
- 문서화 개선 제안
- 코드 스타일, 네이밍, 취향 지적
- 근거 없는 칭찬

## 반드시 할 것

- 가능한 한 구체적인 line / function 단위로 지적
- copy-paste 가능한 수정 방향 제시
- principal quant 관점에서 용납하기 어려운 가정 지적
- 이 파이프라인이 단일 run이 아니라 50개 이상의 optimization iteration에 반복 사용될 때 어떤 문제가 생기는지 고려
