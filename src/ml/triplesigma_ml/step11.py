from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EPSILON = 1e-9
WINDOW_SIZE = 64
FEATURE_DIM = 22
HOLD_MAX = 72
PASS_DEFAULT_K_SL = 1.5
PASS_DEFAULT_K_TP = 2.0
PASS_DEFAULT_HOLD = 24
CAND_DIST_ATR_MAX_STATIC = 2.5
EXPECTED_TIMEFRAME = "PERIOD_M5"
EXPECTED_PRICE_BASIS = "Bid"
EXPECTED_CANDIDATE_POLICY = "0.1.2"
EXPECTED_REGIME_POLICY = "0.1.0q"
EXPECTED_COST_MODEL = "0.1"
EXPECTED_GAP_SECONDS = 300
DEFAULT_VALIDATION_TOLERANCE = 1e-6

VALIDATION_TOLERANCES = {
    "ret_1": DEFAULT_VALIDATION_TOLERANCE,
    "ret_3": DEFAULT_VALIDATION_TOLERANCE,
    "ret_12": DEFAULT_VALIDATION_TOLERANCE,
    "range_atr": DEFAULT_VALIDATION_TOLERANCE,
    "body_atr": DEFAULT_VALIDATION_TOLERANCE,
    "close_pos": DEFAULT_VALIDATION_TOLERANCE,
    "rsi_norm": DEFAULT_VALIDATION_TOLERANCE,
    "adx_norm": DEFAULT_VALIDATION_TOLERANCE,
    "spread_atr": DEFAULT_VALIDATION_TOLERANCE,
    "time_sin": DEFAULT_VALIDATION_TOLERANCE,
    "time_cos": DEFAULT_VALIDATION_TOLERANCE,
    "dist_atr_abs_feature6": DEFAULT_VALIDATION_TOLERANCE,
    "dist_atr_max_t": DEFAULT_VALIDATION_TOLERANCE,
}

HARD_MISMATCH_KEYS = (
    "regime_id",
    "cand_long",
    "cand_short",
    "regime_one_hot",
    "invalid_candidate_pair",
    "dist_atr_max_mode",
    "policy_version",
    "dist_atr_max_nonpositive",
    "dist_atr_max_out_of_range",
    "dist_atr_max_value",
)

FEATURE_COLUMNS = [f"feature_{i}" for i in range(FEATURE_DIM)]
REQUIRED_BAR_LOG_COLUMNS = [
    "time",
    "symbol",
    "timeframe",
    "price_basis",
    "open",
    "high",
    "low",
    "close",
    "spread_points",
    "atr14",
    "adx14",
    "atr_pct",
    "regime_id",
    "cand_long",
    "cand_short",
    "dist_atr_max_t",
    "dist_atr_max_mode",
    "candidate_policy_version",
    "regime_policy_version",
    "cost_model_version",
]
REQUIRED_BAR_LOG_COLUMNS.extend(FEATURE_COLUMNS)


@dataclass(frozen=True)
class Step11Config:
    input_path: Path
    pack_meta_path: Path
    output_dir: Path
    from_ts: pd.Timestamp | None
    to_ts: pd.Timestamp | None
    warmup_bars: int
    lookahead_bars: int
    slip_points: int
    r_pass_buffer: float
    point_size: float | None
    search_space_version: str


@dataclass(frozen=True)
class PackMeta:
    values: dict[str, str]

    @property
    def atr_thr(self) -> float:
        return float(self.values["atr_thr"])

    @property
    def adx_thr1(self) -> float:
        return float(self.values["adx_thr1"])

    @property
    def adx_thr2(self) -> float:
        return float(self.values["adx_thr2"])

    @property
    def model_pack_version(self) -> str:
        return self.values["model_pack_version"]

    @property
    def schema_version(self) -> str:
        return self.values["schema_version"]

    @property
    def candidate_policy_version(self) -> str:
        return self.values["candidate_policy_version"]

    @property
    def regime_policy_version(self) -> str:
        return self.values["regime_policy_version"]

    @property
    def cost_model_version(self) -> str:
        return self.values["cost_model_version"]

    @property
    def dist_atr_max_mode(self) -> str:
        return self.values.get("dist_atr_max_mode", "static") or "static"

    @property
    def dist_atr_max_q(self) -> float:
        return float(self.values.get("dist_atr_max_q", "0.80"))

    @property
    def dist_atr_max_w(self) -> int:
        return int(self.values.get("dist_atr_max_w", "63"))

    @property
    def dist_atr_max_clamp_lo(self) -> float:
        return float(self.values.get("dist_atr_max_clamp_lo", "0.5"))

    @property
    def dist_atr_max_clamp_hi(self) -> float:
        return float(self.values.get("dist_atr_max_clamp_hi", "5.0"))

    @property
    def thr_method(self) -> str:
        return self.values.get("thr_method", "")

    @property
    def thr_seed(self) -> str:
        return self.values.get("thr_seed", "")

    @property
    def thr_notes(self) -> str:
        return self.values.get("thr_notes", "")


def parse_optional_timestamp(value: str | None, end_of_day: bool) -> pd.Timestamp | None:
    if not value:
        return None

    ts = pd.to_datetime(value)
    if end_of_day and len(value) <= 10:
        ts = ts + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)
    return ts


