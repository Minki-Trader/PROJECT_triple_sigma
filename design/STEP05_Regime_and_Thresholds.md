# STEP05. Regime 산출 + one-hot(14–19) 반영 + threshold 정합성 고정

- 목적: regime_id(0~5)를 Contract/EA_RUNTIME의 동일 식으로 계산하고, threshold를 model-pack 단위로 고정한다.

---

## 1) 범위
- `pack_meta.csv` 로드(필수) 및 검증
- atr_thr/adx_thr1/adx_thr2 적용
- regime one-hot(feature[14..19]) 업데이트
- threshold 산출 방법 메타(thr_method 등) 로깅(권장)

---

## 2) 입력 / 출력
### 입력
- ATR14_t, ADX14_t, Close_t (Bid 기준)
- `pack_meta.csv` (atr_thr, adx_thr1, adx_thr2 포함)

### 출력
- regime_id (0~5)
- feature[14..19] one-hot
- bar_log: atr_thr/adx_thr1/adx_thr2, thr_method(선택)

---

## 3) 고정 규칙(Invariants)
- threshold는 **model-pack 단위로 고정**
- `pack_meta.csv` 로드 실패 시: PASS-only + 로그
- one-hot은 반드시 1개만 1 (나머지 0)

---

## 4) threshold 소스 및 메타

### 4.1 필수: 값
- atr_thr
- adx_thr1
- adx_thr2

### 4.2 선택: 산출 방법 메타(권장)
- thr_method: `quantile` / `performance_search` / `manual`
- thr_seed, thr_search_space_version, thr_notes

> 중요: “값 정합성”이 핵심이며, thr_method는 재현성을 위한 보조 정보.

---

## 5) regime 계산
- atr_pct_t = ATR14_t / max(C_t, eps)
- atr_bin = 0 if atr_pct_t < atr_thr else 1
- adx_bin = 0 if ADX14_t < adx_thr1  
- adx_bin = 1 if adx_thr1 <= ADX14_t < adx_thr2  
- adx_bin = 2 if ADX14_t >= adx_thr2  
- regime_id = adx_bin*2 + atr_bin

---

## 6) 로깅(권장)
- `regime_id`
- `atr_pct_t`, `atr_bin`, `adx_bin`
- `atr_thr`, `adx_thr1`, `adx_thr2`
- (선택) `thr_method`

---

## 7) 테스트/검증(Acceptance)
- [A1] pack_meta 없으면 임시 threshold를 쓰지 않고 PASS-only로 떨어짐
- [A2] one-hot 무결성(합=1, 값은 0/1)
- [A3] 동일 bar_log 입력으로 동일 regime_id 재현 가능

---

## 8) 구현 메모
- threshold는 “훈련 분포 기반”이든 “성능 최적화 기반”이든 상관없이,
  - 런타임과 학습이 같은 값을 쓰는 것이 최우선이다.
