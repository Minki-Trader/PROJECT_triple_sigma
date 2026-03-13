"""
build_step11_fold_union.py - Merge multiple STEP11 bundles into one union corpus.

Usage:
    python tools/build_step11_fold_union.py --output-dir <dir> <step11_dir> [<step11_dir> ...]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


COMPATIBILITY_KEYS = (
    "schema_version",
    "model_pack_version",
    "candidate_policy_version",
    "regime_policy_version",
    "cost_model_version",
    "search_space_version",
    "tie_policy",
    "symbol",
    "timeframe",
    "price_basis",
    "point_size",
    "slip_points",
    "slip_price",
    "R_pass_buffer",
    "H",
    "warmup_bars",
    "atr_thr",
    "adx_thr1",
    "adx_thr2",
    "thr_method",
    "thr_seed",
    "thr_notes",
    "dist_atr_max_mode",
    "dist_atr_max_q",
    "dist_atr_max_w",
    "dist_atr_max_clamp_lo",
    "dist_atr_max_clamp_hi",
)

VALIDATION_COUNT_KEYS = (
    "rows_validated",
    "rows_validated_dist_atr_max",
    "gap_first_ready_rows_excluded",
)

FLOAT_COMPATIBILITY_KEYS = {
    "point_size": 1e-9,
    "slip_price": 1e-9,
}


def _determine_project_root(path: Path) -> Path:
    root = path.resolve()
    while root.name != "PROJECT_triple_sigma" and root.parent != root:
        root = root.parent
    return root


def _ensure_ml_imports(project_root: Path) -> None:
    ml_root = project_root / "src" / "ml"
    if str(ml_root) not in sys.path:
        sys.path.insert(0, str(ml_root))


def _load_step11_bundle(step11_dir: Path):
    project_root = _determine_project_root(step11_dir)
    _ensure_ml_imports(project_root)
    from triplesigma_ml.step12 import load_step11_bundle

    return load_step11_bundle(step11_dir)


def _metadata_signature(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: metadata.get(key) for key in COMPATIBILITY_KEYS}


def _assert_compatible(base_dir: Path, base_metadata: dict[str, Any], other_dir: Path, other_metadata: dict[str, Any]) -> None:
    base_signature = _metadata_signature(base_metadata)
    other_signature = _metadata_signature(other_metadata)
    mismatches = []
    for key in COMPATIBILITY_KEYS:
        base_value = base_signature.get(key)
        other_value = other_signature.get(key)
        if key in FLOAT_COMPATIBILITY_KEYS:
            tolerance = FLOAT_COMPATIBILITY_KEYS[key]
            if base_value is None or other_value is None:
                if base_value != other_value:
                    mismatches.append(f"{key}: {base_value!r} != {other_value!r}")
            elif not math.isclose(float(base_value), float(other_value), rel_tol=0.0, abs_tol=tolerance):
                mismatches.append(f"{key}: {base_value!r} != {other_value!r}")
        elif base_value != other_value:
            mismatches.append(f"{key}: {base_value!r} != {other_value!r}")
    if mismatches:
        mismatch_text = "; ".join(mismatches)
        raise ValueError(
            f"STEP11 metadata compatibility mismatch between {base_dir} and {other_dir}: {mismatch_text}"
        )


def _combine_counter_dicts(metadatas: list[dict[str, Any]], field: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    for metadata in metadatas:
        payload = metadata.get(field) or {}
        for key, value in payload.items():
            totals[str(key)] = totals.get(str(key), 0) + int(value)
    return totals


def _combine_validation(metadatas: list[dict[str, Any]]) -> dict[str, Any]:
    validations = [metadata.get("validation") or {} for metadata in metadatas]
    combined: dict[str, Any] = {}
    for key in VALIDATION_COUNT_KEYS:
        combined[key] = sum(int(validation.get(key, 0)) for validation in validations)

    mismatch_totals: dict[str, int] = {}
    max_abs_diff: dict[str, float] = {}
    for validation in validations:
        for key, value in (validation.get("mismatch_count") or {}).items():
            mismatch_totals[str(key)] = mismatch_totals.get(str(key), 0) + int(value)
        for key, value in (validation.get("max_abs_diff") or {}).items():
            key = str(key)
            value = float(value)
            if key not in max_abs_diff or value > max_abs_diff[key]:
                max_abs_diff[key] = value

    combined["mismatch_count"] = mismatch_totals
    combined["max_abs_diff"] = max_abs_diff
    return combined


def _range_info(features: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    return {
        "feature_rows": int(len(features)),
        "label_rows": int(len(labels)),
        "feature_start": str(features["bar_time"].iloc[0]),
        "feature_end": str(features["bar_time"].iloc[-1]),
        "label_start": str(labels["bar_time"].iloc[0]),
        "label_end": str(labels["bar_time"].iloc[-1]),
    }


def build_union(output_dir: Path, step11_dirs: list[Path]) -> dict[str, Any]:
    if len(step11_dirs) < 2:
        raise ValueError("build_step11_fold_union requires at least two STEP11 directories")

    loaded = []
    for step11_dir in step11_dirs:
        bundle = _load_step11_bundle(step11_dir)
        features = bundle.features.reset_index(drop=True)
        labels = bundle.labels.reset_index(drop=True)
        loaded.append(
            {
                "dir": step11_dir,
                "features": features,
                "labels": labels,
                "metadata": bundle.metadata,
                "sort_key": pd.Timestamp(features["bar_time"].iloc[0]),
            }
        )

    loaded.sort(key=lambda item: item["sort_key"])
    base = loaded[0]
    for item in loaded[1:]:
        _assert_compatible(base["dir"], base["metadata"], item["dir"], item["metadata"])

    for prev, current in zip(loaded, loaded[1:]):
        prev_end = pd.Timestamp(prev["features"]["bar_time"].iloc[-1])
        current_start = pd.Timestamp(current["features"]["bar_time"].iloc[0])
        if current_start <= prev_end:
            raise ValueError(
                f"STEP11 folds overlap or are unsorted: {prev['dir']} ends at {prev_end}, "
                f"{current['dir']} starts at {current_start}"
            )

    union_features = []
    union_labels = []
    source_ranges = []
    feature_offset = 0
    sample_offset = 0

    for item in loaded:
        features = item["features"].copy()
        labels = item["labels"].copy()
        labels["window_start_idx"] = labels["window_start_idx"].astype("int64") + feature_offset
        labels["window_end_idx"] = labels["window_end_idx"].astype("int64") + feature_offset
        labels["sample_index"] = range(sample_offset, sample_offset + len(labels))

        union_features.append(features)
        union_labels.append(labels)
        source_ranges.append(
            {
                "step11_dir": str(item["dir"]),
                **_range_info(features, labels),
            }
        )
        feature_offset += len(features)
        sample_offset += len(labels)

    features_df = pd.concat(union_features, ignore_index=True)
    labels_df = pd.concat(union_labels, ignore_index=True)
    metadatas = [item["metadata"] for item in loaded]

    metadata = copy.deepcopy(base["metadata"])
    metadata["data_start"] = str(features_df["bar_time"].iloc[0])
    metadata["data_end"] = str(features_df["bar_time"].iloc[-1])
    metadata["total_bars"] = int(len(features_df))
    metadata["total_labeled_samples"] = int(len(labels_df))
    metadata["forced_pass_count"] = sum(int(item.get("forced_pass_count", 0)) for item in metadatas)
    metadata["label_distribution"] = _combine_counter_dicts(metadatas, "label_distribution")
    metadata["flip_distribution"] = _combine_counter_dicts(metadatas, "flip_distribution")
    metadata["input_files"] = [
        str(path)
        for item in metadatas
        for path in (item.get("input_files") or [])
    ]
    metadata["validation"] = _combine_validation(metadatas)
    metadata["fold_union"] = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_bundle_count": len(loaded),
        "source_step11_dirs": [str(item["dir"]) for item in loaded],
        "source_ranges": source_ranges,
        "non_overlapping_pass": True,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(output_dir / "features.parquet", index=False)
    labels_df.to_parquet(output_dir / "labels.parquet", index=False)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    _load_step11_bundle(output_dir)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a merged STEP11 fold union bundle.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Destination directory for merged STEP11 bundle")
    parser.add_argument("step11_dirs", nargs="+", type=Path, help="STEP11 bundle directories to merge")
    args = parser.parse_args()

    metadata = build_union(args.output_dir, args.step11_dirs)
    print(f"STEP11 union: {args.output_dir}")
    print(f"  Source bundles:   {metadata['fold_union']['source_bundle_count']}")
    print(f"  Total bars:       {metadata['total_bars']}")
    print(f"  Labeled samples:  {metadata['total_labeled_samples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
