# PROJECT_triple_sigma Step21 Ops Checklist v2

> Created: 2026-03-12
> Basis: GPT Pro Audit Report (2026-03-12) + Codex gpt-5.4 cross-review + Codex-only Phase B+ migration
> Supersedes: STEP21_OPS_CHECKLIST.md (v1, 2026-03-10)
> Purpose: Audit Finding F1~F7 remediation을 반영하고, 실제 파일시스템/코드와 교차 대조하여 갱신된 체크리스트

---

## 현재 프로젝트 상태 요약 (v2 재평가)

| 영역 | 준비도 | v1 판정 | v2 재평가 | 근거 |
|------|--------|---------|-----------|------|
| Runtime Integrity | **HIGH** | HIGH | **HIGH** | Step21 완료, 0 error/0 warning, 10개 probe 통과 (`_coord/logs/compile/compile_step21_wip.log`) |
| Data Governance | **HIGH** | HIGH | **HIGH** | data_freeze_manifest.yaml 완료 (`_coord/campaigns/C2026Q1_stage1_refresh/freeze/`) |
| ML Export/Parity | **MED-HIGH** | MED-HIGH | **MED-HIGH** | Step15 ONNX 12개 모델, parity 증거 존재. pack payload hash 미검증 (F4) |
| Optimization Ops | ~~HIGH~~ | HIGH | **PROVISIONAL → Phase A DONE** | F1/F2/F3 remediated: campaign runner+validator, strict gates, contract v2. Admissible run 대기 중 |
| Release/Rollback Mgmt | ~~MODERATE~~ | MODERATE | **FAIL** | runbook만 존재, RC/RB 번들 미실체화 (F4), `_coord/releases/`, `_coord/rollback_points/` empty scaffold |
| Agent Governance | **HIGH** | (없음) | **Phase B+ DONE** | AGENT_ROLE_POLICY.md + AGENTS.md + CODEX_PHASE_B_PLUS_PLAYBOOK.md + Codex hook helpers |

**핵심 결론 (v2)**: 최적화 시작 전 셋업은 **미완료**. admissible campaign lineage 생산, strict validator, agent 권한 분리가 선행 필요.

---

## v1 → v2 STALE 항목 정정

| v1 서술 | 실제 상태 | 근거 |
|---------|----------|------|
| `parser_outputs/ (비어있음 - WF3에서 채워짐)` | 10개 파일 존재 (parquet + manifest) | `parse_manifest.json` |
| counterfactual taxonomy: EARLY_EXIT 중심 | EXIT_SL / EXIT_TP / EXIT_FORCE / EARLY_EXIT | `coverage_manifest.json` L9-12 |
| CP1 `close-before-modify=clean` | warning 4건 존재, pass=true | `parse_manifest.json` L34-35 |
| CP4 **PASS** | **PROVISIONAL** — warning-only gate, ENTRY unmapped 미게이팅 | `build_counterfactual_eval.py` L357 |
| "최적화 시작 전 셋업 완료" | 미완료 — campaign provenance breach (F1) | `parse_manifest.json` raw_dir → `_coord\artifacts\step21_live_trailing_probe` |
| `_coord/releases/`, `_coord/rollback_points/` 상태 미언급 | empty scaffold 존재 | 파일시스템 확인 |
| RETAINED_ARTIFACT_STANDARD 범위 | step19/20만 커버, step21 packager는 SHA-256 이미 구현 | `tools/package_step21_artifacts.py` L315, `RETAINED_ARTIFACT_STANDARD.md` L3 |

---

## Phase 0: 폴더 구조 정비

### 0.1 기존 구조 보존
- [x] `design/` - Step01~21 설계문서 (21개 파일)
- [x] `src/ea/` - TripleSigma.mq5 + .ex5
- [x] `src/include/` - TS_*.mqh 13개 헤더
- [x] `src/ml/` - Python ML 파이프라인 (step11~15)
- [x] `TRIPLE-SIGMA/` - 스펙 문서
- [x] `_coord/artifacts/` - 불변 증거 (step14~21)
- [x] `_coord/logs/` - 컴파일/스모크 로그
- [x] `_coord/tester/` - step16~21 테스터 프리셋
- [x] `_coord/ops/` - 운영 표준/런북
- [x] `tools/` - 패키징/오케스트레이션 스크립트

