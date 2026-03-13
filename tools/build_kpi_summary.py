"""
build_kpi_summary.py - WF4 KPI packet builder.

Reads a campaign-native run directory and produces a machine-readable
summary in 40_kpi/kpi_summary.json for branch routing and governance.

Usage:
    python tools/build_kpi_summary.py <run_dir>
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _validate_against_schema(data: dict, schema_path: Path) -> list[str]:
    import jsonschema

    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda err: list(err.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def _safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value):
    if value is None:
        return None
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    try:
        if pd.isna(value):
            return None
        value = float(value)
    except (TypeError, ValueError):
        return None
    if np.isinf(value) or np.isnan(value):
        return None
    return value


def _series_or_default(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def _profit_factor(pnl: pd.Series):
    pnl = pd.to_numeric(pnl, errors="coerce").dropna()
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = _safe_float(wins.sum())
    gross_loss = abs(_safe_float(losses.sum()))
    if gross_loss > 0:
        return gross_profit / gross_loss
    if gross_profit > 0:
        return np.inf
    return 0.0


def _payoff_ratio(pnl: pd.Series):
    pnl = pd.to_numeric(pnl, errors="coerce").dropna()
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    if wins.empty or losses.empty:
        return None
    return _optional_float(wins.mean() / abs(losses.mean()))


def _describe_tail(series: pd.Series) -> dict:
    if series.empty:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p90": 0.0,
            "positive_rate": 0.0,
        }
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p90": 0.0,
            "positive_rate": 0.0,
        }
    return {
        "mean": _safe_float(numeric.mean()),
        "median": _safe_float(numeric.median()),
        "p90": _safe_float(numeric.quantile(0.90)),
        "positive_rate": _safe_float((numeric > 0).mean()),
    }


def _compute_stage1_signal_metrics(bars_df: pd.DataFrame) -> dict:
    if bars_df.empty:
        return {
            "candidate_bar_count": 0,
            "candidate_long_count": 0,
            "candidate_short_count": 0,
            "entry_allowed_rate_candidate": 0.0,
            "gate_pass_rate_candidate": 0.0,
            "candidate_margin_mean": 0.0,
            "candidate_margin_p10": 0.0,
            "candidate_p_long_mean": 0.0,
            "candidate_p_short_mean": 0.0,
            "candidate_p_pass_mean": 0.0,
        }

    working = bars_df.copy()
    candidate_mask = (
        (_series_or_default(working, "cand_long") == 1)
        | (_series_or_default(working, "cand_short") == 1)
    )
    candidate = working[candidate_mask].copy()

    if candidate.empty:
        return {
            "candidate_bar_count": 0,
            "candidate_long_count": 0,
            "candidate_short_count": 0,
            "entry_allowed_rate_candidate": 0.0,
            "gate_pass_rate_candidate": 0.0,
            "candidate_margin_mean": 0.0,
            "candidate_margin_p10": 0.0,
            "candidate_p_long_mean": 0.0,
            "candidate_p_short_mean": 0.0,
            "candidate_p_pass_mean": 0.0,
        }

    probs = np.column_stack([
        _series_or_default(candidate, "onnx_p_long").to_numpy(dtype=float),
        _series_or_default(candidate, "onnx_p_short").to_numpy(dtype=float),
        _series_or_default(candidate, "onnx_p_pass").to_numpy(dtype=float),
    ])
    ordered = np.sort(probs, axis=1)
    margins = ordered[:, -1] - ordered[:, -2]

    return {
        "candidate_bar_count": int(len(candidate)),
        "candidate_long_count": int((_series_or_default(candidate, "cand_long") == 1).sum()),
        "candidate_short_count": int((_series_or_default(candidate, "cand_short") == 1).sum()),
        "entry_allowed_rate_candidate": _safe_float(_series_or_default(candidate, "entry_allowed").mean()),
        "gate_pass_rate_candidate": _safe_float(_series_or_default(candidate, "gate_pass").mean()),
        "candidate_margin_mean": _safe_float(np.mean(margins)),
        "candidate_margin_p10": _safe_float(np.quantile(margins, 0.10)),
        "candidate_p_long_mean": _safe_float(_series_or_default(candidate, "onnx_p_long").mean()),
        "candidate_p_short_mean": _safe_float(_series_or_default(candidate, "onnx_p_short").mean()),
        "candidate_p_pass_mean": _safe_float(_series_or_default(candidate, "onnx_p_pass").mean()),
    }


def _compute_direction_breakdown(trades_df: pd.DataFrame) -> dict:
    breakdown = {}
    for direction, group in trades_df.groupby("direction"):
        pnl = pd.to_numeric(group["pnl"], errors="coerce").dropna()
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        breakdown[str(direction)] = {
            "trades": int(len(pnl)),
            "net_pnl": _safe_float(pnl.sum()),
            "profit_factor": _optional_float(_profit_factor(pnl)),
            "win_rate": _safe_float((pnl > 0).mean()),
            "mean_pnl": _safe_float(pnl.mean()),
            "median_pnl": _safe_float(pnl.median()),
            "gross_profit": _safe_float(wins.sum()),
            "gross_loss": abs(_safe_float(losses.sum())),
        }
    return breakdown


def _compute_trade_metrics(trades_df: pd.DataFrame) -> dict:
    closed = trades_df.copy()
    closed["pnl"] = pd.to_numeric(closed["pnl"], errors="coerce")
    closed = closed.dropna(subset=["pnl"])

    pnl = closed["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    bars_held = pd.to_numeric(closed.get("bars_held"), errors="coerce").dropna()

    exit_reason_counts = {}
    if "exit_reason" in closed.columns:
        exit_reason_counts = {
            str(key): int(value)
            for key, value in closed["exit_reason"].value_counts().items()
        }

    return {
        "total_trades": int(len(closed)),
        "winning_trades": int((pnl > 0).sum()),
        "losing_trades": int((pnl < 0).sum()),
        "total_pnl": _safe_float(pnl.sum()),
        "gross_profit": _safe_float(wins.sum()),
        "gross_loss": abs(_safe_float(losses.sum())),
        "global_profit_factor": _optional_float(_profit_factor(pnl)),
        "global_win_rate": _safe_float((pnl > 0).mean()),
        "payoff_ratio": _payoff_ratio(pnl),
        "expectancy_per_trade": _safe_float(pnl.mean()),
        "median_trade_pnl": _safe_float(pnl.median()),
        "p90_trade_pnl": _safe_float(pnl.quantile(0.90)) if not pnl.empty else 0.0,
        "avg_bars_held": _safe_float(bars_held.mean()),
        "p90_bars_held": _safe_float(bars_held.quantile(0.90)) if not bars_held.empty else 0.0,
        "direction_breakdown": _compute_direction_breakdown(closed),
        "exit_reason_counts": exit_reason_counts,
    }


def _compute_risk_metrics(daily_df: pd.DataFrame, parse_manifest: dict) -> dict:
    if daily_df.empty:
        return {
            "trading_days": 0,
            "max_drawdown_abs": 0.0,
            "max_equity_dd_pct": 0.0,
            "worst_day_net_pnl": 0.0,
            "best_day_net_pnl": 0.0,
            "daily_net_pnl_std": 0.0,
            "avg_daily_profit_factor": 0.0,
            "avg_daily_win_rate": 0.0,
            "ulcer_index": 0.0,
            "concentration_hhi_mean": 0.0,
            "concentration_hhi_p90": 0.0,
            "initial_equity": _safe_float(
                ((parse_manifest.get("daily_risk_metrics") or {}).get("cost_model") or {}).get("initial_equity")
            ),
            "initial_equity_source": (
                ((parse_manifest.get("daily_risk_metrics") or {}).get("cost_model") or {}).get("initial_equity_source")
                or ""
            ),
        }

    equity_dd = pd.to_numeric(daily_df.get("equity_dd_pct"), errors="coerce").fillna(0.0)
    drawdown_sq = np.square(np.minimum(equity_dd.to_numpy(dtype=float), 0.0))
    daily_pf = pd.to_numeric(daily_df.get("profit_factor"), errors="coerce")
    finite_pf = daily_pf[np.isfinite(daily_pf.to_numpy(dtype=float))]
    concentration = pd.to_numeric(daily_df.get("concentration_hhi"), errors="coerce").dropna()
    net_pnl = pd.to_numeric(daily_df.get("net_pnl"), errors="coerce").fillna(0.0)

    risk_manifest = parse_manifest.get("daily_risk_metrics", {})
    cost_model = risk_manifest.get("cost_model", {})

    return {
        "trading_days": int(len(daily_df)),
        "max_drawdown_abs": abs(_safe_float(pd.to_numeric(daily_df.get("cumulative_drawdown"), errors="coerce").min())),
        "max_equity_dd_pct": _safe_float(pd.to_numeric(daily_df.get("max_equity_dd_pct"), errors="coerce").min()),
        "worst_day_net_pnl": _safe_float(net_pnl.min()),
        "best_day_net_pnl": _safe_float(net_pnl.max()),
        "daily_net_pnl_std": _safe_float(net_pnl.std(ddof=0)),
        "avg_daily_profit_factor": _safe_float(finite_pf.mean()) if not finite_pf.empty else 0.0,
        "avg_daily_win_rate": _safe_float(pd.to_numeric(daily_df.get("win_rate"), errors="coerce").mean()),
        "ulcer_index": _safe_float(np.sqrt(drawdown_sq.mean())) if len(drawdown_sq) else 0.0,
        "concentration_hhi_mean": _safe_float(concentration.mean()),
        "concentration_hhi_p90": _safe_float(concentration.quantile(0.90)) if not concentration.empty else 0.0,
        "initial_equity": _safe_float(cost_model.get("initial_equity")),
        "initial_equity_source": cost_model.get("initial_equity_source", ""),
    }


def _compute_counterfactual_metrics(cf_df: pd.DataFrame, signal_metrics: dict) -> dict:
    if cf_df.empty:
        return {
            "gate_block_count": 0,
            "gate_block_rate_candidate_bars": 0.0,
            "candidate_conversion_rate": 0.0,
            "gate_regret_mean": 0.0,
            "gate_regret_median": 0.0,
            "gate_regret_p90": 0.0,
            "gate_regret_positive_rate": 0.0,
            "exit_opportunity_cost_mean": 0.0,
            "exit_opportunity_cost_p90": 0.0,
            "exit_risk_saved_mean": 0.0,
            "exit_risk_saved_p90": 0.0,
            "exit_cost_to_risk_ratio": None,
            "no_exit_count": 0,
            "modify_count": 0,
            "modify_alpha_loss_mean": 0.0,
            "modify_save_ratio_mean": None,
            "decision_type_counts": {},
        }

    decision_counts = {
        str(key): int(value)
        for key, value in cf_df["decision_type"].value_counts().items()
    }

    gate_rows = cf_df[cf_df["decision_type"] == "GATE_BLOCK"]
    gate_stats = _describe_tail(gate_rows["gate_regret"]) if not gate_rows.empty else _describe_tail(pd.Series(dtype=float))

    exit_rows = cf_df[cf_df["decision_type"].isin(["EARLY_EXIT", "EXIT_SL", "EXIT_TP", "EXIT_FORCE"])]
    exit_cost_stats = _describe_tail(exit_rows["exit_opportunity_cost"]) if not exit_rows.empty else _describe_tail(pd.Series(dtype=float))
    exit_risk_stats = _describe_tail(exit_rows["exit_risk_saved"]) if not exit_rows.empty else _describe_tail(pd.Series(dtype=float))

    modify_rows = cf_df[cf_df["decision_type"] == "MODIFY"]
    modify_alpha = pd.to_numeric(modify_rows.get("modify_alpha_loss"), errors="coerce").dropna()
    modify_save = pd.to_numeric(modify_rows.get("modify_save_ratio"), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()

    candidate_bar_count = signal_metrics.get("candidate_bar_count", 0)
    entry_count = decision_counts.get("ENTRY", 0)
    gate_block_count = decision_counts.get("GATE_BLOCK", 0)

    exit_cost_to_risk_ratio = None
    if exit_risk_stats["mean"] > 0:
        exit_cost_to_risk_ratio = _optional_float(exit_cost_stats["mean"] / exit_risk_stats["mean"])

    return {
        "gate_block_count": gate_block_count,
        "gate_block_rate_candidate_bars": (
            _safe_float(gate_block_count / candidate_bar_count) if candidate_bar_count > 0 else 0.0
        ),
        "candidate_conversion_rate": (
            _safe_float(entry_count / candidate_bar_count) if candidate_bar_count > 0 else 0.0
        ),
        "gate_regret_mean": gate_stats["mean"],
        "gate_regret_median": gate_stats["median"],
        "gate_regret_p90": gate_stats["p90"],
        "gate_regret_positive_rate": gate_stats["positive_rate"],
        "exit_opportunity_cost_mean": exit_cost_stats["mean"],
        "exit_opportunity_cost_p90": exit_cost_stats["p90"],
        "exit_risk_saved_mean": exit_risk_stats["mean"],
        "exit_risk_saved_p90": exit_risk_stats["p90"],
        "exit_cost_to_risk_ratio": exit_cost_to_risk_ratio,
        "no_exit_count": decision_counts.get("NO_EXIT", 0),
        "modify_count": decision_counts.get("MODIFY", 0),
        "modify_alpha_loss_mean": _safe_float(modify_alpha.mean()),
        "modify_save_ratio_mean": _optional_float(modify_save.mean()) if not modify_save.empty else None,
        "decision_type_counts": decision_counts,
    }


def build_summary(run_dir: Path) -> dict:
    parser_dir = run_dir / "30_parsed"
    kpi_dir = run_dir / "40_kpi"
    kpi_dir.mkdir(parents=True, exist_ok=True)

    run_manifest = _load_json(run_dir / "run_manifest.json")
    parse_manifest = _load_json(parser_dir / "parse_manifest.json")
    validator_path = run_dir / "50_validator" / "validator_report.json"
    validator_report = _load_json(validator_path) if validator_path.exists() else {}

    trades_df = pd.read_parquet(parser_dir / "trades_master.parquet")
    cf_df = pd.read_parquet(parser_dir / "counterfactual_eval.parquet")
    daily_df = pd.read_parquet(parser_dir / "daily_risk_metrics.parquet")
    bars_df = pd.read_parquet(parser_dir / "bars_master.parquet")

    signal_metrics = _compute_stage1_signal_metrics(bars_df)
    trade_metrics = _compute_trade_metrics(trades_df)
    risk_metrics = _compute_risk_metrics(daily_df, parse_manifest)
    counterfactual_metrics = _compute_counterfactual_metrics(cf_df, signal_metrics)

    summary = {
        "schema_version": "1.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": run_manifest.get("campaign_id", ""),
        "run_id": run_manifest.get("run_id", ""),
        "window_alias": run_manifest.get("window_alias", ""),
        "window_from": run_manifest.get("window_from", ""),
        "window_to": run_manifest.get("window_to", ""),
        "pack_id": run_manifest.get("pack_id", ""),
        "source_artifacts": {
            "run_manifest": str(run_dir / "run_manifest.json"),
            "parse_manifest": str(parser_dir / "parse_manifest.json"),
            "trades_master": str(parser_dir / "trades_master.parquet"),
            "bars_master": str(parser_dir / "bars_master.parquet"),
            "counterfactual_eval": str(parser_dir / "counterfactual_eval.parquet"),
            "daily_risk_metrics": str(parser_dir / "daily_risk_metrics.parquet"),
            "validator_report": str(validator_path) if validator_path.exists() else "",
        },
        "admissibility": {
            "validator_verdict": validator_report.get("verdict", "UNKNOWN"),
            "parse_pass": bool(parse_manifest.get("pass", False)),
            "invariants_pass": bool(parse_manifest.get("invariants_pass", False)),
            "master_tables_pass": bool(parse_manifest.get("master_tables_pass", False)),
            "coverage_pass": bool((parse_manifest.get("counterfactual_eval") or {}).get("coverage_pass", False)),
            "window_clipping": parse_manifest.get("window_clipping", {}),
        },
        "portfolio": trade_metrics,
        "risk": risk_metrics,
        "signal": signal_metrics,
        "counterfactual": counterfactual_metrics,
    }

    project_root = run_dir.resolve()
    while project_root.name != "PROJECT_triple_sigma" and project_root.parent != project_root:
        project_root = project_root.parent
    schema_path = project_root / "_coord" / "ops" / "schemas" / "kpi_summary.schema.json"
    schema_errors = _validate_against_schema(summary, schema_path)
    if schema_errors:
        raise ValueError("kpi_summary schema validation failed: " + "; ".join(schema_errors))

    output_path = kpi_dir / "kpi_summary.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Build WF4 KPI summary packet.")
    parser.add_argument("run_dir", type=Path, help="Path to runs/RUN_<ts>/")
    args = parser.parse_args()

    summary = build_summary(args.run_dir)
    print(f"KPI summary: {args.run_dir / '40_kpi' / 'kpi_summary.json'}")
    print(f"  Total PnL:      {summary['portfolio']['total_pnl']:.2f}")
    print(f"  Global PF:      {summary['portfolio']['global_profit_factor'] or 0.0:.2f}")
    print(f"  Global WR:      {summary['portfolio']['global_win_rate']:.2%}")
    print(f"  Max equity DD:  {summary['risk']['max_equity_dd_pct']:.2f}%")
    print(f"  Gate regret:    {summary['counterfactual']['gate_regret_mean']:.2f}")


if __name__ == "__main__":
    main()
