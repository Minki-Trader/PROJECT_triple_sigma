from __future__ import annotations

import calendar
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
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
        gaps["prev_weekday"] + "|" + gaps["prev_time"] + "|" + gaps["curr_weekday"] + "|" + gaps["curr_time"] + "|" + gaps["gap_minutes_int"].astype(str)
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
    return gaps.sort_values("prev_timestamp").reset_index(drop=True)


def build_clean_segments(bars: pd.DataFrame, gaps: pd.DataFrame) -> list[Segment]:
    irregular = gaps.loc[gaps["gap_type"] == "intraday_missing_candidate", ["prev_timestamp", "timestamp"]].sort_values("prev_timestamp")
    timestamps = bars["timestamp"].tolist()
    if not timestamps:
        return []

    segments: list[Segment] = []
    seg_start = timestamps[0]
    previous_cut = None
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
        previous_cut = row["timestamp"]

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
    current_start = None
    current_count = 0
    prev_month = None
    for month in tick_df["month"]:
        if month in present:
            if current_start is None:
                current_start = month
                current_count = 1
            else:
                current_count += 1
            prev_month = month
        elif current_start is not None:
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


def intersect_segments(bar_segments: list[Segment], tick_segments: list[Segment]) -> list[Segment]:
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
            intersections.append(
                Segment(
                    start=start.strftime("%Y-%m-%d %H:%M"),
                    end=end.strftime("%Y-%m-%d %H:%M"),
                    bars=0,
                    calendar_days=round((end - start).total_seconds() / 86400.0, 2),
                )
            )
    return intersections


def write_workbook(
    summary: dict[str, object],
    gaps: pd.DataFrame,
    clean_segments: list[Segment],
    tick_df: pd.DataFrame,
    tick_segments: list[Segment],
    combined_segments: list[Segment],
) -> None:
    workbook_path = OUT_DIR / "US100_HISTORY_QUALITY_AUDIT.xlsx"

    summary_rows = [
        {"section": "bar_data", "metric": "source_csv", "value": summary["bar_data"]["source_csv"]},
        {"section": "bar_data", "metric": "bar_count", "value": summary["bar_data"]["bar_count"]},
        {"section": "bar_data", "metric": "start", "value": summary["bar_data"]["start"]},
        {"section": "bar_data", "metric": "end", "value": summary["bar_data"]["end"]},
        {"section": "bar_data", "metric": "gap_count_gt_5m", "value": summary["bar_data"]["gap_count_gt_5m"]},
        {
            "section": "bar_data",
            "metric": "recurring_market_closure_count",
            "value": summary["bar_data"]["recurring_market_closure_count"],
        },
        {
            "section": "bar_data",
            "metric": "exceptional_closure_or_missing_count",
            "value": summary["bar_data"]["exceptional_closure_or_missing_count"],
        },
        {
            "section": "bar_data",
            "metric": "intraday_missing_candidate_count",
            "value": summary["bar_data"]["intraday_missing_candidate_count"],
        },
        {
            "section": "bar_data",
            "metric": "largest_clean_segment_start",
            "value": summary["bar_data"]["largest_clean_segment"]["start"] if summary["bar_data"]["largest_clean_segment"] else None,
        },
        {
            "section": "bar_data",
            "metric": "largest_clean_segment_end",
            "value": summary["bar_data"]["largest_clean_segment"]["end"] if summary["bar_data"]["largest_clean_segment"] else None,
        },
        {
            "section": "bar_data",
            "metric": "largest_clean_segment_bars",
            "value": summary["bar_data"]["largest_clean_segment"]["bars"] if summary["bar_data"]["largest_clean_segment"] else None,
        },
        {
            "section": "bar_data",
            "metric": "largest_clean_segment_calendar_days",
            "value": summary["bar_data"]["largest_clean_segment"]["calendar_days"] if summary["bar_data"]["largest_clean_segment"] else None,
        },
        {"section": "tick_data", "metric": "tick_dir", "value": summary["tick_data"]["tick_dir"]},
        {"section": "tick_data", "metric": "present_month_count", "value": summary["tick_data"]["present_month_count"]},
        {"section": "tick_data", "metric": "missing_month_count", "value": summary["tick_data"]["missing_month_count"]},
        {"section": "tick_data", "metric": "missing_months", "value": ", ".join(summary["tick_data"]["missing_months"])},
        {
            "section": "tick_data",
            "metric": "largest_contiguous_segment_start",
            "value": summary["tick_data"]["largest_contiguous_segment"]["start"] if summary["tick_data"]["largest_contiguous_segment"] else None,
        },
        {
            "section": "tick_data",
            "metric": "largest_contiguous_segment_end",
            "value": summary["tick_data"]["largest_contiguous_segment"]["end"] if summary["tick_data"]["largest_contiguous_segment"] else None,
        },
        {
            "section": "tick_data",
            "metric": "largest_contiguous_segment_months",
            "value": summary["tick_data"]["largest_contiguous_segment"]["bars"] if summary["tick_data"]["largest_contiguous_segment"] else None,
        },
        {
            "section": "tick_data",
            "metric": "largest_contiguous_segment_calendar_days",
            "value": summary["tick_data"]["largest_contiguous_segment"]["calendar_days"] if summary["tick_data"]["largest_contiguous_segment"] else None,
        },
        {
            "section": "recommendation",
            "metric": "recommended_real_tick_backtest_segment_start",
            "value": summary["recommended_real_tick_backtest_segment"]["start"]
            if summary["recommended_real_tick_backtest_segment"]
            else None,
        },
        {
            "section": "recommendation",
            "metric": "recommended_real_tick_backtest_segment_end",
            "value": summary["recommended_real_tick_backtest_segment"]["end"]
            if summary["recommended_real_tick_backtest_segment"]
            else None,
        },
        {
            "section": "recommendation",
            "metric": "recommended_real_tick_backtest_segment_calendar_days",
            "value": summary["recommended_real_tick_backtest_segment"]["calendar_days"]
            if summary["recommended_real_tick_backtest_segment"]
            else None,
        },
    ]

    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        gaps.to_excel(writer, sheet_name="m5_gap_events", index=False)
        pd.DataFrame([asdict(segment) for segment in clean_segments]).to_excel(writer, sheet_name="m5_clean_segments", index=False)
        tick_df.to_excel(writer, sheet_name="tick_month_coverage", index=False)
        pd.DataFrame([asdict(segment) for segment in tick_segments]).to_excel(writer, sheet_name="tick_segments", index=False)
        pd.DataFrame([asdict(segment) for segment in combined_segments]).to_excel(
            writer, sheet_name="combined_realtick", index=False
        )

    workbook = load_workbook(workbook_path)
    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for column_cells in sheet.columns:
            values = [len(str(cell.value)) for cell in column_cells if cell.value is not None]
            width = min(max(values, default=10) + 2, 60)
            sheet.column_dimensions[column_cells[0].column_letter].width = width
    workbook.save(workbook_path)


