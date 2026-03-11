# STEP21 Promotion And Deferred Scope

Status:
- Historical root note retained for traceability.
- Originally written when STEP21 had only been promoted out of STEP20.
- Superseded by `STEP21_CLOSEOUT_AND_VERIFICATION.md` after implementation on
  2026-03-09.

Originally promoted scope:
- wider protective modify family beyond BE-only
- core `trade_log.csv` / `bar_log` schema expansion
- `MODIFY` row emission
- tx-authoritative execution state handling
- runtime hot reload / rollback
- broker audit surface
- broker-connected / live-account testing

Resolution summary:
- protective modify family: implemented
- schema expansion and `MODIFY` rows: implemented
- tx-authoritative runtime surface: implemented
- runtime hot reload / rollback: implemented
- broker audit surface: implemented
- broker-connected / live-account execution: not run in this workspace

Preserved invariants from the original promotion checkpoint:
- no feature-off regression against retained STEP20 evidence
- duplicate `EXIT` remains `0`
- same-timestamp `EXIT -> ENTRY` remains `0`
- close-before-modify precedence remains intact
