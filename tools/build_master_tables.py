"""
build_master_tables.py - Master-table materializer.

Reads parsed outputs from parse_step21_run.py and builds derived tables
per MASTER_TABLE_CONTRACT.md v1.0:
  - trades_master.parquet
  - bars_master.parquet
  - modify_master.parquet
  - execution_master.parquet
  - audit_master.parquet (optional)

Usage:
    python tools/build_master_tables.py <parser_outputs_dir>

Example:
    python tools/build_master_tables.py \
        _coord/campaigns/C2026Q1_stage1_refresh/parser_outputs
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def build_trades_master(trade_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Build paired realized trade ledger. One row per completed trade lifecycle."""
    issues = []

    entries = trade_df[trade_df["event_type"] == "ENTRY"].copy()
    exits = trade_df[trade_df["event_type"] == "EXIT"].copy()
    modifies = trade_df[trade_df["event_type"] == "MODIFY"].copy()

    # Validate: every trade_id has exactly one ENTRY
    entry_counts = entries.groupby("trade_id").size()
    dup_entries = entry_counts[entry_counts > 1]
    if len(dup_entries) > 0:
        issues.append(f"trades_master: {len(dup_entries)} trade_ids with multiple ENTRY rows")

    # Flag EXIT-without-ENTRY anomalies (contract line 60)
    entry_tids = set(entries["trade_id"].unique())
    exit_tids = set(exits["trade_id"].unique())
    orphan_exits = exit_tids - entry_tids
    if orphan_exits:
        issues.append(f"trades_master: {len(orphan_exits)} EXIT rows without matching ENTRY (orphan trade_ids: {sorted(orphan_exits)[:5]}...)")

    # Aggregate modify info per trade
    modify_agg = pd.DataFrame()
    if not modifies.empty:
        modify_agg = modifies.groupby("trade_id").agg(
            modify_count_total=("modify_count", "max"),
            modify_reasons=("modify_reason", lambda x: ",".join(sorted(set(x.dropna())))),
        )

    # Pair ENTRY with EXIT using merge (not join, to avoid cartesian product)
    entries_renamed = entries.rename(columns={
        "timestamp": "entry_time",
        "sl_price": "sl_price_entry",
        "tp_price": "tp_price_entry",
    })

    exit_cols = ["trade_id", "timestamp", "exit_price", "pnl", "sl_price", "tp_price",
                 "k_sl_eff", "k_tp_eff", "bars_held", "exit_reason", "tx_authority",
                 "active_model_pack_dir", "runtime_reload_status"]
    exit_subset = exits[[c for c in exit_cols if c in exits.columns]].copy()
    exit_subset = exit_subset.rename(columns={
        "timestamp": "exit_time",
        "exit_price": "exit_price_final",
        "pnl": "pnl_final",
        "sl_price": "sl_price_exit",
        "tp_price": "tp_price_exit",
        "k_sl_eff": "k_sl_eff_exit",
        "k_tp_eff": "k_tp_eff_exit",
        "bars_held": "bars_held_actual",
        "exit_reason": "exit_reason_final",
        "tx_authority": "tx_authority_final",
        "active_model_pack_dir": "active_model_pack_dir_final",
        "runtime_reload_status": "runtime_reload_status_final",
    })

    merged = entries_renamed.merge(exit_subset, on="trade_id", how="left")

    # Add modify aggregates
    if not modify_agg.empty:
        merged = merged.merge(modify_agg, on="trade_id", how="left")
        merged["modify_count_total"] = merged["modify_count_total"].fillna(0).astype(int)
        merged["modify_reasons"] = merged["modify_reasons"].fillna("")
    else:
        merged["modify_count_total"] = 0
        merged["modify_reasons"] = ""

    # Select and rename columns per contract
    result_cols = {
        "trade_id": "trade_id",
        "position_id": "position_id",
        "entry_time": "entry_time",
        "exit_time": "exit_time",
        "symbol": "symbol",
        "direction": "direction",
        "lot": "lot",
        "entry_price": "entry_price",
        "exit_price_final": "exit_price",
        "sl_price_entry": "sl_price",
        "tp_price_entry": "tp_price",
        "pnl_final": "pnl",
        "k_sl_req": "k_sl_req",
        "k_tp_req": "k_tp_req",
        "k_sl_eff_exit": "k_sl_eff",
        "k_tp_eff_exit": "k_tp_eff",
        "hold_bars": "hold_bars",
        "bars_held_actual": "bars_held",
        "exit_reason_final": "exit_reason",
        "regime_id_at_entry": "regime_id_at_entry",
        "spread_atr_at_entry": "spread_atr_at_entry",
        "flip_used": "flip_used",
        "model_pack_version": "model_pack_version",
        "clf_version": "clf_version",
        "prm_version": "prm_version",
        "cost_model_version": "cost_model_version",
        "modify_count_total": "modify_count",
        "modify_reasons": "modify_reasons",
        "tx_authority_final": "tx_authority",
        "pack_dir_at_entry": "pack_dir_at_entry",
        "active_model_pack_dir_final": "active_model_pack_dir",
        "runtime_reload_status_final": "runtime_reload_status",
    }

    available = {k: v for k, v in result_cols.items() if k in merged.columns}
    result = merged[list(available.keys())].rename(columns=available)
    result = result.reset_index(drop=True)

    # Validation: exit_time > entry_time for completed trades
    completed = result.dropna(subset=["exit_time"])
    if not completed.empty and "entry_time" in completed.columns and "exit_time" in completed.columns:
        bad_order = completed[completed["exit_time"] <= completed["entry_time"]]
        if len(bad_order) > 0:
            issues.append(f"trades_master: {len(bad_order)} trades with exit_time <= entry_time")

    # Flag open trades (informational, not an error)
    open_trades = result[result["exit_time"].isna()]

    return result, issues


