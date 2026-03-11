# EA-ONNX 조립 규격서(Contract) v0.1.1

- 기준일: 2026-03-04
- 목적: EA와 ONNX 모델이 서로 독립 개발해도 **반드시 조립 가능**하도록 I/O 스키마와 불변 규칙을 고정한다.
- 패턴: Pattern C (Hybrid) 고정

> ⚠️ 이 문서는 Candidate 1,1 허용 등 문서들에 섞여 있던 불일치를 제거하고, **EA↔ONNX 조립 규칙을 단일 기준으로 고정한 계약 확정본**이다. (구버전/초안 문서는 별도 보관)

---

## 1. 시스템 정체성
- EA: 실행 엔진 + 하드 안전벨트(비용/제약/리스크/시간 필터, 주문 실행, 로그)
- ONNX: 거래 여부/방향(PASS/LONG/SHORT) + 운용 파라미터(SL/TP/보유시간) 산출

---

## 2. 실행 타이밍(고정)
- 의사결정 타이밍: **새 5분봉 확정(바 마감) 시점에 1회**
- 모델 호출: **매 바 실행**(후보 없어도 실행; cand=0이면 신규진입은 금지되지만 추론/로그는 수행)

---

## 3. 실패/예외 시 안전 동작(고정)
아래 중 하나라도 발생하면 EA는 **무조건 PASS(신규 진입 금지)** + 로그를 남긴다.
- 모델 로드/추론 실패
- 입력/출력 텐서 shape 또는 dtype 불일치
- 입력/출력에 NaN/Inf 존재
- 출력 확률 합이 비정상(합이 0 또는 과도하게 벗어남 등)

### 3.1 확률 유효성 검증 순서(고정) — v0.1.2 확정
아래 순서대로 검사하며, 하나라도 실패 시 즉시 PASS + 로그.

1. **NaN/Inf 체크**: p_long, p_short, p_pass 중 하나라도 NaN 또는 Inf → PASS
2. **범위 체크**: 각 확률이 [0.0, 1.0] 범위를 벗어남 → PASS
3. **합 체크**: abs(p_long + p_short + p_pass - 1.0) > 0.01 → PASS

경고 로그(진입은 허용):
- 0.005 < abs(합 - 1.0) <= 0.01 이면 PASS는 아니지만 warn 로그 기록 권장

근거: float32 softmax 직렬화 오차는 통상 1e-6~1e-4 수준이므로, 0.01은 충분한 여유.

---

## 4. I/O 스키마(핵심 계약)

### 4.1 Input 텐서 X
- dtype: float32
- shape: **[1, 64, 22]**
- time axis:
  - X[0,0,:] = 가장 과거 바
  - X[0,63,:] = 가장 최근 확정 바  
  (과거 → 현재 순)

> 전처리(피처 계산/정규화/결측 처리)는 EA에서 완료 후 모델에 전달한다.  
> 입력 표준화는 model-pack의 필수 파일 `scaler_stats.json`을 기준으로 수행한다.  
> `scaler_stats.json` 형식은 `mean[12]` + `std[12]`이며, feature 0~11에만 적용하고 feature 12~21은 원형 그대로 유지한다.  
> `scaler_stats.json` 누락/파싱 실패/길이 불일치/비정상 std(<=0) 시 EA는 PASS + 로그로 안전 전환한다.

### 4.2 Output 텐서 Y
- dtype: float32
- shape: **[1, 6]**
- 의미:  
  Y = [p_long, p_short, p_pass, k_sl, k_tp, hold_bars]

규칙:
- 확률: p_long + p_short + p_pass = 1 (확률로 해석 가능해야 함)
- k_sl: 클램프 [0.5, 6.0]
- k_tp: 클램프 [0.5, 12.0]
- hold_bars: 클램프 [1, 72], EA에서 정수화(round) 후 사용

---

## 5. Feature Catalog v0.1 (F=22)

피처 index(0~21)는 계약이며, 순서 변경/삭제/의미 변경 금지. 추가는 맨 뒤 append-only.

### 5.1 공통 계산 규칙(고정)
- price_basis: **Bid 기준**  
  - bar OHLC 및 지표 계산은 Bid 기준으로 한다.
- 모든 피처는 bar close 확정값 기준으로 계산한다(재현성).
- spread_price_t = Ask_t - Bid_t (bar close 시점)
- eps = 1e-9 (0 나눗셈 방지)
- 지표(공통):
  - EMA20, EMA50: close 기반 EMA
  - RSI14: close 기반 RSI
  - ATR14: true range 기반 ATR(14)
  - ADX14: 표준 ADX(14)

> EA는 피처 계산 시 NaN/Inf를 생성하지 않도록 방어해야 하며, 생성 시 해당 바는 PASS 처리(Contract 3절).

### 5.2 피처 index 정의(0~13)
0) ret_1   = ln(C_t / max(C_{t-1}, eps))  
1) ret_3   = ln(C_t / max(C_{t-3}, eps))  
2) ret_12  = ln(C_t / max(C_{t-12}, eps))

3) range_atr = (H_t - L_t) / max(ATR14_t, eps)  
4) body_atr  = (C_t - O_t) / max(ATR14_t, eps)

5) close_pos = 2 * ((C_t - L_t) / max(H_t - L_t, eps)) - 1  
   - 범위: [-1, +1]  
   - -1에 가까울수록 저가 부근 종가, +1에 가까울수록 고가 부근 종가

6) ema20_dist = (C_t - EMA20_t) / max(ATR14_t, eps)  
7) ema50_dist = (C_t - EMA50_t) / max(ATR14_t, eps)  
8) ema20_slope = (EMA20_t - EMA20_{t-1}) / max(ATR14_t, eps)

