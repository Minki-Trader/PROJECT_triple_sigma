# CODEX Phase A Review v2

> Date: 2026-03-12
> Scope: 이전 리뷰 `_coord/ops/CODEX_PHASE_A_REVIEW.md`의 5개 보류 조건 재검토
> Target files:
> - `tools/run_campaign_backtest.py`
> - `tools/validate_campaign_run.py`
> - `tools/parse_step21_run.py`
> - `_coord/ops/MASTER_TABLE_CONTRACT.md`
> - `_coord/ops/AGENT_ROLE_POLICY.md`
> - `_coord/ops/STEP21_OPS_CHECKLIST_v2.md`
> - `_coord/ops/schemas/*.schema.json`
> Final Verdict: `보류`

## 주요 findings

1. `[높음]` 보류 조건 3은 아직 닫히지 않았다. runner는 여전히 preset에 `FromDate`/`ToDate`를 date-only로 기록하고(`tools/run_campaign_backtest.py:108-121`), validator는 `window_from`/`window_to`의 시각을 잘라낸 뒤 1일 tolerance로만 raw bar range를 검사한다(`tools/validate_campaign_run.py:199-311`). 이전 리뷰의 해소 조건은 "minute-level window lineage를 실제 run output에 대해 강제하거나, 최소한 post-parse에서 first/last bar를 manifest boundary와 hard check"였는데, 현재 구현은 그 수준에 도달하지 못했다.

2. `[높음]` 보류 조건 4도 아직 닫히지 않았다. runner/validator가 schema 파일을 로드하기는 하지만, 두 구현 모두 `required`와 top-level `const`만 확인하는 경량 검사에 머문다(`tools/run_campaign_backtest.py:394-459`, `tools/validate_campaign_run.py:340-389`). S1은 `hash_manifests.pack_hash_ref`를 `string`으로 요구하지만(`_coord/ops/schemas/campaign_run_manifest.schema.json:111-123`), runner는 pack hash가 없으면 여전히 `None`을 기록할 수 있고(`tools/run_campaign_backtest.py:383-386`), seal 단계는 이를 hard fail이 아니라 warning으로만 출력한다(`tools/run_campaign_backtest.py:411-414`). 재현 확인 결과 `validate_against_schema()`는 `pack_hash_ref: null` 사례에 대해 빈 에러 리스트(`[]`)를 반환했다.

3. `[중간]` 보류 조건 5는 코드/계약 문서 기준으로는 대부분 해소됐지만, ops checklist 문서는 아직 내부 정합성이 닫히지 않았다. `MASTER_TABLE_CONTRACT.md`는 v2.0 헤더, `EXIT_FORCE` taxonomy, current contract version `2.0`을 모두 맞췄고(`_coord/ops/MASTER_TABLE_CONTRACT.md:3-10`, `_coord/ops/MASTER_TABLE_CONTRACT.md:151-155`, `_coord/ops/MASTER_TABLE_CONTRACT.md:234-238`), parser도 `contract_version: "2.0"`을 기록한다(`tools/parse_step21_run.py:340-347`). `AGENT_ROLE_POLICY.md`의 S1/S2/S3 상태도 `Complete`로 갱신됐다(`_coord/ops/AGENT_ROLE_POLICY.md:126-139`). 하지만 checklist는 같은 문서 안에서 F1/F3를 `DONE`으로 적으면서도 runner/validator/contract-v2 항목을 여전히 미체크 또는 `NEEDS UPDATE`로 남겨 두었다(`_coord/ops/STEP21_OPS_CHECKLIST_v2.md:99-125`, `_coord/ops/STEP21_OPS_CHECKLIST_v2.md:191-201`, `_coord/ops/STEP21_OPS_CHECKLIST_v2.md:240-246`).

## 보류 조건별 판정

