# NEXT_ACTIONS_ROADMAP

> Created: 2026-03-12
> Basis: Checklist v2 + GPT Pro Audit Report + Codex cross-review + Claude Opus synthesis
> Purpose: P0 blocker 해소 → admissible baseline → branch decision → promotion infrastructure

---

## Phase A — Admissible Baseline Factory (이번 주)

> 목표: campaign-native run을 생산할 수 있는 인프라 + strict gate hardening
> Codex 합의: "Phase A를 문서정리가 아니라 campaign benchmark single-run admission hardening으로 재정의"

### A0. Agent 권한 분리 정책 문서화
- **산출물**: `_coord/ops/AGENT_ROLE_POLICY.md`
- **내용**: writer / operator / validator / gatekeeper 역할, 권한, 금지 사항 정의 (Audit 섹션 8.1~8.2)
- **완료 기준**: no-self-promotion rule 명문화, 각 role의 read/write scope 확정
- **의존**: 없음
- **Finding**: F6

### A1. Campaign backtest runner 구현
- **산출물**: `tools/run_campaign_backtest.py`
- **내용**: manifest.yaml 읽어 campaign-specific preset 생성 → MT5 backtest 실행 → raw output + hash sealing
- **산출 파일**:
  - `_coord/campaigns/<id>/runs/RUN_<ts>/00_request/preset_snapshot.ini`
  - `_coord/campaigns/<id>/runs/RUN_<ts>/10_compile/compile_log.txt`
  - `_coord/campaigns/<id>/runs/RUN_<ts>/20_raw/` (immutable raw outputs)
  - `_coord/campaigns/<id>/runs/RUN_<ts>/21_hash/raw_hash_manifest.json`
  - `_coord/campaigns/<id>/runs/RUN_<ts>/21_hash/pack_hash_manifest.json`
  - `_coord/campaigns/<id>/runs/RUN_<ts>/run_manifest.json`
- **완료 기준**: benchmark diagnostic run이 campaign workspace 안에서 end-to-end 재생성됨
- **의존**: A3 (schema)
- **참고**: `tools/package_step21_artifacts.py` L315의 SHA-256 로직 재사용 가능 (Codex 제안)
- **Finding**: F1

### A2. Campaign run validator 구현
- **산출물**: `tools/validate_campaign_run.py`
- **내용**:
  - raw_dir가 campaign run workspace 외부면 **hard fail**
  - manifest의 window alias / pack ID와 실제 preset/pack 일치 검증
  - campaign-manifest conformance gate (Codex 발견: current parse가 금지된 smoke pack 사용)
  - raw output completeness: `trade_log.csv`, `bar_log_*.csv`, `exec_state.ini`, `compile_log.txt` 존재 검증 (Codex 최종 리뷰)
  - compile clean 검증 (0 error / 0 warning)
  - hash manifest 완전성 검증
- **완료 기준**: retained artifact replay 자동 reject + raw/compile/hash 완전성 통과
- **의존**: A1
- **Finding**: F1, F6

### A3. Run/Raw/Pack schema 3개 초안
- **산출물**:
  - `_coord/ops/schemas/campaign_run_manifest.schema.json` (S1)
  - `_coord/ops/schemas/raw_hash_manifest.schema.json` (S2)
  - `_coord/ops/schemas/pack_hash_manifest.schema.json` (S3)
- **완료 기준**: A1 runner가 이 schema에 맞는 output 생성
- **의존**: 없음

### A4. close-before-modify hard fail 승격
- **산출물**: `tools/build_master_tables.py` 수정
- **내용**:
  - admissible campaign run에서는 same-trade same-ts EXIT+MODIFY overlap → **hard fail**
  - synthetic regression artifact에만 explicit waiver class 허용
- **완료 기준**: benchmark/OOS/selection run은 overlap>0이면 pass 불가
- **의존**: 없음
- **코드 위치**: `build_master_tables.py` L201-219 (현재 warning-only)
- **Finding**: F2

