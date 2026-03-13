"""
run_stage1_fold_source_pipeline.py - Generate WF5 fold sources from MT5 and run STEP11.

Usage:
    python tools/run_stage1_fold_source_pipeline.py <run_dir> [--fold-id <id> ...]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
DEFAULT_TESTER_ROOT = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Tester" / "D0E8209F77C8CF37AD8BF550E51FF075"


@dataclass(frozen=True)
class FoldWindow:
    fold_id: str
    window_from: str
    window_to: str

    @property
    def tester_from_date(self) -> str:
        return self.window_from.split()[0]

    @property
    def tester_to_date(self) -> str:
        base = datetime.strptime(self.window_to.split()[0], "%Y.%m.%d")
        return (base + timedelta(days=1)).strftime("%Y.%m.%d")


def _determine_project_root(path: Path) -> Path:
    root = path.resolve()
    while root.name != "PROJECT_triple_sigma" and root.parent != root:
        root = root.parent
    return root


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


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


def _load_optimization_folds(campaign_manifest: dict[str, Any]) -> list[FoldWindow]:
    windows = campaign_manifest.get("windows") or {}
    folds = ((windows.get("optimization_folds") or {}).get("folds")) or []
    result: list[FoldWindow] = []
    for fold in folds:
        result.append(
            FoldWindow(
                fold_id=str(fold["id"]),
                window_from=str(fold["from"]),
                window_to=str(fold["to"]),
            )
        )
    if not result:
        raise ValueError("campaign manifest has no optimization_folds")
    return result


def _read_text(path: Path) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _build_generated_preset(base_preset_path: Path, fold: FoldWindow, report_path: Path) -> str:
    output_lines = []
    for raw_line in _read_text(base_preset_path).splitlines():
        if raw_line.startswith("FromDate="):
            output_lines.append(f"FromDate={fold.tester_from_date}")
        elif raw_line.startswith("ToDate="):
            output_lines.append(f"ToDate={fold.tester_to_date}")
        elif raw_line.startswith("Report="):
            output_lines.append(f"Report={report_path}")
        elif raw_line.startswith("ReplaceReport="):
            output_lines.append("ReplaceReport=1")
        elif raw_line.startswith("ShutdownTerminal="):
            output_lines.append("ShutdownTerminal=1")
        else:
            output_lines.append(raw_line)
    return "\n".join(output_lines) + "\n"


def _discover_agent_dirs(tester_root: Path) -> list[Path]:
    return sorted(path for path in tester_root.glob("Agent-*") if path.is_dir())


def _source_log_dir(agent_dir: Path) -> Path:
    return agent_dir / "MQL5" / "Files" / "triple_sigma_logs"


def _agent_logs_dir(agent_dir: Path) -> Path:
    return agent_dir / "logs"


def _clear_source_logs(agent_dirs: list[Path]) -> None:
    for agent_dir in agent_dirs:
        source_dir = _source_log_dir(agent_dir)
        if not source_dir.exists():
            continue
        for child in source_dir.iterdir():
            if child.is_file():
                child.unlink()


def _snapshot_log_sizes(agent_dirs: list[Path]) -> dict[str, int]:
    snapshot: dict[str, int] = {}
    for agent_dir in agent_dirs:
        logs_dir = _agent_logs_dir(agent_dir)
        if not logs_dir.exists():
            continue
        for log_path in logs_dir.glob("*.log"):
            snapshot[str(log_path)] = log_path.stat().st_size
    return snapshot


def _select_used_agent(agent_dirs: list[Path]) -> Path:
    candidates = []
    for agent_dir in agent_dirs:
        source_dir = _source_log_dir(agent_dir)
        bar_logs = sorted(source_dir.glob("bar_log_*.csv")) if source_dir.exists() else []
        if not bar_logs:
            continue
        newest = max(path.stat().st_mtime for path in bar_logs)
        candidates.append((newest, agent_dir))
    if not candidates:
        raise RuntimeError("No agent produced bar_log_*.csv after MT5 run")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _select_agent_log(agent_dir: Path, snapshot_sizes: dict[str, int]) -> tuple[Path, int]:
    logs_dir = _agent_logs_dir(agent_dir)
    if not logs_dir.exists():
        raise FileNotFoundError(f"agent logs directory missing: {logs_dir}")
    candidates = sorted(logs_dir.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no tester log files under {logs_dir}")
    chosen = candidates[0]
    offset = snapshot_sizes.get(str(chosen), 0)
    return chosen, offset


def _artifact_name(campaign_id: str, run_id: str, fold_id: str) -> str:
    return f"{campaign_id}_{run_id}_{fold_id}_step21_control_trade_source"


def _artifact_root(project_root: Path, campaign_id: str, run_id: str) -> Path:
    return project_root / "_coord" / "artifacts" / f"{campaign_id}_{run_id}_wf5_stage1_refresh"


def _run_subprocess(args: list[str | Path], cwd: Path) -> None:
    string_args = [str(arg) for arg in args]
    subprocess.run(string_args, cwd=str(cwd), check=True)


def _build_summary_text(
    fold: FoldWindow,
    generated_preset_path: Path,
    artifact_dir: Path,
    agent_dir: Path,
    agent_log_path: Path,
    step11_dir: Path,
    package_manifest: dict[str, Any],
    step11_metadata: dict[str, Any],
) -> str:
    trade_stats = package_manifest.get("trade_log_stats") or {}
    return "\n".join(
        [
            f"# WF5 {fold.fold_id} Step21 Control Trade Source",
            "",
            "Window:",
            f"- tester date window: `{fold.tester_from_date}` -> `{fold.tester_to_date}`",
            f"- exact STEP11 window: `{fold.window_from}` -> `{fold.window_to}`",
            "",
            "Lineage:",
            f"- generated preset: `{generated_preset_path}`",
            f"- packaged artifact: `{artifact_dir}`",
            f"- source agent: `{agent_dir}`",
            f"- agent log: `{agent_log_path}`",
            f"- STEP11 output: `{step11_dir}`",
            "",
            "Packaged artifact stats:",
            f"- trade_log rows: `{trade_stats.get('rows', 0)}`",
            f"- event_type_counts: `{trade_stats.get('event_type_counts', {})}`",
            f"- exit_reason_counts: `{trade_stats.get('exit_reason_counts', {})}`",
            "",
            "STEP11 stats:",
            f"- total_bars: `{step11_metadata.get('total_bars')}`",
            f"- total_labeled_samples: `{step11_metadata.get('total_labeled_samples')}`",
            f"- forced_pass_count: `{step11_metadata.get('forced_pass_count')}`",
            f"- label_distribution: `{step11_metadata.get('label_distribution')}`",
            "",
        ]
    )


def _run_fold(
    *,
    project_root: Path,
    run_dir: Path,
    fold: FoldWindow,
    campaign_id: str,
    run_id: str,
    reports_dir: Path,
    base_preset_path: Path,
    terminal_path: Path,
    tester_root: Path,
    package_script_path: Path,
    pack_meta_path: Path,
) -> dict[str, str]:
    artifact_dir = project_root / "_coord" / "artifacts" / _artifact_name(campaign_id, run_id, fold.fold_id)
    artifact_dir.parent.mkdir(parents=True, exist_ok=True)

    generated_preset_dir = reports_dir / "generated_presets"
    generated_report_dir = reports_dir / "generated_reports"
    fold_summary_dir = reports_dir / "fold_sources"
    generated_preset_dir.mkdir(parents=True, exist_ok=True)
    generated_report_dir.mkdir(parents=True, exist_ok=True)
    fold_summary_dir.mkdir(parents=True, exist_ok=True)
    generated_preset_path = generated_preset_dir / f"{artifact_dir.name}.ini"
    generated_report_path = generated_report_dir / f"{artifact_dir.name}_report"
    step11_dir = _artifact_root(project_root, campaign_id, run_id) / "step11" / fold.fold_id

    preset_text = _build_generated_preset(base_preset_path, fold, generated_report_path)
    _write_text(generated_preset_path, preset_text)

    agent_dirs = _discover_agent_dirs(tester_root)
    if not agent_dirs:
        raise FileNotFoundError(f"no tester agents found under {tester_root}")

    _clear_source_logs(agent_dirs)
    snapshot_sizes = _snapshot_log_sizes(agent_dirs)
    _run_subprocess([terminal_path, f"/config:{generated_preset_path}"], project_root)

    agent_dir = _select_used_agent(agent_dirs)
    source_log_dir = _source_log_dir(agent_dir)
    agent_log_path, log_offset = _select_agent_log(agent_dir, snapshot_sizes)

    _run_subprocess(
        [
            sys.executable,
            package_script_path,
            "--artifact-dir",
            artifact_dir,
            "--source-log-dir",
            source_log_dir,
            "--agent-log",
            agent_log_path,
            "--log-offset",
            str(log_offset),
            "--title",
            f"WF5 {fold.fold_id} Step21 Control Trade Source Artifact",
            "--preset",
            generated_preset_path,
            "--summary",
            fold_summary_dir / f"{fold.fold_id}.md",
            "--validation-class",
            "wf5-fold-source",
            "--trigger-source",
            "step21 control-trade baseline replay",
            "--baseline-compare",
            base_preset_path,
        ],
        project_root,
    )

    _run_subprocess(
        [
            sys.executable,
            project_root / "src" / "ml" / "step11_labeling.py",
            "--input",
            artifact_dir,
            "--pack-meta",
            pack_meta_path,
            "--output-dir",
            step11_dir,
            "--from",
            fold.window_from,
            "--to",
            fold.window_to,
        ],
        project_root,
    )

    package_manifest = _load_json(artifact_dir / "manifest.json")
    step11_metadata = _load_json(step11_dir / "metadata.json")

    fold_summary_path = fold_summary_dir / f"{fold.fold_id}.md"
    _write_text(
        fold_summary_path,
        _build_summary_text(
            fold,
            generated_preset_path,
            artifact_dir,
            agent_dir,
            agent_log_path,
            step11_dir,
            package_manifest,
            step11_metadata,
        ),
    )

    wf5_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": campaign_id,
        "source_run_id": run_id,
        "fold_id": fold.fold_id,
        "window_from": fold.window_from,
        "window_to": fold.window_to,
        "generated_preset_path": str(generated_preset_path),
        "generated_report_path": str(generated_report_path),
        "artifact_dir": str(artifact_dir),
        "step11_dir": str(step11_dir),
        "tester_root": str(tester_root),
        "selected_agent_dir": str(agent_dir),
        "selected_agent_log": str(agent_log_path),
        "package_script_path": str(package_script_path),
        "base_preset_path": str(base_preset_path),
        "package_manifest_ref": str(artifact_dir / "manifest.json"),
        "step11_metadata_ref": str(step11_dir / "metadata.json"),
        "step11_total_labeled_samples": int(step11_metadata["total_labeled_samples"]),
    }
    _write_text(artifact_dir / "wf5_fold_source_manifest.json", json.dumps(wf5_manifest, indent=2))

    return {
        "fold_id": fold.fold_id,
        "artifact_dir": str(artifact_dir),
        "step11_dir": str(step11_dir),
        "summary_path": str(fold_summary_path),
        "samples": str(step11_metadata["total_labeled_samples"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate WF5 fold sources via MT5 and run STEP11.")
    parser.add_argument("run_dir", type=Path, help="Campaign run directory")
    parser.add_argument("--fold-id", action="append", dest="fold_ids", default=[], help="Optimization fold id to build (repeatable)")
    parser.add_argument("--base-preset", type=Path, default=Path("_coord/tester/step21/step21_tester_control_trade.ini"))
    parser.add_argument("--terminal", type=Path, default=DEFAULT_TERMINAL)
    parser.add_argument("--tester-root", type=Path, default=DEFAULT_TESTER_ROOT)
    parser.add_argument("--package-script", type=Path, default=Path("tools/package_step21_artifacts.py"))
    parser.add_argument("--pack-meta", type=Path, default=Path("_coord/artifacts/step15_export_q1_out/model_pack/pack_meta.csv"))
    parser.add_argument("--refresh-packet", action="store_true", default=True)
    parser.add_argument("--skip-packet-refresh", action="store_true")
    parser.add_argument("--build-union", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    project_root = _determine_project_root(run_dir)
    run_manifest = _load_json(run_dir / "run_manifest.json")
    manifest_path, campaign_manifest = _resolve_campaign_manifest(run_dir, run_manifest)
    reports_dir = _resolve_reports_dir(project_root, manifest_path, campaign_manifest)
    reports_dir.mkdir(parents=True, exist_ok=True)

    terminal_path = args.terminal if args.terminal.is_absolute() else project_root / args.terminal
    if not terminal_path.exists():
        raise FileNotFoundError(f"terminal executable not found: {terminal_path}")

    base_preset_path = args.base_preset if args.base_preset.is_absolute() else project_root / args.base_preset
    package_script_path = args.package_script if args.package_script.is_absolute() else project_root / args.package_script
    pack_meta_path = args.pack_meta if args.pack_meta.is_absolute() else project_root / args.pack_meta

    all_folds = _load_optimization_folds(campaign_manifest)
    fold_map = {fold.fold_id: fold for fold in all_folds}
    selected_fold_ids = args.fold_ids or [fold.fold_id for fold in all_folds]
    selected_folds = [fold_map[fold_id] for fold_id in selected_fold_ids]

    results = []
    for fold in selected_folds:
        results.append(
            _run_fold(
                project_root=project_root,
                run_dir=run_dir,
                fold=fold,
                campaign_id=str(run_manifest["campaign_id"]),
                run_id=str(run_manifest["run_id"]),
                reports_dir=reports_dir,
                base_preset_path=base_preset_path,
                terminal_path=terminal_path,
                tester_root=args.tester_root,
                package_script_path=package_script_path,
                pack_meta_path=pack_meta_path,
            )
        )

    should_refresh = bool(args.refresh_packet) and not args.skip_packet_refresh
    if should_refresh:
        _run_subprocess([sys.executable, project_root / "tools" / "build_stage1_refresh_packet.py", run_dir], project_root)

    if args.build_union:
        union_root = _artifact_root(project_root, str(run_manifest["campaign_id"]), str(run_manifest["run_id"]))
        step11_dirs = [union_root / "step11" / fold.fold_id for fold in all_folds]
        _run_subprocess(
            [
                sys.executable,
                project_root / "tools" / "build_step11_fold_union.py",
                "--output-dir",
                union_root / "step11_union",
                *step11_dirs,
            ],
            project_root,
        )

    print(json.dumps({"status": "ok", "fold_results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
