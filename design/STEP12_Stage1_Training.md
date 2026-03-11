# STEP12. Stage1(분류) 학습 설계 + 수용 기준

> **Status: BASELINE IMPLEMENTED**
>
> A correctness-first STEP12 baseline is implemented in
> `src/ml/triplesigma_ml/step12.py` and `src/ml/step12_training.py`.
> Architecture bake-off, hyperparameter tuning, and walk-forward validation
> remain deferred to STEP14.

- 목적: regime별 Stage1(6개) 분류 모델을 학습한다.  
  운영 안정성 관점에서 “cand=0에서 PASS 안정”이 매우 중요하다.

---

## 1) 범위
- 데이터셋 구성(샘플 규칙 Q6 반영)
- 고정 baseline 아키텍처 1회 학습
- 불균형 처리(cand=0 비율/가중치)
- 평가 지표 및 수용 기준 정의
- ONNX export 전 품질 게이트

---

## 2) 입력 / 출력
### 입력
- STEP11 산출물(라벨/윈도우)
- regime_id별 분리 데이터
- 샘플 규칙:
  - cand XOR==1: 라벨=Action-search
  - cand==0: 라벨=PASS 강제

### 출력
- Stage1 모델 6개(각 regime)
- 검증 리포트(특히 cand=0 subset)
- 모델 버전(clf_version)

---

## 3) 고정 규칙(Invariants)
- 출력: softmax [p_long,p_short,p_pass]
- cand=0 샘플은 반드시 포함(라벨 PASS 강제)
- 시간 누수 없는 검증(STEP14와 연계)
- split은 global chronological boundary + H=72 embargo를 사용
- scaler_stats.json은 global training bars only 기준으로 feature 0~11에서만 계산

---

## 4) 최종 결정(학습 전략)
- 현재 baseline: **고정 MLP 1회 학습**
- 아키텍처 bake-off(MLP/CNN/Transformer)는 STEP14로 이관
- cand=0 샘플 균형:
  - current baseline default: mild cap (`cand0_max_fraction=0.95`) + neutral weight (`cand0_sample_weight=1.0`)
  - stricter rebalance/downweight variants are deferred to STEP14
- 평가 지표(권장):
  - regime별 macro-F1
  - PASS precision/recall
  - **cand=0 subset에서 PASS recall(높아야 함)**
  - 캘리브레이션(기간별 p_pass 평균/분산)

---

## 5) 수용 기준(예시, 값은 팀에서 확정)
- cand=0 subset에서:
  - PASS recall이 충분히 높고(운영 안전)
  - p_pass 분산/드리프트가 과도하지 않음
- cand XOR==1 subset에서:
  - LONG/SHORT 구분 성능이 베이스라인 대비 개선

---

## 6) 로깅/메타
- 학습 산출물에:
  - schema_version, cost_model_version, candidate_policy_version
  - 데이터 기간/심볼
  - seed, 아키텍처/하이퍼파라미터
  - train_end_time, val_start_time, embargo_bars
  - scaler_source=global_train_bars
  를 기록

---

## 7) 테스트/검증(Acceptance)
- [A1] 학습/검증이 시간 누수 없이 수행됨
- [A2] cand=0 subset에서 PASS가 불안정하지 않음(운영 안정성)
- [A3] export 후 ONNX I/O shape/dtype 검증 통과(STEP15 체크)

---

## 8) 구현 메모
- “성능(수익)”보다 “정합성/안정성”을 먼저 만족해야 다음 단계(튜닝)가 의미가 있다.
