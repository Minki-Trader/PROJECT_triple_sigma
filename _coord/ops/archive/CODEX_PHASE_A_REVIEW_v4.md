# CODEX Phase A Review v4

> Date: 2026-03-12
> Scope: Re-review of the 3 residual items from `_coord/ops/CODEX_PHASE_A_REVIEW_v3.md`
> Target files:
> - `tools/run_campaign_backtest.py`
> - `tools/validate_campaign_run.py`
> Final Verdict: `보류`

## Findings

1. `[High]` The `format: "date-time"` gate is still not enforced in the current runtime, so the primary held condition remains open. Both code paths now pass `jsonschema.FormatChecker()` (`tools/run_campaign_backtest.py:449-452`, `tools/validate_campaign_run.py:398-401`), but `jsonschema 4.26.0` on this workstation has no `"date-time"` checker registered, and `rfc3339-validator` is not installed. Direct probes showed:
   - `validate_against_schema()` returned `[]` for a manifest with `run_timestamp="not-a-date"`.
   - `validate_schema_conformance()` likewise emitted no schema failure for the same invalid timestamp.
   - End-to-end `python tools/run_campaign_backtest.py seal <synthetic_run>` with `prepared_at="not-a-date"` exited `0` and printed `Run sealed`.
   - End-to-end `python tools/validate_campaign_run.py <same_run> --campaign-manifest <synthetic_manifest>` returned `Validation: PASS`.

## Residual Issue Reassessment

| # | Requested remediation | Current evidence | Status |
|---|-----------------------|------------------|--------|
| 1 | Add `jsonschema.FormatChecker()` to runner and validator so `format: date-time` is actually enforced | The calls were added in both files (`tools/run_campaign_backtest.py:449-452`, `tools/validate_campaign_run.py:398-401`), but runtime behavior is unchanged for `date-time`. The schema still declares `run_timestamp` with `format: "date-time"` (`_coord/ops/schemas/campaign_run_manifest.schema.json:37-40`), yet invalid timestamps still pass. Root cause observed in probe: `"date-time" not in jsonschema.FormatChecker.checkers`. | `미해소` |
| 2 | Make runner `seal` hard-fail with `sys.exit(1)` on schema validation error | Implemented at `tools/run_campaign_backtest.py:411-415`. Synthetic probe with schema-invalid `campaign_id="BAD"` exited non-zero and printed the schema error block, confirming fail-closed behavior when a schema error is actually emitted. | `해소` |
| 3 | Update validator wording from "1-day tolerance" to minute-level hard check | Header text now says `minute-level hard check` (`tools/validate_campaign_run.py:10`) and the gate docstring now says `No loose tolerance - this is a hard check.` (`tools/validate_campaign_run.py:221`). | `해소` |

## Verification Performed

- `python -m py_compile tools/run_campaign_backtest.py tools/validate_campaign_run.py`
- Runtime checker inspection:
  - `jsonschema` version: `4.26.0`
  - `"date-time" in jsonschema.FormatChecker.checkers` -> `False`
  - `rfc3339-validator` -> not installed
- Direct schema probes:
  - `tools.run_campaign_backtest.validate_against_schema(...)` with `run_timestamp="not-a-date"` -> `[]`
  - `tools.validate_campaign_run.validate_schema_conformance(...)` with `run_timestamp="not-a-date"` -> `[]`
- End-to-end runner probes:
  - Invalid `campaign_id` -> `seal` exited `1` as intended
  - Invalid `prepared_at/run_timestamp` -> `seal` exited `0` unexpectedly
- End-to-end validator probe:
  - Same invalid-timestamp synthetic run -> `Validation: PASS`

## Final Verdict

- Verdict: `보류`
- Reason: remediation items 2 and 3 are closed, but item 1 is still not closed in the actual execution environment. Because invalid RFC3339 timestamps still pass both runner and validator, the held schema-enforcement condition from v3 remains unresolved.

## Minimum Action To Reach Approval

1. Make `date-time` validation deterministic on this workstation, not just syntactically wired. Practical options are:
   - add and pin the dependency that provides the `date-time` checker, then assert it is available at runtime, or
   - register a local `date-time` checker explicitly in code.
2. Add a regression probe or test proving both paths reject `run_timestamp="not-a-date"`:
   - `run_campaign_backtest.py seal` must exit non-zero
   - `validate_campaign_run.py` must emit schema `FAIL`
