# GPT Pro De Novo Audit Report — 2026-03-12

아래 평가는 현재 GitHub repo head의 tree/raw file을 직접 대조한 de novo audit 결과입니다. 이 세션에는 전용 GitHub connector API가 노출되지 않아, mounted filesystem 검색 대신 GitHub repo tree/raw endpoints를 기준으로 검증했으며, 문서-only 항목은 PASS로 승격하지 않았습니다.

---

## 1. Executive Summary

결론부터 말씀드리면, 현재 head는 "Step21 runtime 구현 + pre-optimization governance scaffold"까지는 올라와 있지만, admissible optimization baseline, promotion bundle, rollback bundle, independent gatekeeper까지 닫힌 상태는 아닙니다.

즉, 현재 repo의 **pre-optimization readiness는 PROVISIONAL**, **promotion readiness는 FAIL**로 보는 것이 가장 정확합니다.

실제로 root에는 src, tools, _coord, TRIPLE-SIGMA, Step21 closeout/checklist 문서가 존재하고, _coord 아래에는 artifacts, campaigns, logs, ops, tester가 모두 있으며, Step21 compile log와 tester presets, retained artifacts도 현재 repo에서 확인됩니다. 다만 optimization entry point로 써야 할 current campaign evidence chain이 끊겨 있습니다.

manifest.yaml과 runbook은 WF2 산출물을 raw_tester_outputs/에 immutably 보존하라고 요구하지만, 실제 campaign tree에는 freeze/, parser_outputs/, manifest.yaml만 보이고, parse_manifest.json의 raw_dir는 campaign-native raw가 아니라 `_coord\artifacts\step21_live_trailing_probe`를 가리킵니다. 따라서 현재 parser_outputs/는 "retained artifact replay"로는 유효하지만, "optimization baseline"으로는 admissible하지 않습니다.

추가로, release/rollback은 runbook 수준에서는 잘 정의되어 있으나 실제 `_coord/releases/<rc_id>/`와 `_coord/rollback_points/<rb_id>/` evidence bundle은 현재 repo tree에서 검증되지 않았고, EA는 triple_sigma_runtime_patch와 외부 MQL5/Files pack들을 참조하지만 해당 payload 자체의 repo-retained hash bundle은 확인되지 않았습니다.

즉, "작성·실행·검증·승격"의 폐루프 중 앞단 코드는 있으나, promotion/rollback reproducibility와 independent validation path가 아직 비어 있습니다.

따라서 **immediate next executable phase는 broad optimization이 아니라, campaign-native benchmark diagnostic run → admission hardening**이어야 합니다. 구체적으로는 triple_sigma_pack_step15_q1를 사용한 benchmark single-run을 campaign workspace 안에서 재생성하고, raw/hash/pack/preset manifests를 고정한 뒤 strict validator를 통과시켜 baseline을 만든 다음, 그 결과로 ML-first vs EA-first를 결정해야 합니다.

현재 registry와 selection evidence만 보면 Stage1은 eligible_candidate_count=0인 bottleneck이고 Stage2는 stage2_c02라는 viable incumbent가 있으므로, 기본 prior는 ML-first이지만 이는 benchmark evidence packet으로 다시 확정되어야 합니다.

---

## 2. Current Repo State Assessment

**Verified:** 현재 repo root에는 .claude, TRIPLE-SIGMA, _coord, design, src, tools, PROJECT_triple_sigma_Step21_ops_guide_en.docx, STEP21_CLOSEOUT_AND_VERIFICATION.md, STEP21_OPS_CHECKLIST.md가 존재합니다. _coord 아래에는 artifacts, campaigns/C2026Q1_stage1_refresh, logs, ops, tester가 있고, tools에는 parse_step21_run.py, build_master_tables.py, build_counterfactual_eval.py, build_daily_risk_metrics.py, run_step21_matrix.ps1가 있습니다.
- Evidence type: filesystem, code.

**Verified:** Step21 runtime retained evidence는 현재 repo에서 실제로 확인됩니다. `_coord/logs/compile/compile_step21_wip.log`가 존재하고, 로그 본문은 `Result: 0 errors, 0 warnings`를 기록합니다. `_coord/tester/step21/`에는 10개의 Step21 preset이 있고, `_coord/artifacts/`에도 step21_control_trade, step21_live_pass_regression, step21_live_trailing_probe, step21_runtime_reload_success, step21_runtime_reload_rollback 등 retained artifact 디렉토리가 보입니다.
- Evidence type: filesystem, artifact, document.

**Verified:** current campaign workspace는 부분적으로 실체화되어 있습니다. `_coord/campaigns/C2026Q1_stage1_refresh/`에는 manifest.yaml, freeze/data_freeze_manifest.yaml, populated parser_outputs/가 있고, parser_outputs/ 안에는 bars_master.parquet, trades_master.parquet, modify_master.parquet, execution_master.parquet, counterfactual_eval.parquet, daily_risk_metrics.parquet, parse_manifest.json, coverage_manifest.json가 존재합니다.
- Evidence type: filesystem, artifact.

**Verified:** 그러나 same campaign tree page에서는 raw_tester_outputs/, analytics/, benchmark/, oos/, stress/, shortlist/, reports/ 디렉토리가 현재 보이지 않습니다. 반면 manifest.yaml과 `_coord/README.md`는 이들 output directory를 campaign contract의 일부로 명시합니다. 따라서 "campaign scaffold가 모두 생성됨"은 현재 repo 기준으로는 document-level expectation이지 filesystem-confirmed fact가 아닙니다.
- Evidence type: filesystem, document.

**Verified:** data_freeze_manifest.yaml은 optimization folds, benchmark, OOS, stress를 exact minute boundary로 정의하고, role overlap이 모두 false, broad contaminated range가 disallowed임을 명시합니다. control_pack_registry.yaml은 runtime-integrity control과 profitability control을 분리하고, profitability side의 현재 병목을 Stage1 refresh로 명시합니다.
- Evidence type: artifact, document.

**Verified:** release/rollback governance 문서는 존재하지만, 현재 _coord tree에는 `_coord/releases/`나 `_coord/rollback_points/`가 보이지 않고, root tree에는 `triple_sigma_runtime_patch/`도 보이지 않습니다. EA source는 triple_sigma_pack_v1, triple_sigma_pack_step15_q1, triple_sigma_pack_long_step16, triple_sigma_runtime_patch\*.ini를 `#property tester_file`로 참조합니다.
- Evidence type: filesystem, code, document.

**Verified:** `_coord/GPT_PRO_AUDIT_REPORT_2026-03-11.md`는 ZIP snapshot 기준으로 _coord/logs, _coord/tester, _coord/ops, _coord/campaigns 부재를 문제로 삼았지만, 현재 head에는 그 경로들이 존재합니다. 따라서 그 보고서는 current repo state에 대해서는 **STALE**입니다.
- Evidence type: filesystem, document.

**Verified:** STEP21_OPS_CHECKLIST.md 역시 부분적으로 STALE입니다. 해당 문서는 campaign parser_outputs/가 비어 있다고 적고 counterfactual taxonomy를 EARLY_EXIT 중심으로 서술하지만, 현재 repo에는 populated parser_outputs/가 있고 parse_manifest.json은 EXIT_SL, EXIT_FORCE, EXIT_TP까지 기록합니다.
- Evidence type: artifact, document.

