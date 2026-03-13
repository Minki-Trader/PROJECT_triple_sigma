# Backtest Baseline (Fixed)

Last updated: 2026-03-06 KST

This file is the fixed default for all future Strategy Tester runs unless explicitly overridden in chat.

## Fixed Tester Conditions

- Symbol: `US100`
- Model: `Every tick based on real ticks` (`Model=4`)
- Initial deposit: `500 USD`
- Leverage: `1:100` (`Leverage=100`)

## Notes

- Keep these values locked for all Codex-driven test runs.
- If a task needs a temporary override, write it explicitly in `CHAT.md` and revert to this baseline after the run.
