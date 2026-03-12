---
description: "[NOT IMPLEMENTED - Phase C] Assemble release candidate bundle from validated campaign run."
user-invocable: true
---

# RC Bundle Assembly (Phase C)

> **STATUS: NOT IMPLEMENTED** — Requires `tools/bundle_rc.py`.

## Purpose
Assemble a release candidate bundle from a fully validated campaign run: copy validated artifacts, generate RC manifest, prepare for dual-signature.

## Dependencies
- `tools/bundle_rc.py` (not yet written)
- `_coord/ops/schemas/rc_manifest.schema.json` (S5, not yet written)
- Validated run with `50_validator/validator_report.json` verdict=PASS
- `60_decision/promotion_decision.json` from release-gatekeeper

## Output
- `_coord/releases/<rc_id>/` bundle

## Role
Operates as **release-gatekeeper**.
