# PROJECT_triple_sigma Step21 Ops Guide - Checklist

> Source: `PROJECT_triple_sigma_Step21_ops_guide_en.docx` (2026-03-09 snapshot)
> Created: 2026-03-10
> Last updated: 2026-03-10 (post-codex review fixes)
> Purpose: DOCX 문서 기반 진행 체크리스트. 각 항목별 현재 상태(Done/Skeleton/Missing)를 교차 검증하여 표기.

---

## 현재 프로젝트 상태 요약

| 영역 | 준비도 | 비고 |
|------|--------|------|
| Runtime Integrity | **HIGH** | Step21 완료, 컴파일 0 error/0 warning, 10개 probe 전부 통과 |
| Data Governance | **HIGH** | Data policy + history quality audit + data_freeze_manifest.yaml 완료 |
| ML Export/Parity | **MED-HIGH** | Step15 ONNX 12개 모델 export 완료, parity 증거 존재 |
| Optimization Ops | **HIGH** | 파서 4종 구현+테스트 통과, master table contract 완성, 운영 runbook 완성 |
| Release/Rollback Mgmt | **MODERATE** | SELECTION_RELEASE_RUNBOOK + ROLLBACK_POINT_STANDARD 작성 완료, 실제 번들은 최적화 후 |

**핵심 결론**: 최적화 시작 전 셋업 완료. 파서 파이프라인 구축 및 검증됨. 다음 단계는 WF2 (실제 캠페인 백테스트 실행).

---

## Phase 0: 폴더 구조 정비

### 0.1 기존 구조 보존
- [x] `design/` - Step01~21 설계문서 (21개 파일)
- [x] `src/ea/` - TripleSigma.mq5 + .ex5
- [x] `src/include/` - TS_*.mqh 12개 헤더 (7,680 lines)
- [x] `src/ml/` - Python ML 파이프라인 (step11~15)
- [x] `TRIPLE-SIGMA/` - 스펙 문서 (POLICY_FREEZE, CONTRACT, EA_RUNTIME, ONNX_DEV_SPEC)
- [x] `_coord/artifacts/` - 불변 증거 (step14~21 아티팩트)
- [x] `_coord/logs/` - 컴파일/스모크 로그
- [x] `_coord/tester/` - step16~21 테스터 프리셋
- [x] `_coord/ops/` - 운영 표준/런북
- [x] `tools/` - 패키징/오케스트레이션 스크립트

### 0.2 신규 디렉토리 (DOCX 섹션 3 권장구조)
- [x] `_coord/campaigns/` - 캠페인 워크스페이스 (디렉토리 생성됨)
- [x] `_coord/campaigns/C2026Q1_stage1_refresh/` - 첫 번째 캠페인 (구조 생성됨)
  - [x] `manifest.yaml` (7.6KB, 검증 완료)
  - [x] `freeze/data_freeze_manifest.yaml` (WF0 출력, 검증 완료)
  - [ ] `raw_tester_outputs/` (비어있음 - WF2에서 채워짐)
  - [ ] `parser_outputs/` (비어있음 - WF3에서 채워짐)
  - [ ] `analytics/` (비어있음)
  - [ ] `benchmark/` (비어있음)
  - [ ] `oos/` (비어있음)
  - [ ] `stress/` (비어있음)
  - [ ] `shortlist/` (비어있음)
  - [ ] `reports/` (비어있음)
- [x] `_coord/releases/` (디렉토리만 생성, 비어있음)
- [x] `_coord/rollback_points/` (디렉토리만 생성, 비어있음)
- [x] `_coord/notebooks/` (디렉토리만 생성, 비어있음)
- [x] `triple_sigma_runtime_patch/` (디렉토리만 생성, 비어있음 - 패치 인풋 필요)

---

## Phase 1: WF0 - Data Freeze

> DOCX 섹션 4 WF0: data policy, history-quality audit, tester baseline -> `data_freeze_manifest.yaml`

- [x] Data policy 문서 존재: `design/US100_RealTick_Backtest_Data_Policy.md`
- [x] History quality audit 존재: `_coord/artifacts/us100_history_quality/`
- [x] Backtest baseline 존재: `_coord/BACKTEST_BASELINE.md`
- [x] **`data_freeze_manifest.yaml` 생성 완료** -> `_coord/campaigns/C2026Q1_stage1_refresh/freeze/`
  - [x] Optimization window 정의 (3 folds)
  - [x] Benchmark window 정의
  - [x] OOS window 정의
  - [x] Stress window 정의
  - [x] Role overlap 없음 검증 (`pass: true`)
  - [x] Illegal broad-range 사용 없음 검증 (disallowed 명시)

