from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, log_loss
from sklearn.neural_network import MLPClassifier


WINDOW_SIZE = 64
FEATURE_DIM = 22
SCALED_FEATURE_DIM = 12
DEFAULT_ACCEPTANCE_CAND0_PASS_RECALL = 0.50
EPSILON = 1e-12

CLASS_IDS = np.array([0, 1, 2], dtype=np.int64)
CLASS_NAMES = {0: "LONG", 1: "SHORT", 2: "PASS"}
FEATURE_COLUMNS = [f"feature_{i}" for i in range(FEATURE_DIM)]
SCALED_FEATURE_COLUMNS = FEATURE_COLUMNS[:SCALED_FEATURE_DIM]

REQUIRED_FEATURE_COLUMNS = ["bar_time", "symbol", *FEATURE_COLUMNS]
REQUIRED_LABEL_COLUMNS = [
    "sample_index",
    "bar_time",
    "window_start_idx",
    "window_end_idx",
    "regime_id",
    "cand_long",
    "cand_short",
    "label_dir",
    "label_dir_int",
    "H",
]

STEP11_DEFAULT_VALIDATION_TOLERANCE = 1e-6
STEP11_REQUIRED_ZERO_MISMATCH = (
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
STEP11_MAX_ABS_DIFF_TOLERANCE = {
    "ret_1": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "ret_3": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "ret_12": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "range_atr": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "body_atr": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "close_pos": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "rsi_norm": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "adx_norm": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "spread_atr": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "time_sin": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "time_cos": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "dist_atr_abs_feature6": STEP11_DEFAULT_VALIDATION_TOLERANCE,
    "dist_atr_max_t": STEP11_DEFAULT_VALIDATION_TOLERANCE,
}


@dataclass(frozen=True)
class Step12Config:
    input_dir: Path
    output_dir: Path
    train_ratio: float
    embargo_bars: int | None
    min_train_samples_per_regime: int
    min_val_samples_per_regime: int
    cand0_max_fraction: float
    cand0_sample_weight: float
    hidden_layers: tuple[int, ...]
    learning_rate: float
    weight_decay: float
    batch_size: int
    epochs: int
    patience: int
    min_delta: float
    seed: int
    model_name: str
    fail_on_acceptance: bool


@dataclass(frozen=True)
class Step11Bundle:
    features: pd.DataFrame
    labels: pd.DataFrame
    metadata: dict[str, Any]
    H: int


@dataclass(frozen=True)
class SplitPlan:
    target_split_index: int
    selected_split_index: int
    boundary_window_end_idx: int
    target_train_ratio: float
    effective_train_ratio: float
    embargo_bars: int
    train_count: int
    val_count: int
    dropped_count: int
    requested_min_val_samples_per_regime: int
    effective_min_val_samples_per_regime: int
    relaxed_min_val_requirement: bool
    train_end_time: str
    val_start_time: str
    no_time_leakage: bool
    fallback_used: bool
    train_counts_by_regime: dict[str, int]
    val_counts_by_regime: dict[str, int]
    dropped_counts_by_regime: dict[str, int]

    def summary(self) -> dict[str, Any]:
        return {
            "target_split_index": self.target_split_index,
            "selected_split_index": self.selected_split_index,
            "boundary_window_end_idx": self.boundary_window_end_idx,
            "target_train_ratio": self.target_train_ratio,
            "effective_train_ratio": self.effective_train_ratio,
            "embargo_bars": self.embargo_bars,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "dropped_count": self.dropped_count,
            "requested_min_val_samples_per_regime": self.requested_min_val_samples_per_regime,
            "effective_min_val_samples_per_regime": self.effective_min_val_samples_per_regime,
            "relaxed_min_val_requirement": self.relaxed_min_val_requirement,
            "train_end_time": self.train_end_time,
            "val_start_time": self.val_start_time,
            "no_time_leakage": self.no_time_leakage,
            "fallback_used": self.fallback_used,
            "train_counts_by_regime": self.train_counts_by_regime,
            "val_counts_by_regime": self.val_counts_by_regime,
            "dropped_counts_by_regime": self.dropped_counts_by_regime,
        }


@dataclass(frozen=True)
class ScalerStats:
    mean: list[float]
    std: list[float]
    bar_count: int
    replaced_std_indices: list[int]

    def as_json(self) -> dict[str, list[float]]:
        return {"mean": self.mean, "std": self.std}


@dataclass(frozen=True)
class RegimeTrainingResult:
    regime_id: int
    status: str
    train_count_raw: int
    train_count_retained: int
    val_count: int
    cand0_retained_count: int
    cand1_retained_count: int
    best_epoch: int | None
    epochs_trained: int
    early_stopped: bool
    model_path: str | None
    report_path: str | None
    train_metrics: dict[str, Any] | None
    val_metrics: dict[str, Any] | None
    train_label_distribution: dict[str, int]
    val_label_distribution: dict[str, int]

    def summary_row(self) -> dict[str, Any]:
        return {
            "regime_id": self.regime_id,
            "status": self.status,
            "train_count_raw": self.train_count_raw,
            "train_count_retained": self.train_count_retained,
            "val_count": self.val_count,
            "cand0_retained_count": self.cand0_retained_count,
            "cand1_retained_count": self.cand1_retained_count,
            "best_epoch": self.best_epoch,
            "epochs_trained": self.epochs_trained,
            "early_stopped": self.early_stopped,
            "model_path": self.model_path,
            "report_path": self.report_path,
        }


def serialize_timestamp(value: pd.Timestamp | Any) -> str:
    ts = pd.Timestamp(value)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def distribution_from_labels(labels: np.ndarray) -> dict[str, int]:
    counts = np.bincount(labels.astype(np.int64), minlength=len(CLASS_IDS))
    return {CLASS_NAMES[idx]: int(counts[idx]) for idx in range(len(CLASS_IDS))}


def parse_hidden_layers(value: str) -> tuple[int, ...]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("hidden_layers must contain at least one integer")

    parsed: list[int] = []
    for part in parts:
        try:
            width = int(part)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid hidden layer width: {part}") from exc
        if width <= 0:
            raise argparse.ArgumentTypeError("hidden layer widths must be positive")
        parsed.append(width)
    return tuple(parsed)


def parse_args() -> Step12Config:
    parser = argparse.ArgumentParser(description="STEP12 baseline Stage1 training for Triple Sigma.")
    parser.add_argument("--input-dir", required=True, help="STEP11 output directory")
    parser.add_argument("--output-dir", required=True, help="STEP12 output directory")
    parser.add_argument("--train-ratio", type=float, default=0.80)
    parser.add_argument("--embargo-bars", type=int, default=None)
    parser.add_argument("--min-train-samples-per-regime", type=int, default=24)
    parser.add_argument("--min-val-samples-per-regime", type=int, default=4)
    parser.add_argument("--cand0-max-fraction", type=float, default=0.95)
    parser.add_argument("--cand0-sample-weight", type=float, default=1.00)
    parser.add_argument("--hidden-layers", type=parse_hidden_layers, default=(64, 32))
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--min-delta", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-name", default="mlp_v1")
    parser.add_argument("--fail-on-acceptance", action="store_true")
    args = parser.parse_args()

    if not 0.0 < args.train_ratio < 1.0:
        raise ValueError("train_ratio must be between 0 and 1")
    if not 0.0 < args.cand0_max_fraction < 1.0:
        raise ValueError("cand0_max_fraction must be between 0 and 1")
    if args.cand0_sample_weight <= 0.0:
        raise ValueError("cand0_sample_weight must be > 0")
    if args.batch_size <= 0 or args.epochs <= 0 or args.patience <= 0:
        raise ValueError("batch_size, epochs, patience must be positive")

    return Step12Config(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        train_ratio=args.train_ratio,
        embargo_bars=args.embargo_bars,
        min_train_samples_per_regime=args.min_train_samples_per_regime,
        min_val_samples_per_regime=args.min_val_samples_per_regime,
        cand0_max_fraction=args.cand0_max_fraction,
        cand0_sample_weight=args.cand0_sample_weight,
        hidden_layers=args.hidden_layers,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        batch_size=args.batch_size,
        epochs=args.epochs,
        patience=args.patience,
        min_delta=args.min_delta,
        seed=args.seed,
        model_name=args.model_name,
        fail_on_acceptance=args.fail_on_acceptance,
    )


