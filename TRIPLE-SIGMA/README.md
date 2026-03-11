# EA/ONNX 문서 패키지 (최종 고정본 / LATEST)

- 기준일(Freeze): **2026-03-04 (Asia/Seoul)**
- 목적: 작업 시작 전에 문서 간 **불일치/모호성**을 제거하고, 앞으로 개발/리뷰 중에 “어느 문서가 맞지?”로 헷갈리는 일을 없앤다.
- 원칙: **ONNX Dev Spec(최신) + Policy Freeze(Q1~Q10)** 를 최종 기준으로 삼아 정합성을 맞췄다.

---

## 1) 저장소(Repo) 운영 규칙 — “파일명은 LATEST, 버전은 문서 안에만”

### ✅ 파일명 규칙(고정)
- 버전 문자열(`v0.x.y`)은 **파일명에 넣지 않는다.**
- 저장소에는 아래 **고정 파일명만** 둔다(= 항상 최신/유효본).

| 구분 | 파일명 | 의미 |
|---|---|---|
| 최상위 정책 | `POLICY_FREEZE.md` | Q1~Q10 최종 결정(정책 Freeze) |
| 조립 계약 | `CONTRACT.md` | EA↔ONNX I/O 계약 + 불변 규칙 |
| EA 런타임 | `EA_RUNTIME.md` | EA 실행/게이트/로그/운영 규격 |
| ONNX 개발 | `ONNX_DEV_SPEC.md` | 라벨링/학습/패키징/런타임 조립 규칙 |
| 변경 이력 | `CHANGELOG.md` | 무엇이 언제 바뀌었는지 기록 |
| 참고 | `reference/*` | 설명/예시(충돌 시 효력 없음) |
| 설계도(조립품) | `design/*` | STEP01~STEP16 설계도(직렬 워크플로우 산출물) |

### ✅ “버전은 어디에 쓰나?”
- 각 문서 **첫 줄(제목)** 에 문서 버전을 유지한다. 예: `Contract v0.1.1`
- 각 문서 상단 메타(기준일/적용 범위)에 **Effective Date** 를 유지한다.
- 구버전 문서는 이 저장소에 올리지 않는다(별도 보관).  
  대신 필요하면 **Git tag** 로 “그 시점 스냅샷”을 남긴다(추천):  
  - 예: `docs-freeze-20260304`

---

## 2) 문서 우선순위 — 충돌하면 무엇을 따른다?

1) `POLICY_FREEZE.md` (가장 상위, “정책 결정” 문서)  
2) `CONTRACT.md` (EA↔ONNX 조립 계약)  
3) `EA_RUNTIME.md` (EA 운영 규격)  
4) `ONNX_DEV_SPEC.md` (ONNX 개발 규격)  
5) `reference/*` (참고용, 충돌 시 효력 없음)

> **한 줄 요약:** “정책은 POLICY_FREEZE, 인터페이스는 CONTRACT”만 기억하면 된다.

---

## 3) 이번 Freeze에서 확정된 핵심 요약(비개발자용)

- 패턴: **Pattern C(Hybrid)** 고정
- Candidate: **one-hot-or-zero** (1,1 금지)
- 모델 배포: **Regime(6) × Two-stage(2) = 12개 model-pack**
- PASS 기본값: **k_sl=1.5, k_tp=2.0, hold=24**
- 로그: **model_pack / stage 버전 + cost_model_version**까지 기록
- 보유 상한: **총 72 bars cap(강제 청산)**
- 학습(중요): **Stage1은 cand=0도 학습 포함(라벨 PASS 강제)**, Stage2는 cand=1만
- price_basis: **Bid OHLC 기준** 고정

---

## 4) 산출물 디렉토리 규칙(권장)

### 4.1 설계도(조립품) 문서
- `design/STEP01_*.md` … `design/STEP16_*.md`  
  - deep-research-report의 STEP1~16을 “구현 가능한 설계도”로 분해한 결과물.
  - 설계도는 **직렬(선형) 조립**을 전제로 작성한다.

### 4.2 model-pack 배포 디렉토리(런타임/학습 공통)
권장 구조(예시):
- `model_pack/`
  - `clf_reg0_vXXX.onnx` … `clf_reg5_vXXX.onnx`
  - `prm_reg0_vXXX.onnx` … `prm_reg5_vXXX.onnx`
  - `pack_meta.csv` (필수)
  - *(선택)* `gate_config.json` (게이트 기본값/하드캡 등 “모델 정합성” 성격)
  - *(필수)* `scaler_stats.json` (입력 표준화용 `mean[12]` + `std[12]`)

> ⚠️ 운영에서 즉시 대응이 필요한 값(예: 롤오버 차단 시간)은 model-pack에 넣지 않고, EA 입력 파라미터로 분리하는 것을 권장한다.

---

## 5) 문서 변경 작업(앞으로 수정할 때) 체크리스트

1) 변경이 “정책 결정(Q1~Q10 류)”이면 → `POLICY_FREEZE.md`부터 수정  
2) 변경이 “I/O / 피처 index / 레짐 차원”이면 → `CONTRACT.md` 수정(= 영향이 가장 큼)  
3) 변경이 “런타임 동작/게이트/로그/주문 보정”이면 → `EA_RUNTIME.md` 수정  
4) 변경이 “라벨링/학습/패키징/pack_meta 컬럼”이면 → `ONNX_DEV_SPEC.md` 수정  
5) 변경 후에는 반드시 `CHANGELOG.md`에 1~3줄로 기록  
6) 팀 공유 시에는 “파일 링크” 대신 **고정 파일명(POLICY_FREEZE.md / CONTRACT.md …)** 만 공유  
7) (추천) 큰 변경은 tag로 스냅샷 남기기: `docs-YYYYMMDD`
