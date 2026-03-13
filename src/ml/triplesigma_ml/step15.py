from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import onnx
import onnx.compose
import onnx.shape_inference
import onnxruntime as ort
from onnx import TensorProto, helper
from skl2onnx import to_onnx
from skl2onnx.common.data_types import FloatTensorType

from .step12 import FEATURE_DIM, WINDOW_SIZE, json_ready, write_json
from .step13 import LOWER_BOUNDS, UPPER_BOUNDS, postprocess_stage2_matrix


PINNED_OPSET = 17
SMOKE_SEED = 42
SMOKE_SAMPLES_PER_REGIME = 8
FLAT_INPUT_DIM = WINDOW_SIZE * FEATURE_DIM
PACK_META_REQUIRED_KEYS = (
    "model_pack_version",
    "schema_version",
    "regime_policy_version",
    "candidate_policy_version",
    "cost_model_version",
    "atr_thr",
    "adx_thr1",
    "adx_thr2",
)
PACK_META_OPTIONAL_KEYS = ("thr_method", "thr_seed", "thr_notes")
PACK_META_ADAPTIVE_KEYS = (
    "dist_atr_max_mode",
    "dist_atr_max_q",
    "dist_atr_max_w",
    "dist_atr_max_clamp_lo",
    "dist_atr_max_clamp_hi",
)
PACK_META_ALLOWED_KEYS = set(PACK_META_REQUIRED_KEYS + PACK_META_OPTIONAL_KEYS + PACK_META_ADAPTIVE_KEYS)
LINEAGE_REQUIRED_KEYS = (
    "schema_version",
    "model_pack_version",
    "candidate_policy_version",
    "regime_policy_version",
    "cost_model_version",
    "atr_thr",
    "adx_thr1",
    "adx_thr2",
    "dist_atr_max_mode",
    "dist_atr_max_q",
    "dist_atr_max_w",
    "dist_atr_max_clamp_lo",
    "dist_atr_max_clamp_hi",
)
STAGE1_PROB_TOLERANCE = 1e-4
PARITY_RTOL = 1e-4
PARITY_ATOL = 1e-4
GATE_CONFIG_FILENAME = "gate_config.json"
GATE_CONFIG_DEFAULTS = {
    "spread_atr_max_base": 0.30,
    "spread_atr_max_hard": 0.60,
    "k_tp_scale_min": 1.0,
    "k_tp_scale_max": 6.0,
    "dev_points_base": 3,
    "dev_points_add_max": 5,
    "dev_points_hard_max": 10,
    "risk_pct_base": 0.01,
    "risk_pct_hard_min": 0.002,
    "risk_pct_hard_max": 0.03,
}
GATE_CONFIG_RENDER_ORDER = (
    ("spread_atr_max_base", "0.30"),
    ("spread_atr_max_hard", "0.60"),
    ("k_tp_scale_min", "1.0"),
    ("k_tp_scale_max", "6.0"),
    ("dev_points_base", "3"),
    ("dev_points_add_max", "5"),
    ("dev_points_hard_max", "10"),
    ("risk_pct_base", "0.01"),
    ("risk_pct_hard_min", "0.002"),
    ("risk_pct_hard_max", "0.03"),
)


@dataclass(frozen=True)
class Step15Config:
    step14_dir: Path
    output_dir: Path
    target_opset: int
    smoke_seed: int
    smoke_samples_per_regime: int
    fail_on_acceptance: bool


@dataclass(frozen=True)
class Step15Context:
    step14_dir: Path
    handoff_manifest: dict[str, Any]
    selected_stage1_dir: Path
    selected_stage2_dir: Path
    selected_stage1_metadata: dict[str, Any]
    selected_stage2_metadata: dict[str, Any]
    selected_stage1_scaler_stats: dict[str, Any]
    selected_stage2_scaler_stats: dict[str, Any]
    selected_stage1_split_plan: dict[str, Any]
    selected_stage2_split_plan: dict[str, Any]
    source_step11_metadata: dict[str, Any]
    model_pack_version: str
    clf_version: str
    prm_version: str
    stage1_candidate_id: str
    stage2_candidate_id: str


def parse_args() -> Step15Config:
    parser = argparse.ArgumentParser(description="STEP15 ONNX export and model-pack validation for Triple Sigma.")
    parser.add_argument("--step14-dir", required=True, help="Accepted STEP14 artifact directory")
    parser.add_argument("--output-dir", required=True, help="STEP15 output directory")
    parser.add_argument("--target-opset", type=int, default=PINNED_OPSET)
    parser.add_argument("--smoke-seed", type=int, default=SMOKE_SEED)
    parser.add_argument("--smoke-samples-per-regime", type=int, default=SMOKE_SAMPLES_PER_REGIME)
    parser.add_argument("--fail-on-acceptance", action="store_true")
    args = parser.parse_args()

    if args.target_opset <= 0:
        raise ValueError("target_opset must be > 0")
    if args.smoke_samples_per_regime <= 0:
        raise ValueError("smoke_samples_per_regime must be > 0")

    return Step15Config(
        step14_dir=Path(args.step14_dir),
        output_dir=Path(args.output_dir),
        target_opset=args.target_opset,
        smoke_seed=args.smoke_seed,
        smoke_samples_per_regime=args.smoke_samples_per_regime,
        fail_on_acceptance=args.fail_on_acceptance,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_joblib(path: Path) -> Any:
    return joblib.load(path)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_version_token(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9._-]+", value or ""))


def stringify_pack_meta_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".15g")
    return str(value)