def build_bars_master(bar_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Build full bar-level snapshot. One row per bar."""
    issues = []
    if bar_df.empty:
        return pd.DataFrame(), ["bars_master: no bar data"]

    result = bar_df.copy()

    # Validate time monotonicity
    if "time" in result.columns:
        times = result["time"].tolist()
        non_monotonic = sum(1 for i in range(1, len(times)) if times[i] <= times[i - 1])
        if non_monotonic > 0:
            issues.append(f"bars_master: {non_monotonic} non-monotonic time entries")

    # Validate schema_version and log_schema_version consistency (contract line 87)
    for vcol in ["schema_version", "log_schema_version"]:
        if vcol in result.columns:
            versions = result[vcol].dropna().unique()
            if len(versions) > 1:
                issues.append(f"bars_master: inconsistent {vcol} values: {list(versions)}")

    return result, issues


def build_modify_master(trade_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Build protective management ledger from MODIFY rows. Returns (df, issues, warnings)."""
    issues = []
    warnings = []
    modifies = trade_df[trade_df["event_type"] == "MODIFY"].copy()

    if modifies.empty:
        return pd.DataFrame(), [], []

    # Select columns per contract
    keep_cols = [
        "trade_id", "timestamp", "position_id", "modify_reason", "modify_count",
        "sl_price", "tp_price", "k_sl_eff", "k_tp_eff", "bars_held", "tx_authority",
    ]
    available = [c for c in keep_cols if c in modifies.columns]
    result = modifies[available].reset_index(drop=True)

    # Validate: modify_count monotonically non-decreasing per trade_id
    if "modify_count" in result.columns and "trade_id" in result.columns:
        for tid, group in result.groupby("trade_id"):
            counts = group["modify_count"].tolist()
            for i in range(1, len(counts)):
                if counts[i] < counts[i - 1]:
                    issues.append(
                        f"modify_master: non-monotonic modify_count for trade_id={tid}"
                    )
                    break

    # Validate: close-before-modify precedence (contract line 111)
    # No MODIFY row should exist for a bar that also has an EXIT for the same trade_id.
    # This is a data quality warning, not a structural error.
    if "trade_id" in result.columns and "timestamp" in result.columns:
        exits_df = trade_df[trade_df["event_type"] == "EXIT"]
        if not exits_df.empty and "timestamp" in exits_df.columns:
            exit_keys = set(
                zip(exits_df["trade_id"], exits_df["timestamp"])
            )
            modify_keys = set(
                zip(result["trade_id"], result["timestamp"])
            )
            overlap = exit_keys & modify_keys
            if overlap:
                warnings.append(
                    f"modify_master: {len(overlap)} MODIFY rows share timestamp with EXIT for same trade_id (close-before-modify violation)"
                )

    return result, issues, warnings


def build_execution_master(trade_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Build request/execution/recovery layer. One row per trade_log event."""
    issues = []
    if trade_df.empty:
        return pd.DataFrame(), ["execution_master: no trade data"]

    result = trade_df.copy()
    result["event_order"] = range(len(result))

    # Assign lifecycle_id by trade_id
    if "trade_id" in result.columns:
        tid_map = {tid: i for i, tid in enumerate(result["trade_id"].unique())}
        result["lifecycle_id"] = result["trade_id"].map(tid_map)

    # Validate timestamp monotonicity (contract line 131)
    if "timestamp" in result.columns:
        ts_list = result["timestamp"].tolist()
        non_monotonic = sum(1 for i in range(1, len(ts_list))
                           if pd.notna(ts_list[i]) and pd.notna(ts_list[i-1])
                           and str(ts_list[i]) < str(ts_list[i-1]))
        if non_monotonic > 0:
            issues.append(f"execution_master: {non_monotonic} non-monotonic timestamp entries")

    # Validate event sequence per trade_id: ENTRY -> [MODIFY]* -> EXIT (contract line 132)
    if "trade_id" in result.columns and "event_type" in result.columns:
        for tid, group in result.groupby("trade_id"):
            events = group["event_type"].tolist()
            if not events:
                continue
            if events[0] != "ENTRY":
                issues.append(f"execution_master: trade_id={tid} does not start with ENTRY")
            # Middle events must all be MODIFY
            for i, e in enumerate(events[1:-1], start=1):
                if e != "MODIFY":
                    issues.append(
                        f"execution_master: trade_id={tid} has {e} at position {i} (expected MODIFY)"
                    )
                    break
            if len(events) > 1 and events[-1] not in ("EXIT", "MODIFY"):
                issues.append(f"execution_master: trade_id={tid} ends with unexpected {events[-1]}")

    return result, issues


def build_audit_master(audit_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Build broker audit trail with sequential counter."""
    if audit_df.empty:
        return pd.DataFrame(), []
    result = audit_df.copy()
    result["event_order"] = range(len(result))
    return result, []


def main():
    parser = argparse.ArgumentParser(
        description="Build master tables from parsed Step21 outputs."
    )
    parser.add_argument("parser_dir", type=Path, help="Path to parser_outputs/")
    args = parser.parse_args()

    pdir = args.parser_dir
    all_issues = []
    all_warnings = []

    # Load parsed data
    trade_path = pdir / "trade_log_parsed.parquet"
    bar_path = pdir / "bars_raw.parquet"
    audit_path = pdir / "broker_audit_parsed.parquet"

    trade_df = pd.read_parquet(trade_path) if trade_path.exists() else pd.DataFrame()
    bar_df = pd.read_parquet(bar_path) if bar_path.exists() else pd.DataFrame()
    audit_df = pd.read_parquet(audit_path) if audit_path.exists() else pd.DataFrame()

    # Build each master table
    trades_master, ti = build_trades_master(trade_df)
    all_issues.extend(ti)
    if not trades_master.empty:
        trades_master.to_parquet(pdir / "trades_master.parquet", index=False)

    bars_master, bi = build_bars_master(bar_df)
    all_issues.extend(bi)
    if not bars_master.empty:
        bars_master.to_parquet(pdir / "bars_master.parquet", index=False)

    modify_master, mi, mw = build_modify_master(trade_df)
    all_issues.extend(mi)
    all_warnings.extend(mw)
    if not modify_master.empty:
        modify_master.to_parquet(pdir / "modify_master.parquet", index=False)

    exec_master, ei = build_execution_master(trade_df)
    all_issues.extend(ei)
    if not exec_master.empty:
        exec_master.to_parquet(pdir / "execution_master.parquet", index=False)

    audit_master, ai = build_audit_master(audit_df)
    all_issues.extend(ai)
    if not audit_master.empty:
        audit_master.to_parquet(pdir / "audit_master.parquet", index=False)

    # Update parse_manifest
    manifest_path = pdir / "parse_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["master_tables"] = {
        "trades_master": len(trades_master),
        "bars_master": len(bars_master),
        "modify_master": len(modify_master),
        "execution_master": len(exec_master),
        "audit_master": len(audit_master),
    }
    manifest["master_table_issues"] = all_issues
    manifest["master_table_warnings"] = all_warnings
    manifest["master_tables_pass"] = len(all_issues) == 0
    manifest["master_table_build_timestamp"] = datetime.now().isoformat()

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Report
    print(f"Built: trades={len(trades_master)}, bars={len(bars_master)}, "
          f"modify={len(modify_master)}, exec={len(exec_master)}, audit={len(audit_master)}")
    if all_warnings:
        print(f"\n{len(all_warnings)} warning(s):")
        for w in all_warnings:
            print(f"  [WARN] {w}")
    if all_issues:
        print(f"\n{len(all_issues)} error(s):")
        for issue in all_issues:
            print(f"  [ERROR] {issue}")
        sys.exit(1)
    else:
        print("All master table validations passed.")


if __name__ == "__main__":
    main()
