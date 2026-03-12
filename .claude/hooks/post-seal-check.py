#!/usr/bin/env python3
"""PostToolUse hook: auto-run validator after campaign seal command.

Reads stdin JSON from Claude Code hook system. If the Bash command
contained 'run_campaign_backtest.py seal', extracts the run directory
and runs validate_campaign_run.py, reporting the result via stderr.

Exit code 0 always (PostToolUse hooks cannot block).
"""

import json
import re
import subprocess
import sys


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return

    command = data.get("tool_input", {}).get("command", "")

    # Check if this was a seal command
    if "run_campaign_backtest.py" not in command or "seal" not in command:
        return

    # Extract run directory from command (last argument after 'seal')
    match = re.search(r"seal\s+[\"']?([^\s\"']+)[\"']?", command)
    if not match:
        return

    run_dir = match.group(1)

    # Run validator
    print(f"[post-seal-hook] Auto-validating sealed run: {run_dir}", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, "tools/validate_campaign_run.py", run_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(f"[post-seal-hook] Validator output:\n{result.stdout}", file=sys.stderr)
        if result.returncode != 0:
            print(f"[post-seal-hook] Validator FAILED (exit {result.returncode})", file=sys.stderr)
            if result.stderr:
                print(f"[post-seal-hook] stderr: {result.stderr}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("[post-seal-hook] Validator timed out after 60s", file=sys.stderr)
    except FileNotFoundError:
        print("[post-seal-hook] validate_campaign_run.py not found", file=sys.stderr)


if __name__ == "__main__":
    main()