### 0.2 신규 디렉토리
- [x] `_coord/campaigns/C2026Q1_stage1_refresh/` — manifest.yaml + freeze/ 존재
  - [x] `manifest.yaml` (7.6KB, 검증 완료)
  - [x] `freeze/data_freeze_manifest.yaml` (WF0 출력)
  - [ ] `runs/` — **신규 필요** (campaign-native run workspace, Audit F1)
  - [x] `raw_tester_outputs/` — empty scaffold 존재
  - [~] `parser_outputs/` — 10개 파일 존재, 단 provenance는 retained artifact replay (비admissible)
  - [ ] `analytics/`, `benchmark/`, `oos/`, `stress/`, `shortlist/`, `reports/` — empty
- [x] `_coord/releases/` — empty scaffold
- [x] `_coord/rollback_points/` — empty scaffold
- [x] `_coord/notebooks/` — empty scaffold
- [x] `triple_sigma_runtime_patch/` — empty scaffold

### 0.3 에이전트 구조 (Codex-only Phase B+)
- [x] `AGENTS.md` — repo-root Codex operating instructions
- [x] `_coord/ops/CODEX_PHASE_B_PLUS_PLAYBOOK.md` — 11개 Codex workflow 정의
  - Tier 1: campaign-run-sealer, parser-replay, integrity-gate, codex-validator
  - Tier 2: campaign-bootstrap, mt5-preset-builder, kpi-branch-decision (skeleton)
  - Tier 3: ml-export-parity, pack-hash-capture, rc-bundle-assembly, rollback-bundle-verify (skeleton)
- [x] `tools/codex_hooks/` — 2개 Codex hook helper (post-seal-check, pre-promotion-guard)
  - pre-run/post-rollback helpers deferred (tooling 미존재)
- [x] agent 권한 분리 정책 문서 — `AGENT_ROLE_POLICY.md` (Codex-only)

---

## Phase 1: WF0 - Data Freeze

- [x] Data policy: `design/US100_RealTick_Backtest_Data_Policy.md`
- [x] History quality audit: `_coord/artifacts/us100_history_quality/`
- [x] Backtest baseline: `_coord/BACKTEST_BASELINE.md`
- [x] **`data_freeze_manifest.yaml` 생성 완료**
  - [x] Optimization window 정의 (3 folds)
  - [x] Benchmark / OOS / Stress window 정의
  - [x] Role overlap 없음 (`pass: true`)
- [ ] **[P1] freeze_hash_manifest.json** — source policy hash + freeze hash sealing

---

## Phase 2: WF1 - Control-Pack Selection

- [x] `_coord/ops/control_pack_registry.yaml` (2.5KB)
- [x] Runtime-integrity pack: `triple_sigma_pack_long_step16` (dummy ONNX 136B)
- [x] Profitability pack: `triple_sigma_pack_step15_q1` (real trained v0.1.0)
- [x] Step16 smoke pack profitability baseline 사용 금지 명시
- [ ] **[P0] pack_hash_manifest.json** — external pack payload SHA-256 + ONNX shape 검증 (F4)
- [ ] **[P1] pack parity recheck** — ONNX export parity 재검증 retained

> **CRITICAL (Codex)**: current parse source = `triple_sigma_pack_long_step16` (smoke pack). profitability baseline 금지 대상. 근거: `step21_live_trailing_probe_summary.md` L27

---

## Phase 3: WF2 - Backtest Execution

- [x] Step21 테스터 프리셋: `_coord/tester/step21/*.ini` (10개) — regression/smoke 전용
- [x] 매트릭스 오케스트레이터: `tools/run_step21_matrix.ps1` — workstation-bound retained packager
- [x] **[P0] `tools/run_campaign_backtest.py`** — manifest-driven campaign runner (F1) ✅ Phase A
  - [x] preset_snapshot.ini, run_manifest.json, raw_hash_manifest.json, pack_hash_manifest.json, compile_log.txt
  - [x] `_coord/campaigns/<id>/runs/RUN_<ts>/` 구조 (Audit 섹션 8.6)
- [x] **[P0] `tools/validate_campaign_run.py`** — 9-gate validator (F1+F6) ✅ Phase A
  - [x] raw_dir 외부면 hard fail (provenance gate)
  - [x] manifest window/pack 일치 검증 (window_conformance gate)
  - [x] campaign-manifest conformance gate + schema_conformance gate (jsonschema)
  - [x] window_boundary gate (minute-level hard check)
