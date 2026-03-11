# 정책 확정서 (Policy Freeze) v0.1.0

- 기준일: 2026-03-04
- 이 문서는 **Q1~Q10 결정사항을 “최종 정책”으로 고정**한다.  
- 아래 정책은 기존 PDF/MD 문서에 같은 주제가 다르게 쓰여 있어도 **본 문서가 우선**한다.

---

## A. 확정된 Q-결정(최종 답안)

- Q1) Candidate(cand_long/cand_short) 양방(1,1) 허용? → **A (불허)**  
  - 허용 상태: (0,0), (1,0), (0,1)  
  - 금지 상태: (1,1) → INVALID → PASS + 로그

- Q2) 모델 배포 구조: 단일 파일 vs model-pack(12개)? → **A (model-pack)**  
  - regime_id 0~5 각각에 대해: Stage1(clf) 1개 + Stage2(prm) 1개  
  - 총 12개 ONNX 파일이 1세트

- Q3) PASS일 때 k_sl/k_tp/hold_bars 기본값? → **A**  
  - k_sl_default=1.5, k_tp_default=2.0, hold_default=24

- Q4) 로그에 모델팩/스테이지/비용모델 버전 기록? → **A (기록한다)**

- Q5) 보유시간: 운영에서 72 bars를 넘겨도 되나? → **A (총 보유 72 cap)**

- Q6) cand=0(후보 없음) 바를 Stage1 학습에 포함? → **B (포함한다)**  
  - Stage1: cand=0 바도 샘플에 포함하고 **라벨을 PASS로 강제**  
  - Stage2: 기존대로 cand XOR==1 바만 사용

- Q7) 컨셉(아키텍처) 문서: Pattern C로 업데이트? → **B (업데이트한다)**

- Q8) ‘권장안/예제’ 문서 shape([1,64,16]/[1,5]) 수정? → **A (업데이트한다)**  
  - 최신 계약: Input[1,64,22], Output[1,6]

- Q9) 비용모델(라벨링)과 EA 실행 파라미터를 같은 버전 체계로 묶어 관리? → **A (묶는다)**  
  - cost_model_version을 운영/학습에 공통으로 기록하고, slip_points/price_basis 등을 명시

- Q10) bar OHLC price_basis 기준? → **A (Bid 기준)**

---

## B. 이번 확정으로 “무엇이 바뀌나?” (비개발자 설명)

### 1) 왜 cand(후보) 1,1을 금지하나?
- cand는 “이번 바에서 EA가 모델에게 **어느 방향을 먼저 검토해볼지** 힌트”다.  
- 좌/우 깜빡이를 동시에 켜면(1,1), 모델·EA 모두 판단 기준이 흐려지고, 학습 데이터도 꼬인다.  
- 그래서 **(1,1)은 버그로 취급**하고 안전하게 PASS로 처리한다.

### 2) 왜 모델을 12개 파일(model-pack)로 나누나?
- v0.1은 “배포 단순화”보다 “설계 검증/해석”을 우선한다.  
- 시장 상태(regime)가 6개라서, **상태별로 다른 작은 모델**이 더 안정적일 수 있다.  
- 또 두 단계(two-stage)로 나눠서:
  - Stage1은 “롱/숏/패스”만 결정
  - Stage2는 “SL/TP/보유시간” 같은 운용 파라미터를 산출  
  이런 구조가 디버깅과 개선이 쉽다.

### 3) cand=0 바를 Stage1 학습에 포함하는 이유는?
- 실전에서는 “후보 없음(cand=0)”인 바도 많이 나온다.  
- 특히 포지션 보유 중 조기청산 판단처럼 **‘관리’ 국면**에서 cand=0이 자주 나온다.  
- Stage1이 cand=0을 전혀 못 배우면, 그 상황에서 PASS 확률이 불안정해질 수 있다.  
- 그래서 **cand=0은 PASS로 강제 라벨**해서 학습에 포함한다(안전/안정 목적).

### 4) 왜 “총 72 bars cap”을 두나?
- 라벨링(정답 생성)이 “미래 72 bars까지”를 보고 최적 행동을 정의한다.  
- 실전에서 72를 넘어 들고 가면, 모델이 배운 범위를 넘어선 운영이 된다.  
- 그래서 운영도 **최대 보유시간을 72로 캡**해서 학습 가정과 맞춘다.

---

## C. 이 문서가 만드는 강제 규칙(한 눈에)

1) Candidate: one-hot-or-zero, (1,1) 금지  
2) Runtime: Pattern C, 새 5분봉 마감 1회 의사결정  
3) Model: model-pack(12개), regime별 + two-stage  
4) PASS: (1.5, 2.0, 24)로 Y shape 채움  
5) Logging: schema + model_pack + stage + cost_model 버전 기록  
6) Hold: 총 72 bars 강제 상한  
7) Training: Stage1은 cand=0 포함(PASS 강제), Stage2는 cand=1만  
8) price_basis: Bid

---

## D. 다음 문서들에 반영해야 하는 “필수 패치” 요약
- Contract: (cand=1,1 허용 문구 제거) + PASS 기본값 명문화
- EA Runtime: model-pack 로딩/선택/버전 메타 + 총 72 cap + bar_log에 price_basis/비용모델 버전
- ONNX Dev: Stage1 샘플 규칙(cand=0 포함) + cost_model_version/price_basis 고정 유지
