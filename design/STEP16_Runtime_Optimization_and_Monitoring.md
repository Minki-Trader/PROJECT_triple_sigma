# STEP16. 런타임 최적화(성능/안정) + 운영 모니터링 설계

- 목적: Contract와 현재 runtime semantics를 유지한 채, 운영 가시성과
  로그 I/O 효율을 개선한다.

> Current scope note:
> The first STEP16 baseline is intentionally narrow.
> It does not change trading semantics, model-pack semantics, or CSV schema.
>
> Phase status note:
> - STEP16 phase-1 is implemented and closed out as runtime/logging hardening.
> - STEP16 phase-2 is implemented as a non-executable seam/refactor checkpoint:
>   post-decision seam refactor + shadow-only Early Exit observability, with
>   live trade semantics intentionally unchanged.
> - STEP16 phase-2 is closed as the baseline seam/refactor checkpoint.
> - STEP17 builds on that seam to add the first minimal live Early Exit path.

---

## 1) 1차 baseline 범위
- 상위 문서와 현재 구현의 경계 정리
- `TS_Logger.mqh` 로그 핸들 수명주기 개선
- `TS_Execution.mqh`의 `exec_state.ini` 저장 시점 정리
- 세션 단위 경량 모니터링 요약 추가

---

## 2) 이미 충족된 항목(already satisfied)
- 지표 핸들 재사용(`OnInit()` 생성 후 재사용)
- Stage1이 PASS면 Stage2 미실행
- model-pack / scaler / gate config / ONNX load를 `OnInit()`에서 1회 수행
- 72-bar hard cap(`FORCE_EXIT`) 강제

위 항목은 STEP16의 신규 구현 대상이 아니라, 현재 baseline runtime이 이미
충족한 전제 조건으로 본다.

---

## 3) 1차 baseline 구현 포인트

### 3.1 Logger lifecycle
- `bar_log`:
  - 세션 동안 핸들 유지
  - 일자 변경 시 close/open rotation
  - 행마다 append 후 즉시 flush
- `trade_log`:
  - 세션 동안 핸들 유지
  - 이벤트마다 append 후 즉시 flush
- 공통:
  - 외부 tail/read를 위해 `FILE_SHARE_READ` 사용
  - 기존 CSV 컬럼과 파일명 규칙은 유지

### 3.2 exec_state durability
- `exec_state.ini`는 성능보다 복구 가치를 우선한다.
- 1차 baseline 저장 시점:
  - entry 확정 시
  - pending exit 상태 변경 시
  - bars_held 증가 시
  - exit 정리 시
  - deinit 시
- 같은 bar 안에서 의미 없는 중복 저장은 dirty flag로 줄인다.

### 3.3 Session monitor
- 새 CSV를 만들지 않는다.
- Experts log에 세션 요약 1줄만 주기적으로 출력한다.
- 최소 집계 항목:
  - processed bars
  - cand 분포 `(0,0) / (1,0) / (0,1)`
  - regime 분포 `0..5`
  - final_dir 분포 `PASS / LONG / SHORT`
  - flip_used count
  - gate_pass count
  - gate reject prefix 분포
  - hold_soft_reached count
  - force_exit count
  - soft_fault_total / last_soft_fault_reason
  - avg/max bar-processing time

---

## 4) 1차 baseline에서 제외(out of scope)
- Early Exit / BE / MODIFY 실제 동작
- runtime model-pack hot reload / rollback orchestration
- `bar_log` / `trade_log` 컬럼 추가
- STEP11~STEP15 산출물 의미 변경
- 재학습 / 재패키징 요구
- ONNX graph 최적화 연구
- `TS_Indicators.mqh`, `TS_Models.mqh`, `TS_PackMeta.mqh`, `TS_Gates.mqh`
  semantics 변경

---

## 4.5) Implemented STEP16 phase-2 scope (closed baseline)

Phase-2 goal:
- Keep live trading semantics unchanged.
- Prepare the runtime seam needed for any future live Early Exit family.
- Add shadow-only observability instead of executable exit behavior.

Implemented in-scope items:
- Split held-position management into:
  - pre-decision live management
  - post-decision shadow evaluation
- Keep current live behavior in the pre-decision path:
  - bars_held accounting
  - hold_soft observation
  - 72-bar `FORCE_EXIT`
- Add a post-decision shadow-only Early Exit evaluator that runs after
  current-bar inference/assembly.
- Add monitor counters for:
  - `gate_skipped`
  - `inference_not_ready`
  - `decision_not_ready`
  - `entry_attempted` / `entry_executed` / `entry_rejected`
  - `exit_attempted` / `exit_executed` / `exit_rejected`
  - retcode buckets
  - `last_non_none_soft_fault`
  - `shadow_exit_evaluated` / `shadow_exit_triggered`
  - shadow reason buckets and `min_hold_blocked`
- Add an `OnTradeTransaction()` observer as a first observer only.
- Keep `TS_SyncPositionState()` as reconciliation fallback.
- Harden `exec_state.ini` save path with temp-write plus replace-on-move.
- Prefer a separate session-summary artifact over widening core
  `bar_log` / `trade_log` schema.

Phase-2 out of scope:
- live Early Exit
- live BE / MODIFY
- `trade_log` `MODIFY` emission
- runtime hot reload / rollback
- core `bar_log` / `trade_log` schema expansion
- retraining / repackaging requirements
- ONNX graph optimization work

Phase-2 closeout evidence retained:
- compile clean
- pass-only smoke unchanged
- trade-producing smoke unchanged in live semantics
- shadow-only counters populated without emitting live `EARLY_EXIT`
- restart/recovery smoke after open-position and pending-exit points
- reject-path smoke remained recommended additional coverage because phase-2
  itself did not widen executable live semantics
- current schema remains unchanged unless a separate schema approval is made

---

## 5) 입력 / 출력

### 입력
- STEP01~15 구현체
- 운영 요구(로그 보존/성능/가시성)

### 출력
- mainline `bar_log` / `trade_log`의 불필요한 per-write open/close 제거
- `tensor_debug.csv` per-write 경로는 현재 baseline에서 유지
- 세션 단위 운영 요약 로그
- 복구 가치를 유지한 `exec_state.ini` 저장 경로

---

## 6) 고정 규칙(Invariants)
- Contract 위반(Shape/Dtype/Clamp/72 cap)은 어떤 최적화로도 허용되지
  않는다.
- 예외 발생 시 PASS-only + 로그는 유지한다.
- CSV schema는 1차 baseline에서 변경하지 않는다.
- scaler / model / pack load 시점은 계속 `OnInit()` only로 유지한다.

---

## 7) 수용 기준(Acceptance)
- [A1] EA compile clean
- [A2] 기존 runtime semantics 유지
- [A3] Stage1 PASS short-circuit 유지
- [A4] 72-bar hard cap 유지
- [A5] `bar_log`/`trade_log` 헤더 1회 기록 유지
- [A6] day rollover 시 `bar_log_YYYYMMDD.csv` rotation 정상 동작
- [A7] `exec_state.ini` 재시작 복구 정상 동작
- [A8] monitor summary가 주기적으로 출력되고 deinit 시 final summary 출력
- [A9] 현재 `bar_log` / `trade_log` schema 불변

---

## 8) 구현 메모
- 1차 STEP16은 “더 빠른 로그 처리 + 더 좋은 운영 요약 + 의미론 변화 0”을
  목표로 한다.
- 빠른 것보다 재현 가능한 것이 우선이며, 성능 최적화는 항상 버전/메타/로그와
  같이 가야 한다.
