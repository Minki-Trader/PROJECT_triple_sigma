"""
build_counterfactual_eval.py - H=72 forward ex-post evaluator.

Reads bars_master and trades_master from parser_outputs/ and builds
counterfactual_eval.parquet per MASTER_TABLE_CONTRACT.md v1.0.

For each bar where a decision occurred (gate block, entry, exit, modify),
looks forward H=72 bars to compute:
  - gate_regret: PnL of hypothetical entry if gate was relaxed
  - exit_opportunity_cost: additional PnL if exit was delayed
  - exit_risk_saved: drawdown avoided by exiting
  - modify_alpha_loss: PnL lost due to protective modify
  - modify_save_ratio: drawdown saved / alpha lost

Usage:
    python tools/build_counterfactual_eval.py <parser_outputs_dir> [--horizon 72]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


H_DEFAULT = 72  # bars forward

# Exit reason taxonomy mapping (from TS_Execution.mqh ExitReasonFromDeal)
EXIT_REASON_TO_DECISION = {
    "SL": "EXIT_SL",
    "TP": "EXIT_TP",
    "FORCE_EXIT": "EXIT_FORCE",
    "EARLY_EXIT": "EARLY_EXIT",
}


def floor_to_m5(ts_str: str) -> str:
    """Floor a timestamp to its owning M5 bar.

    Trade timestamps are 'YYYY.MM.DD HH:MM:SS', bar timestamps 'YYYY.MM.DD HH:MM'.
    A trade at HH:MM:SS belongs to the M5 bar starting at HH:(MM floored to 5).
    Example: '2026.01.15 10:32:45' -> '2026.01.15 10:30'
    """
    s = str(ts_str)[:16]  # "YYYY.MM.DD HH:MM"
    try:
        minute = int(s[14:16])
        floored = (minute // 5) * 5
        return f"{s[:14]}{floored:02d}"
    except (ValueError, IndexError):
        return s


def compute_forward_metrics(bars: pd.DataFrame, idx: int, direction: str, h: int):
    """Compute forward price change and drawdown for H bars from index idx."""
    if idx + h >= len(bars):
        remaining = len(bars) - idx - 1
        if remaining < 1:
            return np.nan, np.nan, np.nan
        h = remaining

    entry_close = bars.iloc[idx]["close"]
    future = bars.iloc[idx + 1: idx + 1 + h]

    if future.empty:
        return np.nan, np.nan, np.nan

    future_closes = future["close"].values
    final_close = future_closes[-1]

    if direction == "LONG":
        pnl_72 = final_close - entry_close
        worst = np.min(future["low"].values) - entry_close
        best = np.max(future["high"].values) - entry_close
    else:  # SHORT
        pnl_72 = entry_close - final_close
        worst = entry_close - np.max(future["high"].values)
        best = entry_close - np.min(future["low"].values)

    max_adverse = min(worst, 0.0)
    return float(pnl_72), float(max_adverse), float(best)


def build_counterfactual(bars_df: pd.DataFrame, trades_df: pd.DataFrame,
                         trade_log_df: pd.DataFrame, h: int
                         ) -> tuple[pd.DataFrame, dict]:
    """Build counterfactual evaluation table.

    Returns (counterfactual_df, coverage_info) where coverage_info contains
    unmapped_event_details, unresolved_no_exit, and exit_reason metadata.
    """
    empty_info = {
        "unmapped_event_details": [],
        "unresolved_no_exit": [],
        "exit_reason_available": False,
        "has_exit_reason_col": False,
    }
    if bars_df.empty:
        return pd.DataFrame(), empty_info

    # Ensure numeric types
    for col in ["close", "high", "low"]:
        if col in bars_df.columns:
            bars_df[col] = pd.to_numeric(bars_df[col], errors="coerce")

    bars_df = bars_df.reset_index(drop=True)

    # Build time-to-index lookup (bar times are "YYYY.MM.DD HH:MM" without seconds)
    time_to_idx = {}
    if "time" in bars_df.columns:
        for i, t in enumerate(bars_df["time"]):
            time_to_idx[str(t)] = i

    rows = []

    # --- Gate blocks: bars where gate_pass=0 and there was a candidate ---
    if "gate_pass" in bars_df.columns and "cand_long" in bars_df.columns:
        gate_blocks = bars_df[
            (bars_df["gate_pass"] == 0) &
            ((bars_df["cand_long"] == 1) | (bars_df["cand_short"] == 1))
        ]
        for idx, bar in gate_blocks.iterrows():
            direction = "LONG" if bar.get("cand_long", 0) == 1 else "SHORT"
            pnl_72, mae, mfe = compute_forward_metrics(bars_df, idx, direction, h)
            rows.append({
                "time": bar.get("time"),
                "bar_index": idx,
                "decision_type": "GATE_BLOCK",
                "direction": direction,
                "regime_id": bar.get("regime_id"),
                "actual_outcome_72": pnl_72,
                "gate_regret": max(pnl_72, 0) if not np.isnan(pnl_72) else np.nan,
                "exit_opportunity_cost": np.nan,
                "exit_risk_saved": np.nan,
                "modify_alpha_loss": np.nan,
                "modify_save_ratio": np.nan,
            })

    # --- Entries and exits from trade_log ---
    # Trade timestamps have seconds ("YYYY.MM.DD HH:MM:SS"), bar times don't.
    # Use floor_to_m5() to match trade events to M5 bars.
    # Track exit bar indices to detect NO_EXIT bars later.
    exit_bar_indices = set()
    unmapped_event_details = []
    has_exit_reason_col = (
        not trade_log_df.empty and "exit_reason" in trade_log_df.columns
    )
    exit_reason_available = False

    if not trade_log_df.empty and "timestamp" in trade_log_df.columns:
        for _, event in trade_log_df.iterrows():
            ts = event.get("timestamp")
            etype = event.get("event_type", "")
            direction = event.get("direction", "LONG")
            bar_key = floor_to_m5(ts) if pd.notna(ts) else None
            idx = time_to_idx.get(bar_key)
            if idx is None:
                unmapped_event_details.append({
                    "trade_id": str(event.get("trade_id", "")),
                    "timestamp": str(ts),
                    "event_type": str(etype),
                    "bar_key_attempted": str(bar_key),
                })
                continue

            if etype == "ENTRY":
                pnl_72, mae, mfe = compute_forward_metrics(bars_df, idx, direction, h)
                rows.append({
                    "time": ts,
                    "bar_index": idx,
                    "decision_type": "ENTRY",
                    "direction": direction,
                    "regime_id": event.get("regime_id_at_entry"),
                    "actual_outcome_72": pnl_72,
                    "gate_regret": np.nan,
                    "exit_opportunity_cost": np.nan,
                    "exit_risk_saved": np.nan,
                    "modify_alpha_loss": np.nan,
                    "modify_save_ratio": np.nan,
                })

            elif etype == "EXIT":
                exit_bar_indices.add(idx)
                pnl_72, mae, mfe = compute_forward_metrics(bars_df, idx, direction, h)
                opp_cost = max(pnl_72, 0) if not np.isnan(pnl_72) else np.nan
                risk_saved = abs(min(mae, 0)) if not np.isnan(mae) else np.nan

                # Determine decision_type from exit_reason taxonomy
                raw_reason = str(event.get("exit_reason", "")).strip() if has_exit_reason_col else ""
                if raw_reason and raw_reason in EXIT_REASON_TO_DECISION:
                    decision = EXIT_REASON_TO_DECISION[raw_reason]
                    exit_reason_available = True
                else:
                    decision = "EARLY_EXIT"

                rows.append({
                    "time": ts,
                    "bar_index": idx,
                    "decision_type": decision,
                    "direction": direction,
                    "regime_id": event.get("regime_id_at_entry"),
                    "actual_outcome_72": pnl_72,
                    "gate_regret": np.nan,
                    "exit_opportunity_cost": opp_cost,
                    "exit_risk_saved": risk_saved,
                    "modify_alpha_loss": np.nan,
                    "modify_save_ratio": np.nan,
                })

            elif etype == "MODIFY":
                pnl_72, mae, mfe = compute_forward_metrics(bars_df, idx, direction, h)
                alpha_loss = max(-pnl_72, 0) if not np.isnan(pnl_72) else np.nan
                risk_saved_m = abs(min(mae, 0)) if not np.isnan(mae) else np.nan
                save_ratio = (
                    risk_saved_m / alpha_loss if alpha_loss > 0 else np.inf
                ) if not np.isnan(alpha_loss) and not np.isnan(risk_saved_m) else np.nan
                rows.append({
                    "time": ts,
                    "bar_index": idx,
                    "decision_type": "MODIFY",
                    "direction": direction,
                    "regime_id": event.get("regime_id_at_entry"),
                    "actual_outcome_72": pnl_72,
                    "gate_regret": np.nan,
                    "exit_opportunity_cost": np.nan,
                    "exit_risk_saved": np.nan,
                    "modify_alpha_loss": alpha_loss,
                    "modify_save_ratio": save_ratio,
                })

    if unmapped_event_details:
        unmapped_entry = [e for e in unmapped_event_details if e["event_type"] == "ENTRY"]
        unmapped_critical = [e for e in unmapped_event_details if e["event_type"] in ("EXIT", "MODIFY")]
        if unmapped_entry:
            print(f"  Warning: {len(unmapped_entry)} ENTRY events could not be mapped to bar indices")
        if unmapped_critical:
            print(f"  FATAL: {len(unmapped_critical)} EXIT/MODIFY events unmapped")

    # --- NO_EXIT: bars where exit was pending but did not occur ---
    # Detected via pending_exit_reason in Step21 bar_log tail columns.
    # Build active trade direction per bar index from trade lifecycle.
    active_direction = {}
    if not trade_log_df.empty and "event_type" in trade_log_df.columns:
        tl_entries = trade_log_df[trade_log_df["event_type"] == "ENTRY"]
        tl_exits = trade_log_df[trade_log_df["event_type"] == "EXIT"]
        exit_bar_map = {}
        for _, ex in tl_exits.iterrows():
            tid = ex.get("trade_id")
            ts_ex = ex.get("timestamp")
            if pd.notna(ts_ex) and tid:
                ex_idx = time_to_idx.get(floor_to_m5(ts_ex))
                if ex_idx is not None:
                    exit_bar_map[tid] = ex_idx
        for _, entry in tl_entries.iterrows():
            tid = entry.get("trade_id")
            dir_e = entry.get("direction", "LONG")
            ts_e = entry.get("timestamp")
            if pd.notna(ts_e) and tid:
                en_idx = time_to_idx.get(floor_to_m5(ts_e))
                if en_idx is not None:
                    end_idx = exit_bar_map.get(tid, len(bars_df) - 1)
                    for bi in range(en_idx, end_idx + 1):
                        active_direction[bi] = dir_e

    unresolved_no_exit = []
    if "pending_exit_reason" in bars_df.columns and "has_position" in bars_df.columns:
        no_exit_bars = bars_df[
            (bars_df["has_position"] == 1) &
            (bars_df["pending_exit_reason"].notna()) &
            (bars_df["pending_exit_reason"] != "")
        ]
        for idx, bar in no_exit_bars.iterrows():
            if idx in exit_bar_indices:
                continue  # actual exit happened here
            direction = active_direction.get(idx)
            if direction is None:
                direction = "UNRESOLVED"
                unresolved_no_exit.append(int(idx))
            pnl_72, mae, mfe = compute_forward_metrics(bars_df, idx, direction, h)
            opp_cost = max(pnl_72, 0) if not np.isnan(pnl_72) else np.nan
            risk_saved = abs(min(mae, 0)) if not np.isnan(mae) else np.nan
            rows.append({
                "time": bar.get("time"),
                "bar_index": idx,
                "decision_type": "NO_EXIT",
                "direction": direction,
                "regime_id": bar.get("regime_id"),
                "actual_outcome_72": pnl_72,
                "gate_regret": np.nan,
                "exit_opportunity_cost": opp_cost,
                "exit_risk_saved": risk_saved,
                "modify_alpha_loss": np.nan,
                "modify_save_ratio": np.nan,
            })

    if unresolved_no_exit:
        print(f"  FATAL: {len(unresolved_no_exit)} NO_EXIT bars with unresolved direction")

    result_df = pd.DataFrame(rows) if rows else pd.DataFrame()
    coverage_info = {
        "unmapped_event_details": unmapped_event_details,
        "unresolved_no_exit": unresolved_no_exit,
        "exit_reason_available": exit_reason_available,
        "has_exit_reason_col": has_exit_reason_col,
    }
    return result_df, coverage_info


def _write_coverage_manifest(
    output_dir: Path,
    trade_log_df: pd.DataFrame,
    cf_df: pd.DataFrame,
    unmapped_event_details: list,
    unresolved_no_exit: list,
    exit_reason_available: bool,
    has_exit_reason_col: bool,
) -> dict:
    """Build and write coverage_manifest.json. Returns the manifest dict."""
    # Raw event counts from trade_log
    raw_event_counts = {}
    if not trade_log_df.empty and "event_type" in trade_log_df.columns:
        raw_event_counts = {
            str(k): int(v)
            for k, v in trade_log_df["event_type"].value_counts().items()
        }

    # Mapped event counts from counterfactual_eval
    mapped_event_counts = {}
    if not cf_df.empty and "decision_type" in cf_df.columns:
        mapped_event_counts = {
            str(k): int(v)
            for k, v in cf_df["decision_type"].value_counts().items()
        }

    # Direction distribution
    direction_dist = {}
    if not cf_df.empty and "direction" in cf_df.columns:
        direction_dist = {
            str(k): int(v)
            for k, v in cf_df["direction"].value_counts().items()
        }

    # NO_EXIT stats
    no_exit_rows = cf_df[cf_df["decision_type"] == "NO_EXIT"] if (
        not cf_df.empty and "decision_type" in cf_df.columns
    ) else pd.DataFrame()
    no_exit_total = len(no_exit_rows)
    no_exit_resolved = no_exit_total - len(unresolved_no_exit)

    # Unmapped classification
    unmapped_entry = [e for e in unmapped_event_details if e["event_type"] == "ENTRY"]
    unmapped_exit = [e for e in unmapped_event_details if e["event_type"] == "EXIT"]
    unmapped_modify = [e for e in unmapped_event_details if e["event_type"] == "MODIFY"]

    # Coverage pass gate: EXIT/MODIFY unmapped = 0 AND no unresolved directions
    coverage_pass = (
        len(unmapped_exit) == 0
        and len(unmapped_modify) == 0
        and len(unresolved_no_exit) == 0
    )

    manifest = {
        "raw_event_counts": raw_event_counts,
        "mapped_event_counts": mapped_event_counts,
        "unmapped_events": {
            "total": len(unmapped_event_details),
            "by_type": {
                "ENTRY": len(unmapped_entry),
                "EXIT": len(unmapped_exit),
                "MODIFY": len(unmapped_modify),
            },
            "details": unmapped_event_details,
        },
        "direction_distribution": direction_dist,
        "no_exit_stats": {
            "total": no_exit_total,
            "resolved_direction": no_exit_resolved,
            "unresolved_direction": len(unresolved_no_exit),
        },
        "exit_reason_taxonomy": {
            "exit_reason_column_present": has_exit_reason_col,
            "exit_reason_values_used": exit_reason_available,
        },
        "coverage_pass": coverage_pass,
        "build_timestamp": datetime.now().isoformat(),
    }

    path = output_dir / "coverage_manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Build H=72 counterfactual evaluation table."
    )
    parser.add_argument("parser_dir", type=Path, help="Path to parser_outputs/")
    parser.add_argument("--horizon", type=int, default=H_DEFAULT, help="Forward horizon in bars")
    args = parser.parse_args()

    pdir = args.parser_dir

    # Load data
    bars_path = pdir / "bars_master.parquet"
    if not bars_path.exists():
        bars_path = pdir / "bars_raw.parquet"
    trades_path = pdir / "trades_master.parquet"
    trade_log_path = pdir / "trade_log_parsed.parquet"

    bars_df = pd.read_parquet(bars_path) if bars_path.exists() else pd.DataFrame()
    trades_df = pd.read_parquet(trades_path) if trades_path.exists() else pd.DataFrame()
    trade_log_df = pd.read_parquet(trade_log_path) if trade_log_path.exists() else pd.DataFrame()

    # Build
    cf, coverage_info = build_counterfactual(bars_df, trades_df, trade_log_df, args.horizon)

    if not cf.empty:
        cf.to_parquet(pdir / "counterfactual_eval.parquet", index=False)

    # Write coverage manifest (always, even on failure)
    cov_manifest = _write_coverage_manifest(
        pdir, trade_log_df, cf,
        coverage_info["unmapped_event_details"],
        coverage_info["unresolved_no_exit"],
        coverage_info["exit_reason_available"],
        coverage_info["has_exit_reason_col"],
    )

    # Hard fail if coverage gate fails
    if not cov_manifest["coverage_pass"]:
        print(f"  FATAL: Coverage gate FAIL — see {pdir / 'coverage_manifest.json'}")
        sys.exit(1)

    # Update parse_manifest
    manifest_path = pdir / "parse_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["counterfactual_eval"] = {
        "rows": len(cf),
        "horizon": args.horizon,
        "decision_types": {k: int(v) for k, v in cf["decision_type"].value_counts().items()} if not cf.empty else {},
        "coverage_pass": cov_manifest["coverage_pass"],
        "unmapped_total": cov_manifest["unmapped_events"]["total"],
        "exit_reason_taxonomy_used": cov_manifest["exit_reason_taxonomy"]["exit_reason_values_used"],
        "build_timestamp": datetime.now().isoformat(),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Report
    if not cf.empty:
        print(f"Counterfactual eval: {len(cf)} rows (H={args.horizon})")
        dt_counts = {k: int(v) for k, v in cf["decision_type"].value_counts().items()}
        print(f"  Decision types: {dt_counts}")
        gate_blocks = cf[cf["decision_type"] == "GATE_BLOCK"]
        if not gate_blocks.empty:
            mean_regret = gate_blocks["gate_regret"].mean()
            print(f"  Gate regret mean: {mean_regret:.2f}")
        # Report on all exit types
        exit_types = [v for v in EXIT_REASON_TO_DECISION.values()]
        exits = cf[cf["decision_type"].isin(exit_types)]
        if not exits.empty:
            mean_opp = exits["exit_opportunity_cost"].mean()
            mean_saved = exits["exit_risk_saved"].mean()
            print(f"  Exit opp cost mean: {mean_opp:.2f}, risk saved mean: {mean_saved:.2f}")
    else:
        print("No counterfactual data generated.")


if __name__ == "__main__":
    main()
