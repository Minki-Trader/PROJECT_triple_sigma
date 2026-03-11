from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


CORE_COMPARE_COLUMNS = [
    "trade_id",
    "event_type",
    "direction",
    "lot",
    "entry_price",
    "exit_price",
    "sl_price",
    "tp_price",
    "pnl",
    "k_sl_req",
    "k_tp_req",
    "k_sl_eff",
    "k_tp_eff",
    "hold_bars",
    "bars_held",
    "exit_reason",
    "regime_id_at_entry",
    "spread_atr_at_entry",
    "flip_used",
    "model_pack_version",
    "clf_version",
    "prm_version",
    "cost_model_version",
]


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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def trade_log_stats(trade_log_path: Path) -> dict:
    rows = read_csv_rows(trade_log_path)

    event_type_counts = Counter(row.get("event_type", "") for row in rows)
    exit_reason_counts = Counter(row.get("exit_reason", "") for row in rows if row.get("event_type") == "EXIT")
    modify_reason_counts = Counter(row.get("modify_reason", "") for row in rows if row.get("event_type") == "MODIFY")

    non_modify_groups = Counter(
        (row.get("trade_id", ""), row.get("event_type", ""))
        for row in rows
        if row.get("event_type") != "MODIFY"
    )
    exit_groups = Counter(
        row.get("trade_id", "")
        for row in rows
        if row.get("event_type") == "EXIT"
    )

    same_timestamp_exit_to_entry = 0
    for idx in range(len(rows) - 1):
        if rows[idx].get("event_type") == "EXIT" and rows[idx + 1].get("event_type") == "ENTRY":
            if rows[idx].get("timestamp") == rows[idx + 1].get("timestamp"):
                same_timestamp_exit_to_entry += 1

    tx_authority_counts = Counter(row.get("tx_authority", "") for row in rows if row.get("tx_authority"))
    runtime_status_counts = Counter(row.get("runtime_reload_status", "") for row in rows if row.get("runtime_reload_status"))

    return {
        "rows": len(rows),
        "event_type_counts": dict(event_type_counts),
        "exit_reason_counts": dict(exit_reason_counts),
        "modify_reason_counts": dict(modify_reason_counts),
        "duplicate_non_modify_trade_event_groups": sum(1 for count in non_modify_groups.values() if count > 1),
        "duplicate_exit_groups": sum(1 for count in exit_groups.values() if count > 1),
        "same_timestamp_exit_to_entry": same_timestamp_exit_to_entry,
        "modify_count": int(event_type_counts.get("MODIFY", 0)),
        "tx_authority_counts": dict(tx_authority_counts),
        "runtime_reload_status_counts": dict(runtime_status_counts),
    }


def broker_audit_stats(path: Path) -> dict:
    if not path.exists():
        return {}
    rows = read_csv_rows(path)
    return {
        "rows": len(rows),
        "tag_counts": dict(Counter(row.get("tag", "") for row in rows)),
    }


def last_bar_state(artifact_dir: Path) -> dict:
    bar_logs = sorted(artifact_dir.glob("bar_log_*.csv"))
    if not bar_logs:
        return {}

    rows = read_csv_rows(bar_logs[-1])
    if not rows:
        return {}
    row = rows[-1]
    return {
        "active_model_pack_dir": row.get("active_model_pack_dir", ""),
        "runtime_reload_status": row.get("runtime_reload_status", ""),
        "runtime_reload_attempts": row.get("runtime_reload_attempts", ""),
        "runtime_reload_successes": row.get("runtime_reload_successes", ""),
        "runtime_reload_rollbacks": row.get("runtime_reload_rollbacks", ""),
    }


def compare_with_baseline(current_trade_log: Path, baseline_dir: Path) -> dict:
    baseline_trade_log = baseline_dir / "trade_log.csv"
    if not baseline_trade_log.exists():
        return {"available": False, "reason": f"missing baseline trade log: {baseline_trade_log}"}

    current_rows = read_csv_rows(current_trade_log)
    baseline_rows = read_csv_rows(baseline_trade_log)

    if not current_rows and not baseline_rows:
        return {"available": True, "match": True, "common_columns": CORE_COMPARE_COLUMNS, "row_count_match": True}

    current_columns = set(current_rows[0].keys()) if current_rows else set()
    baseline_columns = set(baseline_rows[0].keys()) if baseline_rows else set()
    common_columns = [column for column in CORE_COMPARE_COLUMNS if column in current_columns and column in baseline_columns]

    projected_current = [tuple(row.get(column, "") for column in common_columns) for row in current_rows]
    projected_baseline = [tuple(row.get(column, "") for column in common_columns) for row in baseline_rows]

    return {
        "available": True,
        "match": projected_current == projected_baseline,
        "row_count_match": len(current_rows) == len(baseline_rows),
        "current_rows": len(current_rows),
        "baseline_rows": len(baseline_rows),
        "common_columns": common_columns,
    }