---

## Phase 2: WF1 - Control-Pack Selection

> DOCX 섹션 4 WF1: runtime-integrity control과 profitability control 분리 -> `control_pack_registry.yaml`

- [x] `_coord/ops/control_pack_registry.yaml` (2.5KB, 검증 완료)
- [x] **내용 검증 완료**:
  - [x] Runtime-integrity control pack 정의 (`triple_sigma_pack_long_step16` - dummy ONNX 136B)
  - [x] Profitability control pack 정의 (`triple_sigma_pack_step15_q1` - real trained v0.1.0)
  - [x] Parity evidence 링크 포함
- [x] **DOCX 필수 원칙**: Step16 smoke pack을 profitability optimizer baseline으로 사용 금지 (명시됨)

---

## Phase 3: WF2 - Backtest Execution

> DOCX 섹션 4 WF2: campaign-specific presets 빌드 -> raw tester results

- [x] Step21 테스터 프리셋 존재: `_coord/tester/step21/*.ini` (10개)
- [x] 매트릭스 오케스트레이터 존재: `tools/run_step21_matrix.ps1`
- [ ] **캠페인 전용 프리셋 생성** (profitability control pack 기반)
- [ ] Raw tester 결과를 `campaigns/C2026Q1_stage1_refresh/raw_tester_outputs/`에 저장
- [ ] 컴파일 클린 + raw output 완전성 검증

---

## Phase 4: WF3 - Parsing & Analytics

> DOCX 섹션 4 WF3 + 섹션 5: master table 파이프라인

### 4.1 Parser Stack (Minimum Operating Set)
- [x] **`tools/parse_step21_run.py`** - raw-run 파서 + 스키마 밸리데이터 (구현+테스트 완료)
- [x] **`tools/build_master_tables.py`** - master table 물리화 (구현+테스트 완료)
- [x] **`tools/build_counterfactual_eval.py`** - H=72 forward evaluator (구현+테스트 완료)
- [x] **`tools/build_daily_risk_metrics.py`** - daily portfolio/risk ledger (구현+테스트 완료)

### 4.2 Master Table Contract
- [x] `_coord/ops/MASTER_TABLE_CONTRACT.md` (검증+수정 완료, trade_id: str)
- [x] **내용이 DOCX 섹션 5 스펙과 일치 검증됨**:
  - [x] `bars_master` - 전체 bar-level 스냅샷 + 시간 단조성 검증 + schema_version 일관성
  - [x] `trades_master` - paired realized trade ledger + EXIT-without-ENTRY anomaly 감지
  - [x] `execution_master` - 이벤트 순서 검증 + timestamp 단조성 + lifecycle 시퀀스
  - [x] `modify_master` - MODIFY ledger + close-before-modify 우선순위 검증
  - [x] `audit_master` - broker audit trail
  - [x] `counterfactual_eval` - GATE_BLOCK/ENTRY/EARLY_EXIT/NO_EXIT/MODIFY 매핑
  - [x] `daily_risk_metrics` - entry-only days 포함, intraday peak-to-trough drawdown

### 4.3 Key/Schema Sanity + Invariant Continuity 검증
- [x] 파싱 후 key/schema sanity check 자동화 (schema_version, log_schema_version 일관성)
- [x] Invariant continuity check (duplicate EXIT=0, same-timestamp EXIT->ENTRY=0)
- [x] trade_id 형식 검증 (TS_XXXXX 패턴)

### 4.4 파이프라인 테스트 결과 (step21_live_trailing_probe)
- Parse: trade_log=5001, bar_log=65333, schema+invariants **PASS**
- Master tables: trades=1805, bars=65333, modify=1392, exec=5001
- Counterfactual: 5407 rows (ENTRY=1805, EARLY_EXIT=1804, MODIFY=1392, NO_EXIT=227, GATE_BLOCK=179)
  - **v2 fix**: timestamp exact-match → M5 bar floor 매핑으로 EXIT coverage 737→1804 복구 (100%)
- Daily risk: 239 trading days, PnL=-44.45, win_rate=68.41%, PF=1.85
- Warnings: 4 close-before-modify timestamp overlaps (data quality, non-blocking)

---

## Phase 5: WF4 - Branch Decision

> DOCX 섹션 4 WF4: parsed analytics 기반 브랜치 결정

