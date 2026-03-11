# STEP07. model-pack 로딩 + Stage1/Stage2 호출 인터페이스 확정

- 목적: regime별(two-stage) model-pack(총 12개)을 안정적으로 로드하고, EA에서 built-in MQL5 ONNX API로 추론을 수행할 수 있는 인터페이스를 확정한다.

---

## 1) 범위
- model-pack 디렉토리 탐색 및 파일 검증(12개)
- `pack_meta.csv` 로드(버전/threshold)
- built-in MQL5 ONNX 핸들 생성/캐시
- I/O shape/dtype 정적 검사
- 실패 시 PASS-only로 안전 전환

---

## 2) 입력 / 출력
### 입력
- model-pack 디렉토리
  - `clf_reg{0..5}_vXXX.onnx` (Stage1)
  - `prm_reg{0..5}_vXXX.onnx` (Stage2)
  - `pack_meta.csv` (필수)
  - `scaler_stats.json` (필수)
    - 형식: `mean[12]` + `std[12]`
    - 적용 범위: feature 0~11만 표준화, feature 12~21은 원형 유지
  - (선택) `gate_config.json`

### 출력
- regime_id별 Stage1/Stage2 세션 핸들(또는 래퍼)
- 버전 메타(model_pack_version, clf_version, prm_version, schema_version, cost_model_version)
- PASS-only 전환 여부 및 reason

---

## 3) 고정 규칙(Invariants)
- 12개 ONNX, `pack_meta.csv`, `scaler_stats.json` 중 1개라도 누락/로드 실패 → PASS-only
- I/O가 Contract와 다르면 → PASS-only
- `scaler_stats.json` 길이 불일치/비정상 std(<=0)/파싱 실패 → PASS-only
- runtime에서 shape/dtype/NaN/Inf 이상 → PASS-only

---

## 4) 구현(결정 사항)

### 4.1 ONNX 연동 방식(최종 결정)
- 결정: **MQL5 built-in ONNX API 사용**
  - canonical backend: `OnnxCreate`, `OnnxSetInputShape`, `OnnxRun`, `OnnxRelease`
  - output 검증: 현재 런타임은 output-shape 강제보다 smoke-run 검증을 기본으로 사용
  - 필요 시 `OnnxGetInputTypeInfo` / `OnnxGetOutputTypeInfo`로 I/O 검증을 더 강화할 수 있음

### 4.2 로딩 전략
- OnInit에서:
  - pack_meta 로드 → threshold/버전 확보
  - 12개 모델 모두 세션 생성(초기 비용은 있지만 런타임 단순화)
- OnDeinit에서 세션/리소스 정리(메모리 누수 방지)

### 4.3 버전 메타 취득 규칙
- 1순위: pack_meta.csv 값
- 2순위: 파일명 파싱(보조)
- 로그에는 항상 pack_meta 기반 버전을 남긴다(재현성)

---

## 5) 검증 체크리스트(권장)
- 파일 존재/권한/경로 확인
- Stage1 출력이 [1,3]인지 확인
- Stage2 출력이 [1,6]인지 확인
- 입력이 [1,64,22] float32인지 확인
- 모델 로드/추론 예외 발생 시 “거래 대신 PASS”로 귀결되는지 확인

---

## 6) 로깅(권장)
- `pass_only_mode`, `pass_only_reason`
- `model_pack_version`, `schema_version`, `cost_model_version`
- `clf_version`, `prm_version`
- pack_meta에서 로드한 threshold(atr_thr/adx_thr1/adx_thr2)

---

## 7) 테스트/검증(Acceptance)
- [A1] 모델 1개만 누락되어도 신규 진입이 0(PASS-only)
- [A2] shape/dtype 불일치 시 PASS-only + reason 로그
- [A3] regime별로 올바른 모델 선택이 되는지(세션 매핑 테스트)

---

## 8) 구현 메모
- 실제 운영에서는 model-pack 교체(롤백/업데이트)가 자주 일어날 수 있으니,
  - “재로딩” 전략(파일 변경 감지 후 안전 재로딩)은 STEP16에서 최적화로 다룬다.