def load_step11_bundle(input_dir: Path) -> Step11Bundle:
    features_path = input_dir / "features.parquet"
    labels_path = input_dir / "labels.parquet"
    metadata_path = input_dir / "metadata.json"
    for path in (features_path, labels_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"required STEP11 artifact not found: {path}")

    features = pd.read_parquet(features_path).reset_index(drop=True)
    labels = pd.read_parquet(labels_path).reset_index(drop=True)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    validate_step11_bundle(features, labels, metadata)
    H = int(labels["H"].iloc[0])
    return Step11Bundle(features=features, labels=labels, metadata=metadata, H=H)


def validate_step11_bundle(features: pd.DataFrame, labels: pd.DataFrame, metadata: dict[str, Any]) -> None:
    assert_step11_validation_clean(metadata)

    missing_feature_columns = [column for column in REQUIRED_FEATURE_COLUMNS if column not in features.columns]
    if missing_feature_columns:
        raise ValueError(f"features.parquet missing columns: {missing_feature_columns}")

    missing_label_columns = [column for column in REQUIRED_LABEL_COLUMNS if column not in labels.columns]
    if missing_label_columns:
        raise ValueError(f"labels.parquet missing columns: {missing_label_columns}")

    if features.empty or labels.empty:
        raise ValueError("STEP11 bundle is empty")

    if not features["bar_time"].is_monotonic_increasing:
        raise ValueError("features.bar_time must be monotonic increasing")
    if not labels["bar_time"].is_monotonic_increasing:
        raise ValueError("labels.bar_time must be monotonic increasing")
    if not labels["sample_index"].is_unique or not labels["sample_index"].is_monotonic_increasing:
        raise ValueError("labels.sample_index must be unique and monotonic increasing")

    window_lengths = labels["window_end_idx"] - labels["window_start_idx"] + 1
    if not (window_lengths == WINDOW_SIZE).all():
        raise ValueError("labels contain non-64 windows")

    if (labels["window_start_idx"] < 0).any() or (labels["window_end_idx"] >= len(features)).any():
        raise ValueError("labels reference out-of-range feature rows")

    feature_times = features["bar_time"].to_numpy()
    expected_label_times = feature_times[labels["window_end_idx"].to_numpy(dtype=np.int64)]
    if not np.array_equal(expected_label_times, labels["bar_time"].to_numpy()):
        raise ValueError("labels.bar_time does not match features[window_end_idx].bar_time")

    invalid_cand = (labels["cand_long"] == 1) & (labels["cand_short"] == 1)
    if invalid_cand.any():
        raise ValueError("labels contain invalid cand_long=1, cand_short=1 rows")

    cand0_mask = (labels["cand_long"] == 0) & (labels["cand_short"] == 0)
    if not (labels.loc[cand0_mask, "label_dir_int"] == 2).all():
        raise ValueError("cand=(0,0) rows must be forced PASS in STEP11 labels")

    unique_h = sorted(int(value) for value in labels["H"].unique())
    if len(unique_h) != 1:
        raise ValueError(f"labels.H must contain a single value, got {unique_h}")
    if "H" in metadata and int(metadata["H"]) != unique_h[0]:
        raise ValueError(f"metadata.H={metadata['H']} does not match labels.H={unique_h[0]}")


