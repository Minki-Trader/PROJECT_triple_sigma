from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.multioutput import MultiOutputRegressor

from .step12 import (
    EPSILON,
    FEATURE_COLUMNS,
    FEATURE_DIM,
    SCALED_FEATURE_COLUMNS,
    SCALED_FEATURE_DIM,
    ScalerStats,
    Step11Bundle,
    WINDOW_SIZE,
    build_scaled_windows,
    json_ready,
    load_step11_bundle,
    write_json,
)


LONG_TARGET_COLUMNS = ("k_sl_L", "k_tp_L", "hold_L")
SHORT_TARGET_COLUMNS = ("k_sl_S", "k_tp_S", "hold_S")
HEAD_OUTPUT_COLUMNS = ("k_sl", "k_tp", "hold")
STAGE2_OUTPUT_ORDER = ("k_sl_L", "k_tp_L", "hold_L", "k_sl_S", "k_tp_S", "hold_S")
DEFAULT_PARAM_VECTOR = np.array([1.5, 2.0, 24.0], dtype=np.float32)
LOWER_BOUNDS = np.array([0.5, 0.5, 1.0], dtype=np.float64)
UPPER_BOUNDS = np.array([6.0, 12.0, 72.0], dtype=np.float64)
HUBER_DELTAS = np.array([0.25, 0.50, 2.00], dtype=np.float64)

STEP13_REQUIRED_LABEL_COLUMNS = [
    "best_R",
    *LONG_TARGET_COLUMNS,
    *SHORT_TARGET_COLUMNS,
]


@dataclass(frozen=True)
class Step13Config:
    step11_dir: Path
    step12_dir: Path
    output_dir: Path
    min_train_samples_per_head: int
    min_val_samples_per_head: int
    pass_row_weight: float
    gbr_n_estimators: int
    gbr_learning_rate: float
    gbr_max_depth: int
    gbr_min_samples_leaf: int
    gbr_subsample: float
    gbr_alpha: float
    seed: int
    model_name: str
    fail_on_acceptance: bool


@dataclass(frozen=True)
class Step12Context:
    split_plan: dict[str, Any]
    scaler_stats: dict[str, Any]
    scaler: ScalerStats
    training_metadata: dict[str, Any]


@dataclass(frozen=True)
class SplitReuseAudit:
    passed: bool
    train_count: int
    val_count: int
    dropped_count: int
    train_counts_by_regime: dict[str, int]
    val_counts_by_regime: dict[str, int]
    dropped_counts_by_regime: dict[str, int]
    train_end_time: str | None
    val_start_time: str | None
    no_time_leakage: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "dropped_count": self.dropped_count,
            "train_counts_by_regime": self.train_counts_by_regime,
            "val_counts_by_regime": self.val_counts_by_regime,
            "dropped_counts_by_regime": self.dropped_counts_by_regime,
            "train_end_time": self.train_end_time,
            "val_start_time": self.val_start_time,
            "no_time_leakage": self.no_time_leakage,
        }


@dataclass(frozen=True)
class Stage2Audit:
    cand1_only: bool
    masking_integrity: bool
    total_candidate_rows: int
    retained_rows: int
    dropped_rows: int
    train_rows: int
    val_rows: int
    rows_by_regime: dict[str, int]
    rows_by_target_side: dict[str, int]
    train_rows_by_regime: dict[str, int]
    val_rows_by_regime: dict[str, int]
    non_pass_rows_matching_target_side: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "cand1_only": self.cand1_only,
            "masking_integrity": self.masking_integrity,
            "total_candidate_rows": self.total_candidate_rows,
            "retained_rows": self.retained_rows,
            "dropped_rows": self.dropped_rows,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "rows_by_regime": self.rows_by_regime,
            "rows_by_target_side": self.rows_by_target_side,
            "train_rows_by_regime": self.train_rows_by_regime,
            "val_rows_by_regime": self.val_rows_by_regime,
            "non_pass_rows_matching_target_side": self.non_pass_rows_matching_target_side,
        }


@dataclass
class DirectionHeadBundle:
    side: str
    status: str
    target_columns: tuple[str, str, str]
    default_vector: list[float]
    model: MultiOutputRegressor | None
    train_count: int
    val_count: int
    fallback_reason: str | None
    train_metrics: dict[str, Any] | None
    val_metrics: dict[str, Any] | None


@dataclass
class Stage2Bundle:
    prm_version: str
    model_name: str
    regime_id: int
    window_size: int
    feature_dim: int
    feature_columns: list[str]
    scaled_feature_columns: list[str]
    output_order: list[str]
    long_head: DirectionHeadBundle
    short_head: DirectionHeadBundle

    def predict_raw(self, X: np.ndarray) -> np.ndarray:
        long_pred = predict_direction_head(self.long_head, X)
        short_pred = predict_direction_head(self.short_head, X)
        return np.concatenate([long_pred, short_pred], axis=1).astype(np.float32, copy=False)

    def predict_effective(self, X: np.ndarray) -> np.ndarray:
        return postprocess_stage2_matrix(self.predict_raw(X))


@dataclass(frozen=True)
class DirectionTrainingResult:
    side: str
    status: str
    train_count: int
    val_count: int
    target_columns: tuple[str, str, str]
    fallback_reason: str | None
    model: MultiOutputRegressor | None
    train_metrics: dict[str, Any] | None
    val_metrics: dict[str, Any] | None
    sample_weight_summary: dict[str, Any]


