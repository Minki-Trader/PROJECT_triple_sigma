# STEP08. 추론 조립(Y 생성) + Flip 규칙 + 출력 클램프/검증 + 실패 시 PASS

- 목적: Stage1/Stage2 출력으로 최종 Y=[1,6]을 조립하고, Contract의 Flip/Clamp/Fail-safe 규칙을 적용한다.

---

## 1) 범위
- Stage1 실행 → (p_long,p_short,p_pass)
- PASS면 Stage2 미실행 + default 파라미터
- LONG/SHORT면 Stage2 실행 후 방향에 맞는 3개만 선택
- Flip 규칙 적용(조건부)
- k_sl/k_tp/hold clamp + hold round
- 이상/예외 시 PASS로 강제

---

## 2) 입력 / 출력
### 입력
- X [1,64,22] float32
- cand_long/cand_short
- Stage1/Stage2 세션 핸들

### 출력
- Y [1,6] float32
- `model_dir`(PASS/LONG/SHORT)
- `flip_used`(0/1)
- `fail_safe_reason`(권장)

---

## 3) 고정 규칙(Invariants)
- PASS일 때도 Y shape 유지:
  - k_sl=1.5, k_tp=2.0, hold=24
- k_sl [0.5,6], k_tp [0.5,12], hold [1,72]
- 확률합이 비정상/NaN/Inf면 PASS
- cand=(0,0)일 때 신규 진입 금지(하지만 추론/로그는 수행)

---

## 4) 조립 로직(최종 결정)
1) Stage1 실행
2) 확률 검증:
   - NaN/Inf 체크
   - p_long+p_short+p_pass ≈ 1 (허용오차 내)
3) model_dir = argmax(p_*)
4) model_dir==PASS:
   - Stage2 미실행
   - Y = [p_long,p_short,p_pass, 1.5,2.0,24]
5) model_dir==LONG/SHORT:
   - Stage2 실행 → raw=[k_sl_L,k_tp_L,hold_L,k_sl_S,k_tp_S,hold_S]
   - 방향에 해당하는 3개 선택
   - Y 구성 후 clamp/round

---

## 5) Flip 규칙(최종 결정)
- p_min_trade, delta_flip은 EA 입력 파라미터로 제공(로그 기록)
- cand_long=1인데 model_dir=SHORT이면:
  - p_short>=p_min_trade AND (p_short-p_long)>=delta_flip 일 때만 SHORT 허용(=flip_used=1)
  - 아니면 PASS
- cand_short=1인데 model_dir=LONG이면 반대로 적용

---

## 6) 로깅(권장)
- p_long/p_short/p_pass
- model_dir, flip_used
- (선택) stage2 raw 6값(prm_raw_0..5)
- 최종 k_sl/k_tp/hold(클램프/반올림 후)

---

## 7) 테스트/검증(Acceptance)
- [A1] PASS면 Stage2가 호출되지 않음
- [A2] 출력 clamp 범위를 벗어나면 항상 clamp 후 사용
- [A3] Flip 조건 미충족 시 강제 PASS
- [A4] 확률합/NaN/Inf 이상 시 신규 진입이 0(PASS)

---

## 8) 구현 메모
- 확률합 검증은 softmax 출력이더라도 “실수 오차”가 있으니 작은 epsilon 허용 필요
- hold는 최종적으로 int(round)로 사용하되, 라벨/학습에서도 동일 규칙을 유지한다.
