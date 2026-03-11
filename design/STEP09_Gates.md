# STEP09. Gate(스프레드/슬리피지/리스크/시간/주문 제약) 구현 + 거절 사유 로깅

- 목적: EA가 가진 “하드 안전벨트”를 구현한다.  
  모델의 출력은 gate를 ‘완화/강화’하는 소프트 신호로만 사용한다.

---

## 1) 범위
- Spread gate (spread_atr) + 동적 상한
- Slippage 허용치(dev_points) 동적 확대
- Risk 기반 lot 계산(확신도 스케일)
- 시간 필터(주간오픈/롤오버)
- 주문 제약(StopLevel/FreezeLevel 등) 체크
- gate 거절 사유를 구조화하여 로그에 남김

---

## 2) 입력 / 출력
### 입력
- spread_atr, ATR14, Ask/Bid
- Stage1 확률(conf), Stage2 k_tp
- Gate 파라미터(출처: gate_config.json 또는 EA 파라미터)
- 운영 파라미터(롤오버 차단 등)

### 출력
- `gate_pass` (true/false)
- `gate_reject_reason` (코드 + 사람이 읽는 문자열 권장)
- dyn_spread_atr_max, dyn_dev_points, risk_pct (권장 로그)

---

## 3) 고정 규칙(Invariants)
- gate 실패 시: 신규 진입 0(PASS) + 사유 로그
- gate는 기본적으로 “신규 진입 판단”에만 적용(청산 로직과 분리)
- 운영 즉시 대응 값(롤오버 차단 등)은 pack에 넣지 않음(권장)

---

## 4) 게이트 파라미터 출처(최종 결정)
- 1순위: model-pack 내 `gate_config.json` (있으면 로드)
- 2순위: EA 입력 파라미터(고정값)
- 로드 실패 시:
  - “조용한 폴백” 대신 PASS-only를 권장(정합성 목적)

---

## 5) Gate 수식(요약)
- conf = max(p_long, p_short)
- conf_t = clamp((conf - p_min_trade)/(1 - p_min_trade), 0, 1)
- tp_t = clamp((k_tp - k_tp_scale_min)/(k_tp_scale_max - k_tp_scale_min), 0, 1)
- dyn_spread_atr_max = min(spread_atr_max_base*(0.85+0.25*conf_t+0.25*tp_t), spread_atr_max_hard)
- dyn_dev_points = min(dev_points_base + round(dev_points_add_max*conf_t), dev_points_hard_max)
- risk_pct = clamp(risk_pct_base*(0.8+0.6*conf_t), risk_pct_hard_min, risk_pct_hard_max)

---

## 6) 주문 제약(최소 보정 연계)
- StopLevel/FreezeLevel 체크는 “STEP10 주문 보정”과 연계
- 이 STEP에서는:
  - 제약 값 조회 및 “보정 필요 여부” 판단
  - 보정 실패 시 거절 사유 코드 정의
- 실제 보정(거리 확장)은 STEP10에서 수행

---

## 7) 로그 설계(권장)
- gate_reject_reason_code: 예) SPREAD, TIME_BLOCK, ORDER_CONSTRAINT, RISK_BLOCK
- gate_reject_reason_detail: 값 포함 문자열(예: spread_atr=0.52 > dyn=0.35)
- dyn_spread_atr_max, dyn_dev_points, risk_pct

---

## 8) 테스트/검증(Acceptance)
- [A1] gate 실패 시 주문이 절대 나가지 않음
- [A2] 거절 사유가 항상 기록됨(빈 값 금지)
- [A3] dyn 값이 계산/로그에 남아 사후 분석 가능

---

## 9) 구현 메모
- gate는 운영/심볼별 튜닝이 잦을 수 있으므로, 설정/버전/스냅샷을 로그에 남기는 것이 중요하다.
