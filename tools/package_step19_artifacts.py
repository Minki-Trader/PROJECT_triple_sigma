from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def read_log_segment(path: Path, offset: int) -> str:
    data = path.read_bytes()
    segment = data[offset:]
    if segment.startswith(b"\xff\xfe") or b"\x00" in segment[:8]:
        return segment.decode("utf-16", errors="replace")
    return segment.decode("utf-8", errors="replace")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trade_log_stats(trade_log_path: Path) -> dict:
    rows = []
    with trade_log_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    event_groups = Counter((row.get("trade_id", ""), row.get("event_type", "")) for row in rows)
    duplicate_groups = sum(1 for count in event_groups.values() if count > 1)

    timestamps = []
    for row in rows:
        timestamps.append((row.get("timestamp", ""), row.get("event_type", "")))

    same_timestamp_exit_to_entry = 0
    for idx in range(len(timestamps) - 1):
        if timestamps[idx][1] == "EXIT" and timestamps[idx + 1][1] == "ENTRY":
            if timestamps[idx][0] == timestamps[idx + 1][0]:
                same_timestamp_exit_to_entry += 1

    exit_reason_counts = Counter(row.get("exit_reason", "") for row in rows if row.get("event_type") == "EXIT")
    event_type_counts = Counter(row.get("event_type", "") for row in rows)

    return {
        "rows": len(rows),
        "event_type_counts": dict(event_type_counts),
        "exit_reason_counts": dict(exit_reason_counts),
        "duplicate_trade_event_groups": duplicate_groups,
        "same_timestamp_exit_to_entry": same_timestamp_exit_to_entry,
        "modify_count": int(event_type_counts.get("MODIFY", 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--source-log-dir", required=True)
    parser.add_argument("--agent-log", required=True)
    parser.add_argument("--log-offset", required=True, type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--preset", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--validation-class", required=True)
    parser.add_argument("--trigger-source", required=True)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--baseline-compare", default="")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    source_log_dir = Path(args.source_log_dir)
    agent_log = Path(args.agent_log)

    if artifact_dir.exists():
      shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    for name in ("trade_log.csv", "exec_state.ini"):
        src = source_log_dir / name
        if src.exists():
            dst = artifact_dir / name
            shutil.copy2(src, dst)
            copied_files.append(dst)

    for src in sorted(source_log_dir.glob("bar_log_*.csv")):
        dst = artifact_dir / src.name
        shutil.copy2(src, dst)
        copied_files.append(dst)

    log_tail_path = artifact_dir / "tester_log_tail.txt"
    log_tail_path.write_text(read_log_segment(agent_log, args.log_offset), encoding="utf-8")
    copied_files.append(log_tail_path)

    trade_log_path = artifact_dir / "trade_log.csv"
    stats = trade_log_stats(trade_log_path) if trade_log_path.exists() else {}

    readme_path = artifact_dir / "README.md"
    readme_lines = [
        f"# {args.title}",
        "",
        "Included files:",
        "- `README.md`",
        "- `manifest.json`",
        "- `trade_log.csv`",
        "- `exec_state.ini`",
        "- `tester_log_tail.txt`",
        "- `bar_log_YYYYMMDD.csv` files emitted by the run",
        "",
        "Source run:",
        f"- preset: `{args.preset}`",
        f"- summary: `{args.summary}`",
        f"- validation class: `{args.validation_class}`",
        f"- trigger source: `{args.trigger_source}`",
        f"- synthetic: `{'true' if args.synthetic else 'false'}`",
    ]
    if args.baseline_compare:
        readme_lines.append(f"- baseline compare: `{args.baseline_compare}`")
    readme_path.write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    manifest = {
        "artifact_dir": str(artifact_dir),
        "preset": args.preset,
        "summary": args.summary,
        "validation_class": args.validation_class,
        "trigger_source": args.trigger_source,
        "synthetic": args.synthetic,
        "baseline_compare": args.baseline_compare,
        "files": {
            path.name: {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in sorted(copied_files + [readme_path], key=lambda p: p.name)
        },
        "trade_log_stats": stats,
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