| # | 이전 보류 조건 | 현재 근거 | 판정 |
|---|----------------|-----------|------|
| 1 | `run_campaign_backtest.py`의 pack path를 실제 `MQL5/Files` 기준으로 수정하고 `pack_hash_manifest.json` 생성 보장 | runner가 `PROJECT_triple_sigma -> Experts -> MQL5 -> Files` 경로를 사용하도록 수정됨 (`tools/run_campaign_backtest.py:330-344`). 현재 워크스페이스에서도 `..\\..\\Files\\triple_sigma_pack_step15_q1`는 존재하고 `..\\..\\..\\Files\\triple_sigma_pack_step15_q1`는 존재하지 않음이 확인됨. | `승인` |
| 2 | compile log 판정 로직을 `Result: X errors, Y warnings` 파싱으로 교체 | runner와 validator 모두 우선적으로 `Result:` 라인을 파싱하고, fallback은 summary line을 직접 세지 않도록 바뀜 (`tools/run_campaign_backtest.py:349-358`, `tools/validate_campaign_run.py:166-181`). | `승인` |
| 3 | minute-level window lineage를 실제 run output에 대해 강제하거나 post-parse에서 first/last bar를 manifest boundary와 hard check | runner는 여전히 preset에 시각을 버린 date-only 값을 기록 (`tools/run_campaign_backtest.py:108-121`). validator는 manifest 시각도 date-only로 잘라 파싱하고 1일 tolerance를 허용 (`tools/validate_campaign_run.py:227-240`, `tools/validate_campaign_run.py:295-311`). minute-level hard check는 없음. | `보류` |
| 4 | S1/S2/S3 schema validation을 seal/validate 단계에 기계적으로 연결 | schema 로드 자체는 추가됐으나, 실제 검사는 `required`/`const`만 확인하는 경량 구현 (`tools/run_campaign_backtest.py:432-459`, `tools/validate_campaign_run.py:358-377`). S1의 `pack_hash_ref: string` 요구(`_coord/ops/schemas/campaign_run_manifest.schema.json:111-123`)가 seal/validate에서 타입 수준으로 강제되지 않음. | `보류` |
| 5 | contract v2 version string과 fallback taxonomy(`EXIT_FORCE`)를 전 파일에서 통일 | contract 문서와 parser 메타데이터는 v2.0으로 정렬됐고 (`_coord/ops/MASTER_TABLE_CONTRACT.md:3-10`, `_coord/ops/MASTER_TABLE_CONTRACT.md:151-155`, `_coord/ops/MASTER_TABLE_CONTRACT.md:234-238`, `tools/parse_step21_run.py:340-347`), AGENT_ROLE_POLICY의 schema 상태도 정리됨 (`_coord/ops/AGENT_ROLE_POLICY.md:126-139`). 다만 checklist가 동일 범위 deliverable을 미완료처럼 남겨 내부 정합성이 아직 닫히지 않음 (`_coord/ops/STEP21_OPS_CHECKLIST_v2.md:99-125`, `_coord/ops/STEP21_OPS_CHECKLIST_v2.md:191-201`, `_coord/ops/STEP21_OPS_CHECKLIST_v2.md:240-246`). | `보류` |

## 추가 확인

- 정적 검증: `python -m py_compile tools/run_campaign_backtest.py tools/validate_campaign_run.py tools/parse_step21_run.py` 통과.
- 스키마 재현 테스트: `tools.run_campaign_backtest.validate_against_schema()`에 `hash_manifests.pack_hash_ref = None`을 넣어도 에러가 발생하지 않음을 확인. 즉 "schema validation 연결"은 되었지만 "schema conformance 강제"는 아직 아니다.

## 최종 판정

- 판정: `보류`
- 이유: 이전 5개 보류 조건 중 1, 2는 해소됐지만 3, 4는 핵심 요구 수준에 미달하며, 5도 target 문서 세트 내부 정합성이 완전히 닫히지 않았다.
- 승인에 필요한 최소 추가 조치:
  1. raw bar first/last timestamp를 manifest의 분 단위 경계와 hard check하도록 validator 또는 post-parse gate 강화
  2. S1/S2/S3에 대해 타입, enum, pattern, nested required까지 포함하는 실제 schema conformance 검증을 fail gate로 승격
  3. `_coord/ops/STEP21_OPS_CHECKLIST_v2.md`의 runner/validator/contract-v2 상태 표기를 현재 구현 상태와 일치하도록 정리
