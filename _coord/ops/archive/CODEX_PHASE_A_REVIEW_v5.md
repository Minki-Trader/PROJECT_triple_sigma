# CODEX Phase A Review v5

> Date: 2026-03-12
> Scope: Final re-review of the remaining `format: date-time` remediation from `_coord/ops/CODEX_PHASE_A_REVIEW_v4.md`
> Target files:
> - `tools/run_campaign_backtest.py`
> - `tools/validate_campaign_run.py`
> Final Verdict: `Hold`

## Findings

1. `[High]` The newly added custom `date-time` checker is still too permissive, so the held condition is only partially fixed. Both code paths now register `@fmt_checker.checks("date-time")`, but the implementation delegates directly to `datetime.fromisoformat(...)` (`tools/run_campaign_backtest.py:449-454`, `tools/validate_campaign_run.py:398-403`). On the current Python 3.13 runtime, `datetime.fromisoformat(...)` accepts several values that are not valid JSON Schema / RFC3339 `date-time` strings:
   - `2026-03-12` (date only)
   - `2026-03-12 10:15:30` (space separator)
   - `2026-03-12T10:15:30` (no timezone offset)

   Direct probes showed:
   - `tools.run_campaign_backtest.validate_against_schema(...)` returned `[]` for all three invalid `run_timestamp` examples above.
   - `tools.validate_campaign_run.validate_schema_conformance(...)` likewise returned `[]` for `run_timestamp="2026-03-12"`.
   - The schema still declares `run_timestamp` as `{"type": "string", "format": "date-time"}` (`_coord/ops/schemas/campaign_run_manifest.schema.json:37-40`), so this implementation still does not enforce the intended contract.

   The remediation is therefore improved but incomplete: it now rejects obviously bad text like `run_timestamp="not-a-date"`, yet it still admits malformed non-RFC3339 timestamps that the schema is supposed to reject.

## Verification Performed

- `python -m py_compile tools/run_campaign_backtest.py tools/validate_campaign_run.py`
- Direct negative probes on the runner path:
  - `run_timestamp="not-a-date"` -> `["run_timestamp: 'not-a-date' is not a 'date-time'"]`
  - `run_timestamp="2026-03-12"` -> `[]`
  - `run_timestamp="2026-03-12 10:15:30"` -> `[]`
  - `run_timestamp="2026-03-12T10:15:30"` -> `[]`
- Direct negative probes on the validator path:
  - `run_timestamp="not-a-date"` -> `[run_manifest] ... is not a 'date-time'`
  - `run_timestamp="2026-03-12"` -> `[]`
- Runtime probe of `datetime.fromisoformat(...)` on this workstation confirmed it accepts the three malformed examples above.

## Final Verdict

- Verdict: `Hold`
- Reason: the specific `not-a-date` probe now fails as requested, but the actual schema contract is still not enforced. A `format: "date-time"` checker cannot be considered closed while date-only, space-separated, and timezone-less timestamps still pass both validation paths.

## Minimum Action To Reach Approval

1. Replace the checker logic with an RFC3339-conformant gate, not bare `datetime.fromisoformat(...)`.
2. Add regression probes or tests for at least these cases in both runner and validator:
   - `2026-03-12`
   - `2026-03-12 10:15:30`
   - `2026-03-12T10:15:30`
   - `2026-03-12T10:15:30Z` or `2026-03-12T10:15:30+00:00` as a positive control