- [ ] **ML-first / EA-first / Runtime-fix-first 결정**
  - [ ] Stage1 상태 평가 (현재: eligible challenger 없음 - ML bottleneck)
  - [ ] Stage2 상태 평가 (현재: winner 존재)
  - [ ] Gate regret 분석
  - [ ] 한 번에 하나의 primary branch만 open

> DOCX 권장: Stage1이 bottleneck이므로 ML-first 가능성 높음

---

## Phase 6: WF5 - Branch Optimization

> DOCX 섹션 4 WF5 + 섹션 6: 최적화 우선순위

### DOCX 권장 순서:
1. [ ] **Data** - window freeze 비협상 유지
2. [ ] **Stage1** - eligible challenger 없음 -> 데이터 확대 + 재보정
3. [ ] **Stage2** - winner 존재, search space 미세조정
4. [ ] **EA Gates** - 좋은 시그널을 gate가 차단하는지 확인
5. [ ] **Early Exit** - opportunity cost vs risk saved 트레이드오프
6. [ ] **Protective Modify** - alpha preservation layer
7. [ ] **Risk Sizing** - edge 표현 변경 (edge 존재 변경 아님)
8. [ ] **Limited Joint Sweep** - 마지막 (조기 joint search는 attribution 파괴)

### 레이어별 Pass 기준:
- [ ] ML: layer-specific improvement without OOS damage
- [ ] EA: layer-specific improvement without OOS damage
- [ ] Joint: no fragile single-interaction dependence

---

## Phase 7: WF6 - Benchmark / OOS / Stress Restage

> DOCX 섹션 4 WF6

- [ ] Small incumbent set 재실행
- [ ] Acceptable dispersion 확인
- [ ] Acceptable concentration 확인

---

## Phase 8: WF7 - Limited Joint Sweep

> DOCX 섹션 4 WF7

- [ ] Small interaction matrix 평가
- [ ] Fragile single-interaction dependence 없음 확인

---

## Phase 9: WF8 - Release Candidate

> DOCX 섹션 4 WF8

- [ ] Selected pack + params 패키징
- [ ] KPI snapshot 포함
- [ ] Runtime patch inputs 포함
- [ ] Runbook 포함
- [ ] Hash 포함
- [ ] Reproducibility 검증
- [ ] Handoff completeness 검증
- [ ] `_coord/releases/` 에 RC 번들 저장

---

## Phase 10: WF9 - Rollback Point

> DOCX 섹션 4 WF9

- [ ] Previous stable state 풀 번들 패키징
- [ ] Patch-input retention 확인
- [ ] Hash verification 통과
- [ ] `_coord/rollback_points/` 에 저장
- [ ] `triple_sigma_runtime_patch/` 패치 인풋 보존

---

## Operating Checkpoints (CP0-CP8)

> DOCX 섹션 9

| CP | 항목 | 상태 | 비고 |
|----|------|------|------|
| CP0 | Build + schema integrity | **PASS** | 컴파일 클린, Step21 스키마 일관성 확인 |
| CP1 | Runtime invariants | **PASS** | dup non-modify=0, dup EXIT=0, same-ts EXIT->ENTRY=0, feature-off match=true, close-before-modify=clean, pending-modify recovery=clear, reload pass |
| CP2 | Data readiness | **PASS** | data_freeze_manifest.yaml 완료, 윈도우 정의+overlap 검증 통과 |
| CP3 | Control-pack readiness | **PASS** | dual control 분리 완료, registry 내용 검증 완료 |
| CP4 | Parser readiness | **PASS** | 파서 4종 구현+테스트 통과, codex 리뷰 반영 완료 |
| CP5 | ML readiness | **NOT STARTED** | leakage-free split, Stage1 guardrails, Stage2 incumbent, drift baseline |
| CP6 | EA policy readiness | **NOT STARTED** | gate regret, early-exit tradeoff, modify tradeoff 측정 가능해야 함 |
| CP7 | Integrated bench/OOS/stress | **NOT STARTED** | team gates 통과 without fatal runtime anomaly |
| CP8 | RC + rollback | **NOT STARTED** | RC reproducible, rollback bundle complete, runbook updated, patch inputs retained |

---

## Immediate Deliverables (DOCX 섹션 10)

### Minimum Operating Set

