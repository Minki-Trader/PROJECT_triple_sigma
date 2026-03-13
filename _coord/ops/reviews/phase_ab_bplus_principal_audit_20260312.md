# Phase A/B/B+ Principal Quant Audit (WF4 pre-check)

## 핵심 결론
- 현재 파이프라인은 **A' clipping 자체는 방어 가능**하나, hash/integrity 체인과 promotion guard에 **실제 우회 경로**가 있어 WF4 전 차단이 필요함.
- 특히 `20_raw/`에 seal 이후 신규 `bar_log_*.csv`가 추가되어도 validator가 검출하지 못하는 구조는 optimization 반복 환경에서 치명적임.