**Inferred:** 현재 repo의 가장 정확한 상태 설명은 "runtime code는 구현·retained evidence까지 존재, optimization governance는 절반 이상 scaffolded, 그러나 admissible campaign lineage와 promotion chain은 미완"입니다.

---

## 3. Critical Integrity / Readiness Findings

### Finding 1 — Campaign provenance breach between WF2 and WF3

- **severity: Critical**

**Verified:** manifest.yaml과 OPTIMIZATION_OPERATOR_RUNBOOK.md는 WF2 산출물을 campaign-specific preset + raw_tester_outputs/ immutable copy로 정의하지만, 실제 campaign tree에는 raw_tester_outputs/가 보이지 않고, parse_manifest.json의 raw_dir는 `_coord\artifacts\step21_live_trailing_probe`입니다. 즉, current campaign parser outputs는 campaign-native raw가 아니라 retained step artifact replay입니다.

- Evidence: `_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml`, `_coord/ops/OPTIMIZATION_OPERATOR_RUNBOOK.md`, current campaign tree, parse_manifest.json.
- Evidence type: document, filesystem, artifact.

**Inferred:** 현재 parser_outputs/는 parser stack smoke/validation evidence로는 유효하지만, optimization baseline·benchmark selection·promotion input으로는 admissible하지 않습니다.

- **impact:** 잘못된 window/pack/preset lineage가 baseline으로 고정되어 branch decision, benchmark comparison, shortlist ranking이 모두 오염될 수 있습니다.
- **remediation:** run_campaign_backtest 계열 runner를 추가해 `_coord/campaigns/<campaign_id>/runs/RUN_<ts>/` 아래에 preset_snapshot.ini, run_manifest.json, raw_hash_manifest.json, pack_hash_manifest.json, compile_log.txt를 생성하고, parser admission에서 raw_dir가 동일 campaign run workspace 밖이면 hard fail하도록 바꿔야 합니다.
- **title:** Seal campaign-native WF2 lineage and reject artifact-replay baselines
- **body:** Implement a manifest-driven campaign runner that emits preset snapshot, compile log, raw hash manifest, pack hash manifest, and run manifest under the campaign run workspace. Update parser admission to reject any parse whose raw_dir is outside the campaign run workspace. Acceptance: benchmark diagnostic run on triple_sigma_pack_step15_q1 can be replayed end-to-end from retained evidence.
- **label: P0**

---

### Finding 2 — CP4 false-green: close-before-modify violation is only a warning

- **severity: Critical**

**Verified:** MASTER_TABLE_CONTRACT.md는 "same trade_id, same bar에서 EXIT가 있으면 MODIFY가 없어야 한다"고 적고, build_master_tables.py는 이 overlap을 structural error가 아니라 warning으로만 처리합니다. 현재 parse_manifest.json에도 `modify_master: 4 MODIFY rows share timestamp with EXIT for same trade_id` warning이 남아 있지만 pass=true, master_tables_pass=true로 기록됩니다.

- Evidence type: code, artifact, document.

**Inferred:** CP1/CP4가 현재는 "runtime ambiguity 존재"와 "gate pass"를 동시에 허용하는 구조입니다.

- **impact:** exit/modify ordering ambiguity가 counterfactual exit-opportunity-cost와 modify-alpha-loss를 동시에 왜곡할 수 있고, synthetic negative-path와 real benchmark baseline을 같은 gate로 통과시키는 false-green이 생깁니다.
- **remediation:** campaign baseline, benchmark, OOS, shortlist 후보에서는 close-before-modify overlap을 hard fail로 승격하고, synthetic regression artifact에만 explicit waiver class를 허용해야 합니다.
- **title:** Promote close-before-modify overlap from warning to hard fail for admissible runs
- **body:** Change build_master_tables / validator behavior so same-trade same-timestamp EXIT+MODIFY overlaps fail admissible campaign runs. Preserve a documented waiver class only for dedicated synthetic regression artifacts. Acceptance: benchmark/OOS/selection runs cannot pass with overlap>0.
- **label: P0**

---

### Finding 3 — Counterfactual gate is improved, but contract/checklist drift remains and ENTRY loss is not gated

- **severity: High**

**Verified:** current code has `floor_to_m5()` and exit taxonomy mapping to EXIT_SL, EXIT_TP, EXIT_FORCE, EARLY_EXIT, so event-to-bar mapping과 exit taxonomy는 예전보다 명확해졌습니다. 하지만 MASTER_TABLE_CONTRACT.md는 여전히 decision_type을 GATE_BLOCK / ENTRY / EARLY_EXIT / NO_EXIT / MODIFY로만 적고 있고, build_counterfactual_eval.py의 coverage_pass는 unmapped EXIT, MODIFY, unresolved NO_EXIT만 fail시키며 unmapped ENTRY는 fail 조건에 포함하지 않습니다. STEP21_OPS_CHECKLIST.md도 아직 old EARLY_EXIT taxonomy를 서술합니다.

- Evidence type: code, artifact, document.

**Inferred:** 현재 counterfactual stack은 exploratory analytics에는 충분하지만, promotion-grade gate로 쓰기에는 contract drift와 admission weakness가 남아 있습니다.

- **impact:** ENTRY mapping 누락이 silent warning으로 지나갈 수 있고, 문서/analytics consumer가 decision_type semantics를 잘못 해석할 수 있습니다.
- **remediation:** contract version을 올려 exit subtype domain을 공식화하고, coverage_pass에 unmapped ENTRY도 포함시키거나 최소 threshold/waiver 체계를 도입해야 합니다. checklist는 parse manifest/coverage manifest에서 자동 생성되게 바꾸는 편이 안전합니다.
- **title:** Version counterfactual contract and gate ENTRY coverage
- **body:** Update MASTER_TABLE_CONTRACT.md to include EXIT_SL/EXIT_TP/EXIT_FORCE and revise checklist generation from parse/coverage manifests. Extend coverage gate so unmapped ENTRY is either a hard fail or an explicitly thresholded waiver. Acceptance: contract, parser outputs, and checklist all agree on decision_type taxonomy and coverage semantics.
- **label: P0**

---

### Finding 4 — Release / rollback are document-backed but not instantiated as evidence bundles

- **severity: Critical**

**Verified:** SELECTION_RELEASE_RUNBOOK.md와 ROLLBACK_POINT_STANDARD.md는 RC/RB bundle, hashes, reproducibility rerun, patch-input retention을 요구합니다. 그러나 current _coord tree에는 `_coord/releases/`와 `_coord/rollback_points/`가 보이지 않고, root tree에는 `triple_sigma_runtime_patch/`도 확인되지 않습니다. 동시에 TripleSigma.mq5는 runtime patch INI와 여러 pack을 `#property tester_file`로 참조합니다.

- Evidence type: document, filesystem, code.

**Inferred:** 현재 repo에서는 누구도 reproducible RC handoff나 deterministic rollback을 수행할 수 없습니다.

