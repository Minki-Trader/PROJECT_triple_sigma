# EA Runtime Spec v0.1.3 (통합 정합성 반영 + Gate/후보/주문 보정 업데이트)

- 기준일: 2026-03-04
- 범위: MT5 EA 런타임 동작(실행/게이트/포지션 운영/로그) 규격
- 상위 우선순위: `POLICY_FREEZE.md` → `CONTRACT.md` → 본 문서
- 패턴: Pattern C (Hybrid) 고정
- I/O: Input[1,64,22] / Output[1,6]

> 이 문서는 **본 패키지의 최종 EA 런타임 기준서**다.  
> 동일 주제가 다른 문서/메모에 다르게 적혀 있더라도, 개발/리뷰/운영은 `POLICY_FREEZE.md → CONTRACT.md → 본 문서` 순서로 해석한다.  
> (구버전/초안 문서는 별도 보관)

---

## 0. 이번 버전(v0.1.3)에서 달라진 점(요약)
1) Regime threshold 산출 방법을 `pack_meta.csv`의 선택 메타(`thr_method` 등)로 추적 가능(값 정합성은 기존과 동일)
2) Candidate 정책: dist_atr_max를 **Adaptive(분포 기반)로 운용 가능** (candidate_policy_version=0.1.2)
3) Gate 파라미터를 model-pack에 동봉하는 것을 지원(선택: `gate_config.json`)  
   - 운영 즉시 대응 값은 EA 파라미터로 분리 권장
4) 주문 제약(StopLevel/FreezeLevel 등) 미충족 시 **“최소 보정 시도 → 불가하면 PASS”** 로 강화
5) 로그 확장(권장): Stage2 raw 6값, 주문 보정 전/후 SL/TP, dist_atr_max_t 등 기록 가능

---

## 1. EA 전체 플로우(런타임)

### 1.1 OnNewBar(새 5분봉 확정) 1회 처리 흐름
1) 새 5분봉 확정 감지  
2) Bar 기반 피처 업데이트(Contract 22개, [64×22])  
3) Regime 산출(6버킷) 및 one-hot 업데이트  
4) Candidate 생성(cand_long/cand_short)  
5) ONNX 추론 실행(매 바 실행)  
6) 하드/동적 게이트(비용/리스크/시간/제약) 통과 여부 판단  
7) 신규 진입 또는 포지션 관리  
   - current runtime mode matrix:
     - `InpEarlyExitEnabled=false`:
       hold_soft_reached 관측 + 72-bar `FORCE_EXIT`
     - `InpEarlyExitEnabled=true`, `InpEarlyExitLive=false`:
       pre-decision live management + post-decision shadow-only Early Exit
       evaluation
     - `InpEarlyExitEnabled=true`, `InpEarlyExitLive=true`:
       same seam, plus minimal live Early Exit on `p_pass >= p_exit_pass`
       after `min_hold_bars_before_exit`
     - `InpEarlyExitEnabled=true`, `InpEarlyExitLive=true`,
       `InpEarlyExitOppositeEnabled=true`:
       close-only live Early Exit may use opposite-direction current decision
       before falling back to `p_pass >= p_exit_pass`
     - protective-adjust overlay:
       - `InpProtectiveAdjustEnabled=true`
       - live protective modify is evaluated only after the close-only Early
         Exit branch
       - currently implemented modify families:
         - `BREAK_EVEN`
         - `TRAILING`
         - `TP_RESHAPE`
         - `TIME_POLICY`
       - executed modifies emit `trade_log.csv` `MODIFY` rows
   - runtime extension surface:
     - `InpTxAuthorityEnabled=true` enables tx-authoritative entry / exit
       emission and state finalization
     - runtime model-pack hot reload / rollback is available through the
       Step21 patch-file flow
8) bar_log / trade_log 기록

> Current seam note:
> The current runtime manages held positions before current-bar inference and
> assembly. Any current-bar Early Exit family therefore requires a seam split
> first. The current runtime keeps live position accounting in the
> pre-decision path and runs Early Exit evaluation in the post-decision path.

---

## 2. Regime(시장 상태) 정책 (regime_policy_version=0.1.0q)