def tensor_shape(value_info: onnx.ValueInfoProto) -> list[int]:
    dims: list[int] = []
    for dim in value_info.type.tensor_type.shape.dim:
        if dim.HasField("dim_value"):
            dims.append(int(dim.dim_value))
        else:
            dims.append(-1)
    return dims


def tensor_elem_type(value_info: onnx.ValueInfoProto) -> str:
    elem_type = value_info.type.tensor_type.elem_type
    return onnx.TensorProto.DataType.Name(elem_type)


def semantic_json_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return json_ready(a) == json_ready(b)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"required STEP15 input not found: {path}")


def load_step15_context(step14_dir: Path) -> Step15Context:
    handoff_path = step14_dir / "handoff_manifest.json"
    selected_stage1_dir = step14_dir / "selected_stage1"
    selected_stage2_dir = step14_dir / "selected_stage2"
    selected_stage1_metadata_path = selected_stage1_dir / "training_metadata.json"
    selected_stage2_metadata_path = selected_stage2_dir / "training_metadata.json"
    selected_stage1_scaler_path = selected_stage1_dir / "scaler_stats.json"
    selected_stage2_scaler_path = selected_stage2_dir / "scaler_stats.json"
    selected_stage1_split_path = selected_stage1_dir / "split_plan.json"
    selected_stage2_split_path = selected_stage2_dir / "split_plan.json"
    for required in (
        handoff_path,
        selected_stage1_metadata_path,
        selected_stage2_metadata_path,
        selected_stage1_scaler_path,
        selected_stage2_scaler_path,
        selected_stage1_split_path,
        selected_stage2_split_path,
    ):
        require_file(required)
    for regime_id in range(6):
        require_file(selected_stage1_dir / f"regime_{regime_id}" / f"clf_reg{regime_id}.joblib")
        require_file(selected_stage2_dir / f"regime_{regime_id}" / f"prm_reg{regime_id}.joblib")

    handoff_manifest = load_json(handoff_path)
    selected_stage1_metadata = load_json(selected_stage1_metadata_path)
    selected_stage2_metadata = load_json(selected_stage2_metadata_path)
    selected_stage1_scaler_stats = load_json(selected_stage1_scaler_path)
    selected_stage2_scaler_stats = load_json(selected_stage2_scaler_path)
    selected_stage1_split_plan = load_json(selected_stage1_split_path)
    selected_stage2_split_plan = load_json(selected_stage2_split_path)

    source_step11_stage1 = selected_stage1_metadata.get("source_step11_metadata")
    source_step11_stage2 = selected_stage2_metadata.get("source_step11_metadata")
    if not isinstance(source_step11_stage1, dict) or not isinstance(source_step11_stage2, dict):
        raise ValueError("selected STEP14 metadata missing source_step11_metadata")
    if not semantic_json_equal(source_step11_stage1, source_step11_stage2):
        raise ValueError("selected_stage1 and selected_stage2 source_step11_metadata mismatch")

    model_pack_version = str(source_step11_stage1.get("model_pack_version", ""))
    if not safe_version_token(model_pack_version):
        raise ValueError(f"invalid model_pack_version for STEP15 export: {model_pack_version!r}")

    clf_version = str(selected_stage1_metadata.get("clf_version", ""))
    prm_version = str(selected_stage2_metadata.get("prm_version", ""))
    stage1_handoff = handoff_manifest.get("stage1", {})
    stage2_handoff = handoff_manifest.get("stage2", {})
    if stage1_handoff.get("clf_version") != clf_version:
        raise ValueError("handoff stage1 clf_version does not match selected_stage1 training metadata")
    if stage2_handoff.get("prm_version") != prm_version:
        raise ValueError("handoff stage2 prm_version does not match selected_stage2 training metadata")

    return Step15Context(
        step14_dir=step14_dir,
        handoff_manifest=handoff_manifest,
        selected_stage1_dir=selected_stage1_dir,
        selected_stage2_dir=selected_stage2_dir,
        selected_stage1_metadata=selected_stage1_metadata,
        selected_stage2_metadata=selected_stage2_metadata,
        selected_stage1_scaler_stats=selected_stage1_scaler_stats,
        selected_stage2_scaler_stats=selected_stage2_scaler_stats,
        selected_stage1_split_plan=selected_stage1_split_plan,
        selected_stage2_split_plan=selected_stage2_split_plan,
        source_step11_metadata=source_step11_stage1,
        model_pack_version=model_pack_version,
        clf_version=clf_version,
        prm_version=prm_version,
        stage1_candidate_id=str(stage1_handoff.get("final_handoff_candidate_id", "")),
        stage2_candidate_id=str(stage2_handoff.get("final_handoff_candidate_id", "")),
    )