9) rsi_norm = (RSI14_t - 50) / 50  
   - 범위: [-1, +1]

10) adx_norm = ADX14_t / 100  
   - 범위: [0, +1]

11) spread_atr = spread_price_t / max(ATR14_t, eps)

시간피처(서버타임, bar close timestamp 기준):
- minute_of_week = weekday*1440 + hour*60 + minute  (0~10079)
  - weekday는 월요일=0 … 일요일=6 (ISO week 기준)
12) time_sin = sin(2*pi*minute_of_week / 10080)  
13) time_cos = cos(2*pi*minute_of_week / 10080)

### 5.3 Regime one-hot (index 14~19) — 6버킷(ADX 3단 × ATR 2단)
regime_id는 0~5 정수이며, one-hot으로 인코딩한다.

- atr_pct_t = ATR14_t / max(C_t, eps)
- ATR 2단(threshold 1개):
  - atr_bin = 0 if atr_pct_t < atr_thr else 1
- ADX 3단(threshold 2개):
  - adx_bin = 0 if ADX14_t < adx_thr1
  - adx_bin = 1 if adx_thr1 <= ADX14_t < adx_thr2
  - adx_bin = 2 if ADX14_t >= adx_thr2
- regime_id = adx_bin*2 + atr_bin

threshold(atr_thr, adx_thr1, adx_thr2)는 **학습/배포 단위(model-pack)에서 고정**이며,
EA 런타임과 학습 파이프라인이 동일 값을 사용해야 한다(정합성).

피처:
14) reg_0 = 1 if regime_id==0 else 0  
15) reg_1 = 1 if regime_id==1 else 0  
16) reg_2 = 1 if regime_id==2 else 0  
17) reg_3 = 1 if regime_id==3 else 0  
18) reg_4 = 1 if regime_id==4 else 0  
19) reg_5 = 1 if regime_id==5 else 0  

### 5.4 Candidate (index 20~21)
- cand_long / cand_short는 float32(0 또는 1)로 인코딩한다.
- Candidate 생성 규칙(수식/기본값)은 `EA_RUNTIME.md`를 단일 출처로 한다.
- 단, 아래 불변 규칙은 계약(Contract)으로 고정한다:
  - (cand_long, cand_short) ∈ {(0,0), (1,0), (0,1)}
  - (1,1)은 금지(INVALID_CAND)

20) cand_long  
21) cand_short

---

## 6. Candidate(후보) 불변 규칙 (Policy Freeze 반영)

### 6.1 허용되는 후보 상태(one-hot-or-zero)
- (cand_long, cand_short) ∈ {(0,0), (1,0), (0,1)}

### 6.2 금지 상태
- (1,1)은 **금지(INVALID_CAND)**  
  - 발생 시 EA는 PASS 처리 + 로그(`invalid_cand=1` 같은 플래그 권장)

### 6.3 후보 경계(신규 진입)
- cand_long=0 AND cand_short=0 이면 **신규 진입 금지(PASS)**  
  - 단, 모델은 실행하고 결과는 로그에 남긴다(학습/디버깅 목적).

---

## 7. 모델 방향 선택 및 Flip(조건부)

### 7.1 모델 방향 선택
- model_dir = argmax(p_long, p_short, p_pass)
- model_dir == PASS면 진입하지 않는다.

### 7.2 조건부 Flip(후보와 반대 방향은 “강한 근거”가 있을 때만)
기본 파라미터:
- p_min_trade = 0.55
- delta_flip = 0.20

규칙:
- cand_long=1, cand_short=0일 때 model_dir=SHORT이면:
  - p_short >= p_min_trade AND (p_short - p_long) >= delta_flip → SHORT Flip 허용
  - 아니면 PASS
- cand_short=1, cand_long=0일 때 model_dir=LONG이면:
  - p_long >= p_min_trade AND (p_long - p_short) >= delta_flip → LONG Flip 허용
  - 아니면 PASS

> (cand_long=1 AND cand_short=1) 케이스는 본 문서에서 **금지**이므로 Flip 규칙에도 존재하지 않는다.

---

## 8. PASS일 때 파라미터 기본값(외부 인터페이스 shape 유지 목적)
모델 또는 EA 조립 결과가 PASS인 경우에도 Y는 [1,6] shape를 유지해야 한다.  
따라서 PASS 시 파라미터는 아래 기본값으로 채운다.

- k_sl_default = 1.5
- k_tp_default = 2.0
- hold_default = 24

---

## 9. 보유시간 상한(정합성 규칙)
- hold_bars는 [1,72]로 클램프한다.
- 운영에서의 **총 보유시간(bars_held)은 72 bars를 초과할 수 없다.**
  - 72에 도달하면 EA는 FORCE_EXIT 처리한다.  
  - (soft hold / extend 로직이 있어도, 최종 상한은 72)

---

## 10. 스키마 버전 규칙
- schema_major 변경: T/F/K 변경, index 의미 변경/순서 변경, 레짐 차원 변경 등
- schema_minor 변경: 맨 뒤 피처 append-only  
  (EA/모델은 동일 minor를 사용해야 함)

> Runtime log naming note:
> Current `bar_log` uses `final_dir`, `k_sl_req`, `k_tp_req`, `k_sl_eff`,
> `k_tp_eff`, and `hold_bars` instead of older abstract names such as
> `action`, `onnx_k_sl`, `onnx_k_tp`, and `onnx_hold_bars`.
> See `design/BAR_LOG_SCHEMA.md` for the current mapping.
