# CODEX Phase A Review

> Date: 2026-03-12
> Scope: Phase A 산출물 11개 + Audit Report / Roadmap / Checklist v2 / 이전 Codex 최종 검토 교차 대조
> Final Verdict: 보류

## 주요 지적사항

1. `[높음]` `tools/run_campaign_backtest.py`의 pack 경로 해석이 실제 MT5 `MQL5/Files` 경로와 다릅니다. `cmd_seal()`은 `project_root.parent.parent.parent / "Files"`를 사용해 `...\\Terminal\\<id>\\Files\\<pack_id>`를 찾지만, 현재 워크스페이스의 실제 pack 위치는 `...\\Terminal\\<id>\\MQL5\\Files\\<pack_id>`입니다. 결과적으로 `pack_hash_manifest.json` 생성을 건너뛰고(`tools/run_campaign_backtest.py:330-345`), S1은 `hash_manifests.pack_hash_ref`를 요구하며(`_coord/ops/schemas/campaign_run_manifest.schema.json:111-123`), validator는 해당 파일 부재를 hard fail로 처리합니다(`tools/validate_campaign_run.py:192-208`). 현재 환경에서도 `..\\..\\Files\\triple_sigma_pack_step15_q1`는 존재하고 `..\\..\\..\\Files\\triple_sigma_pack_step15_q1`는 존재하지 않음을 확인했습니다. 이 상태로는 `prepare -> seal -> validate`가 통과할 수 없습니다.

2. `[높음]` compile clean 판정 로직이 clean compile도 FAIL로 오판정합니다. runner와 validator 모두 `" error"` / `" warning"` substring count로 에러 수를 계산하는데(`tools/run_campaign_backtest.py:347-350`, `tools/validate_campaign_run.py:172-186`), 실제 retained compile log의 `Result: 0 errors, 0 warnings` 문자열은 이 방식에서 `1, 1`로 계산됩니다. 따라서 clean compile이어도 `compile_clean`이 실패할 수 있습니다. 이는 A2 완료 기준인 `0 error / 0 warning` gate를 현재 구현이 만족하지 못한다는 뜻입니다.

3. `[높음]` 분 단위 window lineage가 실제 실행 단계에서 보장되지 않습니다. campaign manifest는 "date-only values are NOT acceptable"를 명시하지만(`_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml:26-28`), runner는 `window_from`, `window_to`에서 시간을 제거해 `FromDate`, `ToDate`를 날짜만으로 기록합니다(`tools/run_campaign_backtest.py:107-120`). validator는 raw bar 범위를 검사하지 않고 run manifest 메타데이터만 비교합니다(`tools/validate_campaign_run.py:57-124`). 소스 트리에서도 분 단위 backtest boundary를 강제하는 EA input은 확인되지 않았습니다. 즉 manifest에는 benchmark `2024.06.04 17:25 -> 2025.04.02 09:00`를 적어도 실제 raw 출력은 경계일 전체를 포함할 수 있고, 그 상태로도 validate를 통과할 수 있습니다. Audit F1과 quantitative independence 요구를 만족했다고 보기 어렵습니다.

4. `[중간]` A3 schema 3종은 생성됐지만 산출물 conformance가 기계적으로 강제되지 않습니다. `run_campaign_backtest.py`와 `validate_campaign_run.py`는 S1/S2/S3를 로드하지 않으며 schema validation도 수행하지 않습니다. 그 결과 현재 코드만으로도 `pack_hash_ref: null` 같은 비정합 run manifest를 쓸 수 있는데(`tools/run_campaign_backtest.py:375-377`), S1은 이를 string으로만 허용합니다(`_coord/ops/schemas/campaign_run_manifest.schema.json:115-123`). A3 완료 기준인 "runner output이 schema에 맞는가"가 선언 수준에 머물러 있습니다.

5. `[중간]` A5 contract v2 정합성이 부분적으로만 닫혔습니다. 문서 헤더와 decision taxonomy는 v2.0인데(`_coord/ops/MASTER_TABLE_CONTRACT.md:3-10`, `_coord/ops/MASTER_TABLE_CONTRACT.md:151-155`), 같은 문서의 versioning section은 아직 `Current contract version: 1.0`로 남아 있습니다(`_coord/ops/MASTER_TABLE_CONTRACT.md:234-238`). 또한 parser는 여전히 `contract_version: 1.0`을 기록하고(`tools/parse_step21_run.py:346-348`), counterfactual builder는 fallback/legacy reason에서 `EARLY_EXIT`를 다시 방출할 수 있습니다(`tools/build_counterfactual_eval.py:32-37`, `tools/build_counterfactual_eval.py:191-197`). 현재 retained sample은 `EXIT_FORCE`를 쓰므로 당장 표면화되지는 않았지만, "contract v2 closed"라고 보기는 이릅니다.