### 2.1 목적
- Regime은 “시장 상태”를 6개 버킷으로 나눠 model-pack(12개) 중 어떤 모델을 쓸지 결정한다.
- Regime 계산은 **EA 런타임과 학습 파이프라인이 동일해야 한다**(정합성).

### 2.2 지표/기준(고정)
- bar OHLC 및 지표는 Bid 기반(Contract의 price_basis 고정)
- ADX14_t, ATR14_t, Close_t는 bar close 확정값

### 2.3 계산식
- atr_pct_t = ATR14_t / max(C_t, eps)
- ATR 2단:
  - atr_bin = 0 if atr_pct_t < atr_thr else 1
- ADX 3단:
  - adx_bin = 0 if ADX14_t < adx_thr1
  - adx_bin = 1 if adx_thr1 <= ADX14_t < adx_thr2
  - adx_bin = 2 if ADX14_t >= adx_thr2
- regime_id = adx_bin*2 + atr_bin   # 0~5
- feature index 14~19에 one-hot 반영(Contract 5.3)

### 2.4 threshold(atr_thr/adx_thr1/adx_thr2) 소스
- threshold는 **model-pack 단위로 고정**한다(정합성 핵심).
- 권장 방식: model-pack 디렉토리에 `pack_meta.csv`를 두고 EA가 로드한다.
  - 로드 실패/파싱 실패 시: PASS-only 모드 + 로그(안전)

#### 2.4.1 (권장) threshold 산출 방법 메타
- Contract는 “threshold 값 정합성”만 요구한다.
- 하지만 재현성/감사를 위해 `pack_meta.csv`에 아래 선택 메타를 추가하는 것을 권장한다:
  - thr_method(예: quantile / performance_search / manual)
  - thr_seed, thr_search_space_version, thr_notes

---

## 3. Candidate(후보) 정책 (candidate_policy_version=0.1.2)

### 3.1 불변 규칙(Contract/Policy Freeze)
- 후보는 bar close 확정값만 사용(재현성)
- 후보 상태는 (0,0), (1,0), (0,1)만 허용(one-hot-or-zero)
- (1,1)은 금지(INVALID_CAND) → PASS + 로그

### 3.2 v0.1.2 Candidate 정책(정의: CAND=B + Adaptive dist_atr_max 옵션)
지표:
- EMA20, EMA50, RSI14, ATR14 (Bid 기반, bar close 확정값)

#### 3.2.1 늦은 진입 방지(거리 제한: dist_atr_max)
- dist_atr = abs(C - EMA20) / max(ATR14, eps)
- if dist_atr > dist_atr_max_t → cand=(0,0)

dist_atr_max_t 산출 모드(둘 중 하나):
- **static**: dist_atr_max_t = dist_atr_max_static (EA 파라미터 또는 pack 기반 설정)
- **adaptive_quantile**(권장):
  - dist_atr_max_t = quantile(dist_atr_{t-1..t-W}, q)
  - 단, 충분한 히스토리(W) 부족 시 static으로 폴백
  - (권장) dist_atr_max_t를 [dist_atr_max_min, dist_atr_max_max]로 클램프

> ⚠️ “adaptive”를 쓰면 후보 분포가 달라지므로, 학습/배포 모두 동일 설정을 써야 한다.  
> 이를 위해 candidate_policy_version과 함께 dist_atr_max_mode/파라미터를 로그에 남기는 것을 권장한다.

#### 3.2.2 모드 전환(ADX bucket 기반)
- Range-mode: adx_bin == 0
- Trend-mode: adx_bin >= 1

Trend-mode:
- Long 후보:
  - EMA20 > EMA50 AND RSI14 >= 52 AND C >= EMA20
- Short 후보:
  - EMA20 < EMA50 AND RSI14 <= 48 AND C <= EMA20

Range-mode:
- Long 후보:
  - RSI14 <= 40 AND C <= EMA50
- Short 후보:
  - RSI14 >= 60 AND C >= EMA50

충돌/동시발생 처리:
- Long 조건과 Short 조건이 동시에 true면 cand=(0,0) (one-hot 유지 목적)

### 3.3 Candidate와 신규 진입
- cand=(0,0)이면 신규 진입 금지(PASS)
- 단, ONNX는 실행하고 결과를 로그에 남긴다(학습/디버깅/포지션 관리 목적)

---

