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
from sklearn.neural_network import MLPClassifier

from .step12 import (
    CLASS_IDS,
    ScalerStats,
    SplitPlan,
    Step11Bundle,
    Step12Config,
    build_sample_weights,
    build_scaled_windows,
    cand0_mask_from_frame,
    compute_metrics,
    compute_scaler,
    count_by_regime,
    counts_to_regime_dict,
    json_ready,
    load_step11_bundle,
    select_retained_train_rows,
    train_regime_classifier,
    write_json,
)
from .step13 import (
    DEFAULT_PARAM_VECTOR,
    LOWER_BOUNDS,
    UPPER_BOUNDS,
    Step12Context,
    Step13Config,
    build_acceptance as build_step13_acceptance,
    build_stage2_frame,
    build_stage2_sample_weights,
    compute_direction_metrics,
    load_step12_context,
    make_direction_regressor,
    rebuild_masks_from_split_plan,
    run_bundle_smoke,
    train_regime_bundle,
)
from .step12 import build_training_metadata as build_step12_training_metadata
from .step13 import build_training_metadata as build_step13_training_metadata


REPRO_DEFAULT_TOLERANCE = 1e-8
STAGE1_PROB_TOLERANCE = 1e-6
STAGE1_PRIMARY_METRIC = "mean_macro_f1"
STAGE1_PRIMARY_METRIC_TOLERANCE = 1e-3
STAGE2_PRIMARY_METRIC = "mean_normalized_effective_mae_mean"


@dataclass(frozen=True)
class Step14Config:
    step11_dir: Path
    step12_dir: Path
    step13_dir: Path
    output_dir: Path
    inner_fold_train_ratios: tuple[float, ...]
    embargo_bars: int
    min_train_samples_per_regime: int
    min_val_samples_per_regime: int
    min_train_samples_per_head: int
    min_val_samples_per_head: int
    stage1_hidden_layer_options: tuple[tuple[int, ...], ...]
    stage1_targeted_variants: tuple[dict[str, Any], ...]
    cand0_max_fractions: tuple[float, ...]
    cand0_sample_weights: tuple[float, ...]
    gbr_n_estimators_grid: tuple[int, ...]
    gbr_learning_rates: tuple[float, ...]
    gbr_max_depths: tuple[int, ...]
    seed: int
    repro_tolerance: float
    run_repro_check: bool
    fail_on_acceptance: bool


@dataclass(frozen=True)
class CandidateSpec:
    stage: str
    candidate_id: str
    search_rank: int
    is_baseline: bool
    params: dict[str, Any]

    def row(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "candidate_id": self.candidate_id,
            "search_rank": self.search_rank,
            "is_baseline": self.is_baseline,
            **self.params,
        }


@dataclass(frozen=True)
class InnerFoldPlan:
    fold_id: int
    target_train_ratio: float
    target_outer_position: int
    selected_outer_position: int
    selected_label_index: int
    boundary_window_end_idx: int
    effective_train_ratio: float
    embargo_bars: int
    train_count: int
    val_count: int
    dropped_count: int
    train_end_time: str
    val_start_time: str
    no_time_leakage: bool
    relaxed_min_requirement: bool
    train_counts_by_regime: dict[str, int]
    val_counts_by_regime: dict[str, int]
    dropped_counts_by_regime: dict[str, int]
    stage2_train_counts_by_regime_side: dict[str, int]
    stage2_val_counts_by_regime_side: dict[str, int]

    def as_json(self) -> dict[str, Any]:
        return json_ready(
            {
                "fold_id": self.fold_id,
                "target_train_ratio": self.target_train_ratio,
                "target_outer_position": self.target_outer_position,
                "selected_outer_position": self.selected_outer_position,
                "selected_label_index": self.selected_label_index,
                "boundary_window_end_idx": self.boundary_window_end_idx,
                "effective_train_ratio": self.effective_train_ratio,
                "embargo_bars": self.embargo_bars,
                "train_count": self.train_count,
                "val_count": self.val_count,
                "dropped_count": self.dropped_count,
                "train_end_time": self.train_end_time,
                "val_start_time": self.val_start_time,
                "no_time_leakage": self.no_time_leakage,
                "relaxed_min_requirement": self.relaxed_min_requirement,
                "train_counts_by_regime": self.train_counts_by_regime,
                "val_counts_by_regime": self.val_counts_by_regime,
                "dropped_counts_by_regime": self.dropped_counts_by_regime,
                "stage2_train_counts_by_regime_side": self.stage2_train_counts_by_regime_side,
                "stage2_val_counts_by_regime_side": self.stage2_val_counts_by_regime_side,
            }
        )


@dataclass(frozen=True)
class FoldRuntime:
    plan: InnerFoldPlan
    train_mask: np.ndarray
    val_mask: np.ndarray
    dropped_mask: np.ndarray
    scaler: ScalerStats
    train_bar_mask: np.ndarray
    X_all: np.ndarray
    stage2_frame: pd.DataFrame


def parse_args() -> Step14Config:
    parser = argparse.ArgumentParser(description="STEP14 validation/tuning/selection harness for Triple Sigma.")
    parser.add_argument("--step11-dir", required=True, help="Accepted STEP11 artifact directory")
    parser.add_argument("--step12-dir", required=True, help="Accepted STEP12 q1 artifact directory")
    parser.add_argument("--step13-dir", required=True, help="Accepted STEP13 q1 artifact directory")
    parser.add_argument("--output-dir", required=True, help="STEP14 output directory")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repro-tolerance", type=float, default=REPRO_DEFAULT_TOLERANCE)
    parser.add_argument("--skip-repro-check", action="store_true")
    parser.add_argument("--fail-on-acceptance", action="store_true")
    args = parser.parse_args()

    if args.repro_tolerance <= 0.0:
        raise ValueError("repro_tolerance must be > 0")

    return Step14Config(
        step11_dir=Path(args.step11_dir),
        step12_dir=Path(args.step12_dir),
        step13_dir=Path(args.step13_dir),
        output_dir=Path(args.output_dir),
        inner_fold_train_ratios=(0.60, 0.80),
        embargo_bars=72,
        min_train_samples_per_regime=24,
        min_val_samples_per_regime=4,
        min_train_samples_per_head=12,
        min_val_samples_per_head=4,
        stage1_hidden_layer_options=((64, 32), (80, 40), (96, 48), (128, 64, 32)),
        stage1_targeted_variants=(
            {
                "hidden_layers": (96, 48),
                "learning_rate": 0.0005,
                "weight_decay": 0.0005,
            },
            {
                "hidden_layers": (128, 64, 32),
                "learning_rate": 0.0005,
                "weight_decay": 0.001,
            },
        ),
        cand0_max_fractions=(0.95, 0.75, 0.50),
        cand0_sample_weights=(1.0, 0.3),
        gbr_n_estimators_grid=(120, 180),
        gbr_learning_rates=(0.05, 0.03),
        gbr_max_depths=(2, 3),
        seed=args.seed,
        repro_tolerance=args.repro_tolerance,
        run_repro_check=not args.skip_repro_check,
        fail_on_acceptance=args.fail_on_acceptance,
    )


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(load_text(path))


def compare_bytes(path_a: Path, path_b: Path) -> bool:
    return path_a.read_bytes() == path_b.read_bytes()


def require_keys(payload: dict[str, Any], required_keys: tuple[str, ...]) -> list[str]:
    return [key for key in required_keys if key not in payload]


def load_context(config: Step14Config) -> tuple[Step11Bundle, Step12Context, dict[str, Any]]:
    bundle = load_step11_bundle(config.step11_dir)
    step12_context = load_step12_context(config.step12_dir)
    step13_metadata = load_json(config.step13_dir / "training_metadata.json")
    return bundle, step12_context, step13_metadata


def build_stage2_all(labels: pd.DataFrame) -> pd.DataFrame:
    all_train = np.ones(len(labels), dtype=bool)
    none_val = np.zeros(len(labels), dtype=bool)
    stage2_all, _ = build_stage2_frame(labels, all_train, none_val)
    return stage2_all


def count_stage2_by_regime_side(stage2_all: pd.DataFrame, label_mask: np.ndarray) -> dict[str, int]:
    if len(stage2_all) == 0:
        return {f"{regime}_{side}": 0 for regime in range(6) for side in ("LONG", "SHORT")}

    retained_mask = label_mask[stage2_all["label_row_idx"].to_numpy(dtype=np.int64)]
    retained = stage2_all.loc[retained_mask]
    out = {f"{regime}_{side}": 0 for regime in range(6) for side in ("LONG", "SHORT")}
    grouped = retained.groupby(["regime_id", "target_side"]).size()
    for (regime_id, side), count in grouped.items():
        out[f"{int(regime_id)}_{str(side)}"] = int(count)
    return out


def stage2_counts_meet_minimums(counts: dict[str, int], *, minimum: int) -> bool:
    for regime_id in range(6):
        for side in ("LONG", "SHORT"):
            if counts[f"{regime_id}_{side}"] < minimum:
                return False
    return True


def split_plan_from_summary(summary: dict[str, Any]) -> SplitPlan:
    return SplitPlan(
        target_split_index=int(summary["target_split_index"]),
        selected_split_index=int(summary["selected_split_index"]),
        boundary_window_end_idx=int(summary["boundary_window_end_idx"]),
        target_train_ratio=float(summary["target_train_ratio"]),
        effective_train_ratio=float(summary["effective_train_ratio"]),
        embargo_bars=int(summary["embargo_bars"]),
        train_count=int(summary["train_count"]),
        val_count=int(summary["val_count"]),
        dropped_count=int(summary["dropped_count"]),
        requested_min_val_samples_per_regime=int(summary["requested_min_val_samples_per_regime"]),
        effective_min_val_samples_per_regime=int(summary["effective_min_val_samples_per_regime"]),
        relaxed_min_val_requirement=bool(summary["relaxed_min_val_requirement"]),
        train_end_time=str(summary["train_end_time"]),
        val_start_time=str(summary["val_start_time"]),
        no_time_leakage=bool(summary["no_time_leakage"]),
        fallback_used=bool(summary["fallback_used"]),
        train_counts_by_regime={str(key): int(value) for key, value in summary["train_counts_by_regime"].items()},
        val_counts_by_regime={str(key): int(value) for key, value in summary["val_counts_by_regime"].items()},
        dropped_counts_by_regime={str(key): int(value) for key, value in summary["dropped_counts_by_regime"].items()},
    )


