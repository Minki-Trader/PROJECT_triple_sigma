"""
build_stage1_refresh_packet.py - Build a WF5 ML-first kickoff packet.

Usage:
    python tools/build_stage1_refresh_packet.py <run_dir> [--step14-dir <dir>]
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from pack_registry import resolve_pack_meta_path, resolve_step14_dir


REQUIRED_BAR_LOG_COLUMNS = {
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
    *[f"feature_{idx}" for idx in range(22)],
}

# Keep the STEP14 output folder short enough for Windows path-length limits.
WF5_STAGE14_DIRNAME = "s14"


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _validate_against_schema(data: dict[str, Any], schema_path: Path) -> list[str]:
    import jsonschema

    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda err: list(err.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def _determine_project_root(path: Path) -> Path:
    root = path.resolve()
    while root.name != "PROJECT_triple_sigma" and root.parent != root:
        root = root.parent
    return root


def _repo_ref(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_campaign_manifest(run_dir: Path, run_manifest: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    manifest_ref = run_manifest.get("manifest_ref")
    if not manifest_ref:
        raise ValueError("run_manifest.json missing manifest_ref")
    manifest_path = Path(manifest_ref)
    if not manifest_path.exists():
        manifest_path = _determine_project_root(run_dir) / manifest_ref
    if not manifest_path.exists():
        raise FileNotFoundError(f"campaign manifest not found: {manifest_ref}")
    with open(manifest_path, encoding="utf-8") as handle:
        return manifest_path, yaml.safe_load(handle) or {}


def _resolve_reports_dir(project_root: Path, manifest_path: Path, campaign_manifest: dict[str, Any]) -> Path:
    reports_ref = ((campaign_manifest.get("output_dirs") or {}).get("reports") or "").strip()
    if reports_ref:
        reports_path = Path(reports_ref)
        if not reports_path.is_absolute():
            reports_path = project_root / reports_ref
        return reports_path
    return manifest_path.parent / "reports"


def _within_any_window(start_ts: pd.Timestamp, end_ts: pd.Timestamp, windows: list[dict[str, str]]) -> bool:
    for window in windows:
        window_start = pd.Timestamp(window["from"])
        window_end = pd.Timestamp(window["to"])
        if start_ts >= window_start and end_ts <= window_end:
            return True
    return False


def _overlaps_window(start_ts: pd.Timestamp, end_ts: pd.Timestamp, window: dict[str, str]) -> bool:
    window_start = pd.Timestamp(window["from"])
    window_end = pd.Timestamp(window["to"])
    return max(start_ts, window_start) <= min(end_ts, window_end)


def _artifact_root(project_root: Path, campaign_id: str, source_run_id: str) -> Path:
    return project_root / "_coord" / "artifacts" / f"{campaign_id}_{source_run_id}_wf5_stage1_refresh"


def _read_csv_header(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader)


def _read_first_timestamp(path: Path) -> pd.Timestamp | None:
    with open(path, encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        first_row = next(reader, None)
    if not first_row:
        return None
    return pd.Timestamp(first_row[0])


def _read_last_timestamp(path: Path) -> pd.Timestamp | None:
    last_row = None
    with open(path, encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if row:
                last_row = row
    if not last_row:
        return None
    return pd.Timestamp(last_row[0])


def _discover_bar_log_directories(
    project_root: Path,
    *,
    campaign_id: str,
    source_run_id: str,
) -> list[dict[str, Any]]:
    artifacts_root = project_root / "_coord" / "artifacts"
    if not artifacts_root.exists():
        return []

    discovered: list[dict[str, Any]] = []
    for artifact_dir in sorted(artifacts_root.iterdir()):
        if not artifact_dir.is_dir():
            continue

        manifest_path = artifact_dir / "manifest.json"
        wf5_manifest_path = artifact_dir / "wf5_fold_source_manifest.json"
        if not manifest_path.exists() or not wf5_manifest_path.exists():
            continue

        manifest = _load_json(manifest_path)
        wf5_manifest = _load_json(wf5_manifest_path)

        if str(manifest.get("validation_class", "")).strip() != "wf5-fold-source":
            continue
        if str(wf5_manifest.get("campaign_id", "")).strip() != campaign_id:
            continue
        if str(wf5_manifest.get("source_run_id", "")).strip() != source_run_id:
            continue

        fold_id = str(wf5_manifest.get("fold_id", "")).strip()
        if not fold_id:
            continue

        files = sorted(artifact_dir.glob("bar_log_*.csv"))
        if not files:
            continue

        header = _read_csv_header(files[0])
        if not REQUIRED_BAR_LOG_COLUMNS.issubset(set(header)):
            continue

        first_ts = _read_first_timestamp(files[0])
        last_ts = _read_last_timestamp(files[-1])
        if first_ts is None or last_ts is None:
            continue

        discovered.append(
            {
                "fold_id": fold_id,
                "path": _repo_ref(project_root, artifact_dir),
                "first_timestamp": first_ts,
                "last_timestamp": last_ts,
                "file_count": len(files),
                "source_manifest_ref": _repo_ref(project_root, manifest_path),
                "source_wf5_manifest_ref": _repo_ref(project_root, wf5_manifest_path),
            }
        )
    return discovered


def _select_fold_sources(
    optimization_folds: list[dict[str, str]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates_by_fold: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        candidates_by_fold.setdefault(str(candidate["fold_id"]), []).append(candidate)

    fold_sources = []
    for fold in optimization_folds:
        fold_id = str(fold["id"])
        fold_from = pd.Timestamp(fold["from"])
        fold_to = pd.Timestamp(fold["to"])
        covering = [
            candidate
            for candidate in candidates_by_fold.get(fold_id, [])
            if candidate["first_timestamp"] <= fold_from and candidate["last_timestamp"] >= fold_to
        ]
        covering.sort(
            key=lambda candidate: (
                candidate["last_timestamp"] - candidate["first_timestamp"],
                candidate["path"],
            )
        )
        selected = covering[0] if covering else None
        fold_sources.append(
            {
                "fold_id": fold_id,
                "window_from": str(fold["from"]),
                "window_to": str(fold["to"]),
                "source_dir": selected["path"] if selected else "",
                "source_first_timestamp": selected["first_timestamp"].strftime("%Y-%m-%d %H:%M:%S") if selected else "",
                "source_last_timestamp": selected["last_timestamp"].strftime("%Y-%m-%d %H:%M:%S") if selected else "",
                "source_manifest_ref": selected["source_manifest_ref"] if selected else "",
                "source_wf5_manifest_ref": selected["source_wf5_manifest_ref"] if selected else "",
                "available": selected is not None,
            }
        )
    return fold_sources


def _format_step11_commands(
    fold_sources: list[dict[str, Any]],
    pack_meta_path: Path,
    artifact_root: Path,
) -> list[str]:
    commands = []
    for fold in fold_sources:
        if not fold["available"]:
            continue
        fold_dir = artifact_root / "step11" / fold["fold_id"]
        commands.append(
            "python src/ml/step11_labeling.py "
            f'--input "{fold["source_dir"]}" '
            f'--pack-meta "{pack_meta_path}" '
            f'--output-dir "{fold_dir}" '
            f'--from "{fold["window_from"]}" '
            f'--to "{fold["window_to"]}"'
        )
    return commands


def build_packet(run_dir: Path, step14_dir: Path | None) -> tuple[dict[str, Any], Path, Path]:
    project_root = _determine_project_root(run_dir)
    run_manifest = _load_json(run_dir / "run_manifest.json")
    if step14_dir is None:
        step14_dir = resolve_step14_dir(project_root, str(run_manifest.get("pack_id", "")))
    elif not step14_dir.is_absolute():
        step14_dir = project_root / step14_dir

    if not step14_dir.exists():
        raise FileNotFoundError(f"STEP14 artifact directory not found: {step14_dir}")

    kpi_summary = _load_json(run_dir / "40_kpi" / "kpi_summary.json")
    branch_packet = _load_json(run_dir / "60_decision" / "branch_decision_packet.json")
    validator_report = _load_json(run_dir / "50_validator" / "validator_report.json")
    manifest_path, campaign_manifest = _resolve_campaign_manifest(run_dir, run_manifest)

    selection_report = _load_json(step14_dir / "stage1_selection_report.json")
    handoff_manifest = _load_json(step14_dir / "handoff_manifest.json")
    selected_stage1_training = _load_json(step14_dir / "selected_stage1" / "training_metadata.json")
    selected_stage1_smoke = _load_json(step14_dir / "selected_stage1_smoke.json")
    validation_metadata = _load_json(step14_dir / "validation_metadata.json")
    regime_summary = pd.read_csv(step14_dir / "selected_stage1" / "regime_summary.csv")

    reports_dir = _resolve_reports_dir(project_root, manifest_path, campaign_manifest)
    reports_dir.mkdir(parents=True, exist_ok=True)

    windows = campaign_manifest.get("windows") or {}
    optimization_folds = ((windows.get("optimization_folds") or {}).get("folds")) or []
    benchmark_window = windows.get("benchmark") or {}
    oos_window = windows.get("oos_validation") or {}

    source_meta = selected_stage1_training.get("source_step11_metadata") or {}
    source_start = pd.Timestamp(source_meta.get("data_start"))
    source_end = pd.Timestamp(source_meta.get("data_end"))
    source_input_dir = str(Path(source_meta["input_files"][0]).parent) if source_meta.get("input_files") else ""

    weakest = regime_summary.sort_values(
        ["val_macro_f1", "val_cand0_pass_recall", "regime_id"],
        ascending=[True, True, True],
    )
    weakest_rows = [
        {
            "regime_id": int(row["regime_id"]),
            "val_macro_f1": float(row["val_macro_f1"]),
            "val_cand0_pass_recall": float(row["val_cand0_pass_recall"]),
        }
        for _, row in weakest.head(3).iterrows()
    ]

    artifact_root = _artifact_root(project_root, run_manifest.get("campaign_id", ""), run_manifest.get("run_id", ""))
    pack_meta_path = resolve_pack_meta_path(project_root, str(run_manifest.get("pack_id", "")))
    candidate_log_dirs = _discover_bar_log_directories(
        project_root,
        campaign_id=str(run_manifest.get("campaign_id", "")),
        source_run_id=str(run_manifest.get("run_id", "")),
    )
    fold_sources = _select_fold_sources(optimization_folds, candidate_log_dirs)
    available_fold_ids = [fold["fold_id"] for fold in fold_sources if fold["available"]]
    missing_fold_ids = [fold["fold_id"] for fold in fold_sources if not fold["available"]]
    step11_fold_commands = _format_step11_commands(
        fold_sources,
        pack_meta_path,
        artifact_root,
    )
    step11_union_dirs = [artifact_root / "step11" / fold["fold_id"] for fold in fold_sources if fold["available"]]
    step11_union_dir = artifact_root / "step11_union"
    step12_dir = artifact_root / "step12_stage1_refresh"
    step13_dir = artifact_root / "step13_stage2_incumbent_refit"
    step14_out_dir = artifact_root / WF5_STAGE14_DIRNAME

    readiness_blockers = []
    if branch_packet.get("primary_branch") != "ML-first":
        readiness_blockers.append("branch_not_ml_first")
    if validator_report.get("verdict") != "PASS":
        readiness_blockers.append("validator_not_pass")
    if branch_packet.get("admissibility", {}).get("runtime_blockers"):
        readiness_blockers.append("runtime_blockers_present")
    if not bool(validation_metadata.get("lineage_audit", {}).get("passed", False)):
        readiness_blockers.append("step14_lineage_audit_failed")
    if not bool(validation_metadata.get("outer_split_audit", {}).get("passed", False)):
        readiness_blockers.append("step14_outer_split_audit_failed")
    if not bool(selected_stage1_smoke.get("all_passed", False)):
        readiness_blockers.append("selected_stage1_smoke_failed")
    if missing_fold_ids:
        readiness_blockers.append("missing_fold_input_sources")

    candidate_rows = selection_report.get("candidate_rows", [])
    selected_candidate_id = str(selection_report.get("provisional_winner_candidate_id", ""))
    selected_candidate_row = next(
        (row for row in candidate_rows if str(row.get("candidate_id", "")) == selected_candidate_id),
        {},
    )
    min_inner_fold_cand0 = float(selected_candidate_row.get("min_cand0_pass_recall", 0.0))

    packet = {
        "schema_version": "1.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": run_manifest.get("campaign_id", ""),
        "source_run_id": run_manifest.get("run_id", ""),
        "primary_branch": branch_packet.get("primary_branch", ""),
        "confidence": branch_packet.get("confidence", "low"),
        "wf5_ready": len(readiness_blockers) == 0,
        "readiness_blockers": readiness_blockers,
        "benchmark_diagnosis": {
            "total_pnl": branch_packet["headline_metrics"]["total_pnl"],
            "global_profit_factor": branch_packet["headline_metrics"]["global_profit_factor"],
            "global_win_rate": branch_packet["headline_metrics"]["global_win_rate"],
            "max_equity_dd_pct": branch_packet["headline_metrics"]["max_equity_dd_pct"],
            "gate_regret_mean": branch_packet["headline_metrics"]["gate_regret_mean"],
            "gate_block_rate_candidate_bars": branch_packet["headline_metrics"]["gate_block_rate_candidate_bars"],
            "candidate_margin_p10": kpi_summary["signal"]["candidate_margin_p10"],
            "long_profit_factor": ((kpi_summary.get("portfolio") or {}).get("direction_breakdown") or {}).get("LONG", {}).get("profit_factor"),
            "short_profit_factor": ((kpi_summary.get("portfolio") or {}).get("direction_breakdown") or {}).get("SHORT", {}).get("profit_factor"),
        },
        "campaign_windows": {
            "optimization_folds": [
                {
                    "id": str(fold.get("id", "")),
                    "from": str(fold.get("from", "")),
                    "to": str(fold.get("to", "")),
                    "note": str(fold.get("note", "")),
                }
                for fold in optimization_folds
            ],
            "benchmark": {
                "from": str(benchmark_window.get("from", "")),
                "to": str(benchmark_window.get("to", "")),
            },
            "oos_validation": {
                "from": str(oos_window.get("from", "")),
                "to": str(oos_window.get("to", "")),
            },
        },
        "incumbent_stage1": {
            "step14_dir": str(step14_dir),
            "selected_candidate_id": selected_candidate_id,
            "selected_candidate_source": str(selection_report.get("provisional_winner_source", "")),
            "eligible_candidate_count": int(selection_report.get("eligible_candidate_count", 0)),
            "used_control_fallback": bool(selection_report.get("used_control_fallback", False)),
            "final_handoff_is_baseline": bool((handoff_manifest.get("stage1") or {}).get("final_handoff_is_baseline", False)),
            "architecture_baseline": selected_stage1_training.get("architecture_baseline", {}),
            "training_config": selected_stage1_training.get("training_config", {}),
            "source_data_window": {
                "from": source_meta.get("data_start", ""),
                "to": source_meta.get("data_end", ""),
            },
            "source_input_dir": source_input_dir,
            "source_data_within_optimization_corpus": _within_any_window(source_start, source_end, optimization_folds),
            "source_data_overlaps_oos_validation": _overlaps_window(source_start, source_end, oos_window) if oos_window else False,
            "total_labeled_samples": int(selected_stage1_training.get("total_labeled_samples", 0)),
            "guardrail": {
                "name": str((selection_report.get("eligibility_guardrail") or {}).get("name", "")),
                "threshold": float((selection_report.get("eligibility_guardrail") or {}).get("threshold", 0.0)),
                "min_inner_fold_cand0_pass_recall": float(min_inner_fold_cand0),
                "outer_refit_cand0_pass_recall_min": float((selected_stage1_training.get("acceptance") or {}).get("A2_cand0_pass_recall_min", 0.0)),
                "inner_selection_pass": int(selection_report.get("eligible_candidate_count", 0)) > 0,
                "outer_refit_pass": bool((selected_stage1_training.get("acceptance") or {}).get("A2_pass", False)),
            },
            "outer_split": {
                "embargo_bars": int((selected_stage1_training.get("split_plan") or {}).get("embargo_bars", 0)),
                "train_count": int((selected_stage1_training.get("split_plan") or {}).get("train_count", 0)),
                "val_count": int((selected_stage1_training.get("split_plan") or {}).get("val_count", 0)),
                "train_end_time": str((selected_stage1_training.get("split_plan") or {}).get("train_end_time", "")),
                "val_start_time": str((selected_stage1_training.get("split_plan") or {}).get("val_start_time", "")),
                "no_time_leakage": bool((selected_stage1_training.get("split_plan") or {}).get("no_time_leakage", False)),
            },
            "lineage_audit_passed": bool((validation_metadata.get("lineage_audit") or {}).get("passed", False)),
            "outer_split_audit_passed": bool((validation_metadata.get("outer_split_audit") or {}).get("passed", False)),
            "smoke_pass": bool(selected_stage1_smoke.get("all_passed", False)),
        },
        "regime_focus": {
            "weakest_regime_id": weakest_rows[0]["regime_id"] if weakest_rows else -1,
            "weakest_regime_val_macro_f1": weakest_rows[0]["val_macro_f1"] if weakest_rows else 0.0,
            "weakest_regime_val_cand0_pass_recall": weakest_rows[0]["val_cand0_pass_recall"] if weakest_rows else 0.0,
            "weakest_regimes": weakest_rows,
        },
        "launch_plan": {
            "artifact_root": _repo_ref(project_root, artifact_root),
            "pack_meta_path": _repo_ref(project_root, pack_meta_path),
            "bar_log_input_dir": source_input_dir if len(set(fold["source_dir"] for fold in fold_sources if fold["available"])) == 1 else "",
            "fold_sources": fold_sources,
            "available_fold_ids": available_fold_ids,
            "missing_fold_ids": missing_fold_ids,
            "step11_fold_commands": step11_fold_commands,
            "step11_union_command": (
                "python tools/build_step11_fold_union.py "
                f'--output-dir "{step11_union_dir}" '
                + " ".join(f'"{fold_dir}"' for fold_dir in step11_union_dirs)
            ) if not missing_fold_ids else "",
            "step12_command": (
                "python src/ml/step12_training.py "
                f'--input-dir "{step11_union_dir}" '
                f'--output-dir "{step12_dir}" '
                "--fail-on-acceptance"
            ) if not missing_fold_ids else "",
            "step13_command": (
                "python src/ml/step13_training.py "
                f'--step11-dir "{step11_union_dir}" '
                f'--step12-dir "{step12_dir}" '
                f'--output-dir "{step13_dir}" '
                "--fail-on-acceptance"
            ) if not missing_fold_ids else "",
            "step14_command": (
                "python src/ml/step14_training.py "
                f'--step11-dir "{step11_union_dir}" '
                f'--step12-dir "{step12_dir}" '
                f'--step13-dir "{step13_dir}" '
                f'--output-dir "{step14_out_dir}" '
                "--fail-on-acceptance"
            ) if not missing_fold_ids else "",
        },
        "recommended_focus": [
            "Build Stage1 corpus only from frozen optimization_folds; do not reuse the current OOS-era training window.",
            "Keep `min_cand0_pass_recall >= 0.5` as the hard Stage1 guardrail during WF5 search.",
            "Expand Stage1 architecture/search before any EA threshold sweep because benchmark losses are broad across both directional books.",
            "Re-run Step14 selection on the merged fold corpus before opening Stage2 retune.",
        ],
        "source_artifacts": {
            "campaign_manifest": str(manifest_path),
            "kpi_summary": str(run_dir / "40_kpi" / "kpi_summary.json"),
            "branch_decision_packet": str(run_dir / "60_decision" / "branch_decision_packet.json"),
            "validator_report": str(run_dir / "50_validator" / "validator_report.json"),
            "stage1_selection_report": str(step14_dir / "stage1_selection_report.json"),
            "handoff_manifest": str(step14_dir / "handoff_manifest.json"),
            "selected_stage1_training_metadata": str(step14_dir / "selected_stage1" / "training_metadata.json"),
            "selected_stage1_smoke": str(step14_dir / "selected_stage1_smoke.json"),
            "validation_metadata": str(step14_dir / "validation_metadata.json"),
            "regime_summary": str(step14_dir / "selected_stage1" / "regime_summary.csv"),
        },
    }

    schema_path = project_root / "_coord" / "ops" / "schemas" / "stage1_refresh_packet.schema.json"
    schema_errors = _validate_against_schema(packet, schema_path)
    if schema_errors:
        raise ValueError("stage1_refresh_packet schema validation failed: " + "; ".join(schema_errors))

    stem = f"stage1_refresh_packet_{run_manifest.get('run_id', '')}"
    json_path = reports_dir / f"{stem}.json"
    md_path = reports_dir / f"{stem}.md"
    json_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    md_lines = [
        f"# Stage1 Refresh Packet - {packet['source_run_id']}",
        "",
        f"- Primary branch: `{packet['primary_branch']}`",
        f"- Confidence: `{packet['confidence']}`",
        f"- WF5 ready: `{packet['wf5_ready']}`",
    ]
    if packet["readiness_blockers"]:
        md_lines.append(f"- Readiness blockers: {', '.join(packet['readiness_blockers'])}")
    md_lines.extend([
        "",
        "## Benchmark Diagnosis",
        f"- Total PnL: {packet['benchmark_diagnosis']['total_pnl']:.2f}",
        f"- Global PF: {(packet['benchmark_diagnosis']['global_profit_factor'] or 0.0):.4f}",
        f"- Global WR: {packet['benchmark_diagnosis']['global_win_rate']:.2%}",
        f"- Max equity DD: {packet['benchmark_diagnosis']['max_equity_dd_pct']:.2f}%",
        f"- Candidate margin p10: {packet['benchmark_diagnosis']['candidate_margin_p10']:.4f}",
        "",
        "## Incumbent Stage1",
        f"- Selected candidate: `{packet['incumbent_stage1']['selected_candidate_id']}` ({packet['incumbent_stage1']['selected_candidate_source']})",
        f"- Eligible challengers: {packet['incumbent_stage1']['eligible_candidate_count']}",
        f"- Used control fallback: {packet['incumbent_stage1']['used_control_fallback']}",
        f"- Source data window: {packet['incumbent_stage1']['source_data_window']['from']} -> {packet['incumbent_stage1']['source_data_window']['to']}",
        f"- Within optimization corpus: {packet['incumbent_stage1']['source_data_within_optimization_corpus']}",
        f"- Overlaps OOS window: {packet['incumbent_stage1']['source_data_overlaps_oos_validation']}",
        f"- Outer refit guardrail pass: {packet['incumbent_stage1']['guardrail']['outer_refit_pass']}",
        "",
        "## Fold Inputs",
    ])
    for fold in packet["launch_plan"]["fold_sources"]:
        if fold["available"]:
            md_lines.append(
                f"- {fold['fold_id']}: {fold['source_dir']} ({fold['source_first_timestamp']} -> {fold['source_last_timestamp']})"
            )
        else:
            md_lines.append(f"- {fold['fold_id']}: MISSING")
    md_lines.extend([
        "",
        "## Weakest Regimes",
    ])
    for row in packet["regime_focus"]["weakest_regimes"]:
        md_lines.append(
            f"- Regime {row['regime_id']}: val_macro_f1={row['val_macro_f1']:.4f}, val_cand0_pass_recall={row['val_cand0_pass_recall']:.4f}"
        )
    md_lines.extend(["", "## Launch Plan"])
    for command in packet["launch_plan"]["step11_fold_commands"]:
        md_lines.append(f"- `{command}`")
    if packet["launch_plan"]["step11_union_command"]:
        md_lines.append(f"- `{packet['launch_plan']['step11_union_command']}`")
        md_lines.append(f"- `{packet['launch_plan']['step12_command']}`")
        md_lines.append(f"- `{packet['launch_plan']['step13_command']}`")
        md_lines.append(f"- `{packet['launch_plan']['step14_command']}`")
    else:
        md_lines.append("- Full union / Step12-14 launch blocked until every optimization fold has a source directory.")
    md_lines.extend(["", "## Recommended Focus"])
    for item in packet["recommended_focus"]:
        md_lines.append(f"- {item}")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return packet, json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build WF5 Stage1 refresh kickoff packet.")
    parser.add_argument("run_dir", type=Path, help="Path to runs/RUN_<ts>/")
    parser.add_argument(
        "--step14-dir",
        type=Path,
        default=None,
        help="Override accepted STEP14 artifact directory. Default: resolve from control_pack_registry.yaml via run_manifest.pack_id",
    )
    args = parser.parse_args()

    packet, json_path, _ = build_packet(args.run_dir, args.step14_dir)
    print(f"Stage1 refresh packet: {json_path}")
    print(f"  WF5 ready:        {packet['wf5_ready']}")
    print(f"  Selected source:  {packet['incumbent_stage1']['selected_candidate_source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
