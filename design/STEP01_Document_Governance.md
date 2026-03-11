# STEP01. 문서 우선순위와 버전/스키마 상수 고정

- 기준 문서: `POLICY_FREEZE.md` → `CONTRACT.md` → `EA_RUNTIME.md` → `ONNX_DEV_SPEC.md`
- 목적: “조립 가능한 시스템”을 깨뜨리는 **문서/버전/스키마 불일치**를 런타임/학습/리뷰 단계에서 선제 차단한다.

---

## 1) 범위
- 문서 우선순위를 코드/리뷰 규칙으로 고정
- 런타임/학습/패키징에서 공통으로 사용할 **버전/스키마 메타** 정의
- PASS-only 상태 머신(안전벨트) 정의

비범위:
- 개별 지표 계산/피처 계산(다음 STEP에서 처리)
- 모델 아키텍처(학습 STEP에서 처리)

---

## 2) 입력 / 출력

### 입력
- `POLICY_FREEZE.md` (Q1~Q10 정책 고정)
- `CONTRACT.md` (X/Y 스키마, 피처 index, clamp, fail-safe)
- `EA_RUNTIME.md` (런타임 플로우, gate, 로그)
- `ONNX_DEV_SPEC.md` (라벨링/학습/패키징)

### 출력(산출물)
- (코드 상수) `schema_version`, `candidate_policy_version`, `regime_policy_version`, `cost_model_version`
- (런타임 상태) `pass_only_mode` 전환 조건 및 로그 필드
- (테스트) “문서 우선순위 위반”을 막는 정적/동적 체크 항목

---

## 3) 고정 규칙(Invariants)
- Contract I/O는 절대 변경 금지:
  - X: float32 [1,64,22] (time axis 과거→현재)
  - Y: float32 [1,6] = [p_long,p_short,p_pass,k_sl,k_tp,hold_bars]
- 실패/예외 시: **무조건 PASS + 로그**
- price_basis: **Bid**
- cand: **one-hot-or-zero**, (1,1) 금지, cand=0은 신규진입 금지(모델은 실행/로그)

---

## 4) 설계(결정 사항)

### 4.1 문서 우선순위 적용 방식
- 코드 리뷰 규칙:
  - “애매하면” 상위 문서가 이긴다.
  - 특히 다음 키워드가 나오면 `CONTRACT.md`/`POLICY_FREEZE.md`를 최우선으로 확인:
    - shape, dtype, clamp, cand 규칙, 72 cap, PASS default
- 런타임 규칙:
  - `schema_version` 불일치/미확인 → PASS-only
  - model-pack 메타 로드 실패 → PASS-only

### 4.2 버전/스키마 메타(로그/학습 공통)
필수 메타(로그에 남기고, 학습 산출물에도 포함):
- `ea_version` (EA 빌드/배포 버전)
- `schema_version` (Contract 규칙에 따름)
- `candidate_policy_version` (예: 0.1.2)
- `regime_policy_version` (예: 0.1.0q)
- `model_pack_version`
- `clf_version`, `prm_version`
- `cost_model_version`

권장 메타(재현성 향상):
- threshold 메타: `thr_method`, `thr_seed` 등
- scaler 메타: `feature_scaler_version` 또는 `scaler_stats_sha`
- gate 메타: `gate_config_version` 또는 `gate_config_sha`

---

## 5) PASS-only 상태 머신(핵심)
PASS-only는 “장애”가 아니라 “안전벨트 정상 동작”으로 취급한다.

### PASS-only 진입 트리거(예시)
- model-pack 12개 중 1개라도 로드 실패
- `pack_meta.csv` 로드/파싱 실패
- X/Y shape/dtype 불일치
- NaN/Inf 감지
- 확률합 비정상(합=0 또는 지나치게 벗어남)
- 버전/스키마 불일치 감지

### PASS-only 동작
- 신규 진입 0 (항상 PASS)
- 단, bar_log는 계속 기록(원인 추적/학습 재현 목적)
- (권장) PASS-only 원인 코드를 `pass_only_reason`로 남김

---

## 6) 테스트/검증(Acceptance)
- [A1] X/Y shape/dtype 검증 실패 시 “주문이 0”임을 보장
- [A2] pack_meta 누락 시 regime 산출 대신 PASS-only로 떨어짐
- [A3] 문서 우선순위 충돌(예: 다른 곳에서 cand=(1,1) 허용) 발견 시 빌드/리뷰에서 차단

---

## 7) 구현 메모
- schema_version 값 자체는 문서에 “규칙”만 있고 문자열 포맷은 팀 표준으로 고정 필요
- 추천: `pack_meta.csv`를 “단일 진실 소스”로 두고 런타임/학습 산출물 모두에 스냅샷 포함