def assert_step11_validation_clean(metadata: dict[str, Any]) -> None:
    validation = metadata.get("validation")
    if not isinstance(validation, dict):
        raise ValueError("STEP11 metadata missing validation block")

    rows_validated = int(validation.get("rows_validated", 0))
    if rows_validated <= 0:
        raise ValueError("STEP11 metadata.validation.rows_validated must be > 0")

    mismatch_count = validation.get("mismatch_count")
    if not isinstance(mismatch_count, dict):
        raise ValueError("STEP11 metadata.validation.mismatch_count missing")
    for key in STEP11_REQUIRED_ZERO_MISMATCH:
        value = int(mismatch_count.get(key, -1))
        if value != 0:
            raise ValueError(f"STEP11 validation dirty: mismatch_count[{key}]={value}")

    max_abs_diff = validation.get("max_abs_diff")
    if not isinstance(max_abs_diff, dict):
        raise ValueError("STEP11 metadata.validation.max_abs_diff missing")
    for key, tolerance in STEP11_MAX_ABS_DIFF_TOLERANCE.items():
        value = float(max_abs_diff.get(key, math.inf))
        if value > tolerance:
            raise ValueError(f"STEP11 validation dirty: max_abs_diff[{key}]={value:.12f} > {tolerance:.12f}")


def count_by_regime(regimes: np.ndarray, mask: np.ndarray, observed_regimes: list[int]) -> dict[str, int]:
    return {str(rid): int(np.sum(mask & (regimes == rid))) for rid in observed_regimes}