def serialize_timestamp(value: pd.Timestamp | Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def audit_lineage(
    config: Step14Config,
    bundle: Step11Bundle,
    step12_context: Step12Context,
    step13_metadata: dict[str, Any],
) -> dict[str, Any]:
    step12_split_path = config.step12_dir / "split_plan.json"
    step12_scaler_path = config.step12_dir / "scaler_stats.json"
    step13_split_path = config.step13_dir / "split_plan.json"
    step13_scaler_path = config.step13_dir / "scaler_stats.json"

    required_metadata_keys = (
        "schema_version",
        "candidate_policy_version",
        "regime_policy_version",
        "cost_model_version",
        "search_space_version",
        "atr_thr",
        "adx_thr1",
        "adx_thr2",
    )
    missing_metadata_keys = require_keys(bundle.metadata, required_metadata_keys)

    step12_acceptance = step12_context.training_metadata.get("acceptance", {})
    step13_acceptance = step13_metadata.get("acceptance", {})
    step13_hard_flags = {
        flag: bool(step13_acceptance.get(flag, False))
        for flag in (
            "A1_split_match_step12",
            "A2_step12_no_time_leakage",
            "A3_cand1_only",
            "A4_masking_integrity",
            "A5_bundle_predict_shape_and_finite",
            "A6_postprocess_contract_valid",
            "A7_export_deferred_to_step15",
        )
    }

    audit = {
        "step12_no_time_leakage": bool(step12_acceptance.get("A1_no_time_leakage", False)),
        "step13_acceptance": step13_hard_flags,
        "split_plan_byte_equal": compare_bytes(step12_split_path, step13_split_path),
        "scaler_stats_byte_equal": compare_bytes(step12_scaler_path, step13_scaler_path),
        "required_threshold_metadata_present": not missing_metadata_keys,
        "missing_threshold_metadata_keys": missing_metadata_keys,
    }
    audit["passed"] = bool(
        audit["step12_no_time_leakage"]
        and all(step13_hard_flags.values())
        and audit["split_plan_byte_equal"]
        and audit["scaler_stats_byte_equal"]
        and audit["required_threshold_metadata_present"]
    )
    return json_ready(audit)


def build_outer_split_audit(labels: pd.DataFrame, step12_context: Step12Context) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    train_mask, val_mask, dropped_mask, split_audit = rebuild_masks_from_split_plan(labels, step12_context.split_plan)
    audit = split_audit.as_json()
    audit["embargo_bars"] = int(step12_context.split_plan["embargo_bars"])
    audit["outer_split_source"] = "accepted_step12_q1"
    return train_mask, val_mask, dropped_mask, json_ready(audit)


def choose_single_inner_fold(
    *,
    labels: pd.DataFrame,
    outer_train_mask: np.ndarray,
    stage2_all: pd.DataFrame,
    target_train_ratio: float,
    config: Step14Config,
    fold_id: int,
) -> tuple[InnerFoldPlan, np.ndarray, np.ndarray, np.ndarray]:
    window_end = labels["window_end_idx"].to_numpy(dtype=np.int64)
    regimes = labels["regime_id"].to_numpy(dtype=np.int64)
    label_times = labels["bar_time"].to_numpy()
    observed_regimes = sorted(int(value) for value in np.unique(regimes))
    outer_indices = np.flatnonzero(outer_train_mask)
    if len(outer_indices) < 2:
        raise ValueError("outer train split is too small to create inner folds")

    outer_window_end = window_end[outer_indices]
    outer_regimes = regimes[outer_indices]
    outer_label_times = label_times[outer_indices]
    observed_regime_array = np.asarray(observed_regimes, dtype=np.int64)
    regime_positions = np.searchsorted(observed_regime_array, outer_regimes)
    if not np.array_equal(observed_regime_array[regime_positions], outer_regimes):
        raise ValueError("outer_train_mask contains regimes outside observed_regimes")

    regime_one_hot = np.zeros((len(outer_indices), len(observed_regimes)), dtype=np.int32)
    regime_one_hot[np.arange(len(outer_indices)), regime_positions] = 1
    cumulative_regime_counts = np.zeros((len(outer_indices) + 1, len(observed_regimes)), dtype=np.int32)
    np.cumsum(regime_one_hot, axis=0, dtype=np.int32, out=cumulative_regime_counts[1:])
    total_regime_counts = cumulative_regime_counts[-1]

    stage2_keys = [f"{regime}_{side}" for regime in range(6) for side in ("LONG", "SHORT")]
    stage2_key_to_position = {key: idx for idx, key in enumerate(stage2_keys)}
    stage2_label_counts = np.zeros((len(labels), len(stage2_keys)), dtype=np.int16)
    for row in stage2_all.itertuples(index=False):
        key = f"{int(row.regime_id)}_{str(row.target_side)}"
        stage2_label_counts[int(row.label_row_idx), stage2_key_to_position[key]] += 1
    outer_stage2_counts = stage2_label_counts[outer_indices]
    cumulative_stage2_counts = np.zeros((len(outer_indices) + 1, len(stage2_keys)), dtype=np.int32)
    np.cumsum(outer_stage2_counts, axis=0, dtype=np.int32, out=cumulative_stage2_counts[1:])
    total_stage2_counts = cumulative_stage2_counts[-1]

    def counts_to_stage2_dict(counts: np.ndarray) -> dict[str, int]:
        return {key: int(count) for key, count in zip(stage2_keys, counts.tolist())}

    target_outer_position = max(1, min(len(outer_indices) - 1, int(round(len(outer_indices) * target_train_ratio))))
    target_label_index = int(outer_indices[target_outer_position])

    selected: dict[str, Any] | None = None
    selected_key: tuple[float, int, int] | None = None
    for selected_outer_position in range(1, len(outer_indices)):
        selected_label_index = int(outer_indices[selected_outer_position])
        boundary_window_end_idx = int(outer_window_end[selected_outer_position])
        train_count = int(np.searchsorted(outer_window_end, boundary_window_end_idx - config.embargo_bars, side="left"))
        val_start_position = int(np.searchsorted(outer_window_end, boundary_window_end_idx, side="left"))
        val_count = len(outer_indices) - val_start_position
        if train_count <= 0 or val_count <= 0:
            continue

        train_counts_array = cumulative_regime_counts[train_count]
        val_counts_array = total_regime_counts - cumulative_regime_counts[val_start_position]
        if np.any(train_counts_array < config.min_train_samples_per_regime):
            continue
        if np.any(val_counts_array < config.min_val_samples_per_regime):
            continue

        stage2_train_counts_array = cumulative_stage2_counts[train_count]
        stage2_val_counts_array = total_stage2_counts - cumulative_stage2_counts[val_start_position]
        stage2_train_counts = counts_to_stage2_dict(stage2_train_counts_array)
        stage2_val_counts = counts_to_stage2_dict(stage2_val_counts_array)
        if not stage2_counts_meet_minimums(stage2_train_counts, minimum=config.min_train_samples_per_head):
            continue
        if not stage2_counts_meet_minimums(stage2_val_counts, minimum=config.min_val_samples_per_head):
            continue

        max_train_end = int(outer_window_end[train_count - 1])
        min_val_end = int(outer_window_end[val_start_position])
        no_time_leakage = bool(max_train_end + config.embargo_bars < min_val_end)
        if not no_time_leakage:
            continue

        dropped_count = int(val_start_position - train_count)
        effective_ratio = train_count / float(train_count + val_count)
        candidate_key = (
            abs(effective_ratio - target_train_ratio),
            abs(selected_label_index - target_label_index),
            dropped_count,
        )
        if selected_key is not None and candidate_key >= selected_key:
            continue

        selected_key = candidate_key
        selected = {
            "selected_outer_position": selected_outer_position,
            "selected_label_index": selected_label_index,
            "boundary_window_end_idx": boundary_window_end_idx,
            "train_count": train_count,
            "val_count": val_count,
            "dropped_count": dropped_count,
            "effective_ratio": effective_ratio,
            "train_counts_by_regime": counts_to_regime_dict(train_counts_array, observed_regimes),
            "val_counts_by_regime": counts_to_regime_dict(val_counts_array, observed_regimes),
            "dropped_counts_by_regime": counts_to_regime_dict(
                total_regime_counts - train_counts_array - val_counts_array,
                observed_regimes,
            ),
            "stage2_train_counts_by_regime_side": stage2_train_counts,
            "stage2_val_counts_by_regime_side": stage2_val_counts,
            "train_end_time": serialize_timestamp(outer_label_times[train_count - 1]),
            "val_start_time": serialize_timestamp(outer_label_times[val_start_position]),
        }

    if selected is None:
        raise ValueError(
            f"unable to build inner fold {fold_id} with target_train_ratio={target_train_ratio:.2f} "
            f"and strict minima (regime train/val={config.min_train_samples_per_regime}/{config.min_val_samples_per_regime}, "
            f"head train/val={config.min_train_samples_per_head}/{config.min_val_samples_per_head})"
        )
    boundary_window_end_idx = int(selected["boundary_window_end_idx"])
    train_mask = outer_train_mask & (window_end + config.embargo_bars < boundary_window_end_idx)
    val_mask = outer_train_mask & (window_end >= boundary_window_end_idx)
    dropped_mask = outer_train_mask & ~(train_mask | val_mask)

    plan = InnerFoldPlan(
        fold_id=fold_id,
        target_train_ratio=float(target_train_ratio),
        target_outer_position=int(target_outer_position),
        selected_outer_position=int(selected["selected_outer_position"]),
        selected_label_index=int(selected["selected_label_index"]),
        boundary_window_end_idx=int(selected["boundary_window_end_idx"]),
        effective_train_ratio=float(selected["effective_ratio"]),
        embargo_bars=int(config.embargo_bars),
        train_count=int(selected["train_count"]),
        val_count=int(selected["val_count"]),
        dropped_count=int(selected["dropped_count"]),
        train_end_time=str(selected["train_end_time"]),
        val_start_time=str(selected["val_start_time"]),
        no_time_leakage=True,
        relaxed_min_requirement=False,
        train_counts_by_regime=selected["train_counts_by_regime"],
        val_counts_by_regime=selected["val_counts_by_regime"],
        dropped_counts_by_regime=selected["dropped_counts_by_regime"],
        stage2_train_counts_by_regime_side=selected["stage2_train_counts_by_regime_side"],
        stage2_val_counts_by_regime_side=selected["stage2_val_counts_by_regime_side"],
    )
    return plan, train_mask, val_mask, dropped_mask


def choose_inner_splits(
    *,
    bundle: Step11Bundle,
    outer_train_mask: np.ndarray,
    config: Step14Config,
) -> list[FoldRuntime]:
    stage2_all = build_stage2_all(bundle.labels)
    fold_runtimes: list[FoldRuntime] = []
    for fold_id, target_ratio in enumerate(config.inner_fold_train_ratios):
        plan, train_mask, val_mask, dropped_mask = choose_single_inner_fold(
            labels=bundle.labels,
            outer_train_mask=outer_train_mask,
            stage2_all=stage2_all,
            target_train_ratio=target_ratio,
            config=config,
            fold_id=fold_id,
        )
        scaler, train_bar_mask = compute_scaler(bundle.features, bundle.labels, train_mask)
        X_all = build_scaled_windows(bundle.features, bundle.labels, scaler)
        stage2_frame, _ = build_stage2_frame(bundle.labels, train_mask, val_mask)
        fold_runtimes.append(
            FoldRuntime(
                plan=plan,
                train_mask=train_mask,
                val_mask=val_mask,
                dropped_mask=dropped_mask,
                scaler=scaler,
                train_bar_mask=train_bar_mask,
                X_all=X_all,
                stage2_frame=stage2_frame,
            )
        )
    return fold_runtimes


def build_inner_split_manifest(folds: list[FoldRuntime]) -> dict[str, Any]:
    return json_ready(
        {
            "fold_count": len(folds),
            "folds": [fold.plan.as_json() for fold in folds],
            "shuffle": False,
            "relaxed_min_requirement": False,
        }
    )


def dedupe_candidate_params(param_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for params in param_sets:
        key = json.dumps(json_ready(params), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(params)
    return unique


def build_stage1_candidate_registry(config: Step14Config) -> list[CandidateSpec]:
    baseline_hidden_layers = tuple(int(value) for value in config.stage1_hidden_layer_options[0])
    cand0_combos = [
        {
            "cand0_max_fraction": float(cand0_max_fraction),
            "cand0_sample_weight": float(cand0_sample_weight),
        }
        for cand0_max_fraction in config.cand0_max_fractions
        for cand0_sample_weight in config.cand0_sample_weights
    ]
    baseline_params = {
        "cand0_max_fraction": config.cand0_max_fractions[0],
        "cand0_sample_weight": config.cand0_sample_weights[0],
        "hidden_layers": baseline_hidden_layers,
    }
    cand0_variants = [
        {
            **combo,
            "hidden_layers": baseline_hidden_layers,
        }
        for combo in cand0_combos
        if combo
        != {
            "cand0_max_fraction": baseline_params["cand0_max_fraction"],
            "cand0_sample_weight": baseline_params["cand0_sample_weight"],
        }
    ]
    architecture_variants = [
        {
            "cand0_max_fraction": baseline_params["cand0_max_fraction"],
            "cand0_sample_weight": baseline_params["cand0_sample_weight"],
            "hidden_layers": tuple(int(value) for value in hidden_layers),
        }
        for hidden_layers in config.stage1_hidden_layer_options[1:]
    ]
    targeted_variants = [
        {
            "cand0_max_fraction": baseline_params["cand0_max_fraction"],
            "cand0_sample_weight": baseline_params["cand0_sample_weight"],
            **variant,
            "hidden_layers": tuple(int(value) for value in variant.get("hidden_layers", baseline_hidden_layers)),
        }
        for variant in config.stage1_targeted_variants
    ]
    ordered = dedupe_candidate_params([baseline_params, *cand0_variants, *architecture_variants, *targeted_variants])
    return [
        CandidateSpec(
            stage="stage1",
            candidate_id="stage1_baseline" if idx == 0 else f"stage1_c{idx:02d}",
            search_rank=idx,
            is_baseline=idx == 0,
            params=combo,
        )
        for idx, combo in enumerate(ordered)
    ]


def build_stage2_candidate_registry(config: Step14Config) -> list[CandidateSpec]:
    combos = [
        {
            "gbr_n_estimators": int(n_estimators),
            "gbr_learning_rate": float(learning_rate),
            "gbr_max_depth": int(max_depth),
        }
        for n_estimators in config.gbr_n_estimators_grid
        for learning_rate in config.gbr_learning_rates
        for max_depth in config.gbr_max_depths
    ]
    baseline_params = {
        "gbr_n_estimators": config.gbr_n_estimators_grid[0],
        "gbr_learning_rate": config.gbr_learning_rates[0],
        "gbr_max_depth": config.gbr_max_depths[0],
    }
    ordered = [baseline_params] + [combo for combo in combos if combo != baseline_params]
    return [
        CandidateSpec(
            stage="stage2",
            candidate_id="stage2_baseline" if idx == 0 else f"stage2_c{idx:02d}",
            search_rank=idx,
            is_baseline=idx == 0,
            params=combo,
        )
        for idx, combo in enumerate(ordered)
    ]


def candidate_registry_df(candidates: list[CandidateSpec], *, seed: int) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        row = candidate.row()
        row["seed"] = seed
        rows.append(row)
    return pd.DataFrame(rows)


def build_stage1_config(base_config: dict[str, Any], candidate: CandidateSpec, output_dir: Path, seed: int) -> Step12Config:
    hidden_layers = candidate.params.get("hidden_layers", base_config.get("hidden_layers", [64, 32]))
    learning_rate = candidate.params.get("learning_rate", base_config["learning_rate"])
    weight_decay = candidate.params.get("weight_decay", base_config["weight_decay"])
    batch_size = candidate.params.get("batch_size", base_config["batch_size"])
    epochs = candidate.params.get("epochs", base_config["epochs"])
    patience = candidate.params.get("patience", base_config["patience"])
    min_delta = candidate.params.get("min_delta", base_config["min_delta"])
    return Step12Config(
        input_dir=Path("."),
        output_dir=output_dir,
        train_ratio=float(base_config["train_ratio"]),
        embargo_bars=int(base_config["embargo_bars"]),
        min_train_samples_per_regime=int(base_config["min_train_samples_per_regime"]),
        min_val_samples_per_regime=int(base_config["min_val_samples_per_regime"]),
        cand0_max_fraction=float(candidate.params["cand0_max_fraction"]),
        cand0_sample_weight=float(candidate.params["cand0_sample_weight"]),
        hidden_layers=tuple(int(value) for value in hidden_layers),
        learning_rate=float(learning_rate),
        weight_decay=float(weight_decay),
        batch_size=int(batch_size),
        epochs=int(epochs),
        patience=int(patience),
        min_delta=float(min_delta),
        seed=int(seed),
        model_name=str(base_config.get("model_name", "mlp_v1")),
        fail_on_acceptance=False,
    )


def build_stage2_config(
    base_config: dict[str, Any],
    candidate: CandidateSpec,
    *,
    step11_dir: Path,
    step12_dir: Path,
    output_dir: Path,
    seed: int,
) -> Step13Config:
    return Step13Config(
        step11_dir=step11_dir,
        step12_dir=step12_dir,
        output_dir=output_dir,
        min_train_samples_per_head=int(base_config["min_train_samples_per_head"]),
        min_val_samples_per_head=int(base_config["min_val_samples_per_head"]),
        pass_row_weight=float(base_config["pass_row_weight"]),
        gbr_n_estimators=int(candidate.params["gbr_n_estimators"]),
        gbr_learning_rate=float(candidate.params["gbr_learning_rate"]),
        gbr_max_depth=int(candidate.params["gbr_max_depth"]),
        gbr_min_samples_leaf=int(base_config["gbr_min_samples_leaf"]),
        gbr_subsample=float(base_config["gbr_subsample"]),
        gbr_alpha=float(base_config["gbr_alpha"]),
        seed=int(seed),
        model_name=str(base_config.get("model_name", "gbr_huber_masked_v1")),
        fail_on_acceptance=False,
    )


def evaluate_stage1_model(model: MLPClassifier, X: np.ndarray, frame: pd.DataFrame) -> tuple[dict[str, Any] | None, bool, bool]:
    if len(frame) == 0:
        return None, False, False
    probabilities = np.asarray(model.predict_proba(X), dtype=np.float64)
    prob_all_finite = bool(np.isfinite(probabilities).all())
    prob_sum_close = bool(prob_all_finite and np.allclose(probabilities.sum(axis=1), 1.0, atol=STAGE1_PROB_TOLERANCE))
    metrics = compute_metrics(model, X, frame)
    return metrics, prob_all_finite, prob_sum_close


def train_stage1_regime_for_eval(
    *,
    regime_id: int,
    labels: pd.DataFrame,
    X_all: np.ndarray,
    regime_train_indices: np.ndarray,
    regime_val_indices: np.ndarray,
    config: Step12Config,
) -> dict[str, Any]:
    train_frame_raw = labels.iloc[regime_train_indices].reset_index(drop=True)
    val_frame = labels.iloc[regime_val_indices].reset_index(drop=True)
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
        batch_size=min(config.batch_size, max(1, len(train_frame))),
        learning_rate_init=config.learning_rate,
        max_iter=1,
        shuffle=False,
        random_state=config.seed + regime_id,
        warm_start=False,
    )

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

    train_metrics, train_prob_all_finite, train_prob_sum_close = evaluate_stage1_model(best_model, X_train, train_frame)
    val_metrics, prob_all_finite, prob_sum_close = evaluate_stage1_model(best_model, X_val, val_frame)
    return json_ready(
        {
            "status": "trained",
            "train_count_raw": int(len(train_frame_raw)),
            "train_count_retained": int(len(train_frame)),
            "val_count": int(len(val_frame)),
            "cand0_retained_count": int(retained_cand0_mask.sum()),
            "cand1_retained_count": int((~retained_cand0_mask).sum()),
            "best_epoch": int(best_epoch) if best_epoch is not None else None,
            "epochs_trained": int(epochs_trained),
            "early_stopped": bool(epochs_trained < config.epochs),
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "train_prob_all_finite": train_prob_all_finite,
            "train_prob_sum_close": train_prob_sum_close,
            "prob_all_finite": prob_all_finite,
            "prob_sum_close": prob_sum_close,
        }
    )


def direction_contract_valid(values: np.ndarray) -> tuple[bool, bool]:
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return True, True
    in_bounds = bool(
        np.all((values[:, 0] >= LOWER_BOUNDS[0]) & (values[:, 0] <= UPPER_BOUNDS[0]))
        and np.all((values[:, 1] >= LOWER_BOUNDS[1]) & (values[:, 1] <= UPPER_BOUNDS[1]))
        and np.all((values[:, 2] >= LOWER_BOUNDS[2]) & (values[:, 2] <= UPPER_BOUNDS[2]))
    )
    holds_integral = bool(np.allclose(values[:, 2], np.rint(values[:, 2])))
    return in_bounds, holds_integral


def train_stage2_direction_for_eval(
    *,
    side: str,
    regime_id: int,
    X_all: np.ndarray,
    stage2_frame: pd.DataFrame,
    config: Step13Config,
) -> dict[str, Any]:
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
    baseline_train = np.repeat(DEFAULT_PARAM_VECTOR.reshape(1, 3), len(train_frame), axis=0)
    baseline_val = np.repeat(DEFAULT_PARAM_VECTOR.reshape(1, 3), len(val_frame), axis=0)

    sample_weights = build_stage2_sample_weights(train_frame, config.pass_row_weight) if len(train_frame) else np.empty(0)
    fallback_reasons: list[str] = []
    if len(train_frame) < config.min_train_samples_per_head:
        fallback_reasons.append(
            f"train_count={len(train_frame)} < min_train_samples_per_head={config.min_train_samples_per_head}"
        )
    if len(val_frame) < config.min_val_samples_per_head:
        fallback_reasons.append(
            f"val_count={len(val_frame)} < min_val_samples_per_head={config.min_val_samples_per_head}"
        )

    if fallback_reasons:
        raw_val_pred = baseline_val
        effective_val = baseline_val.astype(np.float32, copy=False)
        contract_valid, holds_integral = direction_contract_valid(effective_val)
        return json_ready(
            {
                "status": "fallback_constant",
                "fallback_used": True,
                "fallback_reason": "; ".join(fallback_reasons),
                "train_count": int(len(train_frame)),
                "val_count": int(len(val_frame)),
                "metrics_present": len(val_frame) > 0,
                "val_metrics": compute_direction_metrics(y_val, raw_val_pred, baseline_val) if len(val_frame) else None,
                "raw_all_finite": bool(np.isfinite(raw_val_pred).all()),
                "effective_all_finite": bool(np.isfinite(effective_val).all()),
                "contract_valid": bool(contract_valid),
                "holds_integral": bool(holds_integral),
            }
        )

    model = make_direction_regressor(config, random_state=config.seed + regime_id * 10 + (0 if side == "LONG" else 1))
    model.fit(X_train, y_train, sample_weight=sample_weights)
    raw_val_pred = np.asarray(model.predict(X_val), dtype=np.float64)
    effective_val = np.column_stack(
        [
            np.clip(raw_val_pred[:, 0], LOWER_BOUNDS[0], UPPER_BOUNDS[0]),
            np.clip(raw_val_pred[:, 1], LOWER_BOUNDS[1], UPPER_BOUNDS[1]),
            np.clip(np.rint(raw_val_pred[:, 2]), LOWER_BOUNDS[2], UPPER_BOUNDS[2]),
        ]
    ).astype(np.float32, copy=False)
    contract_valid, holds_integral = direction_contract_valid(effective_val)
    return json_ready(
        {
            "status": "trained",
            "fallback_used": False,
            "fallback_reason": None,
            "train_count": int(len(train_frame)),
            "val_count": int(len(val_frame)),
            "metrics_present": len(val_frame) > 0,
            "val_metrics": compute_direction_metrics(y_val, raw_val_pred, baseline_val) if len(val_frame) else None,
            "raw_all_finite": bool(np.isfinite(raw_val_pred).all()),
            "effective_all_finite": bool(np.isfinite(effective_val).all()),
            "contract_valid": bool(contract_valid),
            "holds_integral": bool(holds_integral),
        }
    )


def run_stage1_cv(
    *,
    bundle: Step11Bundle,
    folds: list[FoldRuntime],
    candidates: list[CandidateSpec],
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    regimes = bundle.labels["regime_id"].to_numpy(dtype=np.int64)
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_config = build_stage1_config(base_training_config, candidate, output_dir, seed)
        for fold in folds:
            for regime_id in range(6):
                regime_train_indices = np.flatnonzero(fold.train_mask & (regimes == regime_id))
                regime_val_indices = np.flatnonzero(fold.val_mask & (regimes == regime_id))
                result = train_stage1_regime_for_eval(
                    regime_id=regime_id,
                    labels=bundle.labels,
                    X_all=fold.X_all,
                    regime_train_indices=regime_train_indices,
                    regime_val_indices=regime_val_indices,
                    config=candidate_config,
                )
                val_metrics = result["val_metrics"]
                rows.append(
                    json_ready(
                        {
                            "candidate_id": candidate.candidate_id,
                            "search_rank": candidate.search_rank,
                            "is_baseline": candidate.is_baseline,
                            "fold_id": fold.plan.fold_id,
                            "regime_id": regime_id,
                            "train_count_raw": result["train_count_raw"],
                            "train_count_retained": result["train_count_retained"],
                            "val_count": result["val_count"],
                            "cand0_retained_count": result["cand0_retained_count"],
                            "cand1_retained_count": result["cand1_retained_count"],
                            "best_epoch": result["best_epoch"],
                            "epochs_trained": result["epochs_trained"],
                            "early_stopped": result["early_stopped"],
                            "status": result["status"],
                            "metrics_present": val_metrics is not None,
                            "prob_all_finite": bool(result["prob_all_finite"]),
                            "prob_sum_close": bool(result["prob_sum_close"]),
                            "macro_f1": None if val_metrics is None else val_metrics["macro_f1"],
                            "pass_precision": None if val_metrics is None else val_metrics["pass_precision"],
                            "pass_recall": None if val_metrics is None else val_metrics["pass_recall"],
                            "cand0_pass_recall": None if val_metrics is None else val_metrics["cand0_pass_recall"],
                            "log_loss": None if val_metrics is None else val_metrics["log_loss"],
                        }
                    )
                )

    summary_df = pd.DataFrame(rows).sort_values(["search_rank", "fold_id", "regime_id"]).reset_index(drop=True)
    expected_rows = len(candidates) * len(folds) * 6
    valid = bool(
        len(summary_df) == expected_rows
        and summary_df["metrics_present"].all()
        and summary_df["prob_all_finite"].all()
        and summary_df["prob_sum_close"].all()
        and summary_df[["macro_f1", "pass_precision", "pass_recall", "cand0_pass_recall", "log_loss"]].notna().all().all()
    )
    report = build_stage1_selection_report(summary_df, candidates)
    return summary_df, {
        "valid": valid,
        "report": report,
        "expected_rows": expected_rows,
    }


def build_stage1_selection_report(summary_df: pd.DataFrame, candidates: list[CandidateSpec]) -> dict[str, Any]:
    candidate_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_df = summary_df.loc[summary_df["candidate_id"] == candidate.candidate_id]
        candidate_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "search_rank": candidate.search_rank,
                "is_baseline": candidate.is_baseline,
                "params": candidate.params,
                "mean_macro_f1": float(candidate_df["macro_f1"].mean()),
                "mean_cand0_pass_recall": float(candidate_df["cand0_pass_recall"].mean()),
                "min_cand0_pass_recall": float(candidate_df["cand0_pass_recall"].min()),
                "mean_log_loss": float(candidate_df["log_loss"].mean()),
                "eligible": bool(candidate_df["cand0_pass_recall"].min() >= 0.50),
            }
        )

    eligible_rows = [row for row in candidate_rows if row["eligible"]]
    baseline_row = next(row for row in candidate_rows if row["is_baseline"])
    provisional_winner = None
    provisional_winner_source = "eligible_set"
    used_control_fallback = False
    if eligible_rows:
        best_macro_f1 = max(row["mean_macro_f1"] for row in eligible_rows)
        tolerance_window = [
            row for row in eligible_rows if row["mean_macro_f1"] >= best_macro_f1 - STAGE1_PRIMARY_METRIC_TOLERANCE
        ]
        provisional_winner = min(
            tolerance_window,
            key=lambda row: (
                -row["mean_cand0_pass_recall"],
                -row["min_cand0_pass_recall"],
                row["mean_log_loss"],
                -row["mean_macro_f1"],
                0 if row["is_baseline"] else 1,
                row["search_rank"],
            ),
        )
    else:
        provisional_winner = baseline_row
        provisional_winner_source = "control_fallback"
        used_control_fallback = True

    return json_ready(
        {
            "primary_metric": STAGE1_PRIMARY_METRIC,
            "primary_metric_tolerance": STAGE1_PRIMARY_METRIC_TOLERANCE,
            "tie_breakers": [
                "higher_mean_cand0_pass_recall",
                "higher_min_cand0_pass_recall",
                "lower_mean_log_loss",
                "higher_mean_macro_f1_within_tolerance_window",
                "baseline_preferred",
            ],
            "baseline_candidate_id": baseline_row["candidate_id"],
            "baseline_candidate_score": baseline_row["mean_macro_f1"],
            "eligible_candidate_count": len(eligible_rows),
            "used_control_fallback": used_control_fallback,
            "provisional_winner_source": provisional_winner_source,
            "provisional_winner_candidate_id": provisional_winner["candidate_id"],
            "provisional_winner_aggregate_score": provisional_winner["mean_macro_f1"],
            "eligibility_guardrail": {
                "name": "min_cand0_pass_recall",
                "threshold": 0.50,
            },
            "candidate_rows": candidate_rows,
        }
    )


def run_stage2_cv(
    *,
    folds: list[FoldRuntime],
    candidates: list[CandidateSpec],
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
    step11_dir: Path,
    step12_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_config = build_stage2_config(
            base_training_config,
            candidate,
            step11_dir=step11_dir,
            step12_dir=step12_dir,
            output_dir=output_dir,
            seed=seed,
        )
        for fold in folds:
            for regime_id in range(6):
                for side in ("LONG", "SHORT"):
                    result = train_stage2_direction_for_eval(
                        side=side,
                        regime_id=regime_id,
                        X_all=fold.X_all,
                        stage2_frame=fold.stage2_frame,
                        config=candidate_config,
                    )
                    val_metrics = result["val_metrics"]
                    rows.append(
                        json_ready(
                            {
                                "candidate_id": candidate.candidate_id,
                                "search_rank": candidate.search_rank,
                                "is_baseline": candidate.is_baseline,
                                "fold_id": fold.plan.fold_id,
                                "regime_id": regime_id,
                                "side": side,
                                "status": result["status"],
                                "fallback_used": bool(result["fallback_used"]),
                                "fallback_reason": result["fallback_reason"],
                                "train_count": result["train_count"],
                                "val_count": result["val_count"],
                                "metrics_present": val_metrics is not None,
                                "raw_all_finite": bool(result["raw_all_finite"]),
                                "effective_all_finite": bool(result["effective_all_finite"]),
                                "contract_valid": bool(result["contract_valid"]),
                                "holds_integral": bool(result["holds_integral"]),
                                "normalized_effective_mae_mean": None
                                if val_metrics is None
                                else val_metrics["normalized_effective_mae_mean"],
                                "baseline_normalized_effective_mae_mean": None
                                if val_metrics is None
                                else val_metrics["baseline_normalized_effective_mae_mean"],
                                "beats_default_baseline": None if val_metrics is None else val_metrics["beats_default_baseline"],
                                "hold_boundary_rate": None if val_metrics is None else val_metrics["hold_boundary_rate"],
                            }
                        )
                    )
    summary_df = pd.DataFrame(rows).sort_values(["search_rank", "fold_id", "regime_id", "side"]).reset_index(drop=True)
    expected_rows = len(candidates) * len(folds) * 6 * 2
    valid = bool(
        len(summary_df) == expected_rows
        and summary_df["metrics_present"].all()
        and summary_df["effective_all_finite"].all()
        and summary_df["contract_valid"].all()
        and (~summary_df["fallback_used"]).all()
        and summary_df[["normalized_effective_mae_mean", "baseline_normalized_effective_mae_mean", "hold_boundary_rate"]]
        .notna()
        .all()
        .all()
    )
    report = build_stage2_selection_report(summary_df, candidates)
    return summary_df, {
        "valid": valid,
        "report": report,
        "expected_rows": expected_rows,
    }


def build_stage2_selection_report(summary_df: pd.DataFrame, candidates: list[CandidateSpec]) -> dict[str, Any]:
    candidate_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_df = summary_df.loc[summary_df["candidate_id"] == candidate.candidate_id]
        candidate_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "search_rank": candidate.search_rank,
                "is_baseline": candidate.is_baseline,
                "params": candidate.params,
                "mean_normalized_effective_mae_mean": float(candidate_df["normalized_effective_mae_mean"].mean()),
                "beat_default_share": float(candidate_df["beats_default_baseline"].mean()),
                "max_hold_boundary_rate": float(candidate_df["hold_boundary_rate"].max()),
                "mean_hold_boundary_rate": float(candidate_df["hold_boundary_rate"].mean()),
                "eligible": bool(
                    candidate_df["effective_all_finite"].all()
                    and candidate_df["contract_valid"].all()
                    and (~candidate_df["fallback_used"]).all()
                    and float(candidate_df["hold_boundary_rate"].max()) <= 0.05
                ),
            }
        )

    eligible_rows = [row for row in candidate_rows if row["eligible"]]
    provisional_winner = None
    if eligible_rows:
        provisional_winner = min(
            eligible_rows,
            key=lambda row: (
                row["mean_normalized_effective_mae_mean"],
                -row["beat_default_share"],
                row["mean_hold_boundary_rate"],
                0 if row["is_baseline"] else 1,
                row["search_rank"],
            ),
        )

    baseline_row = next(row for row in candidate_rows if row["is_baseline"])
    return json_ready(
        {
            "primary_metric": STAGE2_PRIMARY_METRIC,
            "tie_breakers": [
                "higher_share_beating_default_baseline",
                "lower_mean_hold_boundary_rate",
                "baseline_preferred",
            ],
            "baseline_candidate_id": baseline_row["candidate_id"],
            "baseline_candidate_score": baseline_row["mean_normalized_effective_mae_mean"],
            "provisional_winner_candidate_id": None if provisional_winner is None else provisional_winner["candidate_id"],
            "provisional_winner_aggregate_score": None
            if provisional_winner is None
            else provisional_winner["mean_normalized_effective_mae_mean"],
            "eligibility_guardrails": {
                "all_finite": True,
                "contract_valid": True,
                "no_sparse_fallback": True,
                "max_hold_boundary_rate": 0.05,
            },
            "candidate_rows": candidate_rows,
        }
    )


