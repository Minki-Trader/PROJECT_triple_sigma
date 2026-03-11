# GPT Pro (ChatGPT 5.4 Pro) 프로젝트 감사 보고서

- **날짜**: 2026-03-11
- **사고 시간**: 64분 2초 (Thought for 64m 2s)
- **입력**: GPT-PRO-FOR-REPORT.zip (256MB, 5601 entries)
- **대상**: PROJECT_triple_sigma 전체 (Step21 Tx-Authoritative Protective Runtime)

---

## 사고 과정 메시지 (Activity Panel)

> 작업 범위가 넓어서 먼저 ZIP 전체를 실제로 풀어 구조·코드·산출물을 기준으로 감사를 진행하겠습니다. 병렬로 운영 문서와 현재 체크리스트 주장도 대조해, 재현 가능한 사실과 설계 권고를 분리하겠습니다.

> 초기 대조에서 체크리스트와 ZIP 추출본 사이에 괴리가 보여, `_coord/ops`·`_coord/logs`·`_coord/campaigns` 누락이 추출 문제인지 실제 부재인지부터 검증하고 있습니다. 한편 parser/master-table 계열 스크립트와 WF0/WF1/WF3 관련 문서상 스캐폴드는 보이지만, 운영 계약 충족과 기계적 검증 가능성은 아직 별도 확인이 필요합니다.

> 추출본이 한 번 불완전했던 정황이 보여 실제 ZIP을 재추출해 대조 중이며, `step21_control_trade` 내부의 `trade_log.csv`·`manifest.json`·`exec_state.ini` 실재는 확인했습니다. 이제 parser/master/counterfactual/daily-risk 스크립트를 retained artifact에 직접 돌려, "존재"가 아니라 gate로 쓸 수 있는지 검증하겠습니다.

> 독립 재실행 기준으로는 CP1 PASS도 그대로 수용할 수 없습니다. trailing probe에서 `MODIFY`·`EXIT` 동일 timestamp 겹침 4건이 나왔고, `build_counterfactual_eval.py`는 모든 `EXIT`를 `EARLY_EXIT`로 오염시킵니다.

---

## 1. Executive Summary

ZIP 기준 최종 판정은 명확합니다. 현재 스냅샷은 Step21 runtime code와 Step14/15 ML lineage를 검토하기에는 충분하지만, pre-optimization operating stack으로는 아직 승격 불가입니다. 핵심 문제는 EA semantics 자체보다, 그것을 재현·검증·승격하는 evidence/contract layer가 ZIP 안에 존재하지 않는다는 점입니다.

코드/산출물로 검증된 사실은 다음입니다.

Step21 runtime surface 자체는 실제로 구현되어 있습니다. `src/ea/TripleSigma.mq5`, `src/include/TS_Execution.mqh`, `src/include/TS_Logger.mqh`, `design/BAR_LOG_SCHEMA.md`는 tx-authoritative entry/exit handling, protective modify family, widened trade/bar log schema, broker audit surface, runtime reload status fields를 반영합니다.

Step14/15 ML chain도 실제 증거가 강합니다. `_coord/artifacts/step14_validation_q1_out/validation_metadata.json`에는 `outer_split_audit.passed=true`, `no_time_leakage=true`, `embargo_bars=72`가 있고, `stage1_selection_report.json`은 `eligible_candidate_count=0`, `used_control_fallback=true`를, `stage2_selection_report.json`은 `provisional_winner_candidate_id=stage2_c02`를 기록합니다. `_coord/artifacts/step15_export_q1_out/export_validation_report.json`은 `accepted=true`와 A1–A9 전부 true를 기록합니다. 즉, ML validation/export lineage는 ZIP 안에서 실제로 검증 가능한 부분입니다.

반대로 Step21 운영 증거 체인은 ZIP 안에서 붕괴되어 있습니다. `_coord` 루트에는 `artifacts/`만 있고 `_coord/logs`, `_coord/tester`, `_coord/ops`, `_coord/campaigns`, `_coord/releases`, `_coord/rollback_points`, `_coord/notebooks`가 없습니다. `_coord/artifacts/step21_*`도 없고, `triple_sigma_runtime_patch/`도 없으며, `TripleSigma.mq5`가 참조하는 runtime patch INI도 없습니다. 그런데 `README.md`와 `STEP21_CLOSEOUT_AND_VERIFICATION.md`는 이들이 "this snapshot"에 retained 되었다고 적고 있습니다. 따라서 Step21 runtime pass claim은 문서상 주장이지, ZIP 기준 독립 재현 증거는 아닙니다.

가장 중요한 불일치는 `PROJECT_triple_sigma_Step21_ops_guide_en.docx`와 `STEP21_OPS_CHECKLIST.md` 사이에 있습니다. ZIP 안의 실제 DOCX를 추출해 보면 paragraph 17은 "No operating parser/analytics stack exists yet.", paragraph 24는 "Missing: parser stack, control registry, campaign manifests, release/rollback standards, operator runbook."라고 적습니다. 또 paragraphs 160–167은 `tools/parse_step21_run.py`, `build_master_tables.py`, `build_counterfactual_eval.py`, `build_daily_risk_metrics.py`, `_coord/ops/MASTER_TABLE_CONTRACT.md`, `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml`, `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md`를 "Minimum operating set"으로 제시합니다. 그런데 `STEP21_OPS_CHECKLIST.md`는 동일 항목을 DONE/PASS로 표시합니다. 이 체크리스트는 이 ZIP의 증빙 문서로 사용할 수 없습니다.

판단은 다음과 같습니다. 현재 ZIP은 "runtime code review snapshot"으로는 유효하지만, "optimization operating readiness pack"으로는 FAIL입니다. 특히 counterfactual coverage integrity, data freeze manifest, control pack registry, campaign scaffold, release/rollback reproducibility는 PASS를 줄 수 없습니다.

---

## 2. Critical Blockers

### CB1. Step21 retained evidence bundle 부재

**Severity**: Critical

**검증된 사실**: `README.md:37-50`과 `STEP21_CLOSEOUT_AND_VERIFICATION.md:19-33, 71-76`은 compile log, Step21 tester presets, smoke summaries, step21 artifact packages가 이 snapshot에 retained 되었다고 적습니다. 그러나 실제 ZIP의 `_coord` 루트에는 `artifacts/`만 있고 `_coord/logs`, `_coord/tester`가 없습니다. `_coord/artifacts`도 step11~20까지만 존재하고 `step21_*` 디렉토리는 없습니다.

**Impact**: CP0, CP1, WF2의 pass claim을 독립적으로 재현할 수 없습니다. Step21이 "locally verified"라는 상태는 현재 ZIP 기준으로는 문서 주장일 뿐입니다.

**Remediation**: 최소한 `_coord/logs/compile/compile_step21_wip.log`, `_coord/tester/step21/*.ini`, `_coord/logs/smoke/step21_*_summary.md`, `_coord/artifacts/step21_*/*`를 모두 포함한 evidence-complete snapshot을 다시 발행해야 합니다. 그 전까지 Step21 runtime verification 상태는 PROVISIONAL로 강등되어야 합니다.