def validate_lineage_required_keys(metadata: dict[str, Any]) -> list[str]:
    return [key for key in LINEAGE_REQUIRED_KEYS if key not in metadata]


def validate_source_bundle(context: Step15Context) -> dict[str, Any]:
    stage1_source = context.selected_stage1_metadata["source_step11_metadata"]
    stage2_source = context.selected_stage2_metadata["source_step11_metadata"]
    missing_stage1_keys = validate_lineage_required_keys(stage1_source)
    missing_stage2_keys = validate_lineage_required_keys(stage2_source)
    lineage_matches = {
        key: stage1_source.get(key) == stage2_source.get(key)
        for key in LINEAGE_REQUIRED_KEYS
        if key in stage1_source and key in stage2_source
    }
    scaler_equal = semantic_json_equal(context.selected_stage1_scaler_stats, context.selected_stage2_scaler_stats)
    split_equal = semantic_json_equal(context.selected_stage1_split_plan, context.selected_stage2_split_plan)

    return json_ready(
        {
            "required_files_present": True,
            "handoff_stage1_matches_selected": context.handoff_manifest["stage1"]["clf_version"] == context.clf_version,
            "handoff_stage2_matches_selected": context.handoff_manifest["stage2"]["prm_version"] == context.prm_version,
            "missing_stage1_lineage_keys": missing_stage1_keys,
            "missing_stage2_lineage_keys": missing_stage2_keys,
            "lineage_matches": lineage_matches,
            "selected_scaler_stats_equal": scaler_equal,
            "selected_split_plan_equal": split_equal,
            "A1_source_bundle_complete_and_consistent": (
                not missing_stage1_keys
                and not missing_stage2_keys
                and all(lineage_matches.values())
                and scaler_equal
                and split_equal
            ),
        }
    )


def build_pack_meta_dict(context: Step15Context) -> dict[str, Any]:
    source = context.source_step11_metadata
    pack_meta: dict[str, Any] = {key: source[key] for key in PACK_META_REQUIRED_KEYS}
    for key in PACK_META_OPTIONAL_KEYS:
        value = source.get(key)
        if value not in (None, ""):
            pack_meta[key] = value
    dist_mode = str(source.get("dist_atr_max_mode", ""))
    if dist_mode == "adaptive_quantile":
        for key in PACK_META_ADAPTIVE_KEYS:
            pack_meta[key] = source[key]
    return pack_meta


def write_pack_meta(path: Path, payload: dict[str, Any]) -> None:
    unsupported = [key for key in payload if key not in PACK_META_ALLOWED_KEYS]
    if unsupported:
        raise ValueError(f"unsupported pack_meta keys for runtime-compatible STEP15 pack: {unsupported}")
    lines = [f"{key}={stringify_pack_meta_value(payload[key])}" for key in payload]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_scaler_stats(context: Step15Context, output_path: Path) -> None:
    payload = json.dumps(json_ready(context.selected_stage1_scaler_stats), indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(payload, encoding="utf-8")


def build_gate_config_dict() -> dict[str, Any]:
    return dict(GATE_CONFIG_DEFAULTS)


def write_gate_config(path: Path, payload: dict[str, Any]) -> None:
    lines = ["{"]
    last_index = len(GATE_CONFIG_RENDER_ORDER) - 1
    for index, (key, rendered_value) in enumerate(GATE_CONFIG_RENDER_ORDER):
        suffix = "," if index < last_index else ""
        lines.append(f'  "{key}": {rendered_value}{suffix}')
    lines.append("}")
    serialized = "\n".join(lines) + "\r\n"
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        handle.write(serialized)


def replace_node_input(nodes: list[onnx.NodeProto], old_name: str, new_name: str) -> list[onnx.NodeProto]:
    replaced: list[onnx.NodeProto] = []
    for node in nodes:
        new_node = copy.deepcopy(node)
        for idx, input_name in enumerate(new_node.input):
            if input_name == old_name:
                new_node.input[idx] = new_name
        replaced.append(new_node)
    return replaced


def gather_opset_imports(*models: onnx.ModelProto) -> list[onnx.OperatorSetIdProto]:
    versions: dict[str, int] = {}
    for model in models:
        for opset in model.opset_import:
            versions[opset.domain] = max(versions.get(opset.domain, 0), int(opset.version))
    return [helper.make_operatorsetid(domain, version) for domain, version in sorted(versions.items())]


def export_stage1_model(model_bundle: dict[str, Any], target_opset: int) -> onnx.ModelProto:
    sklearn_model = model_bundle["model"]
    base_model = to_onnx(
        sklearn_model,
        initial_types=[("X", FloatTensorType([1, FLAT_INPUT_DIM]))],
        options={id(sklearn_model): {"zipmap": False}},
        target_opset=target_opset,
    )
    base_model = onnx.compose.add_prefix(base_model, "clf_")
    nodes = [helper.make_node("Reshape", ["input", "flat_shape"], ["flat"], name="reshape_flat")]
    nodes.extend(replace_node_input(list(base_model.graph.node), "clf_X", "flat"))
    nodes.append(helper.make_node("Identity", ["clf_probabilities"], ["output"], name="select_probabilities"))
    graph = helper.make_graph(
        nodes,
        "triplesigma_step15_stage1",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, WINDOW_SIZE, FEATURE_DIM])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3])],
        initializer=[
            helper.make_tensor("flat_shape", TensorProto.INT64, [2], [1, FLAT_INPUT_DIM]),
            *[copy.deepcopy(initializer) for initializer in base_model.graph.initializer],
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=[copy.deepcopy(opset) for opset in base_model.opset_import],
        producer_name="triplesigma_ml.step15",
        producer_version="0.1.0",
    )
    model.ir_version = base_model.ir_version
    return model