def choose_global_split(
    labels: pd.DataFrame,
    target_train_ratio: float,
    embargo_bars: int,
    min_train_samples_per_regime: int,
    min_val_samples_per_regime: int,
) -> tuple[SplitPlan, np.ndarray, np.ndarray, np.ndarray]:
    window_end = labels["window_end_idx"].to_numpy(dtype=np.int64)
    regimes = labels["regime_id"].to_numpy(dtype=np.int64)
    label_times = labels["bar_time"].to_numpy()
    observed_regimes = sorted(int(value) for value in np.unique(regimes))
    all_rows_mask = np.ones(len(labels), dtype=bool)
    total_counts = count_by_regime(regimes, all_rows_mask, observed_regimes)
    target_split_index = max(1, min(len(labels) - 1, int(round(len(labels) * target_train_ratio))))

    insufficient_train_totals = {
        str(rid): total_counts[str(rid)]
        for rid in observed_regimes
        if total_counts[str(rid)] < min_train_samples_per_regime
    }
    if insufficient_train_totals:
        raise ValueError(
            "unable to find a global split: "
            f"min_train_samples_per_regime={min_train_samples_per_regime} exceeds total counts {insufficient_train_totals}"
        )

    def scan_candidates(effective_min_val: int) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for selected_split_index in range(1, len(labels)):
            boundary_window_end_idx = int(window_end[selected_split_index])
            train_mask = window_end + embargo_bars < boundary_window_end_idx
            val_mask = window_end >= boundary_window_end_idx
            if not train_mask.any() or not val_mask.any():
                continue

            train_counts = count_by_regime(regimes, train_mask, observed_regimes)
            val_counts = count_by_regime(regimes, val_mask, observed_regimes)
            if any(train_counts[str(rid)] < min_train_samples_per_regime for rid in observed_regimes):
                continue
            if any(val_counts[str(rid)] < effective_min_val for rid in observed_regimes):
                continue

            dropped_mask = ~(train_mask | val_mask)
            train_count = int(train_mask.sum())
            val_count = int(val_mask.sum())
            dropped_count = int(dropped_mask.sum())
            effective_ratio = train_count / float(train_count + val_count)

            candidates.append(
                {
                    "selected_split_index": selected_split_index,
                    "boundary_window_end_idx": boundary_window_end_idx,
                    "train_mask": train_mask,
                    "val_mask": val_mask,
                    "dropped_mask": dropped_mask,
                    "train_count": train_count,
                    "val_count": val_count,
                    "dropped_count": dropped_count,
                    "effective_ratio": effective_ratio,
                    "train_counts": train_counts,
                    "val_counts": val_counts,
                    "dropped_counts": count_by_regime(regimes, dropped_mask, observed_regimes),
                }
            )
        return candidates

    requested_min_val = min_val_samples_per_regime
    selected_candidate: dict[str, Any] | None = None
    effective_min_val = requested_min_val
    relaxed = False
    fallback_used = False

    for candidate_min_val in range(requested_min_val, -1, -1):
        candidates = scan_candidates(candidate_min_val)
        if not candidates:
            continue
        selected_candidate = min(
            candidates,
            key=lambda candidate: (
                abs(candidate["effective_ratio"] - target_train_ratio),
                abs(candidate["selected_split_index"] - target_split_index),
                candidate["dropped_count"],
            ),
        )
        effective_min_val = candidate_min_val
        relaxed = candidate_min_val != requested_min_val
        break

    if selected_candidate is None:
        fallback_candidates = scan_candidates(0)
        if not fallback_candidates:
            raise ValueError(
                "unable to find a global split with non-empty train/val sets; "
                f"total_counts_by_regime={total_counts}, "
                f"min_train_samples_per_regime={min_train_samples_per_regime}, "
                f"requested_min_val_samples_per_regime={requested_min_val}, "
                f"embargo_bars={embargo_bars}"
            )
        selected_candidate = min(
            fallback_candidates,
            key=lambda candidate: (
                abs(candidate["effective_ratio"] - target_train_ratio),
                abs(candidate["selected_split_index"] - target_split_index),
                candidate["dropped_count"],
            ),
        )
        effective_min_val = 0
        relaxed = True
        fallback_used = True

    train_mask = selected_candidate["train_mask"]
    val_mask = selected_candidate["val_mask"]
    dropped_mask = selected_candidate["dropped_mask"]
    max_train_window_end = int(window_end[train_mask].max())
    min_val_window_end = int(window_end[val_mask].min())
    no_time_leakage = max_train_window_end + embargo_bars < min_val_window_end

    plan = SplitPlan(
        target_split_index=target_split_index,
        selected_split_index=int(selected_candidate["selected_split_index"]),
        boundary_window_end_idx=int(selected_candidate["boundary_window_end_idx"]),
        target_train_ratio=float(target_train_ratio),
        effective_train_ratio=float(selected_candidate["effective_ratio"]),
        embargo_bars=int(embargo_bars),
        train_count=int(selected_candidate["train_count"]),
        val_count=int(selected_candidate["val_count"]),
        dropped_count=int(selected_candidate["dropped_count"]),
        requested_min_val_samples_per_regime=int(requested_min_val),
        effective_min_val_samples_per_regime=int(effective_min_val),
        relaxed_min_val_requirement=bool(relaxed),
        train_end_time=serialize_timestamp(label_times[train_mask][-1]),
        val_start_time=serialize_timestamp(label_times[val_mask][0]),
        no_time_leakage=bool(no_time_leakage),
        fallback_used=bool(fallback_used),
        train_counts_by_regime=selected_candidate["train_counts"],
        val_counts_by_regime=selected_candidate["val_counts"],
        dropped_counts_by_regime=selected_candidate["dropped_counts"],
    )
    return plan, train_mask, val_mask, dropped_mask


def build_training_bar_mask(labels: pd.DataFrame, train_mask: np.ndarray, n_bars: int) -> np.ndarray:
    diff = np.zeros(n_bars + 1, dtype=np.int64)
    windows = labels.loc[train_mask, ["window_start_idx", "window_end_idx"]].to_numpy(dtype=np.int64)
    for start_idx, end_idx in windows:
        diff[start_idx] += 1
        diff[end_idx + 1] -= 1
    return np.cumsum(diff[:-1]) > 0