### CB2. 체크리스트는 이 ZIP의 admissible certification이 아님

**Severity**: Critical

**검증된 사실**: `README.md:3-4`는 snapshot as of 2026-03-09라고 적고, `STEP21_OPS_CHECKLIST.md:3-5`는 2026-03-10 생성/수정, post-codex review fixes라고 적습니다. 더 중요하게, 실제 ZIP의 DOCX는 parser stack, control registry, campaign manifests, release/rollback standards, operator runbook을 missing 또는 minimum operating set으로 두는데, 체크리스트는 같은 항목을 DONE/PASS로 표기합니다. 실제 filesystem도 체크리스트의 완료 주장과 일치하지 않습니다.

**Impact**: `STEP21_OPS_CHECKLIST.md`를 source-of-truth로 신뢰하면 readiness가 과대평가됩니다. 특히 parser, runbook, campaign, rollback에 대한 PASS가 허위 양성(false positive)으로 작동합니다.

**Remediation**: 체크리스트는 수동 문서가 아니라 snapshot manifest에서 자동 생성되어야 합니다. 문서마다 snapshot date, repo commit SHA, artifact hash를 묶어 version-lock 해야 합니다.

### CB3. counterfactual coverage/integrity gate가 promotion-grade가 아님

**Severity**: Critical

**검증된 사실**: `tools/build_counterfactual_eval.py:31-44`에는 `floor_to_m5()`가 있어 prior exact-match bug에 대한 code-level fix가 들어가 있습니다. `:203-225`에는 `active_direction` 매핑도 있어 prior NO_EXIT LONG hardcode 문제가 부분 수정되었습니다. 그러나 `:128-135`와 `:197-198`에서 unmapped trade events는 카운트만 하고 stdout warning으로 끝납니다. `parse_manifest.json`에는 raw-vs-mapped coverage가 저장되지 않습니다. 또한 `:156-173`은 모든 EXIT를 무조건 `decision_type="EARLY_EXIT"`로 기록합니다. `:235`는 NO_EXIT에서 active direction을 못 찾으면 여전히 LONG으로 fallback 합니다.

**Impact**: 사용자가 실제로 경험한 silent drop / side distortion failure class가 현재 구현에서도 다시 통과할 수 있습니다. 이 상태의 counterfactual_eval은 exploratory analysis에는 쓸 수 있지만 승격 gate로는 부적합합니다.

**Remediation**: `coverage_manifest.json`을 추가해 ENTRY/EXIT/MODIFY/NO_EXIT raw count, mapped count, unmapped IDs, direction coverage, exit_reason taxonomy를 모두 기록하고, EXIT/MODIFY unmapped가 1건이라도 있으면 hard fail해야 합니다. EARLY_EXIT와 일반 EXIT를 분리하고, NO_EXIT는 default LONG fallback을 제거해야 합니다.

### CB4. operational contract layer 부재

**Severity**: High

**검증된 사실**: `_coord/ops/MASTER_TABLE_CONTRACT.md`, `_coord/ops/control_pack_registry.yaml`, `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml`, `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md`, `_coord/ops/SELECTION_RELEASE_RUNBOOK.md`, `_coord/ops/ROLLBACK_POINT_STANDARD.md`는 모두 ZIP에 없습니다. 그런데 `tools/build_master_tables.py`, `build_counterfactual_eval.py`, `build_daily_risk_metrics.py`는 모두 "per MASTER_TABLE_CONTRACT.md v1.0"를 전제로 작성되어 있습니다.

**Impact**: parser와 analytics가 코드로만 존재하고, auditable contract와 operator procedure가 없습니다. 이는 "작동한다"와 "승격 가능하다"를 구분하지 못하게 만듭니다.

**Remediation**: contract 문서와 manifest/runbook을 먼저 만들어야 합니다. 이후 writer가 아니라 independent validator가 contract conformance를 판정하도록 해야 합니다.

### CB5. release/rollback reproducibility가 ZIP 기준으로 부재

**Severity**: Critical

**검증된 사실**: `src/ea/TripleSigma.mq5:51-52`는 `triple_sigma_runtime_patch\\step21_runtime_reload_success.ini`와 rollback peer INI를 `#property tester_file`로 참조합니다. 그러나 `triple_sigma_runtime_patch/` 디렉토리는 ZIP에 없습니다. 같은 파일은 `triple_sigma_pack_v1`, `triple_sigma_pack_step15_q1`, `triple_sigma_pack_long_step16`도 참조하지만, repo root에는 이 pack 디렉토리도 없습니다. `_coord/releases`와 `_coord/rollback_points`도 없습니다.

**Impact**: WF8 release candidate와 WF9 rollback point는 현재 ZIP으로 재현할 수 없습니다. runtime reload/rollback claims 역시 executable evidence가 아니라 문서 주장에 머뭅니다.

**Remediation**: runtime patch inputs, selected pack directory, pack hash manifest, RC manifest, rollback manifest를 모두 immutable bundle로 남겨야 합니다.

### CB6. 자동화 스크립트가 workstation-bound 상태

**Severity**: High

**검증된 사실**: `tools/run_step21_matrix.ps1:3-8`은 specific Windows user path, terminal path, tester agent log path를 하드코딩합니다. `tools/analyze_us100_history_quality.py:13-18`도 Windows terminal/common files path를 하드코딩합니다.

**Impact**: Claude Code CLI / Codex CLI 기반의 reproducible automation이나 clean-room replay가 불가능합니다. 개발자 개인 워크스테이션 이외의 환경에서는 pipeline이 깨집니다.

**Remediation**: 모든 path를 campaign manifest 또는 environment variable로 외부화하고, repo-relative resolution을 기본값으로 사용해야 합니다.

### CB7. parser가 Step21 핵심 surface를 과소검증함

**Severity**: High

**검증된 사실**: `tools/parse_step21_run.py:69-82`는 Step21 bar log tail을 optional로 둡니다. 하지만 `design/BAR_LOG_SCHEMA.md:77-101`은 이를 current runtime/audit tail로 명시합니다. 또 `parse_step21_run.py:94`에 `VALID_TX_AUTHORITY`가 정의되어 있지만 실제 검증에는 사용되지 않습니다.

**Impact**: parser가 Step21-specific audit surface 없이도 pass할 수 있고, tx-authority lineage integrity를 보장하지 못합니다. Step21의 핵심 가치인 authority-vs-sync 분리가 analytics layer에서 무력화됩니다.

**Remediation**: `log_schema_version==2.0` 또는 Step21 run에서는 tail columns를 mandatory로 바꾸고, `tx_authority` 값을 event type별로 강제 검증해야 합니다.

### CB8. daily risk metrics는 아직 release-grade가 아님

**Severity**: High

**검증된 사실**: `tools/build_daily_risk_metrics.py:102-107`은 `expectancy_r`를 mean absolute loss proxy로 계산하고, `:156`은 `net_pnl = gross_pnl` placeholder를 둡니다. commission/slippage/equity normalization이 없습니다.

**Impact**: PF, expectancy, drawdown은 exploratory ranking에는 쓸 수 있지만, institutional acceptance gate로 바로 쓰면 과대평가 위험이 큽니다.