def export_stage2_model(stage2_bundle: Any, target_opset: int) -> onnx.ModelProto:
    long_model = to_onnx(
        stage2_bundle.long_head.model,
        initial_types=[("X", FloatTensorType([1, FLAT_INPUT_DIM]))],
        target_opset=target_opset,
    )
    short_model = to_onnx(
        stage2_bundle.short_head.model,
        initial_types=[("X", FloatTensorType([1, FLAT_INPUT_DIM]))],
        target_opset=target_opset,
    )
    long_model = onnx.compose.add_prefix(long_model, "long_")
    short_model = onnx.compose.add_prefix(short_model, "short_")
    nodes = [helper.make_node("Reshape", ["input", "flat_shape"], ["flat"], name="reshape_flat")]
    nodes.extend(replace_node_input(list(long_model.graph.node), "long_X", "flat"))
    nodes.extend(replace_node_input(list(short_model.graph.node), "short_X", "flat"))
    nodes.append(helper.make_node("Concat", ["long_variable", "short_variable"], ["output"], axis=1, name="concat_stage2"))
    graph = helper.make_graph(
        nodes,
        "triplesigma_step15_stage2",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, WINDOW_SIZE, FEATURE_DIM])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 6])],
        initializer=[
            helper.make_tensor("flat_shape", TensorProto.INT64, [2], [1, FLAT_INPUT_DIM]),
            *[copy.deepcopy(initializer) for initializer in long_model.graph.initializer],
            *[copy.deepcopy(initializer) for initializer in short_model.graph.initializer],
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=gather_opset_imports(long_model, short_model),
        producer_name="triplesigma_ml.step15",
        producer_version="0.1.0",
    )
    model.ir_version = max(long_model.ir_version, short_model.ir_version)
    return model


def save_onnx_model(model: onnx.ModelProto, path: Path) -> None:
    inferred = onnx.shape_inference.infer_shapes(model)
    onnx.checker.check_model(inferred, full_check=True)
    path.write_bytes(inferred.SerializeToString())


def stage1_filename(regime_id: int, model_pack_version: str) -> str:
    return f"clf_reg{regime_id}_v{model_pack_version}.onnx"


def stage2_filename(regime_id: int, model_pack_version: str) -> str:
    return f"prm_reg{regime_id}_v{model_pack_version}.onnx"


def export_model_pack(context: Step15Context, config: Step15Config, model_pack_dir: Path) -> dict[str, list[str]]:
    stage1_files: list[str] = []
    stage2_files: list[str] = []
    for regime_id in range(6):
        stage1_bundle = load_joblib(context.selected_stage1_dir / f"regime_{regime_id}" / f"clf_reg{regime_id}.joblib")
        stage1_path = model_pack_dir / stage1_filename(regime_id, context.model_pack_version)
        save_onnx_model(export_stage1_model(stage1_bundle, config.target_opset), stage1_path)
        stage1_files.append(stage1_path.name)

        stage2_bundle = load_joblib(context.selected_stage2_dir / f"regime_{regime_id}" / f"prm_reg{regime_id}.joblib")
        stage2_path = model_pack_dir / stage2_filename(regime_id, context.model_pack_version)
        save_onnx_model(export_stage2_model(stage2_bundle, config.target_opset), stage2_path)
        stage2_files.append(stage2_path.name)
    return {"stage1": stage1_files, "stage2": stage2_files}


