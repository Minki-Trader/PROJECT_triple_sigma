# ONNX 모델 개발 규격서 v0.1.2 (Policy Freeze 반영 + 패키징/산출물 확장)

- 기준일: 2026-03-04
- 범위: 학습 데이터 규격, 라벨링(정답 생성), 비용 모델, 모델 패키징, ONNX export 요구사항
- 상위 우선순위: `POLICY_FREEZE.md` → `CONTRACT.md` → 본 문서

> 이 문서는 `POLICY_FREEZE.md`를 반영한 **ONNX 개발 기준서**다.  
> 특히 Q6 정책에 따라 Stage1 학습에 cand=0 샘플을 포함(라벨 PASS 강제)하도록 고정한다.  
> (구버전/초안 문서는 별도 보관)

---

## 0. v0.1.2 변경 요약
- (신규) model-pack 메타(`pack_meta.csv`)에 **threshold 산출 방법(thr_method)** 등 재현성 메타를 *선택 컬럼*으로 추가 가능
- (신규) 라벨/학습 산출물 포맷으로 **Parquet 권장**(대용량/스키마 관리 목적)
- (신규) model-pack에 `scaler_stats.json` 필수 동봉, `gate_config.json`은 선택 동봉  
  - 단, 모델 내부 정규화/스케일링은 금지(Contract/기존 정책 유지)

---

## 1. 결정사항 요약(핵심만)
- 입력 데이터: EA의 bar_log 기반(피처 22개, 시계열 64 bars)
- 라벨링: Action-search 방식, lookahead H=72 bars, 유틸리티는 R-multiple 최대
- 비용 모델: spread + 고정 슬리피지 버퍼(slip_points=2) (cost_model_version으로 관리)
- 패키징: regime_id(0~5) 별로 모델 분리(6개) + two-stage(총 12개)
- **학습 샘플 규칙(고정)**:
  - Stage1(방향/패스 분류): cand XOR==1 샘플 + **cand==0 샘플(라벨 PASS 강제)** 포함
  - Stage2(파라미터): cand XOR==1 샘플만 사용

---

## 2. 상위 시스템 계약(Contract) 요약(불변)
- Input: X float32, shape [1,64,22]
- Output: Y float32, shape [1,6] = [p_long,p_short,p_pass,k_sl,k_tp,hold_bars]
- Pattern: 새 5분봉 확정 시점 1회 의사결정, 매 바 추론
- Regime: 6버킷(ADX 3단 × ATR 2단), regime_id 0~5 + one-hot
- Candidate: one-hot-or-zero, cand=0이면 신규진입 금지(모델은 실행/로그)
- Feature Catalog: Contract 5절 정의가 최종(시간피처 포함)

---

## 3. 모델 패키징(파일 구성) - regime별 + two-stage

### 3.1 ONNX 파일 구성(필수)
- regime_id 0~5별 모델 2개:
  - Stage1(Classifier): `clf_reg{rid}_vXXX.onnx` → 출력 [1,3]
  - Stage2(Params):     `prm_reg{rid}_vXXX.onnx` → 출력 [1,6]
- 총 12개 ONNX 파일이 한 세트(model-pack)

### 3.2 런타임 조립 규칙(EA 관점)
1) Stage1 실행 → p_long/p_short/p_pass  
2) PASS면: Y = [p_long, p_short, p_pass, 1.5, 2.0, 24] (default)  
3) LONG/SHORT면: Stage2 실행 → 방향에 맞는 3개 선택  
4) EA는 Contract 규칙대로 클램프/정수화 후 사용

### 3.3 model-pack 메타데이터(필수: regime threshold 정합성)
Regime threshold(atr_thr/adx_thr1/adx_thr2)는 **model-pack 단위로 고정**되어야 한다.  
EA 런타임도 동일 값을 사용해야 하므로, model-pack과 함께 메타 파일을 배포한다.

권장 파일: `pack_meta.csv`

Format:
- key=value text, one entry per line
- lines starting with `#` are comments
- blank lines are ignored

> `pack_meta.csv` is a legacy filename kept for runtime/tester compatibility.
> The current file format is **not** a header/value CSV.

#### 3.3.1 필수 컬럼(Contract/Runtime 정합성)
- model_pack_version
- schema_version
- regime_policy_version
- candidate_policy_version
- cost_model_version
- atr_thr
- adx_thr1
- adx_thr2