### A5. Counterfactual contract v2 + ENTRY gate
- **산출물**:
  - `_coord/ops/MASTER_TABLE_CONTRACT.md` v2 (EXIT_SL/EXIT_TP/EXIT_FORCE domain 추가)
  - `tools/build_counterfactual_eval.py` 수정 (unmapped ENTRY → hard fail / threshold waiver)
- **완료 기준**: contract, parser outputs, coverage manifest의 decision_type taxonomy 일치
- **의존**: 없음
- **코드 위치**: `build_counterfactual_eval.py` L357 (현재 ENTRY 미게이팅)
- **Finding**: F3

### A6. Campaign 디렉토리 구조 마이그레이션 계획 (Codex 최종 리뷰)
- **산출물**: manifest.yaml, OPTIMIZATION_OPERATOR_RUNBOOK.md, parse_step21_run.py, MASTER_TABLE_CONTRACT.md 갱신
- **내용**:
  - 기존 `raw_tester_outputs/` + `parser_outputs/` flat 구조 → `runs/RUN_<ts>/20_raw/` + `runs/RUN_<ts>/30_parsed/` 계층 구조로 전환
  - 기존 parser_outputs/는 "retained artifact replay archive"로 재분류, admissible baseline으로 사용 금지 표기
  - manifest.yaml의 directory_layout 섹션 갱신
  - runbook의 WF2/WF3 경로 참조 갱신
  - parse_step21_run.py의 입출력 경로를 runs/ 구조와 호환되도록 수정
- **완료 기준**: A1 runner 산출물과 기존 운영 문서 체계가 정합
- **의존**: A1, A3

---

## Phase B — First Admissible Run (2주 이내)

> 목표: profitability control pack으로 첫 campaign-native benchmark diagnostic run 완성
> 전제: Phase A 완료

### B1. Benchmark diagnostic single run (WF2)
- **산출물**: `_coord/campaigns/C2026Q1_stage1_refresh/runs/RUN_<ts>/` 전체
- **내용**: `triple_sigma_pack_step15_q1` (profitability pack)으로 benchmark window 실행
- **완료 기준**: run_manifest.json + raw + hash + compile log 모두 campaign workspace 내 존재
- **의존**: A1, A2, A3

### B2. WF3 parse on campaign-native raw
- **산출물**: `runs/RUN_<ts>/30_parsed/` (parse_manifest, coverage_manifest, master tables, counterfactual, daily_risk)
- **완료 기준**: validator가 provenance check 통과, close-before-modify=0, unmapped ENTRY=0
- **의존**: B1, A4, A5

### B3. KPI semantics 분리
- **산출물**: `tools/build_daily_risk_metrics.py` 수정 또는 `tools/build_kpi_summary.py` 신규
- **내용**:
  - global_trade_profit_factor (true trade-level PF)
  - combined_window_profit_factor
  - avg_daily_profit_factor (현재값, 명칭 변경)
  - expectancy_r (initial-risk-normalized)
- **완료 기준**: promotion report에서 daily average PF를 aggregate PF처럼 표기하지 않음
- **의존**: B2
- **Finding**: F7

### ~~B4. pack_hash_manifest 생성~~ → A1에 통합됨
> Codex 최종 리뷰: A1 산출물에 이미 pack_hash_manifest.json이 포함되어 있으므로 B4는 중복. A1/A3에서 커버.

### B4. STALE checklist 전면 갱신
- **산출물**: `_coord/ops/STEP21_OPS_CHECKLIST_v2.md` 최종 갱신
- **내용**: B2 결과 반영하여 CP0~CP4 상태 재평가
- **의존**: B2

### B6. RETAINED_ARTIFACT_STANDARD Step21 확장
- **산출물**: `_coord/ops/RETAINED_ARTIFACT_STANDARD.md` 수정
- **내용**: step21 packager의 SHA-256/manifest/broker stats 범위 반영
- **의존**: 없음

---

## Phase B+ — 에이전트 인프라 (Phase B와 병행, B1 이후 시작)

> 목표: writer/validator 분리를 코드로 강제, 자동화 기반 마련
> Codex 합의: "정책은 A, skills/hooks 구현은 B1~B3 뒤" (runner/validator contract 확정 후)