def validate_scaler_stats_payload(payload: dict[str, Any]) -> dict[str, Any]:
    mean = payload.get("mean")
    std = payload.get("std")
    if not isinstance(mean, list) or not isinstance(std, list):
        return {"schema_valid": False, "reason": "scaler_stats must contain mean/std lists"}
    finite_mean = [np.isfinite(value) for value in mean]
    finite_std = [np.isfinite(value) for value in std]
    std_positive = [float(value) > 0.0 for value in std] if len(std) == 12 else []
    return json_ready(
        {
            "schema_valid": len(mean) == 12 and len(std) == 12 and all(finite_mean) and all(finite_std) and all(std_positive),
            "mean_length": len(mean),
            "std_length": len(std),
            "all_mean_finite": all(finite_mean),
            "all_std_finite": all(finite_std),
            "all_std_positive": all(std_positive) if std_positive else False,
        }
    )


def generate_smoke_samples(seed: int, count: int, regime_id: int) -> list[np.ndarray]:
    samples: list[np.ndarray] = []
    for index in range(count):
        rng = np.random.default_rng(seed + regime_id * 100 + index)
        sample = rng.normal(size=(1, WINDOW_SIZE, FEATURE_DIM)).astype(np.float32)
        samples.append(sample)
    return samples


def run_ort(path: Path, sample: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    return np.asarray(session.run(None, {input_name: sample})[0], dtype=np.float32)


def validate_exported_onnx_file(path: Path, expected_output_shape: list[int]) -> dict[str, Any]:
    model = onnx.load(path)
    checker_ok = True
    checker_error = ""
    try:
        onnx.checker.check_model(model, full_check=True)
    except Exception as exc:
        checker_ok = False
        checker_error = str(exc)

    inferred_ok = True
    inferred_error = ""
    inferred_model = model
    try:
        inferred_model = onnx.shape_inference.infer_shapes(model)
    except Exception as exc:
        inferred_ok = False
        inferred_error = str(exc)

    inputs = inferred_model.graph.input
    outputs = inferred_model.graph.output
    input_summary = [{"name": item.name, "dtype": tensor_elem_type(item), "shape": tensor_shape(item)} for item in inputs]
    output_summary = [{"name": item.name, "dtype": tensor_elem_type(item), "shape": tensor_shape(item)} for item in outputs]
    shape_contract_ok = (
        len(inputs) == 1
        and len(outputs) == 1
        and input_summary[0]["dtype"] == "FLOAT"
        and input_summary[0]["shape"] == [1, WINDOW_SIZE, FEATURE_DIM]
        and output_summary[0]["dtype"] == "FLOAT"
        and output_summary[0]["shape"] == expected_output_shape
    )
    return json_ready(
        {
            "path": str(path),
            "checker_ok": checker_ok,
            "checker_error": checker_error,
            "shape_inference_ok": inferred_ok,
            "shape_inference_error": inferred_error,
            "inputs": input_summary,
            "outputs": output_summary,
            "shape_contract_ok": shape_contract_ok,
        }
    )


def run_stage1_smoke(context: Step15Context, config: Step15Config, model_pack_dir: Path) -> dict[str, Any]:
    overall = True
    by_regime: dict[str, Any] = {}
    for regime_id in range(6):
        model_path = model_pack_dir / stage1_filename(regime_id, context.model_pack_version)
        source_bundle = load_joblib(context.selected_stage1_dir / f"regime_{regime_id}" / f"clf_reg{regime_id}.joblib")
        source_model = source_bundle["model"]
        regime_result = {
            "shape_ok": True,
            "prob_all_finite": True,
            "prob_sum_close": True,
            "parity_allclose": True,
            "max_abs_diff": 0.0,
            "samples_tested": config.smoke_samples_per_regime,
        }
        for sample in generate_smoke_samples(config.smoke_seed, config.smoke_samples_per_regime, regime_id):
            onnx_prob = run_ort(model_path, sample)
            source_prob = np.asarray(source_model.predict_proba(sample.reshape(1, FLAT_INPUT_DIM)), dtype=np.float32)
            diff = float(np.max(np.abs(onnx_prob - source_prob)))
            regime_result["max_abs_diff"] = max(regime_result["max_abs_diff"], diff)
            regime_result["shape_ok"] = regime_result["shape_ok"] and tuple(onnx_prob.shape) == (1, 3)
            regime_result["prob_all_finite"] = regime_result["prob_all_finite"] and bool(np.isfinite(onnx_prob).all())
            regime_result["prob_sum_close"] = regime_result["prob_sum_close"] and bool(
                np.allclose(np.sum(onnx_prob, axis=1), np.ones(1, dtype=np.float32), atol=STAGE1_PROB_TOLERANCE, rtol=0.0)
            )
            regime_result["parity_allclose"] = regime_result["parity_allclose"] and bool(
                np.allclose(onnx_prob, source_prob, rtol=PARITY_RTOL, atol=PARITY_ATOL)
            )
        regime_pass = all(
            (
                regime_result["shape_ok"],
                regime_result["prob_all_finite"],
                regime_result["prob_sum_close"],
                regime_result["parity_allclose"],
            )
        )
        regime_result["passed"] = regime_pass
        overall = overall and regime_pass
        by_regime[str(regime_id)] = json_ready(regime_result)
    return json_ready({"all_passed": overall, "by_regime": by_regime})


def run_stage2_smoke(context: Step15Context, config: Step15Config, model_pack_dir: Path) -> dict[str, Any]:
    overall = True
    by_regime: dict[str, Any] = {}
    for regime_id in range(6):
        model_path = model_pack_dir / stage2_filename(regime_id, context.model_pack_version)
        source_bundle = load_joblib(context.selected_stage2_dir / f"regime_{regime_id}" / f"prm_reg{regime_id}.joblib")
        regime_result = {
            "shape_ok": True,
            "raw_all_finite": True,
            "effective_all_finite": True,
            "contract_valid": True,
            "holds_integral": True,
            "parity_allclose": True,
            "max_abs_diff": 0.0,
            "samples_tested": config.smoke_samples_per_regime,
        }
        for sample in generate_smoke_samples(config.smoke_seed, config.smoke_samples_per_regime, regime_id):
            onnx_raw = run_ort(model_path, sample)
            source_raw = np.asarray(source_bundle.predict_raw(sample.reshape(1, FLAT_INPUT_DIM)), dtype=np.float32)
            effective = postprocess_stage2_matrix(onnx_raw)
            diff = float(np.max(np.abs(onnx_raw - source_raw)))
            regime_result["max_abs_diff"] = max(regime_result["max_abs_diff"], diff)
            regime_result["shape_ok"] = regime_result["shape_ok"] and tuple(onnx_raw.shape) == (1, 6)
            regime_result["raw_all_finite"] = regime_result["raw_all_finite"] and bool(np.isfinite(onnx_raw).all())
            regime_result["effective_all_finite"] = regime_result["effective_all_finite"] and bool(np.isfinite(effective).all())
            regime_result["contract_valid"] = regime_result["contract_valid"] and bool(
                np.all((effective[:, 0] >= LOWER_BOUNDS[0]) & (effective[:, 0] <= UPPER_BOUNDS[0]))
                and np.all((effective[:, 1] >= LOWER_BOUNDS[1]) & (effective[:, 1] <= UPPER_BOUNDS[1]))
                and np.all((effective[:, 2] >= LOWER_BOUNDS[2]) & (effective[:, 2] <= UPPER_BOUNDS[2]))
                and np.all((effective[:, 3] >= LOWER_BOUNDS[0]) & (effective[:, 3] <= UPPER_BOUNDS[0]))
                and np.all((effective[:, 4] >= LOWER_BOUNDS[1]) & (effective[:, 4] <= UPPER_BOUNDS[1]))
                and np.all((effective[:, 5] >= LOWER_BOUNDS[2]) & (effective[:, 5] <= UPPER_BOUNDS[2]))
            )
            regime_result["holds_integral"] = regime_result["holds_integral"] and bool(
                np.allclose(effective[:, 2], np.rint(effective[:, 2]), atol=0.0, rtol=0.0)
                and np.allclose(effective[:, 5], np.rint(effective[:, 5]), atol=0.0, rtol=0.0)
            )
            regime_result["parity_allclose"] = regime_result["parity_allclose"] and bool(
                np.allclose(onnx_raw, source_raw, rtol=PARITY_RTOL, atol=PARITY_ATOL)
            )
        regime_pass = all(
            (
                regime_result["shape_ok"],
                regime_result["raw_all_finite"],
                regime_result["effective_all_finite"],
                regime_result["contract_valid"],
                regime_result["holds_integral"],
                regime_result["parity_allclose"],
            )
        )
        regime_result["passed"] = regime_pass
        overall = overall and regime_pass
        by_regime[str(regime_id)] = json_ready(regime_result)
    return json_ready({"all_passed": overall, "by_regime": by_regime})


def validate_pack_meta(pack_meta: dict[str, Any], pack_meta_path: Path, source_step11_metadata: dict[str, Any]) -> dict[str, Any]:
    missing_required = [key for key in PACK_META_REQUIRED_KEYS if key not in pack_meta]
    if pack_meta.get("dist_atr_max_mode") == "adaptive_quantile":
        missing_required.extend([key for key in PACK_META_ADAPTIVE_KEYS if key not in pack_meta])
    unsupported_keys = [key for key in pack_meta if key not in PACK_META_ALLOWED_KEYS]
    value_matches = {key: pack_meta.get(key) == source_step11_metadata.get(key) for key in pack_meta}
    return json_ready(
        {
            "path": str(pack_meta_path),
            "missing_required_keys": missing_required,
            "unsupported_keys": unsupported_keys,
            "value_matches_source_step11": value_matches,
            "format": "key_value_text",
            "runtime_compatible": not missing_required and not unsupported_keys and all(value_matches.values()),
        }
    )


def validate_gate_config(gate_config: dict[str, Any], gate_config_path: Path) -> dict[str, Any]:
    expected_keys = list(GATE_CONFIG_DEFAULTS.keys())
    actual_keys = list(gate_config.keys())
    missing_required = [key for key in expected_keys if key not in gate_config]
    unsupported_keys = [key for key in actual_keys if key not in GATE_CONFIG_DEFAULTS]
    value_matches = {
        key: gate_config.get(key) == GATE_CONFIG_DEFAULTS[key]
        for key in expected_keys
        if key in gate_config
    }
    return json_ready(
        {
            "path": str(gate_config_path),
            "missing_required_keys": missing_required,
            "unsupported_keys": unsupported_keys,
            "value_matches_runtime_defaults": value_matches,
            "runtime_compatible": not missing_required and not unsupported_keys and all(value_matches.values()),
        }
    )


def collect_file_hashes(model_pack_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(model_pack_dir.iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    return hashes


def build_export_manifest(
    *,
    context: Step15Context,
    config: Step15Config,
    model_pack_dir: Path,
    pack_meta: dict[str, Any],
    stage1_files: list[str],
    stage2_files: list[str],
) -> dict[str, Any]:
    return json_ready(
        {
            "source_step14_dir": str(context.step14_dir),
            "selected_candidate_ids": {"stage1": context.stage1_candidate_id, "stage2": context.stage2_candidate_id},
            "clf_version": context.clf_version,
            "prm_version": context.prm_version,
            "model_pack_version": context.model_pack_version,
            "schema_version": context.source_step11_metadata["schema_version"],
            "candidate_policy_version": context.source_step11_metadata["candidate_policy_version"],
            "regime_policy_version": context.source_step11_metadata["regime_policy_version"],
            "cost_model_version": context.source_step11_metadata["cost_model_version"],
            "atr_thr": context.source_step11_metadata["atr_thr"],
            "adx_thr1": context.source_step11_metadata["adx_thr1"],
            "adx_thr2": context.source_step11_metadata["adx_thr2"],
            "dist_atr_max_mode": context.source_step11_metadata["dist_atr_max_mode"],
            "dist_atr_max_q": context.source_step11_metadata["dist_atr_max_q"],
            "dist_atr_max_w": context.source_step11_metadata["dist_atr_max_w"],
            "dist_atr_max_clamp_lo": context.source_step11_metadata["dist_atr_max_clamp_lo"],
            "dist_atr_max_clamp_hi": context.source_step11_metadata["dist_atr_max_clamp_hi"],
            "target_opset": config.target_opset,
            "model_pack_dir": str(model_pack_dir),
            "stage1_files": stage1_files,
            "stage2_files": stage2_files,
            "pack_meta": pack_meta,
            "file_sha256": collect_file_hashes(model_pack_dir),
        }
    )


def build_export_validation_report(
    *,
    source_bundle_audit: dict[str, Any],
    stage1_validation: dict[str, Any],
    stage2_validation: dict[str, Any],
    pack_meta_validation: dict[str, Any],
    gate_config_validation: dict[str, Any],
    scaler_validation: dict[str, Any],
    stage1_smoke: dict[str, Any],
    stage2_smoke: dict[str, Any],
    pack_layout_validation: dict[str, Any],
    export_manifest: dict[str, Any],
) -> dict[str, Any]:
    acceptance = {
        "A1_source_bundle_complete_and_consistent": source_bundle_audit["A1_source_bundle_complete_and_consistent"],
        "A2_stage1_onnx_export_complete": stage1_validation["all_passed"],
        "A3_stage2_onnx_export_complete": stage2_validation["all_passed"],
        "A4_pack_meta_complete_and_runtime_compatible": pack_meta_validation["runtime_compatible"],
        "A4b_gate_config_runtime_compatible": gate_config_validation["runtime_compatible"],
        "A5_scaler_stats_packaged_and_valid": scaler_validation["schema_valid"] and scaler_validation["semantic_match_selected"],
        "A6_static_inference_smoke_pass": stage1_smoke["all_passed"] and stage2_smoke["all_passed"],
        "A7_source_parity_smoke_pass": stage1_smoke["all_passed"] and stage2_smoke["all_passed"],
        "A8_pack_layout_runtime_compatible": pack_layout_validation["runtime_compatible"],
        "A9_export_reports_complete": True,
    }
    return json_ready(
        {
            "accepted": all(acceptance.values()),
            "acceptance": acceptance,
            "source_bundle_audit": source_bundle_audit,
            "stage1_onnx_validation": stage1_validation,
            "stage2_onnx_validation": stage2_validation,
            "pack_meta_validation": pack_meta_validation,
            "gate_config_validation": gate_config_validation,
            "scaler_validation": scaler_validation,
            "stage1_smoke": stage1_smoke,
            "stage2_smoke": stage2_smoke,
            "pack_layout_validation": pack_layout_validation,
            "export_manifest": export_manifest,
        }
    )


def validate_stage_exports(model_pack_dir: Path, context: Step15Context) -> tuple[dict[str, Any], dict[str, Any]]:
    stage1_results: dict[str, Any] = {}
    stage2_results: dict[str, Any] = {}
    stage1_overall = True
    stage2_overall = True
    for regime_id in range(6):
        stage1_result = validate_exported_onnx_file(model_pack_dir / stage1_filename(regime_id, context.model_pack_version), [1, 3])
        stage2_result = validate_exported_onnx_file(model_pack_dir / stage2_filename(regime_id, context.model_pack_version), [1, 6])
        stage1_results[str(regime_id)] = stage1_result
        stage2_results[str(regime_id)] = stage2_result
        stage1_overall = stage1_overall and stage1_result["checker_ok"] and stage1_result["shape_inference_ok"] and stage1_result["shape_contract_ok"]
        stage2_overall = stage2_overall and stage2_result["checker_ok"] and stage2_result["shape_inference_ok"] and stage2_result["shape_contract_ok"]
    return (
        json_ready({"all_passed": stage1_overall, "by_regime": stage1_results}),
        json_ready({"all_passed": stage2_overall, "by_regime": stage2_results}),
    )


def validate_pack_layout(model_pack_dir: Path, context: Step15Context) -> dict[str, Any]:
    files = sorted(path.name for path in model_pack_dir.iterdir() if path.is_file())
    expected = [stage1_filename(regime_id, context.model_pack_version) for regime_id in range(6)] + [
        stage2_filename(regime_id, context.model_pack_version) for regime_id in range(6)
    ] + [
        "pack_meta.csv",
        "scaler_stats.json",
        GATE_CONFIG_FILENAME,
    ]
    return json_ready({"files": files, "expected_files": expected, "runtime_compatible": files == sorted(expected)})


def main() -> int:
    config = parse_args()
    context = load_step15_context(config.step14_dir)

    ensure_clean_dir(config.output_dir)
    model_pack_dir = config.output_dir / "model_pack"
    model_pack_dir.mkdir(parents=True, exist_ok=True)

    source_bundle_audit = validate_source_bundle(context)
    pack_meta = build_pack_meta_dict(context)
    gate_config = build_gate_config_dict()
    write_pack_meta(model_pack_dir / "pack_meta.csv", pack_meta)
    copy_scaler_stats(context, model_pack_dir / "scaler_stats.json")
    write_gate_config(model_pack_dir / GATE_CONFIG_FILENAME, gate_config)
    exported_files = export_model_pack(context, config, model_pack_dir)

    stage1_validation, stage2_validation = validate_stage_exports(model_pack_dir, context)
    pack_meta_validation = validate_pack_meta(pack_meta, model_pack_dir / "pack_meta.csv", context.source_step11_metadata)
    gate_config_validation = validate_gate_config(gate_config, model_pack_dir / GATE_CONFIG_FILENAME)
    scaler_validation = validate_scaler_stats_payload(load_json(model_pack_dir / "scaler_stats.json"))
    scaler_validation["semantic_match_selected"] = semantic_json_equal(load_json(model_pack_dir / "scaler_stats.json"), context.selected_stage1_scaler_stats)
    stage1_smoke = run_stage1_smoke(context, config, model_pack_dir)
    stage2_smoke = run_stage2_smoke(context, config, model_pack_dir)
    pack_layout_validation = validate_pack_layout(model_pack_dir, context)

    export_manifest = build_export_manifest(
        context=context,
        config=config,
        model_pack_dir=model_pack_dir,
        pack_meta=pack_meta,
        stage1_files=exported_files["stage1"],
        stage2_files=exported_files["stage2"],
    )
    write_json(config.output_dir / "export_manifest.json", export_manifest)

    export_validation_report = build_export_validation_report(
        source_bundle_audit=source_bundle_audit,
        stage1_validation=stage1_validation,
        stage2_validation=stage2_validation,
        pack_meta_validation=pack_meta_validation,
        gate_config_validation=gate_config_validation,
        scaler_validation=json_ready(scaler_validation),
        stage1_smoke=stage1_smoke,
        stage2_smoke=stage2_smoke,
        pack_layout_validation=pack_layout_validation,
        export_manifest=export_manifest,
    )
    write_json(config.output_dir / "export_validation_report.json", export_validation_report)

    acceptance = export_validation_report["acceptance"]
    print(f"[STEP15] export_manifest={config.output_dir / 'export_manifest.json'}")
    print(f"[STEP15] export_validation_report={config.output_dir / 'export_validation_report.json'}")
    print(f"[STEP15] accepted={export_validation_report['accepted']}")
    print(f"[STEP15] model_pack_version={context.model_pack_version}")
    if config.fail_on_acceptance and not all(acceptance.values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