> EA는 `pack_meta.csv`를 로드해 threshold와 버전 메타를 런타임 정합성 기준으로 사용한다.
> Current runtime note:
> `atr_thr`, `adx_thr1`, and `adx_thr2` remain pack-level metadata in
> `pack_meta.csv` and are not repeated on every bar in the current `bar_log`.

#### 3.3.2 선택 컬럼(재현성/감사 목적: 권장)
threshold가 “어떻게” 산출되었는지까지 추적할 수 있으면, 재학습/재검증이 쉬워진다.

- thr_method: 예) `quantile` / `performance_search` / `manual`
- thr_seed: 탐색 랜덤시드(해당 시)
- thr_search_space_version: 탐색 공간 정의 버전(해당 시)
- thr_notes: 자유 메모(짧게)

> **중요:** Contract는 “threshold 값 정합성”만 요구한다.  
> `thr_method`는 값의 출처/재현성 향상을 위한 **보조 메타**이며, 필수 계약은 아니다.

### 3.4 model-pack 부가 파일
아래 파일은 model-pack 정합성 규칙을 구성한다.

- `gate_config.json`  
  - Gate 기본값/하드캡 등 “모델/데이터 정합성 성격” 파라미터를 동봉하고 싶을 때 사용.
  - 운영에서 즉시 대응이 필요한 값(예: 롤오버 차단 시간)은 EA 입력 파라미터로 분리 권장.
- `scaler_stats.json` (필수)
  - 입력 표준화(예: mean/std) 정보를 EA에서 적용하기 위한 필수 파일이다.
  - 형식은 `mean[12]` + `std[12]`로 고정한다.
  - EA는 feature 0~11에만 적용하고, feature 12~21은 원형 그대로 유지한다.
  - 누락/파싱 실패/길이 불일치/비정상 std(<=0)는 model-pack 불완전으로 간주하며, 런타임은 PASS-only로 전환한다.
  - 모델 내부에서 스케일링/정규화를 수행하는 것은 금지(Contract 8절 취지와 동일).

---

## 4. 학습 데이터 규격

### 4.1 기본 소스
- EA의 `bar_log_YYYYMMDD.csv` 계열이 학습 입력의 1차 소스다(실시간 입력=학습 입력 정합성 목적).

### 4.2 bar_log 최소 필수 컬럼(권장)
- time(바 마감 timestamp), symbol
- price_basis(Bid)
- OHLC(open,high,low,close)
- spread_price 또는 spread_points(+Point로 환산 가능)
- ATR14, ADX14, atr_pct
- regime_id(0~5), cand_long/cand_short
- 피처 22개(feature_0..21) 또는 [64x22]를 재구성할 정보
- Stage1 출력: onnx_p_long, onnx_p_short, onnx_p_pass, stage1_argmax
- Stage2 raw: prm_raw_0..5
- 조립 결과: final_dir, flip_used, k_sl_req, k_tp_req, k_sl_eff, k_tp_eff, hold_bars
- 게이트/실행 상태: gate_pass, gate_reject_reason, dyn_spread_atr_max, dyn_dev_points, risk_pct, dist_atr, dist_atr_max_t, dist_atr_max_mode, has_position, bars_held
- 버전 메타: ea_version, model_pack_version, clf_version, prm_version, schema_version, candidate_policy_version, regime_policy_version, cost_model_version

> `atr_thr`, `adx_thr1`, and `adx_thr2` are stored in `pack_meta.csv`, not repeated on every bar.
> See `design/BAR_LOG_SCHEMA.md` for the current runtime column mapping.

### 4.3 권장 산출물 포맷(학습/라벨)
- bar_log 원본은 CSV여도 되지만, 학습 파이프라인 내부 산출물(윈도우/라벨/메타)은 **Parquet 권장**
  - 장점: 스키마/타입 보존, 압축, 대용량 처리 유리
  - 단점: 환경에 따라 뷰어/의존성 필요
- CSV로도 가능하되, dtype/스키마가 흔들리지 않도록 별도 스키마 파일(json/yaml 등)을 유지 권장

---

## 5. 라벨링(정답 생성) - Action-search (H=72)

### 5.1 공통 가정(거래 시뮬레이션)
- 의사결정 시점: bar t close 확정 직후
- 진입 가격: bar t+1 open (OHLC 근사)
- SL/TP 거리: ATR14_t 기준
- lookahead: H=72 bars
- TP/SL 동시 터치: 보수적으로 SL 먼저

### 5.2 비용(cost) 모델 - v0.1 고정
- cost = spread_component + slippage_component
- slippage_component: 진입 1회 + 청산 1회 = 2 * fixed_slippage_buffer
- fixed_slippage_buffer: slip_points=2 points (튜닝 가능, 버전으로 관리)

