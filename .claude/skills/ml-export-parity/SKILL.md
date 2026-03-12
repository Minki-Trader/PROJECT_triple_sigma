---
description: "[NOT IMPLEMENTED - Phase C] Verify ONNX export parity between Python training and MQL5 inference."
user-invocable: true
---

# ML Export Parity (Phase C)

> **STATUS: NOT IMPLEMENTED** — Requires ONNX parity verification tooling.

## Purpose
Verify that ONNX models exported from Python training (step15) produce identical outputs when loaded by the MQL5 EA runtime.

## Dependencies
- ONNX shape inspector tool
- Python-side reference inference outputs
- MQL5-side inference outputs from bar_log
- Comparison script with tolerance threshold

## Role
Operates as **ml-trainer-exporter**.
