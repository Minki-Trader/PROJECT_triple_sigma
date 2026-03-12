---
description: "[NOT IMPLEMENTED - Phase D] Verify rollback point integrity and test restore procedure."
user-invocable: true
---

# Rollback Bundle Verify (Phase D)

> **STATUS: NOT IMPLEMENTED** — Requires `tools/bundle_rollback.py`.

## Purpose
Verify a rollback point bundle: hash integrity check, restore rehearsal, CP0/CP1 rerun after restore.

## Dependencies
- `tools/bundle_rollback.py` (not yet written)
- `_coord/ops/schemas/rollback_manifest.schema.json` (S6, not yet written)
- `_coord/rollback_points/<rb_id>/` bundle

## Role
Operates as **release-gatekeeper**.
