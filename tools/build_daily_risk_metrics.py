"""
build_daily_risk_metrics.py - Daily portfolio/risk ledger builder.

Reads trades_master.parquet and builds daily_risk_metrics.parquet
per MASTER_TABLE_CONTRACT.md v1.0.

Computes per-day:
  - n_trades, n_entries, gross_pnl, net_pnl
  - expectancy_r, profit_factor, payoff_ratio, win_rate
  - max_drawdown_day, cumulative_pnl, cumulative_drawdown
  - long_count, short_count, regime_distribution
  - avg_bars_held, concentration_hhi

Usage:
    python tools/build_daily_risk_metrics.py <parser_outputs_dir>
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def extract_date(ts_str: str) -> str:
    """Extract YYYY.MM.DD from timestamp string."""
    if pd.isna(ts_str):
        return None
    return str(ts_str)[:10]


def compute_hhi(pnl_series: pd.Series) -> float:
    """Compute Herfindahl-Hirschman Index for PnL concentration."""
    if pnl_series.empty or pnl_series.abs().sum() == 0:
        return 0.0
    shares = (pnl_series.abs() / pnl_series.abs().sum()) ** 2
    return float(shares.sum())


def compute_global_trade_metrics(
    trades_df: pd.DataFrame,
    commission_per_lot: float = 0.0,
) -> dict:
    """Compute campaign-level PF/WR from closed trades."""
    closed = trades_df.dropna(subset=["pnl"]).copy()
    if closed.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "global_profit_factor": 0.0,
            "global_win_rate": 0.0,
        }

    pnl_values = pd.to_numeric(closed["pnl"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    if commission_per_lot > 0 and "lot" in closed.columns:
        lot_values = pd.to_numeric(closed["lot"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        pnl_values = pnl_values - (lot_values * commission_per_lot)

    wins = pnl_values[pnl_values > 0]
    losses = pnl_values[pnl_values < 0]
    gross_profit = float(wins.sum()) if len(wins) > 0 else 0.0
    gross_loss = float(abs(losses.sum())) if len(losses) > 0 else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = np.inf
    else:
        profit_factor = 0.0

    return {
        "total_trades": int(len(pnl_values)),
        "winning_trades": int(len(wins)),
        "losing_trades": int(len(losses)),
        "global_profit_factor": float(profit_factor),
        "global_win_rate": float(len(wins) / len(pnl_values)) if len(pnl_values) > 0 else 0.0,
    }


def resolve_initial_equity(parser_dir: Path, explicit_initial_equity: float | None) -> tuple[float, str]:
    """Resolve initial equity from run/campaign provenance when not provided."""
    if explicit_initial_equity is not None:
        return float(explicit_initial_equity), "cli_override"

    run_dir = parser_dir.parent
    run_manifest_path = run_dir / "run_manifest.json"
    if run_manifest_path.exists():
        try:
            with open(run_manifest_path, encoding="utf-8") as f:
                run_manifest = json.load(f)

            tester_baseline = run_manifest.get("tester_baseline") or {}
            deposit = tester_baseline.get("deposit")
            if deposit is not None:
                return float(deposit), "run_manifest.tester_baseline.deposit"

            manifest_ref = run_manifest.get("manifest_ref")
            if manifest_ref:
                manifest_path = Path(manifest_ref)
                if not manifest_path.exists():
                    project_root = parser_dir.resolve()
                    while project_root.name != "PROJECT_triple_sigma" and project_root.parent != project_root:
                        project_root = project_root.parent
                    manifest_path = project_root / manifest_ref
                if manifest_path.exists():
                    with open(manifest_path, encoding="utf-8") as f:
                        campaign_manifest = yaml.safe_load(f) or {}
                    deposit = (
                        campaign_manifest.get("tester_baseline", {}) or {}
                    ).get("deposit")
                    if deposit is not None:
                        return float(deposit), "campaign_manifest.tester_baseline.deposit"
        except (OSError, json.JSONDecodeError, TypeError, ValueError, yaml.YAMLError):
            pass

    return 10000.0, "fallback_default"


def build_daily_metrics(
    trades_df: pd.DataFrame,
    commission_per_lot: float = 0.0,
    initial_equity: float = 10000.0,
) -> pd.DataFrame:
    """Build daily risk metrics from trades_master.

    Note: pnl column already includes broker DEAL_COMMISSION (EA folds it in).
    commission_per_lot is for additional external commission on top of that.
    """
    if trades_df.empty:
        return pd.DataFrame()

    # Ensure numeric
    for col in ["pnl", "lot", "bars_held"]:
        if col in trades_df.columns:
            trades_df[col] = pd.to_numeric(trades_df[col], errors="coerce")

    # Extract dates
    trades_df = trades_df.copy()

    # Use exit_time for closed trades
    if "exit_time" in trades_df.columns:
        trades_df["exit_date"] = trades_df["exit_time"].apply(extract_date)
    if "entry_time" in trades_df.columns:
        trades_df["entry_date"] = trades_df["entry_time"].apply(extract_date)

    # Only closed trades for PnL metrics
    closed = trades_df.dropna(subset=["pnl"]).copy()
    if closed.empty:
        return pd.DataFrame()

    # Collect all trading dates (both entry and exit dates)
    entry_counts = {}
    if "entry_date" in trades_df.columns:
        entry_counts = trades_df.groupby("entry_date").size().to_dict()

    exit_groups = {}
    for date, group in closed.groupby("exit_date"):
        if date is not None:
            exit_groups[date] = group

    # Union of all dates that had either entries or exits
    all_dates = sorted(set(list(entry_counts.keys()) + list(exit_groups.keys())) - {None})

    daily_rows = []
    cum_pnl = 0.0
    peak_pnl = 0.0

    for date in all_dates:
        group = exit_groups.get(date)
        n_entries_day = entry_counts.get(date, 0)

        if group is not None and len(group) > 0:
            pnl_values = group["pnl"].values
            n_trades = len(group)
            gross_pnl = float(pnl_values.sum())

            wins = pnl_values[pnl_values > 0]
            losses = pnl_values[pnl_values < 0]

            gross_profit = float(wins.sum()) if len(wins) > 0 else 0.0
            gross_loss = float(abs(losses.sum())) if len(losses) > 0 else 0.0

            win_rate = len(wins) / n_trades if n_trades > 0 else 0.0
            mean_win = float(wins.mean()) if len(wins) > 0 else 0.0
            mean_loss = float(abs(losses.mean())) if len(losses) > 0 else 0.0

            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            payoff_ratio = mean_win / mean_loss if mean_loss > 0 else np.inf

            # Commission: additional external cost (broker commission already in pnl)
            if commission_per_lot > 0 and "lot" in group.columns:
                day_commission = float(group["lot"].sum()) * commission_per_lot
            else:
                day_commission = 0.0
            net_pnl = gross_pnl - day_commission

            # Expectancy R: mean net PnL / mean risk (proxy: mean |loss|)
            if commission_per_lot > 0 and "lot" in group.columns:
                net_pnl_values = pnl_values - (group["lot"].values * commission_per_lot)
            else:
                net_pnl_values = pnl_values
            losses_net = net_pnl_values[net_pnl_values < 0]
            mean_loss_net = float(abs(losses_net.mean())) if len(losses_net) > 0 else 0.0
            mean_net_pnl = float(net_pnl_values.mean())
            expectancy_r = mean_net_pnl / mean_loss_net if mean_loss_net > 0 else np.inf

            # Cumulative (net of costs)
            cum_pnl += net_pnl
            peak_pnl = max(peak_pnl, cum_pnl)
            cum_dd = cum_pnl - peak_pnl

            # Equity-normalized drawdown
            peak_equity = initial_equity + peak_pnl
            equity_dd_pct = (cum_dd / peak_equity * 100) if peak_equity > 0 else 0.0

            # Direction counts
            long_count = int((group["direction"] == "LONG").sum()) if "direction" in group.columns else 0
            short_count = int((group["direction"] == "SHORT").sum()) if "direction" in group.columns else 0

            # Regime distribution
            regime_dist = {}
            if "regime_id_at_entry" in group.columns:
                regime_dist = group["regime_id_at_entry"].value_counts().to_dict()
                regime_dist = {str(k): int(v) for k, v in regime_dist.items()}

            # Avg bars held
            avg_bars = float(group["bars_held"].mean()) if "bars_held" in group.columns else 0.0

            # Concentration HHI
            hhi = compute_hhi(group["pnl"])

            # Intraday peak-to-trough drawdown (sequential cumulative PnL within day)
            intraday_cum = np.cumsum(pnl_values)
            intraday_peak = np.maximum.accumulate(intraday_cum)
            intraday_dd = intraday_cum - intraday_peak
            max_dd_day = float(abs(intraday_dd.min())) if len(intraday_dd) > 0 else 0.0
        else:
            # Entry-only day: no exits, so no PnL metrics
            n_trades = 0
            gross_pnl = 0.0
            net_pnl = 0.0
            day_commission = 0.0
            win_rate = 0.0
            profit_factor = 0.0
            payoff_ratio = 0.0
            expectancy_r = 0.0
            cum_dd = cum_pnl - peak_pnl
            peak_equity = initial_equity + peak_pnl
            equity_dd_pct = (cum_dd / peak_equity * 100) if peak_equity > 0 else 0.0
            long_count = 0
            short_count = 0
            regime_dist = {}
            avg_bars = 0.0
            hhi = 0.0
            max_dd_day = 0.0

        daily_rows.append({
            "date": date,
            "n_trades": n_trades,
            "n_entries": n_entries_day,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "commission_applied": day_commission,
            "expectancy_r": expectancy_r,
            "profit_factor": profit_factor,
            "payoff_ratio": payoff_ratio,
            "win_rate": win_rate,
            "max_drawdown_day": max_dd_day,
            "cumulative_pnl": cum_pnl,
            "cumulative_drawdown": cum_dd,
            "equity_dd_pct": equity_dd_pct,
            "long_count": long_count,
            "short_count": short_count,
            "regime_distribution": json.dumps(regime_dist),
            "avg_bars_held": avg_bars,
            "concentration_hhi": hhi,
        })

    result = pd.DataFrame(daily_rows)
    if not result.empty:
        result["max_equity_dd_pct"] = result["equity_dd_pct"].cummin()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Build daily portfolio/risk metrics from trades_master."
    )
    parser.add_argument("parser_dir", type=Path, help="Path to parser_outputs/")
    parser.add_argument(
        "--commission-per-lot", type=float, default=0.0,
        help="Additional commission per lot (broker commission already in pnl). Default: 0.0"
    )
    parser.add_argument(
        "--initial-equity", type=float, default=None,
        help=(
            "Initial account equity for percentage drawdown normalization. "
            "If omitted, auto-resolve from run_manifest/campaign manifest deposit."
        ),
    )
    args = parser.parse_args()

    pdir = args.parser_dir
    trades_path = pdir / "trades_master.parquet"

    if not trades_path.exists():
        print(f"trades_master.parquet not found in {pdir}")
        return

    trades_df = pd.read_parquet(trades_path)
    initial_equity, initial_equity_source = resolve_initial_equity(
        pdir,
        args.initial_equity,
    )
    daily = build_daily_metrics(trades_df, args.commission_per_lot, initial_equity)
    global_metrics = compute_global_trade_metrics(trades_df, args.commission_per_lot)

    if not daily.empty:
        daily.to_parquet(pdir / "daily_risk_metrics.parquet", index=False)

    avg_daily_profit_factor = float(
        daily.loc[daily["profit_factor"] != np.inf, "profit_factor"].mean()
    ) if not daily.empty else 0.0
    avg_daily_win_rate = float(daily["win_rate"].mean()) if not daily.empty else 0.0

    # Update manifest
    manifest_path = pdir / "parse_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["daily_risk_metrics"] = {
        "trading_days": len(daily),
        "total_trades": int(daily["n_trades"].sum()) if not daily.empty else 0,
        "total_gross_pnl": float(daily["gross_pnl"].sum()) if not daily.empty else 0.0,
        "total_net_pnl": float(daily["net_pnl"].sum()) if not daily.empty else 0.0,
        "total_pnl": float(daily["cumulative_pnl"].iloc[-1]) if not daily.empty else 0.0,
        "final_drawdown": float(daily["cumulative_drawdown"].iloc[-1]) if not daily.empty else 0.0,
        "max_equity_dd_pct": float(daily["max_equity_dd_pct"].iloc[-1]) if (
            not daily.empty and "max_equity_dd_pct" in daily.columns
        ) else 0.0,
        "cost_model": {
            "broker_commission_in_pnl": True,
            "additional_commission_per_lot": args.commission_per_lot,
            "initial_equity": initial_equity,
            "initial_equity_source": initial_equity_source,
        },
        "global_profit_factor": global_metrics["global_profit_factor"],
        "global_win_rate": global_metrics["global_win_rate"],
        "avg_daily_profit_factor": avg_daily_profit_factor,
        "avg_daily_win_rate": avg_daily_win_rate,
        "winning_trades": global_metrics["winning_trades"],
        "losing_trades": global_metrics["losing_trades"],
        "build_timestamp": datetime.now().isoformat(),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Report
    if not daily.empty:
        total_gross = float(daily["gross_pnl"].sum())
        total_net = float(daily["net_pnl"].sum())
        print(f"Daily risk metrics: {len(daily)} trading days")
        print(f"  Gross PnL: {total_gross:.2f}")
        print(f"  Net PnL:   {total_net:.2f}" + (
            f"  (commission: {total_gross - total_net:.2f})" if total_gross != total_net else ""
        ))
        print(f"  Max cumulative DD: {daily['cumulative_drawdown'].min():.2f}")
        if "max_equity_dd_pct" in daily.columns:
            print(f"  Max equity DD:    {daily['max_equity_dd_pct'].iloc[-1]:.2f}%")
        print(f"  Initial equity:   {initial_equity:.2f} ({initial_equity_source})")
        print(f"  Global win rate:  {global_metrics['global_win_rate']:.2%}")
        print(f"  Global PF:        {global_metrics['global_profit_factor']:.2f}")
        print(f"  Avg daily WR:     {avg_daily_win_rate:.2%}")
        print(f"  Avg daily PF:     {avg_daily_profit_factor:.2f}")
    else:
        print("No daily metrics generated.")


if __name__ == "__main__":
    main()