def parse_args() -> Step11Config:
    parser = argparse.ArgumentParser(description="STEP11 labeling pipeline for Triple Sigma.")
    parser.add_argument("--input", required=True, help="bar_log CSV file or directory containing bar_log_*.csv")
    parser.add_argument("--pack-meta", required=True, help="pack_meta.csv path")
    parser.add_argument("--output-dir", required=True, help="output directory")
    parser.add_argument("--from", dest="from_ts", help="optional inclusive start date/time")
    parser.add_argument("--to", dest="to_ts", help="optional inclusive end date/time")
    parser.add_argument("--warmup-bars", type=int, default=150)
    parser.add_argument("--lookahead-bars", type=int, default=HOLD_MAX)
    parser.add_argument("--slip-points", type=int, default=2)
    parser.add_argument("--r-pass-buffer", type=float, default=0.05)
    parser.add_argument("--point-size", type=float, default=None)
    parser.add_argument("--search-space-version", default="0.1.0")
    args = parser.parse_args()

    return Step11Config(
        input_path=Path(args.input),
        pack_meta_path=Path(args.pack_meta),
        output_dir=Path(args.output_dir),
        from_ts=parse_optional_timestamp(args.from_ts, end_of_day=False),
        to_ts=parse_optional_timestamp(args.to_ts, end_of_day=True),
        warmup_bars=args.warmup_bars,
        lookahead_bars=args.lookahead_bars,
        slip_points=args.slip_points,
        r_pass_buffer=args.r_pass_buffer,
        point_size=args.point_size,
        search_space_version=args.search_space_version,
    )


def load_pack_meta(path: Path) -> PackMeta:
    if not path.exists():
        raise FileNotFoundError(f"pack_meta not found: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    required = [
        "atr_thr",
        "adx_thr1",
        "adx_thr2",
        "model_pack_version",
        "schema_version",
        "candidate_policy_version",
        "regime_policy_version",
        "cost_model_version",
    ]
    missing = [key for key in required if values.get(key, "") == ""]
    if missing:
        raise ValueError(f"pack_meta missing required keys: {missing}")

    return PackMeta(values=values)


def collect_bar_log_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"input path not found: {path}")

    files = sorted(path.glob("bar_log_*.csv"))
    if not files:
        raise FileNotFoundError(f"no bar_log_*.csv under {path}")
    return files


def read_bar_logs(files: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for file_path in files:
        frame = pd.read_csv(file_path)
        missing = [col for col in REQUIRED_BAR_LOG_COLUMNS if col not in frame.columns]
        if missing:
            raise ValueError(f"{file_path} missing columns: {missing}")
        frame["source_file"] = file_path.name
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df["bar_time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")

    numeric_cols = [
        "open", "high", "low", "close", "spread_points", "atr14", "adx14", "atr_pct",
        "regime_id", "cand_long", "cand_short", "entry_allowed", "onnx_p_long", "onnx_p_short",
        "onnx_p_pass", "flip_used", "k_sl_req", "k_tp_req", "k_sl_eff", "k_tp_eff", "hold_bars",
        "gate_pass", "dyn_spread_atr_max", "dyn_dev_points", "risk_pct", "dist_atr", "dist_atr_max_t",
        "has_position", "bars_held",
    ]
    numeric_cols.extend(FEATURE_COLUMNS)

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["bar_time", "source_file"]).drop_duplicates(subset=["bar_time"], keep="last").reset_index(drop=True)


def filter_bar_logs(df: pd.DataFrame, config: Step11Config) -> pd.DataFrame:
    filtered = df.copy()
    if config.from_ts is not None:
        filtered = filtered.loc[filtered["bar_time"] >= config.from_ts]
    if config.to_ts is not None:
        filtered = filtered.loc[filtered["bar_time"] <= config.to_ts]
    filtered = filtered.reset_index(drop=True)
    if filtered.empty:
        raise ValueError("no rows left after date filter")
    return filtered


def validate_static_metadata(df: pd.DataFrame, pack_meta: PackMeta) -> dict[str, Any]:
    symbol_values = sorted(df["symbol"].dropna().unique().tolist())
    timeframe_values = sorted(df["timeframe"].dropna().unique().tolist())
    price_basis_values = sorted(df["price_basis"].dropna().unique().tolist())
    if len(symbol_values) != 1:
        raise ValueError(f"expected single symbol, found {symbol_values}")
    if len(timeframe_values) != 1:
        raise ValueError(f"expected single timeframe, found {timeframe_values}")
    if len(price_basis_values) != 1:
        raise ValueError(f"expected single price_basis, found {price_basis_values}")
    if timeframe_values[0] != EXPECTED_TIMEFRAME:
        raise ValueError(f"timeframe mismatch: expected {EXPECTED_TIMEFRAME}, got {timeframe_values[0]}")
    if price_basis_values[0] != EXPECTED_PRICE_BASIS:
        raise ValueError(f"price_basis mismatch: expected {EXPECTED_PRICE_BASIS}, got {price_basis_values[0]}")

    candidate_versions = sorted(df["candidate_policy_version"].dropna().astype(str).unique().tolist())
    regime_versions = sorted(df["regime_policy_version"].dropna().astype(str).unique().tolist())
    cost_versions = sorted(df["cost_model_version"].dropna().astype(str).unique().tolist())
    if candidate_versions != [pack_meta.candidate_policy_version]:
        raise ValueError(f"candidate policy mismatch: bar_log={candidate_versions} pack_meta={pack_meta.candidate_policy_version}")
    if regime_versions != [pack_meta.regime_policy_version]:
        raise ValueError(f"regime policy mismatch: bar_log={regime_versions} pack_meta={pack_meta.regime_policy_version}")
    if cost_versions != [pack_meta.cost_model_version]:
        raise ValueError(f"cost model mismatch: bar_log={cost_versions} pack_meta={pack_meta.cost_model_version}")
    if pack_meta.candidate_policy_version != EXPECTED_CANDIDATE_POLICY:
        raise ValueError(f"unexpected candidate policy version: {pack_meta.candidate_policy_version}")
    if pack_meta.regime_policy_version != EXPECTED_REGIME_POLICY:
        raise ValueError(f"unexpected regime policy version: {pack_meta.regime_policy_version}")
    if pack_meta.cost_model_version != EXPECTED_COST_MODEL:
        raise ValueError(f"unexpected cost model version: {pack_meta.cost_model_version}")

    return {
        "symbol": symbol_values[0],
        "timeframe": timeframe_values[0],
        "price_basis": price_basis_values[0],
        "candidate_policy_version": candidate_versions[0],
        "regime_policy_version": regime_versions[0],
        "cost_model_version": cost_versions[0],
    }