**Remediation**: MT5 report cost, realized slippage, equity normalization을 포함해 net-of-cost 및 percentage drawdown 지표를 추가해야 합니다.

---

## 3. Pre-Optimization Readiness Audit

이 절의 **실제 구현 상태**는 ZIP 기준 검증된 사실이고, **리스크**와 **필요 수정 사항**은 판단/권고입니다.

| 컴포넌트 | 기대 contract | 실제 구현 상태 | Severity | 리스크 | 필요한 수정 사항 | 판정 |
|---------|-------------|-------------|----------|-------|---------------|------|
| parser pipeline | raw run intake → schema validation → parse manifest → hard integrity gates | `tools/parse_step21_run.py`, `build_counterfactual_eval.py`, `build_daily_risk_metrics.py`는 존재하고 `py_compile`은 통과함. 그러나 Step21 tail이 optional이고, `tx_authority` 검증이 없으며, counterfactual coverage mismatch가 hard fail이 아님. Step21 raw outputs가 ZIP에 없어 replay 검증 불가. | High | malformed Step21 run 또는 partial mapping이 "pass"로 보일 수 있음 | Step21 tail mandatory, `tx_authority` 검증, raw-vs-mapped coverage manifest, golden replay test 추가 | PROVISIONAL |
| master table builders | auditable `bars_master`, `trades_master`, `execution_master`, `modify_master`, `audit_master` + contract conformance | `tools/build_master_tables.py`는 존재. orphan EXIT 검출, modify overlap warning, execution sequence check가 구현되어 있음. 하지만 `_coord/ops/MASTER_TABLE_CONTRACT.md`가 없고, Step21 sample run이 없어 semantic validation 불가. | High | derived ledgers가 code-dependent artifacts로만 존재하고 source-of-truth contract가 없음 | contract 문서 추가, golden dataset replay, reason-level assertions 추가 | PROVISIONAL |
| data freeze manifest | role-locked optimization/benchmark/OOS/stress windows + overlap audit + data quality evidence | `design/US100_RealTick_Backtest_Data_Policy.md`는 존재. 그러나 `_coord/artifacts/us100_history_quality/`가 없고, `_coord/BACKTEST_BASELINE.md`도 없으며, `data_freeze_manifest.yaml`도 없음. history-quality analyzer script만 존재함. | High | window drift, overlap, generated-tick contamination 리스크 | retained history-quality report + baseline doc + immutable freeze manifest 생성 | FAIL |
| control pack registry | runtime-integrity control vs profitability control 분리, pack hash, parity evidence | Step15 export/parity evidence는 존재하고, Step16~20 smoke artifacts도 존재함. 그러나 `_coord/ops/control_pack_registry.yaml`는 없음. runtime pack directories도 root에 없음. | High | Step16 smoke pack이 profitability baseline으로 오염될 수 있음 | registry에 role, source artifact, pack hash, parity proof, approval state를 명시 | FAIL |
| campaign scaffold | campaign manifest, raw/parser/analytics/benchmark/OOS/stress hierarchy, manifest-driven orchestration | `_coord/campaigns/`가 없고 campaign manifest도 없음. `tools/run_step21_matrix.ps1`는 regression smoke runner이며 campaign orchestrator가 아님. `tools/run_campaign_matrix.ps1`도 없음. | Critical | campaigns 간 evidence contamination, rerun 불가, operator ambiguity | `_coord/campaigns/<id>/...` hierarchy와 manifest-driven runner 추가 | FAIL |
| release / rollback scaffold | RC bundle, rollback bundle, patch inputs, hashes, runbooks | `_coord/releases/`, `_coord/rollback_points/`, 관련 runbook 전부 없음. `TripleSigma.mq5`가 참조하는 runtime patch INI도 없음. | Critical | release/rollback을 ZIP 기준으로 재현할 수 없음 | RC/rollback manifests, patch input retention, hash verification, runbooks 추가 | FAIL |

요약 판정은 다음과 같습니다. parser pipeline과 master table builders는 "코드 존재" 수준에서는 긍정적이지만, promotion-grade evidence/contract가 없어 둘 다 PROVISIONAL입니다. 나머지 네 항목은 필수 산출물 부재로 FAIL입니다.

---

## 4. WF0–WF9 / CP0–CP8 Integrity Review

### WF0 — Data freeze

**목적**: optimization / benchmark / OOS / stress window를 role-locked freeze로 고정하는 것.

**현재 상태 / gate quality / 측정 가능성**: `design/US100_RealTick_Backtest_Data_Policy.md`는 존재하지만 freeze manifest가 없으므로 gate는 의미는 있으나 현재 ZIP에서는 형식적입니다. pass/fail을 기계적으로 측정할 수 없습니다.

**Severity**: High

**Evidence**: `design/US100_RealTick_Backtest_Data_Policy.md:53-168`; missing `_coord/artifacts/us100_history_quality/`; missing `_coord/BACKTEST_BASELINE.md`; missing `data_freeze_manifest.yaml`.

**Impact**: window drift 및 overlap 리스크가 통제되지 않습니다.

**Remediation**: overlap audit와 hash를 포함한 `data_freeze_manifest.yaml` 생성.

**판정**: FAIL

### WF1 — Control-pack selection

**목적**: runtime-integrity control과 profitability control을 명시적으로 분리하는 것.

**현재 상태 / gate quality / 측정 가능성**: Step15 export evidence와 Step16 smoke artifacts는 있으나 registry가 없어 gate는 부분적으로만 의미 있습니다. pass/fail을 완전 측정할 수 없습니다.

**Severity**: High

**Evidence**: `_coord/artifacts/step15_export_q1_out/export_validation_report.json`; `_coord/artifacts/step15_export_q1_out/export_manifest.json`; missing `_coord/ops/control_pack_registry.yaml`.

**Impact**: wrong baseline optimization 리스크가 큽니다.

**Remediation**: role-separated pack registry, pack hashes, parity pointers 추가.

**판정**: FAIL

### WF2 — Backtest execution

**목적**: fixed manifest 하에서 reproducible raw tester outputs를 생성하는 것.

**현재 상태 / gate quality / 측정 가능성**: `tools/run_step21_matrix.ps1`는 존재하지만 `_coord/tester/step21/*.ini`, `_coord/logs/smoke`, `_coord/artifacts/step21_*`가 ZIP에 없고 local Windows path가 하드코딩되어 있습니다. 의미 있는 gate였더라도 ZIP에서는 재현 불가입니다.

**Severity**: Critical

**Evidence**: `tools/run_step21_matrix.ps1:3-8, 59-144`; missing `_coord/tester`; missing `_coord/logs`; missing `_coord/artifacts/step21_*`.

**Impact**: Step21 regression result를 독립적으로 재실행할 수 없습니다.

**Remediation**: manifest-driven runner + preset retention + raw output retention + portable path resolution.

**판정**: FAIL

### WF3 — Parsing & analytics

**목적**: raw outputs를 master tables와 KPI summaries로 materialize 하는 것.

