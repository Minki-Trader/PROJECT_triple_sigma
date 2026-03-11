# STEP06. Candidate 정책 구현 + (1,1) 금지 강제

- 목적: EA_RUNTIME의 Candidate 정책(cand_long/cand_short)을 구현하고, Contract의 불변 규칙(one-hot-or-zero, (1,1) 금지)을 강제한다.

---

## 1) 범위
- Candidate 조건 계산(Trend/Range)
- 늦은 진입 제한(dist_atr_max) 적용
- (1,1) 금지 및 동시발생 처리(cand=(0,0))
- feature[20..21] 업데이트
- cand=0 신규 진입 금지(단, 모델 실행/로그는 유지)

---

## 2) 입력 / 출력
### 입력
- EMA20/EMA50/RSI14/ATR14/ADX14 (Bid 기반)
- regime 계산에서 나온 adx_bin
- dist_atr_max 설정(static 또는 adaptive)

### 출력
- cand_long, cand_short ∈ {(0,0),(1,0),(0,1)}
- feature[20]=cand_long, feature[21]=cand_short
- bar_log: cand_long/cand_short, invalid_cand 플래그(권장)

---

## 3) 고정 규칙(Invariants)
- (1,1) 금지 → INVALID_CAND → PASS + 로그
- 둘 다 조건 true면 cand=(0,0) (one-hot 유지)
- cand=(0,0)일 때 신규 진입 금지(모델은 실행/로그)

---

## 4) dist_atr_max (최종 결정: Adaptive 옵션 사용)

### 4.1 dist_atr 정의
- dist_atr = abs(C - EMA20) / max(ATR14, eps)

### 4.2 dist_atr_max_mode
- `static`: dist_atr_max_t = dist_atr_max_static
- `adaptive_quantile`(권장):
  - dist_atr_max_t = quantile(dist_atr_{t-1..t-W}, q)
  - 부족한 히스토리면 static으로 폴백
  - (권장) dist_atr_max_t를 [min,max]로 클램프

### 4.3 로그/재현성
- candidate_policy_version과 함께 다음을 기록 권장:
  - dist_atr_max_mode, W, q, dist_atr_max_t, dist_atr
- 학습/배포 모두 동일 설정을 사용해야 한다.

---

## 5) Candidate 조건(요약)
- Trend-mode(adx_bin>=1):
  - Long: EMA20>EMA50 AND RSI>=52 AND C>=EMA20
  - Short: EMA20<EMA50 AND RSI<=48 AND C<=EMA20
- Range-mode(adx_bin==0):
  - Long: RSI<=40 AND C<=EMA50
  - Short: RSI>=60 AND C>=EMA50

---

## 6) 로깅(필수/권장)
필수:
- cand_long, cand_short
권장:
- dist_atr, dist_atr_max_t
- adx_bin, mode(range/trend)
- invalid_cand(0/1)

---

## 7) 테스트/검증(Acceptance)
- [A1] cand 결과가 항상 3상태 중 하나(0,0)/(1,0)/(0,1)
- [A2] 동시 true 케이스에서 cand=(0,0)
- [A3] adaptive 설정 시 재현 가능(동일 입력 시 동일 dist_atr_max_t 산출)

---

## 8) 구현 메모
- candidate는 “신규 진입 힌트”이지만, 학습/디버깅/관리(보유 중)에도 영향을 주므로,
  - cand=0 구간에서도 모델 실행/로그를 반드시 유지한다.