def infer_point_size(df: pd.DataFrame, explicit_point: float | None) -> float:
    if explicit_point is not None and explicit_point > 0:
        return explicit_point

    spread_feature_price = df["feature_11"].to_numpy(dtype=float) * np.maximum(df["atr14"].to_numpy(dtype=float), EPSILON)
    spread_points = df["spread_points"].to_numpy(dtype=float)
    valid = np.isfinite(spread_feature_price) & np.isfinite(spread_points) & (spread_points > 0.0) & (spread_feature_price > 0.0)
    if np.any(valid):
        point_candidates = spread_feature_price[valid] / spread_points[valid]
        point_candidates = point_candidates[np.isfinite(point_candidates) & (point_candidates > 0.0)]
        if point_candidates.size > 0:
            return float(np.median(point_candidates))

    raise ValueError("unable to infer point size; provide --point-size")

def build_feature_frame(df: pd.DataFrame, point_size: float) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index.copy())
    out["bar_time"] = df["bar_time"]
    out["symbol"] = df["symbol"].astype(str)
    out["open"] = df["open"].astype(float)
    out["high"] = df["high"].astype(float)
    out["low"] = df["low"].astype(float)
    out["close"] = df["close"].astype(float)
    out["spread_points"] = df["spread_points"].astype(float)
    out["spread_price"] = out["spread_points"] * point_size
    out["atr14"] = df["atr14"].astype(float)
    out["adx14"] = df["adx14"].astype(float)
    out["ema20"] = out["close"] - (df["feature_6"].astype(float) * out["atr14"])
    out["ema50"] = out["close"] - (df["feature_7"].astype(float) * out["atr14"])
    out["rsi14"] = (df["feature_9"].astype(float) * 50.0) + 50.0
    out["atr_pct"] = out["atr14"] / np.maximum(np.abs(out["close"]), EPSILON)
    if "dist_atr" in df.columns:
        out["dist_atr"] = df["dist_atr"].astype(float)
    else:
        out["dist_atr"] = np.abs(out["close"] - out["ema20"]) / np.maximum(out["atr14"], EPSILON)
    out["regime_id"] = df["regime_id"].astype(np.int16)
    out["cand_long"] = df["cand_long"].astype(np.int8)
    out["cand_short"] = df["cand_short"].astype(np.int8)
    out["dist_atr_max_t"] = df["dist_atr_max_t"].astype(float)
    out["dist_atr_max_mode"] = df["dist_atr_max_mode"].astype(str)
    for optional_col in [
        "entry_allowed",
        "candidate_policy_version",
        "regime_policy_version",
        "cost_model_version",
        "schema_version",
        "model_pack_version",
    ]:
        if optional_col in df.columns:
            out[optional_col] = df[optional_col]
    for feature_col in FEATURE_COLUMNS:
        out[feature_col] = df[feature_col].astype(float)
    return out


def log_return_series(close_values: np.ndarray, lookback: int) -> np.ndarray:
    indices = np.arange(close_values.shape[0])
    src_indices = np.maximum(indices - lookback, 0)
    close_abs = np.maximum(np.abs(close_values), EPSILON)
    src_abs = np.maximum(np.abs(close_values[src_indices]), EPSILON)
    return np.log(close_abs / src_abs)


def compute_iso_minute_of_week(bar_times: pd.Series) -> np.ndarray:
    weekday = bar_times.dt.weekday.to_numpy(dtype=np.int64)
    hour = bar_times.dt.hour.to_numpy(dtype=np.int64)
    minute = bar_times.dt.minute.to_numpy(dtype=np.int64)
    return (weekday * 1440) + (hour * 60) + minute


def compute_regime_ids(close_values: np.ndarray, atr14: np.ndarray, adx14: np.ndarray, pack_meta: PackMeta) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atr_pct = atr14 / np.maximum(np.abs(close_values), EPSILON)
    atr_bin = (atr_pct >= pack_meta.atr_thr).astype(np.int8)
    adx_bin = np.where(adx14 < pack_meta.adx_thr1, 0, np.where(adx14 < pack_meta.adx_thr2, 1, 2)).astype(np.int8)
    regime_id = (adx_bin * 2 + atr_bin).astype(np.int8)
    return atr_bin, adx_bin, regime_id


def compute_dist_atr_thresholds(
    dist_atr: np.ndarray,
    pack_meta: PackMeta,
    gap_prev: np.ndarray | None = None,
) -> np.ndarray:
    result = np.full(dist_atr.shape[0], CAND_DIST_ATR_MAX_STATIC, dtype=float)
    if pack_meta.dist_atr_max_mode != "adaptive_quantile":
        return result

    if gap_prev is None:
        gap_prev = np.zeros(dist_atr.shape[0], dtype=bool)
    else:
        gap_prev = np.asarray(gap_prev, dtype=bool)
        if gap_prev.shape[0] != dist_atr.shape[0]:
            raise ValueError("gap_prev length must match dist_atr length")

    q = pack_meta.dist_atr_max_q
    w = pack_meta.dist_atr_max_w
    segment_start = 0
    for idx in range(dist_atr.shape[0]):
        if idx > 0 and gap_prev[idx]:
            segment_start = idx

        history_len = idx - segment_start
        if history_len < w:
            continue
        if history_len == w:
            # Runtime first-ready bar after a gap replays the fresh-segment tail,
            # excluding the gap-first row from the threshold history.
            history = np.sort(dist_atr[idx - w + 1 : idx + 1])
        else:
            history = np.sort(dist_atr[idx - w:idx])
        quantile_idx = int(math.floor(q * (history.shape[0] - 1)))
        quantile_value = float(history[quantile_idx])
        result[idx] = float(np.clip(quantile_value, pack_meta.dist_atr_max_clamp_lo, pack_meta.dist_atr_max_clamp_hi))
    return result