**현재 상태 / gate quality / 측정 가능성**: 관련 scripts는 존재하고 syntax는 clean입니다. 그러나 Step21 raw sample이 ZIP에 없고, contract file이 없으며, coverage/integrity gate가 hard fail이 아닙니다. exploratory gate로는 의미가 있으나 promotion gate로는 부족합니다.

**Severity**: High

**Evidence**: `tools/parse_step21_run.py`, `tools/build_master_tables.py`, `tools/build_counterfactual_eval.py`, `tools/build_daily_risk_metrics.py`; missing `_coord/ops/MASTER_TABLE_CONTRACT.md`; `build_counterfactual_eval.py:197-198, 290-295`; `build_daily_risk_metrics.py:156`.

**Impact**: parser가 "성공"해도 coverage hole이나 cost-blind KPI가 남을 수 있습니다.

**Remediation**: contract, golden replay, coverage manifest, net-of-cost metrics, Step21 tail mandatory validation 추가.

**판정**: PROVISIONAL

### WF4 — Branch decision

**목적**: parsed analytics를 근거로 ML-first / EA-first / runtime-fix-first를 선택하는 것.

**현재 상태 / gate quality / 측정 가능성**: branch decision artifact는 없습니다. 다만 existing ML artifacts만 보면 Stage1 challenger 부재, Stage2 winner 존재이므로 ML-first가 가장 유력합니다. 이것은 ZIP 기반 추론이지 실제 WF4 산출물이 아닙니다.

**Severity**: High

**Evidence**: `_coord/artifacts/step14_validation_q1_out/stage1_selection_report.json` (`eligible_candidate_count=0`, `used_control_fallback=true`); `_coord/artifacts/step14_validation_q1_out/stage2_selection_report.json` (`provisional_winner_candidate_id=stage2_c02`).

**Impact**: 현재 브랜치 선택은 체계적 gate가 아니라 analyst judgment에 의존합니다.

**Remediation**: `branch_decision_note.md`와 branch-open criteria를 manifest로 남겨야 합니다.

**판정**: FAIL

### WF5 — Branch optimization

**목적**: ML 또는 EA layer를 branch-specific objective로 개선하는 것.

**현재 상태 / gate quality / 측정 가능성**: design intent는 있으나 campaign scaffold와 retry governance가 없습니다. 한편 runtime code는 `PositionClose`/`PositionModify` 이후 `ResultRetcode()`를 확인하고 `OnTradeTransaction()` 기반 reconcile path를 유지하고 있어 execution semantics는 올바른 방향입니다. MQL5 문서도 `PositionClose`/`PositionModify`의 true return이 실제 execution success를 의미하지 않으며, `ResultRetcode()` 확인이 필요하다고 명시합니다. 또 `OnTradeTransaction()`의 request/result는 `TRADE_TRANSACTION_REQUEST`에서만 의미 있고, 하나의 trade event에 여러 transaction이 대응될 수 있습니다. [출처: MQL5 docs]

**Severity**: High

**Evidence**: `src/include/TS_Execution.mqh:2330-2351, 2542-2588, 2655-2711`.

**Impact**: self-certifying optimization으로 흐르면 runtime integrity를 깨뜨릴 수 있습니다.

**Remediation**: writer/operator/validator 분리, branch budgets, layer-specific acceptance gates 도입.

**판정**: FAIL

### WF6 — Benchmark / OOS / stress restage

**목적**: incumbent 소수 집합을 benchmark/OOS/stress에서 재검증하는 것.

**현재 상태 / gate quality / 측정 가능성**: data policy는 있으나 campaign hierarchy와 rerun outputs가 없습니다. 현재 ZIP 산출물만으로 측정 불가입니다.

**Severity**: High

**Evidence**: `design/US100_RealTick_Backtest_Data_Policy.md`; missing `_coord/campaigns`, benchmark/oos/stress outputs.

**Impact**: in-sample improvement가 true robustness로 오인될 수 있습니다.

**Remediation**: campaign hierarchy와 restage manifests 추가.

**판정**: FAIL

### WF7 — Limited joint sweep

**목적**: stable incumbent에 대해서만 작은 interaction matrix를 보는 것.

**현재 상태 / gate quality / 측정 가능성**: 구현이나 evidence 없음.

**Severity**: Medium

**Evidence**: 관련 runner/outputs 부재.

**Impact**: 현재 joint optimization은 추적 불가능합니다.

**Remediation**: branch-specific 후보가 안정화된 뒤에만 manifest-driven mini-matrix 허용.

**판정**: FAIL

### WF8 — Release candidate

**목적**: selected pack, params, KPI snapshot, runbook, hashes를 포함한 RC bundle 생성.

**현재 상태 / gate quality / 측정 가능성**: release namespace, runbook, patch inputs, bundle manifest가 없습니다. pass/fail 측정 불가.

**Severity**: Critical

**Evidence**: missing `_coord/releases`; missing `_coord/ops/SELECTION_RELEASE_RUNBOOK.md`; missing `triple_sigma_runtime_patch/`.

**Impact**: 승격 대상이 reproducible artifact가 아니라 ad hoc workspace state가 됩니다.

**Remediation**: RC manifest, pack hash, runtime patch inputs, operator handoff bundle 추가.

**판정**: FAIL

### WF9 — Rollback point

**목적**: 이전 stable state의 full rollback bundle 생성.

**현재 상태 / gate quality / 측정 가능성**: rollback namespace, standard, patch retention 모두 없습니다.

**Severity**: Critical

**Evidence**: missing `_coord/rollback_points`; missing `_coord/ops/ROLLBACK_POINT_STANDARD.md`; `TripleSigma.mq5:51-52`.

**Impact**: runtime reload rollback claims은 있어도 production rollback standard는 없습니다.

**Remediation**: rollback manifest, patch hash, full bundle retention, restore proof 추가.

**판정**: FAIL

---

### CP0 — Build + schema integrity

**목적**: compile clean과 Step21 schema consistency를 hard gate로 두는 것.

**현재 상태 / gate quality / 측정 가능성**: schema 문서는 있으나 compile log가 없어서 ZIP 기준 pass/fail 판정 불가입니다. 의미 있는 gate이지만 현재 ZIP에서는 PROVISIONAL입니다.

**Severity**: High

**Evidence**: `design/BAR_LOG_SCHEMA.md`; missing `_coord/logs/compile/compile_step21_wip.log`.

**Impact**: compile clean claim을 독립 확인할 수 없습니다.

**Remediation**: compile log와 build manifest를 retained evidence로 포함.

**판정**: PROVISIONAL

### CP1 — Runtime invariants

**목적**: duplicate non-modify 0, duplicate EXIT 0, same-timestamp EXIT→ENTRY 0, feature-off core-row match, reload pass 등을 hard gate로 두는 것.

**현재 상태 / gate quality / 측정 가능성**: `tools/package_step21_artifacts.py`는 일부 invariant 계산과 baseline compare를 구현합니다. 그러나 Step21 summaries와 artifact packages가 ZIP에 없어 현재 pass/fail 측정 불가입니다. 의미는 있으나 ZIP 기준으로는 ceremonial입니다.

**Severity**: Critical