### 5.3 PASS 라벨 규칙(기본)
- best_R <= R_pass_buffer(=0.05) 이면 PASS

---

## 6. 학습 샘플 선택 규칙(중요: Q6 반영)

### 6.1 Stage1(방향/패스 분류) 샘플 규칙
Stage1은 “운영 안정성(특히 cand=0에서 PASS가 잘 나오게)”를 위해 샘플 규칙을 다음처럼 고정한다.

- 샘플 타입 A: cand_long XOR cand_short == 1  
  - 라벨: Action-search로 LONG/SHORT/PASS 결정(기존 방식)
- 샘플 타입 B: cand_long==0 AND cand_short==0  
  - 라벨: **PASS로 강제(forced PASS)**  
  - 목적: cand=0 입력 분포에서 p_pass 캘리브레이션/안정화

권장 운영(데이터 균형):
- cand=0 샘플이 과도하게 많아 PASS만 학습되는 것을 막기 위해,
  - cand=0 샘플 비율을 상한(예: 전체의 30~50%)으로 제한하거나
  - cand=0 샘플 가중치를 낮춘다(예: weight=0.3)

> 주의: Stage1은 “신규 진입”만이 아니라 “보유 중 조기청산 신호”에도 쓰일 수 있으므로, cand=0 분포 학습이 실전 안정성에 중요하다.

### 6.2 Stage2(파라미터 모델) 샘플 규칙
- **cand_long XOR cand_short == 1**인 바만 사용  
- 이유: Stage2는 “진입 후보가 있는 상황에서의 운용 파라미터”를 학습하는 것이 목적이며, cand=0에서의 파라미터는 의미가 없거나 사용되지 않는다.

---

## 7. 모델 학습 규격(요약)

### 7.1 Stage1 (6개, regime별)
- 입력: X [1,64,22] float32
- 출력: [1,3] softmax → [p_long,p_short,p_pass]
- 손실: cross-entropy
- 참고: PASS 과다/부족 시 class weight 조정 가능

### 7.2 Stage2 (6개, regime별)
- 입력: X [1,64,22] float32
- 출력: [1,6] = [k_sl_L,k_tp_L,hold_L,k_sl_S,k_tp_S,hold_S]
- 손실: Huber 또는 L1 권장
- hold는 회귀로 예측 후 round/clamp

#### 7.2.1 비해당 방향(3개) 학습 처리(권장)
cand_long만 있는 샘플에서 short 3개(또는 반대)를 “의미 있는 타깃”으로 정의하기 어렵다.  
따라서 아래 중 하나를 선택해 일관되게 적용한다.

- 권장: **loss masking**  
  - 해당 방향 3개만 loss에 포함(나머지 3개는 loss 제외)
- 대안: 더미 타깃 채움(고정 상수 등)  
  - 구현은 단순하지만 방향 간 커플링 왜곡 가능

> 어떤 방식을 쓰든, **런타임 조립 규칙(방향에 맞는 3개만 사용)** 은 고정이다.

---

## 8. ONNX export 요구사항(고정)
- 모든 텐서는 float32
- 입력 shape 고정 [1,64,22] (dynamic axis 금지)
- Stage1 출력 [1,3], Stage2 출력 [1,6]
- 모델 내부에 추가 정규화/스케일링 금지(EA에서 스케일된 입력 제공 전제)
- 파일명에 최소 (regime_id, stage, 버전) 포함
- (권장) opset은 팀 표준으로 고정하여 export(현재 baseline: 17)  
  - 프로젝트 내에서 opset을 섞지 않는다.

---

## 9. 로깅/메타데이터(학습 재현 목적)
- bar_log/trade_log에 아래를 남긴다:
  - model_pack_version, clf_version, prm_version, schema_version, cost_model_version
- 추론 출력(p_*, k_*, hold)과 EA 최종 행동(PASS/LONG/SHORT, flip 여부)을 같이 남긴다.
- 라벨 파일에도 동일 버전/threshold 정보를 기록한다.
- (권장) thr_method 등 선택 메타를 함께 남겨 “threshold 재현”이 가능하게 한다.

Current runtime note:
- `atr_thr`, `adx_thr1`, and `adx_thr2` are stored in `pack_meta.csv`, not
  repeated on every bar in `bar_log`.
- Current runtime `clf_version` and `prm_version` are aliases of
  `model_pack_version` until independent per-model runtime versioning is added.