| # | Deliverable | 경로 | 상태 |
|---|-------------|------|------|
| 1 | Raw-run parser + schema validator | `tools/parse_step21_run.py` | **DONE** |
| 2 | Master-table materializer | `tools/build_master_tables.py` | **DONE** |
| 3 | H=72 forward evaluator | `tools/build_counterfactual_eval.py` | **DONE** |
| 4 | Daily portfolio/risk ledger | `tools/build_daily_risk_metrics.py` | **DONE** |
| 5 | Derived-table contract | `_coord/ops/MASTER_TABLE_CONTRACT.md` | **DONE** (codex 리뷰 반영) |
| 6 | First campaign manifest | `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml` | **DONE** (검증 완료) |
| 7 | Optimizer operating SOP | `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md` | **DONE** (검증 완료) |
| 8 | Retained runtime patch inputs | `triple_sigma_runtime_patch/` | **EMPTY** (패치 인풋 보존 필요 - 최적화 시작 시 채워짐) |

### Recommended Expansion Set

| # | Deliverable | 경로 | 상태 |
|---|-------------|------|------|
| 9 | Manifest-driven orchestrator | `tools/run_campaign_matrix.ps1` | **MISSING** |
| 10 | Shortlist/committee-pack builder | `tools/assemble_selection_pack.py` | **MISSING** |
| 11 | Promotion procedure | `_coord/ops/SELECTION_RELEASE_RUNBOOK.md` | **DONE** |
| 12 | Rollback-bundle standard | `_coord/ops/ROLLBACK_POINT_STANDARD.md` | **DONE** |
| 13 | Single-run ledger review notebook | `_coord/notebooks/01_single_run_review.ipynb` | **MISSING** |
| 14 | Policy diagnostics notebook | `_coord/notebooks/02_gate_exit_modify_diagnostics.ipynb` | **MISSING** |
| 15 | Final decision support notebook | `_coord/notebooks/03_selection_committee_pack.ipynb` | **MISSING** |
| 16 | Optuna orchestration module | (after parser stack stable) | **DEFERRED** |

---

## Codex Review Summary (2026-03-10)

Codex (GPT-5.4) 정적 리뷰 2회 수행, 총 9개 항목 발견 후 전부 수정 완료:

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | High | counterfactual_eval: EXIT 대신 EARLY_EXIT/NO_EXIT 매핑 누락 | EARLY_EXIT + NO_EXIT (pending_exit_reason 기반) 구현 |
| 1b | High | counterfactual_eval: timestamp exact-match로 EXIT 59% 누락 (737/1804) | floor_to_m5() 도입, EXIT coverage 100% 복구 |
| 1c | Medium | counterfactual_eval: NO_EXIT 방향 LONG 하드코딩 | active_direction map으로 실제 포지션 방향 추출 |
| 2 | High | build_master_tables: EXIT-without-ENTRY anomaly 무시 | orphan exit 감지 로직 추가 |
| 3 | High | parse_step21_run: schema_version 일관성 미검증, trade_id 형식 미검증 | 양쪽 모두 검증 추가 |
| 4 | Medium | daily_risk_metrics: entry-only day 누락, max_drawdown_day 산출 오류 | all_dates 합집합 + intraday peak-to-trough |
| 5 | Medium | build_master_tables: close-before-modify/timestamp 단조성/lifecycle 검증 부족 | 3가지 검증 모두 추가 |
| 6 | Low | SELECTION_RELEASE_RUNBOOK: 경로 불일치, RC 번들에 runtime patch 누락 | 경로 수정 + patch inputs 추가 |
| - | Drift | MASTER_TABLE_CONTRACT: trade_id int → str | `str` (TS_XXXXX)으로 수정 |

---

## Decision Matrix (DOCX 섹션 8)

| 관찰 증상 | 주요 레이어 | 즉시 조치 | 중지 조건 |
|-----------|------------|----------|-----------|
| Low Stage1 margin + short-side collapse | ML | Stage1 데이터 확대 + 재보정 | EA broad search 동시 금지 |
| High Stage2 regret + hold-boundary pressure | ML | Stage2 search space 재조정 | Stage1 불안정시 deep Stage2 지연 |
| Signal good but gate regret large | EA policy | Gate 완화/조건화 | Execution anomaly 높으면 runtime 우선 |
| Early-exit opp cost > risk saved | EA policy | Threshold/holding 완화 | Invariant 깨지면 중지 |
| Protective modify destroys more alpha | EA policy | Trigger 올리거나 regime-selective | Modify lineage 불완전시 불신 |
| Retcodes/clear latency/auth disagreement rise | Execution | **수익성 작업 중단 -> runtime integrity 복귀** | **Mandatory stop** |
| Dup EXIT/phantom EXIT/core-row drift | Runtime | **모든 최적화 중단 -> anchor 재구축** | **Mandatory stop** |
| Benchmark strong but OOS weak | Data+ML | Retrain cadence 조정 + simpler incumbent 비교 | Joint sweep 금지 |
| PF OK but DD/dispersion excessive | Portfolio/risk | Sizing/concentration 축소 | Edge 문제 은폐 금지 |
| Reload evidence but patch inputs missing | Research ops | Patch inputs + hashes 보존 | Non-reproducible 상태에서 RC 승격 금지 |