## 4. ONNX 모델 로딩/추론(중요: model-pack)

### 4.1 model-pack 구성(필수)
- regime_id 0~5 각각 2개:
  - Stage1(Classifier): `clf_reg{rid}_vXXX.onnx` → 출력 [1,3]
  - Stage2(Params):     `prm_reg{rid}_vXXX.onnx` → 출력 [1,6]
- 총 12개 파일이 1세트(model-pack)
- `pack_meta.csv` (필수)
- `scaler_stats.json` (필수)
  - 형식: `mean[12]` + `std[12]`
  - 적용 범위: feature 0~11만 표준화, feature 12~21은 원형 유지
- `gate_config.json` (선택)

### 4.2 런타임 조립 규칙(EA 관점)
EA는 매 바 다음 순서로 최종 Y=[1,6]을 만든다.

1) regime_id로 Stage1 모델 선택 → p_long/p_short/p_pass 획득  
2) argmax==PASS이면:
   - Y = [p_long, p_short, p_pass, **1.5, 2.0, 24**] (PASS 기본값)
   - Stage2는 실행하지 않음(속도/안정)  
3) argmax==LONG 또는 SHORT이면:
   - 같은 regime의 Stage2 실행 → P=[k_sl_L,k_tp_L,hold_L,k_sl_S,k_tp_S,hold_S]
   - 방향에 맞는 3개만 선택하여 Y에 채움  
4) EA는 Contract대로 (k_sl,k_tp,hold_bars) 클램프/정수화하여 사용  
5) 실패/비정상 출력이면 PASS + 로그

> 참고: cand=0(후보 없음)인 바에서도 ONNX는 실행하지만, 신규 진입은 금지된다.

---

## 5. 신규 진입 정책(요약)
- cand=(0,0)이면 신규 진입 금지(PASS)
- model_dir==PASS면 PASS
- 하드/동적 게이트(섹션 7) 통과시에만 진입
- Flip은 Contract 규칙(p_min_trade, delta_flip)으로만 조건부 허용  
  - p_min_trade/delta_flip 기본값은 Contract에 있으나, EA 파라미터로 오버라이드 가능(로그 기록 권장)

---

## 6. 포지션 관리 정책(핵심만)

### 6.1 SL/TP
- SL 거리 = k_sl * ATR14
- TP 거리 = k_tp * ATR14
- (클램프 적용 후 사용)

### 6.2 hold_bars(소프트) + 총 72 bars cap(강제)
- hold_bars는 “그 이후엔 보수적으로 관리”하는 소프트 트리거
- 연장(max_extend_bars)을 두되, **최종 상한은 72 bars**
  - bars_held >= 72 → FORCE_EXIT (무조건 청산)

> 이 규칙은 라벨링 lookahead H=72와 운영을 일치시키기 위한 정합성 정책이다.

> Current baseline:
> The current runtime treats hold_soft as an observation/logging threshold and
> enforces only the 72-bar `FORCE_EXIT` hard cap as executable exit behavior.
> Any references to `max_extend_bars` in this document are future/reserved for
> the current STEP16 baseline and are not active runtime behavior.

### 6.3 조기청산(Early Exit) - current runtime modes
- Shared runtime seam:
  - held-position management is split into pre-decision live logic and
    post-decision Early Exit evaluation
  - current-bar exit heuristics are evaluated only after inference/assembly
- OFF mode:
  - `InpEarlyExitEnabled=false`
  - no post-decision Early Exit evaluation runs