- [ ] Campaign 전용 프리셋 (`step15_q1` pack 기반) — Phase B (실행 시 생성)
- [x] Raw tester → `runs/RUN_<ts>/20_raw/` immutable 보존 — 구조 구현 완료

---

## Phase 4: WF3 - Parsing & Analytics

### 4.1 Parser Stack
- [x] `tools/parse_step21_run.py`
- [x] `tools/build_master_tables.py`
- [x] `tools/build_counterfactual_eval.py`
- [x] `tools/build_daily_risk_metrics.py`

### 4.2 Master Table Contract
- [x] `_coord/ops/MASTER_TABLE_CONTRACT.md`
- [x] **[P0] Contract v2** — EXIT_SL/EXIT_TP/EXIT_FORCE domain 추가 (F3) ✅ Phase A

### 4.3 Integrity Gates (v2 강화)
- [x] schema_version 일관성
- [x] trade_id 형식 (TS_XXXXX)
- [ ] **[P0] close-before-modify overlap → hard fail** (admissible run) (F2)
  - [ ] synthetic regression에만 waiver class 허용
  - 근거: `build_master_tables.py` L201-216
- [ ] **[P0] unmapped ENTRY → hard fail / threshold waiver** (F3)
  - 근거: `build_counterfactual_eval.py` L357
- [ ] **[P0] parser admission provenance check**

### 4.4 현재 파이프라인 테스트 결과
- Parse: trade_log=5001, bar_log=65333, PASS
- Master: trades=1805, bars=65333, modify=1392, exec=5001
- Counterfactual: 5407 rows, EXIT coverage 100%
- Daily risk: 239 days, PnL=-44.45, **avg_daily_PF=1.85** (daily average, NOT global trade PF — F7)
- **Warnings: 4 close-before-modify overlaps** (v1 "clean" → v2 정정)
- **Provenance: retained artifact replay** (비admissible — F1)

---

## Phase 5~10: WF4~WF9

### Phase 5: WF4 - Branch Decision
- [ ] `tools/build_kpi_summary.py` — trade-level PF, expectancy, drawdown, dispersion, short-side (F7)
- [ ] `tools/build_branch_decision_packet.py` — KPI 기반 routing (Audit 섹션 9.2)
- [ ] ML-first vs EA-first 결정 (admissible baseline 전제)

### Phase 6: WF5 - Branch Optimization
- [ ] DOCX 권장 순서: Data → Stage1 → Stage2 → EA Gates → Early Exit → Protective Modify → Risk Sizing → Joint Sweep

### Phase 7: WF6 - Benchmark / OOS / Stress Restage
- [ ] Dispersion / concentration 확인

### Phase 8: WF7 - Limited Joint Sweep
- [ ] Fragile single-interaction dependence 없음

### Phase 9: WF8 - Release Candidate
- [ ] **`tools/bundle_rc.py`** (F4)
- [ ] `_coord/releases/<rc_id>/` RC 번들
- [ ] dual-signature (writer + validator)

### Phase 10: WF9 - Rollback Point
- [ ] **`tools/bundle_rollback.py`** (F4)
- [ ] `_coord/rollback_points/<rb_id>/`
- [ ] Hash verification + restore rehearsal

---

## Operating Checkpoints (CP0-CP8) — v2

| CP | 항목 | v1 | v2 | 변경 근거 |
|----|------|----|----|-----------|
| CP0 | Build + schema | PASS | **PASS** | 0 err/0 warn. campaign run manifest bind 추가 필요 |
| CP1 | Runtime invariants | PASS | **PROVISIONAL** | close-before-modify warning 4건 (`parse_manifest.json` L34) |
| CP2 | Data readiness | PASS | **PASS** | freeze manifest 완료. freeze_hash 권장 |
| CP3 | Control-pack readiness | PASS | **PROVISIONAL** | external pack hash 미검증 (F4) |
| CP4 | Parser readiness | PASS | **PROVISIONAL** | provenance breach (F1) + warning gate (F2) + ENTRY 미게이팅 (F3) |
| CP5 | ML readiness | NOT STARTED | **PROVISIONAL** | artifacts 존재, validator packet 부재 |
| CP6 | EA policy readiness | NOT STARTED | **NOT STARTED** | benchmark diagnostic 미실행 |
| CP7 | Bench/OOS/stress | NOT STARTED | **NOT STARTED** | admissible run 전제 |
| CP8 | RC + rollback | NOT STARTED | **NOT STARTED** | bundler 미구현 |

---

## Deliverables Matrix