**Evidence**: `tools/package_step21_artifacts.py:61-99, 130-155, 188-227`; missing `_coord/artifacts/step21_*`; missing `_coord/logs/smoke/step21_*`.

**Impact**: Step21 closeout claims이 code-independent evidence로 고정되지 않습니다.

**Remediation**: retained summaries + raw artifacts + baseline compare outputs 포함.

**판정**: PROVISIONAL

### CP2 — Data readiness

**목적**: frozen windows와 gap policy documentation을 강제하는 것.

**현재 상태 / gate quality / 측정 가능성**: policy 문서는 있으나 history audit report와 freeze manifest가 없습니다.

**Severity**: High

**Evidence**: `design/US100_RealTick_Backtest_Data_Policy.md`; missing `_coord/artifacts/us100_history_quality/`; missing freeze manifest.

**Impact**: data governance gate가 미완성입니다.

**Remediation**: history audit artifact와 freeze manifest 추가.

**판정**: FAIL

### CP3 — Control-pack readiness

**목적**: runtime control vs profitability control 분리, parity evidence attach.

**현재 상태 / gate quality / 측정 가능성**: Step15 export parity는 검증되지만 registry 부재로 gate 완성도 부족.

**Severity**: High

**Evidence**: `_coord/artifacts/step15_export_q1_out/export_validation_report.json`; missing registry file.

**Impact**: wrong pack selection 리스크.

**Remediation**: dual-control registry 추가.

**판정**: FAIL

### CP4 — Parser readiness

**목적**: master tables 자동 생성과 key/schema sanity를 강제하는 것.

**현재 상태 / gate quality / 측정 가능성**: scripts 존재, syntax clean. 그러나 Step21 tail optional, `tx_authority` 미검증, contract 부재, counterfactual hard gate 부재. 의미는 있으나 promotion-grade는 아닙니다.

**Severity**: Critical

**Evidence**: `tools/parse_step21_run.py:69-82, 92-95, 239-273, 349-352`; `tools/build_counterfactual_eval.py:197-198, 290-295`; missing contract file.

**Impact**: parser success가 integrity success를 보장하지 않습니다.

**Remediation**: contract + coverage manifests + stricter schema enforcement.

**판정**: PROVISIONAL

### CP5 — ML readiness

**목적**: leakage-free split, Stage1/Stage2 selection stability, export parity를 확인하는 것.

**현재 상태 / gate quality / 측정 가능성**: 이 부분은 ZIP 안에서 가장 강합니다. outer split audit, embargo, `no_time_leakage`, Stage1 bottleneck, Stage2 winner, Step15 export acceptance까지 검증 가능합니다. 다만 drift baseline과 recent OOS KPI pack은 없습니다. Time-ordered split과 embargo 유지가 중요하며, scikit-learn `TimeSeriesSplit`도 이를 위해 gap 파라미터를 제공합니다. [출처: scikit-learn docs]

**Severity**: Medium

**Evidence**: `_coord/artifacts/step14_validation_q1_out/validation_metadata.json`; `stage1_selection_report.json`; `stage2_selection_report.json`; `step15_export_q1_out/export_validation_report.json`.

**Impact**: ML branch 개시는 가능하지만 production acceptance까지는 추가 evidence가 필요합니다.

**Remediation**: drift baseline, recent OOS stability table, regime/side breakdown 추가.

**판정**: PROVISIONAL

### CP6 — EA policy readiness

**목적**: gate regret, early-exit tradeoff, protective-modify tradeoff를 측정 가능하게 만드는 것.

**현재 상태 / gate quality / 측정 가능성**: 코드 surface는 있으나 Step21 raw outputs와 retained analytics가 없어 실제 측정 결과는 ZIP에 없습니다.

**Severity**: High

**Evidence**: `TS_Execution.mqh`, `TS_Logger.mqh`, `BAR_LOG_SCHEMA.md`; missing Step21 parser outputs/analytics.

**Impact**: EA policy tuning이 still blind입니다.

**Remediation**: first real-pack campaign run 후 KPI materialization 필요.

**판정**: FAIL

### CP7 — Integrated benchmark/OOS/stress

**목적**: integrated evaluation에서 fatal runtime anomaly 없이 candidate를 검증하는 것.

**현재 상태 / gate quality / 측정 가능성**: 관련 campaign outputs 부재.

**Severity**: High

**Evidence**: benchmark/oos/stress hierarchy 부재.

**Impact**: candidate stability를 전혀 확인하지 못합니다.

**Remediation**: campaign hierarchy와 integrated report 추가.

**판정**: FAIL

### CP8 — RC + rollback

**목적**: reproducible RC와 complete rollback bundle을 강제하는 것.

**현재 상태 / gate quality / 측정 가능성**: 관련 namespace, manifests, patch inputs, runbooks 모두 부재.

**Severity**: Critical

**Evidence**: missing release/rollback dirs and patch files.

**Impact**: promotion과 rollback이 둘 다 operator memory에 의존합니다.

**Remediation**: RC/rollback standards and bundles 추가.

**판정**: FAIL

---

## 5. Gap Matrix

이 절의 **실제 구현 상태**는 ZIP 기준 검증된 사실이고, **리스크**와 **필요 수정 사항**은 판단/권고입니다.

| 항목 | 기대 contract | 실제 구현 상태 | Severity | 리스크 | 필요한 수정 사항 |
|------|-------------|-------------|----------|-------|---------------|
| snapshot authority chain | ZIP 안 문서·파일·산출물이 서로 일관되고 동일 snapshot을 가리켜야 함 | README/closeout/checklist/DOCX/filesystem이 서로 다름. 특히 checklist는 snapshot보다 늦고, 실제 없는 파일을 DONE/PASS 처리함 | Critical | 잘못된 readiness 판단 | snapshot manifest + commit SHA + auto-generated status docs |
| Step21 retained evidence | compile log, tester presets, smoke summaries, step21 artifacts, hashes | 모두 문서에는 언급되지만 ZIP에는 없음 | Critical | runtime claims independent replay 불가 | full retained evidence republish |
| event-to-bar mapping logic | every event maps deterministically to one M5 bar, with exact coverage proof | `floor_to_m5()` fix 존재. 그러나 unmapped events는 warning only | Critical | silent coverage hole 재발 가능 | `coverage_manifest.json`, fail-on-unmapped |
| EXIT / MODIFY / NO_EXIT accounting completeness | reason- and direction-aware exact counts | 모든 EXIT가 EARLY_EXIT로 collapse. NO_EXIT는 heuristic derivation | Critical | policy attribution 왜곡 | exit_reason taxonomy 분리, exact count gate |
| short-side correctness | runtime와 analytics 모두 explicit SHORT lineage 보존 | runtime code는 LONG/SHORT 분기 명확. analytics는 NO_EXIT에서 lineage miss 시 LONG fallback 남음 | High | short-side KPI 왜곡 | default LONG 제거, unresolved direction hard fail |
| parser contract enforcement | Step21 schema v2.0 fields와 tx-authority lineage를 강제 | Step21 tail optional, `tx_authority` 미검증 | High | Step21 핵심 surface 누락 감지 실패 | Step21 mandatory fields 및 authority validation 추가 |
| data governance evidence | policy + history audit + freeze manifest + baseline | policy만 존재, audit artifact와 freeze manifest 없음 | High | window contamination/role drift | history audit retained artifact와 freeze manifest 생성 |
| control-pack segregation | runtime control / profitability control registry | Step15 export evidence는 있으나 formal registry 없음 | High | Step16 smoke pack 오용 가능 | registry + hashes + approval state 추가 |
| release / rollback reproducibility | patch inputs, pack dirs, bundle manifests, rollback proof | patch INI, pack dirs, release/rollback namespaces 모두 없음 | Critical | rollback 불능, RC non-reproducible | RC/rollback bundle standard + retention |
| campaign orchestration | manifest-driven multi-run operation | `run_step21_matrix.ps1`는 smoke-only, local-path bound | High | campaign contamination, rerun 불가 | `run_campaign_matrix.ps1` + campaign manifest |
| checklist-to-code consistency | checklist claims must be reproducible from ZIP | checklist PASS claims 다수가 ZIP과 불일치 | Critical | false readiness signal | checklist auto-generation 및 evidence links 의무화 |
| portfolio metric trustworthiness | net-of-cost PF/expectancy/DD | `net_pnl = gross_pnl` placeholder, true R/DD 부족 | High | acceptance false positive | net cost, slippage, equity DD 추가 |