- **impact:** live-grade release / promotion / rollback이 evidence bundle 없이 사람 기억과 workstation state에 의존하게 됩니다.
- **remediation:** bundle_rc.py와 bundle_rollback.py를 추가해 model pack, preset, runtime patch inputs, KPI snapshot, SHA-256 hashes, reproducibility rerun 결과를 immutable bundle로 생성하도록 해야 합니다.
- **title:** Instantiate RC and rollback bundles with hash-sealed payloads
- **body:** Add RC and rollback bundle builders/validators that package model pack, preset, runtime patch inputs, KPI snapshot, and SHA-256 hashes. Block promotion when bundle generation or reproducibility rerun fails. Acceptance: every RC has a matching rollback point and both validate from retained files only.
- **label: P0**

---

### Finding 5 — Existing orchestration is workstation-bound and not campaign-driven

- **severity: High**

**Verified:** `tools/run_step21_matrix.ps1`는 특정 Windows user path, MT5 terminal path, tester agent log path, source log directory를 하드코딩하고, fixed Step21 presets를 `_coord/artifacts/step21_*`로 패키징합니다. 이는 campaign manifest를 읽어 benchmark/OOS windows를 바꾸는 WF2 runner가 아니라 retained regression packager에 가깝습니다.

- Evidence type: code.

**Inferred:** 현재 스크립트는 agent-driven optimization workflow의 operator layer로 바로 재사용하기 어렵습니다.

- **impact:** host portability, independent replay, CI/MCP integration, Codex cross-validation이 모두 막힙니다.
- **remediation:** runner를 manifest-driven으로 재작성하고, environment-specific path는 operator config로 분리해야 합니다.
- **title:** Replace workstation-bound step21 matrix script with manifest-driven campaign runner
- **body:** Refactor run_step21_matrix.ps1 into a parameterized campaign runner that reads manifest window aliases, pack IDs, and output roots from config rather than hardcoded workstation paths. Acceptance: the same command can run on a second host without path edits and writes a normalized run manifest.
- **label: P1**

---

### Finding 6 — No mechanized independent validator / gatekeeper path was verified

- **severity: Critical**

**Verified:** runbook는 CP0–CP8와 stop conditions를 잘 정의하지만, current root tree에는 .github workflow나 별도 gatekeeper implementation이 검증되지 않았고, repo에서 확인된 것은 narrative docs/runbooks와 수동 artifact들입니다. 즉, "writer와 validator 분리"는 principle로는 존재하지만 mechanized operating path는 현재 repo에서 확인되지 않습니다.

- Evidence type: filesystem, document.

**Inferred:** 지금 구조에서는 작성 에이전트가 자기 산출물을 자기 문서로 정당화할 여지가 남아 있습니다.

- **impact:** promotion gate가 social process가 되며, auditability와 failure containment가 급격히 약해집니다.
- **remediation:** Codex 또는 동급 validator를 frozen evidence bundle만 읽는 별도 thread/agent로 두고, release gatekeeper는 writer와 분리된 read-only role로 강제해야 합니다.
- **title:** Add independent validator and release gatekeeper with dual-signature policy
- **body:** Create a read-only validator workflow that reruns integrity checks on frozen evidence bundles and produces validator_report.json. Release gatekeeper must reject promotion unless writer and validator manifests agree. Acceptance: no writer agent can self-approve WF8/WF9.
- **label: P0**

---

### Finding 7 — KPI semantics are ambiguous and short-side evidence is statistically too thin

- **severity: High**

**Verified:** current parse_manifest.json은 total_pnl=-44.45인데 avg_profit_factor=1.853...를 동시에 기록합니다. build_daily_risk_metrics.py를 보면 이 값은 global trade-level PF가 아니라 "daily PF 평균"입니다. 동시에 coverage_manifest.json의 direction distribution은 LONG=5346, SHORT=61로 극단적으로 long-dominant합니다.

- Evidence type: artifact, code.

**Inferred:** 현재 KPI surface만으로는 profitability quality를 과대평가할 수 있고, short-side correctness/performance는 release-grade로 주장하기 어렵습니다.

- **impact:** PF/expectancy gate가 잘못 정의되면 benchmark/OOS selection이 오판될 수 있고, regime-adaptive two-sided system이 사실상 long-only처럼 운영될 위험이 있습니다.
- **remediation:** global_trade_profit_factor, combined_window_profit_factor, avg_daily_profit_factor를 분리하고, short-side minimum trade/decision coverage gate를 추가해야 합니다.
- **title:** Separate global PF from daily-average PF and enforce short-side sufficiency
- **body:** Add true trade-level PF / expectancy outputs and rename current daily-average metrics. Introduce minimum short-side coverage/trade thresholds or explicit waiver semantics for long-dominant candidates. Acceptance: promotion reports distinguish aggregate PF from daily-average PF and flag insufficient short-side evidence.
- **label: P1**

---

### 추가 mandatory checks 요약

**Verified:** build_counterfactual_eval.py의 `floor_to_m5()`와 current coverage_manifest.json 덕분에 현재 replay sample에서는 unmapped event가 0이고 NO_EXIT unresolved도 0입니다. parse_step21_run.py는 tx_authority, trade_id regex, Step21 tail columns를 검사합니다. build_daily_risk_metrics.py는 pnl이 broker DEAL_COMMISSION을 이미 포함한다고 명시하고, current parse manifest의 cost model도 이를 반영합니다. 다만 short-side evidence는 매우 얇고, independent validation path는 mechanized state로는 확인되지 않았습니다.

src/include/TS_Execution.mqh local raw inspection에서도 DEAL_PROFIT + DEAL_SWAP + DEAL_COMMISSION 합산이 확인되어, 사용자가 제공한 commission 설명과 repo code는 일치합니다.

---

## 4. Pre-Optimization Readiness Audit

### parser pipeline

| 항목 | 값 |
|------|-----|
| 구현 상태 | IMPLEMENTED |
| readiness 판정 | PROVISIONAL |
| blocker 여부 | Yes |

**Verified:** tools/parse_step21_run.py, build_counterfactual_eval.py, build_daily_risk_metrics.py가 존재하고, current campaign parser_outputs/에는 parse_manifest.json, coverage_manifest.json, master tables, counterfactual_eval.parquet, daily_risk_metrics.parquet가 실제로 생성되어 있습니다.
- Evidence type: code, artifact, filesystem.

**Inferred:** parser 자체는 실체가 있으나, current campaign 산출물의 provenance가 retained artifact replay라서 optimization baseline gate로는 아직 불충분합니다.

- 주요 리스크: external raw_dir, unmapped ENTRY non-fatal, warning-only close-before-modify.
- 필요한 수정 사항: campaign-native raw lineage 강제, strict CP4 validator 분리, KPI semantics 정리.

---

### master table builders

| 항목 | 값 |
|------|-----|
| 구현 상태 | IMPLEMENTED |
| readiness 판정 | PROVISIONAL |
| blocker 여부 | Yes |

**Verified:** tools/build_master_tables.py는 trades_master, bars_master, modify_master, execution_master, optional audit_master를 생성하고, contract 문서도 존재합니다. current campaign에는 해당 parquet outputs가 실제로 있습니다.
- Evidence type: code, artifact, document.

**Inferred:** ledger 구조는 usable하지만, contract enforcement가 ops intent보다 느슨합니다.

- 주요 리스크: close-before-modify가 non-blocking, current campaign audit_master=0이라 broker audit completeness를 baseline에서 확인하지 못함.
- 필요한 수정 사항: admissible run에서는 overlap hard fail, audit-enabled shadow window 최소 1개 의무화.

---

### data freeze manifest