@dataclass(frozen=True)
class RegimeTrainingResult:
    regime_id: int
    status: str
    bundle_path: str
    report_path: str
    long_result: DirectionTrainingResult
    short_result: DirectionTrainingResult

    def summary_row(self) -> dict[str, Any]:
        row = {
            "regime_id": self.regime_id,
            "status": self.status,
            "bundle_path": self.bundle_path,
            "report_path": self.report_path,
            "long_status": self.long_result.status,
            "long_train_count": self.long_result.train_count,
            "long_val_count": self.long_result.val_count,
            "long_fallback_reason": self.long_result.fallback_reason,
            "short_status": self.short_result.status,
            "short_train_count": self.short_result.train_count,
            "short_val_count": self.short_result.val_count,
            "short_fallback_reason": self.short_result.fallback_reason,
        }
        if self.long_result.val_metrics is not None:
            row["long_val_norm_mae"] = self.long_result.val_metrics["normalized_effective_mae_mean"]
            row["long_val_hold_boundary_rate"] = self.long_result.val_metrics["hold_boundary_rate"]
            row["long_beats_default"] = self.long_result.val_metrics["beats_default_baseline"]
        else:
            row["long_val_norm_mae"] = None
            row["long_val_hold_boundary_rate"] = None
            row["long_beats_default"] = None
        if self.short_result.val_metrics is not None:
            row["short_val_norm_mae"] = self.short_result.val_metrics["normalized_effective_mae_mean"]
            row["short_val_hold_boundary_rate"] = self.short_result.val_metrics["hold_boundary_rate"]
            row["short_beats_default"] = self.short_result.val_metrics["beats_default_baseline"]
        else:
            row["short_val_norm_mae"] = None
            row["short_val_hold_boundary_rate"] = None
            row["short_beats_default"] = None
        return row


