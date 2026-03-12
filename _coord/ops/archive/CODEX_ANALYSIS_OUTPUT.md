새 문서 2개를 작성했습니다.

[STEP21_OPS_CHECKLIST_v2.md](C:/Users/awdse/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/PROJECT_triple_sigma/_coord/ops/STEP21_OPS_CHECKLIST_v2.md)에는 Phase 0~10 재검증, Audit Finding 1~7 교차 검증, STALE 항목 정리, CP0~CP8 재평가, 신규 필수 도구 6종과 schema contract 6종, 우선순위와 의존관계까지 반영했습니다.  
[NEXT_ACTIONS_ROADMAP.md](C:/Users/awdse/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/PROJECT_triple_sigma/_coord/ops/NEXT_ACTIONS_ROADMAP.md)에는 이번 주 P0 blocker 해소, 2주 내 campaign-native baseline, 1개월 내 WF2~WF4 및 branch decision 로드맵을 산출물/의존관계/완료 기준과 함께 정리했습니다.

핵심 결론은 현재 상태가 “runtime + scaffold는 있음, 하지만 broad optimization green은 아님”입니다. 특히 `parse_manifest.json`의 외부 `raw_dir`, warning-only `close-before-modify`, empty `raw_tester_outputs/benchmark/oos/stress/reports`, empty `releases/rollback_points/triple_sigma_runtime_patch/`, 부재한 runner/validator/bundler/schema를 기준으로 CP1, CP4, CP7, CP8을 하향 재평가했습니다.

검증은 실제 파일시스템, `_coord/ops` 전 문서, campaign 산출물, 관련 `tools/*`와 `src/ea/TripleSigma.mq5` 대조 기준으로 수행했습니다. 코드 실행 테스트나 새 도구 구현은 하지 않았습니다.