| 항목 | 값 |
|------|-----|
| 구현 상태 | IMPLEMENTED |
| readiness 판정 | PASS |
| blocker 여부 | No |

**Verified:** freeze/data_freeze_manifest.yaml가 exact minute windows, role overlap false, broad contaminated range prohibition, OOS known gap까지 명시하고 있습니다.
- Evidence type: artifact.

**Inferred:** 현재 repo에서 가장 강한 pre-optimization contract 중 하나입니다.

- 주요 리스크: source policy hash와 freeze hash가 별도로 seal되어 있지 않음.
- 필요한 수정 사항: freeze_hash_manifest.json 추가, source document commit/hash 고정.

---

### control pack registry

| 항목 | 값 |
|------|-----|
| 구현 상태 | IMPLEMENTED |
| readiness 판정 | PROVISIONAL |
| blocker 여부 | Yes (autonomous reproducibility 기준) |

**Verified:** control_pack_registry.yaml는 runtime-integrity control과 profitability control을 분리하고, step15 export/step14 selection evidence를 연결합니다. Stage1 bottleneck과 Stage2 incumbent도 registry와 selection reports에서 일치합니다.
- Evidence type: document, artifact.

**Inferred:** governance contract는 적절하지만, 실제 MQL5/Files/* payload contents/hash는 repo에서 독립 검증되지 않았습니다.

- 주요 리스크: external pack drift, unsealed ONNX payload.
- 필요한 수정 사항: pack_hash_manifest.json, ONNX shape/hash validator, pack payload snapshot retention.

---

### campaign scaffold

| 항목 | 값 |
|------|-----|
| 구현 상태 | SCAFFOLD |
| readiness 판정 | PROVISIONAL |
| blocker 여부 | Yes |

**Verified:** campaign manifest, freeze manifest, populated parser outputs는 존재합니다. 그러나 actual campaign tree에는 raw_tester_outputs/, benchmark/, oos/, stress/, shortlist/, reports/가 확인되지 않고, current parser outputs는 retained artifact replay입니다.
- Evidence type: filesystem, artifact, document.

**Inferred:** campaign는 "형식적 구조 + 일부 replay output" 상태이며, 아직 end-to-end WF2→WF7 workspace가 아닙니다.

- 주요 리스크: branch decision가 non-admissible evidence에 기대게 됨.
- 필요한 수정 사항: campaign run workspace, benchmark/oos/stress subtrees 실체화, run manifests 추가.

---

### release / rollback scaffold

| 항목 | 값 |
|------|-----|
| 구현 상태 | SCAFFOLD |
| readiness 판정 | FAIL |
| blocker 여부 | Yes |

**Verified:** release/rollback runbooks는 존재하지만, actual RC/RB bundle은 current repo tree에서 검증되지 않았고, runtime patch payload directory도 확인되지 않습니다.
- Evidence type: document, filesystem, code.

**Inferred:** 현재 상태로는 release approval과 rollback rehearsal 모두 evidence-complete하게 수행할 수 없습니다.

- 주요 리스크: 승격 후 실패 시 deterministic rollback 불가.
- 필요한 수정 사항: RC/RB bundler, hash verifier, reproducibility rerun, patch-input capture.

---

## 5. WF0–WF9 / CP0–CP8 Integrity Review

### WF0

- 원래 목적: data windows와 gap policy를 freeze하고 role overlap을 제거하는 것입니다.
- 현재 구현 상태: **IMPLEMENTED**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 가능
- 누락된 증거: source policy hash, history-quality snapshot hash
- enforceable gate 보완: freeze hash + source commit binding 추가.

### WF1

- 원래 목적: runtime-integrity control과 profitability control을 분리하는 것입니다.
- 현재 구현 상태: **IMPLEMENTED**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 부분 가능
- 누락된 증거: actual pack payload hash / MQL5 pack snapshot
- enforceable gate 보완: pack hash manifest + parity recheck + environment fingerprint.

### WF2

- 원래 목적: campaign-specific preset으로 실제 benchmark/OOS/stress run의 raw outputs를 생성하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 매우 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: campaign preset snapshot, raw outputs, compile log bound to campaign, raw hash manifest
- enforceable gate 보완: manifest-driven runner와 immutable runs/RUN_<ts>/raw/ retention. run_step21_matrix.ps1는 이 역할을 대신하지 못합니다.

### WF3

- 원래 목적: raw outputs를 parser/master/counterfactual/daily risk stack으로 materialize하는 것입니다.
- 현재 구현 상태: **IMPLEMENTED**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 부분 가능
- 누락된 증거: campaign-native provenance, stricter hard-fail semantics
- enforceable gate 보완: parser admission에서 provenance check, coverage ENTRY gate, close-before-modify fail.

### WF4

- 원래 목적: ML-first / EA-first / runtime-fix-first 중 하나만 여는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: reports/branch_decision_packet.json 또는 동등 decision memo
- enforceable gate 보완: KPI evaluator + branch decision packet 자동 생성.

### WF5

- 원래 목적: 선택된 primary branch 하나만 최적화하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: candidate specs, sweep manifests, result packs
- enforceable gate 보완: branch-specific orchestrator와 immutable candidate evidence bundle.

### WF6

- 원래 목적: benchmark/OOS/stress 재스테이징으로 dispersion과 stability를 검증하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: benchmark/OOS/stress candidate reruns
- enforceable gate 보완: window-restage runner와 candidate comparator 추가.

### WF7

- 원래 목적: single-layer attribution 이후 제한적 joint sweep만 수행하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate, 하지만 지금 당장은 열면 형식적 절차가 됩니다.
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: interaction matrix, incumbent/challenger compare set
- enforceable gate 보완: WF5/WF6 완료 후에만 unlock하도록 dependency 강제.

### WF8

- 원래 목적: selected candidate를 RC bundle로 패키징하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: `_coord/releases/<rc_id>/`, rc_manifest.yaml, file hashes, reproducibility rerun
- enforceable gate 보완: RC bundler + dual-signature gatekeeper.

### WF9

- 원래 목적: previous stable state를 rollback bundle로 고정하는 것입니다.
- 현재 구현 상태: **SCAFFOLD**
- gate의 실질성: 의미 있는 gate
- 현재 산출물만으로 pass/fail 측정 가능 여부: 불가
- 누락된 증거: `_coord/rollback_points/<rb_id>/`, rollback_manifest.yaml, patch-input retention
- enforceable gate 보완: rollback bundler + hash verifier + restore rehearsal.

---

### CP0

- 원래 의도된 목적: compile clean + Step21 schema consistency 보장
- 현재 구현 상태: **IMPLEMENTED**
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: current commit binding, MT5 build fingerprint
- 보완: compile을 campaign run manifest 안으로 편입하고 hash 고정. 현재 retained compile log 자체는 존재하며 0 error/0 warning입니다.

### CP1

- 원래 의도된 목적: duplicate/phantom EXIT, same-ts EXIT→ENTRY, core-row alignment 같은 runtime invariants 보장
- 현재 구현 상태: **IMPLEMENTED**, 현 시점 판정은 PROVISIONAL
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: campaign baseline에서의 feature-off core-row alignment, close-before-modify hard fail
- 보완: independent validator가 campaign run 기준으로 CP1 재실행, same-ts 검사를 더 정밀화.

### CP2

- 원래 의도된 목적: window freeze와 gap policy의 기계적 고정
- 현재 구현 상태: **IMPLEMENTED**
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 가능
- 누락된 증거: freeze hash / source commit
- 보완: freeze manifest schema validator 추가.

### CP3

- 원래 의도된 목적: dual-control pack separation과 parity evidence 확보
- 현재 구현 상태: **IMPLEMENTED**, 현 시점 판정은 PROVISIONAL
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: actual external pack payload hashes
- 보완: pack_hash_manifest.json와 ONNX parity recheck 결과를 필수화.

### CP4

- 원래 의도된 목적: parser pipeline이 contract를 만족하면서 자동 materialization되는지 확인
- 현재 구현 상태: **IMPLEMENTED**, 현 시점 판정은 PROVISIONAL
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: admissible provenance, strict failure policy
- 보완: artifact replay 금지, ENTRY coverage gate, close-before-modify fail.

### CP5

- 원래 의도된 목적: leakage-free split, Stage1 guardrail, Stage2 incumbent의 admissibility 확인
- 현재 구현 상태: **IMPLEMENTED at artifact level**, 판정은 PROVISIONAL
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: machine-readable validator packet that ties validation metadata + export parity + pack hashes together
- 보완: ml_lineage_manifest.json 추가, validator가 step14/15 artifacts를 한 번에 확인하도록 구성. Stage1 eligible_candidate_count=0, Stage2 stage2_c02 winner는 현재 evidence와 일치합니다.

### CP6

- 원래 의도된 목적: gate regret / exit trade-off / modify trade-off가 실제로 측정 가능한지 확인
- 현재 구현 상태: **IMPLEMENTED in tooling**, 판정은 PROVISIONAL
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 부분 가능
- 누락된 증거: benchmark diagnostic on profitability control pack
- 보완: current replay sample이 아니라 benchmark diagnostic evidence를 기준으로 decision packet 생성.

### CP7

- 원래 의도된 목적: benchmark/OOS/stress all-pass without fatal runtime anomaly
- 현재 구현 상태: **MISSING evidence**
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 불가
- 누락된 증거: benchmark/OOS/stress outputs and comparator
- 보완: window-restage runner와 comparison report 필수화.

### CP8

- 원래 의도된 목적: RC reproducibility와 rollback completeness 보장
- 현재 구현 상태: **MISSING evidence**
- 의미 있는 gate인지: 예
- 현재 산출물만으로 측정 가능 여부: 불가
- 누락된 증거: RC bundle, rollback bundle, dual-signature validator report
- 보완: release gatekeeper와 rollback verifier를 분리 구현.

---

## 6. Gap Matrix

| Gap | Verified evidence | Effect | Owner | Priority |
|-----|-------------------|--------|-------|----------|
| WF2 provenance admission gap | campaign tree lacks visible raw_tester_outputs/; parse_manifest.json points to retained artifact path. | baseline admissibility 붕괴 | operator + validator | P0 |
| contract / checklist drift gap | contract still lists old counterfactual domain; checklist says parser_outputs/ empty and uses old EARLY_EXIT framing, while current outputs are populated with exit subtypes. | false-green / stale interpretation | writer + validator | P0 |
| integrity-hardfail gap | close-before-modify is only warning; ENTRY unmapped is not gating condition. | CP1/CP4 insufficiently strict | parser maintainer | P0 |
| external asset hashing gap | registry references MQL5/Files/* packs; EA references packs and runtime patch files; repo does not verify retained payload bundle. | reproducibility and promotion integrity weakness | operator + ML exporter | P0 |
| RC / rollback bundle gap | runbooks require bundles; current tree does not verify them. | no admissible promotion / rollback | release gatekeeper | P0 |
| independent validator gap | no mechanized validator/gatekeeper path was verified in the repo tree examined. | writer self-certification risk | platform lead | P0 |
| portability / orchestration gap | run_step21_matrix.ps1 is workstation-bound and packages fixed retained artifacts rather than campaign windows. | agent-driven pipeline cannot scale across hosts | operator tooling | P1 |
| short-side evidence gap | current direction distribution is 5346 LONG vs 61 SHORT. | short-side correctness/performance remains weakly evidenced | ML lead | P1 |
| KPI semantics gap | avg_profit_factor is average daily PF while cumulative PnL is negative. | performance reporting can look stronger than aggregate economics | analytics lead | P1 |

---

## 7. Optimization Roadmap

현재 구조를 기준으로 한 순서는 다음이 가장 안전합니다.

### Immediate next executable phase: campaign-native benchmark diagnostic baseline

먼저 broad optimization을 열지 말고, manifest.yaml의 immediate_actions에 이미 적혀 있는 diagnostic_single_run을 admissible하게 만들어야 합니다. 단, 지금 상태 그대로는 안 되고, campaign-native runner / raw hash / pack hash / preset snapshot / compile log binding이 먼저 필요합니다. 이 단계의 출력은 kpi_summary.json과 branch_decision_packet.json이어야 합니다.

### Prerequisite contracts를 먼저 닫기

- campaign_run_manifest.schema.json
- raw_hash_manifest.schema.json
- pack_hash_manifest.schema.json
- kpi_summary.schema.json
- rc_manifest.schema.json
- rollback_manifest.schema.json

이 여섯 개가 먼저 있어야 이후 workflow가 문서가 아니라 gate가 됩니다. *(Inferred)*

### Missing orchestration pieces를 채우기

- tools/run_campaign_backtest.py 또는 동등한 runner
- tools/validate_campaign_run.py
- tools/build_kpi_summary.py
- tools/build_branch_decision_packet.py
- tools/bundle_rc.py
- tools/bundle_rollback.py

현재 있는 run_step21_matrix.ps1는 retained step21 regression matrix를 패키징하는 스크립트이지, campaign manifest-driven optimization runner가 아닙니다.

### Validation bottlenecks를 우선 해결

- provenance admission
- close-before-modify hard fail
- unmapped ENTRY gating
- external pack hashing
- short-side sufficiency gate
- true trade-level PF / expectancy surface

이 다섯 개가 해결되지 않으면 optimization을 열수록 false-green candidate가 쌓일 가능성이 큽니다. *(Verified gap + Inferred sequencing)*

### Branch sequencing rationale

기본 prior는 ML-first Stage1 refresh가 맞습니다. 이유는 registry와 selection evidence가 이미 Stage1 eligible_candidate_count=0, Stage2 stage2_c02 incumbent를 가리키기 때문입니다. 다만 이 prior를 blind rule로 쓰면 안 되고, benchmark diagnostic에서 실제로 gate regret / exit cost / modify trade-off가 더 큰 병목으로 나오면 EA-first로 바꿔야 합니다. Stage1이 안정되기 전에는 joint sweep을 열지 않는 것이 맞습니다. runbook도 one layer at a time을 명시합니다.

### Promotion blockers를 끝에서가 아니라 중간에 제거

- RC/RB bundler
- dual-signature validator
- reproducibility rerun
- patch-input capture

이 네 개는 마지막에 추가하는 부가 기능이 아니라, shortlist 이전부터 구조를 잡아두어야 합니다. 후보가 생긴 뒤에 bundle contract를 붙이면 lineage가 뒤늦게 맞지 않는 경우가 많습니다. *(Inferred)*

### What should be automated first vs deferred

**먼저 자동화할 것:** runner, validator, pack hashing, KPI evaluator, branch decision packet, RC/RB bundlers, Codex cross-validator

**뒤로 미룰 것:** notebooks, dashboard polish, broad joint sweep search, broker-connected live probes

현재 repo의 bottleneck은 insight 부족이 아니라 admissible evidence manufacturing 부족이기 때문입니다.

---

## 8. Multi-Agent Operating Architecture

이 repo에 맞는 운영 topology는 아래처럼 writer / operator / validator / gatekeeper를 명시적으로 분리하는 구조가 적절합니다. 현재 repo root에 .claude가 있으므로, agent/skill/hook definition도 그 아래로 정리하는 것이 자연스럽습니다.

현재 runbook가 요구하는 CP0–CP8, RC/RB bundle, one-layer-at-a-time discipline을 code-enforced topology로 번역한 설계입니다.

### 8.1 Subagent topology

**writer-orchestrator (Claude Code Opus)**
- 권한: repo code / manifests / scripts 수정
- 금지: 자기 산출물의 promotion 승인
- 산출물: code diff, candidate spec, runner changes, docs update

**mt5-operator**
- 권한: compile / tester run / raw output capture
- 금지: code modification, gate override
- 산출물: compile log, raw outputs, preset snapshot, run manifest

**parser-analytics**
- 권한: raw outputs read-only, parser/kpi outputs write
- 금지: raw CSV rewrite
- 산출물: parse_manifest.json, coverage_manifest.json, master tables, kpi_summary.json

**ml-trainer-exporter**
- 권한: step14/15 retrain, ONNX export, pack rebuild
- 금지: RC promotion
- 산출물: validation reports, export validation report, pack hash manifest

**independent-validator (Codex CLI or equivalent second thread)**
- 권한: frozen evidence bundle read-only
- 금지: source code write, operator config change
- 산출물: validator_report.json, validator_signature.json

**release-gatekeeper**
- 권한: RC/RB bundle 검증 후 promote/reject decision record 작성
- 금지: code edit, candidate generation
- 산출물: promotion_decision.json

**human-principal**
- 권한: explicit override / waiver / kill-switch reset
- 금지: undocumented verbal waiver
- 산출물: override_record.yaml

### 8.2 No-self-promotion rule

- writer는 candidate를 제안할 수만 있고, 승인할 수는 없습니다.
- validator는 writer 산출물을 frozen evidence로만 다시 검증합니다.
- gatekeeper는 writer와 validator의 manifest/hash/signature가 일치할 때만 WF8/WF9를 통과시킵니다.
- human override는 있어도 되지만 반드시 override_record.yaml로 retained 되어야 합니다.

### 8.3 Custom skills

`.claude/skills/` 아래에 최소 다음 skill들을 두는 구성이 적합합니다.

- campaign-bootstrap
- mt5-preset-builder
- campaign-run-sealer
- parser-replay
- integrity-gate
- kpi-branch-decision
- ml-export-parity
- pack-hash-capture
- rc-bundle-assembly
- rollback-bundle-verify
- stale-doc-detector

### 8.4 Hooks structure

`.claude/hooks/` 기준 제안입니다.

**pre-run**
- freeze manifest schema check
- control-pack separation check
- external pack hash capture presence check

**post-run**
- raw file completeness
- raw hash sealing
- compile/tester log copy
- single-run contamination detection

**post-parse**
- CP1/CP4 strict validator
- coverage gate
- KPI summary build

**pre-promotion**
- CP0–CP8 aggregate validator
- RC/RB bundle presence
- dual-signature check

**post-rollback**
- CP0/CP1 rerun
- restore verification packet 작성

### 8.5 MCP integration points

- **github MCP:** issues / PR / commit metadata / artifact links
- **shell/filesystem MCP:** runner execution, hash sealing
- **mt5-runner MCP:** compile/test backtest control
- **parquet-json MCP:** parser outputs inspection
- **onnx-inspector MCP:** pack contents / shape / hash verification
- **thread-bridge MCP:** Claude Code ↔ Codex cross-review packet exchange
- **signing/hash MCP:** SHA-256 + optional signature sealing

### 8.6 Artifact retention strategy

캠페인마다 아래 구조를 권장합니다.

```
_coord/campaigns/<campaign_id>/runs/RUN_<UTCSTAMP>/
  00_request/    — candidate spec, operator config
  10_compile/    — compile log, terminal build info
  20_raw/        — immutable raw tester outputs
  21_hash/       — raw_hash_manifest, pack_hash_manifest
  30_parsed/     — parser outputs
  40_kpi/        — kpi summary, branch decision packet
  50_validator/  — validator report, signatures
  60_decision/   — pass/fail decision, override record
```

이후 selected candidate만 `_coord/releases/<rc_id>/`와 `_coord/rollback_points/<rb_id>/`로 승격됩니다.

### 8.7 Contract validation layer

다음 schema validator는 repo에 반드시 있어야 합니다.

- campaign manifest schema
- run manifest schema
- parse manifest semantic validator
- coverage manifest semantic validator
- KPI summary validator
- RC manifest validator
- rollback manifest validator

### 8.8 Escalation path

- operator infra failure → mt5-operator 재시도 budget 소진 후 writer-orchestrator와 human에 escalate
- integrity failure → 즉시 independent-validator + human, optimization 중단
- writer / validator disagreement → human-principal arbitration
- promotion failure → gatekeeper reject only, writer 수정 후 새 candidate로 재진입

### 8.9 Independent validator integration / Codex cross-review

- Claude writer thread는 frozen evidence bundle만 export합니다.
- Codex validator thread는 동일 bundle을 read-only로 다시 검사해 validator_report.json을 씁니다.
- gatekeeper는 두 report가 불일치하면 자동 reject합니다.
- "writer가 자기 결과를 자기 thread에서 승격 승인"하는 경로는 없어야 합니다.

---

## 9. Closed-Loop Optimization Design

repo에 맞는 closed-loop는 다음 state machine으로 설계하는 것이 적절합니다. 현재 manifest의 diagnostic_single_run → direction_decision, runbook의 WF0–WF9, registry의 Stage1 bottleneck 상태를 그대로 operational loop로 번역한 구조입니다.

### 9.1 Loop

1. **CandidateSpec 생성** — EA parameter sweep candidate 또는 ML refresh candidate를 1개 생성. one primary branch rule 유지.
2. **MT5 Backtest Execution** — benchmark 또는 target window 실행. compile log, preset snapshot, raw outputs, raw hashes 생성.
3. **Parser Pipeline** — parse_step21_run.py → build_master_tables.py → build_counterfactual_eval.py → build_daily_risk_metrics.py
4. **KPI Evaluation** — trade-level PF / expectancy / drawdown / dispersion / HHI / short-side coverage / anomaly counts 산출
5. **Decision Gate:**
   - integrity fail → stop
   - KPI fail + ML symptom → retrain/export/rebuild path
   - KPI fail + EA policy symptom → next EA layer sweep
   - KPI pass + convergence met → WF8 RC packaging
6. **If KPI below threshold:**
   - ML retrain → ONNX re-export → pack rebuild → benchmark retest
   - 필요한 경우에만 OOS/stress restage
7. **If convergence met:**
   - WF8 RC packaging → matching WF9 rollback point
   - independent validator sign-off
   - human promotion review

### 9.2 Decision routing logic

**ML-first로 보내는 증상:**
- low Stage1 margin
- short-side collapse
- Stage1 guardrail fail
- candidate scarcity / no eligible challenger

**EA-first로 보내는 증상:**
- signal quality는 괜찮은데 gate regret가 큼
- early-exit opportunity cost가 risk saved보다 큼
- protective modify alpha loss가 save ratio보다 큼

**runtime-fix-first로 보내는 증상:**
- dup EXIT / same-ts EXIT→ENTRY / core-row drift
- authority disagreement 증가
- patch input lineage 불완전

이는 현재 runbook decision matrix와 정합적입니다.

### 9.3 Coverage / integrity gates

다음은 hard gate여야 합니다.

- duplicate non-modify groups = 0
- duplicate EXIT groups = 0
- same-ts EXIT→ENTRY = 0
- close-before-modify overlap = 0 for admissible runs
- unmapped ENTRY/EXIT/MODIFY = 0
- unresolved NO_EXIT = 0
- feature-off core-row alignment = true
- runtime reload active이면 patch inputs retained = true
- raw_dir provenance = campaign run workspace only

현재 repo 기준으로 마지막 넷은 아직 enforceable gate가 아니므로 추가 구현이 필요합니다.

### 9.4 Retry budget

- infra/transient execution failure: 3회 자동 재시도
- parser file-lock / partial-copy failure: 1회 재시도
- integrity failure: 0회 재시도, 즉시 stop
- candidate branch cycle without benchmark improvement: 2회 연속 실패 시 human escalation

### 9.5 Divergence detection

다음 중 하나면 divergence로 취급하는 것이 적절합니다.

- OOS PF / benchmark PF < 0.75
- OOS expectancy / benchmark expectancy < 0.60
- regime dispersion threshold 초과
- monthly or regime HHI 급등
- short-side coverage collapse
- authority disagreement / retcode anomaly 상승
- reproducibility rerun mismatch
- negative PnL with deceptively high daily-average PF

### 9.6 Rollback trigger

- promoted RC의 shadow/live에서 CP1 위반
- pack hash mismatch
- runtime patch input missing
- broker audit / tx authority mismatch
- RC reproducibility mismatch
- hard drawdown breach
- human kill-switch

### 9.7 Audit trail / evidence retention

각 loop iteration마다 최소 retained artifact는 아래여야 합니다.

- candidate_spec.yaml
- run_manifest.json
- raw_hash_manifest.json
- pack_hash_manifest.json
- parse_manifest.json
- coverage_manifest.json
- kpi_summary.json
- decision_packet.json
- validator_report.json
- promotion_decision.json
- override_record.yaml (있을 경우)

### 9.8 Human override points

- branch choice override
- soft-threshold waiver
- synthetic negative-path overlap waiver
- final promotion approval
- kill-switch reset after incident review

### 9.9 Kill-switch conditions

다음은 자동 중단 조건으로 두는 편이 맞습니다.

- duplicate EXIT > 0
- same-ts EXIT→ENTRY > 0
- close-before-modify > 0 on admissible run
- unmapped EXIT/MODIFY > 0
- unresolved NO_EXIT > 0
- feature-off core-row alignment false
- runtime patch lineage missing
- pack hash mismatch
- OOS hard-gate breach after accepted candidate

---

## 10. Quantitative Acceptance Criteria

아래 수치는 현재 repo가 아직 enforce하지는 않지만, 현재 data_freeze_manifest.yaml의 window geometry와 repo의 KPI surface를 감안할 때 live-grade governance에 적합한 제안값입니다. 중요한 전제는, 현재 avg_profit_factor는 average daily PF이므로 release gate에는 true trade-level PF를 새로 추가해야 한다는 점입니다.

### 10.1 Non-negotiable integrity gates

| Gate | Threshold | Type |
|------|-----------|------|
| duplicate EXIT | = 0 | Hard gate |
| same-ts EXIT→ENTRY | = 0 | Hard gate |
| close-before-modify overlap | = 0 | Hard gate |
| unmapped ENTRY/EXIT/MODIFY | = 0 | Hard gate |
| unresolved NO_EXIT | = 0 | Hard gate |
| feature-off core-row alignment | = true | Hard gate |

이 숫자들은 0이 맞습니다. runtime ambiguity가 profitability보다 먼저 막혀야 하기 때문입니다.

### 10.2 Train / validation / benchmark / OOS minimum span

| Window | Requirement | Type |
|--------|-------------|------|
| optimization corpus | 세 frozen optimization fold 전체 사용 또는 동등한 clean actual-tick bars ≥ 120k, 어떤 fold도 40k bars 미만 불가 | Hard gate |
| benchmark | current independent benchmark window 전체 사용 | Hard gate |
| OOS | current OOS window 전체 사용 또는 90 calendar days 이상 | Hard gate |
| stress | current stress window 전체 사용 | Soft warning for profitability, Hard gate for runtime integrity |

현재 freeze geometry가 이미 약 47k / 60k / 47k bars의 3-fold를 제공하므로, 이보다 얇게 줄이면 regime-adaptive variance를 감당하기 어렵습니다. benchmark와 OOS는 independence가 핵심이라 full reserved window 사용이 중요합니다.

### 10.3 Minimum trade count

| Window | Requirement | Type |
|--------|-------------|------|
| benchmark closed trades | ≥ 250 | Hard gate |
| OOS closed trades | ≥ 150 | Hard gate |
| benchmark+OOS combined closed trades | ≥ 500 | Hard gate |
| regime-level 비교 | 해당 regime trade count ≥ 30일 때만 hard judgment, 미만은 UNVERIFIED | Soft warning |

regime-adaptive 시스템은 overall PF만 보면 regime-specific collapse를 놓치기 쉽습니다. n<30 regime는 hard acceptance에 쓰기엔 표본이 너무 얇습니다.

### 10.4 Stage1 guardrail

| Gate | Threshold | Type |
|------|-----------|------|
| min_cand0_pass_recall | >= 0.50 | Hard gate |

runbook와 selection report 모두 이 값을 핵심 Stage1 guardrail로 사용하고 있고, current bottleneck도 여기서 발생합니다. PASS/abstention discipline이 무너지면 downstream EA tuning으로 고치기 어렵습니다.

### 10.5 Profit factor threshold

| Window | Requirement | Type |
|--------|-------------|------|
| benchmark global trade-level PF | ≥ 1.15 | Hard gate |
| OOS global trade-level PF | ≥ 1.05 | Hard gate |
| benchmark+OOS combined PF | ≥ 1.10 | Hard gate |
| stress PF | ≥ 1.00 | Soft warning |

benchmark는 selection window라 OOS보다 약간 더 높은 quality를 요구하는 것이 합리적입니다. OOS는 decay를 감안해도 1.05 아래면 live-grade margin이 얇습니다. regime-adaptive 시스템에서는 OOS collapse가 benchmark outperformance보다 더 중요합니다.

### 10.6 expectancy_r threshold

| Window | Requirement | Type |
|--------|-------------|------|
| benchmark expectancy | ≥ +0.05R | Hard gate |
| OOS expectancy | ≥ +0.02R | Hard gate |
| stress expectancy | ≥ 0R | Soft warning |

PF는 trade size와 tail 구조를 가릴 수 있고, R-normalized expectancy가 실제 execution edge를 더 직접적으로 보여줍니다. 단, current repo의 expectancy는 proxy 성격이 있으므로 true initial-risk-normalized R로 재정의해야 합니다.

### 10.7 Sharpe-like / return-quality

| Window | Requirement | Type |
|--------|-------------|------|
| benchmark daily equity-normalized Sharpe-like | ≥ 0.8 | Soft warning |
| OOS daily equity-normalized Sharpe-like | ≥ 0.5 | Soft warning |

intraday execution system에서 daily Sharpe-like는 helpful하지만, integrity gate보다 우선순위가 낮습니다. 다만 drawdown과 함께 보면 overfit/fragility 탐지에 유용합니다.

### 10.8 Maximum drawdown

| Window | Requirement | Type |
|--------|-------------|------|
| benchmark max equity DD | ≤ 8% | Hard gate |
| OOS max equity DD | ≤ 10% | Hard gate |
| stress max equity DD | ≤ 12% | Hard gate for release candidates |

live-grade execution system에서 DD ceiling은 release admissibility의 핵심입니다. OOS가 benchmark보다 1.5배 이상 나빠지면 regime adaptation이 unstable할 가능성이 큽니다.

### 10.9 Regime-level dispersion

| Gate | Threshold | Type |
|------|-----------|------|
| worst regime PF (regime trades ≥ 30) | ≥ 0.90 | Hard gate |
| best-to-worst regime expectancy spread | ≤ 0.35R | Hard gate |
| worst regime expectancy vs overall expectancy | gap ≤ 0.20R | Hard gate |

이 시스템은 본질적으로 regime-adaptive이므로, 일부 regime에서만 edge가 나오는 후보는 구조적으로 취약합니다.

### 10.10 Concentration HHI

| Gate | Threshold | Type |
|------|-----------|------|
| regime PnL HHI | ≤ 0.30 | Hard gate |
| monthly PnL HHI | ≤ 0.22 | Soft warning |

특정 regime나 특정 월에 PnL이 쏠리면, 실전에서는 state drift에 취약합니다. current repo의 day-level HHI만으로는 부족하므로 month/regime level HHI를 추가해야 합니다.

### 10.11 Minimum OOS consistency

| Gate | Threshold | Type |
|------|-----------|------|
| OOS calendar months 중 profitable month 비율 | ≥ 60% | Hard gate |
| OOS를 3등분했을 때 최소 profitable subwindows | 2/3 이상 | Hard gate |
| single subwindow contribution share | ≤ 50% of OOS net PnL | Hard gate |

한 구간 대박에 의존하는 후보는 selection artifact일 가능성이 큽니다.

### 10.12 Benchmark 대비 OOS stability

| Gate | Threshold | Type |
|------|-----------|------|
| OOS PF / benchmark PF | ≥ 0.75 | Hard gate |
| OOS expectancy / benchmark expectancy | ≥ 0.60 | Hard gate |
| OOS DD ≤ 1.5 × benchmark DD | — | Hard gate |

benchmark 대비 OOS decay를 정량화하지 않으면 regime-adaptive system의 generalization failure를 늦게 발견합니다.

### 10.13 Short-side sufficiency

| Gate | Threshold | Type |
|------|-----------|------|
| two-sided release 주장 시 benchmark+OOS 기준 short-side closed trades 비중 | ≥ 10% 또는 short-side decisions ≥ 10% | Hard gate |
| long-dominant 전략으로 명시한다면 short-side | waiver required | Soft warning |

현재 sample처럼 SHORT evidence가 매우 얇으면, SHORT correctness는 코드 존재만으로는 충분하지 않기 때문입니다.

---

## 11. Immediate Remediation Backlog (우선순위 순)

### P0 — Campaign-native runner 도입

- 산출물: run_manifest.json, raw_hash_manifest.json, pack_hash_manifest.json, preset_snapshot.ini
- done condition: benchmark diagnostic run이 campaign workspace 안에서 end-to-end 재생성됨

### P0 — Strict validator 도입

- 산출물: validate_campaign_run.py
- done condition: provenance mismatch, close-before-modify, unmapped ENTRY/EXIT/MODIFY, unresolved NO_EXIT가 hard fail

### P0 — RC / rollback bundler 도입

- 산출물: bundle_rc.py, bundle_rollback.py
- done condition: RC마다 matching rollback point가 자동 생성되고 hash 검증 통과

### P0 — Independent validator / gatekeeper 분리

- 산출물: Codex validator thread + validator_report.json + gatekeeper policy
- done condition: writer self-promotion 불가

### P1 — KPI semantic repair

- 산출물: true trade-level PF, combined PF, avg_daily_PF 구분
- done condition: promotion report에서 daily average PF를 aggregate PF처럼 쓰지 않음

### P1 — Contract / checklist regeneration

- 산출물: versioned MASTER_TABLE_CONTRACT.md, auto-generated checklist
- done condition: contract, parse manifest, checklist taxonomy 일치

### P1 — External pack / patch hashing

- 산출물: pack snapshot hash, patch-input retention
- done condition: external MQL5/Files state가 promotion evidence에 포함됨

### P1 — Short-side / regime sufficiency gates

- 산출물: sample sufficiency checker
- done condition: thin-side candidates가 warning이나 fail로 명시됨

### P2 — Readiness report 자동 생성

- 산출물: filesystem/artifact 기반 audit summary
- done condition: stale manual checklist 의존도 제거

### P2 — Notebook / dashboard polish

- 산출물: review-friendly dashboard
- done condition: 의사결정 편의성 향상, 그러나 gate 자체에는 영향 없음

---

## 12. Repo에서 검증 불가능한 항목

- **external MQL5/Files/triple_sigma_pack_v1, triple_sigma_pack_step15_q1, triple_sigma_pack_long_step16의 실제 payload contents와 hashes** — repo code와 registry는 참조하지만, repo-retained payload bundle은 현재 검증되지 않았습니다.

- **triple_sigma_runtime_patch/ 실제 contents** — EA는 참조하지만 current repo tree에서는 directory가 확인되지 않았습니다.

- **broker-connected / live-account execution evidence** — closeout 문서 자체가 "this workspace에서는 live/broker-connected execution을 돌리지 않았다"고 명시합니다.

- **current commit에서의 independent recompile / rerun** — compile log는 retained evidence로 존재하지만, 이 세션에서 MT5를 실제 실행해 재컴파일·재백테스트하지는 않았습니다.

- **actual RC / rollback bundles** — runbook는 있으나 current tree에서 bundle 실체는 검증되지 않았습니다.

- **dedicated ops guide DOCX의 full content** — root에 DOCX 파일 존재는 확인했지만, 이번 평가는 더 강한 증거인 current repo tree/raw code/artifacts를 우선 사용했고, DOCX 본문 전체를 별도로 추출·인용하지는 않았습니다.

- **실제 Claude Code ↔ Codex thread bridge / MCP runtime deployment 상태** — 운영 설계는 제안 가능하지만, 현재 repo만으로는 외부 agent runtime의 실가동 여부를 검증할 수 없습니다.

---

## 최종 판정

> 현재 repo는 Step21 runtime과 pre-opt governance의 핵심 재료는 갖췄지만, **admissible campaign lineage · strict validator · RC/RB bundles · independent gatekeeper**가 없어서 autonomous optimization 승격선에는 아직 못 올라와 있습니다.
