# STEP10. 주문 실행 + 포지션 관리 + 72 bars 강제 청산 + 로그 산출물 완성

- 목적: 실제 주문/포지션 관리/강제 청산/로그를 구현한다.  
  이 STEP부터 “실전 안전성”이 직접 걸리므로, fail-safe가 최우선이다.

---

## 1) 범위
- 신규 진입(Entry) 실행
- SL/TP 설정(k*ATR14)
- hold_bars 소프트 + 총 72 bars cap 하드 강제 청산
- (선택) 조기청산 인터페이스(초기엔 비활성 권장)
- bar_log/trade_log 완성

---

## 2) 입력 / 출력
### 입력
- 최종 행동: PASS/LONG/SHORT
- 최종 파라미터: k_sl, k_tp, hold_bars
- gate 결과: gate_pass, dyn_dev_points, risk_pct 등
- 주문 제약(StopLevel/FreezeLevel 등)
- 현재 포지션 상태(bars_held 등)

### 출력
- 주문 요청/체결 결과
- trade_log 이벤트(ENTRY/EXIT/MODIFY)
- bar_log 1행(매 바)

---

## 3) 고정 규칙(Invariants)
- bars_held >= 72 → FORCE_EXIT (무조건)
- cand=0 또는 model_dir=PASS 또는 gate_fail → 신규 진입 금지
- 주문 실패/예외 → PASS + reason 로그

---

## 4) 주문 실행(최종 결정)
- 포지션 수: 심볼당 1포지션(권장)
- 진입 타이밍:
  - “바 마감 후” 의사결정이므로, 실제 주문은 **다음 바 초반(t+1)** 에 실행(OHLC 근사와 정합)
- SL/TP:
  - requested 거리 = k * ATR14
  - 주문 제약 미충족 시:
    - **거리 확장 방향으로 최소 보정 시도**
    - 보정 후 k가 clamp 상한을 넘으면 → 주문 취소(PASS)
  - 보정 전/후 값을 모두 로그

---

## 5) 포지션 관리
- bars_held 추적:
  - 바가 갱신될 때마다 +1
  - 재시작/재연결 시에도 복원 가능하도록 entry_time 기반 계산 권장
- hold_bars(소프트):
  - hold_bars 이후 “보수적 관리” 가능(구체 규칙은 별도 정책)
- FORCE_EXIT(하드):
  - bars_held >= 72 즉시 청산

---

## 6) 조기청산(Early Exit)
- 문서에 파라미터만 있고 규칙은 미지정인 부분이 존재
- 최종 결정:
  - 인터페이스(파라미터, 로그 컬럼)만 먼저 구현
  - 초기 버전에서는 feature-flag로 비활성(default OFF)

---

## 7) 로그(필수)
### 7.1 bar_log.csv (매 바 1행)
- feature_0..21
- onnx_p_*, onnx_k_*, onnx_hold_bars
- action, flip_used, gate_reject_reason
- 버전 메타(ea_version, schema_version, pack/meta 버전 등)

권장:
- raw stage2 6값
- 주문 보정 전/후(req/eff) 값

### 7.2 trade_log.csv (이벤트 1행)
- ENTRY/EXIT/MODIFY
- entry/exit 가격, SL/TP, lot, pnl
- exit_reason (SL/TP/EARLY_EXIT/HOLD_SOFT/FORCE_EXIT 등)
- regime_id_at_entry, spread_atr_at_entry, flip_used
- 버전 메타 스냅샷

---

## 8) 테스트/검증(Acceptance)
- [A1] 72 cap이 어떤 상황에서도 발동(포지션이 73 bars 이상 유지되지 않음)
- [A2] 주문 제약 미충족 시 “무리한 주문” 대신 PASS 또는 보정 후 주문
- [A3] bar_log/trade_log가 누락 없이 생성되고, 학습 입력으로 재사용 가능

---

## 9) 구현 메모
- 실제 체결/슬리피지는 예측 불가능하므로,
  - 요청값(req)과 체결값(fill)을 분리해 기록해야 사후 분석이 가능하다.