def compute_candidate_flags(df: pd.DataFrame, adx_bin: np.ndarray, dist_atr_max_t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    close_values = df["close"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    ema50 = df["ema50"].to_numpy(dtype=float)
    rsi14 = df["rsi14"].to_numpy(dtype=float)
    dist_atr = df["dist_atr"].to_numpy(dtype=float)

    long_cond = np.zeros(df.shape[0], dtype=bool)
    short_cond = np.zeros(df.shape[0], dtype=bool)
    trend_mask = adx_bin >= 1
    range_mask = ~trend_mask

    long_cond[trend_mask] = (ema20[trend_mask] > ema50[trend_mask]) & (rsi14[trend_mask] >= 52.0) & (close_values[trend_mask] >= ema20[trend_mask])
    short_cond[trend_mask] = (ema20[trend_mask] < ema50[trend_mask]) & (rsi14[trend_mask] <= 48.0) & (close_values[trend_mask] <= ema20[trend_mask])
    long_cond[range_mask] = (rsi14[range_mask] <= 40.0) & (close_values[range_mask] <= ema50[range_mask])
    short_cond[range_mask] = (rsi14[range_mask] >= 60.0) & (close_values[range_mask] >= ema50[range_mask])

    within_dist = dist_atr <= dist_atr_max_t
    cand_long = (within_dist & long_cond & ~short_cond).astype(np.int8)
    cand_short = (within_dist & short_cond & ~long_cond).astype(np.int8)
    return cand_long, cand_short


def compute_candidate_flags_from_logged_fields(df: pd.DataFrame, adx_bin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ema20_dist = df["feature_6"].to_numpy(dtype=float)
    ema50_dist = df["feature_7"].to_numpy(dtype=float)
    rsi_norm = df["feature_9"].to_numpy(dtype=float)
    dist_atr = df["dist_atr"].to_numpy(dtype=float)
    dist_atr_max_t = df["dist_atr_max_t"].to_numpy(dtype=float)

    long_cond = np.zeros(df.shape[0], dtype=bool)
    short_cond = np.zeros(df.shape[0], dtype=bool)
    trend_mask = adx_bin >= 1
    range_mask = ~trend_mask

    long_cond[trend_mask] = (ema20_dist[trend_mask] < ema50_dist[trend_mask]) & (rsi_norm[trend_mask] >= 0.04) & (ema20_dist[trend_mask] >= 0.0)
    short_cond[trend_mask] = (ema20_dist[trend_mask] > ema50_dist[trend_mask]) & (rsi_norm[trend_mask] <= -0.04) & (ema20_dist[trend_mask] <= 0.0)
    long_cond[range_mask] = (rsi_norm[range_mask] <= -0.20) & (ema50_dist[range_mask] <= 0.0)
    short_cond[range_mask] = (rsi_norm[range_mask] >= 0.20) & (ema50_dist[range_mask] >= 0.0)

    within_dist = dist_atr <= (dist_atr_max_t + 1e-9)
    cand_long = (within_dist & long_cond & ~short_cond).astype(np.int8)
    cand_short = (within_dist & short_cond & ~long_cond).astype(np.int8)
    return cand_long, cand_short


def validate_feature_integrity(df: pd.DataFrame, pack_meta: PackMeta, warmup_bars: int) -> dict[str, Any]:
    close_values = df["close"].to_numpy(dtype=float)
    high_values = df["high"].to_numpy(dtype=float)
    low_values = df["low"].to_numpy(dtype=float)
    atr14 = df["atr14"].to_numpy(dtype=float)
    adx14 = df["adx14"].to_numpy(dtype=float)
    spread_price = df["spread_price"].to_numpy(dtype=float)
    range_atr = (high_values - low_values) / np.maximum(atr14, EPSILON)
    body_atr = (close_values - df["open"].to_numpy(dtype=float)) / np.maximum(atr14, EPSILON)

    ret_1 = log_return_series(close_values, 1)
    ret_3 = log_return_series(close_values, 3)
    ret_12 = log_return_series(close_values, 12)
    close_pos = np.clip((2.0 * ((close_values - low_values) / np.maximum(high_values - low_values, EPSILON))) - 1.0, -1.0, 1.0)
    rsi_norm = (df["rsi14"].to_numpy(dtype=float) - 50.0) / 50.0
    dist_atr = df["dist_atr"].to_numpy(dtype=float)
    dist_atr_from_feature = np.abs(df["feature_6"].to_numpy(dtype=float))

    minute_of_week = compute_iso_minute_of_week(df["bar_time"])
    angle = 2.0 * math.pi * (minute_of_week / 10080.0)
    time_sin = np.sin(angle)
    time_cos = np.cos(angle)

    _, adx_bin, regime_id = compute_regime_ids(close_values, atr14, adx14, pack_meta)
    cand_long, cand_short = compute_candidate_flags_from_logged_fields(df, adx_bin)

    valid_runtime = (atr14 > 0.0) & (df["regime_id"].to_numpy(dtype=int) >= 0)
    valid_runtime &= np.arange(df.shape[0]) >= max(warmup_bars - 1, WINDOW_SIZE - 1)

    def max_abs_diff(lhs: np.ndarray, rhs: np.ndarray, mask: np.ndarray | None = None) -> float:
        if mask is None:
            mask = np.ones(lhs.shape[0], dtype=bool)
        values = np.abs(lhs[mask] - rhs[mask])
        if values.size == 0:
            return 0.0
        return float(np.nanmax(values))

    runtime_regime = df["regime_id"].to_numpy(dtype=int)
    good_regime = (runtime_regime >= 0) & (runtime_regime < 6)
    one_hot_runtime = np.zeros((df.shape[0], 6), dtype=np.int8)
    one_hot_runtime[good_regime, runtime_regime[good_regime]] = 1
    one_hot_logged = np.stack([df[f"feature_{idx}"].to_numpy(dtype=float) for idx in range(14, 20)], axis=1)
    cand_logged_long = df["cand_long"].to_numpy(dtype=np.int8)
    cand_logged_short = df["cand_short"].to_numpy(dtype=np.int8)
    dist_atr_max_t = df["dist_atr_max_t"].to_numpy(dtype=float)
    gap_prev, _ = build_gap_flags(df["bar_time"])
    expected_dist_atr_max_t = compute_dist_atr_thresholds(dist_atr, pack_meta, gap_prev)
    dist_atr_mode = df["dist_atr_max_mode"].astype(str).to_numpy()
    policy_versions_match = (
        (df.get("candidate_policy_version", pd.Series([pack_meta.candidate_policy_version] * df.shape[0])).astype(str).to_numpy() == pack_meta.candidate_policy_version)
        & (df.get("regime_policy_version", pd.Series([pack_meta.regime_policy_version] * df.shape[0])).astype(str).to_numpy() == pack_meta.regime_policy_version)
        & (df.get("cost_model_version", pd.Series([pack_meta.cost_model_version] * df.shape[0])).astype(str).to_numpy() == pack_meta.cost_model_version)
    )
    segment_age = build_segment_age(gap_prev)
    gap_first_ready_mask = segment_age == WINDOW_SIZE
    dist_atr_value_mask = valid_runtime & ~gap_first_ready_mask

    return {
        "rows_validated": int(np.count_nonzero(valid_runtime)),
        "rows_validated_dist_atr_max": int(np.count_nonzero(dist_atr_value_mask)),
        "gap_first_ready_rows_excluded": int(np.count_nonzero(valid_runtime & gap_first_ready_mask)),
        "max_abs_diff": {
            "ret_1": max_abs_diff(ret_1, df["feature_0"].to_numpy(dtype=float), valid_runtime),
            "ret_3": max_abs_diff(ret_3, df["feature_1"].to_numpy(dtype=float), valid_runtime),
            "ret_12": max_abs_diff(ret_12, df["feature_2"].to_numpy(dtype=float), valid_runtime),
            "range_atr": max_abs_diff(range_atr, df["feature_3"].to_numpy(dtype=float), valid_runtime),
            "body_atr": max_abs_diff(body_atr, df["feature_4"].to_numpy(dtype=float), valid_runtime),
            "close_pos": max_abs_diff(close_pos, df["feature_5"].to_numpy(dtype=float), valid_runtime),
            "rsi_norm": max_abs_diff(rsi_norm, df["feature_9"].to_numpy(dtype=float), valid_runtime),
            "adx_norm": max_abs_diff(adx14 / 100.0, df["feature_10"].to_numpy(dtype=float), valid_runtime),
            "spread_atr": max_abs_diff(spread_price / np.maximum(atr14, EPSILON), df["feature_11"].to_numpy(dtype=float), valid_runtime),
            "time_sin": max_abs_diff(time_sin, df["feature_12"].to_numpy(dtype=float), valid_runtime),
            "time_cos": max_abs_diff(time_cos, df["feature_13"].to_numpy(dtype=float), valid_runtime),
            "dist_atr_abs_feature6": max_abs_diff(dist_atr, dist_atr_from_feature, valid_runtime),
            "dist_atr_max_t": max_abs_diff(expected_dist_atr_max_t, dist_atr_max_t, dist_atr_value_mask),
        },
        "mismatch_count": {
            "regime_id": int(np.count_nonzero(regime_id[valid_runtime] != df.loc[valid_runtime, "regime_id"].to_numpy(dtype=np.int8))),
            "cand_long": int(np.count_nonzero(cand_long[valid_runtime] != cand_logged_long[valid_runtime])),
            "cand_short": int(np.count_nonzero(cand_short[valid_runtime] != cand_logged_short[valid_runtime])),
            "regime_one_hot": int(np.count_nonzero(np.abs(one_hot_runtime[valid_runtime].astype(float) - one_hot_logged[valid_runtime]) > 1e-6)),
            "invalid_candidate_pair": int(np.count_nonzero((cand_logged_long[valid_runtime] == 1) & (cand_logged_short[valid_runtime] == 1))),
            "dist_atr_max_mode": int(np.count_nonzero(dist_atr_mode[valid_runtime] != pack_meta.dist_atr_max_mode)),
            "policy_version": int(np.count_nonzero(~policy_versions_match[valid_runtime])),
            "dist_atr_max_nonpositive": int(np.count_nonzero(dist_atr_max_t[valid_runtime] <= 0.0)),
            "dist_atr_max_out_of_range": int(
                np.count_nonzero(
                    (dist_atr_max_t[valid_runtime] < pack_meta.dist_atr_max_clamp_lo - 1e-9)
                    | (dist_atr_max_t[valid_runtime] > pack_meta.dist_atr_max_clamp_hi + 1e-9)
                )
            ) if pack_meta.dist_atr_max_mode == "adaptive_quantile" else 0,
            "dist_atr_max_value": int(
                np.count_nonzero(
                    np.abs(expected_dist_atr_max_t[dist_atr_value_mask] - dist_atr_max_t[dist_atr_value_mask]) > VALIDATION_TOLERANCES["dist_atr_max_t"]
                )
            ),
        },
    }


def assert_validation_pass(validation: dict[str, Any]) -> None:
    rows_validated = int(validation.get("rows_validated", 0))
    if rows_validated <= 0:
        raise ValueError("STEP11 validation failed: no rows validated")

    mismatch_count = validation.get("mismatch_count", {})
    for key in HARD_MISMATCH_KEYS:
        value = int(mismatch_count.get(key, -1))
        if value != 0:
            raise ValueError(f"STEP11 validation failed: mismatch_count[{key}]={value}")

    max_abs_diff = validation.get("max_abs_diff", {})
    for key, value in max_abs_diff.items():
        tolerance = float(VALIDATION_TOLERANCES.get(key, DEFAULT_VALIDATION_TOLERANCE))
        if float(value) > tolerance:
            raise ValueError(f"STEP11 validation failed: max_abs_diff[{key}]={float(value):.12f} > {tolerance:.12f}")


def build_gap_flags(bar_times: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    bar_seconds = (bar_times.astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
    diffs = np.diff(bar_seconds, prepend=bar_seconds[0])
    gap_prev = diffs > EXPECTED_GAP_SECONDS
    gap_next = np.concatenate((gap_prev[1:], np.array([False], dtype=bool)))
    return gap_prev.astype(bool), gap_next.astype(bool)


def build_segment_age(gap_prev: np.ndarray) -> np.ndarray:
    segment_age = np.zeros(gap_prev.shape[0], dtype=np.int32)
    age = 0
    for idx in range(gap_prev.shape[0]):
        if idx == 0 or gap_prev[idx]:
            age = 1
        else:
            age += 1
        segment_age[idx] = age
    return segment_age


def build_cumulative_flags(flags: np.ndarray) -> np.ndarray:
    return np.concatenate(([0], np.cumsum(flags.astype(np.int64))))


def has_any_true(cumsum: np.ndarray, start: int, end_inclusive: int) -> bool:
    if end_inclusive < start:
        return False
    return bool(cumsum[end_inclusive + 1] - cumsum[start] > 0)

def action_search_for_direction(
    direction: str,
    decision_row: pd.Series,
    future_rows: pd.DataFrame,
    k_sl_grid: np.ndarray,
    k_tp_grid: np.ndarray,
    hold_grid: np.ndarray,
    slip_price: float,
) -> dict[str, Any]:
    atr14_t = float(decision_row["atr14"])
    spread_t = float(decision_row["spread_price"])
    bid_open_t1 = float(future_rows.iloc[0]["open"])
    bid_high = future_rows["high"].to_numpy(dtype=float)
    bid_low = future_rows["low"].to_numpy(dtype=float)
    bid_close = future_rows["close"].to_numpy(dtype=float)
    spread_future = future_rows["spread_price"].to_numpy(dtype=float)

    if direction == "LONG":
        effective_entry = bid_open_t1 + spread_t + slip_price
        sl_prices = effective_entry - (k_sl_grid * atr14_t)
        tp_prices = effective_entry + (k_tp_grid * atr14_t)

        sl_hit_idx = np.full(k_sl_grid.shape[0], HOLD_MAX + 1, dtype=np.int16)
        tp_hit_idx = np.full(k_tp_grid.shape[0], HOLD_MAX + 1, dtype=np.int16)
        for idx, sl_price in enumerate(sl_prices):
            hits = np.flatnonzero(bid_low <= sl_price)
            if hits.size:
                sl_hit_idx[idx] = int(hits[0]) + 1
        for idx, tp_price in enumerate(tp_prices):
            hits = np.flatnonzero(bid_high >= tp_price)
            if hits.size:
                tp_hit_idx[idx] = int(hits[0]) + 1

        sl_first = sl_hit_idx[:, None] <= tp_hit_idx[None, :]
        natural_exit_hold = np.where(sl_first, sl_hit_idx[:, None], tp_hit_idx[None, :]).astype(np.int16)
        hit_exit_price = np.where(sl_first, sl_prices[:, None] - slip_price, tp_prices[None, :] - slip_price)
        hit_raw_pnl = hit_exit_price - effective_entry
        hold_exit_price = bid_close[: hold_grid.shape[0]] - slip_price
        hold_raw_pnl = hold_exit_price[None, :] - effective_entry
    else:
        effective_entry = bid_open_t1 - slip_price
        sl_prices = effective_entry + (k_sl_grid * atr14_t)
        tp_prices = effective_entry - (k_tp_grid * atr14_t)
        ask_high = bid_high + spread_future
        ask_low = bid_low + spread_future

        sl_hit_idx = np.full(k_sl_grid.shape[0], HOLD_MAX + 1, dtype=np.int16)
        tp_hit_idx = np.full(k_tp_grid.shape[0], HOLD_MAX + 1, dtype=np.int16)
        for idx, sl_price in enumerate(sl_prices):
            hits = np.flatnonzero(ask_high >= sl_price)
            if hits.size:
                sl_hit_idx[idx] = int(hits[0]) + 1
        for idx, tp_price in enumerate(tp_prices):
            hits = np.flatnonzero(ask_low <= tp_price)
            if hits.size:
                tp_hit_idx[idx] = int(hits[0]) + 1

        sl_first = sl_hit_idx[:, None] <= tp_hit_idx[None, :]
        natural_exit_hold = np.where(sl_first, sl_hit_idx[:, None], tp_hit_idx[None, :]).astype(np.int16)
        hit_exit_price = np.where(sl_first, sl_prices[:, None] + slip_price, tp_prices[None, :] + slip_price)
        hit_raw_pnl = effective_entry - hit_exit_price
        hold_exit_price = bid_close[: hold_grid.shape[0]] + spread_future[: hold_grid.shape[0]] + slip_price
        hold_raw_pnl = effective_entry - hold_exit_price[None, :]

    sl_dist = k_sl_grid * atr14_t
    hit_r = hit_raw_pnl / sl_dist[:, None]
    hold_r = hold_raw_pnl / sl_dist[:, None]

    holds = hold_grid[None, None, :]
    use_hit = holds >= natural_exit_hold[:, :, None]
    r_cube = np.where(use_hit, hit_r[:, :, None], hold_r[:, None, :])
    actual_hold_cube = np.where(use_hit, natural_exit_hold[:, :, None], holds).astype(np.int16)
    exit_type_cube = np.where(use_hit, np.where(sl_first[:, :, None], "SL", "TP"), "HOLD_EXPIRE")

    best_flat_idx = int(np.argmax(r_cube))
    k_sl_idx, k_tp_idx, hold_idx = np.unravel_index(best_flat_idx, r_cube.shape)

    return {
        "direction": direction,
        "best_r": float(r_cube[k_sl_idx, k_tp_idx, hold_idx]),
        "k_sl": float(k_sl_grid[k_sl_idx]),
        "k_tp": float(k_tp_grid[k_tp_idx]),
        "hold": int(hold_grid[hold_idx]),
        "actual_hold": int(actual_hold_cube[k_sl_idx, k_tp_idx, hold_idx]),
        "exit_type": str(exit_type_cube[k_sl_idx, k_tp_idx, hold_idx]),
    }


def select_best_direction(
    long_result: dict[str, Any],
    short_result: dict[str, Any],
    cand_long: int,
    cand_short: int,
) -> dict[str, Any]:
    long_r = float(long_result["best_r"])
    short_r = float(short_result["best_r"])

    if not math.isclose(long_r, short_r, rel_tol=0.0, abs_tol=1e-12):
        return long_result if long_r > short_r else short_result

    if cand_long == 1 and cand_short == 0:
        return long_result
    if cand_short == 1 and cand_long == 0:
        return short_result
    return long_result


def finalize_labels_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()

    int8_cols = ["regime_id", "cand_long", "cand_short", "future_has_gap", "label_requires_flip", "label_dir_int"]
    int16_cols = ["best_actual_hold", "slip_points", "H"]
    nullable_int16_cols = ["hold_L", "hold_S"]
    int64_cols = ["sample_index", "window_start_idx", "window_end_idx"]

    for col in int8_cols:
        out[col] = out[col].astype(np.int8)
    for col in int16_cols:
        out[col] = out[col].astype(np.int16)
    for col in nullable_int16_cols:
        out[col] = out[col].astype("Int16")
    for col in int64_cols:
        out[col] = out[col].astype(np.int64)

    return out


def build_labels(
    features: pd.DataFrame,
    config: Step11Config,
    pack_meta: PackMeta,
    static_meta: dict[str, Any],
    point_size: float,
) -> pd.DataFrame:
    k_sl_grid = np.arange(0.5, 6.0 + 0.001, 0.5, dtype=float)
    k_tp_grid = np.arange(0.5, 12.0 + 0.001, 0.5, dtype=float)
    hold_grid = np.arange(1, config.lookahead_bars + 1, dtype=np.int16)
    slip_price = config.slip_points * point_size

    gap_prev, gap_next = build_gap_flags(features["bar_time"])
    gap_prev_cumsum = build_cumulative_flags(gap_prev)

    labels: list[dict[str, Any]] = []
    sample_index = 0
    total_rows = features.shape[0]
    start_idx = max(config.warmup_bars - 1, WINDOW_SIZE - 1)
    end_idx = total_rows - config.lookahead_bars - 1

    for t in range(start_idx, end_idx + 1):
        if has_any_true(gap_prev_cumsum, t - (WINDOW_SIZE - 1) + 1, t):
            continue
        if gap_next[t]:
            continue

        future_rows = features.iloc[t + 1 : t + 1 + config.lookahead_bars]
        if future_rows.shape[0] != config.lookahead_bars:
            continue

        decision_row = features.iloc[t]
        cand_long = int(decision_row["cand_long"])
        cand_short = int(decision_row["cand_short"])
        regime_id = int(decision_row["regime_id"])
        future_has_gap = int(bool(np.any(gap_prev[t + 2 : t + config.lookahead_bars + 1])))

        label: dict[str, Any] = {
            "sample_index": sample_index,
            "bar_time": decision_row["bar_time"],
            "symbol": static_meta["symbol"],
            "window_start_idx": int(t - (WINDOW_SIZE - 1)),
            "window_end_idx": int(t),
            "regime_id": regime_id,
            "cand_long": cand_long,
            "cand_short": cand_short,
            "dist_atr_max_t": float(decision_row["dist_atr_max_t"]),
            "spread_t": float(decision_row["spread_price"]),
            "atr14_t": float(decision_row["atr14"]),
            "cost_price": float(decision_row["spread_price"] + (2.0 * slip_price)),
            "entry_price": float(features.iloc[t + 1]["open"]),
            "search_space_version": config.search_space_version,
            "cost_model_version": pack_meta.cost_model_version,
            "candidate_policy_version": pack_meta.candidate_policy_version,
            "regime_policy_version": pack_meta.regime_policy_version,
            "R_pass_buffer": float(config.r_pass_buffer),
            "slip_points": int(config.slip_points),
            "H": int(config.lookahead_bars),
            "future_has_gap": future_has_gap,
            "label_requires_flip": 0,
        }

        if cand_long == 0 and cand_short == 0:
            label.update(
                {
                    "label_dir": "PASS",
                    "label_dir_int": 2,
                    "best_R": 0.0,
                    "best_exit_type": "PASS_FORCED",
                    "best_actual_hold": 0,
                    "k_sl_L": PASS_DEFAULT_K_SL,
                    "k_tp_L": PASS_DEFAULT_K_TP,
                    "hold_L": PASS_DEFAULT_HOLD,
                    "k_sl_S": PASS_DEFAULT_K_SL,
                    "k_tp_S": PASS_DEFAULT_K_TP,
                    "hold_S": PASS_DEFAULT_HOLD,
                }
            )
            labels.append(label)
            sample_index += 1
            continue

        long_result = action_search_for_direction("LONG", decision_row, future_rows, k_sl_grid, k_tp_grid, hold_grid, slip_price)
        short_result = action_search_for_direction("SHORT", decision_row, future_rows, k_sl_grid, k_tp_grid, hold_grid, slip_price)
        best = select_best_direction(long_result, short_result, cand_long, cand_short)

        requires_flip = int(
            (cand_long == 1 and best["direction"] == "SHORT")
            or (cand_short == 1 and best["direction"] == "LONG")
        )

        label_dir = "PASS" if best["best_r"] <= config.r_pass_buffer else best["direction"]
        label_dir_int = 2 if label_dir == "PASS" else (0 if label_dir == "LONG" else 1)
        label.update(
            {
                "label_dir": label_dir,
                "label_dir_int": label_dir_int,
                "best_R": float(best["best_r"]),
                "best_exit_type": str(best["exit_type"]),
                "best_actual_hold": int(best["actual_hold"]),
                "k_sl_L": float(best["k_sl"]) if best["direction"] == "LONG" else math.nan,
                "k_tp_L": float(best["k_tp"]) if best["direction"] == "LONG" else math.nan,
                "hold_L": int(best["hold"]) if best["direction"] == "LONG" else math.nan,
                "k_sl_S": float(best["k_sl"]) if best["direction"] == "SHORT" else math.nan,
                "k_tp_S": float(best["k_tp"]) if best["direction"] == "SHORT" else math.nan,
                "hold_S": int(best["hold"]) if best["direction"] == "SHORT" else math.nan,
                "label_requires_flip": requires_flip,
            }
        )
        labels.append(label)
        sample_index += 1

    if not labels:
        raise ValueError("no labels generated; input range is too short")

    return finalize_labels_frame(pd.DataFrame(labels))

def metadata_summary(
    config: Step11Config,
    static_meta: dict[str, Any],
    pack_meta: PackMeta,
    point_size: float,
    input_files: list[Path],
    features: pd.DataFrame,
    labels: pd.DataFrame,
    validation: dict[str, Any],
) -> dict[str, Any]:
    label_distribution = {key: int(value) for key, value in labels["label_dir"].value_counts(dropna=False).sort_index().items()}
    flip_distribution = {
        "requires_flip_0": int((labels["label_requires_flip"] == 0).sum()),
        "requires_flip_1": int((labels["label_requires_flip"] == 1).sum()),
    }
    forced_pass_count = int(((labels["cand_long"] == 0) & (labels["cand_short"] == 0) & (labels["label_dir"] == "PASS")).sum())

    return {
        "schema_version": pack_meta.schema_version,
        "model_pack_version": pack_meta.model_pack_version,
        "candidate_policy_version": pack_meta.candidate_policy_version,
        "regime_policy_version": pack_meta.regime_policy_version,
        "cost_model_version": pack_meta.cost_model_version,
        "search_space_version": config.search_space_version,
        "tie_policy": "candidate_preferred_then_long",
        "symbol": static_meta["symbol"],
        "timeframe": static_meta["timeframe"],
        "price_basis": static_meta["price_basis"],
        "point_size": point_size,
        "slip_points": config.slip_points,
        "slip_price": config.slip_points * point_size,
        "R_pass_buffer": config.r_pass_buffer,
        "H": config.lookahead_bars,
        "warmup_bars": config.warmup_bars,
        "atr_thr": pack_meta.atr_thr,
        "adx_thr1": pack_meta.adx_thr1,
        "adx_thr2": pack_meta.adx_thr2,
        "thr_method": pack_meta.thr_method,
        "thr_seed": pack_meta.thr_seed,
        "thr_notes": pack_meta.thr_notes,
        "dist_atr_max_mode": pack_meta.dist_atr_max_mode,
        "dist_atr_max_q": pack_meta.dist_atr_max_q,
        "dist_atr_max_w": pack_meta.dist_atr_max_w,
        "dist_atr_max_clamp_lo": pack_meta.dist_atr_max_clamp_lo,
        "dist_atr_max_clamp_hi": pack_meta.dist_atr_max_clamp_hi,
        "data_start": str(features["bar_time"].min()),
        "data_end": str(features["bar_time"].max()),
        "total_bars": int(features.shape[0]),
        "total_labeled_samples": int(labels.shape[0]),
        "forced_pass_count": forced_pass_count,
        "label_distribution": label_distribution,
        "flip_distribution": flip_distribution,
        "input_files": [str(path) for path in input_files],
        "validation": validation,
    }


def write_outputs(output_dir: Path, features: pd.DataFrame, labels: pd.DataFrame, metadata: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_dir / "features.parquet", index=False)
    labels.to_parquet(output_dir / "labels.parquet", index=False)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    config = parse_args()
    pack_meta = load_pack_meta(config.pack_meta_path)
    input_files = collect_bar_log_files(config.input_path)
    raw_df = read_bar_logs(input_files)
    filtered_df = filter_bar_logs(raw_df, config)
    static_meta = validate_static_metadata(filtered_df, pack_meta)
    point_size = infer_point_size(filtered_df, config.point_size)
    features = build_feature_frame(filtered_df, point_size)
    validation = validate_feature_integrity(features, pack_meta, config.warmup_bars)
    assert_validation_pass(validation)
    labels = build_labels(features, config, pack_meta, static_meta, point_size)
    metadata = metadata_summary(config, static_meta, pack_meta, point_size, input_files, features, labels, validation)
    write_outputs(config.output_dir, features, labels, metadata)

    print(f"STEP11 complete: {labels.shape[0]} labeled samples")
    print(f"features.parquet: {config.output_dir / 'features.parquet'}")
    print(f"labels.parquet: {config.output_dir / 'labels.parquet'}")
    print(f"metadata.json: {config.output_dir / 'metadata.json'}")
    print(f"label_distribution: {metadata['label_distribution']}")
    print(f"flip_distribution: {metadata['flip_distribution']}")
    return 0
