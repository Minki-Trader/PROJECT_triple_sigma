#!/usr/bin/env python3
"""PreToolUse hook: block promotion to _coord/releases/ without validator approval.

Reads stdin JSON from Claude Code hook system. If the Bash command
targets _coord/releases/, checks that a validator_report.json with
verdict=PASS exists. Denies the action if not.

Exit code 0 = allow, exit code 2 = deny.
"""

import json
import sys
from pathlib import Path


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return  # Allow on parse failure (non-blocking)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return

    command = data.get("tool_input", {}).get("command", "")

    # Check if command targets releases directory
    if "_coord/releases/" not in command and "_coord\\releases\\" not in command:
        return  # Not a promotion command, allow

    # Find the most recent run with a validator report
    campaigns_dir = Path("_coord/campaigns")
    if not campaigns_dir.exists():
        print(
            json.dumps({"decision": "deny"}),
        )
        print(
            "[pre-promotion-guard] DENIED: _coord/campaigns/ not found. "
            "Cannot verify validator approval.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Search for validator reports in all runs
    validator_reports = sorted(campaigns_dir.glob("**/50_validator/validator_report.json"))
    if not validator_reports:
        print(json.dumps({"decision": "deny"}))
        print(
            "[pre-promotion-guard] DENIED: No validator_report.json found. "
            "Run /integrity-gate and /codex-validator first.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Check the most recent report
    latest = validator_reports[-1]
    try:
        report = json.loads(latest.read_text(encoding="utf-8"))
        verdict = report.get("verdict", "UNKNOWN")
    except (json.JSONDecodeError, OSError):
        verdict = "UNKNOWN"

    if verdict != "PASS":
        print(json.dumps({"decision": "deny"}))
        print(
            f"[pre-promotion-guard] DENIED: Latest validator verdict is {verdict} "
            f"(from {latest}). Must be PASS before promotion.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Passed — allow promotion
    print(
        f"[pre-promotion-guard] ALLOWED: Validator verdict PASS ({latest})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
