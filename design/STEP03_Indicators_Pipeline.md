# STEP03. 지표(EMA/RSI/ATR/ADX) 계산 파이프라인 구축

- 목적: Contract/EA_RUNTIME에서 요구하는 지표(EMA20/50, RSI14, ATR14, ADX14)를 **Bid 기반, bar close 확정값**으로 안정적으로 산출한다.

---

## 1) 범위
- MT5 내장 지표 핸들 생성/재사용
- CopyBuffer 기반 값 수집 + 시계열 정렬
- NaN/Inf 방어 및 워밍업 처리
- 지표 값을 bar_log에 기록(학습 재현 목적)

---

## 2) 입력 / 출력
### 입력
- 64-bar Bid OHLC(확정 바)
- timeframe=5m

### 출력
- 각 바 t에 대해:
  - EMA20_t, EMA50_t
  - RSI14_t
  - ATR14_t
  - ADX14_t
- (품질 플래그) `indicators_ready`, `indicator_nan_inf_flag`

---

## 3) 고정 규칙(Invariants)
- price_basis: Bid
- 지표는 bar close 확정값 기반(재현성)
- NaN/Inf 발생 시: 해당 바는 PASS-only 경로로 유도(Contract fail-safe)

---

## 4) 설계(결정 사항)

### 4.1 구현 방식
- 권장: MT5 기본 지표(iMA/iRSI/iATR/iADX) + CopyBuffer
- 핸들은 OnInit에서 1회 생성하고 재사용(성능/안정)

### 4.2 워밍업
- 최소 워밍업 바 수는 문서에 고정값이 없음  
  - 권장: EMA50 안정화까지 고려해 100~200 bars 확보 후 `indicators_ready=1`
- 워밍업 동안은 신규 진입 금지(PASS-only)

### 4.3 시계열 정렬
- CopyBuffer 결과의 인덱스가 “현재=0”인 경우가 많으므로,
  - 항상 “64 bars 과거→현재”로 재정렬하여 사용
- 지표/바 데이터 time alignment를 검사(바 time이 동일한지)

---

## 5) 로깅(필수/권장)
bar_log에 최소 아래를 기록:
- ATR14, ADX14 (regime 계산에 직접 사용)
- EMA20, EMA50, RSI14 (candidate/피처 계산에 직접 사용)

권장:
- `indicators_ready`
- `nan_inf_detected`
- `warmup_bars_used`

---

## 6) 테스트/검증(Acceptance)
- [A1] 64-bar 구간에서 지표가 NaN/Inf 없이 산출
- [A2] 지표 time alignment가 bar close time과 일치
- [A3] 워밍업 미충족 시 신규 진입이 0(PASS-only)

---

## 7) 구현 메모
- ADX는 여러 버퍼(+DI/-DI/ADX 등)로 나오므로, “ADX main line” 버퍼 인덱스를 정확히 고정한다.