---

## 6. Multi-Agent Architecture

이 절은 전부 권고 설계입니다. ZIP로 검증된 사실이 아니라, 현재 저장소에 맞춘 실제 운영 topology 제안입니다.

### 권장 topology

```
Human Principal
  → Claude Orchestrator
    → EA Writer
    → ML Writer
    → Parser Writer
    → MT5 Operator
    → Artifact Assembler
    → Machine Validator
    → Codex Independent Reviewer
    → Release Gatekeeper
```

핵심 원칙은 하나입니다. **writer는 자기 산출물을 self-certify할 수 없어야 합니다.**

**Claude Orchestrator**는 branch opening, task routing, manifest assembly만 담당합니다. 전략 코드 수정 권한은 있되, `accepted`, `pass`, `promoted`, `rollback_ready` 같은 final state field는 쓸 수 없어야 합니다.

**EA Writer**는 `src/ea/`, `src/include/`만 수정합니다. 특히 `TS_Execution.mqh`, `TS_Logger.mqh`, `TS_Decision.mqh` 같은 runtime-critical file을 다룰 때는 tx-authority, pending-state, retcode, reconcile logic을 변경할 수 있지만, compile/backtest 실행이나 승격 판정은 할 수 없어야 합니다.

**ML Writer**는 `src/ml/` 및 export tooling만 수정합니다. Stage1/Stage2 retrain, ONNX re-export, pack rebuild를 담당하지만, OOS acceptance와 release candidate 승격은 할 수 없습니다.

**Parser Writer**는 `tools/parse_step21_run.py`, `build_master_tables.py`, `build_counterfactual_eval.py`, `build_daily_risk_metrics.py`, 계약 문서만 수정합니다. 이 agent는 raw run을 promotion-grade evidence로 바꾸는 역할이므로, 특히 self-certification 금지가 중요합니다.

**MT5 Operator**는 코드 수정 권한이 없어야 합니다. compile, tester run, raw output capture만 수행합니다. 이 분리는 MQL5 execution semantics 때문에 필수입니다. `PositionClose`/`PositionModify`는 true return만으로 execution success가 보장되지 않고 `ResultRetcode()` 확인이 필요하며, `OnTradeTransaction()`도 request/result를 transaction type에 따라 다르게 해석해야 하기 때문입니다. [출처: MQL5 docs]

**Artifact Assembler**는 raw outputs를 immutable campaign namespace에 정리하고, hash/manifest를 생성합니다. 수정이 아니라 copy-and-freeze만 해야 합니다.

**Machine Validator**는 schema, coverage, integrity, KPI gates를 계산합니다. `parse_manifest.json`, `coverage_manifest.json`, `kpi_snapshot.json`, `rc_manifest.json`, `rollback_manifest.json`의 `*_pass` field는 이 validator만 기록해야 합니다.

**Codex Independent Reviewer**는 separate context에서 code diff와 retained artifacts를 읽고, `codex_validation.md`를 생성합니다. 동일 branch에 직접 patch를 쓰지 않는 read-mostly reviewer 모드가 바람직합니다. independent review는 machine gate를 대체하지 않고, machine gate와 병렬로 동작해야 합니다.

**Release Gatekeeper**는 writer가 아닙니다. RC bundle, rollback bundle, operator handoff pack을 만들고, machine validator + Codex review + human sign-off가 모두 통과한 뒤에만 승격 flag를 작성합니다.

### 권장 custom skills

여섯 개면 충분합니다:
1. `step21-runtime-integrity-audit`
2. `step21-parser-contract-audit`
3. `step21-counterfactual-coverage-audit`
4. `step21-control-pack-audit`
5. `step21-release-bundle-audit`
6. `step21-rollback-bundle-audit`

여기에 `mql5-tx-authority-review`와 `oos-stability-gate`를 추가하면 충분히 운영 가능합니다.

### 권장 hooks

다섯 개입니다:

1. **pre-change**: path-based routing과 forbidden area enforcement를 수행합니다.
2. **post-change**: `py_compile`, static grep, contract drift detection을 수행합니다.
3. **pre-backtest**: data freeze, control pack registry, runtime patch inputs, pack hash를 확인합니다.
4. **post-backtest**: raw artifact freeze → parser → master tables → coverage manifest → KPI snapshot을 자동 실행합니다.
5. **pre-promotion**: independent review presence, RC bundle completeness, rollback bundle completeness를 검사합니다.

### 권장 MCP integration points

- git/filesystem
- MT5 terminal/tester
- python + duckdb
- onnxruntime/checker
- artifact hash registry

HPO를 붙일 때는 Optuna를 선택할 수 있습니다. define-by-run API와 sampler/pruner 조합이 branch-specific search orchestration에 적합하며, discrete EA sweep에는 `GridSampler`, ML search에는 `TPE + MedianPruner` 조합이 실용적입니다. [출처: optuna.readthedocs.io]

### Artifact retention strategy

- `raw_tester_outputs/`는 immutable
- `parser_outputs/`는 parser version + git SHA stamped
- `analytics/`는 KPI schema version stamped
- validator reports는 immutable markdown/json
- RC/rollback bundles는 hash-locked immutable artifact

### Escalation path

- writer fail 1회는 같은 writer에게 반환
- 2회 연속 fail이면 Machine Validator + Codex joint review
- runtime integrity fail 또는 release/rollback fail이면 즉시 Human Principal escalation
- threshold 변경은 언제나 human approval로 고정

---

## 7. Closed-Loop Optimization Design

이 절도 권고 설계입니다. 현재 ZIP에는 이 loop를 완성하는 scaffold가 없습니다.

### 권장 closed loop