def compute_scaler(features: pd.DataFrame, labels: pd.DataFrame, train_mask: np.ndarray) -> tuple[ScalerStats, np.ndarray]:
    train_bar_mask = build_training_bar_mask(labels, train_mask, len(features))
    if not train_bar_mask.any():
        raise ValueError("training split does not cover any feature bars")

    values = features.loc[train_bar_mask, SCALED_FEATURE_COLUMNS].to_numpy(dtype=np.float64)
    mean = values.mean(axis=0)
    std = values.std(axis=0, ddof=0)
    replaced_std_indices: list[int] = []
    for idx in range(len(std)):
        if not np.isfinite(std[idx]) or std[idx] <= EPSILON:
            std[idx] = 1.0
            replaced_std_indices.append(idx)

    stats = ScalerStats(
        mean=[float(value) for value in mean.tolist()],
        std=[float(value) for value in std.tolist()],
        bar_count=int(train_bar_mask.sum()),
        replaced_std_indices=replaced_std_indices,
    )
    return stats, train_bar_mask


def build_scaled_windows(features: pd.DataFrame, labels: pd.DataFrame, scaler: ScalerStats) -> np.ndarray:
    feature_values = features.loc[:, FEATURE_COLUMNS].to_numpy(dtype=np.float64)
    windows = np.empty((len(labels), WINDOW_SIZE, FEATURE_DIM), dtype=np.float64)
    indices = labels.loc[:, ["window_start_idx", "window_end_idx"]].to_numpy(dtype=np.int64)
    for row_idx, (start_idx, end_idx) in enumerate(indices):
        window = feature_values[start_idx : end_idx + 1]
        if window.shape != (WINDOW_SIZE, FEATURE_DIM):
            raise ValueError(
                f"window shape mismatch at row {row_idx}: expected {(WINDOW_SIZE, FEATURE_DIM)}, got {window.shape}"
            )
        windows[row_idx] = window

    mean = np.asarray(scaler.mean, dtype=np.float64).reshape(1, 1, SCALED_FEATURE_DIM)
    std = np.asarray(scaler.std, dtype=np.float64).reshape(1, 1, SCALED_FEATURE_DIM)
    windows[:, :, :SCALED_FEATURE_DIM] = (windows[:, :, :SCALED_FEATURE_DIM] - mean) / std
    return windows.reshape(len(labels), WINDOW_SIZE * FEATURE_DIM).astype(np.float32, copy=False)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [json_ready(inner) for inner in value]
    if isinstance(value, tuple):
        return [json_ready(inner) for inner in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return serialize_timestamp(value)
    return value


def cand0_mask_from_frame(frame: pd.DataFrame) -> np.ndarray:
    return ((frame["cand_long"] == 0) & (frame["cand_short"] == 0)).to_numpy(dtype=bool)


def compute_metrics(model: MLPClassifier, X: np.ndarray, frame: pd.DataFrame) -> dict[str, Any] | None:
    if len(frame) == 0:
        return None

    y_true = frame["label_dir_int"].to_numpy(dtype=np.int64)
    cand0_mask = cand0_mask_from_frame(frame)
    probabilities = model.predict_proba(X)
    probabilities = np.clip(probabilities, 1e-9, 1.0)
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    y_pred = probabilities.argmax(axis=1)

    pass_true = y_true == 2
    pass_pred = y_pred == 2
    cand1_mask = ~cand0_mask

    predicted_pass_count = int(pass_pred.sum())
    actual_pass_count = int(pass_true.sum())
    true_positive_pass = int(np.sum(pass_true & pass_pred))

    metrics = {
        "count": int(len(frame)),
        "label_distribution": distribution_from_labels(y_true),
        "pred_distribution": distribution_from_labels(y_pred.astype(np.int64)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASS_IDS, average="macro", zero_division=0)),
        "pass_precision": float(true_positive_pass / predicted_pass_count) if predicted_pass_count else 0.0,
        "pass_recall": float(true_positive_pass / actual_pass_count) if actual_pass_count else 0.0,
        "cand0_pass_recall": float(np.mean(pass_pred[cand0_mask])) if cand0_mask.any() else None,
        "cand1_accuracy": float(np.mean(y_pred[cand1_mask] == y_true[cand1_mask])) if cand1_mask.any() else None,
        "cand0_mean_p_pass": float(np.mean(probabilities[cand0_mask, 2])) if cand0_mask.any() else None,
        "cand0_std_p_pass": float(np.std(probabilities[cand0_mask, 2], ddof=0)) if cand0_mask.any() else None,
        "log_loss": float(log_loss(y_true, probabilities, labels=CLASS_IDS)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASS_IDS).tolist(),
    }
    return json_ready(metrics)


