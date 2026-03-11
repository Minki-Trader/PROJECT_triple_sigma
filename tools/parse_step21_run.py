"""
parse_step21_run.py - Step21 raw-run parser and schema validator.

Reads raw tester outputs (trade_log.csv, bar_log_*.csv, broker_audit.csv)
from a campaign's raw_tester_outputs/ directory, validates schema against
BAR_LOG_SCHEMA v2.0, and emits a parse_manifest.json with validation results.

Usage:
    python tools/parse_step21_run.py <raw_dir> <output_dir>

Example:
    python tools/parse_step21_run.py \
        _coord/campaigns/C2026Q1_stage1_refresh/raw_tester_outputs \
        _coord/campaigns/C2026Q1_stage1_refresh/parser_outputs
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Schema definitions (BAR_LOG_SCHEMA v2.0)
# ---------------------------------------------------------------------------

TRADE_LOG_COLUMNS = [
    "trade_id", "timestamp", "symbol", "event_type", "direction", "lot",
    "entry_price", "exit_price", "sl_price", "tp_price", "pnl",
    "k_sl_req", "k_tp_req", "k_sl_eff", "k_tp_eff", "hold_bars", "bars_held",
    "exit_reason", "regime_id_at_entry", "spread_atr_at_entry", "flip_used",
    "model_pack_version", "clf_version", "prm_version", "cost_model_version",
    "event_detail", "deal_ticket", "position_id", "modify_reason",
    "modify_count", "tx_authority", "pack_dir_at_entry",
    "active_model_pack_dir", "runtime_reload_status", "ea_version",
    "log_schema_version",
]

BAR_LOG_CORE_COLUMNS = [
    "time", "symbol", "timeframe", "price_basis", "open", "high", "low",
    "close", "spread_points", "atr14", "adx14", "atr_pct", "regime_id",
    "cand_long", "cand_short", "entry_allowed",
]

BAR_LOG_FEATURE_COLUMNS = [f"feature_{i}" for i in range(22)]

BAR_LOG_STAGE1_COLUMNS = ["onnx_p_long", "onnx_p_short", "onnx_p_pass", "stage1_argmax"]

BAR_LOG_STAGE2_COLUMNS = [
    "prm_raw_0", "prm_raw_1", "prm_raw_2", "prm_raw_3", "prm_raw_4",
    "prm_raw_5", "final_dir", "flip_used", "k_sl_req", "k_tp_req",
    "k_sl_eff", "k_tp_eff", "hold_bars",
]

BAR_LOG_GATE_COLUMNS = [
    "gate_pass", "gate_reject_reason", "dyn_spread_atr_max", "dyn_dev_points",
    "risk_pct", "dist_atr", "dist_atr_max_t", "dist_atr_max_mode",
    "has_position", "bars_held",
]

BAR_LOG_VERSION_COLUMNS = [
    "ea_version", "schema_version", "candidate_policy_version",
    "regime_policy_version", "model_pack_version", "clf_version",
    "prm_version", "cost_model_version",
]

# Step21 bar_log may have additional tail columns (optional)
BAR_LOG_STEP21_TAIL = [
    "pending_exit_reason", "pending_modify_reason", "last_modify_reason",
    "modify_count", "be_applied", "entry_log_emitted", "tx_authority_enabled",
    "broker_audit_enabled", "active_model_pack_dir", "pack_dir_at_entry",
    "runtime_reload_attempts", "runtime_reload_successes",
    "runtime_reload_rollbacks", "runtime_reload_status", "log_schema_version",
]

BAR_LOG_REQUIRED = (
    BAR_LOG_CORE_COLUMNS + BAR_LOG_FEATURE_COLUMNS +
    BAR_LOG_STAGE1_COLUMNS + BAR_LOG_STAGE2_COLUMNS +
    BAR_LOG_GATE_COLUMNS + BAR_LOG_VERSION_COLUMNS
)

BROKER_AUDIT_COLUMNS = [
    "timestamp", "symbol", "tag", "detail", "trade_id", "position_id",
    "pending_exit_reason", "pending_modify_reason", "modify_count",
    "active_model_pack_dir", "pack_dir_at_entry", "tx_authority_enabled",
    "runtime_reload_status", "account_login", "account_server",
    "ea_version", "log_schema_version",
]

VALID_EVENT_TYPES = {"ENTRY", "EXIT", "MODIFY"}
VALID_MODIFY_REASONS = {"BREAK_EVEN", "TRAILING", "TP_RESHAPE", "TIME_POLICY", ""}
VALID_TX_AUTHORITY = {"TX_DEAL", "TX_POSITION", "SYNC_POSITION", "TX_OR_SYNC", ""}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def find_files(raw_dir: Path):
    """Locate trade_log, bar_log files, and optional broker_audit."""
    trade_log = raw_dir / "trade_log.csv"
    bar_logs = sorted(raw_dir.glob("bar_log_*.csv"))
    broker_audit = raw_dir / "broker_audit.csv"
    return trade_log, bar_logs, broker_audit


def validate_columns(df: pd.DataFrame, expected: list[str], file_label: str) -> list[str]:
    """Check that all expected columns exist. Return list of issues."""
    issues = []
    actual = set(df.columns)
    missing = [c for c in expected if c not in actual]
    if missing:
        issues.append(f"{file_label}: missing columns: {missing}")
    return issues


def parse_trade_log(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Parse trade_log.csv and validate schema."""
    issues = []
    if not path.exists():
        return pd.DataFrame(), [f"trade_log.csv not found at {path}"]

    df = pd.read_csv(path, dtype=str)
    issues.extend(validate_columns(df, TRADE_LOG_COLUMNS, "trade_log"))

    # Type conversions
    for col in ["lot", "entry_price", "exit_price", "sl_price", "tp_price",
                 "pnl", "k_sl_req", "k_tp_req", "k_sl_eff", "k_tp_eff",
                 "spread_atr_at_entry"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["hold_bars", "bars_held", "regime_id_at_entry",
                 "deal_ticket", "position_id", "modify_count", "flip_used"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Validate event_type values
    if "event_type" in df.columns:
        bad = set(df["event_type"].dropna().unique()) - VALID_EVENT_TYPES
        if bad:
            issues.append(f"trade_log: unexpected event_type values: {bad}")

    # Validate modify_reason values
    if "modify_reason" in df.columns:
        reasons = set(df["modify_reason"].fillna("").unique())
        bad = reasons - VALID_MODIFY_REASONS
        if bad:
            issues.append(f"trade_log: unexpected modify_reason values: {bad}")

    # Validate tx_authority values
    if "tx_authority" in df.columns:
        tx_values = set(df["tx_authority"].fillna("").unique())
        bad_tx = tx_values - VALID_TX_AUTHORITY
        if bad_tx:
            issues.append(f"trade_log: unexpected tx_authority values: {bad_tx}")

    # Enforce tx_authority presence for schema v2.0
    if "log_schema_version" in df.columns:
        versions = df["log_schema_version"].dropna().unique()
        if len(versions) == 1 and str(versions[0]) == "2.0":
            if "tx_authority" not in df.columns:
                issues.append(
                    "trade_log: log_schema_version=2.0 but tx_authority column missing"
                )

    # Validate trade_id format (TS_XXXXX)
    if "trade_id" in df.columns:
        import re
        tid_pattern = re.compile(r"^TS_\d{5}$")
        invalid_tids = df["trade_id"].dropna()[
            ~df["trade_id"].dropna().apply(lambda x: bool(tid_pattern.match(str(x))))
        ]
        if len(invalid_tids) > 0:
            samples = invalid_tids.head(3).tolist()
            issues.append(f"trade_log: {len(invalid_tids)} trade_id values not matching TS_XXXXX format (samples: {samples})")

    # Validate log_schema_version consistency
    if "log_schema_version" in df.columns:
        versions = df["log_schema_version"].dropna().unique()
        if len(versions) > 1:
            issues.append(f"trade_log: inconsistent log_schema_version values: {list(versions)}")

    return df, issues


def parse_bar_logs(paths: list[Path]) -> tuple[pd.DataFrame, list[str], str | None]:
    """Parse and concatenate all bar_log_YYYYMMDD.csv files.

    Returns (combined_df, issues, detected_schema_version).
    """
    issues = []
    detected_schema_version = None
    if not paths:
        return pd.DataFrame(), ["No bar_log_*.csv files found"], None

    frames = []
    for p in paths:
        df = pd.read_csv(p, dtype=str)
        # Extract date from filename
        date_str = p.stem.replace("bar_log_", "")
        df["date"] = date_str
        if frames:
            # Check column consistency
            if set(df.columns) != set(frames[0].columns):
                issues.append(
                    f"bar_log column mismatch: {p.name} vs {paths[0].name}"
                )
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined["bar_index"] = range(len(combined))

    # Validate required columns (step21 tail is optional)
    issues.extend(validate_columns(combined, BAR_LOG_REQUIRED, "bar_log"))

    # Type conversions for numeric columns
    numeric_cols = (
        ["open", "high", "low", "close", "spread_points", "atr14", "adx14",
         "atr_pct", "regime_id", "cand_long", "cand_short", "entry_allowed"]
        + BAR_LOG_FEATURE_COLUMNS
        + ["onnx_p_long", "onnx_p_short", "onnx_p_pass"]
        + [f"prm_raw_{i}" for i in range(6)]
        + ["k_sl_req", "k_tp_req", "k_sl_eff", "k_tp_eff", "hold_bars",
           "gate_pass", "dyn_spread_atr_max", "dyn_dev_points", "risk_pct",
           "dist_atr", "dist_atr_max_t", "has_position", "bars_held"]
    )
    for col in numeric_cols:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Validate schema_version and log_schema_version consistency across all rows
    for vcol in ["schema_version", "log_schema_version"]:
        if vcol in combined.columns:
            versions = combined[vcol].dropna().unique()
            if len(versions) > 1:
                issues.append(f"bar_log: inconsistent {vcol} values: {list(versions)}")

    # Detect schema version for Step21 enforcement
    for vcol in ["log_schema_version", "schema_version"]:
        if detected_schema_version is None and vcol in combined.columns:
            sv = combined[vcol].dropna().unique()
            if len(sv) == 1:
                detected_schema_version = str(sv[0])

    # Step21 conditional enforcement: v2.0 requires tail columns
    if detected_schema_version == "2.0":
        step21_missing = validate_columns(
            combined, BAR_LOG_STEP21_TAIL, "bar_log[step21_v2.0]"
        )
        if step21_missing:
            issues.extend(step21_missing)
            issues.append(
                "bar_log: schema_version=2.0 detected but Step21 tail columns missing"
            )

    return combined, issues, detected_schema_version


def parse_broker_audit(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Parse broker_audit.csv if present."""
    issues = []
    if not path.exists():
        return pd.DataFrame(), []  # Optional file

    df = pd.read_csv(path, dtype=str)
    issues.extend(validate_columns(df, BROKER_AUDIT_COLUMNS, "broker_audit"))
    return df, issues


# ---------------------------------------------------------------------------
# Invariant checks (from STEP21_CLOSEOUT_AND_VERIFICATION.md)
# ---------------------------------------------------------------------------

def check_invariants(trade_df: pd.DataFrame) -> list[str]:
    """Run Step21 runtime invariants on trade_log data."""
    issues = []
    if trade_df.empty:
        return ["trade_log is empty - cannot check invariants"]

    # 1. Duplicate non-modify (trade_id, event_type) groups
    non_modify = trade_df[trade_df["event_type"] != "MODIFY"]
    dup_groups = non_modify.groupby(["trade_id", "event_type"]).size()
    dup_count = (dup_groups > 1).sum()
    if dup_count > 0:
        issues.append(f"INVARIANT FAIL: duplicate non-modify (trade_id, event_type) groups = {dup_count}")

    # 2. Duplicate EXIT groups
    exits = trade_df[trade_df["event_type"] == "EXIT"]
    dup_exits = exits.groupby("trade_id").size()
    dup_exit_count = (dup_exits > 1).sum()
    if dup_exit_count > 0:
        issues.append(f"INVARIANT FAIL: duplicate EXIT groups = {dup_exit_count}")

    # 3. Same-timestamp EXIT -> ENTRY
    if "timestamp" in trade_df.columns:
        exit_ts = set(
            trade_df.loc[trade_df["event_type"] == "EXIT", "timestamp"].dropna()
        )
        entry_ts = set(
            trade_df.loc[trade_df["event_type"] == "ENTRY", "timestamp"].dropna()
        )
        same_ts = exit_ts & entry_ts
        if same_ts:
            issues.append(
                f"INVARIANT FAIL: same-timestamp EXIT->ENTRY = {len(same_ts)}"
            )

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse Step21 raw backtest outputs and validate schema."
    )
    parser.add_argument("raw_dir", type=Path, help="Path to raw_tester_outputs/")
    parser.add_argument("output_dir", type=Path, help="Path to parser_outputs/")
    args = parser.parse_args()

    raw_dir = args.raw_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    all_issues = []
    manifest = {
        "parser_version": "1.0",
        "parse_timestamp": datetime.now().isoformat(),
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "files_parsed": {},
        "schema_version": "2.0",
        "contract_version": "1.0",
    }

    # --- Parse trade_log ---
    trade_path, bar_paths, audit_path = find_files(raw_dir)

    trade_df, trade_issues = parse_trade_log(trade_path)
    all_issues.extend(trade_issues)
    if not trade_df.empty:
        manifest["files_parsed"]["trade_log"] = {
            "rows": len(trade_df),
            "columns": len(trade_df.columns),
            "entry_count": int((trade_df["event_type"] == "ENTRY").sum()),
            "exit_count": int((trade_df["event_type"] == "EXIT").sum()),
            "modify_count": int((trade_df["event_type"] == "MODIFY").sum()),
        }

    # --- Parse bar_logs ---
    bar_df, bar_issues, detected_schema_version = parse_bar_logs(bar_paths)
    all_issues.extend(bar_issues)
    if not bar_df.empty:
        manifest["files_parsed"]["bar_log"] = {
            "files": len(bar_paths),
            "total_rows": len(bar_df),
            "columns": len(bar_df.columns),
        }

    # --- Parse broker_audit ---
    audit_df, audit_issues = parse_broker_audit(audit_path)
    all_issues.extend(audit_issues)
    if not audit_df.empty:
        manifest["files_parsed"]["broker_audit"] = {
            "rows": len(audit_df),
            "columns": len(audit_df.columns),
        }

    # --- Invariant checks ---
    invariant_issues = check_invariants(trade_df)
    all_issues.extend(invariant_issues)

    # --- Save parsed dataframes ---
    if not trade_df.empty:
        trade_df.to_parquet(output_dir / "trade_log_parsed.parquet", index=False)
    if not bar_df.empty:
        bar_df.to_parquet(output_dir / "bars_raw.parquet", index=False)
    if not audit_df.empty:
        audit_df.to_parquet(output_dir / "broker_audit_parsed.parquet", index=False)

    # --- Step21 enforcement ---
    manifest["step21_enforcement"] = {
        "detected_schema_version": detected_schema_version,
        "step21_tail_enforced": detected_schema_version == "2.0",
        "tx_authority_validated": True,
    }

    # --- Manifest ---
    manifest["issues"] = all_issues
    manifest["invariant_issues"] = invariant_issues
    manifest["pass"] = len(all_issues) == 0
    manifest["invariants_pass"] = len(invariant_issues) == 0

    manifest_path = output_dir / "parse_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # --- Report ---
    print(f"Parsed: trade_log={len(trade_df)}, bar_log={len(bar_df)}, audit={len(audit_df)} rows")
    if all_issues:
        print(f"\n{len(all_issues)} issue(s) found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("All schema and invariant checks passed.")


if __name__ == "__main__":
    main()