def parse_args() -> Step13Config:
    parser = argparse.ArgumentParser(description="STEP13 baseline Stage2 training for Triple Sigma.")
    parser.add_argument("--step11-dir", required=True, help="STEP11 output directory")
    parser.add_argument("--step12-dir", required=True, help="STEP12 output directory")
    parser.add_argument("--output-dir", required=True, help="STEP13 output directory")
    parser.add_argument("--min-train-samples-per-head", type=int, default=12)
    parser.add_argument("--min-val-samples-per-head", type=int, default=4)
    parser.add_argument("--pass-row-weight", type=float, default=0.25)
    parser.add_argument("--gbr-n-estimators", type=int, default=120)
    parser.add_argument("--gbr-learning-rate", type=float, default=0.05)
    parser.add_argument("--gbr-max-depth", type=int, default=2)
    parser.add_argument("--gbr-min-samples-leaf", type=int, default=8)
    parser.add_argument("--gbr-subsample", type=float, default=0.80)
    parser.add_argument("--gbr-alpha", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-name", default="gbr_huber_masked_v1")
    parser.add_argument("--fail-on-acceptance", action="store_true")
    args = parser.parse_args()

    if args.min_train_samples_per_head <= 0 or args.min_val_samples_per_head < 0:
        raise ValueError("min_train_samples_per_head must be > 0 and min_val_samples_per_head must be >= 0")
    if not 0.0 < args.pass_row_weight <= 1.0:
        raise ValueError("pass_row_weight must be in (0, 1]")
    if args.gbr_n_estimators <= 0 or args.gbr_max_depth <= 0 or args.gbr_min_samples_leaf <= 0:
        raise ValueError("GBR hyperparameters must be positive")
    if not 0.0 < args.gbr_learning_rate <= 1.0:
        raise ValueError("gbr_learning_rate must be in (0, 1]")
    if not 0.0 < args.gbr_subsample <= 1.0:
        raise ValueError("gbr_subsample must be in (0, 1]")
    if not 0.0 < args.gbr_alpha < 1.0:
        raise ValueError("gbr_alpha must be in (0, 1)")

    return Step13Config(
        step11_dir=Path(args.step11_dir),
        step12_dir=Path(args.step12_dir),
        output_dir=Path(args.output_dir),
        min_train_samples_per_head=args.min_train_samples_per_head,
        min_val_samples_per_head=args.min_val_samples_per_head,
        pass_row_weight=args.pass_row_weight,
        gbr_n_estimators=args.gbr_n_estimators,
        gbr_learning_rate=args.gbr_learning_rate,
        gbr_max_depth=args.gbr_max_depth,
        gbr_min_samples_leaf=args.gbr_min_samples_leaf,
        gbr_subsample=args.gbr_subsample,
        gbr_alpha=args.gbr_alpha,
        seed=args.seed,
        model_name=args.model_name,
        fail_on_acceptance=args.fail_on_acceptance,
    )


def serialize_timestamp(value: pd.Timestamp | Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def load_step12_context(step12_dir: Path) -> Step12Context:
    split_plan_path = step12_dir / "split_plan.json"
    scaler_stats_path = step12_dir / "scaler_stats.json"
    training_metadata_path = step12_dir / "training_metadata.json"
    for path in (split_plan_path, scaler_stats_path, training_metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"required STEP12 artifact not found: {path}")

    split_plan = json.loads(split_plan_path.read_text(encoding="utf-8"))
    scaler_stats = json.loads(scaler_stats_path.read_text(encoding="utf-8"))
    training_metadata = json.loads(training_metadata_path.read_text(encoding="utf-8"))

    step12_acceptance = training_metadata.get("acceptance", {})
    if not step12_acceptance.get("A1_no_time_leakage", False):
        raise ValueError("STEP12 acceptance.A1_no_time_leakage must be true before STEP13")
    if training_metadata.get("scaler_source") != "global_train_bars":
        raise ValueError("STEP12 scaler_source must be global_train_bars")

    metadata_split_plan = training_metadata.get("split_plan")
    if not isinstance(metadata_split_plan, dict):
        raise ValueError("STEP12 training_metadata missing split_plan")
    if json_ready(metadata_split_plan) != json_ready(split_plan):
        raise ValueError("STEP12 training_metadata.split_plan must exactly match split_plan.json")

    mean = scaler_stats.get("mean")
    std = scaler_stats.get("std")
    if not isinstance(mean, list) or not isinstance(std, list):
        raise ValueError("STEP12 scaler_stats must contain mean/std lists")
    if len(mean) != SCALED_FEATURE_DIM or len(std) != SCALED_FEATURE_DIM:
        raise ValueError("STEP12 scaler_stats mean/std must both have length 12")
    if any((not np.isfinite(value)) for value in mean):
        raise ValueError("STEP12 scaler_stats.mean must be finite")
    if any((not np.isfinite(value)) or value <= 0.0 for value in std):
        raise ValueError("STEP12 scaler_stats.std must be finite and > 0")

    scaler_bar_count = int(training_metadata.get("scaler_bar_count", 0))
    if scaler_bar_count <= 0:
        raise ValueError("STEP12 scaler_bar_count must be > 0")
    replaced_std_indices = [int(value) for value in training_metadata.get("scaler_replaced_std_indices", [])]

    scaler = ScalerStats(
        mean=[float(value) for value in mean],
        std=[float(value) for value in std],
        bar_count=scaler_bar_count,
        replaced_std_indices=replaced_std_indices,
    )
    return Step12Context(
        split_plan=split_plan,
        scaler_stats=scaler_stats,
        scaler=scaler,
        training_metadata=training_metadata,
    )


def count_by_regime(regimes: np.ndarray, mask: np.ndarray, observed_regimes: list[int]) -> dict[str, int]:
    return {str(regime_id): int(np.sum(mask & (regimes == regime_id))) for regime_id in observed_regimes}


def validate_stage2_columns(labels: pd.DataFrame) -> None:
    missing_columns = [column for column in STEP13_REQUIRED_LABEL_COLUMNS if column not in labels.columns]
    if missing_columns:
        raise ValueError(f"STEP11 labels missing STEP13 columns: {missing_columns}")


def rebuild_masks_from_split_plan(
    labels: pd.DataFrame, split_plan: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, SplitReuseAudit]:
    window_end = labels["window_end_idx"].to_numpy(dtype=np.int64)
    regimes = labels["regime_id"].to_numpy(dtype=np.int64)
    label_times = labels["bar_time"].to_numpy()
    observed_regimes = sorted(int(value) for value in np.unique(regimes))

    boundary_window_end_idx = int(split_plan["boundary_window_end_idx"])
    embargo_bars = int(split_plan["embargo_bars"])

    train_mask = window_end + embargo_bars < boundary_window_end_idx
    val_mask = window_end >= boundary_window_end_idx
    dropped_mask = ~(train_mask | val_mask)

    actual_train = int(train_mask.sum())
    actual_val = int(val_mask.sum())
    actual_dropped = int(dropped_mask.sum())
    expected_train = int(split_plan["train_count"])
    expected_val = int(split_plan["val_count"])
    expected_dropped = int(split_plan["dropped_count"])
    if actual_train != expected_train:
        raise ValueError(f"STEP12 split mismatch(train): expected {expected_train}, got {actual_train}")
    if actual_val != expected_val:
        raise ValueError(f"STEP12 split mismatch(val): expected {expected_val}, got {actual_val}")
    if actual_dropped != expected_dropped:
        raise ValueError(f"STEP12 split mismatch(dropped): expected {expected_dropped}, got {actual_dropped}")

    actual_train_counts = count_by_regime(regimes, train_mask, observed_regimes)
    actual_val_counts = count_by_regime(regimes, val_mask, observed_regimes)
    actual_dropped_counts = count_by_regime(regimes, dropped_mask, observed_regimes)
    if json_ready(actual_train_counts) != json_ready(split_plan.get("train_counts_by_regime", {})):
        raise ValueError("STEP12 split mismatch(train_counts_by_regime)")
    if json_ready(actual_val_counts) != json_ready(split_plan.get("val_counts_by_regime", {})):
        raise ValueError("STEP12 split mismatch(val_counts_by_regime)")
    if json_ready(actual_dropped_counts) != json_ready(split_plan.get("dropped_counts_by_regime", {})):
        raise ValueError("STEP12 split mismatch(dropped_counts_by_regime)")

    train_end_time = serialize_timestamp(label_times[train_mask][-1]) if actual_train else None
    val_start_time = serialize_timestamp(label_times[val_mask][0]) if actual_val else None
    if train_end_time != split_plan.get("train_end_time"):
        raise ValueError(
            "STEP12 split mismatch(train_end_time): "
            f"expected {split_plan.get('train_end_time')}, got {train_end_time}"
        )
    if val_start_time != split_plan.get("val_start_time"):
        raise ValueError(
            "STEP12 split mismatch(val_start_time): "
            f"expected {split_plan.get('val_start_time')}, got {val_start_time}"
        )

    no_time_leakage = True
    if actual_train and actual_val:
        max_train_end = int(window_end[train_mask].max())
        min_val_end = int(window_end[val_mask].min())
        no_time_leakage = bool(max_train_end + embargo_bars < min_val_end)
    if no_time_leakage != bool(split_plan.get("no_time_leakage", False)):
        raise ValueError("STEP12 split mismatch(no_time_leakage)")

    audit = SplitReuseAudit(
        passed=True,
        train_count=actual_train,
        val_count=actual_val,
        dropped_count=actual_dropped,
        train_counts_by_regime=actual_train_counts,
        val_counts_by_regime=actual_val_counts,
        dropped_counts_by_regime=actual_dropped_counts,
        train_end_time=train_end_time,
        val_start_time=val_start_time,
        no_time_leakage=no_time_leakage,
    )
    return train_mask, val_mask, dropped_mask, audit


def build_stage2_frame(
    labels: pd.DataFrame, train_mask: np.ndarray, val_mask: np.ndarray
) -> tuple[pd.DataFrame, Stage2Audit]:
    validate_stage2_columns(labels)

    cand_xor = labels["cand_long"].to_numpy(dtype=np.int64) + labels["cand_short"].to_numpy(dtype=np.int64)
    cand1_mask = cand_xor == 1
    if not np.isin(cand_xor, [0, 1]).all():
        raise ValueError("cand_long/cand_short must satisfy one-hot-or-zero before STEP13")

    stage2 = labels.loc[cand1_mask].copy()
    stage2["label_row_idx"] = stage2.index.to_numpy(dtype=np.int64)
    stage2["split"] = np.where(
        train_mask[stage2["label_row_idx"]],
        "train",
        np.where(val_mask[stage2["label_row_idx"]], "val", "drop"),
    )
    dropped_rows = int((stage2["split"] == "drop").sum())
    stage2 = stage2.loc[stage2["split"] != "drop"].reset_index(drop=True)

    long_valid = stage2["k_sl_L"].notna() & stage2["k_tp_L"].notna() & stage2["hold_L"].notna()
    short_valid = stage2["k_sl_S"].notna() & stage2["k_tp_S"].notna() & stage2["hold_S"].notna()
    masking_integrity = bool((long_valid ^ short_valid).all())
    if not masking_integrity:
        bad = stage2.loc[~(long_valid ^ short_valid), ["sample_index", "regime_id", "cand_long", "cand_short"]]
        raise ValueError(f"STEP13 target-side integrity failed for rows: {bad.head(5).to_dict(orient='records')}")

    stage2["target_side"] = np.where(long_valid, "LONG", "SHORT")
    stage2["target_k_sl"] = np.where(long_valid, stage2["k_sl_L"], stage2["k_sl_S"])
    stage2["target_k_tp"] = np.where(long_valid, stage2["k_tp_L"], stage2["k_tp_S"])
    stage2["target_hold"] = np.where(long_valid, stage2["hold_L"], stage2["hold_S"])

    target_values = stage2.loc[:, ["target_k_sl", "target_k_tp", "target_hold"]].to_numpy(dtype=np.float64)
    if not np.isfinite(target_values).all():
        raise ValueError("STEP13 target columns must be finite after masking")

    non_pass = stage2["label_dir"].isin(["LONG", "SHORT"])
    non_pass_target_side_match = bool((stage2.loc[non_pass, "label_dir"] == stage2.loc[non_pass, "target_side"]).all())

    rows_by_regime = {str(regime_id): 0 for regime_id in range(6)}
    for regime_id, count in stage2["regime_id"].value_counts(sort=False).sort_index().items():
        rows_by_regime[str(regime_id)] = int(count)

    rows_by_target_side = {"LONG": 0, "SHORT": 0}
    for side, count in stage2["target_side"].value_counts(sort=False).sort_index().items():
        rows_by_target_side[str(side)] = int(count)

    train_rows_by_regime = {str(regime_id): 0 for regime_id in range(6)}
    for regime_id, count in stage2.loc[stage2["split"] == "train", "regime_id"].value_counts(sort=False).sort_index().items():
        train_rows_by_regime[str(regime_id)] = int(count)

    val_rows_by_regime = {str(regime_id): 0 for regime_id in range(6)}
    for regime_id, count in stage2.loc[stage2["split"] == "val", "regime_id"].value_counts(sort=False).sort_index().items():
        val_rows_by_regime[str(regime_id)] = int(count)

    retained_cand1_only = bool(
        (
            stage2["cand_long"].to_numpy(dtype=np.int64) + stage2["cand_short"].to_numpy(dtype=np.int64)
        == 1
        ).all()
    )

    audit = Stage2Audit(
        cand1_only=retained_cand1_only,
        masking_integrity=masking_integrity,
        total_candidate_rows=int(cand1_mask.sum()),
        retained_rows=int(len(stage2)),
        dropped_rows=dropped_rows,
        train_rows=int((stage2["split"] == "train").sum()),
        val_rows=int((stage2["split"] == "val").sum()),
        rows_by_regime=rows_by_regime,
        rows_by_target_side=rows_by_target_side,
        train_rows_by_regime=train_rows_by_regime,
        val_rows_by_regime=val_rows_by_regime,
        non_pass_rows_matching_target_side=non_pass_target_side_match,
    )
    return stage2, audit


def build_stage2_sample_weights(frame: pd.DataFrame, pass_row_weight: float) -> np.ndarray:
    weights = np.ones(len(frame), dtype=np.float64)
    pass_mask = (frame["label_dir"] == "PASS").to_numpy(dtype=bool)
    weights[pass_mask] *= pass_row_weight
    mean_weight = float(weights.mean())
    if mean_weight > EPSILON:
        weights /= mean_weight
    return weights


def make_direction_regressor(config: Step13Config, random_state: int) -> MultiOutputRegressor:
    base = GradientBoostingRegressor(
        loss="huber",
        alpha=config.gbr_alpha,
        n_estimators=config.gbr_n_estimators,
        learning_rate=config.gbr_learning_rate,
        max_depth=config.gbr_max_depth,
        min_samples_leaf=config.gbr_min_samples_leaf,
        subsample=config.gbr_subsample,
        max_features="sqrt",
        random_state=random_state,
    )
    return MultiOutputRegressor(base)


def predict_direction_head(head: DirectionHeadBundle, X: np.ndarray) -> np.ndarray:
    if head.model is None:
        default_vec = np.asarray(head.default_vector, dtype=np.float32).reshape(1, 3)
        return np.repeat(default_vec, len(X), axis=0)
    return np.asarray(head.model.predict(X), dtype=np.float32)


def postprocess_direction_matrix(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=np.float64).copy()
    out[:, 0] = np.clip(out[:, 0], LOWER_BOUNDS[0], UPPER_BOUNDS[0])
    out[:, 1] = np.clip(out[:, 1], LOWER_BOUNDS[1], UPPER_BOUNDS[1])
    out[:, 2] = np.clip(np.rint(out[:, 2]), LOWER_BOUNDS[2], UPPER_BOUNDS[2])
    return out.astype(np.float32, copy=False)


def postprocess_stage2_matrix(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != len(STAGE2_OUTPUT_ORDER):
        raise ValueError(f"stage2 matrix must have shape [N,6], got {values.shape}")
    long_eff = postprocess_direction_matrix(values[:, :3])
    short_eff = postprocess_direction_matrix(values[:, 3:])
    return np.concatenate([long_eff, short_eff], axis=1).astype(np.float32, copy=False)


def huber_loss_per_target(y_true: np.ndarray, y_pred: np.ndarray) -> list[float]:
    errors = np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred, dtype=np.float64)
    out: list[float] = []
    for idx, delta in enumerate(HUBER_DELTAS):
        abs_error = np.abs(errors[:, idx])
        loss = np.where(abs_error <= delta, 0.5 * (errors[:, idx] ** 2), delta * (abs_error - 0.5 * delta))
        out.append(float(np.mean(loss)))
    return out


def compute_direction_metrics(y_true: np.ndarray, raw_pred: np.ndarray, baseline_pred: np.ndarray) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=np.float64)
    raw_pred = np.asarray(raw_pred, dtype=np.float64)
    baseline_pred = np.asarray(baseline_pred, dtype=np.float64)
    if len(y_true) == 0:
        raise ValueError("compute_direction_metrics requires at least one sample")

    effective_pred = postprocess_direction_matrix(raw_pred)
    effective_baseline = postprocess_direction_matrix(baseline_pred)

    raw_mae = mean_absolute_error(y_true, raw_pred, multioutput="raw_values")
    effective_mae = mean_absolute_error(y_true, effective_pred, multioutput="raw_values")
    baseline_effective_mae = mean_absolute_error(y_true, effective_baseline, multioutput="raw_values")

    normalized_effective_mae = effective_mae / (UPPER_BOUNDS - LOWER_BOUNDS)
    normalized_baseline_effective_mae = baseline_effective_mae / (UPPER_BOUNDS - LOWER_BOUNDS)
    hold_raw = raw_pred[:, 2]

    metrics = {
        "count": int(len(y_true)),
        "raw_mae": {name: float(raw_mae[idx]) for idx, name in enumerate(HEAD_OUTPUT_COLUMNS)},
        "effective_mae": {name: float(effective_mae[idx]) for idx, name in enumerate(HEAD_OUTPUT_COLUMNS)},
        "baseline_effective_mae": {
            name: float(baseline_effective_mae[idx]) for idx, name in enumerate(HEAD_OUTPUT_COLUMNS)
        },
        "raw_huber": {
            name: value for name, value in zip(HEAD_OUTPUT_COLUMNS, huber_loss_per_target(y_true, raw_pred), strict=True)
        },
        "normalized_effective_mae": {
            name: float(normalized_effective_mae[idx]) for idx, name in enumerate(HEAD_OUTPUT_COLUMNS)
        },
        "normalized_effective_mae_mean": float(np.mean(normalized_effective_mae)),
        "baseline_normalized_effective_mae_mean": float(np.mean(normalized_baseline_effective_mae)),
        "beats_default_baseline": bool(np.mean(normalized_effective_mae) <= np.mean(normalized_baseline_effective_mae)),
        "k_sl_low_clip_rate": float(np.mean(raw_pred[:, 0] < LOWER_BOUNDS[0])),
        "k_sl_high_clip_rate": float(np.mean(raw_pred[:, 0] > UPPER_BOUNDS[0])),
        "k_tp_low_clip_rate": float(np.mean(raw_pred[:, 1] < LOWER_BOUNDS[1])),
        "k_tp_high_clip_rate": float(np.mean(raw_pred[:, 1] > UPPER_BOUNDS[1])),
        "hold_low_clip_rate": float(np.mean(hold_raw < LOWER_BOUNDS[2])),
        "hold_high_clip_rate": float(np.mean(hold_raw > UPPER_BOUNDS[2])),
        "hold_round_changed_rate": float(np.mean(np.rint(hold_raw) != hold_raw)),
        "hold_boundary_rate": float(
            np.mean((effective_pred[:, 2] <= LOWER_BOUNDS[2]) | (effective_pred[:, 2] >= UPPER_BOUNDS[2]))
        ),
        "raw_nan_count": int(np.isnan(raw_pred).sum()),
        "raw_inf_count": int(np.isinf(raw_pred).sum()),
        "effective_all_finite": bool(np.isfinite(effective_pred).all()),
    }
    return json_ready(metrics)


def train_direction_head(
    side: str,
    regime_id: int,
    X_all: np.ndarray,
    stage2_frame: pd.DataFrame,
    config: Step13Config,
) -> DirectionTrainingResult:
    target_columns = LONG_TARGET_COLUMNS if side == "LONG" else SHORT_TARGET_COLUMNS
    side_frame = stage2_frame[(stage2_frame["regime_id"] == regime_id) & (stage2_frame["target_side"] == side)]
    train_frame = side_frame[side_frame["split"] == "train"].reset_index(drop=True)
    val_frame = side_frame[side_frame["split"] == "val"].reset_index(drop=True)

    X_train = (
        X_all[train_frame["label_row_idx"].to_numpy(dtype=np.int64)]
        if len(train_frame)
        else np.empty((0, X_all.shape[1]), dtype=np.float32)
    )
    X_val = (
        X_all[val_frame["label_row_idx"].to_numpy(dtype=np.int64)]
        if len(val_frame)
        else np.empty((0, X_all.shape[1]), dtype=np.float32)
    )
    y_train = train_frame.loc[:, ["target_k_sl", "target_k_tp", "target_hold"]].to_numpy(dtype=np.float64)
    y_val = val_frame.loc[:, ["target_k_sl", "target_k_tp", "target_hold"]].to_numpy(dtype=np.float64)

    sample_weights = build_stage2_sample_weights(train_frame, config.pass_row_weight) if len(train_frame) else np.empty(0)
    sample_weight_summary = {
        "pass_row_weight": float(config.pass_row_weight),
        "min": float(sample_weights.min()) if len(sample_weights) else 0.0,
        "max": float(sample_weights.max()) if len(sample_weights) else 0.0,
        "mean": float(sample_weights.mean()) if len(sample_weights) else 0.0,
        "pass_count": int((train_frame["label_dir"] == "PASS").sum()) if len(train_frame) else 0,
        "non_pass_count": int((train_frame["label_dir"] != "PASS").sum()) if len(train_frame) else 0,
    }

    baseline_train = np.repeat(DEFAULT_PARAM_VECTOR.reshape(1, 3), len(train_frame), axis=0)
    baseline_val = np.repeat(DEFAULT_PARAM_VECTOR.reshape(1, 3), len(val_frame), axis=0)

    fallback_reasons: list[str] = []
    if len(train_frame) < config.min_train_samples_per_head:
        fallback_reasons.append(
            f"train_count={len(train_frame)} < min_train_samples_per_head={config.min_train_samples_per_head}"
        )
    if len(val_frame) < config.min_val_samples_per_head:
        fallback_reasons.append(f"val_count={len(val_frame)} < min_val_samples_per_head={config.min_val_samples_per_head}")

    if fallback_reasons:
        return DirectionTrainingResult(
            side=side,
            status="fallback_constant",
            train_count=int(len(train_frame)),
            val_count=int(len(val_frame)),
            target_columns=target_columns,
            fallback_reason="; ".join(fallback_reasons),
            model=None,
            train_metrics=compute_direction_metrics(y_train, baseline_train, baseline_train) if len(train_frame) else None,
            val_metrics=compute_direction_metrics(y_val, baseline_val, baseline_val) if len(val_frame) else None,
            sample_weight_summary=sample_weight_summary,
        )

    model = make_direction_regressor(config, random_state=config.seed + regime_id * 10 + (0 if side == "LONG" else 1))
    model.fit(X_train, y_train, sample_weight=sample_weights)

    raw_train_pred = np.asarray(model.predict(X_train), dtype=np.float64)
    raw_val_pred = np.asarray(model.predict(X_val), dtype=np.float64) if len(val_frame) else np.empty((0, 3), dtype=np.float64)

    return DirectionTrainingResult(
        side=side,
        status="trained",
        train_count=int(len(train_frame)),
        val_count=int(len(val_frame)),
        target_columns=target_columns,
        fallback_reason=None,
        model=model,
        train_metrics=compute_direction_metrics(y_train, raw_train_pred, baseline_train) if len(train_frame) else None,
        val_metrics=compute_direction_metrics(y_val, raw_val_pred, baseline_val) if len(val_frame) else None,
        sample_weight_summary=sample_weight_summary,
    )


def build_regime_status(long_result: DirectionTrainingResult, short_result: DirectionTrainingResult) -> str:
    trained_count = int(long_result.status == "trained") + int(short_result.status == "trained")
    if trained_count == 2:
        return "trained_both"
    if trained_count == 1:
        return "trained_partial"
    return "fallback_only"


def train_regime_bundle(
    regime_id: int,
    X_all: np.ndarray,
    stage2_frame: pd.DataFrame,
    config: Step13Config,
    output_dir: Path,
) -> RegimeTrainingResult:
    regime_dir = output_dir / f"regime_{regime_id}"
    regime_dir.mkdir(parents=True, exist_ok=True)

    long_result = train_direction_head("LONG", regime_id, X_all, stage2_frame, config)
    short_result = train_direction_head("SHORT", regime_id, X_all, stage2_frame, config)
    regime_status = build_regime_status(long_result, short_result)

    bundle = Stage2Bundle(
        prm_version=f"step13_{config.model_name}",
        model_name=config.model_name,
        regime_id=regime_id,
        window_size=WINDOW_SIZE,
        feature_dim=FEATURE_DIM,
        feature_columns=list(FEATURE_COLUMNS),
        scaled_feature_columns=list(SCALED_FEATURE_COLUMNS),
        output_order=list(STAGE2_OUTPUT_ORDER),
        long_head=DirectionHeadBundle(
            side="LONG",
            status=long_result.status,
            target_columns=long_result.target_columns,
            default_vector=[float(value) for value in DEFAULT_PARAM_VECTOR.tolist()],
            model=long_result.model,
            train_count=long_result.train_count,
            val_count=long_result.val_count,
            fallback_reason=long_result.fallback_reason,
            train_metrics=long_result.train_metrics,
            val_metrics=long_result.val_metrics,
        ),
        short_head=DirectionHeadBundle(
            side="SHORT",
            status=short_result.status,
            target_columns=short_result.target_columns,
            default_vector=[float(value) for value in DEFAULT_PARAM_VECTOR.tolist()],
            model=short_result.model,
            train_count=short_result.train_count,
            val_count=short_result.val_count,
            fallback_reason=short_result.fallback_reason,
            train_metrics=short_result.train_metrics,
            val_metrics=short_result.val_metrics,
        ),
    )

    bundle_path = regime_dir / f"prm_reg{regime_id}.joblib"
    report_path = regime_dir / "train_report.json"
    joblib.dump(bundle, bundle_path)

    report_payload = {
        "regime_id": regime_id,
        "status": regime_status,
        "bundle_path": str(bundle_path),
        "output_order": list(STAGE2_OUTPUT_ORDER),
        "long_head": {
            "status": long_result.status,
            "train_count": long_result.train_count,
            "val_count": long_result.val_count,
            "target_columns": list(long_result.target_columns),
            "fallback_reason": long_result.fallback_reason,
            "sample_weight_summary": long_result.sample_weight_summary,
            "train_metrics": long_result.train_metrics,
            "val_metrics": long_result.val_metrics,
        },
        "short_head": {
            "status": short_result.status,
            "train_count": short_result.train_count,
            "val_count": short_result.val_count,
            "target_columns": list(short_result.target_columns),
            "fallback_reason": short_result.fallback_reason,
            "sample_weight_summary": short_result.sample_weight_summary,
            "train_metrics": short_result.train_metrics,
            "val_metrics": short_result.val_metrics,
        },
    }
    write_json(report_path, report_payload)

    return RegimeTrainingResult(
        regime_id=regime_id,
        status=regime_status,
        bundle_path=str(bundle_path),
        report_path=str(report_path),
        long_result=long_result,
        short_result=short_result,
    )


def sample_smoke_rows(regime_frame: pd.DataFrame, max_per_side: int = 4) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for side in ("LONG", "SHORT"):
        side_rows = regime_frame.loc[regime_frame["target_side"] == side].head(max_per_side)
        if not side_rows.empty:
            parts.append(side_rows)
    if not parts:
        return regime_frame.head(0).copy()
    return pd.concat(parts, axis=0, ignore_index=True)


def run_bundle_smoke(bundle_path: str, regime_frame: pd.DataFrame, X_all: np.ndarray) -> dict[str, Any]:
    bundle = joblib.load(bundle_path)
    smoke_rows = sample_smoke_rows(regime_frame)
    if smoke_rows.empty:
        return {"tested": False, "row_count": 0}

    X_smoke = X_all[smoke_rows["label_row_idx"].to_numpy(dtype=np.int64)]
    raw = bundle.predict_raw(X_smoke)
    effective = bundle.predict_effective(X_smoke)

    shape_ok = raw.shape == (len(smoke_rows), 6) and effective.shape == (len(smoke_rows), 6)
    raw_all_finite = bool(np.isfinite(raw).all())
    effective_all_finite = bool(np.isfinite(effective).all())
    contract_valid = bool(
        np.all((effective[:, 0] >= LOWER_BOUNDS[0]) & (effective[:, 0] <= UPPER_BOUNDS[0]))
        and np.all((effective[:, 1] >= LOWER_BOUNDS[1]) & (effective[:, 1] <= UPPER_BOUNDS[1]))
        and np.all((effective[:, 2] >= LOWER_BOUNDS[2]) & (effective[:, 2] <= UPPER_BOUNDS[2]))
        and np.all((effective[:, 3] >= LOWER_BOUNDS[0]) & (effective[:, 3] <= UPPER_BOUNDS[0]))
        and np.all((effective[:, 4] >= LOWER_BOUNDS[1]) & (effective[:, 4] <= UPPER_BOUNDS[1]))
        and np.all((effective[:, 5] >= LOWER_BOUNDS[2]) & (effective[:, 5] <= UPPER_BOUNDS[2]))
    )
    holds_integral = bool(
        np.allclose(effective[:, 2], np.rint(effective[:, 2])) and np.allclose(effective[:, 5], np.rint(effective[:, 5]))
    )

    return {
        "tested": True,
        "row_count": int(len(smoke_rows)),
        "shape_ok": bool(shape_ok),
        "raw_all_finite": raw_all_finite,
        "effective_all_finite": effective_all_finite,
        "contract_valid": contract_valid,
        "holds_integral": holds_integral,
        "target_side_counts": {
            str(side): int(count)
            for side, count in smoke_rows["target_side"].value_counts(sort=False).sort_index().items()
        },
    }


def build_acceptance(
    step12_context: Step12Context,
    split_audit: SplitReuseAudit,
    stage2_audit: Stage2Audit,
    stage2_frame: pd.DataFrame,
    results: list[RegimeTrainingResult],
    X_all: np.ndarray,
) -> dict[str, Any]:
    smoke_by_regime: dict[str, Any] = {}
    smoke_shape_ok = True
    smoke_contract_ok = True
    for result in results:
        regime_frame = stage2_frame.loc[stage2_frame["regime_id"] == result.regime_id]
        smoke = run_bundle_smoke(result.bundle_path, regime_frame, X_all)
        smoke_by_regime[str(result.regime_id)] = smoke
        if smoke.get("tested"):
            smoke_shape_ok = smoke_shape_ok and smoke["shape_ok"] and smoke["raw_all_finite"] and smoke["effective_all_finite"]
            smoke_contract_ok = smoke_contract_ok and smoke["contract_valid"] and smoke["holds_integral"]

    quality_rows: list[dict[str, Any]] = []
    fallback_head_count = 0
    for result in results:
        for side, head in (("LONG", result.long_result), ("SHORT", result.short_result)):
            if head.status != "trained":
                fallback_head_count += 1
            if head.val_metrics is None:
                continue
            quality_rows.append(
                {
                    "regime_id": result.regime_id,
                    "side": side,
                    "status": head.status,
                    "val_count": head.val_count,
                    "beats_default_baseline": head.val_metrics["beats_default_baseline"],
                    "normalized_effective_mae_mean": head.val_metrics["normalized_effective_mae_mean"],
                    "baseline_normalized_effective_mae_mean": head.val_metrics["baseline_normalized_effective_mae_mean"],
                    "hold_boundary_rate": head.val_metrics["hold_boundary_rate"],
                }
            )

    return {
        "A1_split_match_step12": bool(split_audit.passed),
        "A2_step12_no_time_leakage": bool(
            step12_context.training_metadata.get("acceptance", {}).get("A1_no_time_leakage", False)
            and step12_context.split_plan.get("no_time_leakage", False)
            and split_audit.no_time_leakage
        ),
        "A3_cand1_only": bool(stage2_audit.cand1_only),
        "A4_masking_integrity": bool(stage2_audit.masking_integrity and stage2_audit.non_pass_rows_matching_target_side),
        "A5_bundle_predict_shape_and_finite": bool(smoke_shape_ok),
        "A6_postprocess_contract_valid": bool(smoke_contract_ok),
        "A7_export_deferred_to_step15": True,
        "fallback_head_count": fallback_head_count,
        "quality_heads_evaluated": len(quality_rows),
        "quality_heads_beating_default_baseline": int(sum(1 for row in quality_rows if row["beats_default_baseline"])),
        "quality_max_hold_boundary_rate": max((float(row["hold_boundary_rate"]) for row in quality_rows), default=None),
        "quality_rows": quality_rows,
        "split_reuse_audit": split_audit.as_json(),
        "stage2_audit": stage2_audit.as_json(),
        "bundle_smoke": smoke_by_regime,
    }


def build_training_metadata(
    bundle: Step11Bundle,
    step12_context: Step12Context,
    config: Step13Config,
    split_audit: SplitReuseAudit,
    stage2_audit: Stage2Audit,
    results: list[RegimeTrainingResult],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    per_regime: dict[str, Any] = {}
    for result in results:
        per_regime[str(result.regime_id)] = {
            "status": result.status,
            "bundle_path": result.bundle_path,
            "report_path": result.report_path,
            "long_head": {
                "status": result.long_result.status,
                "train_count": result.long_result.train_count,
                "val_count": result.long_result.val_count,
                "fallback_reason": result.long_result.fallback_reason,
                "sample_weight_summary": result.long_result.sample_weight_summary,
                "train_metrics": result.long_result.train_metrics,
                "val_metrics": result.long_result.val_metrics,
            },
            "short_head": {
                "status": result.short_result.status,
                "train_count": result.short_result.train_count,
                "val_count": result.short_result.val_count,
                "fallback_reason": result.short_result.fallback_reason,
                "sample_weight_summary": result.short_result.sample_weight_summary,
                "train_metrics": result.short_result.train_metrics,
                "val_metrics": result.short_result.val_metrics,
            },
        }

    return json_ready(
        {
            "implementation_status": "step13_baseline_implemented",
            "prm_version": f"step13_{config.model_name}",
            "architecture_baseline": {
                "family": "sklearn_gradient_boosting_regressor",
                "wrapper": "multioutput_per_direction",
                "loss": "huber",
                "direction_masking": "two_direction_heads",
            },
            "training_config": {
                "min_train_samples_per_head": config.min_train_samples_per_head,
                "min_val_samples_per_head": config.min_val_samples_per_head,
                "pass_row_weight": config.pass_row_weight,
                "gbr_n_estimators": config.gbr_n_estimators,
                "gbr_learning_rate": config.gbr_learning_rate,
                "gbr_max_depth": config.gbr_max_depth,
                "gbr_min_samples_leaf": config.gbr_min_samples_leaf,
                "gbr_subsample": config.gbr_subsample,
                "gbr_alpha": config.gbr_alpha,
                "seed": config.seed,
                "model_name": config.model_name,
            },
            "source_step11_metadata": bundle.metadata,
            "source_step12_training_metadata": step12_context.training_metadata,
            "source_split_plan": step12_context.split_plan,
            "source_scaler_stats": step12_context.scaler_stats,
            "data_start": bundle.metadata.get("data_start"),
            "data_end": bundle.metadata.get("data_end"),
            "total_labeled_samples": int(len(bundle.labels)),
            "total_stage2_samples": int(stage2_audit.retained_rows),
            "stage2_train_samples": int(stage2_audit.train_rows),
            "stage2_val_samples": int(stage2_audit.val_rows),
            "split_reuse_audit": split_audit.as_json(),
            "stage2_audit": stage2_audit.as_json(),
            "per_regime": per_regime,
            "acceptance": acceptance,
        }
    )


def main() -> int:
    config = parse_args()
    config.output_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_step11_bundle(config.step11_dir)
    step12_context = load_step12_context(config.step12_dir)
    train_mask, val_mask, _dropped_mask, split_audit = rebuild_masks_from_split_plan(bundle.labels, step12_context.split_plan)
    X_all = build_scaled_windows(bundle.features, bundle.labels, step12_context.scaler)
    stage2_frame, stage2_audit = build_stage2_frame(bundle.labels, train_mask, val_mask)

    results: list[RegimeTrainingResult] = []
    for regime_id in range(6):
        result = train_regime_bundle(regime_id, X_all, stage2_frame, config, config.output_dir)
        results.append(result)
        print(
            f"[STEP13] regime={regime_id} status={result.status} "
            f"long=({result.long_result.status},{result.long_result.train_count}/{result.long_result.val_count}) "
            f"short=({result.short_result.status},{result.short_result.train_count}/{result.short_result.val_count})"
        )

    acceptance = build_acceptance(step12_context, split_audit, stage2_audit, stage2_frame, results, X_all)
    training_metadata = build_training_metadata(bundle, step12_context, config, split_audit, stage2_audit, results, acceptance)

    write_json(config.output_dir / "training_metadata.json", training_metadata)
    write_json(config.output_dir / "split_plan.json", step12_context.split_plan)
    write_json(config.output_dir / "scaler_stats.json", step12_context.scaler_stats)
    pd.DataFrame([result.summary_row() for result in results]).to_csv(config.output_dir / "regime_summary.csv", index=False)

    print(f"[STEP13] stage2_train_samples={stage2_audit.train_rows}")
    print(f"[STEP13] stage2_val_samples={stage2_audit.val_rows}")
    print(f"[STEP13] acceptance={json.dumps(acceptance, ensure_ascii=False)}")
    print(f"[STEP13] training_metadata={config.output_dir / 'training_metadata.json'}")

    if config.fail_on_acceptance:
        hard_flags = [
            acceptance["A1_split_match_step12"],
            acceptance["A2_step12_no_time_leakage"],
            acceptance["A3_cand1_only"],
            acceptance["A4_masking_integrity"],
            acceptance["A5_bundle_predict_shape_and_finite"],
            acceptance["A6_postprocess_contract_valid"],
        ]
        if not all(hard_flags):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
