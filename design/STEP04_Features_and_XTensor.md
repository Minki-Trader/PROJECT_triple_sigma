# STEP04. Contract 피처 22개 계산 + X 텐서 생성

- 목적: Contract의 Feature Catalog(v0.1, F=22)를 **인덱스 고정**으로 계산하고, X float32 [1,64,22]를 생성한다.

---

## 1) 범위
- 피처 0~21 계산(Contract 정의 그대로)
- 피처 표준화(mean/std) 적용(모델 내부 정규화 금지 원칙 준수)
- X 텐서 생성/검증(dtypes/shape/time axis)
- feature index 변경 방지 테스트

---

## 2) 입력 / 출력
### 입력
- 64-bar Bid OHLC
- 지표(EMA20/50, RSI14, ATR14, ADX14)
- regime_id(one-hot) [14..19]
- candidate(one-hot) [20..21]

### 출력
- X: float32 shape [1,64,22]
- bar_log: feature_0..21 기록(권장)

---

## 3) 고정 규칙(Invariants)
- Feature index(0~21)는 계약: **순서 변경/삭제/의미 변경 금지**
- 추가는 append-only만 허용(Contract schema_minor)
- eps=1e-9로 0 나눗셈 방지
- price_basis: Bid
- NaN/Inf 발생 시 PASS-only

---

## 4) 피처 정의(요약)
- 0~2: ret_1, ret_3, ret_12 (ln 수익률)
- 3~4: range_atr, body_atr
- 5: close_pos [-1,+1]
- 6~8: ema20_dist, ema50_dist, ema20_slope
- 9~10: rsi_norm, adx_norm
- 11: spread_atr
- 12~13: time_sin, time_cos (minute_of_week)
- 14~19: regime one-hot
- 20~21: candidate one-hot

(정확한 수식은 `CONTRACT.md`를 단일 기준으로 따른다.)

---

## 5) 표준화(필수 적용: 최종 결정)
- 결정: **EA에서 mean/std 표준화 적용** (모델 내부 스케일링 금지 원칙 유지)
- 근거:
  - 학습/배포 정합성을 EA에서 통제하기 쉬움
  - 필수 파일 `scaler_stats.json`으로 학습/배포 입력 분포를 고정 가능

### 표준화 규칙(권장)
- 대상: feature 0~11
- feature 12~21(time_sin/cos, regime one-hot, candidate)는 원형 그대로 유지
- 표준화 수식:
  - x' = (x - mean) / max(std, eps)
- 스케일러 소스:
  1) model-pack의 필수 파일 `scaler_stats.json`
- 스케일러 형식:
  - `mean[12]`
  - `std[12]`
- 스케일러 로드 실패 시:
  - **누락/파싱 실패/길이 불일치/비정상 std(<=0)는 PASS-only** (정합성 목적)

---

## 6) X 텐서 생성/검증
- dtype: float32 강제
- shape: [1,64,22] 강제
- time axis: 과거→현재 강제
- 검증 실패 시: PASS-only + 로그

---

## 7) 로깅(필수/권장)
필수(권장 최소):
- `feature_0..feature_21` (디버깅/학습 재현)
권장:
- `scaler_stats_version` 또는 `scaler_stats_sha`
- `x_nan_inf_flag`
- `x_order_check_ok`

---

## 8) 테스트/검증(Acceptance)
- [A1] 피처 인덱스가 계약과 정확히 일치(단위 테스트)
- [A2] X shape/dtype/order 검증 통과
- [A3] 표준화 통계가 다르면 스키마/버전 불일치로 감지 가능(로그)
- [A4] `scaler_stats.json` 누락/비정상 시 PASS-only 전환

---

## 9) 구현 메모
- 표준화는 “피처 계산 후”에 적용한다(수식 정의는 원본 값 기준 유지).
