from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(r"C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma")
COMMON_FILES = Path(r"C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
BAR_CSV = COMMON_FILES / "history_qa" / "us100_m5_bars.csv"
TICK_DIR = Path(r"C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases\FPMarketsSC-Live\ticks\US100")
OUT_DIR = ROOT / "_coord" / "artifacts" / "us100_history_quality"
REPORT_DIR = ROOT / "GPT-PRO-FOR-REPORT" / "_coord" / "artifacts" / "us100_history_quality"


@dataclass(frozen=True)
class Segment:
    start: str
    end: str
    bars: int
    calendar_days: float


@dataclass(frozen=True)
class Scenario:
    scenario: str
    start: str
    end: str
    bars: int
    calendar_days: float
    actual_tick_coverage: str
    generated_tick_exposure: str
    training_suitability: str
    optimization_suitability: str
    final_backtest_suitability: str
    notes: str


def load_bars() -> pd.DataFrame:
    bars = pd.read_csv(BAR_CSV)
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], format="%Y.%m.%d %H:%M")
    bars = bars.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    bars["prev_timestamp"] = bars["timestamp"].shift(1)
    bars["gap_minutes"] = (bars["timestamp"] - bars["prev_timestamp"]).dt.total_seconds().div(60.0)
    return bars


def classify_gaps(bars: pd.DataFrame) -> pd.DataFrame:
    gaps = bars.loc[bars["gap_minutes"] > 5.0, ["prev_timestamp", "timestamp", "gap_minutes"]].copy()
    if gaps.empty:
        gaps["pattern_count"] = []
        gaps["gap_type"] = []
        return gaps

    gaps["prev_weekday"] = gaps["prev_timestamp"].dt.day_name()
    gaps["prev_time"] = gaps["prev_timestamp"].dt.strftime("%H:%M")
    gaps["curr_weekday"] = gaps["timestamp"].dt.day_name()
    gaps["curr_time"] = gaps["timestamp"].dt.strftime("%H:%M")
    gaps["gap_minutes_int"] = gaps["gap_minutes"].round().astype(int)
    gaps["pattern_key"] = (
        gaps["prev_weekday"]
        + "|"
        + gaps["prev_time"]
        + "|"
        + gaps["curr_weekday"]
        + "|"
        + gaps["curr_time"]
        + "|"
        + gaps["gap_minutes_int"].astype(str)
    )
    pattern_counts = gaps["pattern_key"].value_counts()
    gaps["pattern_count"] = gaps["pattern_key"].map(pattern_counts).astype(int)

    def classify(row: pd.Series) -> str:
        if row["pattern_count"] >= 8:
            return "recurring_market_closure"
        if row["gap_minutes"] >= 60:
            return "exceptional_closure_or_missing"
        return "intraday_missing_candidate"

    gaps["gap_type"] = gaps.apply(classify, axis=1)
    gaps["missing_bars"] = (gaps["gap_minutes"] / 5.0 - 1.0).round().astype(int)
    return gaps.sort_values("prev_timestamp").reset_index(drop=True)


def build_clean_segments(bars: pd.DataFrame, gaps: pd.DataFrame) -> list[Segment]:
    irregular = gaps.loc[gaps["gap_type"] == "intraday_missing_candidate", ["prev_timestamp", "timestamp"]].sort_values("prev_timestamp")
    timestamps = bars["timestamp"].tolist()
    if not timestamps:
        return []

    segments: list[Segment] = []
    seg_start = timestamps[0]
    for _, row in irregular.iterrows():
        seg_end = row["prev_timestamp"]
        subset = bars.loc[(bars["timestamp"] >= seg_start) & (bars["timestamp"] <= seg_end), "timestamp"]
        if not subset.empty:
            segments.append(
                Segment(
                    start=subset.iloc[0].strftime("%Y-%m-%d %H:%M"),
                    end=subset.iloc[-1].strftime("%Y-%m-%d %H:%M"),
                    bars=int(len(subset)),
                    calendar_days=round((subset.iloc[-1] - subset.iloc[0]).total_seconds() / 86400.0, 2),
                )
            )
        seg_start = row["timestamp"]

    subset = bars.loc[bars["timestamp"] >= seg_start, "timestamp"]
    if not subset.empty:
        segments.append(
            Segment(
                start=subset.iloc[0].strftime("%Y-%m-%d %H:%M"),
                end=subset.iloc[-1].strftime("%Y-%m-%d %H:%M"),
                bars=int(len(subset)),
                calendar_days=round((subset.iloc[-1] - subset.iloc[0]).total_seconds() / 86400.0, 2),
            )
        )
    return segments


