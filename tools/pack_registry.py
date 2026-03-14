from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


WINDOWS_ABS_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def determine_project_root(path: Path) -> Path:
    root = path.resolve()
    while root.name != "PROJECT_triple_sigma" and root.parent != root:
        root = root.parent
    return root


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_repo_path(project_root: Path, ref: str | Path) -> Path:
    raw = str(ref).strip()
    if not raw:
        return Path()

    direct = Path(raw)
    if direct.exists():
        return direct

    normalized = Path(raw.replace("\\", "/"))
    if normalized.exists():
        return normalized

    if WINDOWS_ABS_PATH_PATTERN.match(raw):
        return normalized

    if normalized.is_absolute():
        return normalized

    return project_root / normalized


def _load_registry(project_root: Path) -> dict[str, Any]:
    registry_path = project_root / "_coord" / "ops" / "control_pack_registry.yaml"
    if not registry_path.exists():
        raise FileNotFoundError(f"control pack registry not found: {registry_path}")
    with open(registry_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def resolve_pack_registry_entry(project_root: Path, pack_id: str) -> dict[str, Any]:
    registry = _load_registry(project_root)
    for entry in registry.values():
        if isinstance(entry, dict) and str(entry.get("pack", "")).strip() == pack_id:
            return entry
    raise KeyError(f"pack_id not found in control_pack_registry.yaml: {pack_id}")


def _resolve_export_manifest_path(project_root: Path, pack_id: str) -> Path | None:
    entry = resolve_pack_registry_entry(project_root, pack_id)
    parity_ref = str(entry.get("parity_evidence", "")).strip()
    if not parity_ref:
        return None

    parity_path = resolve_repo_path(project_root, parity_ref)
    candidates = []
    if parity_path.name == "export_manifest.json":
        candidates.append(parity_path)
    if parity_path.name == "export_validation_report.json":
        candidates.append(parity_path.with_name("export_manifest.json"))
    candidates.append(parity_path.parent / "export_manifest.json")

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return None


def resolve_step14_dir(project_root: Path, pack_id: str) -> Path:
    entry = resolve_pack_registry_entry(project_root, pack_id)
    selection = entry.get("selection_evidence") or {}
    stage1_ref = str(selection.get("stage1", "")).strip()
    if not stage1_ref:
        raise FileNotFoundError(f"selection_evidence.stage1 missing for pack_id {pack_id}")

    stage1_report_path = resolve_repo_path(project_root, stage1_ref)
    if not stage1_report_path.exists():
        raise FileNotFoundError(
            f"selection_evidence.stage1 not found for pack_id {pack_id}: {stage1_report_path}"
        )
    return stage1_report_path.parent


def resolve_retained_pack_dir(project_root: Path, pack_id: str) -> Path | None:
    export_manifest_path = _resolve_export_manifest_path(project_root, pack_id)
    if export_manifest_path is None:
        return None

    export_manifest = load_json(export_manifest_path)
    model_pack_ref = str(export_manifest.get("model_pack_dir", "")).strip()
    if model_pack_ref:
        model_pack_dir = resolve_repo_path(project_root, model_pack_ref)
        if model_pack_dir.exists():
            return model_pack_dir

    fallback_dir = export_manifest_path.parent / "model_pack"
    if fallback_dir.exists():
        return fallback_dir
    return None


def resolve_pack_meta_path(project_root: Path, pack_id: str) -> Path:
    retained_pack_dir = resolve_retained_pack_dir(project_root, pack_id)
    if retained_pack_dir is None:
        raise FileNotFoundError(
            f"Could not resolve retained export pack directory for pack_id {pack_id}"
        )

    pack_meta_path = retained_pack_dir / "pack_meta.csv"
    if not pack_meta_path.exists():
        raise FileNotFoundError(f"retained pack_meta.csv not found: {pack_meta_path}")
    return pack_meta_path