6. `[낮음]` 문서 상태 표기는 일부 stale합니다. `AGENT_ROLE_POLICY.md`는 S1/S2/S3를 아직 `Planned`로 적고 있고(`_coord/ops/AGENT_ROLE_POLICY.md:128-139`), `STEP21_OPS_CHECKLIST_v2.md`는 A1-A5를 `NOT STARTED`로 남겨 현재 Phase A 산출물 상태와 어긋납니다. 실행 차단 이슈는 아니지만 validator/gatekeeper 운영 관점에서는 혼선을 줄 수 있습니다.

## 항목별 판정

- 완성도: A0, A1, A2, A3, A4, A5, A6에 해당하는 파일은 모두 존재합니다. 다만 A1/A2는 현재 구현상 실행 불능 수준의 blocker 2건이 있고, A5는 contract version sync가 덜 끝났습니다. 따라서 "산출물 존재"는 충족하지만 "Phase A 요구사항 충족"은 미달입니다.
- 정확성: A0의 7-role / no-self-promotion 정책, A4의 strict default + synthetic waiver, A6의 `runs/RUN_<ts>/...` 경로 문서화는 Audit Report Section 8 방향과 대체로 일치합니다. 반면 A1/A2는 F1 lineage와 F6 validator gate를 구현했지만 실제 경로/compile 판정 버그로 권고안대로 작동하지 않습니다.
- 일관성: `manifest.yaml`과 `OPTIMIZATION_OPERATOR_RUNBOOK.md`는 `runs/RUN_<ts>/20_raw`, `30_parsed` 구조로 정합합니다. `parse_step21_run.py`도 이 경로를 지원합니다. 그러나 schema ↔ runner, contract v2 ↔ parser metadata, exact window contract ↔ preset generation은 아직 불일치가 남아 있습니다.

## 이전 Codex 검토 3건 반영 여부

- `pack_hash Phase 충돌 해소`: 반영됨. 현재 Phase A 산출물 세트에서는 pack hash가 runner/seal 단계의 산출물로 정리되어 있고, 이전의 B4 중복 생성 관점 충돌은 target 파일들 안에서는 보이지 않습니다. 다만 실제 구현은 위 1번 blocker 때문에 정상 생성되지 않습니다.
- `runs/ 마이그레이션`: 반영됨. `manifest.yaml`과 runbook이 `runs/RUN_<ts>/...` 구조를 기준으로 갱신됐고, parser도 campaign-native layout을 지원합니다.
- `validator 증거 완전성`: 반영됨. validator는 raw completeness, compile clean, hash completeness, raw hash integrity를 모두 점검합니다. 다만 compile clean 로직 자체가 오판정 버그를 갖고 있어 구현 품질은 미완입니다.

## 실행 가능성 평가

- 정적 검증 결과 `python -m py_compile tools/run_campaign_backtest.py tools/validate_campaign_run.py tools/build_master_tables.py tools/build_counterfactual_eval.py tools/parse_step21_run.py`는 통과했습니다.
- CLI 진입점도 동작합니다. `python tools/run_campaign_backtest.py --help`, `python tools/validate_campaign_run.py --help` 모두 정상 출력됩니다.
- `parse_step21_run.py`는 `runs/RUN_<ts>/20_raw -> runs/RUN_<ts>/30_parsed` 경로를 지원하므로 `validate` 이후 `parse` 단계 자체는 연결 가능합니다.
- 그러나 현재 상태에서는 `seal`이 pack hash를 제대로 만들지 못하고, `validate`는 clean compile도 FAIL로 오판정하므로 실제 MT5 terminal 기준 `prepare -> tester -> seal -> validate -> parse` 파이프라인은 성공적으로 닫히지 않습니다.
- 위 두 blocker를 고쳐도, 분 단위 window boundary를 실제 raw 산출물에서 검증하지 않는 한 "admissible baseline" 판정은 여전히 `PROVISIONAL`이 맞습니다.

## 잘 반영된 점

- `_coord/ops/AGENT_ROLE_POLICY.md`는 Audit Section 8의 역할 토폴로지를 7 roles로 정리했고, `writer self-promotion 금지`를 명시적으로 금지합니다.
- `tools/build_master_tables.py`는 close-before-modify를 strict mode에서 hard fail로 승격했고, synthetic regression에만 waiver를 허용합니다.
- `tools/build_counterfactual_eval.py`는 unmapped ENTRY를 coverage gate에 포함시켰고 기본 threshold를 0으로 둬 strict mode를 기본값으로 설정했습니다.
- `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml`과 `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md`는 legacy flat archive와 admissible runs 구조를 문서상 구분했습니다.

## 최종 판정

- 판정: `보류`
- 해소 조건:
  1. `run_campaign_backtest.py`의 pack path를 실제 `MQL5/Files` 기준으로 수정하고 `pack_hash_manifest.json` 생성 보장
  2. compile log 판정 로직을 `Result: X errors, Y warnings` 파싱으로 교체
  3. minute-level window lineage를 실제 run output에 대해 강제하거나, 최소한 post-parse에서 first/last bar를 manifest boundary와 hard check
  4. S1/S2/S3 schema validation을 seal/validate 단계에 기계적으로 연결
  5. contract v2 version string과 fallback taxonomy(`EXIT_FORCE`)를 전 파일에서 통일
