# STEP21 Deferred Runtime Surface

Status:
- Historical promotion note retained for traceability.
- The parked STEP21 surface described here was activated and implemented on
  2026-03-09.
- Active implementation details now live in
  `design/STEP21_Tx_Authoritative_Protective_Runtime.md`.

Original purpose of this file:
- Separate STEP20 closeout from follow-on engineering work.
- List the runtime and observability surface intentionally deferred out of
  STEP20.
- Preserve a restart note before any STEP21 code work began.

Original promoted carry-over:
- wider protective modify family beyond BE-only:
  - TP reshape
  - trailing logic
  - extra time-policy logic
- core `trade_log.csv` / `bar_log` schema expansion
- `MODIFY` row emission
- tx-authoritative execution state handling using `OnTradeTransaction()`
- runtime hot reload / rollback
- broker audit surface
- broker-connected / live-account testing

Resolution:
- trailing / TP reshape / time-policy protective modify: implemented
- `trade_log.csv` / `bar_log` schema expansion: implemented
- `MODIFY` row emission: implemented
- tx-authoritative entry / exit logging and state finalization: implemented
- runtime hot reload / rollback: implemented
- broker audit surface: implemented
- broker-connected / live-account execution: not run in this workspace; remains
  an operational validation follow-up rather than a local code blocker

Preserved invariants from the original promotion note:
- feature-off STEP21 control / live-pass / live-opposite regressions remain
  aligned with retained STEP20 artifacts
- close-before-modify precedence remains intact
- duplicate `EXIT` groups remain `0`
- same-timestamp `EXIT -> ENTRY` remains `0`
- tester-only synthetic flags remain inert outside tester mode