def analyze_tick_months(bar_end: pd.Timestamp | None) -> tuple[pd.DataFrame, list[Segment], list[str]]:
    files = sorted(path.name for path in TICK_DIR.glob("*.tkc") if path.stem.isdigit())
    present = sorted(file.replace(".tkc", "") for file in files)
    if not present:
        return pd.DataFrame(columns=["month", "present"]), [], []

    start = pd.Period(min(present), freq="M")
    end = pd.Period(max(present), freq="M")
    months = pd.period_range(start, end, freq="M")
    tick_df = pd.DataFrame({"month": [period.strftime("%Y%m") for period in months]})
    tick_df["present"] = tick_df["month"].isin(set(present))

    missing = tick_df.loc[~tick_df["present"], "month"].tolist()

    segments: list[Segment] = []
    current_start: str | None = None
    current_count = 0
    prev_month: str | None = None
    for month in tick_df["month"]:
        if month in present:
            if current_start is None:
                current_start = month
                current_count = 1
            else:
                current_count += 1
            prev_month = month
        elif current_start is not None and prev_month is not None:
            start_p = pd.Period(current_start, freq="M")
            end_p = pd.Period(prev_month, freq="M")
            end_time = end_p.end_time
            if bar_end is not None and end_time > bar_end:
                end_time = bar_end
            segments.append(
                Segment(
                    start=start_p.start_time.strftime("%Y-%m-%d"),
                    end=end_time.strftime("%Y-%m-%d %H:%M"),
                    bars=current_count,
                    calendar_days=round((end_time - start_p.start_time).total_seconds() / 86400.0, 2),
                )
            )
            current_start = None
            current_count = 0
            prev_month = None
    if current_start is not None and prev_month is not None:
        start_p = pd.Period(current_start, freq="M")
        end_p = pd.Period(prev_month, freq="M")
        end_time = end_p.end_time
        if bar_end is not None and end_time > bar_end:
            end_time = bar_end
        segments.append(
            Segment(
                start=start_p.start_time.strftime("%Y-%m-%d"),
                end=end_time.strftime("%Y-%m-%d %H:%M"),
                bars=current_count,
                calendar_days=round((end_time - start_p.start_time).total_seconds() / 86400.0, 2),
            )
        )
    return tick_df, segments, missing


def intersect_segments(bars: pd.DataFrame, bar_segments: list[Segment], tick_segments: list[Segment]) -> list[Segment]:
    intersections: list[Segment] = []
    for bar_seg in bar_segments:
        bar_start = pd.Timestamp(bar_seg.start)
        bar_end = pd.Timestamp(bar_seg.end)
        for tick_seg in tick_segments:
            tick_start = pd.Timestamp(tick_seg.start)
            tick_end = pd.Timestamp(tick_seg.end)
            start = max(bar_start, tick_start)
            end = min(bar_end, tick_end)
            if end <= start:
                continue
            subset = bars.loc[(bars["timestamp"] >= start) & (bars["timestamp"] <= end), "timestamp"]
            intersections.append(
                Segment(
                    start=start.strftime("%Y-%m-%d %H:%M"),
                    end=end.strftime("%Y-%m-%d %H:%M"),
                    bars=int(len(subset)),
                    calendar_days=round((end - start).total_seconds() / 86400.0, 2),
                )
            )
    return intersections