---

## KPI Framework (DOCX 섹션 7)

### ML Signal Layer
- [ ] Macro-F1 by regime / PASS recall
- [ ] Calibration log loss / Brier
- [ ] Margin-decile monotonicity
- [ ] SHORT coverage ratio
- [ ] Stage2 parameter regret / posterior drift PSI

### EA Policy Layer
- [ ] Candidate conversion rate
- [ ] Gate block rate by reason / gate regret
- [ ] Early-exit opportunity cost / risk saved
- [ ] Protective-modify save ratio / alpha-loss ratio
- [ ] Hold utilization / force-exit share

### Execution / Recovery Layer
- [ ] Retcode executed share
- [ ] Pending clear latency
- [ ] Synthetic vs actual reject rate
- [ ] Duplicate / phantom EXIT count
- [ ] Observer/authority disagreement

### Portfolio / Risk Layer
- [ ] Expectancy R
- [ ] PF / payoff ratio
- [ ] MAE/MFE capture ratio
- [ ] Drawdown / ulcer profile
- [ ] Concentration and window dispersion

---

## First 5 Actions (DOCX 섹션 11)

> 즉시 실행 권장 순서

1. [x] 현재 data policy에서 첫 번째 캠페인 windows freeze (data_freeze_manifest.yaml)
2. [x] Dual-control `control_pack_registry.yaml` 내용 완성/검증
3. [x] Step21 parser + master-table pipeline 구축 (`parse_step21_run.py`, `build_master_tables.py`)
4. [x] Counterfactual + daily-risk analytics layer 구축
5. [ ] 첫 번째 real-pack single run 실행 -> ML-first vs EA-first 결정

---

## Appendix A: Operating Handbook Outline (DOCX 부록 A)

> 향후 완성할 핸드북 구조

1. Purpose and scope
2. Source of truth and document priority
3. Runtime invariants and non-negotiable gates
4. Data freeze policy
5. Control-pack registry and parity rules
6. Backtest execution SOP
7. Parser/master-table contract
8. KPI definitions and escalation rules
9. Branching logic: ML-first / EA-first / Runtime-fix-first
10. Benchmark / OOS / stress standard
11. Selection committee package
12. Release-candidate standard
13. Rollback-point bundle standard
14. Operator handoff and incident triage
15. Evidence retention and archive policy

---

## Appendix B: Evidence Anchors (DOCX 부록 B)

> DOCX 작성시 직접 검토된 내부 파일 목록

- `README.md`
- `STEP21_CLOSEOUT_AND_VERIFICATION.md`
- `STEP21_PROMOTION_AND_DEFERRED_SCOPE.md`
- `design/BAR_LOG_SCHEMA.md`
- `design/US100_RealTick_Backtest_Data_Policy.md`
- `_coord/BACKTEST_BASELINE.md`
- `_coord/README.md`
- `_coord/ops/RETAINED_ARTIFACT_STANDARD.md`
- `_coord/ops/RECOVERY_MATRIX.md`
- `_coord/ops/EARLY_EXIT_TRIAGE_RUNBOOK.md`
- `_coord/ops/PROTECTIVE_MODIFY_TRIAGE_RUNBOOK.md`
- `_coord/logs/compile/compile_step21_wip.log`
- `_coord/logs/smoke/step21_*_summary.md`
- `_coord/tester/step21/*.ini`
- `_coord/artifacts/step14_validation_q1_out/*`
- `_coord/artifacts/step15_export_q1_out/*`
- `_coord/artifacts/step21_*/*`
- `_coord/artifacts/us100_history_quality/*`
- `tools/run_step21_matrix.ps1`
- `tools/package_step21_artifacts.py`
- `src/ml/pyproject.toml`
- `src/ea/TripleSigma.mq5`
- `src/include/TS_Execution.mqh`
- `src/include/TS_Logger.mqh`
- `src/include/TS_Monitor.mqh`
