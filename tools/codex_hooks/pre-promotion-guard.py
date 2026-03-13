#!/usr/bin/env python3
"""Block promotion unless a run is promotion-ready.

Supports two modes:
1. Direct CLI: `python tools/codex_hooks/pre-promotion-guard.py <run_dir>`
2. Hook payload on stdin from an external orchestrator
"""

import json
import re
import sys
from pathlib import Path


RUN_ID_PATTERN = r"RUN_\d{8}T\d{6}Z"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def extract_target_run_id(command: str) -> str | None:
    run_ids = sorted(set(re.findall(RUN_ID_PATTERN, command)))
    if len(run_ids) == 1:
        return run_ids[0]
    return None


def resolve_run_dir_from_hook_payload() -> Path | None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return None

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return None

    command = data.get("tool_input", {}).get("command", "")
    if "_coord/releases/" not in command and "_coord\\releases\\" not in command:
        return None

    run_id = extract_target_run_id(command)
    if run_id is None:
        print(
            json.dumps({"decision": "deny"}),
            flush=True,
        )
        print(
            "[pre-promotion-guard] DENIED: Could not resolve a unique RUN_<ts> from the "
            "promotion command. Include the source run path explicitly.",
            file=sys.stderr,
        )
        sys.exit(2)

    reports = sorted(Path("_coord/campaigns").glob(f"**/runs/{run_id}/50_validator/validator_report.json"))
    if len(reports) != 1:
        print(json.dumps({"decision": "deny"}), flush=True)
        if not reports:
            print(
                f"[pre-promotion-guard] DENIED: No validator_report.json found for {run_id}.",
                file=sys.stderr,
            )
        else:
            print(
                f"[pre-promotion-guard] DENIED: Multiple validator_report.json files found for {run_id}.",
                file=sys.stderr,
            )
        sys.exit(2)

    return reports[0].parents[1]


def evaluate_run(run_dir: Path) -> tuple[bool, str]:
    campaign_dir = run_dir.parent.parent
    validator_path = run_dir / "50_validator" / "validator_report.json"
    codex_validator_path = run_dir / "50_validator" / "codex_validator_report.md"
    run_manifest_path = run_dir / "run_manifest.json"
    parse_manifest_path = run_dir / "30_parsed" / "parse_manifest.json"
    freeze_hash_path = campaign_dir / "freeze" / "freeze_hash_manifest.json"
    pack_parity_path = campaign_dir / "freeze" / "pack_parity_recheck.json"

    required_paths = [
        validator_path,
        codex_validator_path,
        run_manifest_path,
        parse_manifest_path,
        freeze_hash_path,
        pack_parity_path,
    ]
    for path in required_paths:
        if not path.exists():
            return False, f"Missing required promotion artifact: {path}"

    if codex_validator_path.stat().st_size == 0:
        return False, f"Codex validator memo is empty: {codex_validator_path}"

    try:
        report = load_json(validator_path)
        run_manifest = load_json(run_manifest_path)
        parse_manifest = load_json(parse_manifest_path)
        freeze_hash = load_json(freeze_hash_path)
        pack_parity = load_json(pack_parity_path)
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"Cannot read promotion evidence: {exc}"

    if report.get("verdict") != "PASS":
        return False, f"validator_report.json verdict is {report.get('verdict', 'UNKNOWN')}"
    if not parse_manifest.get("pass", False):
        return False, "parse_manifest.json reports pass=false"
    if not parse_manifest.get("invariants_pass", False):
        return False, "parse_manifest.json reports invariants_pass=false"
    if "master_tables_pass" in parse_manifest and not parse_manifest.get("master_tables_pass", False):
        return False, "parse_manifest.json reports master_tables_pass=false"

    clipping = parse_manifest.get("window_clipping")
    if not isinstance(clipping, dict):
        return False, "parse_manifest.json is missing window_clipping"

    expected_from = run_manifest.get("window_from", "")
    expected_to = run_manifest.get("window_to", "")
    if clipping.get("window_from") != expected_from or clipping.get("window_to") != expected_to:
        return False, (
            "parse_manifest window_clipping does not match run_manifest window: "
            f"{clipping.get('window_from')}->{clipping.get('window_to')} vs "
            f"{expected_from}->{expected_to}"
        )

    if not freeze_hash.get("role_overlap_pass", False):
        return False, "freeze_hash_manifest.json reports role_overlap_pass=false"

    if pack_parity.get("verdict") != "PASS":
        missing_export = pack_parity.get("missing_in_export_manifest", [])
        mismatch_note = f" missing_in_export_manifest={missing_export}" if missing_export else ""
        return False, (
            "pack_parity_recheck.json verdict is "
            f"{pack_parity.get('verdict', 'UNKNOWN')}.{mismatch_note}"
        )

    return True, f"{run_dir.name} is promotion-ready"


def main() -> int:
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
        ok, message = evaluate_run(run_dir)
        stream = sys.stdout if ok else sys.stderr
        print(f"[pre-promotion-guard] {'ALLOWED' if ok else 'DENIED'}: {message}", file=stream)
        return 0 if ok else 2

    run_dir = resolve_run_dir_from_hook_payload()
    if run_dir is None:
        return 0

    ok, message = evaluate_run(run_dir)
    if not ok:
        print(json.dumps({"decision": "deny"}), flush=True)
        print(f"[pre-promotion-guard] DENIED: {message}", file=sys.stderr)
        return 2

    print(f"[pre-promotion-guard] ALLOWED: {message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
