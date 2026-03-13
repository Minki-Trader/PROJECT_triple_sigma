# Stage1 Refresh Packet - RUN_20260312T115832Z

- Primary branch: `ML-first`
- Confidence: `high`
- WF5 ready: `True`

## Benchmark Diagnosis
- Total PnL: -458.85
- Global PF: 0.7370
- Global WR: 40.01%
- Max equity DD: -92.21%
- Candidate margin p10: 0.0627

## Incumbent Stage1
- Selected candidate: `stage1_baseline` (control_fallback)
- Eligible challengers: 0
- Used control fallback: True
- Source data window: 2025-11-28 20:10:00 -> 2026-02-27 23:50:00
- Within optimization corpus: False
- Overlaps OOS window: True
- Outer refit guardrail pass: True

## Fold Inputs
- fold_1: C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_1_step21_control_trade_source (2022-09-12 23:50:00 -> 2023-05-03 23:50:00)
- fold_2: C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_2_step21_control_trade_source (2023-05-02 23:50:00 -> 2024-02-26 23:50:00)
- fold_3: C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_3_step21_control_trade_source (2025-04-01 23:50:00 -> 2025-11-24 23:50:00)

## Weakest Regimes
- Regime 1: val_macro_f1=0.3631, val_cand0_pass_recall=0.9497
- Regime 3: val_macro_f1=0.4222, val_cand0_pass_recall=0.6291
- Regime 5: val_macro_f1=0.4760, val_cand0_pass_recall=0.7609

## Launch Plan
- `python src/ml/step11_labeling.py --input "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_1_step21_control_trade_source" --pack-meta "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\step15_export_q1_out\model_pack\pack_meta.csv" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_1" --from "2022.09.13 17:15" --to "2023.05.03 09:45"`
- `python src/ml/step11_labeling.py --input "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_2_step21_control_trade_source" --pack-meta "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\step15_export_q1_out\model_pack\pack_meta.csv" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_2" --from "2023.05.03 09:55" --to "2024.02.26 20:05"`
- `python src/ml/step11_labeling.py --input "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_fold_3_step21_control_trade_source" --pack-meta "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\step15_export_q1_out\model_pack\pack_meta.csv" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_3" --from "2025.04.02 09:10" --to "2025.11.24 14:50"`
- `python tools/build_step11_fold_union.py --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11_union" "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_1" "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_2" "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11\fold_3"`
- `python src/ml/step12_training.py --input-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11_union" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step12_stage1_refresh" --fail-on-acceptance`
- `python src/ml/step13_training.py --step11-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11_union" --step12-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step12_stage1_refresh" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step13_stage2_incumbent_refit" --fail-on-acceptance`
- `python src/ml/step14_training.py --step11-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step11_union" --step12-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step12_stage1_refresh" --step13-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step13_stage2_incumbent_refit" --output-dir "C:\Users\awdse\.codex\worktrees\0fc9\PROJECT_triple_sigma\_coord\artifacts\C2026Q1_stage1_refresh_RUN_20260312T115832Z_wf5_stage1_refresh\step14_stage1_refresh_validation" --fail-on-acceptance`

## Recommended Focus
- Build Stage1 corpus only from frozen optimization_folds; do not reuse the current OOS-era training window.
- Keep `min_cand0_pass_recall >= 0.5` as the hard Stage1 guardrail during WF5 search.
- Expand Stage1 architecture/search before any EA threshold sweep because benchmark losses are broad across both directional books.
- Re-run Step14 selection on the merged fold corpus before opening Stage2 retune.