def sum_segment_bars(bars: pd.DataFrame, segments: pd.DataFrame) -> int:
    total = 0
    for _, row in segments.iterrows():
        start = pd.Timestamp(row["start"])
        end = pd.Timestamp(row["end"])
        total += int(((bars["timestamp"] >= start) & (bars["timestamp"] <= end)).sum())
    return total


def make_scenarios(
    bars: pd.DataFrame,
    gaps: pd.DataFrame,
    tick_df: pd.DataFrame,
    tick_segments: list[Segment],
    combined_df: pd.DataFrame,
) -> tuple[list[Scenario], dict[str, object]]:
    intraday = gaps.loc[gaps["gap_type"] == "intraday_missing_candidate"].copy()
    largest_tick = max(tick_segments, key=lambda item: item.calendar_days)
    largest_clean_realtick = max(
        [Segment(row["start"], row["end"], int(row["bars"]), float(row["calendar_days"])) for _, row in combined_df.iterrows()],
        key=lambda item: item.calendar_days,
    )

    full_available_start = bars["timestamp"].iloc[0]
    full_available_end = bars["timestamp"].iloc[-1]
    full_available_bars = int(len(bars))

    full_rt_start = pd.Timestamp(largest_tick.start)
    full_rt_end = pd.Timestamp(largest_tick.end)
    full_rt_bars = int(((bars["timestamp"] >= full_rt_start) & (bars["timestamp"] <= full_rt_end)).sum())
    full_rt_intraday = intraday.loc[(intraday["prev_timestamp"] >= full_rt_start) & (intraday["timestamp"] <= full_rt_end)]
    full_rt_missing_bars = int(full_rt_intraday["missing_bars"].sum())
    full_rt_missing_ratio = (full_rt_missing_bars / full_rt_bars * 100.0) if full_rt_bars else 0.0

    tick_missing_months = tick_df.loc[~tick_df["present"], "month"].tolist()
    full_actual_tick_observed_start = pd.to_datetime(tick_df["month"].iloc[0], format="%Y%m")
    full_actual_tick_observed_end = full_available_end
    bars_in_observed_tick_range = bars.loc[
        (bars["timestamp"] >= full_actual_tick_observed_start) & (bars["timestamp"] <= full_actual_tick_observed_end)
    ].copy()
    bars_in_observed_tick_range["month"] = bars_in_observed_tick_range["timestamp"].dt.strftime("%Y%m")
    bars_in_missing_tick_months = bars_in_observed_tick_range.loc[bars_in_observed_tick_range["month"].isin(tick_missing_months)]
    missing_tick_month_bar_share = (
        len(bars_in_missing_tick_months) / len(bars_in_observed_tick_range) * 100.0 if len(bars_in_observed_tick_range) else 0.0
    )

    rolling_pack = combined_df.loc[combined_df["calendar_days"] >= 180.0].copy()
    rolling_pack_bars = sum_segment_bars(bars, rolling_pack)
    rolling_pack_days = float(rolling_pack["calendar_days"].sum()) if not rolling_pack.empty else 0.0

    largest_clean_bar_only = None
    clean_bar_segments = build_clean_segments(bars, gaps)
    if clean_bar_segments:
        largest_clean_bar_only = max(clean_bar_segments, key=lambda item: item.calendar_days)

    rolling_pack_start = ""
    rolling_pack_end = ""
    if not rolling_pack.empty:
        rolling_pack_start = pd.to_datetime(rolling_pack["start"]).min().strftime("%Y-%m-%d %H:%M")
        rolling_pack_end = pd.to_datetime(rolling_pack["end"]).max().strftime("%Y-%m-%d %H:%M")

    scenarios = [
        Scenario(
            scenario="full_available_m5_range",
            start=full_available_start.strftime("%Y-%m-%d %H:%M"),
            end=full_available_end.strftime("%Y-%m-%d %H:%M"),
            bars=full_available_bars,
            calendar_days=round((full_available_end - full_available_start).total_seconds() / 86400.0, 2),
            actual_tick_coverage="incomplete",
            generated_tick_exposure=f"very_high ({missing_tick_month_bar_share:.2f}% of bars fall inside months without .tkc coverage between {tick_df['month'].iloc[0]} and {tick_df['month'].iloc[-1]})",
            training_suitability="low_to_medium",
            optimization_suitability="low",
            final_backtest_suitability="low",
            notes="Not suitable as a single Model=4 optimization/final-evaluation range. If the tester substitutes generated ticks across missing tick months, the contamination is too large.",
        ),
        Scenario(
            scenario="largest_clean_bar_only_segment",
            start=largest_clean_bar_only.start if largest_clean_bar_only else "",
            end=largest_clean_bar_only.end if largest_clean_bar_only else "",
            bars=largest_clean_bar_only.bars if largest_clean_bar_only else 0,
            calendar_days=largest_clean_bar_only.calendar_days if largest_clean_bar_only else 0.0,
            actual_tick_coverage="partial_or_none",
            generated_tick_exposure="n/a_for_training_bars",
            training_suitability="medium_to_high",
            optimization_suitability="low",
            final_backtest_suitability="low",
            notes="Useful only as auxiliary bar-based training data. Keep it out of final Model=4 optimization/reporting because actual tick coverage is not continuous.",
        ),
        Scenario(
            scenario="full_contiguous_actual_tick_range",
            start=largest_tick.start,
            end=largest_tick.end,
            bars=full_rt_bars,
            calendar_days=largest_tick.calendar_days,
            actual_tick_coverage="contiguous_months_present",
            generated_tick_exposure=f"low ({full_rt_missing_bars} missing M5 bars inside range, {full_rt_missing_ratio:.4f}% of bars)",
            training_suitability="medium_to_high",
            optimization_suitability="medium",
            final_backtest_suitability="medium",
            notes="Viable for exploratory backtests and broad stress runs, but still crosses 10 intraday missing-bar events. Keep gap dates visible in evaluation notes.",
        ),
        Scenario(
            scenario="largest_clean_actual_tick_window",
            start=largest_clean_realtick.start,
            end=largest_clean_realtick.end,
            bars=largest_clean_realtick.bars,
            calendar_days=largest_clean_realtick.calendar_days,
            actual_tick_coverage="clean_and_contiguous",
            generated_tick_exposure="none_expected",
            training_suitability="high",
            optimization_suitability="high",
            final_backtest_suitability="high",
            notes="Best single clean window for high-confidence Model=4 optimization and final comparisons.",
        ),
        Scenario(
            scenario="segment_aware_clean_actual_tick_pack",
            start=rolling_pack_start,
            end=rolling_pack_end,
            bars=rolling_pack_bars,
            calendar_days=round(rolling_pack_days, 2),
            actual_tick_coverage="clean_and_contiguous_by_segment",
            generated_tick_exposure="none_inside_selected_segments",
            training_suitability="high",
            optimization_suitability="high",
            final_backtest_suitability="medium_to_high",
            notes="Best choice for rolling or walk-forward optimization. Use the four >=180-day clean actual-tick windows as separate folds instead of forcing one contaminated continuous range.",
        ),
    ]

    metrics = {
        "full_actual_tick_range": {
            "start": largest_tick.start,
            "end": largest_tick.end,
            "bars": full_rt_bars,
            "calendar_days": largest_tick.calendar_days,
            "intraday_gap_count": int(len(full_rt_intraday)),
            "missing_bars": full_rt_missing_bars,
            "missing_bar_ratio_pct": round(full_rt_missing_ratio, 6),
        },
        "missing_tick_months": {
            "count": int(len(tick_missing_months)),
            "months": tick_missing_months,
            "bars_in_missing_tick_months": int(len(bars_in_missing_tick_months)),
            "share_of_observed_tick_range_bars_pct": round(missing_tick_month_bar_share, 2),
        },
        "rolling_clean_pack": {
            "segment_count_ge_180d": int(len(rolling_pack)),
            "total_bars": int(rolling_pack_bars),
            "total_calendar_days": round(rolling_pack_days, 2),
            "segments": rolling_pack[["start", "end", "bars", "calendar_days"]].to_dict(orient="records"),
        },
    }
    return scenarios, metrics