def stage1_outer_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    df = pd.DataFrame(rows)
    guardrail_pass = bool(df["cand0_pass_recall"].min() >= 0.50 and df["prob_all_finite"].all() and df["prob_sum_close"].all())
    return json_ready(
        {
            "row_count": int(len(df)),
            "mean_macro_f1": float(df["macro_f1"].mean()),
            "mean_cand0_pass_recall": float(df["cand0_pass_recall"].mean()),
            "min_cand0_pass_recall": float(df["cand0_pass_recall"].min()),
            "mean_log_loss": float(df["log_loss"].mean()),
            "guardrail_pass": guardrail_pass,
            "rows": rows,
        }
    )


def evaluate_stage1_candidate_on_outer_holdout(
    *,
    bundle: Step11Bundle,
    outer_train_mask: np.ndarray,
    outer_val_mask: np.ndarray,
    X_all: np.ndarray,
    candidate: CandidateSpec,
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
) -> dict[str, Any]:
    candidate_config = build_stage1_config(base_training_config, candidate, output_dir, seed)
    regimes = bundle.labels["regime_id"].to_numpy(dtype=np.int64)
    rows: list[dict[str, Any]] = []
    for regime_id in range(6):
        regime_train_indices = np.flatnonzero(outer_train_mask & (regimes == regime_id))
        regime_val_indices = np.flatnonzero(outer_val_mask & (regimes == regime_id))
        result = train_stage1_regime_for_eval(
            regime_id=regime_id,
            labels=bundle.labels,
            X_all=X_all,
            regime_train_indices=regime_train_indices,
            regime_val_indices=regime_val_indices,
            config=candidate_config,
        )
        val_metrics = result["val_metrics"]
        rows.append(
            {
                "regime_id": regime_id,
                "prob_all_finite": bool(result["prob_all_finite"]),
                "prob_sum_close": bool(result["prob_sum_close"]),
                "macro_f1": float(val_metrics["macro_f1"]),
                "pass_precision": float(val_metrics["pass_precision"]),
                "pass_recall": float(val_metrics["pass_recall"]),
                "cand0_pass_recall": float(val_metrics["cand0_pass_recall"]),
                "log_loss": float(val_metrics["log_loss"]),
            }
        )
    return stage1_outer_summary(rows)