### B+1. 핵심 skills 구현
- **산출물**: `.claude/skills/` 아래 우선 구현 대상
  - `campaign-bootstrap` — 신규 campaign workspace 초기화
  - `campaign-run-sealer` — run 완료 후 hash sealing + manifest 생성
  - `integrity-gate` — CP1/CP4 strict validator 실행
  - `parser-replay` — raw → parsed 재실행
- **완료 기준**: campaign run의 핵심 단계가 skill로 호출 가능
- **의존**: A1, A2 (runner/validator contract 확정)

### B+2. 핵심 hooks 구성
- **산출물**: `.claude/hooks/` 구성
  - `post-run` — raw completeness + hash sealing + compile log copy
  - `post-parse` — CP1/CP4 strict validator + coverage gate + KPI summary
- **완료 기준**: run/parse 이후 자동 검증 trigger
- **의존**: B+1

### B+3. Codex validator thread 설정
- **산출물**: Codex CLI read-only validator 구성
- **내용**: frozen evidence bundle만 읽어 validator_report.json 생성
- **완료 기준**: writer agent가 자기 결과를 자기가 승인하는 경로 차단
- **의존**: B2 (검증 대상 evidence 존재)
- **Finding**: F6

### B+4. Artifact retention 구조
- **산출물**: campaign run workspace 템플릿
  ```
  runs/RUN_<ts>/
    00_request/    — candidate spec, operator config
    10_compile/    — compile log, terminal build info
    20_raw/        — immutable raw tester outputs
    21_hash/       — raw_hash_manifest, pack_hash_manifest
    30_parsed/     — parser outputs
    40_kpi/        — kpi summary, branch decision packet
    50_validator/  — validator report, signatures
    60_decision/   — pass/fail decision, override record
  ```
- **의존**: A1

---

## Phase C — Branch Decision (3주)

> 목표: 첫 admissible baseline에서 ML-first vs EA-first 결정
> 전제: Phase B 완료 (admissible benchmark diagnostic run 존재)

### C1. KPI summary + branch decision packet
- **산출물**:
  - `tools/build_kpi_summary.py`
  - `tools/build_branch_decision_packet.py`
  - `_coord/ops/schemas/kpi_summary.schema.json` (S4)
- **내용**: trade-level PF, expectancy, drawdown, dispersion, short-side coverage, gate regret, exit cost, modify tradeoff
- **완료 기준**: `runs/RUN_<ts>/40_kpi/kpi_summary.json` + `branch_decision_packet.json` 생성
- **의존**: B1, B2, B3

### C2. ML-first vs EA-first 결정 (WF4)
- **산출물**: `reports/branch_decision_memo.md`
- **내용**: Audit 섹션 9.2 decision routing 기준 적용
  - Stage1 eligible_candidate_count=0 → ML-first prior
  - gate regret / exit cost / modify tradeoff 비교
- **완료 기준**: 한 개의 primary branch만 open, 근거 문서화
- **의존**: C1

### C3. RC/RB bundler dry-run skeleton
- **산출물**: `tools/bundle_rc.py`, `tools/bundle_rollback.py` 초안
- **내용**: full production이 아닌 schema + placeholder 생성 수준
- **스키마**:
  - `_coord/ops/schemas/rc_manifest.schema.json` (S5)
  - `_coord/ops/schemas/rollback_manifest.schema.json` (S6)
- **완료 기준**: dry-run 시 skeleton bundle이 `_coord/releases/`, `_coord/rollback_points/`에 생성됨
- **의존**: S5, S6
- **Finding**: F4
- **Codex 합의**: "full production은 D, skeleton은 shortlist 전에"

### C4. Short-side sufficiency gate
- **산출물**: KPI summary에 short-side coverage/trade threshold 추가
- **내용**: benchmark+OOS short-side closed trades ≥ 10% 또는 explicit waiver (Audit 섹션 10.13)
- **의존**: C1
- **Finding**: F7

---

## Phase D — Promotion Infrastructure (1개월)