def select_retained_train_rows(
    frame: pd.DataFrame,
    config: Step12Config,
    rng: np.random.Generator,
) -> np.ndarray:
    row_indices = np.arange(len(frame), dtype=np.int64)
    cand0_mask = cand0_mask_from_frame(frame)
    cand0_indices = row_indices[cand0_mask]
    cand1_indices = row_indices[~cand0_mask]

    if len(cand0_indices) == 0 or len(cand1_indices) == 0:
        return row_indices

    target_max_cand0 = int(
        math.floor((config.cand0_max_fraction * len(cand1_indices)) / (1.0 - config.cand0_max_fraction))
    )
    target_max_cand0 = max(target_max_cand0, max(config.min_train_samples_per_regime - len(cand1_indices), 0))
    target_max_cand0 = max(target_max_cand0, 1)
    target_max_cand0 = min(target_max_cand0, len(cand0_indices))

    if len(cand0_indices) <= target_max_cand0:
        return row_indices

    retained_cand0 = np.sort(rng.choice(cand0_indices, size=target_max_cand0, replace=False))
    return np.sort(np.concatenate([cand1_indices, retained_cand0]))


def build_sample_weights(y_train: np.ndarray, cand0_mask: np.ndarray, cand0_sample_weight: float) -> np.ndarray:
    weights = np.ones(len(y_train), dtype=np.float64)
    class_counts = np.bincount(y_train, minlength=len(CLASS_IDS))
    present_classes = np.flatnonzero(class_counts > 0)
    if len(present_classes) > 0:
        class_weights = np.ones(len(CLASS_IDS), dtype=np.float64)
        for class_id in present_classes:
            class_weights[class_id] = len(y_train) / float(len(present_classes) * class_counts[class_id])
        weights *= class_weights[y_train]

    weights[cand0_mask] *= cand0_sample_weight
    mean_weight = float(weights.mean())
    if mean_weight > EPSILON:
        weights /= mean_weight
    return weights


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_ready(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def train_regime_classifier(
    regime_id: int,
    X_all: np.ndarray,
    labels: pd.DataFrame,
    regime_train_indices: np.ndarray,
    regime_val_indices: np.ndarray,
    config: Step12Config,
    output_dir: Path,
) -> RegimeTrainingResult:
    regime_dir = output_dir / f"regime_{regime_id}"
    regime_dir.mkdir(parents=True, exist_ok=True)

    train_frame_raw = labels.iloc[regime_train_indices].reset_index(drop=True)
    val_frame = labels.iloc[regime_val_indices].reset_index(drop=True)
    train_label_distribution = distribution_from_labels(train_frame_raw["label_dir_int"].to_numpy(dtype=np.int64))
    val_label_distribution = distribution_from_labels(val_frame["label_dir_int"].to_numpy(dtype=np.int64))

    if train_frame_raw.empty:
        report_path = regime_dir / "train_report.json"
        write_json(
            report_path,
            {
                "regime_id": regime_id,
                "status": "skipped_no_train",
                "train_count_raw": 0,
                "val_count": int(len(val_frame)),
                "train_label_distribution": train_label_distribution,
                "val_label_distribution": val_label_distribution,
            },
        )
        return RegimeTrainingResult(
            regime_id=regime_id,
            status="skipped_no_train",
            train_count_raw=0,
            train_count_retained=0,
            val_count=int(len(val_frame)),
            cand0_retained_count=0,
            cand1_retained_count=0,
            best_epoch=None,
            epochs_trained=0,
            early_stopped=False,
            model_path=None,
            report_path=str(report_path),
            train_metrics=None,
            val_metrics=None,
            train_label_distribution=train_label_distribution,
            val_label_distribution=val_label_distribution,
        )

    rng = np.random.default_rng(config.seed + regime_id)
    retained_local_indices = select_retained_train_rows(train_frame_raw, config, rng)
    train_frame = train_frame_raw.iloc[retained_local_indices].reset_index(drop=True)
    X_train = X_all[regime_train_indices][retained_local_indices]
    X_val = X_all[regime_val_indices]
    y_train = train_frame["label_dir_int"].to_numpy(dtype=np.int64)
    retained_cand0_mask = cand0_mask_from_frame(train_frame)
    sample_weights = build_sample_weights(y_train, retained_cand0_mask, config.cand0_sample_weight)

    model = MLPClassifier(
        hidden_layer_sizes=config.hidden_layers,
        activation="relu",
        solver="adam",
        alpha=config.weight_decay,
        batch_size=min(config.batch_size, len(train_frame)),
        learning_rate_init=config.learning_rate,
        max_iter=1,
        shuffle=False,
        random_state=config.seed + regime_id,
        warm_start=False,
    )

    history: list[dict[str, Any]] = []
    best_model: MLPClassifier | None = None
    best_epoch: int | None = None
    best_score = math.inf
    epochs_without_improve = 0
    epochs_trained = 0

    for epoch in range(1, config.epochs + 1):
        permutation = rng.permutation(len(train_frame))
        X_epoch = X_train[permutation]
        y_epoch = y_train[permutation]
        w_epoch = sample_weights[permutation]
        if epoch == 1:
            model.partial_fit(X_epoch, y_epoch, classes=CLASS_IDS, sample_weight=w_epoch)
        else:
            model.partial_fit(X_epoch, y_epoch, sample_weight=w_epoch)

        epochs_trained = epoch
        epoch_train_metrics = compute_metrics(model, X_train, train_frame)
        epoch_val_metrics = compute_metrics(model, X_val, val_frame)
        monitor_metrics = epoch_val_metrics if epoch_val_metrics is not None else epoch_train_metrics
        assert monitor_metrics is not None

        monitor_score = float(monitor_metrics["log_loss"])
        history.append(
            {
                "epoch": epoch,
                "train_log_loss": epoch_train_metrics["log_loss"] if epoch_train_metrics else None,
                "val_log_loss": epoch_val_metrics["log_loss"] if epoch_val_metrics else None,
                "monitor_log_loss": monitor_score,
            }
        )

        if monitor_score + config.min_delta < best_score:
            best_score = monitor_score
            best_epoch = epoch
            best_model = copy.deepcopy(model)
            epochs_without_improve = 0
        else:
            epochs_without_improve += 1
            if epochs_without_improve >= config.patience:
                break

    if best_model is None:
        best_model = copy.deepcopy(model)
        best_epoch = epochs_trained

    train_metrics = compute_metrics(best_model, X_train, train_frame)
    val_metrics = compute_metrics(best_model, X_val, val_frame)
    model_path = regime_dir / f"clf_reg{regime_id}.joblib"
    report_path = regime_dir / "train_report.json"

    model_bundle = {
        "clf_version": f"step12_{config.model_name}",
        "model_name": config.model_name,
        "regime_id": regime_id,
        "hidden_layers": list(config.hidden_layers),
        "classes": [int(class_id) for class_id in CLASS_IDS.tolist()],
        "class_names": [CLASS_NAMES[idx] for idx in CLASS_IDS.tolist()],
        "window_size": WINDOW_SIZE,
        "feature_dim": FEATURE_DIM,
        "feature_columns": FEATURE_COLUMNS,
        "scaled_feature_columns": SCALED_FEATURE_COLUMNS,
        "model": best_model,
    }
    joblib.dump(model_bundle, model_path)

    report_payload = {
        "regime_id": regime_id,
        "status": "trained" if val_metrics is not None else "trained_no_val",
        "train_count_raw": int(len(train_frame_raw)),
        "train_count_retained": int(len(train_frame)),
        "val_count": int(len(val_frame)),
        "cand0_retained_count": int(retained_cand0_mask.sum()),
        "cand1_retained_count": int((~retained_cand0_mask).sum()),
        "best_epoch": best_epoch,
        "epochs_trained": epochs_trained,
        "early_stopped": bool(epochs_trained < config.epochs),
        "train_label_distribution_raw": train_label_distribution,
        "train_label_distribution_retained": distribution_from_labels(y_train),
        "val_label_distribution": val_label_distribution,
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "history": history,
        "model_path": str(model_path),
    }
    write_json(report_path, report_payload)

    return RegimeTrainingResult(
        regime_id=regime_id,
        status=str(report_payload["status"]),
        train_count_raw=int(len(train_frame_raw)),
        train_count_retained=int(len(train_frame)),
        val_count=int(len(val_frame)),
        cand0_retained_count=int(retained_cand0_mask.sum()),
        cand1_retained_count=int((~retained_cand0_mask).sum()),
        best_epoch=int(best_epoch) if best_epoch is not None else None,
        epochs_trained=int(epochs_trained),
        early_stopped=bool(report_payload["early_stopped"]),
        model_path=str(model_path),
        report_path=str(report_path),
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        train_label_distribution=train_label_distribution,
        val_label_distribution=val_label_distribution,
    )


def build_training_metadata(
    bundle: Step11Bundle,
    config: Step12Config,
    split_plan: SplitPlan,
    scaler: ScalerStats,
    train_bar_mask: np.ndarray,
    results: list[RegimeTrainingResult],
) -> dict[str, Any]:
    cand0_recall_values = [
        float(result.val_metrics["cand0_pass_recall"])
        for result in results
        if result.val_metrics is not None and result.val_metrics.get("cand0_pass_recall") is not None
    ]
    min_cand0_pass_recall = min(cand0_recall_values) if cand0_recall_values else None
    acceptance = {
        "A1_no_time_leakage": split_plan.no_time_leakage,
        "A2_cand0_pass_recall_min": min_cand0_pass_recall,
        "A2_threshold": DEFAULT_ACCEPTANCE_CAND0_PASS_RECALL,
        "A2_pass": None
        if min_cand0_pass_recall is None
        else bool(min_cand0_pass_recall >= DEFAULT_ACCEPTANCE_CAND0_PASS_RECALL),
        "A3_export_deferred_to_step15": True,
        "evaluated_regimes": len(cand0_recall_values),
    }

    per_regime = {
        str(result.regime_id): {
            **result.summary_row(),
            "train_label_distribution": result.train_label_distribution,
            "val_label_distribution": result.val_label_distribution,
            "train_metrics": result.train_metrics,
            "val_metrics": result.val_metrics,
        }
        for result in results
    }

    metadata = {
        "implementation_status": "step12_baseline_implemented",
        "clf_version": f"step12_{config.model_name}",
        "architecture_baseline": {
            "family": "sklearn_mlp",
            "hidden_layers": list(config.hidden_layers),
        },
        "training_config": {
            "train_ratio": config.train_ratio,
            "embargo_bars": split_plan.embargo_bars,
            "min_train_samples_per_regime": config.min_train_samples_per_regime,
            "min_val_samples_per_regime": config.min_val_samples_per_regime,
            "cand0_max_fraction": config.cand0_max_fraction,
            "cand0_sample_weight": config.cand0_sample_weight,
            "learning_rate": config.learning_rate,
            "weight_decay": config.weight_decay,
            "batch_size": config.batch_size,
            "epochs": config.epochs,
            "patience": config.patience,
            "min_delta": config.min_delta,
            "seed": config.seed,
            "model_name": config.model_name,
        },
        "source_step11_metadata": bundle.metadata,
        "data_start": bundle.metadata.get("data_start"),
        "data_end": bundle.metadata.get("data_end"),
        "total_labeled_samples": int(len(bundle.labels)),
        "train_bar_count": int(train_bar_mask.sum()),
        "scaler_source": "global_train_bars",
        "scaler_bar_count": scaler.bar_count,
        "scaler_replaced_std_indices": scaler.replaced_std_indices,
        "split_plan": split_plan.summary(),
        "per_regime": per_regime,
        "acceptance": acceptance,
    }
    return json_ready(metadata)


def main() -> int:
    config = parse_args()
    config.output_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_step11_bundle(config.input_dir)
    embargo_bars = bundle.H if config.embargo_bars is None else int(config.embargo_bars)

    split_plan, train_mask, val_mask, _ = choose_global_split(
        bundle.labels,
        target_train_ratio=config.train_ratio,
        embargo_bars=embargo_bars,
        min_train_samples_per_regime=config.min_train_samples_per_regime,
        min_val_samples_per_regime=config.min_val_samples_per_regime,
    )
    scaler, train_bar_mask = compute_scaler(bundle.features, bundle.labels, train_mask)
    X_all = build_scaled_windows(bundle.features, bundle.labels, scaler)

    regimes = bundle.labels["regime_id"].to_numpy(dtype=np.int64)
    results: list[RegimeTrainingResult] = []
    for regime_id in range(6):
        regime_train_indices = np.flatnonzero(train_mask & (regimes == regime_id))
        regime_val_indices = np.flatnonzero(val_mask & (regimes == regime_id))
        result = train_regime_classifier(
            regime_id=regime_id,
            X_all=X_all,
            labels=bundle.labels,
            regime_train_indices=regime_train_indices,
            regime_val_indices=regime_val_indices,
            config=config,
            output_dir=config.output_dir,
        )
        results.append(result)
        print(
            f"[STEP12] regime={regime_id} status={result.status} "
            f"train={result.train_count_retained} val={result.val_count} best_epoch={result.best_epoch}"
        )

    training_metadata = build_training_metadata(bundle, config, split_plan, scaler, train_bar_mask, results)
    write_json(config.output_dir / "training_metadata.json", training_metadata)
    write_json(config.output_dir / "split_plan.json", split_plan.summary())
    write_json(config.output_dir / "scaler_stats.json", scaler.as_json())

    summary_rows = []
    for result in results:
        row = result.summary_row()
        row["train_macro_f1"] = result.train_metrics["macro_f1"] if result.train_metrics else None
        row["val_macro_f1"] = result.val_metrics["macro_f1"] if result.val_metrics else None
        row["val_cand0_pass_recall"] = result.val_metrics["cand0_pass_recall"] if result.val_metrics else None
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(config.output_dir / "regime_summary.csv", index=False)

    acceptance = training_metadata["acceptance"]
    print(f"[STEP12] split train={split_plan.train_count} val={split_plan.val_count} dropped={split_plan.dropped_count}")
    print(f"[STEP12] no_time_leakage={acceptance['A1_no_time_leakage']}")
    print(f"[STEP12] min_cand0_pass_recall={acceptance['A2_cand0_pass_recall_min']}")
    print(f"[STEP12] training_metadata={config.output_dir / 'training_metadata.json'}")

    if config.fail_on_acceptance:
        if not acceptance["A1_no_time_leakage"]:
            return 2
        if acceptance["A2_pass"] is False:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
