# STEP11. 라벨링(Action-search, H=72) + 비용모델(v0.1) 구현

- 목적: bar_log로부터 학습 윈도우(X)와 라벨(Y*)를 생성한다.  
  운영(72 cap)과 라벨링(H=72)을 일치시켜 “학습-배포 정합성”을 확보한다.

---

## 1) 범위
- bar_log → [64x22] 윈도우 재구성
- Action-search로 LONG/SHORT/PASS 및 최적 파라미터(k_sl,k_tp,hold) 탐색
- 비용모델 v0.1 적용(spread + slip_points*2)
- 산출물 저장(권장: Parquet) + 메타데이터 스냅샷

---

## 2) 입력 / 출력
### 입력
- bar_log.csv (필수 컬럼 충족)
- cost_model_version, slip_points=2, price_basis=Bid

### 출력
- Stage1 라벨: {LONG,SHORT,PASS}
- Stage2 라벨: k_sl_L/k_tp_L/hold_L, k_sl_S/k_tp_S/hold_S (또는 방향별 별도 타깃)
- 산출물 포맷(권장): Parquet
- 메타: schema_version/model_pack_version/cost_model_version/threshold 등

---

## 3) 고정 규칙(Invariants)
- lookahead H=72
- 진입 가격: t+1 open 근사
- SL/TP 거리: ATR14_t 기준
- TP/SL 동시 터치: SL 우선(보수적)
- PASS 라벨: best_R <= 0.05 이면 PASS
- 비용모델: spread + 고정 슬리피지 버퍼(진입/청산 2회)

---

## 4) 탐색 공간(미지정 처리 원칙)
문서에 탐색 공간(k 후보 집합 등)이 고정되어 있지 않다면:
- “그럴듯하게 큰 공간”을 임의로 쓰지 않는다.
- 팀 표준 탐색 공간 버전을 따로 정의하고,
  - `thr_search_space_version`처럼 `search_space_version` 메타로 기록한다.

---

## 5) 산출물 포맷(최종 결정)
- 결정: **Parquet 권장**
  - 이유: dtype/스키마 보존, 대용량 처리
- CSV도 가능하나, 스키마 파일(별도 json/yaml)로 dtype 고정이 필요

---

## 6) 재현성 체크리스트(권장)
- 동일 입력(bar_log) → 동일 라벨이 생성되는지(결정적 실행)
- seed/탐색공간 버전/비용모델 버전이 산출물에 포함되는지
- threshold(atr_thr/adx_thr*) 스냅샷 포함

---

## 7) 테스트/검증(Acceptance)
- [A1] 라벨 재생성 시 완전 동일 결과(재현성)
- [A2] H=72, slip_points=2, R_pass_buffer=0.05가 산출물 메타에 기록됨
- [A3] 라벨이 Contract의 clamp 범위 밖으로 생성되지 않음(또는 생성 시 clamp 규칙 명시)

---

## 8) 구현 메모
- Stage2 출력 형식([1,6])과 학습 타깃 구조(마스킹 등)는 STEP13에서 확정한다.