### 기존 Minimum Operating Set

| # | Deliverable | 경로 | 상태 | 비고 |
|---|-------------|------|------|------|
| 1 | Raw-run parser | `tools/parse_step21_run.py` | DONE | contract_version 2.0, campaign-native layout 지원 |
| 2 | Master-table materializer | `tools/build_master_tables.py` | DONE | strict mode hard fail 완료 (F2) ✅ |
| 3 | H=72 forward evaluator | `tools/build_counterfactual_eval.py` | DONE | ENTRY gate + contract v2 완료 (F3) ✅ |
| 4 | Daily risk ledger | `tools/build_daily_risk_metrics.py` | DONE | KPI semantics 분리 (F7) Phase B |
| 5 | Table contract | `_coord/ops/MASTER_TABLE_CONTRACT.md` | DONE | v2.0: EXIT_SL/EXIT_TP/EXIT_FORCE 완료 (F3) ✅ |
| 6 | Campaign manifest | `campaigns/.../manifest.yaml` | DONE | |
| 7 | Operator runbook | `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md` | DONE | |
| 8 | Runtime patch inputs | `triple_sigma_runtime_patch/` | EMPTY | |

### 신규 도구

| # | Deliverable | 경로 | 우선순위 | 상태 | 의존 |
|---|-------------|------|----------|------|------|
| 9 | Campaign runner | `tools/run_campaign_backtest.py` | P0 | ✅ DONE | S1,S2,S3 |
| 10 | Campaign validator | `tools/validate_campaign_run.py` | P0 | ✅ DONE | #9 |
| 11 | KPI summary | `tools/build_kpi_summary.py` | P1 | — | admissible run |
| 12 | Branch decision | `tools/build_branch_decision_packet.py` | P1 | — | #11 |
| 13 | RC bundler | `tools/bundle_rc.py` | P1 | — | skeleton Phase C |
| 14 | RB bundler | `tools/bundle_rollback.py` | P1 | — | #13 |

### 신규 Schema Contracts

| # | Schema | 우선순위 | 시점 | 상태 |
|---|--------|----------|------|------|
| S1 | campaign_run_manifest.schema.json | P0 | Phase A | ✅ DONE |
| S2 | raw_hash_manifest.schema.json | P0 | Phase A | ✅ DONE |
| S3 | pack_hash_manifest.schema.json | P0 | Phase A | ✅ DONE |
| S4 | kpi_summary.schema.json | P1 | Phase C |
| S5 | rc_manifest.schema.json | P1 | Phase C |
| S6 | rollback_manifest.schema.json | P1 | Phase C |

### 에이전트 인프라

| # | Deliverable | 우선순위 | 시점 |
|---|-------------|----------|------|
| AG1 | Agent role/permission policy | P0 | Phase A | ✅ DONE |
| AG2 | Codex Phase B+ playbook workflows | P1 | Phase B+ | ✅ DONE (`CODEX_PHASE_B_PLUS_PLAYBOOK.md`, 11 workflows) |
| AG3 | Codex hook helpers | P1 | Phase B+ | ✅ DONE (`tools/codex_hooks/`, 2 helpers) |
| AG4 | Codex independent validator path | P1 | Phase B+ | ✅ DONE (Codex-only `codex-validator` workflow + `codex_validator_report.md`) |
| AG5 | Artifact retention template | P0 | Phase A | ✅ DONE |

---

## Audit Finding Remediation Tracker

| Finding | Severity | 제목 | Phase | 상태 |
|---------|----------|------|-------|------|
| F1 | P0 | Campaign provenance → campaign-native runner | A | **DONE** (run_campaign_backtest.py + validate_campaign_run.py) |
| F2 | P0 | close-before-modify → hard fail | A | **DONE** (build_master_tables.py strict mode) |
| F3 | P0 | Counterfactual contract drift + ENTRY gate | A | **DONE** (contract v2 + ENTRY gate in build_counterfactual_eval.py) |
| F4 | P0 | RC/Rollback 번들 미실체화 | C (skeleton) / D (full) | NOT STARTED |
| F5 | P1 | Workstation-bound orchestration | D | NOT STARTED |
| F6 | P0 | Independent validator 부재 | A (정책) / B+ (구현) | **DONE** (정책: AGENT_ROLE_POLICY.md + 구현: Codex playbook + Codex pre-promotion guard) |
| F7 | P1 | KPI semantics + short-side | B | NOT STARTED |