def write_outputs(scenarios: list[Scenario], metrics: dict[str, object], combined_df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matrix_df = pd.DataFrame([asdict(item) for item in scenarios])
    rolling_df = combined_df.copy()
    rolling_df["recommended_for_rolling_pack"] = rolling_df["calendar_days"] >= 180.0
    rolling_df["recommended_for_single_run"] = rolling_df["calendar_days"] >= 270.0

    (OUT_DIR / "US100_REALTICK_RECOMMENDATION_MATRIX.csv").write_text(matrix_df.to_csv(index=False), encoding="utf-8")
    (OUT_DIR / "US100_REALTICK_WINDOW_CANDIDATES.csv").write_text(rolling_df.to_csv(index=False), encoding="utf-8")
    (OUT_DIR / "US100_REALTICK_FEASIBILITY_SUMMARY.json").write_text(
        json.dumps(
            {
                "scenarios": [asdict(item) for item in scenarios],
                "metrics": metrics,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lines = [
        "# US100 Real-Tick Feasibility Report",
        "",
        "## Executive Summary",
        f"- Full contiguous actual-tick coverage exists only from `{metrics['full_actual_tick_range']['start']}` to `{metrics['full_actual_tick_range']['end']}`.",
        f"- Inside that contiguous actual-tick range, intraday bar-side missing exposure is `{metrics['full_actual_tick_range']['missing_bars']}` M5 bars over `{metrics['full_actual_tick_range']['bars']}` bars total (`{metrics['full_actual_tick_range']['missing_bar_ratio_pct']}`%).",
        f"- Missing tick months inside the broader observed tick range account for `{metrics['missing_tick_months']['bars_in_missing_tick_months']}` M5 bars (`{metrics['missing_tick_months']['share_of_observed_tick_range_bars_pct']}%` of bars).",
        "- Conclusion: using the entire long history as one Model=4 optimization/evaluation range is not recommended.",
        "",
        "## Direct Answers",
        "1. Maximum practical actual-tick backtest span:",
        f"   - Use the contiguous actual-tick range `{metrics['full_actual_tick_range']['start']}` -> `{metrics['full_actual_tick_range']['end']}` as the outer limit.",
        "2. Missing-data status under `Every tick based on real ticks`:",
        f"   - There are `{metrics['missing_tick_months']['count']}` whole months with no `.tkc` files in the broader observed tick range.",
        f"   - There are `{metrics['full_actual_tick_range']['intraday_gap_count']}` intraday missing-bar events even inside the contiguous actual-tick range.",
        "3. If generated ticks substitute the missing regions, is that acceptable?",
        "   - For final backtest comparison and optimizer selection across the full long range: no.",
        "   - For exploratory stress runs inside the contiguous actual-tick span with only sparse bar-side gaps: sometimes acceptable, but only with explicit contamination notes.",
        "   - For ML training, the impact is lower because STEP11+ are bar-close driven, but that does not make generated-tick backtests equivalent to actual-tick execution studies.",
        "4. If contamination matters, what is the best backtest plan?",
        "   - Use a segment-aware rolling plan over clean actual-tick windows instead of one long contaminated period.",
        "5. Can you just run the whole range anyway?",
        "   - You can run it, but it should be tagged exploratory only, not as the main optimization/final-comparison corpus.",
        "6. What is most suitable for training/optimization?",
        "   - Best single high-confidence window: the largest clean actual-tick window.",
        "   - Best overall research plan: the segmented clean actual-tick rolling pack.",
        "   - Worst option for optimizer/final comparison: the full long range with missing tick months substituted/generated.",
        "",
        "## Recommendation Matrix",
        "",
    ]

    for scenario in scenarios:
        lines.extend(
            [
                f"### {scenario.scenario}",
                f"- Period: `{scenario.start}` -> `{scenario.end}`",
                f"- Bars: `{scenario.bars}`",
                f"- Calendar span (days): `{scenario.calendar_days}`",
                f"- Actual tick coverage: `{scenario.actual_tick_coverage}`",
                f"- Generated tick exposure: `{scenario.generated_tick_exposure}`",
                f"- Training suitability: `{scenario.training_suitability}`",
                f"- Optimization suitability: `{scenario.optimization_suitability}`",
                f"- Final backtest suitability: `{scenario.final_backtest_suitability}`",
                f"- Notes: {scenario.notes}",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Segment-Aware Rolling Pack",
            f"- Candidate clean actual-tick windows >=180 days: `{metrics['rolling_clean_pack']['segment_count_ge_180d']}`",
            f"- Aggregate bars across those windows: `{metrics['rolling_clean_pack']['total_bars']}`",
            f"- Aggregate calendar days across those windows: `{metrics['rolling_clean_pack']['total_calendar_days']}`",
            "",
        ]
    )

    for segment in metrics["rolling_clean_pack"]["segments"]:
        lines.append(
            f"- `{segment['start']}` -> `{segment['end']}` | bars=`{segment['bars']}` | days=`{segment['calendar_days']}`"
        )

    lines.extend(
        [
            "",
            "## Practical Policy",
            "- Primary optimization / final comparison:",
            "  use the largest clean actual-tick window first.",
            "- Preferred broader workflow:",
            "  use the clean actual-tick rolling pack as separate folds/windows.",
            "- Exploratory stress runs only:",
            "  use the full contiguous actual-tick span and annotate the sparse intraday gap dates.",
            "- Do not treat the full long range with generated/missing tick substitution as the main optimizer or final backtest corpus.",
            "- If additional training volume is needed, the largest clean M5-only segment may be used as auxiliary train-only data, but keep it out of final Model=4 selection/reporting.",
            "",
            "## Files",
            "- `US100_REALTICK_FEASIBILITY_REPORT.md`",
            "- `US100_REALTICK_FEASIBILITY_SUMMARY.json`",
            "- `US100_REALTICK_RECOMMENDATION_MATRIX.csv`",
            "- `US100_REALTICK_WINDOW_CANDIDATES.csv`",
        ]
    )

    (OUT_DIR / "US100_REALTICK_FEASIBILITY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    if REPORT_DIR.parent.exists():
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        for name in [
            "US100_REALTICK_FEASIBILITY_REPORT.md",
            "US100_REALTICK_FEASIBILITY_SUMMARY.json",
            "US100_REALTICK_RECOMMENDATION_MATRIX.csv",
            "US100_REALTICK_WINDOW_CANDIDATES.csv",
        ]:
            (REPORT_DIR / name).write_bytes((OUT_DIR / name).read_bytes())


def main() -> None:
    bars = load_bars()
    gaps = classify_gaps(bars)
    clean_segments = build_clean_segments(bars, gaps)
    bar_end = bars["timestamp"].iloc[-1] if len(bars) else None
    tick_df, tick_segments, _ = analyze_tick_months(bar_end)
    combined_segments = intersect_segments(bars, clean_segments, tick_segments)
    combined_df = pd.DataFrame([asdict(segment) for segment in combined_segments]).sort_values(
        ["calendar_days", "start"], ascending=[False, True]
    )
    scenarios, metrics = make_scenarios(bars, gaps, tick_df, tick_segments, combined_df)
    write_outputs(scenarios, metrics, combined_df)


if __name__ == "__main__":
    main()