```
Campaign Init
  → Candidate Generator
  → MT5 Backtest Execution
  → Raw Artifact Freeze
  → Parser / Master Build
  → Coverage / Integrity Gate
  → KPI Evaluation
  → Decision Gate
    → if KPI fail: ML retrain/export or EA retune
    → Pack rebuild
    → Retest
  → Benchmark/OOS/Stress Restage
  → Convergence Gate
  → WF8 RC Packaging
  → Release Gatekeeper
```

### Decision Gate

세 갈래만 허용해야 합니다: `RUNTIME_FIX_FIRST`, `ML_FIRST`, `EA_FIRST`. 동시에 여러 primary branch를 열지 않아야 attribution이 보존됩니다.

### Coverage / integrity gates

아래처럼 exact-count 기반이어야 합니다:

- **G0. Raw completeness**: `trade_log.csv`, `bar_log_*.csv`, `exec_state.ini`, `tester_log_tail.txt` 필수. reload path에서는 `broker_audit.csv` 필수.
- **G1. Parse pass**: schema, `trade_id` format, log version consistency.
- **G2. Event coverage**: raw ENTRY/EXIT/MODIFY counts와 mapped counts exact match. EXIT/MODIFY unmapped는 0.
- **G3. NO_EXIT lineage**: every NO_EXIT row must have resolved direction and source lineage.
- **G4. Runtime invariants**: duplicate non-modify 0, duplicate EXIT 0, same-timestamp EXIT→ENTRY 0, close-before-modify violations 0.
- **G5. Pack lineage**: `active_model_pack_dir`, `pack_dir_at_entry`, `runtime_reload_status` consistency.
- **G6. Independent validation**: machine validator pass + Codex review present.

이 중 G2와 G3는 지금 ZIP에서 가장 부족한 부분입니다. `build_counterfactual_eval.py`의 현 상태로는 G2/G3를 enforceable gate로 볼 수 없습니다.

### Branch routing

- Stage1 challenger가 없으면 `ML_FIRST`로 시작합니다.
- Stage2 winner는 이미 있으므로 Stage1 data/threshold/calibration을 먼저 손대고, 그 다음 Stage2를 미세조정합니다.
- `EA_FIRST`는 ML signal layer가 안정적일 때만 허용합니다.
- runtime anomaly가 하나라도 나오면 무조건 `RUNTIME_FIX_FIRST`로 돌아갑니다.

### Retry budget

| 경로 | 최대 retry budget | 초과 시 조치 |
|------|-----------------|------------|
| 동일 raw run 재패키징/재파싱 | 1 | parser bug branch로 escalation |
| runtime-fix code iteration | 2 | human review |
| Stage1 retrain/export cycle | 3 | branch close 또는 data rethink |
| Stage2 retune/export cycle | 3 | Stage1 stability 재검토 |
| EA gates/exit/modify tuning cycle | 2 | ML-first로 복귀 |
| pack rebuild/parity cycle | 2 | release hold |
| limited joint sweep | 1 mini-matrix | fragile interaction 발견 시 즉시 종료 |

### Divergence detection

수치 기반이어야 합니다:
- OOS PF가 benchmark 개선과 반대로 급락
- OOS expectancy retention이 benchmark 대비 60% 미만
- regime dispersion이 widening
- HHI가 급상승
- short-side share가 붕괴
- independent reviewer와 machine gate 결과가 불일치

### Rollback trigger

release 후뿐 아니라 optimization 중에도 존재해야 합니다. duplicate/phantom EXIT, unmapped EXIT/MODIFY, active pack hash mismatch, runtime patch mismatch, or unexpected pack switch가 나오면 즉시 rollback candidate 생성과 branch freeze를 걸어야 합니다.

### Audit trail

최소한 다음 아티팩트를 남겨야 합니다:
- `campaign_manifest.yaml`
- `raw_receipt.json`
- `parse_manifest.json`
- `coverage_manifest.json`
- `kpi_snapshot.json`
- `decision_gate.json`
- `codex_validation.md`
- `rc_manifest.json`
- `rollback_manifest.json`

### Human override points

네 군데면 충분합니다:
1. window freeze 변경
2. acceptance threshold 변경
3. RC promotion 승인
4. rollback execution 승인

### Kill-switch conditions

비타협적으로 두어야 합니다. 다음 중 하나라도 있으면 optimization 또는 release는 즉시 중단:
- compile fail
- schema fail
- coverage mismatch
- duplicate EXIT
- same-timestamp EXIT→ENTRY
- pack hash mismatch
- missing independent validator
- missing rollback bundle

---

## 8. Quantitative Acceptance Criteria

이 절의 숫자는 전부 권고 설계입니다. ZIP로 검증된 사실이 아닙니다. 또한 현재 ZIP의 `daily_risk_metrics.py`는 net-of-cost와 equity-normalized drawdown을 계산하지 않으므로, 아래 hard gate 중 일부는 analytics upgrade 이후에만 기계적으로 enforceable 합니다.

### 기간 기준

| 기준 | 제안 수치 | 왜 이 숫자인가 | Gate |
|------|---------|-------------|------|
| Train 최소 기간 | clean actual-tick 기준 누적 18개월 이상, 가능하면 3개 이상 rolling folds | 6-regime system은 단기 표본에서 regime recurrence가 부족해짐 | Hard |
| Validation 최소 기간 | 누적 6개월 이상 + 72-bar embargo 유지 | threshold/calibration 조정 시 leakage 방지 필요 | Hard |
| Benchmark 최소 기간 | contiguous clean window 9개월 이상 | single best window에서 candidate ranking 안정성 확보 | Hard |
| OOS 최소 기간 | recent OOS 9개월 이상 | 최신 regime transition에 대한 robustness 확인 | Hard |
| Stress 최소 기간 | 24개월 이상 또는 practical outer span 전체 | candidate fragility와 concentration 노출 확인 | Soft for search, Hard for RC |

### 통계 및 성과 기준