> 목표: autonomous optimization loop 가동 가능 상태
> 전제: Phase C 완료 (branch decision 확정)

### D1. RC/RB bundler 완성
- **산출물**: `tools/bundle_rc.py`, `tools/bundle_rollback.py` production grade
- **내용**: model pack + preset + runtime patch + KPI snapshot + SHA-256 + reproducibility rerun
- **완료 기준**: RC마다 matching rollback point 자동 생성, hash 검증 통과
- **Finding**: F4

### D2. Independent validator workflow (dual-signature)
- **산출물**: validator_report.json + validator_signature.json + promotion_decision.json
- **내용**: Codex validator가 frozen evidence 재검증 → writer + validator manifest 일치 시에만 WF8/WF9 통과
- **완료 기준**: writer self-promotion 불가
- **Finding**: F6

### D3. Manifest-driven orchestrator
- **산출물**: `tools/run_step21_matrix.ps1` 대체 또는 보완
- **내용**: environment-specific path를 operator config로 분리, manifest window alias 기반 실행
- **완료 기준**: 동일 명령이 다른 호스트에서 path 수정 없이 실행 가능
- **Finding**: F5

### D4. Broker-audit shadow run
- **산출물**: audit_master > 0인 campaign run 1회
- **내용**: current audit_master=0 상태 해소, broker audit surface 실증
- **완료 기준**: audit_master parquet에 실제 broker audit 데이터 존재
- **Codex 발견**: Step21 audit surface는 tester-validated이나 실제 run 증거 부재

### D5. 나머지 에이전트 인프라
- **산출물**: `.claude/skills/` 나머지 (ml-export-parity, pack-hash-capture, rc-bundle-assembly, rollback-bundle-verify, stale-doc-detector, kpi-branch-decision, mt5-preset-builder)
- **산출물**: `.claude/hooks/` 나머지 (pre-run, pre-promotion, post-rollback)
- **산출물**: MCP 연동 (thread-bridge, signing/hash 등)
- **완료 기준**: Audit 섹션 8.3~8.5 전체 커버

---

## 의존관계 그래프

```
A0 (정책) ──────────────────────────────────────┐
A3 (schema 3개) ─→ A1 (runner) ─→ A2 (validator) │
A4 (hard fail) ──┐                                │
A5 (contract v2) ┤                                │
                 ↓                                │
           B1 (first run) ─→ B2 (parse) ──────────┤
                 │              ↓                  │
                 │         B3 (KPI fix)            │
                 │              ↓                  │
                 └─→ B4 (pack hash)                │
                                                   │
           B+1~B+4 (에이전트 인프라) ←── B1 이후 병행
                                                   │
           C1 (KPI summary) ←── B2, B3             │
                 ↓                                 │
           C2 (branch decision) ←── C1             │
           C3 (RC/RB skeleton) ←── S5, S6          │
                 ↓                                 │
           D1~D5 (promotion infra) ←── C 전체      │
```

---

## 뒤로 미룰 것 (Audit + Codex 합의)

- notebooks / dashboard polish
- broad joint sweep search
- broker-connected live probes
- Optuna orchestration module

현재 bottleneck은 insight 부족이 아니라 **admissible evidence manufacturing 부족**이므로, 분석 도구보다 생산 인프라를 먼저 구축.

---

## Quantitative Acceptance Criteria

> Audit Report 섹션 10 참조. 주요 hard gate만 요약:

| Gate | Benchmark | OOS | Type |
|------|-----------|-----|------|
| Global trade-level PF | ≥ 1.15 | ≥ 1.05 | Hard |
| Expectancy | ≥ +0.05R | ≥ +0.02R | Hard |
| Max equity DD | ≤ 8% | ≤ 10% | Hard |
| Closed trades | ≥ 250 | ≥ 150 | Hard |
| OOS PF / Benchmark PF | — | ≥ 0.75 | Hard |
| Short-side trades (two-sided claim) | ≥ 10% | ≥ 10% | Hard |
| Worst regime PF (n≥30) | ≥ 0.90 | — | Hard |
| Regime PnL HHI | ≤ 0.30 | — | Hard |
