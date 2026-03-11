# Recovery Matrix

| Case | Preset class | Synthetic component | Expected invariant |
| --- | --- | --- | --- |
| Control trade | control | none | feature-off baseline stays core-row aligned with retained STEP20 control |
| Live pass regression | actual-path | none | pass-based live early exit only, opposite count stays `0`, modify count stays `0` |
| Live opposite regression | synthetic trigger + actual close path | opposite trigger source | close path remains actual tester path, feature-off baseline still matches retained STEP20 live opposite |
| Close-vs-modify precedence | synthetic close trigger + synthetic BE trigger + actual close path | opposite trigger, BE trigger | close wins, `MODIFY=0`, duplicate `EXIT=0`, same-timestamp `EXIT -> ENTRY=0` |
| Live trailing probe | actual modify path | none | `MODIFY` rows emit with `modify_reason=TRAILING`, no duplicate `EXIT`, same-timestamp `EXIT -> ENTRY=0` |
| Live TP reshape probe | actual modify path | none | `MODIFY` rows emit with `modify_reason=TP_RESHAPE`, no duplicate `EXIT`, same-timestamp `EXIT -> ENTRY=0` |
| Live time-policy probe | actual modify path | none | `MODIFY` rows emit with `modify_reason=TIME_POLICY`, no duplicate `EXIT`, same-timestamp `EXIT -> ENTRY=0` |
| Pending modify recovery with tx authority | synthetic trigger + recovery probe + actual modify path | BE trigger, reload probe | `MODIFY` rows emit with `modify_reason=BREAK_EVEN`, pending modify clears after reconcile, duplicate `EXIT=0` |
| Runtime reload success | runtime patch success | patch file | active model pack changes, status ends `RELOADED`, broker audit retains attempt and success tags |
| Runtime reload rollback | runtime patch forced failure | patch file | active model pack restores previous pack, status ends `ROLLED_BACK`, broker audit retains attempt and rollback tags |

Rule:
- synthetic components are limited to trigger fabrication, reload probes, and
  fault injection.
- close execution, modify execution, transaction observation, persistence, and
  reconciliation remain actual tester-path validation.