def stage2_outer_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    df = pd.DataFrame(rows)
    guardrail_pass = bool(
        df["effective_all_finite"].all()
        and df["contract_valid"].all()
        and (~df["fallback_used"]).all()
        and float(df["hold_boundary_rate"].max()) <= 0.05
    )
    return json_ready(
        {
            "row_count": int(len(df)),
            "mean_normalized_effective_mae_mean": float(df["normalized_effective_mae_mean"].mean()),
            "beat_default_share": float(df["beats_default_baseline"].mean()),
            "max_hold_boundary_rate": float(df["hold_boundary_rate"].max()),
            "mean_hold_boundary_rate": float(df["hold_boundary_rate"].mean()),
            "guardrail_pass": guardrail_pass,
            "rows": rows,
        }
    )


def evaluate_stage2_candidate_on_outer_holdout(
    *,
    stage2_frame: pd.DataFrame,
    X_all: np.ndarray,
    candidate: CandidateSpec,
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
    step11_dir: Path,
    step12_dir: Path,
) -> dict[str, Any]:
    candidate_config = build_stage2_config(
        base_training_config,
        candidate,
        step11_dir=step11_dir,
        step12_dir=step12_dir,
        output_dir=output_dir,
        seed=seed,
    )
    rows: list[dict[str, Any]] = []
    for regime_id in range(6):
        for side in ("LONG", "SHORT"):
            result = train_stage2_direction_for_eval(
                side=side,
                regime_id=regime_id,
                X_all=X_all,
                stage2_frame=stage2_frame,
                config=candidate_config,
            )
            val_metrics = result["val_metrics"]
            rows.append(
                {
                    "regime_id": regime_id,
                    "side": side,
                    "fallback_used": bool(result["fallback_used"]),
                    "effective_all_finite": bool(result["effective_all_finite"]),
                    "contract_valid": bool(result["contract_valid"]),
                    "normalized_effective_mae_mean": float(val_metrics["normalized_effective_mae_mean"]),
                    "baseline_normalized_effective_mae_mean": float(val_metrics["baseline_normalized_effective_mae_mean"]),
                    "beats_default_baseline": bool(val_metrics["beats_default_baseline"]),
                    "hold_boundary_rate": float(val_metrics["hold_boundary_rate"]),
                }
            )
    return stage2_outer_summary(rows)


