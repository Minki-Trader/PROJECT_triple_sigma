#!/usr/bin/env python3
"""Run campaign validation after sealing.

Supports two modes:
1. Direct CLI: `python tools/codex_hooks/post-seal-check.py <run_dir>`
2. Hook payload on stdin from an external orchestrator
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def resolve_run_dir_from_hook_payload() -> str | None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return None

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return None

    command = data.get("tool_input", {}).get("command", "")
    if "run_campaign_backtest.py" not in command or "seal" not in command:
        return None

    match = re.search(r"seal\s+[\"']?([^\s\"']+)[\"']?", command)
    if not match:
        return None
    return match.group(1)


def run_validator(run_dir: str) -> int:
    print(f"[post-seal-check] validating sealed run: {run_dir}", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, "tools/validate_campaign_run.py", run_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("[post-seal-check] validator timed out after 60s", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("[post-seal-check] validate_campaign_run.py not found", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


def main() -> int:
    if len(sys.argv) > 1:
        run_dir = sys.argv[1]
        if not Path(run_dir).exists():
            print(f"[post-seal-check] run directory not found: {run_dir}", file=sys.stderr)
            return 1
        return run_validator(run_dir)

    run_dir = resolve_run_dir_from_hook_payload()
    if run_dir is None:
        return 0

    run_validator(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
