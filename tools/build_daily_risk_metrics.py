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
        "--initial-equity", type=float, default=10000.0,
        help="Initial account equity for percentage drawdown normalization. Default: 10000"
    )
    args = parser.parse_args()

    pdir = args.parser_dir
    trades_path = pdir / "trades_master.parquet"

    if not trades_path.exists():
        print(f"trades_master.parquet not found in {pdir}")
        return

    trades_df = pd.read_parquet(trades_path)
    daily = build_daily_metrics(trades_df, args.commission_per_lot, args.initial_equity)

    if not daily.empty:
        daily.to_parquet(pdir / "daily_risk_metrics.parquet", index=False)

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
            "initial_equity": args.initial_equity,
        },
        "avg_profit_factor": float(
            daily.loc[daily["profit_factor"] != np.inf, "profit_factor"].mean()
        ) if not daily.empty else 0.0,
        "avg_win_rate": float(daily["win_rate"].mean()) if not daily.empty else 0.0,
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
        print(f"  Avg win rate: {daily['win_rate'].mean():.2%}")
        print(f"  Avg PF: {daily.loc[daily['profit_factor'] != np.inf, 'profit_factor'].mean():.2f}")
    else:
        print("No daily metrics generated.")


if __name__ == "__main__":
    main()
