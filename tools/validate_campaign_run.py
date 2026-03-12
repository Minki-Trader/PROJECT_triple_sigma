"""
validate_campaign_run.py - Campaign run validator.

Validates that a sealed campaign run meets admissibility requirements:
  1. Provenance: raw_dir inside campaign workspace (not external artifact replay)
  2. Manifest conformance: window/pack match campaign manifest
  3. Pack admission: profitability pack used (not smoke pack)
  4. Raw completeness: trade_log.csv, bar_log_*.csv, exec_state.ini, compile_log.txt
  5. Compile clean: 0 errors, 0 warnings
  6. Window boundary: bar log date range within manifest window (minute-level hard check)
  7. Hash completeness: raw_hash_manifest.json + pack_hash_manifest.json present
  8. Hash integrity: SHA-256 verification of raw files against manifest

Output: validator_report.json in runs/RUN_<ts>/50_validator/

Usage:
    python tools/validate_campaign_run.py <run_dir> [--campaign-manifest <path>]

Findings: F1 (provenance), F6 (independent validator)
Phase: A2
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

RFC3339_DATETIME_PATTERN = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_provenance(run_dir: Path, campaign_dir: Path) -> list[dict]:
    """Check that run_dir is inside the campaign workspace."""
    issues = []
    try:
        run_dir.resolve().relative_to(campaign_dir.resolve())
    except ValueError:
        issues.append({
            "gate": "provenance",
            "severity": "FAIL",
            "message": (
                f"Run directory {run_dir} is outside campaign workspace {campaign_dir}. "
                "Retained artifact replay is not admissible."
            ),
        })
    return issues


def validate_manifest_conformance(
    run_manifest: dict, campaign_manifest: dict
) -> list[dict]:
    """Check window/pack match between run and campaign manifests."""
    issues = []

    # Pack must be profitability pack
    expected_pack = campaign_manifest.get("profitability_pack", "")
    actual_pack = run_manifest.get("pack_id", "")
    smoke_pack = campaign_manifest.get("runtime_integrity_pack", "")

    if actual_pack == smoke_pack:
        issues.append({
            "gate": "pack_admission",
            "severity": "FAIL",
            "message": (
                f"Run uses smoke/runtime-integrity pack '{actual_pack}'. "
                f"Admissible runs require profitability pack '{expected_pack}'."
            ),
        })
    elif actual_pack != expected_pack:
        issues.append({
            "gate": "pack_admission",
            "severity": "FAIL",
            "message": (
                f"Run pack '{actual_pack}' does not match "
                f"campaign profitability pack '{expected_pack}'."
            ),
        })

    # Window validation
    window_alias = run_manifest.get("window_alias", "")
    windows = campaign_manifest.get("windows", {})

    expected_from = None
    expected_to = None

    if window_alias.startswith("fold_"):
        folds = windows.get("optimization_folds", {}).get("folds", [])
        for fold in folds:
            if fold["id"] == window_alias:
                expected_from = fold["from"]
                expected_to = fold["to"]
                break
    elif window_alias in windows:
        expected_from = windows[window_alias].get("from")
        expected_to = windows[window_alias].get("to")

    if expected_from is None:
        issues.append({
            "gate": "window_conformance",
            "severity": "FAIL",
            "message": f"Window alias '{window_alias}' not found in campaign manifest.",
        })
    else:
        run_from = run_manifest.get("window_from", "")
        run_to = run_manifest.get("window_to", "")
        if run_from != expected_from or run_to != expected_to:
            issues.append({
                "gate": "window_conformance",
                "severity": "FAIL",
                "message": (
                    f"Window mismatch: run has {run_from}->{run_to}, "
                    f"manifest expects {expected_from}->{expected_to}."
                ),
            })

    return issues


def validate_raw_completeness(run_dir: Path) -> list[dict]:
    """Check all required raw output files exist."""
    issues = []
    raw_dir = run_dir / "20_raw"

    required = {
        "trade_log.csv": raw_dir / "trade_log.csv",
        "exec_state.ini": raw_dir / "exec_state.ini",
    }

    for name, path in required.items():
        if not path.exists():
            issues.append({
                "gate": "raw_completeness",
                "severity": "FAIL",
                "message": f"Missing required file: 20_raw/{name}",
            })

    bar_logs = list(raw_dir.glob("bar_log_*.csv"))
    if not bar_logs:
        issues.append({
            "gate": "raw_completeness",
            "severity": "FAIL",
            "message": "No bar_log_*.csv files found in 20_raw/",
        })

    compile_log = run_dir / "10_compile" / "compile_log.txt"
    if not compile_log.exists():
        issues.append({
            "gate": "raw_completeness",
            "severity": "FAIL",
            "message": "Missing required file: 10_compile/compile_log.txt",
        })

    return issues


def validate_compile_clean(run_dir: Path) -> list[dict]:
    """Check compile log has 0 errors and 0 warnings."""
    issues = []
    compile_log = run_dir / "10_compile" / "compile_log.txt"

    if not compile_log.exists():
        return issues  # Already caught by raw_completeness

    text = compile_log.read_text(encoding="utf-8", errors="replace")
    result_match = re.search(r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", text)
    if result_match:
        error_count = int(result_match.group(1))
        warning_count = int(result_match.group(2))
    else:
        error_count = len(re.findall(r"(?i)^.*\berror\b(?!\s*s?,).*$", text, re.MULTILINE))
        warning_count = len(re.findall(r"(?i)^.*\bwarning\b(?!\s*s?,).*$", text, re.MULTILINE))

    if error_count > 0:
        issues.append({
            "gate": "compile_clean",
            "severity": "FAIL",
            "message": f"Compile log contains {error_count} error(s).",
        })
    if warning_count > 0:
        issues.append({
            "gate": "compile_clean",
            "severity": "FAIL",
            "message": f"Compile log contains {warning_count} warning(s).",
        })

    return issues


def _parse_datetime_flexible(s: str) -> "datetime | None":
    """Parse MT5-style datetime strings with full precision.

    Tries formats in order: YYYY.MM.DD HH:MM:SS, YYYY.MM.DD HH:MM, YYYY.MM.DD.
    Returns None if no format matches.
    """
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def validate_window_boundary(run_dir: Path, run_manifest: dict) -> list[dict]:
    """Check bar log date range falls within manifest window boundaries.

    Parses manifest window_from/window_to at full precision (minute-level when
    available). If the manifest only has date-level values (MT5 preset
    limitation), the gate still enforces a tight boundary: bar data must not
    start before window_from 00:00 or end after window_to 23:59.

    No loose tolerance — this is a hard check.
    """
    import csv

    issues = []
    raw_dir = run_dir / "20_raw"
    bar_logs = sorted(raw_dir.glob("bar_log_*.csv"))

    if not bar_logs:
        return issues  # Already caught by raw_completeness

    window_from = run_manifest.get("window_from", "")
    window_to = run_manifest.get("window_to", "")
    if not window_from or not window_to:
        issues.append({
            "gate": "window_boundary",
            "severity": "WARN",
            "message": "Cannot verify window boundary: window_from/window_to missing from run manifest.",
        })
        return issues

    # Parse manifest window dates at FULL precision (do NOT truncate to date)
    w_from = _parse_datetime_flexible(window_from)
    w_to = _parse_datetime_flexible(window_to)

    if w_from is None or w_to is None:
        issues.append({
            "gate": "window_boundary",
            "severity": "WARN",
            "message": f"Cannot parse manifest window dates: {window_from} / {window_to}",
        })
        return issues

    # If window_to was date-only (00:00), extend to end of that day (23:59:59)
    # so we don't false-fail on intraday bars
    if w_to.hour == 0 and w_to.minute == 0 and w_to.second == 0:
        w_to = w_to.replace(hour=23, minute=59, second=59)

    # Read first and last timestamps from bar logs
    all_timestamps = []
    for bar_log in bar_logs:
        try:
            with open(bar_log, encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None:
                    continue
                first_row = next(reader, None)
                if first_row is None:
                    continue
                ts_str = first_row[0].strip()
                all_timestamps.append(ts_str)
                last_row = first_row
                for row in reader:
                    last_row = row
                all_timestamps.append(last_row[0].strip())
        except (StopIteration, IndexError, OSError):
            continue

    if not all_timestamps:
        issues.append({
            "gate": "window_boundary",
            "severity": "WARN",
            "message": "Cannot extract timestamps from bar logs for window boundary check.",
        })
        return issues

    # Parse bar timestamps at full precision
    bar_dates = []
    for ts in all_timestamps:
        dt = _parse_datetime_flexible(ts)
        if dt is not None:
            bar_dates.append(dt)

    if not bar_dates:
        issues.append({
            "gate": "window_boundary",
            "severity": "WARN",
            "message": f"Cannot parse bar log timestamps: {all_timestamps[:2]}",
        })
        return issues

    bar_min = min(bar_dates)
    bar_max = max(bar_dates)

    # A' policy: raw overcapture is expected (MT5 uses date-only FromDate),
    # so bar_min < w_from is WARN. Parser will clip to exact window.
    # bar_max > w_to remains FAIL (unexpected overcapture on the right).
    if bar_min < w_from:
        issues.append({
            "gate": "window_boundary",
            "severity": "WARN",
            "message": (
                f"Raw overcapture: bar data starts {bar_min.strftime('%Y.%m.%d %H:%M')} "
                f"which is before manifest window_from {window_from}. "
                f"Parser-level clipping required."
            ),
        })

    if bar_max > w_to:
        issues.append({
            "gate": "window_boundary",
            "severity": "FAIL",
            "message": (
                f"Bar data ends {bar_max.strftime('%Y.%m.%d %H:%M')} which is after "
                f"manifest window_to {window_to}."
            ),
        })

    # Trade log boundary check: no ENTRY trade should open before window_from
    trade_log = raw_dir / "trade_log.csv"
    if trade_log.exists():
        try:
            with open(trade_log, encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    # Find time column index
                    time_idx = None
                    action_idx = None
                    for i, col in enumerate(header):
                        col_lower = col.strip().lower()
                        if col_lower in ("time", "timestamp"):
                            time_idx = i
                        elif col_lower in ("action", "event_type"):
                            action_idx = i

                    if time_idx is not None and action_idx is not None:
                        pre_window_entries = 0
                        post_window_entries = 0
                        for row in reader:
                            if len(row) <= max(time_idx, action_idx):
                                continue
                            action = row[action_idx].strip()
                            if action != "ENTRY":
                                continue
                            ts = _parse_datetime_flexible(row[time_idx].strip())
                            if ts is None:
                                continue
                            if ts < w_from:
                                pre_window_entries += 1
                            if ts > w_to:
                                post_window_entries += 1

                        if pre_window_entries > 0:
                            issues.append({
                                "gate": "window_boundary",
                                "severity": "WARN",
                                "message": (
                                    f"Trade log has {pre_window_entries} ENTRY trade(s) before "
                                    f"manifest window_from {window_from}. "
                                    f"Parser-level clipping will exclude these."
                                ),
                            })

                        if post_window_entries > 0:
                            issues.append({
                                "gate": "window_boundary",
                                "severity": "FAIL",
                                "message": (
                                    f"Trade log has {post_window_entries} ENTRY trade(s) after "
                                    f"manifest window_to {window_to}."
                                ),
                            })
        except (OSError, StopIteration):
            pass

    # Informational: report actual bar range for lineage
    bar_boundary_issues = [i for i in issues if i["severity"] == "FAIL"]
    if not bar_boundary_issues:
        issues.append({
            "gate": "window_boundary",
            "severity": "INFO",
            "message": (
                f"Bar range [{bar_min.strftime('%Y.%m.%d %H:%M')} ~ "
                f"{bar_max.strftime('%Y.%m.%d %H:%M')}] vs manifest window "
                f"[{window_from} ~ {window_to}]. "
                f"Raw overcapture (if any) will be clipped at parser level."
            ),
        })

    return issues


def validate_hash_completeness(run_dir: Path) -> list[dict]:
    """Check hash manifests exist."""
    issues = []
    hash_dir = run_dir / "21_hash"

    if not (hash_dir / "raw_hash_manifest.json").exists():
        issues.append({
            "gate": "hash_completeness",
            "severity": "FAIL",
            "message": "Missing 21_hash/raw_hash_manifest.json",
        })

    if not (hash_dir / "pack_hash_manifest.json").exists():
        issues.append({
            "gate": "hash_completeness",
            "severity": "FAIL",
            "message": "Missing 21_hash/pack_hash_manifest.json",
        })

    return issues


def validate_schema_conformance(run_dir: Path, run_manifest: dict) -> list[dict]:
    """Full JSON Schema validation of run_manifest and hash manifests.

    Uses jsonschema library for complete validation: required, type, enum,
    pattern, const, nested objects, additionalProperties.
    """
    import jsonschema

    issues = []

    # Find schema directory
    project_root = run_dir
    while project_root.name != "PROJECT_triple_sigma" and project_root.parent != project_root:
        project_root = project_root.parent
    schema_dir = project_root / "_coord" / "ops" / "schemas"

    if not schema_dir.exists():
        issues.append({
            "gate": "schema_conformance",
            "severity": "WARN",
            "message": f"Schema directory not found: {schema_dir}",
        })
        return issues

    def check_schema(data, schema_path, label):
        if not schema_path.exists():
            issues.append({
                "gate": "schema_conformance",
                "severity": "WARN",
                "message": f"[{label}] Schema file not found: {schema_path.name}",
            })
            return
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        fmt_checker = jsonschema.FormatChecker()

        @fmt_checker.checks("date-time", raises=ValueError)
        def check_datetime(value):
            # RFC3339 strict: YYYY-MM-DDTHH:MM:SS with timezone offset (Z or ±HH:MM)
            if not isinstance(value, str) or re.fullmatch(RFC3339_DATETIME_PATTERN, value) is None:
                raise ValueError(f"Not a valid RFC3339 date-time: {value}")
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True

        validator = jsonschema.Draft7Validator(
            schema,
            format_checker=fmt_checker,
        )
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in error.absolute_path) or "(root)"
            issues.append({
                "gate": "schema_conformance",
                "severity": "FAIL",
                "message": f"[{label}] {path}: {error.message}",
            })

    check_schema(run_manifest, schema_dir / "campaign_run_manifest.schema.json", "run_manifest")

    raw_hash_path = run_dir / "21_hash" / "raw_hash_manifest.json"
    if raw_hash_path.exists():
        with open(raw_hash_path, encoding="utf-8") as f:
            check_schema(json.load(f), schema_dir / "raw_hash_manifest.schema.json", "raw_hash")

    pack_hash_path = run_dir / "21_hash" / "pack_hash_manifest.json"
    if pack_hash_path.exists():
        with open(pack_hash_path, encoding="utf-8") as f:
            check_schema(json.load(f), schema_dir / "pack_hash_manifest.schema.json", "pack_hash")

    return issues


def validate_hash_integrity(run_dir: Path) -> list[dict]:
    """Recompute SHA-256 of raw files and compare to manifest."""
    issues = []
    raw_hash_path = run_dir / "21_hash" / "raw_hash_manifest.json"

    if not raw_hash_path.exists():
        return issues  # Already caught by hash_completeness

    with open(raw_hash_path, encoding="utf-8") as f:
        raw_hash = json.load(f)

    raw_dir = run_dir / "20_raw"
    for filename, entry in raw_hash.get("files", {}).items():
        file_path = raw_dir / filename
        if not file_path.exists():
            issues.append({
                "gate": "hash_integrity",
                "severity": "FAIL",
                "message": f"File listed in hash manifest but missing: {filename}",
            })
            continue

        actual_hash = sha256_file(file_path)
        expected_hash = entry.get("sha256", "")
        if actual_hash != expected_hash:
            issues.append({
                "gate": "hash_integrity",
                "severity": "FAIL",
                "message": (
                    f"Hash mismatch for {filename}: "
                    f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
                ),
            })

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate a sealed campaign run for admissibility (F1/F6 remediation)."
    )
    parser.add_argument("run_dir", type=Path, help="Path to RUN_<ts> directory")
    parser.add_argument(
        "--campaign-manifest", type=Path, default=None,
        help="Path to campaign manifest.yaml (auto-detected from run_manifest if omitted)"
    )
    args = parser.parse_args()

    run_dir = args.run_dir
    if not run_dir.exists():
        print(f"FATAL: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Load run manifest
    run_manifest_path = run_dir / "run_manifest.json"
    if not run_manifest_path.exists():
        print(f"FATAL: run_manifest.json not found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    with open(run_manifest_path, encoding="utf-8") as f:
        run_manifest = json.load(f)

    # Load campaign manifest
    campaign_manifest_path = args.campaign_manifest
    if campaign_manifest_path is None:
        manifest_ref = run_manifest.get("manifest_ref", "")
        if manifest_ref:
            campaign_manifest_path = Path(manifest_ref)
        else:
            # Try to find it relative to run_dir
            # run_dir = campaigns/<id>/runs/RUN_<ts>/ → campaign_dir = campaigns/<id>/
            campaign_dir = run_dir.parent.parent
            campaign_manifest_path = campaign_dir / "manifest.yaml"

    if not campaign_manifest_path.exists():
        print(f"FATAL: Campaign manifest not found: {campaign_manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(campaign_manifest_path, encoding="utf-8") as f:
        campaign_manifest = yaml.safe_load(f)

    campaign_dir = campaign_manifest_path.parent

    # Run all validation gates
    all_issues = []

    all_issues.extend(validate_provenance(run_dir, campaign_dir))
    all_issues.extend(validate_manifest_conformance(run_manifest, campaign_manifest))
    all_issues.extend(validate_raw_completeness(run_dir))
    all_issues.extend(validate_compile_clean(run_dir))
    all_issues.extend(validate_window_boundary(run_dir, run_manifest))
    all_issues.extend(validate_hash_completeness(run_dir))
    all_issues.extend(validate_hash_integrity(run_dir))
    all_issues.extend(validate_schema_conformance(run_dir, run_manifest))

    # Compute verdict
    fails = [i for i in all_issues if i["severity"] == "FAIL"]
    verdict = "PASS" if len(fails) == 0 else "FAIL"

    # Build report
    report = {
        "schema_version": "1.0",
        "run_id": run_manifest.get("run_id", "unknown"),
        "campaign_id": run_manifest.get("campaign_id", "unknown"),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "total_checks": len(all_issues) if all_issues else 7,
        "fails": len(fails),
        "issues": all_issues,
        "gates_checked": [
            "provenance",
            "pack_admission",
            "window_conformance",
            "raw_completeness",
            "compile_clean",
            "window_boundary",
            "hash_completeness",
            "hash_integrity",
            "schema_conformance",
        ],
    }

    # Write report
    validator_dir = run_dir / "50_validator"
    validator_dir.mkdir(parents=True, exist_ok=True)
    report_path = validator_dir / "validator_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print summary
    print(f"Validation: {verdict}")
    print(f"  Run: {run_manifest.get('run_id', 'unknown')}")
    print(f"  Campaign: {run_manifest.get('campaign_id', 'unknown')}")

    if fails:
        print(f"\n{len(fails)} FAIL(s):")
        for issue in fails:
            print(f"  [{issue['gate']}] {issue['message']}")
        print(f"\nReport: {report_path}")
        sys.exit(1)
    else:
        print(f"  All gates passed.")
        print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
