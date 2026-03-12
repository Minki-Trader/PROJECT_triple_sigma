---
description: Generate MT5 tester .ini preset from campaign manifest parameters. Use when creating a custom backtest configuration with parameter overrides.
user-invocable: true
---

# MT5 Preset Builder

Generate or inspect MT5 tester presets from campaign manifest.

## Arguments
- `$ARGUMENTS` = manifest path or run directory

## Usage Modes

### Mode 1: Inspect existing preset
If `$ARGUMENTS` points to a run directory with `00_request/preset_snapshot.ini`:
- Read and display the preset
- Cross-check against manifest parameters
- Flag any date override issues

### Mode 2: Generate new preset
If `$ARGUMENTS` points to a manifest.yaml:
- Extract `diagnostic_baseline_params` section
- Extract `tester_baseline` section (symbol, period, model, deposit, leverage)
- Extract target window boundaries

**Critical Warning**: The manifest's `source_preset_dates_are: oos` (line 98) means the source preset covers the OOS window, NOT the benchmark window. Always apply explicit date overrides when targeting a different window.

## Key Parameters
From `manifest.yaml` `diagnostic_baseline_params.params`:
- `InpModelPackDir`, `InpPMinTrade`, `InpDeltaFlip`
- `InpSpreadAtrMaxBase`, `InpSpreadAtrMaxHard`
- `InpKTPScaleMin`, `InpKTPScaleMax`
- `InpDevPointsBase`, `InpDevPointsAddMax`, `InpDevPointsHardMax`
- `InpRiskPctBase`, `InpRiskPctHardMin`, `InpRiskPctHardMax`
- `InpEarlyExitEnabled`, `InpEarlyExitLive`, `InpPExitPass`, `InpMinHoldBarsBeforeExit`
- All boolean feature flags

## MT5 Date Limitation
MT5 tester accepts date-only `FromDate`/`ToDate` (no minute precision). This creates raw overcapture which is handled by parser-level window clipping (A' policy).