def write_summary(
    path: Path,
    *,
    title: str,
    preset: str,
    validation_class: str,
    trigger_source: str,
    synthetic: bool,
    baseline_compare: str,
    trade_stats: dict,
    broker_stats: dict,
    bar_state: dict,
    baseline_result: dict | None,
) -> None:
    lines = [
        f"# {title} Summary",
        "",
        "Run date:",
        f"- {datetime.now().astimezone().date().isoformat()}",
        "",
        "Preset:",
        f"- `{preset}`",
        "",
        "Validation class:",
        f"- `{validation_class}`",
        "",
        "Trigger source:",
        f"- `{trigger_source}`",
        f"- synthetic: `{'true' if synthetic else 'false'}`",
        "",
        "Trade log stats:",
        f"- rows: `{trade_stats.get('rows', 0)}`",
        f"- event counts: `{json.dumps(trade_stats.get('event_type_counts', {}), ensure_ascii=True, sort_keys=True)}`",
        f"- exit reasons: `{json.dumps(trade_stats.get('exit_reason_counts', {}), ensure_ascii=True, sort_keys=True)}`",
        f"- modify reasons: `{json.dumps(trade_stats.get('modify_reason_counts', {}), ensure_ascii=True, sort_keys=True)}`",
        f"- duplicate non-modify `(trade_id,event_type)` groups: `{trade_stats.get('duplicate_non_modify_trade_event_groups', 0)}`",
        f"- duplicate `EXIT` groups: `{trade_stats.get('duplicate_exit_groups', 0)}`",
        f"- same-timestamp `EXIT -> ENTRY`: `{trade_stats.get('same_timestamp_exit_to_entry', 0)}`",
        f"- tx authority tags: `{json.dumps(trade_stats.get('tx_authority_counts', {}), ensure_ascii=True, sort_keys=True)}`",
        "",
        "Runtime tail state:",
        f"- active model pack: `{bar_state.get('active_model_pack_dir', '')}`",
        f"- runtime status: `{bar_state.get('runtime_reload_status', '')}`",
        f"- runtime counters: `attempt={bar_state.get('runtime_reload_attempts', '')} success={bar_state.get('runtime_reload_successes', '')} rollback={bar_state.get('runtime_reload_rollbacks', '')}`",
    ]

    if broker_stats:
        lines.extend(
            [
                "",
                "Broker audit stats:",
                f"- rows: `{broker_stats.get('rows', 0)}`",
                f"- tags: `{json.dumps(broker_stats.get('tag_counts', {}), ensure_ascii=True, sort_keys=True)}`",
            ]
        )

    if baseline_compare:
        lines.extend(["", "Baseline compare:", f"- baseline: `{baseline_compare}`"])
        if baseline_result:
            if baseline_result.get("available"):
                lines.extend(
                    [
                        f"- core-row match: `{'true' if baseline_result.get('match') else 'false'}`",
                        f"- row count match: `{'true' if baseline_result.get('row_count_match') else 'false'}`",
                        f"- common columns: `{', '.join(baseline_result.get('common_columns', []))}`",
                    ]
                )
            else:
                lines.append(f"- compare skipped: `{baseline_result.get('reason', '')}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    project_root = Path(__file__).resolve().parent.parent
    artifact_dir = Path(args.artifact_dir)
    source_log_dir = Path(args.source_log_dir)
    agent_log = Path(args.agent_log)

    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    for name in ("trade_log.csv", "exec_state.ini", "broker_audit.csv"):
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
    trade_stats = trade_log_stats(trade_log_path) if trade_log_path.exists() else {}
    broker_stats = broker_audit_stats(artifact_dir / "broker_audit.csv")
    bar_state = last_bar_state(artifact_dir)

    baseline_result = None
    if args.baseline_compare and trade_log_path.exists():
        baseline_result = compare_with_baseline(trade_log_path, project_root / args.baseline_compare)

    readme_path = artifact_dir / "README.md"
    readme_lines = [
        f"# {args.title}",
        "",
        "Included files:",
        "- `README.md`",
        "- `manifest.json`",
        "- `trade_log.csv`",
        "- `exec_state.ini`",
        "- `broker_audit.csv` when enabled",
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
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "trade_log_stats": trade_stats,
        "broker_audit_stats": broker_stats,
        "last_bar_state": bar_state,
        "baseline_result": baseline_result,
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary_path = Path(args.summary)
    if not summary_path.is_absolute():
        summary_path = project_root / summary_path
    write_summary(
        summary_path,
        title=args.title,
        preset=args.preset,
        validation_class=args.validation_class,
        trigger_source=args.trigger_source,
        synthetic=args.synthetic,
        baseline_compare=args.baseline_compare,
        trade_stats=trade_stats,
        broker_stats=broker_stats,
        bar_state=bar_state,
        baseline_result=baseline_result,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
