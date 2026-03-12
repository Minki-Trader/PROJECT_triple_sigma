"""
run_campaign_backtest.py - Campaign-native backtest runner.

Reads a campaign manifest.yaml and produces an admissible run directory
with full provenance chain. This tool handles:
  1. Preset generation from manifest params + window
  2. Run directory scaffold creation
  3. Post-run: raw output sealing (SHA-256 hash manifests)
  4. Run manifest generation (conforms to campaign_run_manifest.schema.json)

The actual MT5 tester execution is manual (workstation-bound). Workflow:
  Step 1: `python run_campaign_backtest.py prepare <manifest> --window <alias>`
           → creates run dir + preset .ini
  Step 2: User runs preset in MT5 terminal, places outputs in 20_raw/
  Step 3: `python run_campaign_backtest.py seal <run_dir>`
           → seals hashes, generates run_manifest.json

Usage:
    python tools/run_campaign_backtest.py prepare <manifest_yaml> --window benchmark
    python tools/run_campaign_backtest.py seal <run_dir>

Finding: F1 (Campaign provenance breach)
Phase: A1
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


# ---------------------------------------------------------------------------
# SHA-256 utility (pattern from package_step21_artifacts.py)
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_manifest(manifest_path: Path) -> dict:
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_window(manifest: dict, window_alias: str) -> tuple[str, str]:
    """Return (from, to) for the given window alias."""
    windows = manifest.get("windows", {})

    # Check optimization folds
    if window_alias.startswith("fold_"):
        folds = windows.get("optimization_folds", {}).get("folds", [])
        for fold in folds:
            if fold["id"] == window_alias:
                return fold["from"], fold["to"]
        raise ValueError(f"Window alias '{window_alias}' not found in optimization_folds")

    # Check named windows
    if window_alias in windows:
        w = windows[window_alias]
        return w["from"], w["to"]

    raise ValueError(
        f"Window alias '{window_alias}' not found. "
        f"Available: {list(windows.keys())} + fold IDs"
    )


def resolve_pack(manifest: dict, pack_type: str = "profitability") -> str:
    """Return pack directory name from manifest."""
    if pack_type == "profitability":
        return manifest.get("profitability_pack", "")
    elif pack_type == "runtime_integrity":
        return manifest.get("runtime_integrity_pack", "")
    raise ValueError(f"Unknown pack type: {pack_type}")


# ---------------------------------------------------------------------------
# Preset generation
# ---------------------------------------------------------------------------

def generate_preset(
    manifest: dict,
    window_from: str,
    window_to: str,
    pack_id: str,
    report_path: str,
) -> str:
    """Generate MT5 tester preset .ini content from manifest params."""
    baseline = manifest.get("tester_baseline", {})
    params = manifest.get("diagnostic_baseline_params", {}).get("params", {})

    # Override pack to campaign profitability pack
    params["InpModelPackDir"] = pack_id

    # Convert from/to to date-only for MT5 (YYYY.MM.DD)
    from_date = window_from.split(" ")[0]
    to_date = window_to.split(" ")[0]

    lines = [
        "[Tester]",
        f"Expert=PROJECT_triple_sigma\\src\\ea\\TripleSigma.ex5",
        f"Symbol={baseline.get('symbol', 'US100')}",
        f"Period={baseline.get('period', 'M5')}",
        "Optimization=0",
        f"Model={baseline.get('model', 4)}",
        "Dates=1",
        f"FromDate={from_date}",
        f"ToDate={to_date}",
        "ForwardMode=0",
        f"Deposit={baseline.get('deposit', 500)}",
        f"Currency={baseline.get('currency', 'USD')}",
        "ProfitInPips=0",
        f"Leverage={baseline.get('leverage', 100)}",
        "ExecutionMode=0",
        "OptimizationCriterion=0",
        "Visual=0",
        f"Report={report_path}",
        "ReplaceReport=1",
        "ShutdownTerminal=1",
        "",
        "[TesterInputs]",
        "InpStartupValidation=true",
        "InpLogHeartbeat=false",
        "InpTimerSeconds=1",
        "InpDebugAlignment=false",
    ]

    for key, value in params.items():
        # Convert Python bool to lowercase string
        if isinstance(value, bool):
            value = "true" if value else "false"
        lines.append(f"{key}={value}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Run directory scaffold
# ---------------------------------------------------------------------------

def create_run_scaffold(campaign_dir: Path, run_id: str) -> Path:
    """Create the run directory structure per Audit Section 8.6."""
    run_dir = campaign_dir / "runs" / run_id
    subdirs = [
        "00_request",
        "10_compile",
        "20_raw",
        "21_hash",
        "30_parsed",
        "40_kpi",
        "50_validator",
        "60_decision",
    ]
    for sub in subdirs:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    return run_dir


# ---------------------------------------------------------------------------
# Hash sealing
# ---------------------------------------------------------------------------

def seal_raw_outputs(run_dir: Path, run_id: str) -> dict:
    """Compute SHA-256 hashes for all files in 20_raw/. Returns manifest dict."""
    raw_dir = run_dir / "20_raw"
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw output directory not found: {raw_dir}")

    files = sorted(raw_dir.iterdir())
    if not files:
        raise FileNotFoundError(f"No files found in {raw_dir}")

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            path.name: {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in files
            if path.is_file()
        },
    }
    return manifest


def seal_pack(pack_dir: Path, pack_id: str) -> dict:
    """Compute SHA-256 hashes for all files in pack directory. Returns manifest dict."""
    if not pack_dir.exists():
        raise FileNotFoundError(f"Pack directory not found: {pack_dir}")

    manifest = {
        "schema_version": "1.0",
        "pack_id": pack_id,
        "pack_dir": str(pack_dir),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "models": {
            path.name: {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in sorted(pack_dir.iterdir())
            if path.is_file()
        },
        "registry_ref": "_coord/ops/control_pack_registry.yaml",
    }
    return manifest


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_prepare(args):
    """Prepare a campaign run: create scaffold + preset."""
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    campaign_id = manifest.get("campaign_id", "unknown")
    campaign_dir = manifest_path.parent

    # Resolve window
    window_from, window_to = resolve_window(manifest, args.window)
    pack_id = resolve_pack(manifest, "profitability")

    # Generate run ID
    run_id = f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    # Create scaffold
    run_dir = create_run_scaffold(campaign_dir, run_id)

    # Generate and save preset
    report_path = str(run_dir / "report").replace("/", "\\")
    preset_content = generate_preset(manifest, window_from, window_to, pack_id, report_path)
    preset_path = run_dir / "00_request" / "preset_snapshot.ini"
    preset_path.write_text(preset_content, encoding="utf-8")

    # Save request metadata
    request_meta = {
        "campaign_id": campaign_id,
        "run_id": run_id,
        "window_alias": args.window,
        "window_from": window_from,
        "window_to": window_to,
        "pack_id": pack_id,
        "manifest_ref": str(manifest_path),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "00_request" / "request_meta.json").write_text(
        json.dumps(request_meta, indent=2), encoding="utf-8"
    )

    print(f"Run prepared: {run_dir}")
    print(f"  Window: {args.window} ({window_from} -> {window_to})")
    print(f"  Pack: {pack_id}")
    print(f"  Preset: {preset_path}")
    print()
    print("Next steps:")
    print(f"  1. Run preset in MT5 terminal")
    print(f"  2. Copy raw outputs (trade_log.csv, bar_log_*.csv, exec_state.ini) to:")
    print(f"     {run_dir / '20_raw'}")
    print(f"  3. Copy compile_log.txt to:")
    print(f"     {run_dir / '10_compile'}")
    print(f"  4. Seal: python tools/run_campaign_backtest.py seal {run_dir}")


def cmd_seal(args):
    """Seal a campaign run: hash raw outputs + pack, generate run_manifest."""
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"FATAL: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Load request metadata
    request_meta_path = run_dir / "00_request" / "request_meta.json"
    if not request_meta_path.exists():
        print(f"FATAL: request_meta.json not found in {run_dir / '00_request'}", file=sys.stderr)
        sys.exit(1)

    with open(request_meta_path, encoding="utf-8") as f:
        request_meta = json.load(f)

    run_id = request_meta["run_id"]
    pack_id = request_meta["pack_id"]

    # Validate raw outputs exist
    raw_dir = run_dir / "20_raw"
    trade_log = raw_dir / "trade_log.csv"
    exec_state = raw_dir / "exec_state.ini"
    bar_logs = sorted(raw_dir.glob("bar_log_*.csv"))
    compile_log = run_dir / "10_compile" / "compile_log.txt"

    missing = []
    if not trade_log.exists():
        missing.append("20_raw/trade_log.csv")
    if not exec_state.exists():
        missing.append("20_raw/exec_state.ini")
    if not bar_logs:
        missing.append("20_raw/bar_log_*.csv (at least one)")
    if not compile_log.exists():
        missing.append("10_compile/compile_log.txt")

    if missing:
        print("FATAL: Missing required files:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)

    # Seal raw outputs
    raw_hash = seal_raw_outputs(run_dir, run_id)
    raw_hash_path = run_dir / "21_hash" / "raw_hash_manifest.json"
    raw_hash_path.write_text(json.dumps(raw_hash, indent=2), encoding="utf-8")
    print(f"Raw hash manifest: {raw_hash_path} ({len(raw_hash['files'])} files)")

    # Seal pack
    # Resolve pack directory (MQL5/Files/<pack_id>)
    project_root = run_dir.resolve()
    while project_root.name != "PROJECT_triple_sigma" and project_root.parent != project_root:
        project_root = project_root.parent

    # PROJECT_triple_sigma → Experts → MQL5 → Files
    mql5_files = project_root.parent.parent / "Files"
    pack_dir = mql5_files / pack_id

    if pack_dir.exists():
        pack_hash = seal_pack(pack_dir, pack_id)
        pack_hash_path = run_dir / "21_hash" / "pack_hash_manifest.json"
        pack_hash_path.write_text(json.dumps(pack_hash, indent=2), encoding="utf-8")
        print(f"Pack hash manifest: {pack_hash_path} ({len(pack_hash['models'])} models)")
    else:
        print(f"WARNING: Pack directory not found at {pack_dir}, skipping pack hash")
        pack_hash = None

    # Parse compile log for error/warning count (MT5 result line: "Result: N errors, N warnings")
    compile_text = compile_log.read_text(encoding="utf-8", errors="replace")
    result_match = re.search(r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", compile_text)
    if result_match:
        compile_errors = int(result_match.group(1))
        compile_warnings = int(result_match.group(2))
    else:
        # Fallback: if no Result line found, count actual error/warning lines (excluding summary)
        compile_errors = len(re.findall(r"(?i)^.*\berror\b(?!\s*s?,).*$", compile_text, re.MULTILINE))
        compile_warnings = len(re.findall(r"(?i)^.*\bwarning\b(?!\s*s?,).*$", compile_text, re.MULTILINE))

    # Generate run manifest
    run_manifest = {
        "schema_version": "1.0",
        "campaign_id": request_meta["campaign_id"],
        "run_id": run_id,
        "run_timestamp": request_meta["prepared_at"],
        "manifest_ref": request_meta["manifest_ref"],
        "pack_id": pack_id,
        "pack_dir": str(pack_dir) if pack_dir.exists() else pack_id,
        "preset_snapshot": "00_request/preset_snapshot.ini",
        "window_alias": request_meta["window_alias"],
        "window_from": request_meta["window_from"],
        "window_to": request_meta["window_to"],
        "compile_result": {
            "errors": compile_errors,
            "warnings": compile_warnings,
            "log_path": "10_compile/compile_log.txt",
        },
        "raw_outputs": {
            "trade_log": "20_raw/trade_log.csv",
            "bar_logs": [f"20_raw/{bl.name}" for bl in bar_logs],
            "exec_state": "20_raw/exec_state.ini",
        },
        "hash_manifests": {
            "raw_hash_ref": "21_hash/raw_hash_manifest.json",
            "pack_hash_ref": "21_hash/pack_hash_manifest.json" if pack_hash else None,
        },
        "status": "complete",
    }

    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    print(f"Run manifest: {manifest_path}")

    # Schema validation
    schema_dir = project_root / "_coord" / "ops" / "schemas"
    validation_errors = []

    errs = validate_against_schema(run_manifest, schema_dir / "campaign_run_manifest.schema.json")
    if errs:
        validation_errors.extend([f"[run_manifest] {e}" for e in errs])

    errs = validate_against_schema(raw_hash, schema_dir / "raw_hash_manifest.schema.json")
    if errs:
        validation_errors.extend([f"[raw_hash] {e}" for e in errs])

    if pack_hash:
        errs = validate_against_schema(pack_hash, schema_dir / "pack_hash_manifest.schema.json")
        if errs:
            validation_errors.extend([f"[pack_hash] {e}" for e in errs])

    if validation_errors:
        print("\nSchema validation ERRORS (seal cannot proceed):", file=sys.stderr)
        for err in validation_errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)

    # Summary
    print()
    print(f"Run sealed: {run_id}")
    print(f"  Raw files: {len(raw_hash['files'])}")
    print(f"  Compile: {compile_errors} errors, {compile_warnings} warnings")
    if compile_errors > 0:
        print("  WARNING: Compile errors detected — run may not be admissible")
    print()
    print("Next step: validate with:")
    print(f"  python tools/validate_campaign_run.py {run_dir}")


# ---------------------------------------------------------------------------
# Full JSON Schema validation
# ---------------------------------------------------------------------------

def validate_against_schema(data: dict, schema_path: Path) -> list[str]:
    """Validate data against a JSON Schema using jsonschema library.

    Returns list of validation error messages (empty = valid).
    Performs full validation: required, type, enum, pattern, const, nested objects.
    """
    import jsonschema

    errors = []
    if not schema_path.exists():
        errors.append(f"Schema file not found: {schema_path}")
        return errors

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
        errors.append(f"{path}: {error.message}")

    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Campaign-native backtest runner (F1 remediation)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prepare
    prep = subparsers.add_parser("prepare", help="Create run scaffold + preset from manifest")
    prep.add_argument("manifest", type=str, help="Path to campaign manifest.yaml")
    prep.add_argument(
        "--window", type=str, required=True,
        help="Window alias (fold_1, fold_2, fold_3, benchmark, oos_validation, stress)"
    )

    # seal
    seal = subparsers.add_parser("seal", help="Seal raw outputs and generate run manifest")
    seal.add_argument("run_dir", type=str, help="Path to RUN_<ts> directory")

    args = parser.parse_args()

    if args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "seal":
        cmd_seal(args)


if __name__ == "__main__":
    main()
