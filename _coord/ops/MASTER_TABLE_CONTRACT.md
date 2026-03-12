# Master Table Contract

Version: 2.1 (updated 2026-03-12, A' window clipping policy)

Status:
- Defines the derived-table schema for Step21 backtest analytics.
- Source schema: `design/BAR_LOG_SCHEMA.md` (log schema v2.0).
- Core CSV files are retained as-emitted per `RETAINED_ARTIFACT_STANDARD.md`.
- Derived tables are built by the parser pipeline, not by modifying core CSVs.
- v2.0 changes: EXIT_SL/EXIT_TP/EXIT_FORCE taxonomy in counterfactual_eval (replaces EARLY_EXIT).
- v2.1 changes: A' window clipping policy added (see below).

## Window Clipping Policy (A')

MT5 Strategy Tester accepts date-only `FromDate`/`ToDate` (no minute precision),
but campaign manifest defines minute-level window boundaries. This creates
unavoidable "raw overcapture" — bars and trades before `window_from` or after
`window_to` appear in raw output.

**Policy:**
1. **Raw immutability**: files in `20_raw/` are never modified after seal.
2. **Validator**: raw overcapture on the left (bar_min < window_from) is **WARN**,
   not FAIL. Overcapture on the right (bar_max > window_to) remains **FAIL**.
3. **Parser-level clipping**: `parse_step21_run.py --window-from --window-to`
   trims both bar_log and trade_log to exact manifest boundaries before emitting
   parsed parquet files. Clipping stats are recorded in `parse_manifest.json`
   under `window_clipping`.
4. **Trade lifecycle integrity**: when an ENTRY trade falls outside the window,
   the entire trade lifecycle (ENTRY + MODIFY + EXIT rows with the same
   `trade_id`) is removed. Partial lifecycle rows are never emitted.
5. **Invariant checks** run on the post-clipping dataset, so only in-window
   trades are validated.

## Source files per single backtest run

| File | Schema source | Notes |
|------|---------------|-------|
| `trade_log.csv` | `BAR_LOG_SCHEMA.md` trade_log section | ENTRY / EXIT / MODIFY rows |
| `bar_log_YYYYMMDD.csv` | `BAR_LOG_SCHEMA.md` bar_log section | One file per trading day |
| `broker_audit.csv` | `BAR_LOG_SCHEMA.md` broker_audit section | Optional, enabled by `InpBrokerAuditEnabled` |
| `exec_state.ini` | Runtime persisted state | Pending exit/modify, recovery state |

## Derived table: `trades_master`

Paired realized trade ledger. One row per completed trade lifecycle.

Required columns:
- `trade_id` (str) - from trade_log (format: `TS_XXXXX`)
- `position_id` (int) - from trade_log
- `entry_time` (datetime) - timestamp of ENTRY row
- `exit_time` (datetime) - timestamp of EXIT row
- `symbol` (str)
- `direction` (str) - LONG / SHORT
- `lot` (float)
- `entry_price` (float)
- `exit_price` (float)
- `sl_price` (float) - at entry
- `tp_price` (float) - at entry
- `pnl` (float) - from EXIT row
- `k_sl_req` (float)
- `k_tp_req` (float)
- `k_sl_eff` (float) - effective after modify
- `k_tp_eff` (float) - effective after modify
- `hold_bars` (int) - predicted
- `bars_held` (int) - actual
- `exit_reason` (str) - SL / TP / EARLY_EXIT / TIME_POLICY / etc.
- `regime_id_at_entry` (int)
- `spread_atr_at_entry` (float)
- `flip_used` (bool)
- `model_pack_version` (str)
- `clf_version` (str)
- `prm_version` (str)
- `cost_model_version` (str)
- `modify_count` (int) - total modifies during lifecycle
- `modify_reasons` (str) - comma-separated list of modify reasons applied
- `tx_authority` (str) - from EXIT row
- `pack_dir_at_entry` (str)
- `active_model_pack_dir` (str) - at exit
- `runtime_reload_status` (str) - at exit

Derivation rules:
- Pair each EXIT row with its matching ENTRY row by `trade_id`.
- `modify_count` and `modify_reasons` are aggregated from all MODIFY rows
  with the same `trade_id`.
- Trades with EXIT but no matching ENTRY are flagged as anomalies.
- Trades with ENTRY but no matching EXIT (open at end) are retained with
  `exit_time=NULL` and `pnl=NULL`.

Validation invariants:
- Every `trade_id` has exactly one ENTRY row.
- Every completed `trade_id` has exactly one EXIT row.
- `exit_time > entry_time` for all completed trades.
- No duplicate `(trade_id, event_type)` pairs for ENTRY/EXIT.

## Derived table: `bars_master`

Full bar-level signal and state snapshot. One row per bar.

Required columns (from bar_log):
- All columns from `bar_log_YYYYMMDD.csv` as defined in BAR_LOG_SCHEMA.md.

Additional derived columns:
- `date` (date) - extracted from filename
- `bar_index` (int) - sequential bar counter within run

Derivation rules:
- Concatenate all `bar_log_YYYYMMDD.csv` files in date order.
- Add `date` from filename and `bar_index` as sequential counter.

Validation invariants:
- `time` column is strictly monotonically increasing.
- `schema_version` and `log_schema_version` are consistent across all rows.

## Derived table: `modify_master`

Protective management ledger. One row per executed modify event.

Required columns (from trade_log MODIFY rows):
- `trade_id` (str) - format: `TS_XXXXX`
- `timestamp` (datetime)
- `position_id` (int)
- `modify_reason` (str) - BREAK_EVEN / TRAILING / TP_RESHAPE / TIME_POLICY
- `modify_count` (int) - cumulative modify count at this event
- `sl_price` (float) - new SL after modify
- `tp_price` (float) - new TP after modify
- `k_sl_eff` (float) - effective after modify
- `k_tp_eff` (float) - effective after modify
- `bars_held` (int) - bars held at time of modify
- `tx_authority` (str)

Derivation rules:
- Filter trade_log for `event_type=MODIFY` rows only.
- Retain all columns as-emitted.

Validation invariants:
- No MODIFY row should exist for a bar that also has an EXIT for the same
  `trade_id` (close-before-modify precedence).
- `modify_count` is monotonically non-decreasing per `trade_id`.

## Derived table: `execution_master`

Request/execution/recovery layer. One row per trade_log event.

Required columns:
- All columns from `trade_log.csv` as-emitted.

Additional derived columns:
- `event_order` (int) - sequential event counter within run
- `lifecycle_id` (int) - grouped by trade_id for lifecycle analysis

Derivation rules:
- Retain trade_log as-is with additional sequential counters.
- Group events by `trade_id` for lifecycle tracking.

Validation invariants:
- `timestamp` is monotonically non-decreasing.
- Event sequence per trade_id follows: ENTRY -> [MODIFY]* -> EXIT.

## Derived table: `audit_master` (optional)

Broker-style audit trail. Only built when `broker_audit.csv` exists.

Required columns:
- All columns from `broker_audit.csv` as-emitted.
- `event_order` (int) - sequential counter.

## Derived table: `counterfactual_eval`

H=72 bar ex-post evaluator. One row per bar where a decision was made.

Required columns:
- `time` (datetime) - bar time
- `decision_type` (str) - GATE_BLOCK / ENTRY / EXIT_SL / EXIT_TP / EXIT_FORCE / NO_EXIT / MODIFY
  - EXIT_SL: exit via stop-loss trigger
  - EXIT_TP: exit via take-profit trigger
  - EXIT_FORCE: forced exit (TIME_POLICY, EARLY_EXIT, or other non-SL/TP reasons)
  - Note: replaces the former single EARLY_EXIT category with exit-reason-aware taxonomy
- `actual_outcome_72` (float) - price change over next 72 bars
- `gate_regret` (float) - PnL of hypothetical entry if gate was relaxed
  (NULL if not a gate block)
- `exit_opportunity_cost` (float) - additional PnL if exit was delayed
  (NULL if not an exit event)
- `exit_risk_saved` (float) - drawdown avoided by exiting
  (NULL if not an exit event)
- `modify_alpha_loss` (float) - PnL lost due to protective modify
  (NULL if not a modify event)
- `modify_save_ratio` (float) - drawdown saved / alpha lost by modify
  (NULL if not a modify event)
- `regime_id` (int)

Derivation rules:
- For each bar, look forward 72 bars (H=72) to compute ex-post outcomes.
- Gate regret: compare actual (blocked) vs hypothetical (entered) outcome.
- Exit trade-off: compare actual (exited) vs hypothetical (held) outcome.
- Modify trade-off: compare actual (modified) vs hypothetical (unmodified).

## Derived table: `daily_risk_metrics`

Daily portfolio/risk aggregation. One row per trading day.

Required columns:
- `date` (date)
- `n_trades` (int) - trades closed on this day
- `n_entries` (int) - trades opened on this day
- `gross_pnl` (float) - sum of PnL for trades closed today
- `net_pnl` (float) - after costs
- `expectancy_r` (float) - mean PnL / mean risk
- `profit_factor` (float) - gross profit / gross loss
- `payoff_ratio` (float) - mean win / mean loss
- `win_rate` (float)
- `max_drawdown_day` (float) - intraday peak-to-trough
- `cumulative_pnl` (float) - running cumulative
- `cumulative_drawdown` (float) - from equity peak
- `long_count` (int)
- `short_count` (int)
- `regime_distribution` (str) - JSON dict of regime counts
- `avg_bars_held` (float)
- `concentration_hhi` (float) - Herfindahl index of PnL concentration

Validation invariants:
- `date` is unique and in chronological order.
- `n_trades >= 0` for all rows.
- `profit_factor >= 0` when gross_loss > 0.

## Parser output layout

### Campaign-native layout (admissible — v2)

```
runs/RUN_<ts>/30_parsed/
  trades_master.parquet
  bars_master.parquet
  modify_master.parquet
  execution_master.parquet
  audit_master.parquet          (optional)
  counterfactual_eval.parquet
  daily_risk_metrics.parquet
  coverage_manifest.json
  parse_manifest.json           (metadata + validation results)
```

### Legacy flat layout (retained artifact replay archive — non-admissible)

```
parser_outputs/
  trades_master.parquet
  bars_master.parquet
  modify_master.parquet
  execution_master.parquet
  audit_master.parquet          (optional)
  counterfactual_eval.parquet
  daily_risk_metrics.parquet
  parse_manifest.json           (metadata + validation results)
```

## Schema versioning

- Current contract version: `2.0`
- Contract changes require version bump and manifest update.
- Parser must validate emitted schema version against this contract.
