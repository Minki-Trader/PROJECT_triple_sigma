# Branch Decision Packet - RUN_20260312T115832Z

- Primary branch: `ML-first`
- Confidence: `high`
- Rationale: Losses are broad across both directional books while gate/exit pressure is not dominant. The benchmark points upstream to Stage1/Stage2 quality before EA relaxation.

## Headline Metrics
- Total PnL: -458.85
- Global PF: 0.7370
- Global WR: 40.01%
- Max equity DD: -92.21%
- Gate regret mean: 16.95
- Gate block rate: 0.0067
- Exit cost/risk ratio: 0.5198

## Triggered Rules
- `ML-first` / `pf_below_one`: observed=0.7370456967988172 threshold=< 1.0 :: Portfolio PF is below break-even.
- `ML-first` / `negative_total_pnl`: observed=-458.84999999999997 threshold=< 0 :: Benchmark baseline is losing money.
- `ML-first` / `both_directions_weak`: observed={'LONG': 0.7592555929518906, 'SHORT': 0.7252252252252251} threshold=both < 0.9 :: Both directional books are weak, pointing upstream to model quality rather than a single EA layer.
- `ML-first` / `gate_block_rate_low`: observed=0.006699419383653417 threshold=< 0.02 :: Gate rejection rate is too low to explain the benchmark loss by itself.
- `ML-first` / `exit_cost_not_dominant`: observed=0.5198312710077878 threshold=<= 1.0 :: Exit opportunity cost does not exceed risk saved, so EA exits are not the primary deficit.
- `ML-first` / `candidate_margin_tail_thin`: observed=0.06268739999999999 threshold=< 0.10 :: Low tail margin suggests weak classifier separation on the weakest candidate decile.

## Next Actions
- Prioritize Stage1 refresh on the frozen optimization folds before changing EA thresholds.
- Keep Stage2 retune secondary unless post-refresh branch metrics still show weak exit/gate attribution.
- Re-stage the benchmark run after ML refresh and compare PF, drawdown, and directional PF symmetry.