- SHADOW_ONLY mode:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=false`
  - may observe:
    - `p_pass >= p_exit_pass`
    - opposite-direction signal buckets
    - `min_hold_bars_before_exit` blocking
  - must not:
    - close a live position
    - emit `trade_log` `EARLY_EXIT`
    - change `has_position`
    - change `pending_exit_*`
- LIVE_PASS_ONLY mode:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - executable trigger is intentionally narrow:
    - `p_pass >= p_exit_pass`
    - `bars_held >= min_hold_bars_before_exit`
  - live close is executed through the existing close/reconcile path
  - `trade_log.csv` still emits `ENTRY` / `EXIT` rows only
  - live early exits appear as:
    - `event_type=EXIT`
    - `exit_reason=EARLY_EXIT`
- LIVE_PASS_PLUS_OPPOSITE mode:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - `InpEarlyExitOppositeEnabled=true`
  - executable trigger family remains close-only and intentionally narrow:
    - opposite-direction current decision
    - otherwise `p_pass >= p_exit_pass`
    - both still respect `bars_held >= min_hold_bars_before_exit`
  - live close still reuses the existing close/reconcile path
  - `trade_log.csv` still emits `ENTRY` / `EXIT` rows only
  - subtype detail remains non-core and is observed through monitor/runtime
    diagnostics rather than new trade-log columns
- Protective-adjust overlay:
  - `InpProtectiveAdjustEnabled=true`
  - modify is evaluated only after the live Early Exit branch
  - currently implemented families:
    - `BREAK_EVEN`
    - `TRAILING`
    - `TP_RESHAPE`
    - `TIME_POLICY`
  - executed modifies emit `trade_log.csv` `MODIFY` rows
  - persisted intent still uses `pending_modify_*`
  - `TS_SyncPositionState()` remains the fallback reconciliation surface
- `OnTradeTransaction()` is now used for tx-authoritative entry / exit
  observation and final trade-log emission.
  Current diagnostics rule:
  - direct `CTrade.Result*` is still the immediate call-site result surface
  - `pending_exit_*` and `pending_modify_*` remain the persisted intent
    surface
  - `OnTradeTransaction()` handles normal entry / exit confirmation
  - `TS_SyncPositionState()` remains the fallback reconciliation surface for
    recovery and out-of-band state repair

### 6.4 조기청산(Early Exit) / BE / MODIFY - future / reserved
- 보유 중에도 매 바 ONNX는 실행될 수 있다.
- 예: p_pass가 충분히 크거나, 반대 확률이 강하게 높으면 조기청산 고려  
- 단, 진입 직후 난사 방지를 위해 `min_hold_bars_before_exit` 미만은 금지  
- (권장) 초기 버전에서는 feature-flag로 비활성화하고, 규칙이 확정되면 활성화

> Current-state note:
> The current implementation supports:
> - hold_soft observation
> - 72-bar `FORCE_EXIT`
> - shadow-only Early Exit evaluation
> - minimal live Early Exit on `P_EXIT_PASS` when explicitly enabled
> - default-off close-only live opposite Early Exit when explicitly enabled
> - default-off protective modify families when explicitly enabled:
>   - `BREAK_EVEN`
>   - `TRAILING`
>   - `TP_RESHAPE`
>   - `TIME_POLICY`
> - tx-authoritative trade logging with sync fallback
> - runtime model-pack hot reload / rollback

---

## 7. 비용/리스크/주문 게이트 (하드캡 + 동적 스케일)

### 7.0 게이트 파라미터의 “출처” 원칙(중요)
게이트 파라미터는 성격에 따라 2종으로 분리한다.

1) **모델 정합성 파라미터(권장: model-pack 동봉)**  
   - 예: spread_atr_max_base/hard, k_tp_scale_min/max, dev_points_* , risk_pct_*  
   - 이유: 모델 출력 분포/학습 가정과 함께 움직여야 하는 값들
2) **운영 즉시 대응 파라미터(권장: EA 입력 파라미터)**  
   - 예: block_rollover_minutes, block_week_open_minutes, 긴급 차단 스위치 등  
   - 이유: 운영 중 “즉시 조정”이 필요한 값들

권장 우선순위:
- (있으면) `gate_config.json` → (없으면) EA 입력 파라미터 기본값

### 7.1 공통 원칙
- EA는 “절대 하드캡(안전벨트)”을 가진다.
- ONNX 출력은 “소프트 기준”을 동적으로 조절하는 데만 사용한다.
- 동적 게이트는 신규 진입 판단에만 적용한다(기본).  
  (청산/관리 로직은 별도 정책에 따른다.)

### 7.2 Spread gate (spread_atr) — 동적 상한
정의:
- spread_atr = (Ask - Bid) / max(ATR14, eps)
- conf = max(p_long, p_short)
- conf_t = clamp((conf - p_min_trade) / (1 - p_min_trade), 0, 1)

TP 규모 반영(권장):
- tp_t = clamp((k_tp - k_tp_scale_min) / (k_tp_scale_max - k_tp_scale_min), 0, 1)

동적 상한:
- dyn_spread_atr_max = spread_atr_max_base * (0.85 + 0.25*conf_t + 0.25*tp_t)
- dyn_spread_atr_max = min(dyn_spread_atr_max, spread_atr_max_hard)

게이트:
- trade allowed iff spread_atr <= dyn_spread_atr_max

### 7.3 Slippage 허용치(dev_points) — 동적 확대(소폭)
- dyn_dev_points = dev_points_base + round(dev_points_add_max * conf_t)
- dyn_dev_points = min(dyn_dev_points, dev_points_hard_max)

> dev_points는 “허용 슬리피지”이며, 학습 비용모델의 slip_points(고정)와는 개념이 다르다.  
> 다만 운영/학습 정합성 분석을 위해 둘 다 cost_model_version/EA 파라미터로 로그에 남긴다.

### 7.4 Lot / Risk gate — 계좌 n% 상한 + ONNX 확신도 스케일
- EA는 “리스크 % 기반”으로 lot을 계산한다(권장).
- 기본:
  - risk_pct = clamp(risk_pct_base * (0.8 + 0.6*conf_t), risk_pct_hard_min, risk_pct_hard_max)
- SL 거리(가격)는 k_sl*ATR14로 결정되므로,
  - risk 기반 lot 계산은 자연스럽게 ONNX(k_sl)의 영향도 함께 반영한다.

### 7.5 시간 필터(하드)
- decision bar close time(서버 시간) 기준으로 주간 오픈 직후 N분 진입 금지
- decision bar close time(서버 시간) 기준으로 자정 전후 N분 롤오버 진입 금지

> Current-state note:
> The current gate evaluates time filters on the latest decision bar timestamp,
> not wall-clock `TimeCurrent()`. Rollover blocking applies both shortly after
> midnight and shortly before the next midnight boundary.

### 7.6 주문 제약(하드) + 최소 보정(권장)
- StopLevel/FreezeLevel/호가단위/최소거리 등 충족
- 미충족 시 “그대로 주문”하지 않고 아래 순서로 처리한다.

#### 7.6.1 최소 보정 알고리즘(권장)
1) 목표 SL/TP(가격)를 k_sl/k_tp로 계산  
2) 브로커 제약으로 요구되는 최소거리(min_stop_distance)를 계산  
3) SL/TP 거리가 min_stop_distance 미만이면:
   - **거리를 늘리는 방향으로만** 보정(리스크 축소를 위해 거리를 줄이지 않음)
   - 보정 후 k_sl/k_tp가 Contract 클램프 상한을 초과하면 → PASS + 로그
4) 보정이 성공하면 “effective SL/TP”로 주문 시도
5) 어떤 단계에서든 불가/오류면 → PASS + 로그

> 권장 로그: requested_k_sl/k_tp, effective_k_sl/k_tp, requested_sl/tp_price, effective_sl/tp_price, reject_reason

---

## 8. 로그/산출물(필수)

### 8.1 bar_log_YYYYMMDD.csv (매 5분봉 1행, 일자별 rotation)
**목표:** “실시간 입력 = 학습 입력” 정합성을 보장할 수 있을 정도로 남긴다.

필수(권장 최소):
- time(바 마감 timestamp), symbol, timeframe
- price_basis (고정: Bid)
- OHLC(open,high,low,close)
- spread_points 또는 spread_price
- ATR14, ADX14, atr_pct, regime_id
- cand_long, cand_short
- feature_0..feature_21 (22개 피처)
- onnx_p_long, onnx_p_short, onnx_p_pass, stage1_argmax
- prm_raw_0..5
- final_dir(PASS/LONG/SHORT), flip_used(0/1)
- k_sl_req, k_tp_req, k_sl_eff, k_tp_eff, hold_bars
- gate_pass, gate_reject_reason, has_position, bars_held

동적 게이트(권장):
- dyn_spread_atr_max, dyn_dev_points, risk_pct

threshold/정합성(권장):
- atr_thr, adx_thr1, adx_thr2는 `pack_meta.csv`에서 관리
- (선택) thr_method
- dist_atr, dist_atr_max_t, dist_atr_max_mode

Stage2 raw/디버깅(선택):
- prm_raw_0..5  (Stage2 원출력 6개)

주문 보정(선택):
- k_sl_req, k_tp_req, k_sl_eff, k_tp_eff

> `final_dir` is the model-assembled direction, not the final entry action.
> See `design/BAR_LOG_SCHEMA.md` for the current runtime schema and decision flow.
> Current-state note:
> Any future decision/request-field realignment must keep
> `design/BAR_LOG_SCHEMA.md` as the current-state source of truth until the
> code and emitted schema are updated together.

**버전 메타(필수):**
- ea_version
- schema_version
- candidate_policy_version
- regime_policy_version
- model_pack_version
- clf_version
- prm_version
- cost_model_version

### 8.2 trade_log.csv (트레이드 이벤트 1행)
필수(권장 최소):
- trade_id, timestamp, symbol
- event_type(ENTRY/EXIT/MODIFY), direction, lot
- entry_price, sl_price, tp_price, exit_price, pnl
- k_sl_req, k_tp_req, k_sl_eff, k_tp_eff, hold_bars, bars_held
- exit_reason
  - current examples: `SL`, `TP`, `FORCE_EXIT`, `EARLY_EXIT`
  - future/reserved examples: `HOLD_SOFT`, `ROLLOVER_BLOCK`, `RISK_BLOCK`
- regime_id_at_entry, spread_atr_at_entry, flip_used
- (권장) model_pack_version / clf_version / prm_version / cost_model_version 스냅샷
- (권장) 주문 보정 전/후(req/eff) 파라미터 스냅샷

> Current-state note:
> The current runtime emits `ENTRY`, `EXIT`, and `MODIFY` rows.
> `EARLY_EXIT` is emitted only through the current minimal live Early Exit mode.
> Opposite-direction live Early Exit, when enabled, still emits the same
> `EXIT` row plus `exit_reason=EARLY_EXIT`; subtype detail stays outside the
> core CSV schema.
> Protective modify rows are emitted only when a live modify actually executes.
> Step21 suffix columns add tx-authority, runtime-reload, and pack/audit
> context to each trade event.
> Shadow-only Early Exit evaluation must not emit `EARLY_EXIT` or `MODIFY`
> rows.

---

## 9. 버전/배포 운영 규칙(권장)
- EA 설정에는 “활성 model-pack 디렉토리”를 지정한다.
- 12개 ONNX 파일 중 1개라도 로드 실패하거나 `scaler_stats.json`이 누락/파싱 실패/형식 불일치면 **PASS-only 모드**로 전환하고 로그에 남긴다.
- `pack_meta.csv`가 존재하면 아래를 로드해 정합성을 고정한다(권장):
  - atr_thr, adx_thr1, adx_thr2
  - model_pack_version, schema_version, regime_policy_version, candidate_policy_version, cost_model_version
- `scaler_stats.json`은 필수로 로드한다:
  - `mean[12]`, `std[12]`
  - feature 0~11만 표준화 적용
- (권장) `gate_config.json`이 있으면 gate 기본값/하드캡을 로드한다.

---

## 10. 파라미터(핵심만)

Regime/후보:
- atr_thr, adx_thr1, adx_thr2 (권장: pack_meta로 주입)
- dist_atr_max_mode(static / adaptive_quantile)
- dist_atr_max_static, dist_atr_window, dist_atr_quantile, dist_atr_max_min/max

Flip/진입:
- p_min_trade, delta_flip

Exit (current + future / reserved):
- `InpEarlyExitEnabled`
- `InpEarlyExitLive`
- `InpEarlyExitOppositeEnabled`
- p_exit_pass
- min_hold_bars_before_exit
- `InpProtectiveAdjustEnabled`
- `InpBreakEvenEnabled`
- `InpBreakEvenRRTrigger`
- `InpBreakEvenMinHoldBars`
- `InpBreakEvenOffsetPoints`
- p_exit_flip, delta_exit
- max_extend_bars (단, 최종 72 cap)

Gate(스프레드/슬리피지/리스크):
- spread_atr_max_base, spread_atr_max_hard
- k_tp_scale_min, k_tp_scale_max
- dev_points_base, dev_points_add_max, dev_points_hard_max
- risk_pct_base, risk_pct_hard_min, risk_pct_hard_max

시간 필터:
- block_week_open_minutes, block_rollover_minutes