| 기준 | 제안 수치 | 왜 중요한가 | Gate |
|------|---------|-----------|------|
| 최소 closed trade 수 | benchmark+OOS 합산 1,200건 이상 | 6-regime × side decomposition을 생각하면 수백 건 수준은 너무 얕음 | Hard |
| OOS closed trade 수 | recent OOS 400건 이상 | OOS 결론의 분산을 낮추기 위함 | Hard |
| regime-level sample | 최소 4개 regime에서 각 75건 이상, 나머지 regime도 40건 이상 | regime-adaptive가 실제로 여러 regime에서 작동하는지 확인 | Hard for 4 regimes, Soft warning for remainders |
| short-side sample | benchmark+OOS 합산 150건 이상, recent OOS 50건 이상 | 본 프로젝트는 short-side bug 이력이 있어 별도 하한이 필요 | Hard |
| PF threshold | benchmark ≥ 1.20, OOS ≥ 1.10 | execution system은 margin of safety가 필요. OOS에서 1.0 근처는 너무 얇음 | Hard |
| expectancy_r | benchmark ≥ 0.10R, OOS ≥ 0.05R | PF만 좋고 trade payoff가 빈약한 경우를 걸러냄 | Hard |
| Sharpe-like proxy | daily net-PnL Sharpe proxy benchmark ≥ 0.75, OOS ≥ 0.50 | non-Gaussian trade series라 hard gate보다는 warning용이 적절 | Soft |
| maximum drawdown | OOS normalized DD ≤ 12%, preferred ≤ 9% | live-grade execution stack이면 DD tolerance가 낮아야 함 | Hard / Soft preferred |
| regime dispersion | n≥60인 regime 중 negative expectancy_r가 2개 초과면 fail | 일부 regime에만 의존하는 adaptive system은 실제론 brittle | Hard |
| regime dispersion spread | n≥60인 regime의 max-min expectancy_r ≤ 0.20R | 지나친 regime dispersion은 classifier 오류 시 큰 손실로 연결 | Soft |
| concentration HHI | full OOS absolute-PnL HHI ≤ 0.15 | 몇 개 trade에 수익이 집중되면 live transferability가 낮음 | Hard |
| monthly concentration HHI | 각 월 HHI ≤ 0.18 | 한 달 단위 winner-take-all 구조 방지 | Soft |
| minimum OOS consistency | 최근 rolling 3-month OOS 4개 중 3개 이상에서 PF>1.0, expectancy_r>0 | one-window fluke를 방지 | Hard |
| benchmark 대비 OOS stability | OOS expectancy_r ≥ benchmark의 60%, OOS PF ≥ benchmark의 85%, OOS DD ≤ benchmark의 125% | regime-adaptive system의 일반화 안정성 확인 | Hard |

이 숫자들이 regime-adaptive 시스템에서 특히 중요한 이유는 단순 aggregate PF가 아니라 regime classifier와 execution policy가 동시에 틀릴 때 손실이 증폭되기 때문입니다. 따라서 dispersion, HHI, OOS stability를 PF와 동급의 hard consideration으로 다루는 것이 맞습니다.

---

## 9. Immediate Remediation Backlog (우선순위 순)

### P0 — Evidence-complete snapshot 재발행

**Severity**: Critical

**Evidence**: Step21 retained logs/tester/artifacts/patch inputs absent.

**Impact**: 현재 ZIP은 runtime claims를 independently certify할 수 없음.

**Remediation**: `_coord/logs`, `_coord/tester/step21`, `_coord/artifacts/step21_*`, `triple_sigma_runtime_patch/` 포함 재발행.

### P0 — STEP21_OPS_CHECKLIST.md 폐기 또는 재생성

**Severity**: Critical

**Evidence**: checklist와 DOCX/filesystem 불일치.

**Impact**: false readiness signal.

**Remediation**: snapshot manifest 기반 auto-generated checklist로 교체.

### P0 — counterfactual coverage gate hardening

**Severity**: Critical

**Evidence**: `build_counterfactual_eval.py` unmapped warning-only, EXIT→EARLY_EXIT collapse, LONG fallback.

**Impact**: prior silent-drop class 재발 가능.

**Remediation**: `coverage_manifest.json`, fail-on-unmapped, exact reason/direction accounting.

### P0 — missing contracts/manifests/runbooks 생성

**Severity**: High

**Evidence**: `MASTER_TABLE_CONTRACT`, `control_pack_registry`, `data_freeze_manifest`, campaign manifest, operator SOP, release/rollback runbooks 전부 부재.

**Impact**: analytics와 operations가 auditable contract 없이 동작.

**Remediation**: 이 파일들을 우선 생성하고 validator write-only fields를 정의.

### P1 — manifest-driven campaign scaffold 구축

**Severity**: High

**Evidence**: `_coord/campaigns` 없음, `run_campaign_matrix.ps1` 없음.

**Impact**: optimization runs가 reproducible campaign unit으로 남지 않음.

**Remediation**: `_coord/campaigns/<id>/raw_tester_outputs/parser_outputs/analytics/...` hierarchy와 runner 추가.

### P1 — release/rollback bundle standard 구현

**Severity**: Critical

**Evidence**: release/rollback namespace와 patch inputs 없음.

**Impact**: RC promotion과 rollback이 workspace state에 의존.

**Remediation**: `rc_manifest.json`, `rollback_manifest.json`, pack hash, patch hash, restore proof 추가.

### P1 — independent validator lane 구현

**Severity**: High

**Evidence**: current repo에는 self-certification 차단 구조가 없음.

**Impact**: writer가 자기 산출물을 pass시킬 수 있음.

**Remediation**: Machine Validator + Codex read-only review + Gatekeeper write restriction 도입.

### P1 — parser strictness 상향

**Severity**: High

**Evidence**: Step21 tail optional, `tx_authority` 미검증, net-of-cost 부재.

**Impact**: Step21 analytics의 신뢰도 저하.

**Remediation**: schema strict mode, authority validation, cost-aware metrics, true drawdown metrics 추가.

### P2 — hard-coded local path 제거

**Severity**: High

**Evidence**: `run_step21_matrix.ps1`, `analyze_us100_history_quality.py` local Windows path 고정.

**Impact**: CI/agent portability 저하.

**Remediation**: env/manifest-driven path resolution으로 교체.

### P2 — first real-pack single run 실행 후 WF4 결정

**Severity**: High

**Evidence**: branch decision artifact 없음.

**Impact**: ML-first/EA-first 우선순위가 문서 추론에 머뭄.

**Remediation**: Step15 profitability control pack 기준 single run → parser → KPI → branch decision note 생성.

---

## 10. ZIP만으로는 검증 불가능한 항목

다음 항목은 PASS로 둘 수 없습니다. 모두 검증 불가입니다.

1. **0 errors, 0 warnings compile claim.** compile log가 ZIP에 없습니다.
2. **10개 Step21 tester preset pass claim.** `_coord/tester/step21/*.ini`와 `_coord/logs/smoke/step21_*_summary.md`가 없습니다.
3. **feature-off core-row alignment true claim.** step21 artifact packages와 baseline compare outputs가 없습니다.
4. **duplicate non-modify 0 / duplicate EXIT 0 / same-timestamp EXIT→ENTRY 0의 Step21 runtime 결과.** summary artifacts가 없습니다.
5. **trailing/TP reshape/time policy/pending modify recovery의 actual MODIFY counts.** step21 retained raw outputs가 없습니다.
6. **runtime reload success / rollback pass claim.** patch inputs와 retained step21 reload artifacts가 없습니다.
7. **history-quality audit completion claim.** `_coord/artifacts/us100_history_quality/` report가 없습니다.
8. **checklist에 적힌 parser pipeline test result (`step21_live_trailing_probe`)와 EXIT coverage 100% claim.** 해당 raw run이 ZIP에 없습니다.
9. **real broker-connected execution behavior.** README와 closeout 문서도 미실행이라고 적습니다.
10. **RC reproducibility와 rollback completeness.** 관련 bundle 자체가 없습니다.

---

## 최종 판정

이 ZIP은 "runtime/ML codebase audit용 snapshot"으로는 가치가 있지만, "optimization 승격 직전 운영 체계"로는 아직 부족합니다. 현재 시점에서 가장 먼저 해야 할 일은 새 기능 추가가 아니라, **거짓 양성 PASS를 제거하고 evidence/contract/gate layer를 실제 파일로 복원하는 것**입니다.
