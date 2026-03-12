---
description: "[NOT IMPLEMENTED - Phase C] Seal external model pack payload with SHA-256 hashes and ONNX shape verification."
user-invocable: true
---

# Pack Hash Capture (Phase C)

> **STATUS: NOT IMPLEMENTED** — Pack hashing is currently done inside `run_campaign_backtest.py seal`.

## Purpose
Standalone pack payload sealing: SHA-256 hash every file in the model pack directory, verify ONNX file shapes, produce `pack_hash_manifest.json`.

## Dependencies
- `tools/run_campaign_backtest.py` seal already handles pack hashing during run sealing
- This skill would be for standalone pack verification outside of a campaign run

## Role
Operates as **ml-trainer-exporter**.