def select_final_stage1_candidate(selection_report: dict[str, Any], final_holdout: dict[str, Any]) -> dict[str, Any]:
    baseline_id = str(selection_report["baseline_candidate_id"])
    provisional_id = selection_report["provisional_winner_candidate_id"]
    baseline_summary = final_holdout["baseline"]
    provisional_summary = final_holdout["provisional"]
    provisional_beats = bool(
        provisional_id is not None
        and provisional_summary["guardrail_pass"]
        and provisional_summary["mean_macro_f1"] > baseline_summary["mean_macro_f1"]
    )
    final_candidate_id = provisional_id if provisional_beats else baseline_id
    return {
        "baseline_candidate_id": baseline_id,
        "provisional_winner_candidate_id": provisional_id,
        "final_handoff_candidate_id": final_candidate_id,
        "final_handoff_is_baseline": final_candidate_id == baseline_id,
        "provisional_strictly_beats_baseline": provisional_beats,
        "arbitration_result": "provisional_winner" if provisional_beats else "baseline_fallback",
    }


def select_final_stage2_candidate(selection_report: dict[str, Any], final_holdout: dict[str, Any]) -> dict[str, Any]:
    baseline_id = str(selection_report["baseline_candidate_id"])
    provisional_id = selection_report["provisional_winner_candidate_id"]
    baseline_summary = final_holdout["baseline"]
    provisional_summary = final_holdout["provisional"]
    provisional_beats = bool(
        provisional_id is not None
        and provisional_summary["guardrail_pass"]
        and provisional_summary["mean_normalized_effective_mae_mean"] < baseline_summary["mean_normalized_effective_mae_mean"]
    )
    final_candidate_id = provisional_id if provisional_beats else baseline_id
    return {
        "baseline_candidate_id": baseline_id,
        "provisional_winner_candidate_id": provisional_id,
        "final_handoff_candidate_id": final_candidate_id,
        "final_handoff_is_baseline": final_candidate_id == baseline_id,
        "provisional_strictly_beats_baseline": provisional_beats,
        "arbitration_result": "provisional_winner" if provisional_beats else "baseline_fallback",
    }


