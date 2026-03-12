# CODEX Phase A Review v3

> Date: 2026-03-12
> Scope: Re-review of the 3 held conditions from `_coord/ops/CODEX_PHASE_A_REVIEW_v2.md`
> Target files:
> - `tools/run_campaign_backtest.py`
> - `tools/validate_campaign_run.py`
> - `_coord/ops/schemas/campaign_run_manifest.schema.json`
> - `_coord/ops/STEP21_OPS_CHECKLIST_v2.md`
> Final Verdict: `보류`

## Findings

1. `[High]` Held condition 4 is not fully closed. The runner now uses `jsonschema.Draft7Validator`, but `seal` still downgrades schema violations to warnings and continues (`tools/run_campaign_backtest.py:394-414`). In addition, both runner and validator construct `Draft7Validator` without a format checker (`tools/run_campaign_backtest.py:432-453`, `tools/validate_campaign_run.py:364-419`), so the schema's `run_timestamp` `"format": "date-time"` is not actually enforced (`_coord/ops/schemas/campaign_run_manifest.schema.json:37-40`). Direct probe result: `validate_against_schema()` returned `[]` for `run_timestamp="not-a-date"`, while correctly failing `window_alias="bad_alias"`. This is a substantial improvement over v2, but it is not yet "full Draft7 validation" as claimed.

## Held Condition Reassessment

| # | Previous held condition | Current evidence | Status |
|---|-------------------------|------------------|--------|
| 3 | Minute-level window lineage or hard boundary check on parsed bars | `prepare` still writes MT5 preset dates as date-only (`tools/run_campaign_backtest.py:108-121`), but it preserves the original campaign timestamps in `request_meta.json` (`tools/run_campaign_backtest.py:253-266`) and re-emits them into `run_manifest.json` (`tools/run_campaign_backtest.py:360-388`). The validator now parses full datetime precision and performs a no-tolerance hard boundary check (`tools/validate_campaign_run.py:199-339`). The actual campaign manifest still carries minute-level windows (`_coord/campaigns/C2026Q1_stage1_refresh/manifest.yaml:39-86`). A synthetic probe with `bar_min=2026.01.01 09:59` and `window_from=2026.01.01 10:00` produced `FAIL`. | `해소` |
| 4 | Full schema validation wired into seal/validate stages | `pack_hash_ref` is now `[string, null]` in S1 (`_coord/ops/schemas/campaign_run_manifest.schema.json:111-123`). Runner and validator both use `jsonschema.Draft7Validator` (`tools/run_campaign_backtest.py:432-453`, `tools/validate_campaign_run.py:388-417`). Enum/type/nested required checks now fire: direct probe confirmed `window_alias="bad_alias"` fails, and `pack_hash_ref=None` is accepted. However `run_timestamp="not-a-date"` still passes because `format` is unchecked, and the runner does not fail closed on schema errors. | `부분 해소 / 보류` |
| 5 | Checklist sync for runner / validator / contract-v2 / schema items | The WF2 runner and validator entries are marked done (`_coord/ops/STEP21_OPS_CHECKLIST_v2.md:101-108`), Contract v2 is marked done (`_coord/ops/STEP21_OPS_CHECKLIST_v2.md:126`), and the deliverables/schema tables now show `DONE` for runner, validator, and S1-S3 (`_coord/ops/STEP21_OPS_CHECKLIST_v2.md:211-224`). | `해소` |

## Verification Performed

- `python -m py_compile tools/run_campaign_backtest.py tools/validate_campaign_run.py`
- Direct schema probes against `campaign_run_manifest.schema.json`
  - `pack_hash_ref=None` -> accepted as intended
  - `window_alias="bad_alias"` -> enum failure emitted
  - `run_timestamp="not-a-date"` -> unexpectedly accepted
- Synthetic window-boundary probe
  - `bar_log` first timestamp `2026.01.01 09:59`
  - manifest `window_from=2026.01.01 10:00`
  - validator result -> `FAIL`

## Final Verdict

- Verdict: `보류`
- Reason: held conditions 3 and 5 are closed, but held condition 4 is only partially resolved. The schema layer is much stronger than v2, yet it is still not fully fail-closed or fully conformant with the claimed Draft7 validation behavior.

## Minimum Actions To Reach Approval

1. Add a Draft7 format checker in both schema validation paths so `format: "date-time"` is actually enforced.
2. Make `tools/run_campaign_backtest.py seal` exit non-zero when schema validation errors exist, instead of printing warnings and continuing.
3. Optional hygiene: update the module header in `tools/validate_campaign_run.py`, which still says "1-day tolerance" even though the gate is now a hard check.