def write_outputs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bars = load_bars()
    gaps = classify_gaps(bars)
    clean_segments = build_clean_segments(bars, gaps)
    bar_end = bars["timestamp"].iloc[-1] if len(bars) else None
    tick_df, tick_segments, missing_tick_months = analyze_tick_months(bar_end)
    combined_segments = intersect_segments(clean_segments, tick_segments)

    gaps.to_csv(OUT_DIR / "m5_gap_events.csv", index=False)
    tick_df.to_csv(OUT_DIR / "tick_month_coverage.csv", index=False)
    pd.DataFrame([asdict(segment) for segment in clean_segments]).to_csv(OUT_DIR / "m5_clean_segments.csv", index=False)
    pd.DataFrame([asdict(segment) for segment in tick_segments]).to_csv(OUT_DIR / "tick_contiguous_segments.csv", index=False)
    pd.DataFrame([asdict(segment) for segment in combined_segments]).to_csv(OUT_DIR / "combined_clean_realtick_segments.csv", index=False)

    summary = {
        "bar_data": {
            "source_csv": str(BAR_CSV),
            "bar_count": int(len(bars)),
            "start": bars["timestamp"].iloc[0].strftime("%Y-%m-%d %H:%M") if len(bars) else None,
            "end": bars["timestamp"].iloc[-1].strftime("%Y-%m-%d %H:%M") if len(bars) else None,
            "gap_count_gt_5m": int(len(gaps)),
            "recurring_market_closure_count": int((gaps["gap_type"] == "recurring_market_closure").sum()) if len(gaps) else 0,
            "exceptional_closure_or_missing_count": int((gaps["gap_type"] == "exceptional_closure_or_missing").sum()) if len(gaps) else 0,
            "intraday_missing_candidate_count": int((gaps["gap_type"] == "intraday_missing_candidate").sum()) if len(gaps) else 0,
            "largest_clean_segment": asdict(max(clean_segments, key=lambda item: item.bars)) if clean_segments else None,
        },
        "tick_data": {
            "tick_dir": str(TICK_DIR),
            "present_month_count": int(tick_df["present"].sum()) if len(tick_df) else 0,
            "missing_month_count": int((~tick_df["present"]).sum()) if len(tick_df) else 0,
            "missing_months": missing_tick_months,
            "largest_contiguous_segment": asdict(max(tick_segments, key=lambda item: item.bars)) if tick_segments else None,
        },
        "recommended_real_tick_backtest_segment": asdict(max(combined_segments, key=lambda item: item.calendar_days)) if combined_segments else None,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_workbook(summary, gaps, clean_segments, tick_df, tick_segments, combined_segments)

    irregular = gaps.loc[gaps["gap_type"] == "intraday_missing_candidate", ["prev_timestamp", "timestamp", "gap_minutes"]].copy()
    exceptional = gaps.loc[gaps["gap_type"] == "exceptional_closure_or_missing", ["prev_timestamp", "timestamp", "gap_minutes", "pattern_count"]].copy()
    largest_clean = max(clean_segments, key=lambda item: item.bars) if clean_segments else None
    largest_tick = max(tick_segments, key=lambda item: item.bars) if tick_segments else None
    best_combined = max(combined_segments, key=lambda item: item.calendar_days) if combined_segments else None

    lines = [
        "# US100 History Quality Audit",
        "",
        "## Scope",
        "- Symbol: `US100`",
        "- Bar series: `M5` tester-exported bars",
        "- Tick coverage: `FPMarketsSC-Live` monthly `.tkc` files",
        "",
        "## Headline Findings",
        f"- Earliest exported M5 bar: `{summary['bar_data']['start']}`",
        f"- Latest exported M5 bar: `{summary['bar_data']['end']}`",
        f"- Exported M5 bars: `{summary['bar_data']['bar_count']}`",
        f"- Gaps greater than 5 minutes: `{summary['bar_data']['gap_count_gt_5m']}`",
        f"- Recurring market-closure gaps: `{summary['bar_data']['recurring_market_closure_count']}`",
        f"- Exceptional closure/missing candidates: `{summary['bar_data']['exceptional_closure_or_missing_count']}`",
        f"- Intraday missing-bar candidates: `{summary['bar_data']['intraday_missing_candidate_count']}`",
        "",
        "## Tick Coverage",
        f"- Tick months present: `{summary['tick_data']['present_month_count']}`",
        f"- Tick months missing inside observed range: `{summary['tick_data']['missing_month_count']}`",
        f"- Missing tick months: `{', '.join(missing_tick_months) if missing_tick_months else 'none'}`",
        "",
    ]

    if largest_clean:
        lines.extend([
            "## Clean M5 Segment",
            f"- Largest segment without intraday missing-bar candidates: `{largest_clean.start}` -> `{largest_clean.end}`",
            f"- Bars: `{largest_clean.bars}`",
            f"- Calendar span (days): `{largest_clean.calendar_days}`",
            "",
        ])

    if largest_tick:
        lines.extend([
            "## Clean Real-Tick Segment",
            f"- Largest contiguous tick-month segment: `{largest_tick.start}` -> `{largest_tick.end}`",
            f"- Contiguous months: `{largest_tick.bars}`",
            f"- Calendar span (days): `{largest_tick.calendar_days}`",
            "",
        ])

    if best_combined:
        lines.extend([
            "## Recommended Clean Real-Tick Backtest Segment",
            f"- Best overlap of bar-clean + tick-contiguous coverage: `{best_combined.start}` -> `{best_combined.end}`",
            f"- Calendar span (days): `{best_combined.calendar_days}`",
            "",
        ])

    if not irregular.empty:
        lines.append("## Intraday Missing-Bar Candidates")
        for _, row in irregular.head(20).iterrows():
            lines.append(
                f"- `{row['prev_timestamp']:%Y-%m-%d %H:%M}` -> `{row['timestamp']:%Y-%m-%d %H:%M}` : `{row['gap_minutes']:.0f}` minutes"
            )
        lines.append("")

    if not exceptional.empty:
        lines.append("## Exceptional Closure Or Missing Candidates")
        for _, row in exceptional.head(20).iterrows():
            lines.append(
                f"- `{row['prev_timestamp']:%Y-%m-%d %H:%M}` -> `{row['timestamp']:%Y-%m-%d %H:%M}` : `{row['gap_minutes']:.0f}` minutes (pattern_count={int(row['pattern_count'])})"
            )
        lines.append("")

    lines.extend([
        "## Recommended Backtest Usage",
        "- For `Model=4` real-tick backtests, prefer the largest contiguous tick-month segment first.",
        "- Use `m5_clean_segments.csv` to inspect bar-continuous windows separately from tick-month continuity.",
        "- Treat `intraday_missing_candidate` rows as the primary data-quality red flag for bar continuity.",
        "",
        "## Files",
        "- `summary.json`",
        "- `m5_gap_events.csv`",
        "- `m5_clean_segments.csv`",
        "- `tick_month_coverage.csv`",
        "- `tick_contiguous_segments.csv`",
        "- `combined_clean_realtick_segments.csv`",
        "- `US100_HISTORY_QUALITY_AUDIT.xlsx`",
    ])
    (OUT_DIR / "US100_HISTORY_QUALITY_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")

    if REPORT_DIR.parent.exists():
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        for name in [
            "summary.json",
            "m5_gap_events.csv",
            "m5_clean_segments.csv",
            "tick_month_coverage.csv",
            "tick_contiguous_segments.csv",
            "combined_clean_realtick_segments.csv",
            "US100_HISTORY_QUALITY_AUDIT.md",
            "US100_HISTORY_QUALITY_AUDIT.xlsx",
        ]:
            (REPORT_DIR / name).write_bytes((OUT_DIR / name).read_bytes())


if __name__ == "__main__":
    write_outputs()