def build_outer_holdout_report(
    *,
    stage1_selection_report: dict[str, Any],
    stage2_selection_report: dict[str, Any],
    stage1_baseline_summary: dict[str, Any],
    stage1_provisional_summary: dict[str, Any],
    stage2_baseline_summary: dict[str, Any],
    stage2_provisional_summary: dict[str, Any],
) -> dict[str, Any]:
    stage1 = {
        "baseline": stage1_baseline_summary,
        "provisional": stage1_provisional_summary,
    }
    stage1.update(select_final_stage1_candidate(stage1_selection_report, stage1))
    stage2 = {
        "baseline": stage2_baseline_summary,
        "provisional": stage2_provisional_summary,
    }
    stage2.update(select_final_stage2_candidate(stage2_selection_report, stage2))
    return json_ready({"stage1": stage1, "stage2": stage2})


def candidate_lookup(candidates: list[CandidateSpec]) -> dict[str, CandidateSpec]:
    return {candidate.candidate_id: candidate for candidate in candidates}


def write_selected_stage1_artifacts(
    *,
    bundle: Step11Bundle,
    step12_context: Step12Context,
    outer_train_mask: np.ndarray,
    outer_val_mask: np.ndarray,
    selected_candidate: CandidateSpec,
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outer_plan = split_plan_from_summary(step12_context.split_plan)
    selected_config = build_stage1_config(base_training_config, selected_candidate, output_dir, seed)
    selected_config = Step12Config(
        **{
            **selected_config.__dict__,
            "output_dir": output_dir,
            "model_name": f"step14_{selected_candidate.candidate_id}",
        }
    )
    scaler, train_bar_mask = compute_scaler(bundle.features, bundle.labels, outer_train_mask)
    X_all = build_scaled_windows(bundle.features, bundle.labels, scaler)
    regimes = bundle.labels["regime_id"].to_numpy(dtype=np.int64)
    results = []
    for regime_id in range(6):
        result = train_regime_classifier(
            regime_id=regime_id,
            X_all=X_all,
            labels=bundle.labels,
            regime_train_indices=np.flatnonzero(outer_train_mask & (regimes == regime_id)),
            regime_val_indices=np.flatnonzero(outer_val_mask & (regimes == regime_id)),
            config=selected_config,
            output_dir=output_dir,
        )
        results.append(result)

    training_metadata = build_step12_training_metadata(bundle, selected_config, outer_plan, scaler, train_bar_mask, results)
    training_metadata["implementation_status"] = "step14_selected_stage1_refit"
    training_metadata["selected_from_step14_candidate_id"] = selected_candidate.candidate_id
    training_metadata["step14_selection"] = {
        "stage": "stage1",
        "candidate_id": selected_candidate.candidate_id,
        "candidate_params": selected_candidate.params,
    }
    training_metadata["clf_version"] = f"step14_{selected_candidate.candidate_id}"
    write_json(output_dir / "training_metadata.json", training_metadata)
    write_json(output_dir / "split_plan.json", outer_plan.summary())
    write_json(output_dir / "scaler_stats.json", scaler.as_json())

    summary_rows = []
    for result in results:
        row = result.summary_row()
        row["train_macro_f1"] = result.train_metrics["macro_f1"] if result.train_metrics else None
        row["val_macro_f1"] = result.val_metrics["macro_f1"] if result.val_metrics else None
        row["val_cand0_pass_recall"] = result.val_metrics["cand0_pass_recall"] if result.val_metrics else None
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(output_dir / "regime_summary.csv", index=False)
    return {"training_metadata": training_metadata, "scaler": scaler, "X_all": X_all}


def write_selected_stage2_artifacts(
    *,
    bundle: Step11Bundle,
    selected_stage1_dir: Path,
    outer_train_mask: np.ndarray,
    outer_val_mask: np.ndarray,
    selected_candidate: CandidateSpec,
    base_training_config: dict[str, Any],
    output_dir: Path,
    seed: int,
    step11_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_step12_context = load_step12_context(selected_stage1_dir)
    split_audit_train_mask, split_audit_val_mask, _dropped_mask, split_audit = rebuild_masks_from_split_plan(
        bundle.labels, selected_step12_context.split_plan
    )
    if not np.array_equal(split_audit_train_mask, outer_train_mask) or not np.array_equal(split_audit_val_mask, outer_val_mask):
        raise ValueError("selected_stage1 split lineage does not match STEP14 outer holdout")

    stage2_config = build_stage2_config(
        base_training_config,
        selected_candidate,
        step11_dir=step11_dir,
        step12_dir=selected_stage1_dir,
        output_dir=output_dir,
        seed=seed,
    )
    stage2_config = Step13Config(
        **{
            **stage2_config.__dict__,
            "step12_dir": selected_stage1_dir,
            "output_dir": output_dir,
            "model_name": f"step14_{selected_candidate.candidate_id}",
        }
    )

    X_all = build_scaled_windows(bundle.features, bundle.labels, selected_step12_context.scaler)
    stage2_frame, stage2_audit = build_stage2_frame(bundle.labels, outer_train_mask, outer_val_mask)
    results = []
    for regime_id in range(6):
        result = train_regime_bundle(regime_id, X_all, stage2_frame, stage2_config, output_dir)
        results.append(result)

    acceptance = build_step13_acceptance(selected_step12_context, split_audit, stage2_audit, stage2_frame, results, X_all)
    training_metadata = build_step13_training_metadata(
        bundle,
        selected_step12_context,
        stage2_config,
        split_audit,
        stage2_audit,
        results,
        acceptance,
    )
    training_metadata["implementation_status"] = "step14_selected_stage2_refit"
    training_metadata["selected_from_step14_candidate_id"] = selected_candidate.candidate_id
    training_metadata["step14_selection"] = {
        "stage": "stage2",
        "candidate_id": selected_candidate.candidate_id,
        "candidate_params": selected_candidate.params,
    }
    training_metadata["prm_version"] = f"step14_{selected_candidate.candidate_id}"
    write_json(output_dir / "training_metadata.json", training_metadata)
    write_json(output_dir / "split_plan.json", selected_step12_context.split_plan)
    write_json(output_dir / "scaler_stats.json", selected_step12_context.scaler_stats)
    pd.DataFrame([result.summary_row() for result in results]).to_csv(output_dir / "regime_summary.csv", index=False)
    return {"training_metadata": training_metadata, "stage2_frame": stage2_frame, "X_all": X_all}


def run_stage1_smoke(selected_dir: Path, labels: pd.DataFrame, val_mask: np.ndarray, X_all: np.ndarray) -> dict[str, Any]:
    smoke: dict[str, Any] = {}
    overall = True
    regimes = labels["regime_id"].to_numpy(dtype=np.int64)
    for regime_id in range(6):
        bundle_path = selected_dir / f"regime_{regime_id}" / f"clf_reg{regime_id}.joblib"
        bundle = joblib.load(bundle_path)
        row_indices = np.flatnonzero(val_mask & (regimes == regime_id))[:4]
        if len(row_indices) == 0:
            regime_smoke = {"tested": False, "row_count": 0}
        else:
            probabilities = np.asarray(bundle["model"].predict_proba(X_all[row_indices]), dtype=np.float64)
            regime_smoke = {
                "tested": True,
                "row_count": int(len(row_indices)),
                "shape_ok": bool(probabilities.shape == (len(row_indices), 3)),
                "prob_all_finite": bool(np.isfinite(probabilities).all()),
                "prob_sum_close": bool(np.allclose(probabilities.sum(axis=1), 1.0, atol=STAGE1_PROB_TOLERANCE)),
            }
            overall = overall and regime_smoke["shape_ok"] and regime_smoke["prob_all_finite"] and regime_smoke["prob_sum_close"]
        smoke[str(regime_id)] = regime_smoke
    smoke["all_passed"] = overall
    return json_ready(smoke)


def run_stage2_smoke(selected_dir: Path, stage2_frame: pd.DataFrame, X_all: np.ndarray) -> dict[str, Any]:
    smoke: dict[str, Any] = {}
    overall = True
    for regime_id in range(6):
        bundle_path = selected_dir / f"regime_{regime_id}" / f"prm_reg{regime_id}.joblib"
        regime_frame = stage2_frame.loc[stage2_frame["regime_id"] == regime_id]
        regime_smoke = run_bundle_smoke(str(bundle_path), regime_frame, X_all)
        smoke[str(regime_id)] = regime_smoke
        if regime_smoke.get("tested"):
            overall = (
                overall
                and regime_smoke["shape_ok"]
                and regime_smoke["raw_all_finite"]
                and regime_smoke["effective_all_finite"]
                and regime_smoke["contract_valid"]
                and regime_smoke["holds_integral"]
            )
    smoke["all_passed"] = overall
    return json_ready(smoke)


def build_handoff_manifest(
    *,
    bundle: Step11Bundle,
    outer_split_plan: dict[str, Any],
    final_holdout_report: dict[str, Any],
    selected_stage1_candidate: CandidateSpec,
    selected_stage2_candidate: CandidateSpec,
    selected_stage1_metadata: dict[str, Any],
    selected_stage2_metadata: dict[str, Any],
) -> dict[str, Any]:
    model_pack_version = str(bundle.metadata["model_pack_version"])
    return json_ready(
        {
            "schema_version": bundle.metadata["schema_version"],
            "candidate_policy_version": bundle.metadata["candidate_policy_version"],
            "regime_policy_version": bundle.metadata["regime_policy_version"],
            "cost_model_version": bundle.metadata["cost_model_version"],
            "search_space_version": bundle.metadata["search_space_version"],
            "atr_thr": bundle.metadata["atr_thr"],
            "adx_thr1": bundle.metadata["adx_thr1"],
            "adx_thr2": bundle.metadata["adx_thr2"],
            "step14_outer_split": outer_split_plan,
            "stage1": {
                "selected_candidate_id": selected_stage1_candidate.candidate_id,
                "selected_candidate_params": selected_stage1_candidate.params,
                "final_handoff_candidate_id": final_holdout_report["stage1"]["final_handoff_candidate_id"],
                "final_handoff_is_baseline": final_holdout_report["stage1"]["final_handoff_is_baseline"],
                "clf_version": selected_stage1_metadata["clf_version"],
                "expected_future_pack_filenames": [
                    f"clf_reg{regime_id}_v{model_pack_version}.onnx" for regime_id in range(6)
                ],
            },
            "stage2": {
                "selected_candidate_id": selected_stage2_candidate.candidate_id,
                "selected_candidate_params": selected_stage2_candidate.params,
                "final_handoff_candidate_id": final_holdout_report["stage2"]["final_handoff_candidate_id"],
                "final_handoff_is_baseline": final_holdout_report["stage2"]["final_handoff_is_baseline"],
                "prm_version": selected_stage2_metadata["prm_version"],
                "expected_future_pack_filenames": [
                    f"prm_reg{regime_id}_v{model_pack_version}.onnx" for regime_id in range(6)
                ],
            },
        }
    )


def compare_json_exact(path_a: Path, path_b: Path) -> bool:
    return load_json(path_a) == load_json(path_b)


def compare_csv_exact(path_a: Path, path_b: Path) -> bool:
    return pd.read_csv(path_a).equals(pd.read_csv(path_b))


def compare_float(a: float, b: float, tolerance: float) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def run_repro_check(output_dir: Path, repro_dir: Path, base_runtime: dict[str, Any], tolerance: float) -> dict[str, Any]:
    repro_stage1_selection = load_json(repro_dir / "stage1_selection_report.json")
    repro_stage2_selection = load_json(repro_dir / "stage2_selection_report.json")
    repro_holdout = load_json(repro_dir / "final_holdout_report.json")
    comparisons = {
        "outer_split_plan_match": compare_json_exact(output_dir / "outer_split_plan.json", repro_dir / "outer_split_plan.json"),
        "inner_split_manifest_match": compare_json_exact(
            output_dir / "inner_split_manifest.json", repro_dir / "inner_split_manifest.json"
        ),
        "stage1_candidate_registry_match": compare_csv_exact(
            output_dir / "stage1_candidate_registry.csv", repro_dir / "stage1_candidate_registry.csv"
        ),
        "stage2_candidate_registry_match": compare_csv_exact(
            output_dir / "stage2_candidate_registry.csv", repro_dir / "stage2_candidate_registry.csv"
        ),
        "stage1_provisional_winner_match": base_runtime["stage1_selection_report"]["provisional_winner_candidate_id"]
        == repro_stage1_selection["provisional_winner_candidate_id"],
        "stage2_provisional_winner_match": base_runtime["stage2_selection_report"]["provisional_winner_candidate_id"]
        == repro_stage2_selection["provisional_winner_candidate_id"],
        "stage1_final_handoff_match": base_runtime["final_holdout_report"]["stage1"]["final_handoff_candidate_id"]
        == repro_holdout["stage1"]["final_handoff_candidate_id"],
        "stage2_final_handoff_match": base_runtime["final_holdout_report"]["stage2"]["final_handoff_candidate_id"]
        == repro_holdout["stage2"]["final_handoff_candidate_id"],
        "stage1_primary_metric_close": compare_float(
            base_runtime["stage1_selection_report"]["baseline_candidate_score"],
            repro_stage1_selection["baseline_candidate_score"],
            tolerance,
        ),
        "stage2_primary_metric_close": compare_float(
            base_runtime["stage2_selection_report"]["baseline_candidate_score"],
            repro_stage2_selection["baseline_candidate_score"],
            tolerance,
        ),
        "stage1_outer_holdout_metric_close": compare_float(
            base_runtime["final_holdout_report"]["stage1"]["baseline"]["mean_macro_f1"],
            repro_holdout["stage1"]["baseline"]["mean_macro_f1"],
            tolerance,
        ),
        "stage2_outer_holdout_metric_close": compare_float(
            base_runtime["final_holdout_report"]["stage2"]["baseline"]["mean_normalized_effective_mae_mean"],
            repro_holdout["stage2"]["baseline"]["mean_normalized_effective_mae_mean"],
            tolerance,
        ),
    }
    return json_ready({"passed": all(comparisons.values()), "comparisons": comparisons, "tolerance": tolerance})


def build_validation_metadata(
    *,
    config: Step14Config,
    lineage_audit: dict[str, Any],
    outer_split_audit: dict[str, Any],
    inner_manifest: dict[str, Any],
    stage1_registry_df: pd.DataFrame,
    stage2_registry_df: pd.DataFrame,
    stage1_cv_summary: pd.DataFrame,
    stage2_cv_summary: pd.DataFrame,
    stage1_selection_report: dict[str, Any],
    stage2_selection_report: dict[str, Any],
    selected_stage1_smoke: dict[str, Any],
    selected_stage2_smoke: dict[str, Any],
    final_holdout_report: dict[str, Any],
    handoff_manifest: dict[str, Any],
    repro_report: dict[str, Any] | None,
) -> dict[str, Any]:
    stage1_candidate_count = len(stage1_registry_df)
    stage2_candidate_count = len(stage2_registry_df)
    acceptance = {
        "A1_lineage_audit_pass": bool(lineage_audit["passed"]),
        "A2_outer_holdout_matches_step12": bool(
            outer_split_audit["no_time_leakage"] and int(outer_split_audit["embargo_bars"]) == config.embargo_bars
        ),
        "A3_inner_split_manifest_valid": bool(
            inner_manifest["fold_count"] == len(config.inner_fold_train_ratios)
            and all(not fold["relaxed_min_requirement"] for fold in inner_manifest["folds"])
            and all(fold["embargo_bars"] == config.embargo_bars for fold in inner_manifest["folds"])
            and all(fold["no_time_leakage"] for fold in inner_manifest["folds"])
        ),
        "A4_candidate_registries_complete": bool(
            stage1_candidate_count >= 1
            and stage2_candidate_count >= 1
            and bool(stage1_registry_df["is_baseline"].sum() == 1)
            and bool(stage2_registry_df["is_baseline"].sum() == 1)
            and stage1_registry_df["candidate_id"].is_unique
            and stage2_registry_df["candidate_id"].is_unique
        ),
        "A5_stage1_cv_complete_and_valid": bool(
            len(stage1_cv_summary) == stage1_candidate_count * len(config.inner_fold_train_ratios) * 6
            and stage1_cv_summary["metrics_present"].all()
            and stage1_cv_summary["prob_all_finite"].all()
            and stage1_cv_summary["prob_sum_close"].all()
            and stage1_selection_report["provisional_winner_candidate_id"] is not None
        ),
        "A6_stage2_cv_complete_and_valid": bool(
            len(stage2_cv_summary) == stage2_candidate_count * len(config.inner_fold_train_ratios) * 6 * 2
            and stage2_cv_summary["metrics_present"].all()
            and stage2_cv_summary["effective_all_finite"].all()
            and stage2_cv_summary["contract_valid"].all()
            and (~stage2_cv_summary["fallback_used"]).all()
            and stage2_selection_report["provisional_winner_candidate_id"] is not None
        ),
        "A7_selected_final_artifacts_exist_and_smoke_pass": bool(
            selected_stage1_smoke.get("all_passed", False) and selected_stage2_smoke.get("all_passed", False)
        ),
        "A8_outer_holdout_handoff_decision_valid": bool(
            handoff_manifest["stage1"]["final_handoff_candidate_id"] == final_holdout_report["stage1"]["final_handoff_candidate_id"]
            and handoff_manifest["stage2"]["final_handoff_candidate_id"] == final_holdout_report["stage2"]["final_handoff_candidate_id"]
        ),
        "A9_reproducibility_pass": True if repro_report is None else bool(repro_report["passed"]),
    }
    return json_ready(
        {
            "implementation_status": "step14_validation_selection_implemented",
            "step11_dir": str(config.step11_dir),
            "step12_dir": str(config.step12_dir),
            "step13_dir": str(config.step13_dir),
            "output_dir": str(config.output_dir),
            "inner_fold_train_ratios": list(config.inner_fold_train_ratios),
            "embargo_bars": int(config.embargo_bars),
            "repro_tolerance": float(config.repro_tolerance),
            "lineage_audit": lineage_audit,
            "outer_split_audit": outer_split_audit,
            "inner_manifest": inner_manifest,
            "stage1_selection": stage1_selection_report,
            "stage2_selection": stage2_selection_report,
            "final_holdout": final_holdout_report,
            "handoff_manifest": handoff_manifest,
            "acceptance": acceptance,
        }
    )


def run_pipeline(config: Step14Config) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    bundle, step12_context, step13_metadata = load_context(config)

    lineage_audit = audit_lineage(config, bundle, step12_context, step13_metadata)
    write_json(config.output_dir / "lineage_audit.json", lineage_audit)

    outer_train_mask, outer_val_mask, _outer_dropped_mask, outer_split_audit = build_outer_split_audit(bundle.labels, step12_context)
    write_json(config.output_dir / "outer_split_plan.json", step12_context.split_plan)
    write_json(config.output_dir / "outer_split_audit.json", outer_split_audit)

    folds = choose_inner_splits(bundle=bundle, outer_train_mask=outer_train_mask, config=config)
    inner_manifest = build_inner_split_manifest(folds)
    write_json(config.output_dir / "inner_split_manifest.json", inner_manifest)
    inner_scaler_dir = config.output_dir / "inner_scaler_stats"
    inner_scaler_dir.mkdir(parents=True, exist_ok=True)
    for fold in folds:
        fold_scaler_payload = fold.scaler.as_json()
        fold_scaler_payload["bar_count"] = fold.scaler.bar_count
        fold_scaler_payload["replaced_std_indices"] = fold.scaler.replaced_std_indices
        write_json(inner_scaler_dir / f"fold_{fold.plan.fold_id}.json", fold_scaler_payload)

    stage1_candidates = build_stage1_candidate_registry(config)
    stage2_candidates = build_stage2_candidate_registry(config)
    stage1_registry_df = candidate_registry_df(stage1_candidates, seed=config.seed)
    stage2_registry_df = candidate_registry_df(stage2_candidates, seed=config.seed)
    stage1_registry_df.to_csv(config.output_dir / "stage1_candidate_registry.csv", index=False)
    stage2_registry_df.to_csv(config.output_dir / "stage2_candidate_registry.csv", index=False)

    step12_base_training_config = {**step12_context.training_metadata["training_config"]}
    step12_base_training_config["hidden_layers"] = step12_context.training_metadata["architecture_baseline"]["hidden_layers"]
    step13_base_training_config = step13_metadata["training_config"]

    stage1_cv_summary, stage1_cv = run_stage1_cv(
        bundle=bundle,
        folds=folds,
        candidates=stage1_candidates,
        base_training_config=step12_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
    )
    stage1_cv_summary.to_csv(config.output_dir / "stage1_cv_summary.csv", index=False)
    stage1_selection_report = stage1_cv["report"]
    write_json(config.output_dir / "stage1_selection_report.json", stage1_selection_report)

    stage2_cv_summary, stage2_cv = run_stage2_cv(
        folds=folds,
        candidates=stage2_candidates,
        base_training_config=step13_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
        step11_dir=config.step11_dir,
        step12_dir=config.step12_dir,
    )
    stage2_cv_summary.to_csv(config.output_dir / "stage2_cv_summary.csv", index=False)
    stage2_selection_report = stage2_cv["report"]
    write_json(config.output_dir / "stage2_selection_report.json", stage2_selection_report)

    candidate_by_id_stage1 = candidate_lookup(stage1_candidates)
    candidate_by_id_stage2 = candidate_lookup(stage2_candidates)
    stage1_baseline_candidate = candidate_by_id_stage1[stage1_selection_report["baseline_candidate_id"]]
    stage1_provisional_candidate = stage1_baseline_candidate
    if stage1_selection_report["provisional_winner_candidate_id"] is not None:
        stage1_provisional_candidate = candidate_by_id_stage1[stage1_selection_report["provisional_winner_candidate_id"]]

    stage2_baseline_candidate = candidate_by_id_stage2[stage2_selection_report["baseline_candidate_id"]]
    stage2_provisional_candidate = stage2_baseline_candidate
    if stage2_selection_report["provisional_winner_candidate_id"] is not None:
        stage2_provisional_candidate = candidate_by_id_stage2[stage2_selection_report["provisional_winner_candidate_id"]]

    outer_scaler, _outer_train_bar_mask = compute_scaler(bundle.features, bundle.labels, outer_train_mask)
    outer_X_all = build_scaled_windows(bundle.features, bundle.labels, outer_scaler)
    outer_stage2_frame, _outer_stage2_audit = build_stage2_frame(bundle.labels, outer_train_mask, outer_val_mask)

    stage1_baseline_outer = evaluate_stage1_candidate_on_outer_holdout(
        bundle=bundle,
        outer_train_mask=outer_train_mask,
        outer_val_mask=outer_val_mask,
        X_all=outer_X_all,
        candidate=stage1_baseline_candidate,
        base_training_config=step12_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
    )
    stage1_provisional_outer = evaluate_stage1_candidate_on_outer_holdout(
        bundle=bundle,
        outer_train_mask=outer_train_mask,
        outer_val_mask=outer_val_mask,
        X_all=outer_X_all,
        candidate=stage1_provisional_candidate,
        base_training_config=step12_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
    )
    stage2_baseline_outer = evaluate_stage2_candidate_on_outer_holdout(
        stage2_frame=outer_stage2_frame,
        X_all=outer_X_all,
        candidate=stage2_baseline_candidate,
        base_training_config=step13_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
        step11_dir=config.step11_dir,
        step12_dir=config.step12_dir,
    )
    stage2_provisional_outer = evaluate_stage2_candidate_on_outer_holdout(
        stage2_frame=outer_stage2_frame,
        X_all=outer_X_all,
        candidate=stage2_provisional_candidate,
        base_training_config=step13_base_training_config,
        output_dir=config.output_dir,
        seed=config.seed,
        step11_dir=config.step11_dir,
        step12_dir=config.step12_dir,
    )

    final_holdout_report = build_outer_holdout_report(
        stage1_selection_report=stage1_selection_report,
        stage2_selection_report=stage2_selection_report,
        stage1_baseline_summary=stage1_baseline_outer,
        stage1_provisional_summary=stage1_provisional_outer,
        stage2_baseline_summary=stage2_baseline_outer,
        stage2_provisional_summary=stage2_provisional_outer,
    )
    write_json(config.output_dir / "final_holdout_report.json", final_holdout_report)

    final_stage1_candidate = candidate_by_id_stage1[final_holdout_report["stage1"]["final_handoff_candidate_id"]]
    final_stage2_candidate = candidate_by_id_stage2[final_holdout_report["stage2"]["final_handoff_candidate_id"]]

    selected_stage1_dir = config.output_dir / "selected_stage1"
    selected_stage1 = write_selected_stage1_artifacts(
        bundle=bundle,
        step12_context=step12_context,
        outer_train_mask=outer_train_mask,
        outer_val_mask=outer_val_mask,
        selected_candidate=final_stage1_candidate,
        base_training_config=step12_base_training_config,
        output_dir=selected_stage1_dir,
        seed=config.seed,
    )
    selected_stage1_smoke = run_stage1_smoke(selected_stage1_dir, bundle.labels, outer_val_mask, selected_stage1["X_all"])
    write_json(config.output_dir / "selected_stage1_smoke.json", selected_stage1_smoke)

    selected_stage2_dir = config.output_dir / "selected_stage2"
    selected_stage2 = write_selected_stage2_artifacts(
        bundle=bundle,
        selected_stage1_dir=selected_stage1_dir,
        outer_train_mask=outer_train_mask,
        outer_val_mask=outer_val_mask,
        selected_candidate=final_stage2_candidate,
        base_training_config=step13_base_training_config,
        output_dir=selected_stage2_dir,
        seed=config.seed,
        step11_dir=config.step11_dir,
    )
    selected_stage2_smoke = run_stage2_smoke(selected_stage2_dir, selected_stage2["stage2_frame"], selected_stage2["X_all"])
    write_json(config.output_dir / "selected_stage2_smoke.json", selected_stage2_smoke)

    handoff_manifest = build_handoff_manifest(
        bundle=bundle,
        outer_split_plan=step12_context.split_plan,
        final_holdout_report=final_holdout_report,
        selected_stage1_candidate=final_stage1_candidate,
        selected_stage2_candidate=final_stage2_candidate,
        selected_stage1_metadata=selected_stage1["training_metadata"],
        selected_stage2_metadata=selected_stage2["training_metadata"],
    )
    write_json(config.output_dir / "handoff_manifest.json", handoff_manifest)

    repro_report = None
    if config.run_repro_check:
        repro_dir = config.output_dir / "_repro"
        repro_config = Step14Config(
            **{
                **config.__dict__,
                "output_dir": repro_dir,
                "run_repro_check": False,
                "fail_on_acceptance": False,
            }
        )
        run_pipeline(repro_config)
        repro_report = run_repro_check(
            config.output_dir,
            repro_dir,
            {
                "stage1_selection_report": stage1_selection_report,
                "stage2_selection_report": stage2_selection_report,
                "final_holdout_report": final_holdout_report,
            },
            config.repro_tolerance,
        )
        write_json(config.output_dir / "reproducibility_report.json", repro_report)
    else:
        repro_report = {"passed": True, "skipped": True}
        write_json(config.output_dir / "reproducibility_report.json", repro_report)

    validation_metadata = build_validation_metadata(
        config=config,
        lineage_audit=lineage_audit,
        outer_split_audit=outer_split_audit,
        inner_manifest=inner_manifest,
        stage1_registry_df=stage1_registry_df,
        stage2_registry_df=stage2_registry_df,
        stage1_cv_summary=stage1_cv_summary,
        stage2_cv_summary=stage2_cv_summary,
        stage1_selection_report=stage1_selection_report,
        stage2_selection_report=stage2_selection_report,
        selected_stage1_smoke=selected_stage1_smoke,
        selected_stage2_smoke=selected_stage2_smoke,
        final_holdout_report=final_holdout_report,
        handoff_manifest=handoff_manifest,
        repro_report=repro_report,
    )
    write_json(config.output_dir / "validation_metadata.json", validation_metadata)
    return {
        "validation_metadata": validation_metadata,
        "stage1_selection_report": stage1_selection_report,
        "stage2_selection_report": stage2_selection_report,
        "final_holdout_report": final_holdout_report,
    }


def main() -> int:
    config = parse_args()
    runtime = run_pipeline(config)
    acceptance = runtime["validation_metadata"]["acceptance"]
    print(f"[STEP14] validation_metadata={config.output_dir / 'validation_metadata.json'}")
    print(f"[STEP14] stage1_final={runtime['final_holdout_report']['stage1']['final_handoff_candidate_id']}")
    print(f"[STEP14] stage2_final={runtime['final_holdout_report']['stage2']['final_handoff_candidate_id']}")
    print(f"[STEP14] acceptance={json.dumps(acceptance, ensure_ascii=False)}")

    if config.fail_on_acceptance and not all(bool(value) for value in acceptance.values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
